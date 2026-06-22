import re
import logging
import tempfile
import os
import asyncio
from typing import Any

from langgraph.types import interrupt
from llama_parse import LlamaParse
from pydantic import ValidationError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.agents.state import DevSelectState
from app.config import settings
from app.models.candidate import CandidateExtraction
from app.prompts.agent1_prompt import AGENT1_PROMPT
from app.utils.llm_observability import (
    cap_text_for_llm,
    estimate_tokens_from_text,
    log_llm_request,
    log_llm_usage,
)
from app.utils.cv_likeness import assess_cv_likeness
from app.utils.candidate_domain import (
    SKIP_NON_TECHNICAL,
    classify_candidate_domain,
    github_review_policy,
    resolve_candidate_display_role_with_source,
)
from app.utils.llm_provider import (
    GROQ_PROVIDER,
    LLMProviderConfigurationError,
    LLMProviderRateLimitError,
    LLMProviderUnavailableError,
    create_chat_llm,
    current_ai_provider,
    llm_error_details,
    llm_model_name,
    structured_output_kwargs,
)

logger = logging.getLogger("devselect")
CV_NOT_LIKELY_MESSAGE = "This PDF does not look like a candidate CV. Please upload a CV or resume PDF."
CV_EXTRACTION_INVALID_MESSAGE = "This PDF could not be read as a candidate CV. Please upload a standard CV or resume PDF."
CV_ANALYSIS_TEMPORARILY_UNAVAILABLE_MESSAGE = "CV analysis is temporarily unavailable. Please try again in a few minutes."
EVALUATION_PREPARATION_FAILED_MESSAGE = "We could not prepare this evaluation. Please upload the CV again."
GROQ_VALIDATION_FAILED_MESSAGE = "Groq returned an incomplete structured response. Please try again."
NON_TECHNICAL_GITHUB_SKIP_MESSAGE = (
    "This CV appears to be for a non-technical or business-oriented role. "
    "GitHub review will be skipped and the evaluation will proceed using CV evidence only."
)
UNCLEAR_ROLE_GITHUB_SKIP_MESSAGE = (
    "The candidate role is unclear from the CV, so GitHub review will be skipped and "
    "the evaluation will proceed cautiously using CV evidence only."
)


class LlamaParseTransientError(Exception):
    pass


class LlamaParseTimeoutError(Exception):
    pass


class LlamaParseEmptyResultError(Exception):
    pass


class GeminiTransientError(Exception):
    pass


class Agent1StructuredOutputError(Exception):
    pass




def _cv_evidence_flags(text: str) -> dict[str, bool]:
    upper_text = (text or "").upper()
    return {
        "skills": "SKILLS" in upper_text,
        "projects": "PROJECTS" in upper_text,
        "education": "EDUCATION" in upper_text,
        "certifications": "CERTIFICATIONS" in upper_text,
        "devselect": "DEVSELECT" in upper_text,
        "casex": "CASEX" in upper_text,
    }


def _delete_file(path: str | None) -> None:
    if not path:
        return

    try:
        os.unlink(path)
    except FileNotFoundError:
        return
    except Exception as e:
        logger.warning(f"Temporary PDF cleanup failed: {type(e).__name__}")


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    retry=retry_if_exception_type(LlamaParseTransientError),
    reraise=True,
)
async def _parse_pdf_with_llamaparse(pdf_path: str) -> str:
    try:
        parser = LlamaParse(
            api_key=settings.LLAMAPARSE_API_KEY,
            result_type="markdown",
            use_vendor_multimodal_model=False,
            language="en",
            verbose=False,
        )

        documents = await asyncio.wait_for(
            parser.aload_data(pdf_path),
            timeout=settings.LLAMA_PARSE_TIMEOUT_SECONDS,
        )

        if not documents:
            raise LlamaParseEmptyResultError("LlamaParse returned no documents.")

        markdown_text = "\n\n".join(doc.text for doc in documents)

        if not markdown_text.strip():
            raise LlamaParseEmptyResultError("LlamaParse returned empty markdown.")

        return markdown_text

    except asyncio.TimeoutError as e:
        logger.warning("LlamaParse timed out after %s seconds", settings.LLAMA_PARSE_TIMEOUT_SECONDS)
        raise LlamaParseTimeoutError("LlamaParse timed out.") from e
    except LlamaParseEmptyResultError:
        raise
    except Exception as e:
        logger.error("LlamaParse error : error_type=%s", type(e).__name__)
        raise LlamaParseTransientError(f"LlamaParse transient error: {e}")


