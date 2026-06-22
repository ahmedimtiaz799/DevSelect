import os
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from pydantic import ValidationError

os.environ["SENTRY_DSN"] = ""
os.environ["APP_ENV"] = "development"

from app.config import Settings
from app.main import create_app


STRONG_ADMIN_SECRET = "gate3-test-admin-secret-value-1234567890"


def _settings(**overrides) -> Settings:
    values = {
        "ADMIN_ROUTES_ENABLED": False,
        "API_DOCS_ENABLED": None,
        "SUPABASE_URL": "https://test-project.supabase.co",
        "SUPABASE_ANON_KEY": "test-anon-key",
        "SUPABASE_SERVICE_ROLE_KEY": "test-service-role-key",
        "SUPABASE_JWT_SECRET": "test-jwt-secret",
        "DATABASE_URL": "postgresql://test",
        "GEMINI_API_KEY": "test-gemini-key",
        "LLAMAPARSE_API_KEY": "test-llamaparse-key",
        "HUGGINGFACE_API_TOKEN": "test-huggingface-token",
        "GITHUB_TOKEN": "test-github-token",
        "UPSTASH_REDIS_REST_URL": "",
        "UPSTASH_REDIS_REST_TOKEN": "",
        "ADMIN_SECRET": "",
        "FRONTEND_URL": "http://localhost:5173",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def _client(app_settings: Settings) -> TestClient:
    app = create_app(
        app_settings,
        lifespan_handler=None,
        initialize_observability=False,
    )
    return TestClient(app)


class HealthRouteSecurityTests(unittest.TestCase):
    def test_health_returns_minimal_stable_output(self):
        with _client(_settings()) as client:
            response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "service": "DevSelect API"})
        self.assertNotIn("environment", response.json())
        self.assertNotIn("FRONTEND_URL", response.text)


class AdminRouteSecurityTests(unittest.TestCase):
    def test_admin_routes_are_not_mounted_when_disabled(self):
        with _client(_settings(ADMIN_ROUTES_ENABLED=False)) as client:
            response = client.get("/admin/reliability/status")

        self.assertEqual(response.status_code, 404)

    def test_missing_admin_secret_is_rejected_safely(self):
        settings = _settings(ADMIN_ROUTES_ENABLED=True, ADMIN_SECRET=STRONG_ADMIN_SECRET)

        with _client(settings) as client:
            response = client.get("/admin/reliability/status")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), {"error": "Invalid admin secret."})

    def test_wrong_admin_secret_is_rejected_safely(self):
        settings = _settings(ADMIN_ROUTES_ENABLED=True, ADMIN_SECRET=STRONG_ADMIN_SECRET)

        with _client(settings) as client:
            response = client.get(
                "/admin/reliability/status",
                headers={"X-Admin-Secret": "wrong-admin-secret"},
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), {"error": "Invalid admin secret."})

    def test_correct_admin_secret_allows_reliability_status(self):
        settings = _settings(ADMIN_ROUTES_ENABLED=True, ADMIN_SECRET=STRONG_ADMIN_SECRET)

        with patch("app.middleware.circuit_breaker._redis_configured", return_value=False):
            with _client(settings) as client:
                response = client.get(
                    "/admin/reliability/status",
                    headers={"X-Admin-Secret": STRONG_ADMIN_SECRET},
                )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["redis_configured"])

    def test_correct_admin_secret_allows_circuit_control(self):
        settings = _settings(ADMIN_ROUTES_ENABLED=True, ADMIN_SECRET=STRONG_ADMIN_SECRET)

        with patch("app.middleware.circuit_breaker._set_flag", new=AsyncMock()) as set_flag:
            with _client(settings) as client:
                response = client.post(
                    "/admin/circuit/open",
                    headers={"X-Admin-Secret": STRONG_ADMIN_SECRET},
                )

        self.assertEqual(response.status_code, 200)
        set_flag.assert_awaited_once_with("true")


class Gate3ConfigurationTests(unittest.TestCase):
    def test_production_uses_safe_defaults(self):
        settings = _settings(
            APP_ENV="production",
            FRONTEND_URL="https://app.example.test",
        )

        self.assertTrue(settings.is_production)
        self.assertFalse(settings.api_docs_enabled)

    def test_enabled_admin_routes_require_strong_non_placeholder_secret(self):
        invalid_values = ("", "short", "your_admin_secret_here", "<staging-admin-secret>")

        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    _settings(ADMIN_ROUTES_ENABLED=True, ADMIN_SECRET=value)

    def test_production_docs_are_disabled_by_default(self):
        settings = _settings(
            APP_ENV="production",
            API_DOCS_ENABLED=None,
            FRONTEND_URL="https://app.example.test",
        )

        with _client(settings) as client:
            self.assertEqual(client.get("/docs").status_code, 404)
            self.assertEqual(client.get("/redoc").status_code, 404)
            self.assertEqual(client.get("/openapi.json").status_code, 404)

    def test_production_docs_can_be_enabled_explicitly(self):
        settings = _settings(
            APP_ENV="production",
            API_DOCS_ENABLED=True,
            FRONTEND_URL="https://app.example.test",
        )

        with _client(settings) as client:
            self.assertEqual(client.get("/docs").status_code, 200)
            self.assertEqual(client.get("/openapi.json").status_code, 200)

    def test_development_docs_remain_enabled_by_default(self):
        settings = _settings(APP_ENV="development", API_DOCS_ENABLED=None)

        with _client(settings) as client:
            self.assertEqual(client.get("/docs").status_code, 200)
            self.assertEqual(client.get("/openapi.json").status_code, 200)

    def test_production_rejects_mock_evaluation(self):
        with self.assertRaises(ValidationError):
            _settings(APP_ENV="production", DEV_MOCK_EVALUATION=True)


if __name__ == "__main__":
    unittest.main()
