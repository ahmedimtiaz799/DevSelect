import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass
from uuid import uuid4

import httpx

from app.config import settings


logger = logging.getLogger("devselect")
_http_client = httpx.AsyncClient(timeout=5.0)
_memory_lock = asyncio.Lock()
_memory_locks: dict[str, tuple[str, float]] = {}

EVALUATION_ALREADY_IN_PROGRESS = "EVALUATION_ALREADY_IN_PROGRESS"
EVALUATION_LOCK_UNAVAILABLE = "EVALUATION_LOCK_UNAVAILABLE"

_RELEASE_LOCK_LUA = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("DEL", KEYS[1])
end
return 0
"""

_CLAIM_STREAM_LOCK_LUA = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
    redis.call("SET", KEYS[1], ARGV[2], "EX", ARGV[3])
    return 1
end
return 0
"""


@dataclass(frozen=True)
class EvaluationLockDecision:
    allowed: bool
    token: str | None = None
    code: str | None = None
    error: str | None = None
    retry_after_seconds: int | None = None


def _lock_key(chat_id: str) -> str:
    digest = hashlib.sha256(str(chat_id).encode("utf-8")).hexdigest()
    return f"evaluation_lock:chat:{digest}"


def _redis_configured() -> bool:
    url = settings.UPSTASH_REDIS_REST_URL.strip()
    token = settings.UPSTASH_REDIS_REST_TOKEN.strip()
    return bool(
        url.startswith("http")
        and token
        and "your-redis-instance" not in url
        and "your_upstash_redis_token_here" not in token
    )


async def acquire_evaluation_lock(chat_id: str) -> EvaluationLockDecision:
    token = str(uuid4())
    if _redis_configured():
        try:
            response = await _http_client.post(
                settings.UPSTASH_REDIS_REST_URL.rstrip("/"),
                json=[
                    "SET",
                    _lock_key(chat_id),
                    token,
                    "NX",
                    "EX",
                    str(settings.EVALUATION_LOCK_TTL_SECONDS),
                ],
                headers={
                    "Authorization": f"Bearer {settings.UPSTASH_REDIS_REST_TOKEN}",
                    "Content-Type": "application/json",
                },
            )
            if response.status_code != 200:
                raise RuntimeError(f"status={response.status_code}")
            if response.json().get("result") == "OK":
                return EvaluationLockDecision(allowed=True, token=token)
            return _duplicate_decision()
        except Exception as error:
            logger.warning(
                "Evaluation lock Redis unavailable : error_type=%s",
                type(error).__name__,
            )
            if settings.is_production:
                return _unavailable_decision()

    if settings.is_production:
        return _unavailable_decision()
    return await _acquire_memory_lock(chat_id, token)


async def claim_evaluation_stream(chat_id: str, admission_token: str | None) -> str | None:
    if not admission_token:
        return None
    stream_token = str(uuid4())
    if _redis_configured():
        try:
            response = await _http_client.post(
                settings.UPSTASH_REDIS_REST_URL.rstrip("/"),
                json=[
                    "EVAL",
                    _CLAIM_STREAM_LOCK_LUA,
                    1,
                    _lock_key(chat_id),
                    admission_token,
                    stream_token,
                    str(settings.EVALUATION_LOCK_TTL_SECONDS),
                ],
                headers={
                    "Authorization": f"Bearer {settings.UPSTASH_REDIS_REST_TOKEN}",
                    "Content-Type": "application/json",
                },
            )
            if response.status_code == 200 and int(response.json().get("result") or 0) == 1:
                return stream_token
            return None
        except Exception as error:
            logger.warning(
                "Evaluation stream lock claim failed : error_type=%s",
                type(error).__name__,
            )
            return None
    return await _claim_memory_stream_lock(chat_id, admission_token, stream_token)


async def release_evaluation_lock(chat_id: str, token: str | None) -> bool:
    if not token:
        return False
    if _redis_configured():
        try:
            response = await _http_client.post(
                settings.UPSTASH_REDIS_REST_URL.rstrip("/"),
                json=["EVAL", _RELEASE_LOCK_LUA, 1, _lock_key(chat_id), token],
                headers={
                    "Authorization": f"Bearer {settings.UPSTASH_REDIS_REST_TOKEN}",
                    "Content-Type": "application/json",
                },
            )
            return response.status_code == 200 and int(response.json().get("result") or 0) == 1
        except Exception as error:
            logger.warning(
                "Evaluation lock release failed; TTL will expire it : error_type=%s",
                type(error).__name__,
            )
            return False
    return await _release_memory_lock(chat_id, token)


async def _acquire_memory_lock(chat_id: str, token: str) -> EvaluationLockDecision:
    key = _lock_key(chat_id)
    now = time.monotonic()
    async with _memory_lock:
        existing = _memory_locks.get(key)
        if existing and existing[1] > now:
            return _duplicate_decision()
        _memory_locks[key] = (token, now + settings.EVALUATION_LOCK_TTL_SECONDS)
    return EvaluationLockDecision(allowed=True, token=token)


async def _claim_memory_stream_lock(
    chat_id: str,
    admission_token: str,
    stream_token: str,
) -> str | None:
    key = _lock_key(chat_id)
    async with _memory_lock:
        existing = _memory_locks.get(key)
        if not existing or existing[0] != admission_token:
            return None
        _memory_locks[key] = (
            stream_token,
            time.monotonic() + settings.EVALUATION_LOCK_TTL_SECONDS,
        )
        return stream_token


async def _release_memory_lock(chat_id: str, token: str) -> bool:
    key = _lock_key(chat_id)
    async with _memory_lock:
        existing = _memory_locks.get(key)
        if not existing or existing[0] != token:
            return False
        del _memory_locks[key]
        return True


def _duplicate_decision() -> EvaluationLockDecision:
    return EvaluationLockDecision(
        allowed=False,
        code=EVALUATION_ALREADY_IN_PROGRESS,
        error="An evaluation is already in progress for this chat.",
        retry_after_seconds=settings.EVALUATION_LOCK_RETRY_AFTER_SECONDS,
    )


def _unavailable_decision() -> EvaluationLockDecision:
    return EvaluationLockDecision(
        allowed=False,
        code=EVALUATION_LOCK_UNAVAILABLE,
        error="Evaluation admission is temporarily unavailable. Please try again later.",
    )
