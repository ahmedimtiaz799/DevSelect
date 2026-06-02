import re
import logging
import tempfile
import os
import asyncio
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.types import interrupt
from llama_parse import LlamaParse
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
from app.utils.json_parser import parse_llm_json
from app.utils.llm_observability import (
    cap_text_for_llm,
    estimate_tokens_from_text,
    log_llm_request,
    log_llm_usage,
)
from app.utils.cv_likeness import assess_cv_likeness

logger = logging.getLogger("devselect")
AGENT1_MODEL = "gemini-2.5-flash"
CV_NOT_LIKELY_MESSAGE = "This PDF does not look like a candidate CV. Please upload a CV or resume PDF."
CV_EXTRACTION_INVALID_MESSAGE = "This PDF could not be read as a candidate CV. Please upload a standard CV or resume PDF."


class LlamaParseTransientError(Exception):
    pass


class LlamaParseTimeoutError(Exception):
    pass


class GeminiTransientError(Exception):
    pass


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
            raise ValueError("LlamaParse returned no documents.")

        markdown_text = "\n\n".join(doc.text for doc in documents)

        if not markdown_text.strip():
            raise ValueError("LlamaParse returned empty markdown.")

        return markdown_text

    except asyncio.TimeoutError as e:
        logger.warning("LlamaParse timed out after %s seconds", settings.LLAMA_PARSE_TIMEOUT_SECONDS)
        raise LlamaParseTimeoutError("LlamaParse timed out.") from e
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"LlamaParse error: {e}")
        raise LlamaParseTransientError(f"LlamaParse transient error: {e}")


async def _parse_pdf_bytes_with_llamaparse(pdf_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name

    try:
        return await _parse_pdf_with_llamaparse(tmp_path)
    finally:
        _delete_file(tmp_path)


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
    retry=retry_if_exception_type(GeminiTransientError),
    reraise=True,
)
async def _extract_with_gemini(markdown_text: str, thread_id: str | None = None) -> str:
    llm = ChatGoogleGenerativeAI(
        model=AGENT1_MODEL,
        google_api_key=settings.GEMINI_API_KEY,
        temperature=0.2,
        max_tokens=settings.AGENT1_MAX_OUTPUT_TOKENS,
        request_timeout=settings.GEMINI_TIMEOUT_SECONDS,
        max_retries=0,
    )

    prompt = AGENT1_PROMPT.format(cv_text=markdown_text)
    estimated_input_tokens = estimate_tokens_from_text(prompt)

    try:
        log_llm_request(
            logger,
            "agent1",
            AGENT1_MODEL,
            thread_id,
            estimated_input_tokens,
            settings.AGENT1_MAX_OUTPUT_TOKENS,
        )
        response = await llm.ainvoke(prompt)
        log_llm_usage(logger, "agent1", AGENT1_MODEL, thread_id, response)
        return response.content
    except Exception as e:
        error_str = str(e).lower()
        if "429" in error_str or "quota" in error_str:
            raise ValueError(
                "Gemini API rate limit exceeded. Please try again in a few minutes."
            )
        raise GeminiTransientError(f"Gemini API error: {e}")


def is_valid_github_url(url: str) -> bool:
    pattern = r'^(https?://)?github\.com/[a-zA-Z0-9_.-]+(/[a-zA-Z0-9_.\-]*)?$'
    return bool(re.match(pattern, url.strip()))


def normalize_github_url(url: str) -> str:
    url = url.strip()
    if not url.startswith("http"):
        url = "https://" + url
    return url


async def agent1_cv_extraction(state: DevSelectState) -> dict[str, Any]:
    logger.info(f"Agent 1 starting for thread_id={state['thread_id']}")

    if state.get("error"):
        logger.warning("Agent 1 skipping — error already set in state.")
        return {}

    pdf_temp_path = state.get("pdf_temp_path")
    pdf_bytes = state.get("pdf_bytes")

    if not pdf_temp_path and not pdf_bytes:
        return {"error": "No PDF bytes found in state. Upload may have failed."}

    try:
        logger.info("Agent 1: Sending PDF to LlamaParse...")
        if pdf_temp_path:
            raw_cv_text = await _parse_pdf_with_llamaparse(pdf_temp_path)
        else:
            raw_cv_text = await _parse_pdf_bytes_with_llamaparse(pdf_bytes)
        logger.info(f"Agent 1: LlamaParse returned {len(raw_cv_text)} characters")
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
    except Exception as e:
        logger.error(f"Agent 1 failed in Step A: {e}")
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
        logger.info("Agent 1: Sending parsed text to Gemini...")
        raw_json_str = await _extract_with_gemini(
            gemini_cv_text,
            thread_id=state["thread_id"],
        )
        logger.info("Agent 1: Gemini responded")
    except ValueError as e:
        return {"pdf_bytes": None, "pdf_temp_path": None, "raw_cv_text": raw_cv_text, "error": str(e)}
    except Exception as e:
        logger.error(f"Agent 1 failed in Step B: {e}")
        return {
            "pdf_bytes": None,
            "pdf_temp_path": None,
            "raw_cv_text": raw_cv_text,
            "error": (
                "CV analysis failed after 2 attempts. "
                "Please try again in a few minutes."
            ),
        }

    try:
        logger.info("Agent 1: Parsing and validating Gemini response...")
        parsed_dict = parse_llm_json(raw_json_str)
        candidate = CandidateExtraction(**parsed_dict)
        logger.info(f"Agent 1: Extracted candidate — {candidate.full_name}")
    except ValueError as e:
        logger.error(
            "Agent 1 failed in Step C (JSON): error_type=%s response_chars=%s",
            type(e).__name__,
            len(raw_json_str) if isinstance(raw_json_str, str) else 0,
        )
        return {
            "pdf_bytes": None,
            "pdf_temp_path": None,
            "raw_cv_text": raw_cv_text,
            "error": CV_EXTRACTION_INVALID_MESSAGE,
            "error_code": "CV_EXTRACTION_INVALID",
        }
    except Exception as e:
        logger.error(
            "Agent 1 failed in Step C (Pydantic): error_type=%s response_chars=%s",
            type(e).__name__,
            len(raw_json_str) if isinstance(raw_json_str, str) else 0,
        )
        return {
            "pdf_bytes": None,
            "pdf_temp_path": None,
            "raw_cv_text": raw_cv_text,
            "error": CV_EXTRACTION_INVALID_MESSAGE,
            "error_code": "CV_EXTRACTION_INVALID",
        }

    logger.info("Agent 1: Analysing GitHub URLs and calling interrupt()...")

    github_urls: list[str] = candidate.github_urls or []
    github_urls = [u for u in github_urls if "github.com" in u.lower()]

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
            logger.info(f"Agent 1: One valid URL found — {url}")
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
            logger.warning(f"Agent 1: Malformed URL found — {url}")
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
        logger.info(f"Agent 1: Multiple URLs found — {normalised}")
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
        "candidate": candidate,
    }
