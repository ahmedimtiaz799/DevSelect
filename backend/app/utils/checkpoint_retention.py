import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator

from app.utils.logging_hygiene import safe_log_id


logger = logging.getLogger("devselect")


@asynccontextmanager
async def _checkpoint_connection(checkpointer) -> AsyncIterator:
    connection_source = getattr(checkpointer, "conn", None)
    if connection_source is None:
        raise RuntimeError("Checkpoint connection is unavailable")

    connection_factory = getattr(connection_source, "connection", None)
    if callable(connection_factory):
        async with connection_factory() as connection:
            yield connection
        return

    yield connection_source


async def purge_checkpoint_thread(
    checkpointer,
    thread_id: str | None,
    *,
    reason: str,
) -> bool:
    if not thread_id:
        return False

    delete_thread = getattr(checkpointer, "adelete_thread", None)
    if delete_thread is None:
        raise RuntimeError("Checkpoint thread deletion is unavailable")

    await delete_thread(str(thread_id))
    logger.info(
        "Checkpoint thread purged : thread=%s reason=%s",
        safe_log_id(thread_id, "thread"),
        reason,
    )
    return True


async def purge_graph_thread(graph, thread_id: str | None, *, reason: str) -> bool:
    checkpointer = getattr(graph, "checkpointer", None)
    if checkpointer is None:
        raise RuntimeError("Graph checkpointer is unavailable")
    return await purge_checkpoint_thread(checkpointer, thread_id, reason=reason)


async def find_stale_checkpoint_threads(
    checkpointer,
    *,
    older_than: datetime,
    limit: int,
) -> list[str]:
    query = """
        SELECT thread_id
        FROM public.checkpoints
        GROUP BY thread_id
        HAVING MAX((checkpoint ->> 'ts')::timestamptz) < %s
        ORDER BY MAX((checkpoint ->> 'ts')::timestamptz) ASC
        LIMIT %s
    """

    async with _checkpoint_connection(checkpointer) as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(query, (older_than, max(1, int(limit))))
            rows = await cursor.fetchall()

    thread_ids = []
    for row in rows:
        thread_id = row.get("thread_id") if isinstance(row, dict) else row[0]
        if thread_id:
            thread_ids.append(str(thread_id))
    return thread_ids


async def cleanup_stale_checkpoint_threads(
    checkpointer,
    *,
    ttl_hours: int,
    batch_size: int,
) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max(1, ttl_hours))
    thread_ids = await find_stale_checkpoint_threads(
        checkpointer,
        older_than=cutoff,
        limit=batch_size,
    )

    purged = 0
    for thread_id in thread_ids:
        if await purge_checkpoint_thread(
            checkpointer,
            thread_id,
            reason="ttl_expired",
        ):
            purged += 1

    if purged:
        logger.info("Checkpoint TTL cleanup completed : purged_threads=%s", purged)
    return purged


async def checkpoint_cleanup_loop(
    checkpointer,
    *,
    ttl_hours: int,
    interval_seconds: int,
    batch_size: int,
) -> None:
    while True:
        try:
            await cleanup_stale_checkpoint_threads(
                checkpointer,
                ttl_hours=ttl_hours,
                batch_size=batch_size,
            )
        except asyncio.CancelledError:
            raise
        except Exception as error:
            logger.warning(
                "Checkpoint TTL cleanup failed : error_type=%s",
                type(error).__name__,
            )

        await asyncio.sleep(max(60, interval_seconds))
