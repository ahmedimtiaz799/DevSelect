import hashlib
import logging
import re
from typing import Any


FILTERED = "[Filtered]"

_UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
    r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b"
)
_IPV4_RE = re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])")
_URL_RE = re.compile(r"\b(?:https?|postgres(?:ql)?|redis)://[^\s'\"<>]+", re.IGNORECASE)
_RELATIVE_QUERY_RE = re.compile(r"(?P<path>/[^\s?\"']+)\?[^\s\"']+")
_BEARER_RE = re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE)
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")
_PROVIDER_KEY_RE = re.compile(
    r"\b(?:sk-[A-Za-z0-9_-]{8,}|AIza[A-Za-z0-9_-]{8,}|gsk_[A-Za-z0-9_-]{8,})\b"
)
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(?:authorization|access_token|refresh_token|api_key|service_role|"
    r"jwt_secret|database_url|redis_token|password|secret|resume_payload|"
    r"raw_cv_text|cv_text|prompt|provider_response)\s*[:=]\s*[^\s,;]+"
)

_SENSITIVE_FIELD_MARKERS = (
    "authorization",
    "access_token",
    "refresh_token",
    "service_role",
    "jwt",
    "password",
    "secret",
    "cookie",
    "database_url",
    "redis",
    "api_key",
    "request_body",
    "body",
    "query_string",
    "resume_payload",
    "raw_cv",
    "cv_text",
    "resume_text",
    "pdf_preview",
    "prompt",
    "provider_payload",
    "provider_response",
    "response_body",
    "locals",
    "vars",
)


def safe_log_id(value: Any, label: str = "id") -> str:
    if value is None or value == "":
        return f"{label}:unknown"
    digest = hashlib.sha256(str(value).encode("utf-8", errors="replace")).hexdigest()[:10]
    return f"{label}:{digest}"


def redact_log_text(value: Any) -> str:
    text = str(value)
    text = _BEARER_RE.sub("Bearer [Filtered]", text)
    text = _JWT_RE.sub(FILTERED, text)
    text = _PROVIDER_KEY_RE.sub(FILTERED, text)
    text = _SECRET_ASSIGNMENT_RE.sub(FILTERED, text)
    text = _URL_RE.sub("[url]", text)
    text = _RELATIVE_QUERY_RE.sub(lambda match: f"{match.group('path')}?[Filtered]", text)
    text = _UUID_RE.sub(lambda match: safe_log_id(match.group(0)), text)
    text = _IPV4_RE.sub(lambda match: safe_log_id(match.group(0), "ip"), text)
    return text


class SensitiveDataFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.msg = redact_log_text(record.getMessage())
            record.args = ()
        except Exception:
            record.msg = "Log message redacted after formatting failure"
            record.args = ()
        return True


def configure_logging_hygiene() -> None:
    for handler in logging.getLogger().handlers:
        if not any(isinstance(item, SensitiveDataFilter) for item in handler.filters):
            handler.addFilter(SensitiveDataFilter())

    for logger_name in (
        "devselect",
        "uvicorn.access",
        "uvicorn.error",
        "httpx",
        "httpcore",
        "supabase",
        "postgrest",
        "gotrue",
        "storage3",
    ):
        logger = logging.getLogger(logger_name)
        if not any(isinstance(item, SensitiveDataFilter) for item in logger.filters):
            logger.addFilter(SensitiveDataFilter())


def _is_sensitive_field(key: Any) -> bool:
    normalized = str(key).strip().lower()
    return any(marker in normalized for marker in _SENSITIVE_FIELD_MARKERS)


def _scrub_mapping(value: dict[Any, Any]) -> dict[Any, Any]:
    scrubbed: dict[Any, Any] = {}
    for key, item in value.items():
        scrubbed[key] = FILTERED if _is_sensitive_field(key) else _scrub_value(item)
    return scrubbed


def _scrub_value(value: Any) -> Any:
    if isinstance(value, dict):
        return _scrub_mapping(value)
    if isinstance(value, list):
        return [_scrub_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_scrub_value(item) for item in value)
    if isinstance(value, str):
        return redact_log_text(value)
    return value


def scrub_sentry_event(event: dict[str, Any], hint: dict[str, Any] | None = None) -> dict[str, Any]:
    request = event.get("request")
    if isinstance(request, dict):
        request["headers"] = FILTERED
        request["cookies"] = FILTERED
        request["data"] = FILTERED
        request["query_string"] = FILTERED
        request["env"] = FILTERED
        if request.get("url"):
            request["url"] = FILTERED

    event["user"] = {}

    breadcrumbs = event.get("breadcrumbs")
    if isinstance(breadcrumbs, dict):
        values = breadcrumbs.get("values")
        if isinstance(values, list):
            for breadcrumb in values:
                if isinstance(breadcrumb, dict):
                    breadcrumb["message"] = FILTERED
                    breadcrumb["data"] = FILTERED

    exception = event.get("exception")
    if isinstance(exception, dict):
        values = exception.get("values")
        if isinstance(values, list):
            for exception_value in values:
                if not isinstance(exception_value, dict):
                    continue
                exception_value["value"] = exception_value.get("type") or "Exception"
                stacktrace = exception_value.get("stacktrace")
                if isinstance(stacktrace, dict):
                    frames = stacktrace.get("frames")
                    if isinstance(frames, list):
                        for frame in frames:
                            if isinstance(frame, dict):
                                frame["vars"] = FILTERED

    threads = event.get("threads")
    if isinstance(threads, dict):
        for thread in threads.get("values") or []:
            if not isinstance(thread, dict):
                continue
            stacktrace = thread.get("stacktrace")
            if isinstance(stacktrace, dict):
                for frame in stacktrace.get("frames") or []:
                    if isinstance(frame, dict):
                        frame["vars"] = FILTERED

    for key in ("extra", "contexts", "tags", "logentry"):
        value = event.get(key)
        if isinstance(value, dict):
            event[key] = _scrub_mapping(value)

    spans = event.get("spans")
    if isinstance(spans, list):
        event["spans"] = [
            _scrub_mapping(span) if isinstance(span, dict) else FILTERED
            for span in spans
        ]

    if event.get("message"):
        event["message"] = FILTERED
    if event.get("transaction"):
        event["transaction"] = redact_log_text(event["transaction"])

    return event