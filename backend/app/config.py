import logging
from urllib.parse import urlsplit
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s"
)

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ADMIN_SECRET_MIN_LENGTH = 32
ADMIN_SECRET_PLACEHOLDER_MARKERS = (
    "<staging-admin-secret>",
    "your_admin_secret",
    "change-me",
    "changeme",
    "placeholder",
    "example",
)
LOCAL_APP_ENVS = {"development", "dev", "local", "test"}

class Settings(BaseSettings):
    """
    All application configuration loaded from environment variables.

    pydantic-settings reads these automatically from the .env file.
    If any required variable is missing, the app will fail at startup
    with a clear error message not silently at runtime.
    """

    APP_ENV: str = "production"
    ADMIN_ROUTES_ENABLED: bool = False
    API_DOCS_ENABLED: bool | None = None

    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_JWT_SECRET: str
    SUPABASE_JWT_ALGORITHMS: str = "ES256"
    SUPABASE_JWT_AUDIENCE: str = "authenticated"

    DATABASE_URL: str

    AI_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str
    GROQ_API_KEY: str | None = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    AGENT1_MODEL: str = "gemini-2.5-flash"
    AGENT2_MODEL: str = "gemini-2.5-flash"
    AGENT3_MODEL: str = "gemini-2.5-pro"
    AGENT3_FALLBACK_MODEL: str = "gemini-2.5-flash"
    FOLLOW_UP_MODEL: str = "gemini-2.5-flash"
    AGENT1_MAX_INPUT_CHARS: int = 30000
    AGENT2_MAX_INPUT_CHARS: int = 30000
    AGENT3_MAX_INPUT_CHARS: int = 25000
    AGENT1_MAX_OUTPUT_TOKENS: int = 3200
    AGENT2_MAX_OUTPUT_TOKENS: int = 1200
    AGENT3_MAX_OUTPUT_TOKENS: int = 2600
    FOLLOW_UP_MAX_CONTEXT_CHARS: int = 12000
    FOLLOW_UP_MAX_QUESTION_CHARS: int = 2000
    FOLLOW_UP_MAX_OUTPUT_TOKENS: int = 1000
    MAX_USER_INPUT_CHARS: int = 2000
    EVALUATION_TIMEZONE: str = "UTC"
    GEMINI_TIMEOUT_SECONDS: int = 120
    LLAMA_PARSE_TIMEOUT_SECONDS: int = 90
    MAX_CV_PDF_PAGES: int = 20
    ENABLE_CV_LIKENESS_CHECK: bool = True
    CV_LIKENESS_MIN_TEXT_CHARS: int = 300
    CV_LIKENESS_MIN_SCORE: int = 3
    CV_LIKENESS_MAX_PAGES_TO_SCAN: int = 3
    DEV_MOCK_EVALUATION: bool = False
    DAILY_BUDGET_ENABLED: bool = False
    DAILY_USER_EVALUATION_LIMIT: int = 25
    DAILY_USER_ESTIMATED_TOKEN_LIMIT: int = 1000000
    DAILY_GLOBAL_ESTIMATED_TOKEN_LIMIT: int = 10000000
    RATE_LIMIT_FAIL_OPEN: bool = True
    CIRCUIT_BREAKER_FAIL_OPEN: bool = False
    BUDGET_REDIS_FALLBACK_ENABLED: bool = True
    LLAMAPARSE_API_KEY: str
    HUGGINGFACE_API_TOKEN: str

    GITHUB_TOKEN: str

    UPSTASH_REDIS_REST_URL: str
    UPSTASH_REDIS_REST_TOKEN: str
    ADMIN_SECRET: str = ""

    SENTRY_DSN: str | None = None

    FRONTEND_URL: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.strip().lower() in {"production", "prod"}

    @property
    def is_local_development(self) -> bool:
        return self.APP_ENV.strip().lower() in LOCAL_APP_ENVS

    @property
    def api_docs_enabled(self) -> bool:
        if self.API_DOCS_ENABLED is not None:
            return self.API_DOCS_ENABLED
        return not self.is_production

    @property
    def frontend_origin(self) -> str:
        value = self.FRONTEND_URL.strip()
        parsed = urlsplit(value)
        try:
            parsed.port
        except ValueError as exc:
            raise ValueError("FRONTEND_URL contains an invalid port") from exc

        if (
            not value
            or "*" in value
            or parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.hostname is None
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(
                "FRONTEND_URL must be a single origin without path, query, "
                "fragment, credentials, or wildcard"
            )
        if self.is_production and parsed.scheme != "https":
            raise ValueError("FRONTEND_URL must use HTTPS in production")
        return f"{parsed.scheme}://{parsed.netloc}"

    @model_validator(mode="after")
    def validate_gate3_security(self):
        if self.ADMIN_ROUTES_ENABLED:
            secret = self.ADMIN_SECRET.strip()
            lowered_secret = secret.lower()
            if (
                len(secret) < ADMIN_SECRET_MIN_LENGTH
                or any(marker in lowered_secret for marker in ADMIN_SECRET_PLACEHOLDER_MARKERS)
            ):
                raise ValueError(
                    "ADMIN_SECRET must be a non-placeholder value of at least "
                    f"{ADMIN_SECRET_MIN_LENGTH} characters when admin routes are enabled"
                )

        if self.is_production and self.DEV_MOCK_EVALUATION:
            raise ValueError("DEV_MOCK_EVALUATION cannot be enabled in production")

        return self

settings = Settings()
