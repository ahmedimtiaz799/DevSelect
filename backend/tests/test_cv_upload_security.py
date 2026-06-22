import unittest
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from pypdf import PdfWriter
from starlette.datastructures import Headers, UploadFile

from app.config import settings
from app.routers.evaluation import (
    MAX_CV_UPLOAD_BYTES,
    UploadSecurityError,
    _delete_temp_file,
    _read_validated_pdf_upload,
    _run_cv_likeness_precheck,
    _safe_upload_name,
    _write_temp_pdf,
    delete_chat_with_checkpoint_cleanup,
    evaluation_stream_generator,
)
from app.utils.checkpoint_retention import (
    cleanup_stale_checkpoint_threads,
    purge_checkpoint_thread,
)


def _pdf_bytes(*, pages=1, encrypted=False):
    output = BytesIO()
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=612, height=792)
    if encrypted:
        writer.encrypt("test-password")
    writer.write(output)
    return output.getvalue()


def _upload(content, *, filename="candidate.pdf", content_type="application/pdf", size=None):
    return UploadFile(
        BytesIO(content),
        size=len(content) if size is None else size,
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


class CvUploadValidationTests(unittest.IsolatedAsyncioTestCase):
    async def assert_upload_error(self, upload, code):
        with self.assertRaises(UploadSecurityError) as caught:
            await _read_validated_pdf_upload(upload)
        self.assertEqual(caught.exception.code, code)
        self.assertTrue(upload.file.closed)

    async def test_empty_file_is_rejected_and_closed(self):
        await self.assert_upload_error(_upload(b""), "INVALID_PDF")

    async def test_oversized_file_metadata_is_rejected_and_closed(self):
        upload = _upload(b"%PDF-1.7", size=MAX_CV_UPLOAD_BYTES + 1)
        await self.assert_upload_error(upload, "FILE_TOO_LARGE")

    async def test_oversized_stream_is_bounded_when_size_is_unknown(self):
        upload = _upload(b"%PDF-" + b"x" * 64, size=None)
        upload.size = None
        with patch("app.routers.evaluation.MAX_CV_UPLOAD_BYTES", 32):
            await self.assert_upload_error(upload, "FILE_TOO_LARGE")

    async def test_wrong_mime_is_rejected_and_closed(self):
        await self.assert_upload_error(
            _upload(_pdf_bytes(), content_type="application/octet-stream"),
            "INVALID_FILE_TYPE",
        )

    async def test_non_pdf_extension_is_rejected(self):
        await self.assert_upload_error(
            _upload(_pdf_bytes(), filename="candidate.txt"),
            "INVALID_FILE_TYPE",
        )

    async def test_renamed_non_pdf_is_rejected(self):
        await self.assert_upload_error(
            _upload(b"This is not a PDF", filename="candidate.pdf"),
            "INVALID_PDF",
        )

    async def test_malformed_pdf_with_header_is_rejected(self):
        await self.assert_upload_error(
            _upload(b"%PDF-1.7\nmalformed"),
            "INVALID_PDF",
        )

    async def test_encrypted_pdf_is_rejected(self):
        await self.assert_upload_error(
            _upload(_pdf_bytes(encrypted=True)),
            "ENCRYPTED_PDF",
        )

    async def test_page_limit_is_enforced(self):
        upload = _upload(_pdf_bytes(pages=2))
        with patch.object(settings, "MAX_CV_PDF_PAGES", 1):
            await self.assert_upload_error(upload, "PDF_TOO_LONG")

    async def test_traversal_filename_is_sanitized_and_never_used_as_path(self):
        safe_name = _safe_upload_name("../../private/candidate.pdf")
        self.assertNotIn("/", safe_name)
        self.assertNotIn("\\", safe_name)
        self.assertTrue(safe_name.endswith("candidate.pdf"))

        upload = _upload(_pdf_bytes(), filename="../../private/candidate.pdf")
        with patch("app.routers.evaluation._run_cv_likeness_precheck", return_value="CV preview"):
            pdf_bytes, preview = await _read_validated_pdf_upload(upload)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))
        self.assertEqual(preview, "CV preview")
        self.assertTrue(upload.file.closed)

    def test_preview_text_is_capped_before_state(self):
        preview = "skills experience education " * 2000
        with patch("app.routers.evaluation._extract_pdf_preview_text", return_value=preview):
            capped = _run_cv_likeness_precheck(b"unused")
        self.assertLessEqual(len(capped), settings.CV_PREVIEW_MAX_CHARS)

    def test_temp_pdf_cleanup_removes_file(self):
        temp_path = _write_temp_pdf(_pdf_bytes())
        self.assertTrue(Path(temp_path).exists())
        _delete_temp_file(temp_path)
        self.assertFalse(Path(temp_path).exists())


