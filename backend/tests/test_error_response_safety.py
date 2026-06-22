import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from starlette.requests import Request

from app.agents.agent1_cv_extraction import agent1_cv_extraction
from app.middleware.error_handler import handle_http_exception
from app.routers.evaluation import evaluation_stream_generator, upload_cv
from app.utils.budget_limits import BudgetDecision
from app.utils.evaluation_lock import EvaluationLockDecision
from app.utils.json_parser import parse_llm_json
from app.utils.public_errors import public_error_payload


SENSITIVE_SENTINELS = (
    "raw_cv_text=CANDIDATE_PRIVATE_CV_TEXT",
    "system prompt: INTERNAL_RECRUITER_PROMPT",
    "prompt=PRIVATE_MODEL_INSTRUCTION",
    "SELECT * FROM auth.users WHERE password = 'private'",
    "DROP TABLE public.messages",
    "Bearer eyJFAKEHEADER.FAKEPAYLOAD.FAKESIGNATURE",
    "https://private.example.test/provider?token=private",
    "Traceback (most recent call last): RuntimeError",
    r"C:\private\resume\candidate.pdf",
    "provider output=PRIVATE_MODEL_RESPONSE",
    "thread_id=private-evaluation-thread",
)


def _request(path="/api/chat/chat-1/upload"):
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 50000),
            "server": ("testserver", 80),
        }
    )


class PublicErrorMapperTests(unittest.IsolatedAsyncioTestCase):
    def assert_no_sensitive_text(self, value):
        serialized = json.dumps(value)
        for sentinel in SENSITIVE_SENTINELS:
            self.assertNotIn(sentinel, serialized)

    def test_unknown_error_codes_use_stable_public_fallback(self):
        for sentinel in SENSITIVE_SENTINELS:
            payload = public_error_payload(
                sentinel,
                default_code="EVALUATION_PIPELINE_ERROR",
            )
            self.assertEqual(payload["code"], "EVALUATION_PIPELINE_ERROR")
            self.assertEqual(payload["error"], "Evaluation failed. Please try again.")
            self.assert_no_sensitive_text(payload)

    async def test_http_exception_details_never_forward_sensitive_text(self):
        for status_code in (400, 500):
            for sentinel in SENSITIVE_SENTINELS:
                response = await handle_http_exception(
                    _request(),
                    HTTPException(status_code=status_code, detail=sentinel),
                )
                self.assertEqual(response.status_code, status_code)
                self.assert_no_sensitive_text(json.loads(response.body))

    def test_json_parser_exception_does_not_include_model_output(self):
        sentinel = SENSITIVE_SENTINELS[-2]
        with self.assertRaises(ValueError) as caught:
            parse_llm_json(f"not-json {sentinel}")
        self.assertNotIn(sentinel, str(caught.exception))


class EvaluationResponseBoundaryTests(unittest.IsolatedAsyncioTestCase):
    def assert_no_sensitive_text(self, value):
        serialized = value if isinstance(value, str) else json.dumps(value)
        for sentinel in SENSITIVE_SENTINELS:
            self.assertNotIn(sentinel, serialized)

    async def test_agent1_value_error_becomes_stable_public_state(self):
        raw_text = (
            "Professional experience skills education projects certifications "
            * 30
        )
        state = {
            "thread_id": "thread-1",
            "pdf_temp_path": None,
            "pdf_bytes": None,
            "pdf_preview_text": raw_text,
            "error": None,
        }
        with (
            patch(
                "app.agents.agent1_cv_extraction._preview_fallback_text",
                return_value=raw_text,
            ),
            patch(
                "app.agents.agent1_cv_extraction._extract_with_gemini",
                new=AsyncMock(side_effect=ValueError(SENSITIVE_SENTINELS[0])),
            ),
        ):
            result = await agent1_cv_extraction(state)

        self.assertEqual(result["error_code"], "CV_EXTRACTION_INVALID")
        self.assert_no_sensitive_text(result["error"])

    async def test_upload_does_not_forward_raw_graph_error(self):
        graph = SimpleNamespace(
            ainvoke=AsyncMock(
                return_value={
                    "error": " ".join(SENSITIVE_SENTINELS),
                    "error_code": "UNKNOWN_INTERNAL_ERROR",
                }
            )
        )
        request = SimpleNamespace(
            app=SimpleNamespace(state=SimpleNamespace(graph=graph)),
        )
        with (
            patch(
                "app.routers.evaluation._get_owned_chat",
                new=AsyncMock(
                    return_value={
                        "id": "chat-1",
                        "user_id": "user-1",
                        "thread_id": None,
                    }
                ),
            ),
            patch(
                "app.routers.evaluation._read_validated_pdf_upload",
                new=AsyncMock(return_value=(b"%PDF-test", "CV preview")),
            ),
            patch(
                "app.routers.evaluation._graph_thread_has_state",
                new=AsyncMock(return_value=False),
            ),
            patch(
                "app.routers.evaluation.acquire_evaluation_lock",
                new=AsyncMock(
                    return_value=EvaluationLockDecision(
                        allowed=True,
                        token="lock-token",
                    )
                ),
            ),
            patch(
                "app.routers.evaluation.record_evaluation_usage",
                new=AsyncMock(
                    return_value=BudgetDecision(
                        allowed=True,
                        storage="test",
                        scope="evaluation",
                    )
                ),
            ),
            patch("app.routers.evaluation._save_chat_thread_id", new=AsyncMock()),
            patch("app.routers.evaluation._write_temp_pdf", return_value="temp.pdf"),
            patch("app.routers.evaluation._delete_temp_file"),
            patch("app.routers.evaluation.release_evaluation_lock", new=AsyncMock()),
            patch("app.routers.evaluation._set_graph_evaluation_status", new=AsyncMock()),
            patch("app.routers.evaluation.purge_graph_thread", new=AsyncMock()),
        ):
            response = await upload_cv(
                "chat-1",
                request,
                SimpleNamespace(),
                None,
                None,
                None,
                "user-1",
            )

        payload = json.loads(response.body)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(payload["code"], "EVALUATION_UPLOAD_FAILED")
        self.assert_no_sensitive_text(payload)

    async def test_sse_does_not_forward_raw_checkpoint_error(self):
        async def state_stream(*args, **kwargs):
            yield {
                "error": " ".join(SENSITIVE_SENTINELS),
                "error_code": "UNKNOWN_INTERNAL_ERROR",
            }

        graph = SimpleNamespace(astream=state_stream)
        request = SimpleNamespace(is_disconnected=AsyncMock(return_value=False))
        with (
            patch("app.routers.evaluation._set_graph_evaluation_status", new=AsyncMock()),
            patch("app.routers.evaluation._release_stream_thread", new=AsyncMock()),
            patch("app.routers.evaluation.purge_graph_thread", new=AsyncMock()),
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
                    "stream-lock-token",
                )
            ]

        output = "".join(events)
        self.assertIn("EVALUATION_PIPELINE_ERROR", output)
        self.assert_no_sensitive_text(output)


if __name__ == "__main__":
    unittest.main()
