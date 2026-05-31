from collections.abc import Mapping
from typing import Any

TRUNCATION_MARKER = "\n\n[Content truncated for token budget]"


def estimate_tokens_from_text(text: str | None) -> int:
    if not text:
        return 0

    return max(1, (len(text) + 3) // 4)


def cap_text_for_llm(text: str | None, max_chars: int) -> tuple[str, int, int, bool]:
    value = text or ""
    original_chars = len(value)

    if max_chars <= 0 or original_chars <= max_chars:
        return value, original_chars, original_chars, False

    if max_chars <= len(TRUNCATION_MARKER):
        capped = TRUNCATION_MARKER[:max_chars]
    else:
        keep_chars = max_chars - len(TRUNCATION_MARKER)
        capped = value[:keep_chars].rstrip() + TRUNCATION_MARKER

    return capped, original_chars, len(capped), True


def estimate_tokens_from_messages(messages: list[Any]) -> int:
    total_chars = 0

    for message in messages:
        total_chars += _content_length(getattr(message, "content", message))

    if total_chars == 0:
        return 0

    return max(1, (total_chars + 3) // 4)


def log_llm_request(
    logger,
    agent: str,
    model: str,
    thread_id: str | None,
    estimated_input_tokens: int,
    max_output_tokens: int,
) -> None:
    logger.info(
        "LLM request : agent=%s model=%s thread=%s estimated_input_tokens=%s max_output_tokens=%s",
        agent,
        model,
        thread_id or "unknown",
        estimated_input_tokens,
        max_output_tokens,
    )


def log_llm_usage(
    logger,
    agent: str,
    model: str,
    thread_id: str | None,
    response: Any,
) -> None:
    usage = _usage_metadata(response)

    if not usage:
        logger.info(
            "LLM usage unavailable : agent=%s model=%s thread=%s",
            agent,
            model,
            thread_id or "unknown",
        )
        return

    prompt_tokens = _value(usage, "input_tokens", "prompt_tokens", "prompt_token_count")
    output_tokens = _value(
        usage,
        "output_tokens",
        "completion_tokens",
        "candidate_tokens",
        "candidates_token_count",
    )
    total_tokens = _value(usage, "total_tokens", "total_token_count")
    cached_tokens = _cached_tokens(usage)

    logger.info(
        "LLM usage : agent=%s model=%s thread=%s prompt_tokens=%s output_tokens=%s total_tokens=%s cached_tokens=%s",
        agent,
        model,
        thread_id or "unknown",
        prompt_tokens if prompt_tokens is not None else "unknown",
        output_tokens if output_tokens is not None else "unknown",
        total_tokens if total_tokens is not None else "unknown",
        cached_tokens if cached_tokens is not None else "unknown",
    )


def _content_length(content: Any) -> int:
    if content is None:
        return 0

    if isinstance(content, str):
        return len(content)

    if isinstance(content, (list, tuple)):
        return sum(_content_length(item) for item in content)

    if isinstance(content, Mapping):
        return sum(_content_length(value) for value in content.values())

    return len(str(content))


def _usage_metadata(response: Any) -> Any:
    usage = getattr(response, "usage_metadata", None)
    if usage:
        return usage

    response_metadata = getattr(response, "response_metadata", None)
    if isinstance(response_metadata, Mapping):
        return response_metadata.get("usage_metadata") or response_metadata.get("token_usage")

    return None


def _value(source: Any, *names: str) -> Any:
    for name in names:
        if isinstance(source, Mapping) and source.get(name) is not None:
            return source.get(name)

        value = getattr(source, name, None)
        if value is not None:
            return value

    return None


def _cached_tokens(usage: Any) -> Any:
    direct_value = _value(usage, "cached_tokens", "cached_content_token_count", "cache_read")
    if direct_value is not None:
        return direct_value

    input_details = _value(usage, "input_token_details", "prompt_token_details")
    if input_details is None:
        return None

    return _value(input_details, "cache_read", "cached_tokens", "cached_content_token_count")
