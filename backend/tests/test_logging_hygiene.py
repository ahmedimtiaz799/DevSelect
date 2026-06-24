import json
import logging
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from starlette.requests import Request
from uvicorn.logging import AccessFormatter

os.environ["SENTRY_DSN"] = ""
os.environ["APP_ENV"] = "development"

from app.agents.agent2_github_analysis import _log_structured_output_failure
from app.middleware.error_handler import handle_unhandled_exception, init_sentry
from app.routers.evaluation import _log_evaluation_marker
from app.utils.logging_hygiene import (
    configure_logging_hygiene,
    redact_log_text,
    safe_log_id,
    scrub_sentry_event,
)


CV_SENTINEL = "SENTINEL_CV_PRIVATE_NAME_AND_ADDRESS"
PROMPT_SENTINEL = "SENTINEL_PRIVATE_PROMPT_TEXT"
PROVIDER_SENTINEL = "SENTINEL_PROVIDER_OUTPUT_TEXT"
FAKE_JWT = "eyJhbGciOiJFUzI1NiJ9.eyJzdWIiOiJzZW50aW5lbCJ9.signaturevalue"
FAKE_KEY = "gsk_SENTINEL_PROVIDER_KEY_123456"
FAKE_URL = "https://private.example.test/candidate?token=sentinel"
FAKE_UUID = "123e4567-e89b-42d3-a456-426614174000"
FAKE_IP = "203.0.113.42"


class LoggingHygieneUnitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        configure_logging_hygiene()

    def test_identifier_is_hashed_without_exposing_source_value(self):
        safe_value = safe_log_id(FAKE_UUID, "chat")

        self.assertTrue(safe_value.startswith("chat:"))
        self.assertNotIn(FAKE_UUID, safe_value)
        self.assertEqual(safe_value, safe_log_id(FAKE_UUID, "chat"))

    def test_log_filter_redacts_tokens_urls_uuid_and_ip(self):
        logger = logging.getLogger("devselect")

        with self.assertLogs(logger, level="WARNING") as captured:
            logger.warning(
                "token=%s key=%s url=%s chat=%s ip=%s",
                FAKE_JWT,
                FAKE_KEY,
                FAKE_URL,
                FAKE_UUID,
                FAKE_IP,
            )

        output = "\n".join(captured.output)
        for sentinel in (FAKE_JWT, FAKE_KEY, FAKE_URL, FAKE_UUID, FAKE_IP):
            self.assertNotIn(sentinel, output)
        self.assertIn("id:", output)
        self.assertIn("ip:", output)

    def test_access_log_filter_removes_resume_query_and_identifiers(self):
        logger = logging.getLogger("uvicorn.access")
        request_target = (
            f"/api/chat/{FAKE_UUID}/stream?thread_id={FAKE_UUID}"
            f"&resume_payload={PROMPT_SENTINEL}"
        )

        with self.assertLogs(logger, level="INFO") as captured:
            logger.info('GET %s from %s', request_target, FAKE_IP)

        output = "\n".join(captured.output)
        self.assertNotIn(PROMPT_SENTINEL, output)
        self.assertNotIn(FAKE_UUID, output)
        self.assertNotIn(FAKE_IP, output)
        self.assertIn("?[Filtered]", output)

    def test_access_log_filter_preserves_uvicorn_formatter_arguments(self):
        logger = logging.getLogger("uvicorn.access")
        request_target = (
            f"/api/chat/{FAKE_UUID}/stream?thread_id={FAKE_UUID}"
            f"&resume_payload={PROMPT_SENTINEL}"
        )
        record = logging.LogRecord(
            "uvicorn.access",
            logging.INFO,
            __file__,
            1,
            '%s - "%s %s HTTP/%s" %d',
            (FAKE_IP, "GET", request_target, "1.1", 200),
            None,
        )

        for log_filter in logger.filters:
            log_filter.filter(record)

        self.assertEqual(len(record.args), 5)
        output = AccessFormatter(
            '%(client_addr)s - "%(request_line)s" %(status_code)s',
            use_colors=False,
        ).format(record)

        self.assertNotIn(PROMPT_SENTINEL, output)
        self.assertNotIn(FAKE_UUID, output)
        self.assertNotIn(FAKE_IP, output)
        self.assertIn("?[Filtered]", output)
        self.assertIn("200 OK", output)

    def test_redact_log_text_never_returns_secret_material(self):
        output = redact_log_text(
            f"Authorization: Bearer {FAKE_JWT} service_role={FAKE_KEY} {FAKE_URL}"
        )

        self.assertNotIn(FAKE_JWT, output)
        self.assertNotIn(FAKE_KEY, output)
        self.assertNotIn(FAKE_URL, output)

    def test_sentry_event_scrubs_request_breadcrumbs_locals_and_sensitive_payloads(self):
        event = {
            "request": {
                "url": FAKE_URL,
                "headers": {"Authorization": f"Bearer {FAKE_JWT}"},
                "query_string": f"resume_payload={PROMPT_SENTINEL}",
                "data": {"cv_text": CV_SENTINEL},
                "cookies": {"session": FAKE_JWT},
                "env": {"REMOTE_ADDR": FAKE_IP},
            },
            "user": {"id": FAKE_UUID, "ip_address": FAKE_IP},
            "breadcrumbs": {
                "values": [
                    {
                        "message": PROMPT_SENTINEL,
                        "data": {"provider_response": PROVIDER_SENTINEL},
                    }
                ]
            },
            "exception": {
                "values": [
                    {
                        "type": "RuntimeError",
                        "value": PROVIDER_SENTINEL,
                        "stacktrace": {
                            "frames": [{"vars": {"raw_cv_text": CV_SENTINEL}}]
                        },
                    }
                ]
            },
            "extra": {
                "raw_cv_text": CV_SENTINEL,
                "prompt": PROMPT_SENTINEL,
                "provider_response": PROVIDER_SENTINEL,
                "safe_count": 12,
            },
            "contexts": {"auth": {"access_token": FAKE_JWT}},
            "tags": {"database_url": FAKE_URL},
            "message": f"failure {CV_SENTINEL} {PROMPT_SENTINEL} {PROVIDER_SENTINEL} {FAKE_JWT} {FAKE_URL}",
        }

        scrubbed = scrub_sentry_event(event, {})
        serialized = json.dumps(scrubbed, sort_keys=True)

        for sentinel in (
            CV_SENTINEL,
            PROMPT_SENTINEL,
            PROVIDER_SENTINEL,
            FAKE_JWT,
            FAKE_KEY,
            FAKE_URL,
            FAKE_UUID,
            FAKE_IP,
        ):
            self.assertNotIn(sentinel, serialized)
        self.assertEqual(scrubbed["extra"]["safe_count"], 12)
        self.assertEqual(scrubbed["exception"]["values"][0]["value"], "RuntimeError")

    def test_provider_output_failure_log_contains_metrics_not_output(self):
        raw_response = SimpleNamespace(
            content=PROVIDER_SENTINEL,
            response_metadata={"finish_reason": "STOP"},
            usage_metadata=None,
        )
        logger = logging.getLogger("devselect")

        with self.assertLogs(logger, level="ERROR") as captured:
            _log_structured_output_failure(raw_response, ValueError("invalid"), FAKE_UUID)

        output = "\n".join(captured.output)
        self.assertNotIn(PROVIDER_SENTINEL, output)
        self.assertNotIn(FAKE_UUID, output)
        self.assertIn(f"response_chars={len(PROVIDER_SENTINEL)}", output)
        self.assertIn("error_type=ValueError", output)

    def test_sentry_initialization_uses_scrubber(self):
        with patch("app.middleware.error_handler.settings.SENTRY_DSN", "https://example.invalid/1"):
            with patch("app.middleware.error_handler.sentry_sdk.init") as sentry_init:
                init_sentry()

        self.assertIs(sentry_init.call_args.kwargs["before_send"], scrub_sentry_event)
        self.assertFalse(sentry_init.call_args.kwargs["send_default_pii"])

    def test_frontend_console_diagnostics_are_development_only_and_message_free(self):
        frontend_root = Path(__file__).resolve().parents[2] / "frontend/src"
        sources = [
            (frontend_root / "hooks/useChat.js").read_text(encoding="utf-8"),
            (frontend_root / "lib/streaming.js").read_text(encoding="utf-8"),
            (frontend_root / "components/auth/SocialButton.jsx").read_text(encoding="utf-8"),
        ]
        combined = "\n".join(sources)

        self.assertNotRegex(
            combined,
            r"console\.(?:warn|error|info|log)\([^;]{0,300}error\??\.message",
        )
        for source in sources:
            self.assertIn("import.meta.env.DEV", source)

    def test_sensitive_content_log_contracts_do_not_include_excerpts(self):
        backend_root = Path(__file__).resolve().parents[1]
        sources = {
            "agent1": (backend_root / "app/agents/agent1_cv_extraction.py").read_text(encoding="utf-8"),
            "agent2": (backend_root / "app/agents/agent2_github_analysis.py").read_text(encoding="utf-8"),
            "follow_up": (backend_root / "app/agents/follow_up.py").read_text(encoding="utf-8"),
            "evaluation": (backend_root / "app/routers/evaluation.py").read_text(encoding="utf-8"),
        }

        combined = "\n".join(sources.values())
        for forbidden in ("first_100", "first_200", "last_200", "meta={meta}"):
            self.assertNotIn(forbidden, combined)
        self.assertNotIn("_safe_cv_preview", sources["agent1"])

    def test_evaluation_flow_markers_use_safe_diagnostics_only(self):
        logger = logging.getLogger("devselect")

        with self.assertLogs(logger, level="INFO") as captured:
            _log_evaluation_marker(
                "upload:start",
                chat_id=FAKE_UUID,
                user_id=FAKE_UUID,
                thread_id=FAKE_UUID,
                file_ext=CV_SENTINEL,
                file_size_bytes=12345,
                error_type=f"RuntimeError {FAKE_JWT}",
                error_code=FAKE_JWT,
            )

        output = "\n".join(captured.output)
        self.assertIn("evaluation_flow", output)
        self.assertIn("marker=upload:start", output)
        self.assertIn("chat=chat:", output)
        self.assertIn("user=user:", output)
        self.assertIn("thread=thread:", output)
        self.assertIn("file_size_bytes=12345", output)
        self.assertIn("file_ext=unknown", output)
        self.assertIn("error_type=Exception", output)
        self.assertIn("error_code=UNKNOWN", output)
        for sentinel in (FAKE_UUID, FAKE_JWT, CV_SENTINEL, FAKE_IP):
            self.assertNotIn(sentinel, output)


class ErrorHandlerLoggingTests(unittest.IsolatedAsyncioTestCase):
    async def test_unhandled_exception_log_excludes_exception_message(self):
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/chat/test/upload",
            "headers": [],
            "query_string": b"",
            "server": ("testserver", 80),
            "client": ("127.0.0.1", 1234),
            "scheme": "http",
        }
        request = Request(scope)
        logger = logging.getLogger("devselect")
        exception = RuntimeError(
            f"{CV_SENTINEL} {PROMPT_SENTINEL} {PROVIDER_SENTINEL} {FAKE_JWT}"
        )

        with patch("app.middleware.error_handler.sentry_sdk.capture_exception") as capture:
            with self.assertLogs(logger, level="ERROR") as captured:
                response = await handle_unhandled_exception(request, exception)

        output = "\n".join(captured.output)
        for sentinel in (CV_SENTINEL, PROMPT_SENTINEL, PROVIDER_SENTINEL, FAKE_JWT):
            self.assertNotIn(sentinel, output)
        self.assertIn("error_type=RuntimeError", output)
        self.assertEqual(response.status_code, 500)
        capture.assert_called_once_with(exception)


if __name__ == "__main__":
    unittest.main()