class _FakeCheckpointQuery:
    def __init__(self):
        self.deleted = False
        self.filters = {}

    def delete(self):
        self.deleted = True
        return self

    def eq(self, column, value):
        self.filters[column] = value
        return self

    async def execute(self):
        return SimpleNamespace(data=[])


class _FakeSupabase:
    def __init__(self):
        self.query = _FakeCheckpointQuery()

    def table(self, table_name):
        if table_name != "chats":
            raise AssertionError(f"Unexpected table: {table_name}")
        return self.query


class CheckpointRetentionTests(unittest.IsolatedAsyncioTestCase):
    async def test_checkpoint_purge_deletes_entire_thread(self):
        checkpointer = SimpleNamespace(adelete_thread=AsyncMock())
        purged = await purge_checkpoint_thread(
            checkpointer,
            "thread-1",
            reason="test",
        )
        self.assertTrue(purged)
        checkpointer.adelete_thread.assert_awaited_once_with("thread-1")

    async def test_ttl_cleanup_purges_stale_threads(self):
        checkpointer = SimpleNamespace(adelete_thread=AsyncMock())
        with patch(
            "app.utils.checkpoint_retention.find_stale_checkpoint_threads",
            new=AsyncMock(return_value=["stale-1", "stale-2"]),
        ):
            purged = await cleanup_stale_checkpoint_threads(
                checkpointer,
                ttl_hours=24,
                batch_size=10,
            )
        self.assertEqual(purged, 2)
        self.assertEqual(checkpointer.adelete_thread.await_count, 2)

    async def test_chat_delete_purges_checkpoint_before_deleting_row(self):
        graph = SimpleNamespace(checkpointer=SimpleNamespace(adelete_thread=AsyncMock()))
        request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(graph=graph)))
        supabase = _FakeSupabase()

        with (
            patch(
                "app.routers.evaluation._get_owned_chat",
                new=AsyncMock(return_value={"id": "chat-1", "user_id": "user-1", "thread_id": "thread-1"}),
            ),
            patch("app.routers.evaluation.get_supabase", new=AsyncMock(return_value=supabase)),
            patch("app.routers.evaluation.clear_evaluation_follow_up_usage", new=AsyncMock()),
        ):
            response = await delete_chat_with_checkpoint_cleanup(
                "chat-1",
                request,
                "user-1",
            )

        self.assertEqual(response.status_code, 204)
        graph.checkpointer.adelete_thread.assert_awaited_once_with("thread-1")
        self.assertTrue(supabase.query.deleted)
        self.assertEqual(supabase.query.filters, {"id": "chat-1", "user_id": "user-1"})

    async def test_completed_stream_purges_checkpoint_after_done(self):
        request = SimpleNamespace(is_disconnected=AsyncMock(return_value=False))
        graph = SimpleNamespace(
            checkpointer=SimpleNamespace(adelete_thread=AsyncMock()),
            astream=lambda *args, **kwargs: _state_stream({"report": "OK"}),
        )

        with (
            patch("app.routers.evaluation._set_graph_evaluation_status", new=AsyncMock()),
            patch("app.routers.evaluation._release_stream_thread", new=AsyncMock()),
            patch("app.routers.evaluation.release_evaluation_lock", new=AsyncMock()),
        ):
            events = [
                event
                async for event in evaluation_stream_generator(
                    request,
                    "chat-1",
                    "thread-1",
                    {"scenario": "SKIPPED"},
                    {"candidate_name": "Candidate", "role": "Role"},
                    graph,
                    "lock-token",
                )
            ]

        self.assertTrue(any("event: done" in event for event in events))
        graph.checkpointer.adelete_thread.assert_awaited_once_with("thread-1")


async def _state_stream(state):
    yield state


if __name__ == "__main__":
    unittest.main()