def _response_content_length(response: Any) -> int:
    content = getattr(response, "content", None)
    if content is None:
        return 0

    if isinstance(content, str):
        return len(content)

    return len(str(content))


def _response_finish_reason(response: Any) -> str:
    metadata = getattr(response, "response_metadata", None)
    if isinstance(metadata, dict):
        for key in ("finish_reason", "finishReason", "finish_reasons"):
            value = metadata.get(key)
            if value:
                return str(value)

    return "unknown"


def _is_structured_output_exception(error: Exception) -> bool:
    error_type = type(error).__name__.lower()
    error_text = str(error).lower()
    return any(
        marker in error_type or marker in error_text
        for marker in ("json", "parse", "parser", "validation", "schema")
    )


def _structured_failure_stage(response_chars: int, error: Exception | None = None) -> str:
    if response_chars == 0:
        return "no_model_text"

    if response_chars < 120:
        return "short_or_refusal_response"

    if error:
        error_type = type(error).__name__.lower()
        if "validation" in error_type:
            return "pydantic_validation"
        if "json" in error_type or "parse" in error_type or "parser" in error_type:
            return "invalid_json"

    return "structured_output"


async def _parse_pdf_bytes_with_llamaparse(pdf_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name

    try:
        return await _parse_pdf_with_llamaparse(tmp_path)
    finally:
        _delete_file(tmp_path)


def _preview_fallback_text(state: DevSelectState, reason: str) -> str | None:
    preview_text = (state.get("pdf_preview_text") or "").strip()
    fallback_text_chars = len(preview_text)
    fallback_available = fallback_text_chars >= settings.CV_LIKENESS_MIN_TEXT_CHARS

    logger.info(
        "Agent 1: LlamaParse fallback check thread=%s reason=%s llamaparse_docs=0 fallback_used=%s fallback_text_chars=%s",
        state["thread_id"],
        reason,
        fallback_available,
        fallback_text_chars,
    )

    if fallback_available:
        return preview_text

    return None


def _cv_likeness_rejection(markdown_text: str, thread_id: str) -> dict[str, Any] | None:
    if not settings.ENABLE_CV_LIKENESS_CHECK:
        return None

    assessment = assess_cv_likeness(
        markdown_text,
        min_text_chars=settings.CV_LIKENESS_MIN_TEXT_CHARS,
        min_score=settings.CV_LIKENESS_MIN_SCORE,
    )
    logger.info(
        "Agent 1: Parsed CV likeness check thread=%s text_chars=%s score=%s negative_score=%s categories=%s negative_categories=%s low_text=%s reject=%s decision_reason=%s",
        thread_id,
        assessment["text_chars"],
        assessment["score"],
        assessment["negative_score"],
        ",".join(assessment["signal_categories"]) or "none",
        ",".join(assessment["negative_categories"]) or "none",
        assessment["low_text"],
        assessment["should_reject"],
        assessment.get("decision_reason", "unknown"),
    )

    if not assessment["should_reject"]:
        return None

    return {
        "pdf_bytes": None,
        "pdf_temp_path": None,
        "error": CV_NOT_LIKELY_MESSAGE,
        "error_code": "NOT_A_CV",
    }


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    retry=retry_if_exception_type((GeminiTransientError, LLMProviderUnavailableError)),
    reraise=True,
)
async def _extract_with_gemini(markdown_text: str, thread_id: str | None = None) -> CandidateExtraction:
    provider = current_ai_provider()
    model_name = llm_model_name("agent1")
    llm = create_chat_llm(
        "agent1",
        temperature=0.2,
        max_tokens=settings.AGENT1_MAX_OUTPUT_TOKENS,
        max_retries=0,
    )
    structured_llm = llm.with_structured_output(
        CandidateExtraction,
        **structured_output_kwargs(include_raw=True),
    )

    prompt = AGENT1_PROMPT.format(cv_text=markdown_text)
    estimated_input_tokens = estimate_tokens_from_text(prompt)

    try:
        log_llm_request(
            logger,
            "agent1",
            model_name,
            thread_id,
            estimated_input_tokens,
            settings.AGENT1_MAX_OUTPUT_TOKENS,
        )
        result = await structured_llm.ainvoke(prompt)
    except Exception as e:
        details = llm_error_details(e)
        if details.rate_limited:
            raise LLMProviderRateLimitError(
                provider,
                model_name,
                e,
                details.retry_after_seconds,
            ) from e
        if _is_structured_output_exception(e):
            logger.error(
                "Agent 1 structured extraction failed : stage=%s error_type=%s model=%s thread=%s response_chars=%s",
                _structured_failure_stage(0, e),
                type(e).__name__,
                model_name,
                thread_id or "unknown",
                0,
            )
            raise Agent1StructuredOutputError("Agent 1 structured extraction failed.") from e
        if details.transient:
            raise LLMProviderUnavailableError(
                provider,
                model_name,
                e,
                details.status_code,
                details.provider_status,
                details.retry_after_seconds,
            ) from e
        raise GeminiTransientError(f"{provider} API error: {type(e).__name__}") from e

    raw_response = result.get("raw") if isinstance(result, dict) else None
    log_llm_usage(logger, "agent1", model_name, thread_id, raw_response or result)
    finish_reason = _response_finish_reason(raw_response)
    logger.info(
        "Agent 1 response diagnostics : thread=%s model=%s response_chars=%s finish_reason=%s",
        thread_id or "unknown",
        model_name,
        _response_content_length(raw_response),
        finish_reason,
    )
    if "MAX_TOKENS" in finish_reason.upper():
        logger.error(
            "Agent 1 structured extraction failed : stage=max_tokens error_type=%s model=%s thread=%s response_chars=%s",
            Agent1StructuredOutputError.__name__,
            model_name,
            thread_id or "unknown",
            _response_content_length(raw_response),
        )
        raise Agent1StructuredOutputError("Agent 1 structured extraction reached the output limit.")

    if isinstance(result, CandidateExtraction):
        return result

    if isinstance(result, dict):
        parsed = result.get("parsed")
        parsing_error = result.get("parsing_error")
        response_chars = _response_content_length(raw_response)

        if parsing_error:
            logger.error(
                "Agent 1 structured extraction failed : stage=%s error_type=%s model=%s thread=%s response_chars=%s",
                _structured_failure_stage(response_chars, parsing_error),
                type(parsing_error).__name__,
                model_name,
                thread_id or "unknown",
                response_chars,
            )
            raise Agent1StructuredOutputError("Agent 1 structured extraction failed.") from parsing_error

        if isinstance(parsed, CandidateExtraction):
            return parsed

        if isinstance(parsed, dict):
            try:
                return CandidateExtraction.model_validate(parsed)
            except ValidationError as e:
                logger.error(
                    "Agent 1 structured extraction failed : stage=%s error_type=%s model=%s thread=%s response_chars=%s",
                    _structured_failure_stage(response_chars, e),
                    type(e).__name__,
                    model_name,
                    thread_id or "unknown",
                    response_chars,
                )
                raise Agent1StructuredOutputError("Agent 1 structured extraction failed.") from e

        logger.error(
            "Agent 1 structured extraction failed : stage=%s error_type=%s model=%s thread=%s response_chars=%s",
            _structured_failure_stage(response_chars),
            type(parsed).__name__,
            model_name,
            thread_id or "unknown",
            response_chars,
        )
        raise Agent1StructuredOutputError("Agent 1 structured extraction failed.")

    logger.error(
        "Agent 1 structured extraction failed : stage=%s error_type=%s model=%s thread=%s response_chars=%s",
        "unexpected_result",
        type(result).__name__,
        model_name,
        thread_id or "unknown",
        0,
    )
    raise Agent1StructuredOutputError("Agent 1 structured extraction failed.")


