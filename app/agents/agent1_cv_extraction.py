import re
import logging
import tempfile
import os
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

logger = logging.getLogger("devselect")


class LlamaParseTimeoutError(Exception):
    pass


class GeminiTransientError(Exception):
    pass


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
async def _parse_pdf_with_llamaparse(pdf_bytes: bytes) -> str:
    try:
        parser = LlamaParse(
            api_key=settings.LLAMAPARSE_API_KEY,
            result_type="markdown",
            use_vendor_multimodal_model=False,
            language="en",
            verbose=False,
        )

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        try:
            documents = await parser.aload_data(tmp_path)
        finally:
            os.unlink(tmp_path)

        if not documents:
            raise ValueError("LlamaParse returned no documents.")

        markdown_text = "\n\n".join(doc.text for doc in documents)

        if not markdown_text.strip():
            raise ValueError("LlamaParse returned empty markdown.")

        return markdown_text

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"LlamaParse error: {e}")
        raise


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    retry=retry_if_exception_type(GeminiTransientError),
    reraise=True,
)
async def _extract_with_gemini(markdown_text: str) -> str:
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=settings.GEMINI_API_KEY,
        temperature=0.2,
        timeout=30,
        max_retries=0,
    )

    prompt = AGENT1_PROMPT.format(cv_text=markdown_text)

    try:
        response = await llm.ainvoke(prompt)
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

    if not state.get("pdf_bytes"):
        return {"error": "No PDF bytes found in state. Upload may have failed."}

    try:
        logger.info("Agent 1: Sending PDF to LlamaParse...")
        raw_cv_text = await _parse_pdf_with_llamaparse(state["pdf_bytes"])
        logger.info(f"Agent 1: LlamaParse returned {len(raw_cv_text)} characters")
    except Exception as e:
        logger.error(f"Agent 1 failed in Step A: {e}")
        return {
            "error": (
                "CV parsing failed after 2 attempts. "
                "Please check the PDF is not password-protected and try again."
            )
        }

    try:
        logger.info("Agent 1: Sending parsed text to Gemini...")
        raw_json_str = await _extract_with_gemini(raw_cv_text)
        logger.info("Agent 1: Gemini responded")
    except ValueError as e:
        return {"raw_cv_text": raw_cv_text, "error": str(e)}
    except Exception as e:
        logger.error(f"Agent 1 failed in Step B: {e}")
        return {
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
        logger.error(f"Agent 1 failed in Step C (JSON): {e}")
        return {
            "raw_cv_text": raw_cv_text,
            "error": "CV data extraction produced invalid output. Please try again.",
        }
    except Exception as e:
        logger.error(f"Agent 1 failed in Step C (Pydantic): {e}")
        return {
            "raw_cv_text": raw_cv_text,
            "error": f"CV data validation failed: {e}",
        }

    logger.info("Agent 1: Analysing GitHub URLs and calling interrupt()...")

    github_urls: list[str] = candidate.github_urls or []
    github_urls = [u for u in github_urls if "github.com" in u.lower()]

    partial_state = {
        "raw_cv_text": raw_cv_text,
        "candidate": candidate,
    }

    if len(github_urls) == 0:
        logger.info("Agent 1: No GitHub URLs found")
        interrupt({
            "github_url": None,
            "scenario": "NOT_FOUND",
            "candidate_name": candidate.full_name,
            "message": (
                "No GitHub profile was found in this CV. "
                "You can provide a GitHub URL manually or proceed without one."
            ),
        })

    elif len(github_urls) == 1:
        url = normalize_github_url(github_urls[0])
        if is_valid_github_url(url):
            logger.info(f"Agent 1: One valid URL found — {url}")
            interrupt({
                "github_url": url,
                "scenario": "ACCESSIBLE",
                "candidate_name": candidate.full_name,
                "message": (
                    f"GitHub profile found: {url}. "
                    "Please confirm this is the correct profile."
                ),
            })
        else:
            logger.warning(f"Agent 1: Malformed URL found — {url}")
            interrupt({
                "github_url": url,
                "scenario": "COULD_NOT_BE_ACCESSED",
                "candidate_name": candidate.full_name,
                "message": (
                    f"A GitHub URL was found ({url}) but it appears malformed. "
                    "Please provide the correct GitHub URL manually."
                ),
            })

    else:
        normalised = [normalize_github_url(u) for u in github_urls]
        logger.info(f"Agent 1: Multiple URLs found — {normalised}")
        interrupt({
            "profiles": normalised,
            "scenario": "MULTIPLE_FOUND",
            "candidate_name": candidate.full_name,
            "message": (
                f"Multiple GitHub profiles found in this CV: {normalised}. "
                "Please select the correct one."
            ),
        })

    return partial_state



            
 