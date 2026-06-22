import os
import unittest

from fastapi.testclient import TestClient

os.environ["SENTRY_DSN"] = ""
os.environ["APP_ENV"] = "development"

from app.config import Settings
from app.main import create_app


def _settings(**overrides) -> Settings:
    values = {
        "APP_ENV": "development",
        "ADMIN_ROUTES_ENABLED": False,
        "API_DOCS_ENABLED": False,
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
        "FRONTEND_URL": "http://localhost:5173",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def _client(app_settings: Settings) -> TestClient:
    return TestClient(
        create_app(
            app_settings,
            lifespan_handler=None,
            initialize_observability=False,
        )
    )


def _preflight(client: TestClient, origin: str):
    return client.options(
        "/api/chat/test-chat/upload",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )


class CorsOriginSecurityTests(unittest.TestCase):
    def assert_origin_allowed(self, client: TestClient, origin: str):
        response = _preflight(client, origin)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("access-control-allow-origin"), origin)
        self.assertEqual(response.headers.get("access-control-allow-credentials"), "true")
        self.assertIn("POST", response.headers.get("access-control-allow-methods", ""))
        allowed_headers = response.headers.get("access-control-allow-headers", "").lower()
        self.assertIn("authorization", allowed_headers)
        self.assertIn("content-type", allowed_headers)

    def assert_origin_denied(self, client: TestClient, origin: str):
        response = _preflight(client, origin)
        self.assertEqual(response.status_code, 400)
        self.assertIsNone(response.headers.get("access-control-allow-origin"))

    def test_production_allows_only_configured_frontend_origin(self):
        settings = _settings(
            APP_ENV="production",
            FRONTEND_URL="https://frontend.example",
        )

        with _client(settings) as client:
            self.assert_origin_allowed(client, "https://frontend.example")
            self.assert_origin_denied(client, "http://localhost:5173")
            self.assert_origin_denied(client, "http://127.0.0.1:5173")
            self.assert_origin_denied(client, "https://untrusted.example")

    def test_development_allows_configured_and_loopback_origins(self):
        settings = _settings(
            APP_ENV="development",
            FRONTEND_URL="http://localhost:4173",
        )

        with _client(settings) as client:
            self.assert_origin_allowed(client, "http://localhost:4173")
            self.assert_origin_allowed(client, "http://localhost:5173")
            self.assert_origin_allowed(client, "http://127.0.0.1:5173")
            self.assert_origin_denied(client, "https://untrusted.example")

    def test_staging_allows_only_configured_origin(self):
        settings = _settings(
            APP_ENV="staging",
            FRONTEND_URL="https://staging-frontend.example",
        )

        with _client(settings) as client:
            self.assert_origin_allowed(client, "https://staging-frontend.example")
            self.assert_origin_denied(client, "http://localhost:5173")
            self.assert_origin_denied(client, "http://127.0.0.1:5173")

    def test_frontend_origin_normalizes_one_trailing_slash(self):
        settings = _settings(
            APP_ENV="production",
            FRONTEND_URL="https://frontend.example/",
        )

        self.assertEqual(settings.frontend_origin, "https://frontend.example")

    def test_production_requires_https(self):
        settings = _settings(
            APP_ENV="production",
            FRONTEND_URL="http://frontend.example",
        )

        with self.assertRaisesRegex(ValueError, "HTTPS"):
            settings.frontend_origin

    def test_frontend_url_rejects_non_origin_values(self):
        invalid_values = (
            "https://*.example.com",
            "https://frontend.example/chat",
            "https://frontend.example?source=test",
            "https://frontend.example#fragment",
            "https://user:password@frontend.example",
            "https://frontend.example:not-a-port",
            "frontend.example",
        )

        for value in invalid_values:
            with self.subTest(value=value):
                settings = _settings(FRONTEND_URL=value)
                with self.assertRaises(ValueError):
                    settings.frontend_origin


if __name__ == "__main__":
    unittest.main()
