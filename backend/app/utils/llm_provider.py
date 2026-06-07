from dataclasses import dataclass
import math
import re
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import settings

GEMINI_PROVIDER = "gemini"
GROQ_PROVIDER = "groq"


class LLMProviderConfigurationError(Exception):
    pass


class LLMProviderRateLimitError(Exception):
    def __init__(
        self,
        provider: str,
        model: str,
        original_error: Exception,
        retry_after_seconds: int | None = None,
    ):
        self.provider = provider
        self.model = model
        self.original_error = original_error
        self.retry_after_seconds = retry_after_seconds
        self.user_message = llm_rate_limit_message(provider)
        self.error_code = llm_rate_limit_code(provider)
        super().__init__(f"{provider} rate-limited for {model}: {type(original_error).__name__}")


class LLMProviderUnavailableError(Exception):
    def __init__(
        self,
        provider: str,
        model: str,
        original_error: Exception,
        status_code: int | None = None,
        provider_status: str = "unknown",
        retry_after_seconds: int | None = None,
    ):
        self.provider = provider
        self.model = model
        self.original_error = original_error
        self.status_code = status_code
        self.provider_status = provider_status
        self.retry_after_seconds = retry_after_seconds
        self.user_message = llm_unavailable_message(provider, status_code)
        self.error_code = llm_unavailable_code(provider, status_code)
        super().__init__(f"{provider} unavailable for {model}: {type(original_error).__name__}")


@dataclass(frozen=True)
class LLMErrorDetails:
    error_type: str
    status_code: int | None
    provider_status: str
    retry_after_seconds: int | None
    rate_limited: bool
    transient: bool


def current_ai_provider() -> str:
    provider = (settings.AI_PROVIDER or GEMINI_PROVIDER).strip().lower()
    if provider not in {GEMINI_PROVIDER, GROQ_PROVIDER}:
        raise LLMProviderConfigurationError(f"Unsupported AI_PROVIDER: {provider}")
    return provider


def llm_model_name(agent: str, fallback: bool = False) -> str:
    if current_ai_provider() == GROQ_PROVIDER:
        return settings.GROQ_MODEL

    if agent == "agent1":
        return settings.AGENT1_MODEL
    if agent == "agent2":
        return settings.AGENT2_MODEL
    if agent == "agent3":
        return settings.AGENT3_FALLBACK_MODEL if fallback else settings.AGENT3_MODEL
    if agent == "follow_up":
        return settings.FOLLOW_UP_MODEL

    raise LLMProviderConfigurationError(f"Unsupported LLM agent: {agent}")


def create_chat_llm(
    agent: str,
    *,
    model_name: str | None = None,
    temperature: float,
    max_tokens: int,
    streaming: bool = False,
    max_retries: int = 0,
):
    provider = current_ai_provider()
    selected_model = model_name or llm_model_name(agent)

    if provider == GROQ_PROVIDER:
        if not settings.GROQ_API_KEY:
            raise LLMProviderConfigurationError("GROQ_API_KEY is not configured.")
        try:
            from langchain_groq import ChatGroq
        except ImportError as e:
            raise LLMProviderConfigurationError(
                "langchain-groq is not installed. Install backend requirements before using AI_PROVIDER=groq."
            ) from e

        return ChatGroq(
            model=selected_model,
            groq_api_key=settings.GROQ_API_KEY,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=settings.GEMINI_TIMEOUT_SECONDS,
            max_retries=max_retries,
        )

    gemini_kwargs = {
        "model": selected_model,
        "google_api_key": settings.GEMINI_API_KEY,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "request_timeout": settings.GEMINI_TIMEOUT_SECONDS,
        "max_retries": max_retries,
    }
    if agent in {"agent1", "agent2"} or (
        agent == "agent3" and "flash" in selected_model.lower()
    ):
        gemini_kwargs["thinking_budget"] = 0
    if streaming:
        gemini_kwargs["streaming"] = True

    return ChatGoogleGenerativeAI(**gemini_kwargs)