def is_valid_github_url(url: str) -> bool:
    pattern = r'^(https?://)?github\.com/[a-zA-Z0-9_.-]+(/[a-zA-Z0-9_.\-]*)?$'
    return bool(re.match(pattern, url.strip()))


def normalize_github_url(url: str) -> str:
    url = url.strip()
    if not url.startswith("http"):
        url = "https://" + url
    return url


GITHUB_URL_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?github\.com/[a-zA-Z0-9_.-]+(?:/[a-zA-Z0-9_.-]+)?",
    re.IGNORECASE,
)
GITHUB_OWNER_BLOCKLIST = {
    "about",
    "collections",
    "events",
    "explore",
    "features",
    "join",
    "login",
    "marketplace",
    "new",
    "orgs",
    "pricing",
    "search",
    "settings",
    "topics",
    "trending",
}

ROLE_KEYWORDS = (
    "engineer",
    "developer",
    "architect",
    "designer",
    "executive",
    "officer",
    "accountant",
    "manager",
    "analyst",
    "scientist",
    "specialist",
    "consultant",
    "teacher",
    "lecturer",
    "instructor",
    "trainer",
    "devops",
    "qa",
    "frontend",
    "front-end",
    "backend",
    "back-end",
    "full stack",
    "full-stack",
    "machine learning",
    "ml",
    "ai",
    "data",
    "product",
    "scrum",
    "banking",
    "finance",
    "financial",
    "business",
    "marketing",
    "sales",
    "operations",
    "administrator",
    "coordinator",
)

