import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s"
)

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    All application configuration loaded from environment variables.
    
    pydantic-settings reads these automatically from the .env file.
    If any required variable is missing, the app will fail at startup
    with a clear error message not silently at runtime.
    """
      
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_JWT_SECRET: str

    DATABASE_URL: str

    GEMINI_API_KEY: str
    AGENT1_MAX_INPUT_CHARS: int = 30000
    AGENT2_MAX_INPUT_CHARS: int = 30000
    AGENT3_MAX_INPUT_CHARS: int = 25000
    AGENT1_MAX_OUTPUT_TOKENS: int = 1200
    AGENT2_MAX_OUTPUT_TOKENS: int = 1200
    AGENT3_MAX_OUTPUT_TOKENS: int = 1800
    GEMINI_TIMEOUT_SECONDS: int = 120
    DEV_MOCK_EVALUATION: bool = False
    LLAMAPARSE_API_KEY: str
    HUGGINGFACE_API_TOKEN: str

    GITHUB_TOKEN: str

    UPSTASH_REDIS_REST_URL: str
    UPSTASH_REDIS_REST_TOKEN: str
    ADMIN_SECRET: str

    SENTRY_DSN: str | None = None

    FRONTEND_URL: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