def structured_output_kwargs(include_raw: bool = True) -> dict[str, Any]:
    method = "json_mode" if current_ai_provider() == GROQ_PROVIDER else "json_schema"
    return {
        "method": method,
        "include_raw": include_raw,
    }


def llm_error_details(error: Exception) -> LLMErrorDetails:
    text = str(error)
    lowered = text.lower()
    status_code_match = re.search(r"\b(400|401|403|408|429|500|502|503|504)\b", text)
    retry_match = re.search(
        r"(?:retry(?:Delay|_delay| in)?[\"':=\s]*)(\d+(?:\.\d+)?)\s*s",
        text,
        re.IGNORECASE,
    )
    provider_status = _error_provider_status(error, lowered)
    status_code = _error_status_code(error)
    if status_code is None and status_code_match:
        status_code = int(status_code_match.group(1))

    retry_after_seconds = math.ceil(float(retry_match.group(1))) if retry_match else None
    rate_limited = (
        status_code == 429
        or provider_status in {"RESOURCE_EXHAUSTED", "RATE_LIMITED", "RATE_LIMIT_EXCEEDED"}
        or any(marker in lowered for marker in ("quota", "rate limit", "rate_limit", "too many requests"))
    )
    transient = (
        status_code in {408, 500, 502, 503, 504}
        or provider_status in {"UNAVAILABLE", "DEADLINE_EXCEEDED", "INTERNAL", "SERVICE_UNAVAILABLE"}
        or any(marker in lowered for marker in ("timeout", "timed out", "overloaded", "temporarily unavailable"))
    )

    return LLMErrorDetails(
        error_type=type(error).__name__,
        status_code=429 if rate_limited and status_code is None else status_code,
        provider_status=(
            "RESOURCE_EXHAUSTED"
            if rate_limited and provider_status == "unknown"
            else provider_status
        ),
        retry_after_seconds=retry_after_seconds,
        rate_limited=rate_limited,
        transient=transient,
    )


def llm_rate_limit_message(provider: str) -> str:
    if provider == GROQ_PROVIDER:
        return "Groq is temporarily rate-limited. Please try again in a few minutes."
    return "Gemini is temporarily rate-limited. Please try again in a few minutes."


def llm_unavailable_message(provider: str, status_code: int | None = None) -> str:
    if provider == GROQ_PROVIDER:
        return "Groq is temporarily unavailable. Please try again in a few minutes."
    if status_code == 504:
        return "Gemini timed out while generating the evaluation. Please try again in a few minutes."
    return "Gemini is temporarily overloaded. Please try again in a few minutes."


def llm_rate_limit_code(provider: str) -> str:
    return "GROQ_RATE_LIMITED" if provider == GROQ_PROVIDER else "GEMINI_RATE_LIMITED"


def llm_unavailable_code(provider: str, status_code: int | None = None) -> str:
    if provider == GROQ_PROVIDER:
        return "GROQ_TEMPORARILY_UNAVAILABLE"
    if status_code == 504:
        return "GEMINI_TIMEOUT"
    return "GEMINI_PROVIDER_UNAVAILABLE"


def _error_status_code(error: Exception) -> int | None:
    for attr in ("status_code", "code"):
        value = getattr(error, attr, None)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
        enum_value = getattr(value, "value", None)
        if isinstance(enum_value, int):
            return enum_value

    response = getattr(error, "response", None)
    value = getattr(response, "status_code", None)
    return value if isinstance(value, int) else None


def _error_provider_status(error: Exception, lowered_text: str) -> str:
    for attr in ("status", "reason"):
        value = getattr(error, attr, None)
        if value:
            status = str(getattr(value, "name", value)).strip()
            if status:
                return status

    return next(
        (
            status
            for status in (
                "RESOURCE_EXHAUSTED",
                "RATE_LIMITED",
                "RATE_LIMIT_EXCEEDED",
                "UNAVAILABLE",
                "SERVICE_UNAVAILABLE",
                "DEADLINE_EXCEEDED",
                "INVALID_ARGUMENT",
                "INTERNAL",
            )
            if status.lower() in lowered_text
        ),
        "unknown",
    )