ROLE_STOP_LINES = {
    "professional summary",
    "summary",
    "experience",
    "work experience",
    "projects",
    "skills",
    "education",
    "certifications",
    "contact",
}


def _extract_github_profile_urls(text: str) -> list[str]:
    profiles: list[str] = []

    for match in GITHUB_URL_PATTERN.finditer(text or ""):
        raw_url = match.group(0).rstrip(".,;:)]}>\"'")
        path = re.sub(
            r"^(?:https?://)?(?:www\.)?github\.com/",
            "",
            raw_url,
            flags=re.IGNORECASE,
        ).strip("/")
        parts = [part for part in path.split("/") if part]
        if not parts:
            continue

        owner = parts[0]
        if owner.lower() in GITHUB_OWNER_BLOCKLIST:
            continue

        profile_url = f"https://github.com/{owner}"
        if is_valid_github_url(profile_url) and profile_url not in profiles:
            profiles.append(profile_url)

    return profiles


def _clean_role(value: str | None) -> str | None:
    role = re.sub(r"\s+", " ", (value or "").strip(" :-|•\t"))
    if not role or len(role) > 80:
        return None

    lowered = role.lower()
    if lowered in ROLE_STOP_LINES:
        return None

    if any(marker in lowered for marker in ("@", "http://", "https://", "github.com", "linkedin.com")):
        return None

    if not any(keyword in lowered for keyword in ROLE_KEYWORDS):
        return None

    return role


def _candidate_role_from_experience(candidate: CandidateExtraction) -> str | None:
    for experience in candidate.work_experience or []:
        role = _clean_role(experience.title)
        if role:
            return role

    return None


def _candidate_role_from_header(raw_cv_text: str, full_name: str | None) -> str | None:
    lines = [
        re.sub(r"\s+", " ", line).strip()
        for line in (raw_cv_text or "").splitlines()
        if line.strip()
    ]
    if not lines:
        return None

    if full_name:
        target_name = re.sub(r"\s+", " ", full_name).strip().lower()
        for index, line in enumerate(lines[:12]):
            if line.lower() == target_name:
                for next_line in lines[index + 1:index + 5]:
                    role = _clean_role(next_line)
                    if role:
                        return role

    for line in lines[:8]:
        role = _clean_role(line)
        if role:
            return role

    return None


def _candidate_role_from_summary(summary: str | None) -> str | None:
    text = re.sub(r"\s+", " ", (summary or "").strip())
    if not text:
        return None

    leading = re.split(r"\bwith\b|\bwho\b|,|\.|;", text, maxsplit=1, flags=re.IGNORECASE)[0]
    role = _clean_role(leading)
    if role:
        return role

    match = re.search(
        r"\b([A-Z][A-Za-z0-9+/# .-]{2,80}?\b(?:Engineer|Developer|Architect|Designer|Manager|Analyst|Scientist|Specialist|Consultant|DevOps|QA)\b)",
        text,
    )
    if match:
        return _clean_role(match.group(1))

    return None


def _ensure_candidate_role(
    candidate: CandidateExtraction,
    raw_cv_text: str,
) -> tuple[CandidateExtraction, str]:
    resolved_role, resolved_source = resolve_candidate_display_role_with_source(candidate, raw_cv_text)
    if resolved_role:
        if resolved_role != candidate.current_title:
            return candidate.model_copy(update={"current_title": resolved_role}), resolved_source
        return candidate, resolved_source

    role_sources = (
        ("cv_header", _candidate_role_from_header(raw_cv_text, candidate.full_name)),
        ("raw_cv_summary", _candidate_role_from_summary(raw_cv_text)),
    )

    for source, role in role_sources:
        if role:
            return candidate.model_copy(update={"current_title": role}), source

    return candidate, "missing"


async def agent1_cv_extraction(state: DevSelectState) -> dict[str, Any]:
    logger.info(f"Agent 1 starting for thread_id={state['thread_id']}")

    if state.get("error"):
        logger.warning("Agent 1 skipping — error already set in state.")
        return {}

    pdf_temp_path = state.get("pdf_temp_path")
    pdf_bytes = state.get("pdf_bytes")
    preview_text = (state.get("pdf_preview_text") or "").strip()

    if not pdf_temp_path and not pdf_bytes and not preview_text:
        return {"error": EVALUATION_PREPARATION_FAILED_MESSAGE}

    try:
        logger.info("Agent 1: Sending PDF to LlamaParse...")
        try:
            if pdf_temp_path:
                if not os.path.exists(pdf_temp_path):
                    raise LlamaParseEmptyResultError("PDF temp path unavailable.")
                raw_cv_text = await _parse_pdf_with_llamaparse(pdf_temp_path)
            elif pdf_bytes:
                raw_cv_text = await _parse_pdf_bytes_with_llamaparse(pdf_bytes)
            else:
                raise LlamaParseEmptyResultError("PDF payload unavailable.")
            logger.info(f"Agent 1: LlamaParse returned {len(raw_cv_text)} characters")
        except LlamaParseEmptyResultError as e:
            fallback_text = _preview_fallback_text(state, type(e).__name__)
            if not fallback_text:
                raise
            raw_cv_text = fallback_text
            logger.info(
                "Agent 1: Using PDF preview fallback thread=%s fallback_text_chars=%s",
                state["thread_id"],
                len(raw_cv_text),
            )
        parsed_flags = _cv_evidence_flags(raw_cv_text)
        logger.info(
            "Agent 1: Parsed CV evidence thread=%s parsed_cv_text_length=%s has_skills=%s has_projects=%s has_education=%s has_certifications=%s has_devselect=%s has_casex=%s",
            state["thread_id"],
            len(raw_cv_text),
            parsed_flags["skills"],
            parsed_flags["projects"],
            parsed_flags["education"],
            parsed_flags["certifications"],
            parsed_flags["devselect"],
            parsed_flags["casex"],
        )
        rejection = _cv_likeness_rejection(raw_cv_text, state["thread_id"])
        if rejection:
            return rejection
        gemini_cv_text, original_cv_chars, capped_cv_chars, was_truncated = cap_text_for_llm(
            raw_cv_text,
            settings.AGENT1_MAX_INPUT_CHARS,
        )
        logger.info(
            "Agent 1: CV markdown input cap thread=%s original_chars=%s capped_chars=%s truncated=%s",
            state["thread_id"],
            original_cv_chars,
            capped_cv_chars,
            was_truncated,
        )
    except LlamaParseTimeoutError:
        return {
            "pdf_bytes": None,
            "pdf_temp_path": None,
            "error": "This file took too long to process. Please upload a standard PDF CV.",
            "error_code": "PDF_PARSE_TIMEOUT",
        }
    except LlamaParseEmptyResultError as e:
        logger.error("Agent 1 failed in Step A: LlamaParse empty and fallback unavailable error_type=%s", type(e).__name__)
        return {
            "pdf_bytes": None,
            "pdf_temp_path": None,
            "error": "This file could not be processed safely. Please upload a standard PDF CV.",
            "error_code": "PDF_PROCESSING_FAILED",
        }
    except Exception as e:
        logger.error("Agent 1 failed in Step A : error_type=%s", type(e).__name__)
        return {
            "pdf_bytes": None,
            "pdf_temp_path": None,
            "error": "This file could not be processed safely. Please upload a standard PDF CV.",
            "error_code": "PDF_PROCESSING_FAILED",
        }
    finally:
        if pdf_temp_path:
            _delete_file(pdf_temp_path)

    try:
        logger.info("Agent 1: Sending parsed text to LLM...")
        candidate = await _extract_with_gemini(
            gemini_cv_text,
            thread_id=state["thread_id"],
        )
        logger.info("Agent 1: LLM responded")
    except LLMProviderRateLimitError as e:
        return {
            "pdf_bytes": None,
            "pdf_temp_path": None,
            "raw_cv_text": raw_cv_text,
            "error": e.user_message,
            "error_code": e.error_code,
            "retry_after_seconds": e.retry_after_seconds,
        }
    except LLMProviderUnavailableError as e:
        return {
            "pdf_bytes": None,
            "pdf_temp_path": None,
            "raw_cv_text": raw_cv_text,
            "error": e.user_message,
            "error_code": e.error_code,
            "retry_after_seconds": e.retry_after_seconds,
        }
    except LLMProviderConfigurationError:
        logger.error("Agent 1 provider configuration failed : thread=%s", state["thread_id"])
        return {
            "pdf_bytes": None,
            "pdf_temp_path": None,
            "raw_cv_text": raw_cv_text,
            "error": CV_ANALYSIS_TEMPORARILY_UNAVAILABLE_MESSAGE,
            "error_code": "LLM_PROVIDER_CONFIGURATION_ERROR",
        }
    except ValueError as e:
        return {"pdf_bytes": None, "pdf_temp_path": None, "raw_cv_text": raw_cv_text, "error": str(e)}
    except Agent1StructuredOutputError:
        if current_ai_provider() == GROQ_PROVIDER:
            return {
                "pdf_bytes": None,
                "pdf_temp_path": None,
                "raw_cv_text": raw_cv_text,
                "error": GROQ_VALIDATION_FAILED_MESSAGE,
                "error_code": "GROQ_VALIDATION_FAILED",
            }
        return {
            "pdf_bytes": None,
            "pdf_temp_path": None,
            "raw_cv_text": raw_cv_text,
            "error": CV_EXTRACTION_INVALID_MESSAGE,
            "error_code": "CV_EXTRACTION_INVALID",
        }
    except Exception as e:
        logger.error("Agent 1 failed in Step B : error_type=%s", type(e).__name__)
        return {
            "pdf_bytes": None,
            "pdf_temp_path": None,
            "raw_cv_text": raw_cv_text,
            "error": CV_ANALYSIS_TEMPORARILY_UNAVAILABLE_MESSAGE,
        }

    candidate, role_source = _ensure_candidate_role(candidate, raw_cv_text)
    candidate_domain, candidate_domain_source = classify_candidate_domain(candidate, raw_cv_text)
    review_policy = github_review_policy(candidate_domain)
    candidate_log_state = candidate.model_dump(mode="json")
    candidate_state_text = str(candidate_log_state).lower()
    raw_section_count = sum(
        parsed_flags[key]
        for key in ("skills", "projects", "education", "certifications")
    )
    extracted_evidence_groups = sum(
        bool(group)
        for group in (
            candidate.skills,
            candidate.languages,
            candidate.frameworks,
            candidate.projects,
            candidate.work_experience,
            candidate.education,
            candidate.certifications,
        )
    )
    logger.info(
        "Agent 1: Extracted candidate thread=%s keys=%s role_present=%s role_source=%s candidate_domain=%s candidate_domain_source=%s github_review_policy=%s skills=%s languages=%s frameworks=%s projects=%s experience=%s education_present=%s certifications=%s candidate_state_chars=%s parsed_cv_chars=%s",
        state["thread_id"],
        ",".join(candidate_log_state.keys()),
        bool(candidate.current_title),
        role_source,
        candidate_domain,
        candidate_domain_source,
        review_policy or "standard",
        len(candidate.skills or []),
        len(candidate.languages or []),
        len(candidate.frameworks or []),
        len(candidate.projects or []),
        len(candidate.work_experience or []),
        bool(candidate.education),
        len(candidate.certifications or []),
        len(candidate_state_text),
        len(raw_cv_text),
    )
    if (
        len(raw_cv_text) >= 1000
        and raw_section_count >= 2
        and extracted_evidence_groups == 0
    ):
        logger.error(
            "Agent 1 blocked incomplete structured extraction : thread=%s parsed_cv_chars=%s raw_section_count=%s extracted_evidence_groups=%s max_output_tokens=%s",
            state["thread_id"],
            len(raw_cv_text),
            raw_section_count,
            extracted_evidence_groups,
            settings.AGENT1_MAX_OUTPUT_TOKENS,
        )
        return {
            "pdf_bytes": None,
            "pdf_temp_path": None,
            "raw_cv_text": raw_cv_text,
            "error": CV_EXTRACTION_INVALID_MESSAGE,
            "error_code": "CANDIDATE_EVIDENCE_INCOMPLETE",
        }

    logger.info("Agent 1: Analysing GitHub URLs and calling interrupt()...")

    if review_policy:
        logger.info(
            "Agent 1: Skipping GitHub review thread=%s candidate_domain=%s policy=%s",
            state["thread_id"],
            candidate_domain,
            review_policy,
        )
        interrupt({
            "github_url": None,
            "scenario": "SKIPPED",
            "candidate_name": candidate.full_name,
            "candidate_role": candidate.current_title,
            "candidate_domain": candidate_domain,
            "message": (
                NON_TECHNICAL_GITHUB_SKIP_MESSAGE
                if review_policy == SKIP_NON_TECHNICAL
                else UNCLEAR_ROLE_GITHUB_SKIP_MESSAGE
            ),
        })
        return {
            "pdf_bytes": None,
            "pdf_temp_path": None,
            "raw_cv_text": raw_cv_text,
            "candidate": candidate.model_dump(mode="json"),
            "candidate_domain": candidate_domain,
            "candidate_domain_source": candidate_domain_source,
            "github_review_policy": review_policy,
        }

    github_urls: list[str] = candidate.github_urls or []
    github_urls = _extract_github_profile_urls("\n".join(github_urls + [raw_cv_text]))
    if github_urls:
        candidate = candidate.model_copy(update={"github_urls": github_urls})
        logger.info(
            "Agent 1: Deterministic GitHub URL detection thread=%s profile_count=%s",
            state["thread_id"],
            len(github_urls),
        )

    if len(github_urls) == 0:
        logger.info("Agent 1: No GitHub URLs found")
        resume_value = interrupt({
            "github_url": None,
            "scenario": "NOT_FOUND",
            "candidate_name": candidate.full_name,
            "message": (
                "No GitHub profile was found in this CV. "
                "You can provide a GitHub URL manually or proceed without one."
            ),
        })
        selected_url = resume_value.get("github_url") if isinstance(resume_value, dict) else None
        if selected_url:
            candidate = candidate.model_copy(update={"github_url": selected_url})

    elif len(github_urls) == 1:
        url = normalize_github_url(github_urls[0])
        if is_valid_github_url(url):
            logger.info("Agent 1: One valid GitHub profile URL found")
            resume_value = interrupt({
                "github_url": url,
                "scenario": "ACCESSIBLE",
                "candidate_name": candidate.full_name,
                "message": (
                    f"GitHub profile found: {url}. "
                    "Please confirm this is the correct profile."
                ),
            })
            selected_url = resume_value.get("github_url") if isinstance(resume_value, dict) else url
            candidate = candidate.model_copy(update={"github_url": selected_url})
        else:
            logger.warning("Agent 1: Malformed GitHub profile URL found")
            resume_value = interrupt({
                "github_url": url,
                "scenario": "COULD_NOT_BE_ACCESSED",
                "candidate_name": candidate.full_name,
                "message": (
                    f"A GitHub URL was found ({url}) but it appears malformed. "
                    "Please provide the correct GitHub URL manually."
                ),
            })
            selected_url = resume_value.get("github_url") if isinstance(resume_value, dict) else None
            if selected_url:
                candidate = candidate.model_copy(update={"github_url": selected_url})

    else:
        normalised = [normalize_github_url(u) for u in github_urls]
        logger.info("Agent 1: Multiple GitHub profile URLs found : count=%s", len(normalised))
        resume_value = interrupt({
            "profiles": normalised,
            "scenario": "MULTIPLE_FOUND",
            "candidate_name": candidate.full_name,
            "message": (
                f"Multiple GitHub profiles found in this CV: {normalised}. "
                "Please select the correct one."
            ),
        })
        selected_url = resume_value.get("github_url") if isinstance(resume_value, dict) else None
        candidate = candidate.model_copy(update={"github_url": selected_url})

    return {
        "pdf_bytes": None,
        "pdf_temp_path": None,
        "raw_cv_text": raw_cv_text,
        "candidate": candidate.model_dump(mode="json"),
        "candidate_domain": candidate_domain,
        "candidate_domain_source": candidate_domain_source,
        "github_review_policy": None,
    }
