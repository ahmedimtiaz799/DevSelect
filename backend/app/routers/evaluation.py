from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Optional, AsyncGenerator
from uuid import uuid4
import asyncio
import json
import urllib.parse
import logging
import re
import os
import tempfile
from datetime import datetime
from io import BytesIO
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from langgraph.types import Command
from psycopg import InterfaceError, OperationalError

from app.agents.follow_up import (
    FollowUpAnswerIncompleteError,
    answer_follow_up_question,
    mock_follow_up_answer,
)
from app.agents.agent3_lead_evaluator import GeminiQuotaExceededError
from app.config import settings
from app.db.supabase_client import get_supabase
from app.dependencies import verify_token
from app.models.requests import FollowUpRequest, ResumeRequest
from app.utils.budget_limits import (
    budget_error_payload,
    budget_error_status_code,
    estimate_evaluation_budget,
    record_budget_usage,
)
from app.utils.cv_likeness import assess_cv_likeness
from app.utils.candidate_domain import resolve_candidate_display_role
from app.utils.llm_observability import cap_text_for_llm
from app.utils.llm_provider import LLMProviderUnavailableError

logger = logging.getLogger("devselect")

router = APIRouter(prefix="/api/chat", tags=["evaluation"])

EVALUATION_PENDING = "pending"
EVALUATION_IN_PROGRESS = "in_progress"
EVALUATION_COMPLETED = "completed"
EVALUATION_STOPPED = "stopped"
EVALUATION_FAILED = "failed"
UNKNOWN_CANDIDATE = "Unknown Candidate"
UNKNOWN_ROLE_VALUES = {
    "unknown role",
    "unknown title",
    "not detected",
    "not found",
    "n/a",
    "na",
    "none",
    "null",
}
DETECTED_ROLE_PATTERN = re.compile(
    r"^\s*\*{0,2}Detected Role\s*(?::\*{0,2}|\*{0,2}:)\s*(.+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
MOCK_META = {
    "candidate_name": "Ahmed Imtiaz",
    "role": "Full Stack AI Engineer",
}
MOCK_RESUME_PAYLOAD = {
    "scenario": "MOCK",
    "github_url": None,
}
MOCK_STATUSES = [
    "Analyzing CV...",
    "Checking GitHub Repository...",
    "Generating Recommendation...",
]
MOCK_REPORT = """
## Candidate Overview
Ahmed Imtiaz is presented as a Full Stack AI Engineer with strong practical experience across frontend, backend, AI integration, and product-focused delivery.

## CV & Experience Review
The CV shows a balanced profile with modern JavaScript, React, Python, FastAPI, API design, and AI-assisted application development. The experience reads as hands-on and implementation-heavy, with evidence of building usable systems rather than only prototypes.

## GitHub Profile Review
The mocked GitHub review indicates active project work, readable repository structure, and practical use of full-stack patterns. Repository signals suggest good ownership habits, with room to improve documentation depth and test coverage visibility.

## Skill Match Assessment
The candidate appears well aligned for roles requiring React, FastAPI, Python, database-backed APIs, authentication flows, SSE streaming, and AI product integration. The strongest match is for full-stack AI application engineering.

## Red Flags
- Testing depth is not fully proven from the available summary.
- Production observability and deployment ownership should be discussed in interview.
- Security review habits should be validated with scenario-based questions.

## Strengths
- Strong full-stack implementation range.
- Comfortable working across frontend state, backend APIs, and AI workflows.
- Clear evidence of practical product-building instincts.
- Good fit for teams building AI-assisted internal tools or SaaS workflows.

## Hiring Recommendation
Recommend moving Ahmed Imtiaz to the next interview stage for a Full Stack AI Engineer role. The profile is promising, especially if the team values builders who can move across the application stack and integrate AI systems responsibly.

## Suggested Next Steps
1. Run a technical interview focused on FastAPI, React state management, and streaming UX.
2. Ask for a walkthrough of one shipped project and the tradeoffs behind it.
3. Include a short debugging exercise around API failure handling.
4. Validate testing, deployment, and security ownership through practical questions.
""".strip()
ACTIVE_STREAM_THREADS: set[str] = set()
MOCK_EVALUATION_RUNS: dict[str, dict] = {}
EVALUATION_GUARD_LOCK = asyncio.Lock()
CHECKPOINT_STATE_READ_ATTEMPTS = 2
CHECKPOINT_STATE_READ_RETRY_DELAY_SECONDS = 0.25
RECRUITER_INSTRUCTION_MAX_CHARS = settings.MAX_USER_INPUT_CHARS
PRE_CV_GUIDANCE_MESSAGE = "Please upload a candidate CV to begin an evaluation."
FOLLOW_UP_REQUIRES_REPORT_MESSAGE = "A completed evaluation is required before follow-up questions."
EVALUATION_RESTORE_FAILED_MESSAGE = "This evaluation session could not be restored. Please upload the CV again."
REPORT_CONTEXT_HINTS = (
    "Candidate Overview",
    "Hiring Recommendation",
    "Skill Match Assessment",
    "Detected Role",
)
ASSISTANT_MESSAGE_PREFIX = "__DEVSELECT_ASSISTANT_MESSAGE__"
EVALUATION_REPORT_MESSAGE_TYPE = "evaluation_report"
MAX_CV_UPLOAD_BYTES = 10 * 1024 * 1024
PDF_HEADER_READ_BYTES = 32
CHAT_ACCESS_DENIED_MESSAGE = "You do not have access to this chat."
EVALUATION_SESSION_UNAVAILABLE_MESSAGE = "This evaluation session is no longer available. Please start a new evaluation."
EVALUATION_STATE_TEMPORARILY_UNAVAILABLE_MESSAGE = "Evaluation state is temporarily unavailable. Please try again."
UPLOAD_SECURITY_MESSAGES = {
    "INVALID_FILE_TYPE": "Please upload a valid PDF CV under 10 MB.",
    "FILE_TOO_LARGE": "Please upload a valid PDF CV under 10 MB.",
    "INVALID_PDF": "This file could not be processed safely. Please upload a standard PDF CV.",
    "ENCRYPTED_PDF": "This PDF is password-protected or encrypted. Please upload an unlocked PDF CV.",
    "PDF_TOO_LONG": "This PDF is too long for evaluation.",
    "PDF_PARSE_TIMEOUT": "This file took too long to process. Please upload a standard PDF CV.",
    "PDF_PROCESSING_FAILED": "This file could not be processed safely. Please upload a standard PDF CV.",
    "NOT_A_CV": "This PDF does not look like a candidate CV. Please upload a CV or resume PDF.",
    "CV_EXTRACTION_INVALID": "This PDF could not be read as a candidate CV. Please upload a standard CV or resume PDF.",
}


class UploadSecurityError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _upload_security_response(code: str, status_code: int = 400) -> JSONResponse:
    error = (
        f"This PDF is too long for evaluation. Please upload a CV under {settings.MAX_CV_PDF_PAGES} pages."
        if code == "PDF_TOO_LONG"
        else UPLOAD_SECURITY_MESSAGES.get(
            code,
            UPLOAD_SECURITY_MESSAGES["PDF_PROCESSING_FAILED"],
        )
    )

    return JSONResponse(
        status_code=status_code,
        content={
            "error": error,
            "code": code,
        },
    )


def _safe_upload_name(filename: str | None) -> str:
    original_name = filename or "upload.pdf"
    safe_name = "".join(
        c for c in original_name
        if c.isalnum() or c in ("-", "_", ".")
    )
    safe_name = safe_name[:100]
    return safe_name or "upload.pdf"


def _has_pdf_header(prefix: bytes) -> bool:
    return prefix.lstrip(b" \t\r\n\f").startswith(b"%PDF-")


def _validate_pdf_structure(pdf_bytes: bytes) -> None:
    try:
        from pypdf import PdfReader
    except ImportError as e:
        logger.error("PDF validation dependency missing: pypdf")
        raise UploadSecurityError("PDF_PROCESSING_FAILED") from e

    try:
        reader = PdfReader(BytesIO(pdf_bytes), strict=False)
        if reader.is_encrypted:
            raise UploadSecurityError("ENCRYPTED_PDF")

        page_count = len(reader.pages)
    except UploadSecurityError:
        raise
    except Exception as e:
        logger.warning(
            "PDF structural validation failed : bytes=%s error_type=%s",
            len(pdf_bytes),
            type(e).__name__,
        )
        raise UploadSecurityError("INVALID_PDF") from e

    if page_count <= 0:
        raise UploadSecurityError("INVALID_PDF")

    if page_count > settings.MAX_CV_PDF_PAGES:
        logger.info(
            "PDF rejected by page limit : pages=%s max_pages=%s bytes=%s",
            page_count,
            settings.MAX_CV_PDF_PAGES,
            len(pdf_bytes),
        )
        raise UploadSecurityError("PDF_TOO_LONG")


def _extract_pdf_preview_text(pdf_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""

    try:
        reader = PdfReader(BytesIO(pdf_bytes), strict=False)
    except Exception as e:
        logger.warning("PDF preview text extraction failed : error_type=%s", type(e).__name__)
        return ""

    text_parts = []
    max_pages = max(1, settings.CV_LIKENESS_MAX_PAGES_TO_SCAN)
    page_count = min(len(reader.pages), max_pages)

    for index in range(page_count):
        try:
            text_parts.append(reader.pages[index].extract_text() or "")
        except Exception as e:
            logger.warning(
                "PDF preview text page extraction failed : page=%s error_type=%s",
                index + 1,
                type(e).__name__,
            )

    return "\n".join(text_parts)


def _run_cv_likeness_precheck(pdf_bytes: bytes) -> str:
    if not settings.ENABLE_CV_LIKENESS_CHECK:
        return ""

    preview_text = _extract_pdf_preview_text(pdf_bytes)
    assessment = assess_cv_likeness(
        preview_text,
        min_text_chars=settings.CV_LIKENESS_MIN_TEXT_CHARS,
        min_score=settings.CV_LIKENESS_MIN_SCORE,
    )
    logger.info(
        "CV likeness precheck : text_chars=%s score=%s negative_score=%s categories=%s negative_categories=%s low_text=%s reject=%s decision_reason=%s",
        assessment["text_chars"],
        assessment["score"],
        assessment["negative_score"],
        ",".join(assessment["signal_categories"]) or "none",
        ",".join(assessment["negative_categories"]) or "none",
        assessment["low_text"],
        assessment["should_reject"],
        assessment.get("decision_reason", "unknown"),
    )

    if assessment["should_reject"]:
        raise UploadSecurityError("NOT_A_CV")

    return preview_text


def _write_temp_pdf(pdf_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        return tmp.name


def _delete_temp_file(path: str | None) -> None:
    if not path:
        return

    try:
        os.unlink(path)
    except FileNotFoundError:
        return
    except Exception as e:
        logger.warning("Temporary PDF cleanup failed : error_type=%s", type(e).__name__)


def _field(value, name: str):
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)


def _clean_text(value) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _normalize_recruiter_instruction(value) -> str | None:
    instruction = _clean_text(value)
    if not instruction:
        return None

    capped, original_chars, capped_chars, was_truncated = cap_text_for_llm(
        instruction,
        RECRUITER_INSTRUCTION_MAX_CHARS,
    )
    logger.info(
        "Recruiter instruction received : provided=%s original_chars=%s capped_chars=%s truncated=%s",
        True,
        original_chars,
        capped_chars,
        was_truncated,
    )
    return capped or None


def _load_timezone(timezone_name: str | None) -> ZoneInfo | None:
    clean_timezone = _clean_text(timezone_name)
    if not clean_timezone or len(clean_timezone) > 128:
        return None

    try:
        return ZoneInfo(clean_timezone)
    except (ZoneInfoNotFoundError, ValueError):
        return None


def _evaluation_datetime_context(client_timezone: str | None = None) -> dict[str, str]:
    client_timezone_name = _clean_text(client_timezone)
    client_zoneinfo = _load_timezone(client_timezone_name)
    used_client_timezone = client_zoneinfo is not None

    timezone_name = client_timezone_name if used_client_timezone else settings.EVALUATION_TIMEZONE
    timezone_info = client_zoneinfo or _load_timezone(timezone_name)

    if timezone_info is None:
        logger.warning("Invalid fallback evaluation timezone configured : timezone=%s", timezone_name)
        timezone_name = "UTC"
        timezone_info = ZoneInfo(timezone_name)

    evaluation_datetime = datetime.now(timezone_info)

    return {
        "evaluation_date": evaluation_datetime.date().isoformat(),
        "evaluation_timezone": timezone_name,
        "evaluation_datetime_iso": evaluation_datetime.isoformat(),
        "evaluation_timezone_source": "browser" if used_client_timezone else "fallback",
    }


def _known_role(value) -> str | None:
    role = _clean_text(value)
    if not role or role.lower() in UNKNOWN_ROLE_VALUES:
        return None

    return role


def _candidate_role(candidate, raw_cv_text: str | None = None) -> str | None:
    role = _known_role(resolve_candidate_display_role(candidate, raw_cv_text))
    if role:
        return role

    role = _known_role(_field(candidate, "current_title"))
    if role:
        return role

    for experience in (_field(candidate, "work_experience") or []):
        role = _known_role(_field(experience, "title"))
        if role:
            return role

    return None


def _report_role(report: str | None) -> str | None:
    if not report:
        return None

    match = DETECTED_ROLE_PATTERN.search(report)
    if not match:
        return None

    role = re.sub(r"[*_`]+", "", match.group(1)).strip()
    return _known_role(role)


def _meta_from_tasks(tasks) -> dict:
    meta = {}

    for task in (tasks or []):
        for interrupt_obj in (getattr(task, "interrupts", None) or []):
            interrupt_val = getattr(interrupt_obj, "value", None)
            if not isinstance(interrupt_val, dict):
                continue

            name = _clean_text(interrupt_val.get("candidate_name"))
            role = (
                _known_role(interrupt_val.get("role"))
                or _known_role(interrupt_val.get("candidate_role"))
                or _known_role(interrupt_val.get("current_title"))
            )

            if name:
                meta["candidate_name"] = name
            if role:
                meta["role"] = role

            if meta:
                return meta

    return meta


def _candidate_meta(values: dict | None, tasks=None) -> dict:
    values = values or {}
    candidate = values.get("candidate")
    meta = {}

    if candidate:
        name = _clean_text(_field(candidate, "full_name"))
        role = _candidate_role(
            candidate,
            values.get("raw_cv_text") or values.get("pdf_preview_text"),
        )

        if name:
            meta["candidate_name"] = name
        if role:
            meta["role"] = role

    task_meta = _meta_from_tasks(tasks)
    meta = {
        **task_meta,
        **meta,
    }

    return {
        "candidate_name": meta.get("candidate_name") or UNKNOWN_CANDIDATE,
        "role": meta.get("role"),
    }


def _meta_changed(current: dict, previous: dict) -> bool:
    if current.get("role") and current.get("role") != previous.get("role"):
        return True

    return (
        current.get("candidate_name") != previous.get("candidate_name")
        and current.get("candidate_name") != UNKNOWN_CANDIDATE
    )


def _meta_with_report_role(meta: dict, report: str | None) -> dict:
    report_role = _report_role(report)
    if not report_role:
        return meta

    return {
        "candidate_name": meta.get("candidate_name") or UNKNOWN_CANDIDATE,
        "role": report_role,
    }


def _evaluation_status(values: dict | None) -> str:
    values = values or {}
    status = values.get("evaluation_status")

    if status in {
        EVALUATION_IN_PROGRESS,
        EVALUATION_COMPLETED,
        EVALUATION_STOPPED,
        EVALUATION_FAILED,
    }:
        return status

    if values.get("report"):
        return EVALUATION_COMPLETED

    if values.get("error"):
        return EVALUATION_FAILED

    return EVALUATION_PENDING


def _is_completed_report_content(content: str | None) -> bool:
    if not content:
        return False

    text = str(content).strip()
    if not text or text == PRE_CV_GUIDANCE_MESSAGE:
        return False

    if text in {
        "Evaluation failed. Please try again.",
        "Evaluation stopped unexpectedly. Please try again.",
        "Gemini quota reached. Please wait and try again.",
        "Gemini is temporarily rate-limited. Please try again in a few minutes.",
        "Groq is temporarily rate-limited. Please try again in a few minutes.",
        "The AI provider is temporarily rate-limited. Please try again in a few minutes.",
    }:
        return False

    return len(text) >= 500 or any(hint in text for hint in REPORT_CONTEXT_HINTS)


def _assistant_message_content(content: str | None) -> tuple[str, str | None]:
    if not isinstance(content, str):
        return "", None

    text = content.strip()
    if not text.startswith(ASSISTANT_MESSAGE_PREFIX):
        return text, None

    try:
        payload = json.loads(text[len(ASSISTANT_MESSAGE_PREFIX):])
    except (json.JSONDecodeError, TypeError):
        return "", None

    if not isinstance(payload, dict):
        return "", None

    message_text = payload.get("content")
    message_type = payload.get("message_type") or payload.get("kind")

    return (
        message_text.strip() if isinstance(message_text, str) else "",
        _clean_text(message_type),
    )


def _completed_report_from_messages(messages: list[dict]) -> str | None:
    explicit_report = None
    candidates = []

    for message in messages:
        if message.get("role") != "assistant":
            continue

        content, message_type = _assistant_message_content(message.get("content"))

        if message_type == EVALUATION_REPORT_MESSAGE_TYPE and content:
            explicit_report = content
            continue

        if message_type:
            continue

        if not _is_completed_report_content(content):
            continue

        hint_score = sum(1 for hint in REPORT_CONTEXT_HINTS if hint in content)
        candidates.append((hint_score, len(content), content))

    if explicit_report:
        return explicit_report

    if not candidates:
        return None

    candidates.sort(reverse=True)
    return candidates[0][2]


async def _load_completed_report_for_chat(chat_id: str, user_id: str) -> str | None:
    chat = await _get_owned_chat(chat_id, user_id, raise_on_missing=False)
    if not chat:
        return None

    supabase = await get_supabase()
    messages_result = await (
        supabase.table("messages")
        .select("role,content,created_at")
        .eq("chat_id", chat_id)
        .eq("role", "assistant")
        .order("created_at", desc=False)
        .execute()
    )
    return _completed_report_from_messages(getattr(messages_result, "data", None) or [])


async def _get_owned_chat(chat_id: str, user_id: str, raise_on_missing: bool = True) -> dict | None:
    try:
        supabase = await get_supabase()
        chat_result = await (
            supabase.table("chats")
            .select("id,user_id,thread_id")
            .eq("id", chat_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
    except Exception as e:
        logger.error("Chat ownership lookup failed : chat=%s user=%s error_type=%s", chat_id, user_id, type(e).__name__)
        raise HTTPException(status_code=500, detail="Chat access could not be verified. Please try again.") from e

    rows = getattr(chat_result, "data", None) or []
    if rows:
        return rows[0]

    logger.warning("Chat ownership denied : chat=%s user=%s", chat_id, user_id)
    if raise_on_missing:
        raise HTTPException(status_code=403, detail=CHAT_ACCESS_DENIED_MESSAGE)

    return None


def _chat_thread_id(chat: dict | None) -> str | None:
    if not chat:
        return None

    return _clean_text(chat.get("thread_id"))


def _assert_chat_thread(chat: dict, thread_id: str) -> None:
    stored_thread_id = _chat_thread_id(chat)
    requested_thread_id = _clean_text(thread_id)

    if stored_thread_id and requested_thread_id == stored_thread_id:
        return

    logger.warning(
        "Evaluation thread access denied : chat=%s has_stored_thread=%s has_requested_thread=%s",
        chat.get("id"),
        bool(stored_thread_id),
        bool(requested_thread_id),
    )
    raise HTTPException(status_code=403, detail=EVALUATION_SESSION_UNAVAILABLE_MESSAGE)


async def _save_chat_thread_id(chat_id: str, user_id: str, thread_id: str) -> dict:
    try:
        supabase = await get_supabase()
        await (
            supabase.table("chats")
            .update({"thread_id": thread_id})
            .eq("id", chat_id)
            .eq("user_id", user_id)
            .execute()
        )
        verify_result = await (
            supabase.table("chats")
            .select("id,user_id,thread_id")
            .eq("id", chat_id)
            .eq("user_id", user_id)
            .eq("thread_id", thread_id)
            .execute()
        )
    except Exception as e:
        logger.error("Chat thread binding failed : chat=%s user=%s error_type=%s", chat_id, user_id, type(e).__name__)
        raise HTTPException(status_code=500, detail="Evaluation session could not be prepared. Please try again.") from e

    rows = getattr(verify_result, "data", None) or []
    if not rows:
        logger.warning("Chat thread binding denied : chat=%s user=%s", chat_id, user_id)
        raise HTTPException(status_code=403, detail=CHAT_ACCESS_DENIED_MESSAGE)

    return rows[0]


def _thread_terminal_error_payload(status: str) -> dict:
    if status == EVALUATION_COMPLETED:
        return {
            "error": "Evaluation is already completed.",
            "code": "EVALUATION_ALREADY_COMPLETED",
        }

    if status == EVALUATION_IN_PROGRESS:
        return {
            "error": "Evaluation is already in progress. Please wait for it to finish.",
            "code": "EVALUATION_ALREADY_IN_PROGRESS",
        }

    if status == EVALUATION_STOPPED:
        return {
            "error": "Evaluation was stopped. Please upload the CV again to start a new evaluation.",
            "code": "EVALUATION_STOPPED",
        }

    if status == EVALUATION_FAILED:
        return {
            "error": "Evaluation already failed. Please upload the CV again to retry.",
            "code": "EVALUATION_ALREADY_FAILED",
        }

    return {
        "error": "Evaluation is not ready to stream. Please upload the CV again.",
        "code": "EVALUATION_NOT_READY",
    }


def _sse_response(generator: AsyncGenerator[str, None]) -> StreamingResponse:
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


async def _single_error_stream(payload: dict) -> AsyncGenerator[str, None]:
    yield f"event: error\ndata: {json.dumps(payload)}\n\n"


async def _cached_report_stream_generator(
    request: Request,
    thread_id: str,
    meta: dict,
    report: str,
) -> AsyncGenerator[str, None]:
    if await request.is_disconnected():
        logger.info(f"Cached SSE client disconnected before stream start : thread={thread_id}")
        return

    cached_meta = _meta_with_report_role(meta, report)
    yield f"event: meta\ndata: {json.dumps(cached_meta)}\n\n"
    yield f"event: status\ndata: {json.dumps({'text': 'Generating Recommendation...'})}\n\n"
    logger.info(f"Cached SSE stream started : thread={thread_id}")

    for char in report:
        if await request.is_disconnected():
            logger.info(f"Cached SSE client disconnected during token stream : thread={thread_id}")
            return

        yield f"event: token\ndata: {json.dumps({'text': char})}\n\n"

    yield f"event: done\ndata: {json.dumps({})}\n\n"
    logger.info(f"Cached SSE stream completed : thread={thread_id}")


async def _claim_stream_thread(thread_id: str, chat_id: str | None = None) -> bool:
    async with EVALUATION_GUARD_LOCK:
        if thread_id in ACTIVE_STREAM_THREADS:
            logger.info(
                "Stream lock acquisition rejected : chat=%s thread=%s acquired=%s active_count=%s",
                chat_id or "unknown",
                thread_id,
                False,
                len(ACTIVE_STREAM_THREADS),
            )
            return False

        ACTIVE_STREAM_THREADS.add(thread_id)
        logger.info(
            "Stream lock acquired : chat=%s thread=%s acquired=%s active_count=%s",
            chat_id or "unknown",
            thread_id,
            True,
            len(ACTIVE_STREAM_THREADS),
        )
        return True


async def _release_stream_thread(
    thread_id: str,
    reason: str = "unknown",
    chat_id: str | None = None,
) -> None:
    async with EVALUATION_GUARD_LOCK:
        was_active = thread_id in ACTIVE_STREAM_THREADS
        ACTIVE_STREAM_THREADS.discard(thread_id)
        logger.info(
            "Stream lock released : chat=%s thread=%s was_active=%s reason=%s active_count=%s",
            chat_id or "unknown",
            thread_id,
            was_active,
            reason,
            len(ACTIVE_STREAM_THREADS),
        )


async def _set_graph_evaluation_status(graph, thread_id: str, status: str) -> None:
    update_state = getattr(graph, "aupdate_state", None)
    if update_state is None:
        return

    try:
        await update_state(
            {"configurable": {"thread_id": thread_id}},
            {"evaluation_status": status},
        )
    except Exception as e:
        logger.warning("Evaluation status update failed : thread=%s status=%s error_type=%s", thread_id, status, type(e).__name__)


def _is_checkpoint_connection_error(error: Exception) -> bool:
    if isinstance(error, (OperationalError, InterfaceError)):
        return True

    error_text = str(error).lower()
    return any(
        marker in error_text
        for marker in (
            "server closed the connection unexpectedly",
            "connection is closed",
            "closed connection",
            "bad connection",
            "consuming input failed",
        )
    )


async def _read_graph_state_with_retry(graph, thread_id: str, operation_name: str):
    config = {"configurable": {"thread_id": thread_id}}
    last_error = None

    for attempt in range(1, CHECKPOINT_STATE_READ_ATTEMPTS + 1):
        try:
            snapshot = await graph.aget_state(config)
            if attempt > 1:
                logger.info(
                    "Checkpoint state read retry succeeded : thread=%s operation=%s attempt=%s",
                    thread_id,
                    operation_name,
                    attempt,
                )
            return snapshot
        except Exception as e:
            last_error = e
            retryable = _is_checkpoint_connection_error(e)
            should_retry = retryable and attempt < CHECKPOINT_STATE_READ_ATTEMPTS
            logger.warning(
                "Checkpoint state read failed : thread=%s operation=%s attempt=%s error_type=%s retryable=%s retry_attempted=%s",
                thread_id,
                operation_name,
                attempt,
                type(e).__name__,
                retryable,
                should_retry,
            )
            if not should_retry:
                break
            await asyncio.sleep(CHECKPOINT_STATE_READ_RETRY_DELAY_SECONDS)

    raise last_error


async def _graph_thread_has_state(graph, thread_id: str) -> bool:
    try:
        snapshot = await _read_graph_state_with_retry(
            graph,
            thread_id,
            "checkpoint_existence_check",
        )
    except Exception as e:
        logger.error(
            "Checkpoint existence check failed : thread=%s error_type=%s",
            thread_id,
            type(e).__name__,
        )
        raise HTTPException(
            status_code=503,
            detail=EVALUATION_STATE_TEMPORARILY_UNAVAILABLE_MESSAGE,
        ) from e

    return bool(snapshot and snapshot.values)


async def _prepare_mock_thread(thread_id: str) -> str:
    async with EVALUATION_GUARD_LOCK:
        if thread_id in MOCK_EVALUATION_RUNS:
            new_thread_id = str(uuid4())
            logger.info(f"Mock upload requested existing thread : old={thread_id} new={new_thread_id}")
            thread_id = new_thread_id

        MOCK_EVALUATION_RUNS[thread_id] = {
            "status": EVALUATION_PENDING,
            "report": None,
            "meta": MOCK_META,
        }
        return thread_id


async def _mock_run_status(thread_id: str) -> str:
    async with EVALUATION_GUARD_LOCK:
        run = MOCK_EVALUATION_RUNS.get(thread_id)
        if not run:
            return EVALUATION_PENDING

        return run.get("status") or EVALUATION_PENDING


async def _mock_run_exists(thread_id: str) -> bool:
    async with EVALUATION_GUARD_LOCK:
        return thread_id in MOCK_EVALUATION_RUNS


async def _mock_run_report(thread_id: str) -> str | None:
    async with EVALUATION_GUARD_LOCK:
        run = MOCK_EVALUATION_RUNS.get(thread_id)
        if not run:
            return None

        return run.get("report")


async def _set_mock_run_status(
    thread_id: str,
    status: str,
    report: str | None = None,
) -> None:
    async with EVALUATION_GUARD_LOCK:
        run = MOCK_EVALUATION_RUNS.setdefault(
            thread_id,
            {
                "status": EVALUATION_PENDING,
                "report": None,
                "meta": MOCK_META,
            },
        )
        run["status"] = status
        if report is not None:
            run["report"] = report
            run["meta"] = MOCK_META


def _mock_token_chunks(text: str) -> list[str]:
    return re.findall(r"\S+\s*", text)


async def mock_evaluation_stream_generator(
    request: Request,
    thread_id: str,
) -> AsyncGenerator[str, None]:
    if await request.is_disconnected():
        logger.info(f"Mock SSE client disconnected before stream start : thread={thread_id}")
        await _set_mock_run_status(thread_id, EVALUATION_STOPPED)
        await _release_stream_thread(thread_id, reason="mock_prestart_disconnect")
        return

    try:
        await _set_mock_run_status(thread_id, EVALUATION_IN_PROGRESS)
        yield f"event: meta\ndata: {json.dumps(MOCK_META)}\n\n"
        logger.info(f"Mock SSE stream started : thread={thread_id}")
        await asyncio.sleep(0.25)

        for status in MOCK_STATUSES:
            if await request.is_disconnected():
                logger.info(f"Mock SSE client disconnected during status stream : thread={thread_id}")
                await _set_mock_run_status(thread_id, EVALUATION_STOPPED)
                return

            yield f"event: status\ndata: {json.dumps({'text': status})}\n\n"
            await asyncio.sleep(0.35)

        for chunk in _mock_token_chunks(MOCK_REPORT):
            if await request.is_disconnected():
                logger.info(f"Mock SSE client disconnected during token stream : thread={thread_id}")
                await _set_mock_run_status(thread_id, EVALUATION_STOPPED)
                return

            yield f"event: token\ndata: {json.dumps({'text': chunk})}\n\n"
            await asyncio.sleep(0.025)

        if await request.is_disconnected():
            logger.info(f"Mock SSE client disconnected before done : thread={thread_id}")
            await _set_mock_run_status(thread_id, EVALUATION_STOPPED)
            return

        await _set_mock_run_status(thread_id, EVALUATION_COMPLETED, report=MOCK_REPORT)
        yield f"event: done\ndata: {json.dumps({})}\n\n"
        logger.info(f"Mock SSE stream completed : thread={thread_id}")
    except asyncio.CancelledError:
        await _set_mock_run_status(thread_id, EVALUATION_STOPPED)
        logger.info(f"Mock SSE stream cancelled : thread={thread_id}")
        return
    except Exception:
        await _set_mock_run_status(thread_id, EVALUATION_FAILED)
        raise
    finally:
        await _release_stream_thread(thread_id, reason="mock_stream_finally")


@router.post("/{chat_id}/upload")
async def upload_cv(
    chat_id: str,
    request: Request,
    file: UploadFile = File(...),
    thread_id: Optional[str] = Form(None),
    recruiter_instruction: Optional[str] = Form(None),
    evaluation_timezone: Optional[str] = Form(None),
    user_id: str = Depends(verify_token),
):
    owned_chat = await _get_owned_chat(chat_id, user_id)

    if file.size and file.size > MAX_CV_UPLOAD_BYTES:
        return _upload_security_response("FILE_TOO_LARGE")

    safe_name = _safe_upload_name(file.filename)
    if not safe_name.lower().endswith(".pdf"):
        return _upload_security_response("INVALID_FILE_TYPE")

    if file.content_type != "application/pdf":
        return _upload_security_response("INVALID_FILE_TYPE")

    header = await file.read(PDF_HEADER_READ_BYTES)
    if not _has_pdf_header(header):
        return _upload_security_response("INVALID_PDF")

    await file.seek(0)
    pdf_bytes = await file.read()
    if len(pdf_bytes) > MAX_CV_UPLOAD_BYTES:
        return _upload_security_response("FILE_TOO_LARGE")

    try:
        _validate_pdf_structure(pdf_bytes)
        pdf_preview_text = _run_cv_likeness_precheck(pdf_bytes)
    except UploadSecurityError as e:
        return _upload_security_response(e.code)

    normalized_recruiter_instruction = _normalize_recruiter_instruction(recruiter_instruction)
    if not normalized_recruiter_instruction:
        logger.info("Recruiter instruction received : provided=%s chars=%s", False, 0)

    stored_thread_id = _chat_thread_id(owned_chat)
    if stored_thread_id and thread_id and thread_id != stored_thread_id:
        raise HTTPException(status_code=403, detail=EVALUATION_SESSION_UNAVAILABLE_MESSAGE)

    thread_id = stored_thread_id or thread_id or str(uuid4())

    if settings.DEV_MOCK_EVALUATION:
        thread_id = await _prepare_mock_thread(thread_id)
        await _save_chat_thread_id(chat_id, user_id, thread_id)
        logger.info(f"Mock evaluation upload accepted : thread={thread_id}")
        return JSONResponse(
            status_code=200,
            content={
                "thread_id": thread_id,
                "status": "ready_to_stream",
                "resume_payload": MOCK_RESUME_PAYLOAD,
            },
        )

    graph = request.app.state.graph
    if await _graph_thread_has_state(graph, thread_id):
        old_thread_id = thread_id
        thread_id = str(uuid4())
        logger.info(f"Upload requested existing thread : old={old_thread_id} new={thread_id}")

    await _save_chat_thread_id(chat_id, user_id, thread_id)

    estimated_budget_tokens = estimate_evaluation_budget(len(pdf_bytes))
    budget_decision = await record_budget_usage(user_id, estimated_budget_tokens)
    if not budget_decision.allowed:
        logger.warning(
            "Evaluation budget blocked before start : user=%s thread=%s code=%s estimated_tokens=%s",
            user_id,
            thread_id,
            budget_decision.code,
            budget_decision.estimated_tokens,
        )
        return JSONResponse(
            status_code=budget_error_status_code(budget_decision),
            content=budget_error_payload(budget_decision),
        )

    pdf_temp_path = _write_temp_pdf(pdf_bytes)
    evaluation_context = _evaluation_datetime_context(evaluation_timezone)
    logger.info(
        "Evaluation date context : thread=%s date=%s timezone=%s source=%s",
        thread_id,
        evaluation_context["evaluation_date"],
        evaluation_context["evaluation_timezone"],
        evaluation_context["evaluation_timezone_source"],
    )

    initial_state = {
        "pdf_bytes": None,
        "pdf_temp_path": pdf_temp_path,
        "pdf_preview_text": pdf_preview_text,
        "thread_id": thread_id,
        "raw_cv_text": "",
        "recruiter_instruction": normalized_recruiter_instruction,
        "evaluation_date": evaluation_context["evaluation_date"],
        "evaluation_timezone": evaluation_context["evaluation_timezone"],
        "evaluation_datetime_iso": evaluation_context["evaluation_datetime_iso"],
        "evaluation_timezone_source": evaluation_context["evaluation_timezone_source"],
        "candidate": None,
        "candidate_domain": None,
        "candidate_domain_source": None,
        "github_review_policy": None,
        "github_analysis": None,
        "report": None,
        "error": None,
        "error_code": None,
        "retry_after_seconds": None,
        "evaluation_status": EVALUATION_PENDING,
    }

    try:
        result = await graph.ainvoke(
            initial_state,
            config={"configurable": {"thread_id": thread_id}},
        )
    except Exception:
        _delete_temp_file(pdf_temp_path)
        raise

    if result.get("error"):
        await _set_graph_evaluation_status(graph, thread_id, EVALUATION_FAILED)
        logger.warning(
            "Upload evaluation failed before interrupt : thread=%s error_code=%s",
            thread_id,
            result.get("error_code") or "unknown",
        )
        if result.get("error_code") in UPLOAD_SECURITY_MESSAGES:
            return _upload_security_response(result["error_code"])

        return JSONResponse(
            status_code=503,
            content={
                "error": result["error"],
                "code": result.get("error_code") or "EVALUATION_UPLOAD_FAILED",
            },
        )

    interrupts = result.get("__interrupt__") or []
    interrupt_payload = interrupts[0] if interrupts else None
    if hasattr(interrupt_payload, "value"):
        interrupt_payload = interrupt_payload.value

    if not isinstance(interrupt_payload, dict) or "scenario" not in interrupt_payload:
        await _set_graph_evaluation_status(graph, thread_id, EVALUATION_FAILED)
        logger.error(f"Upload evaluation returned no resume scenario : thread={thread_id}")
        return JSONResponse(
            status_code=500,
            content={"error": "Evaluation could not be started. Please try again."},
        )

    scenario = interrupt_payload.get("scenario")

    if scenario == "MULTIPLE_FOUND":
        return JSONResponse(
            status_code=202,
            content={
                "thread_id": thread_id,
                "profiles": interrupt_payload.get("profiles", []),
            },
        )

    return JSONResponse(
        status_code=200,
        content={
            "thread_id": thread_id,
            "status": "ready_to_stream",
            "resume_payload": interrupt_payload,
        },
    )


@router.post("/{chat_id}/resume")
async def resume_evaluation(
    chat_id: str,
    body: ResumeRequest,
    user_id: str = Depends(verify_token),
):
    owned_chat = await _get_owned_chat(chat_id, user_id)
    _assert_chat_thread(owned_chat, body.thread_id)

    resume_payload = {
        "github_url": str(body.selected_profile) if body.selected_profile else None,
        "scenario": "ACCESSIBLE",
    }

    return JSONResponse(
        status_code=200,
        content={
            "thread_id": body.thread_id,
            "status": "ready_to_stream",
            "resume_payload": resume_payload,
        },
    )


@router.post("/{chat_id}/follow-up")
async def follow_up_question(
    chat_id: str,
    body: FollowUpRequest,
    user_id: str = Depends(verify_token),
):
    question = _clean_text(body.question)
    if not question:
        raise HTTPException(status_code=400, detail="Follow-up question is required.")

    report_context = await _load_completed_report_for_chat(chat_id, user_id)
    if not report_context:
        return JSONResponse(
            status_code=400,
            content={
                "error": FOLLOW_UP_REQUIRES_REPORT_MESSAGE,
                "code": "FOLLOW_UP_REQUIRES_COMPLETED_REPORT",
            },
        )

    logger.info(
        "Follow-up request accepted : chat=%s user=%s question_chars=%s report_context_chars=%s mock=%s",
        chat_id,
        user_id,
        len(question),
        len(report_context),
        settings.DEV_MOCK_EVALUATION,
    )

    try:
        answer = await _generate_follow_up_answer(chat_id, question, report_context)
    except GeminiQuotaExceededError as e:
        logger.warning("Follow-up quota failure : chat=%s error_type=%s", chat_id, type(e).__name__)
        return JSONResponse(
            status_code=429,
            content={
                "error": e.user_message,
                "code": e.code,
                "retry_after_seconds": e.retry_after_seconds,
            },
        )
    except LLMProviderUnavailableError as e:
        logger.warning(
            "Follow-up provider unavailable : chat=%s provider=%s model=%s status_code=%s provider_status=%s",
            chat_id,
            e.provider,
            e.model,
            e.status_code or "unknown",
            e.provider_status,
            exc_info=True,
        )
        return JSONResponse(
            status_code=503,
            content={
                "error": e.user_message,
                "code": e.error_code,
                "retry_after_seconds": e.retry_after_seconds,
            },
        )
    except FollowUpAnswerIncompleteError as e:
        logger.warning("Follow-up answer incomplete : chat=%s", chat_id)
        return JSONResponse(
            status_code=500,
            content={
                "error": e.user_message,
                "code": "FOLLOW_UP_INCOMPLETE",
            },
        )
    except Exception as e:
        logger.error("Follow-up failed : chat=%s error_type=%s", chat_id, type(e).__name__)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Follow-up answer failed. Please try again.",
                "code": "FOLLOW_UP_FAILED",
            },
        )

    return JSONResponse(
        status_code=200,
        content={"answer": answer},
    )


async def _generate_follow_up_answer(
    chat_id: str,
    question: str,
    report_context: str,
) -> str:
    if settings.DEV_MOCK_EVALUATION:
        return mock_follow_up_answer(question)

    return await answer_follow_up_question(report_context, question, chat_id=chat_id)


async def follow_up_stream_generator(
    request: Request,
    chat_id: str,
    question: str,
    report_context: str,
) -> AsyncGenerator[str, None]:
    if await request.is_disconnected():
        logger.info("Follow-up SSE client disconnected before stream start : chat=%s", chat_id)
        return

    try:
        answer = await _generate_follow_up_answer(chat_id, question, report_context)

        if await request.is_disconnected():
            logger.info("Follow-up SSE client disconnected before token stream : chat=%s", chat_id)
            return

        logger.info("Follow-up SSE stream started : chat=%s response_chars=%s", chat_id, len(answer))

        for chunk in _mock_token_chunks(answer):
            if await request.is_disconnected():
                logger.info("Follow-up SSE client disconnected during token stream : chat=%s", chat_id)
                return

            yield f"event: token\ndata: {json.dumps({'text': chunk})}\n\n"
            await asyncio.sleep(0.02)

        if await request.is_disconnected():
            logger.info("Follow-up SSE client disconnected before done : chat=%s", chat_id)
            return

        yield f"event: done\ndata: {json.dumps({})}\n\n"
        logger.info("Follow-up SSE stream completed : chat=%s", chat_id)
    except GeminiQuotaExceededError as e:
        logger.warning("Follow-up SSE quota failure : chat=%s error_type=%s", chat_id, type(e).__name__)
        payload = {
            "error": e.user_message,
            "code": e.code,
            "retry_after_seconds": e.retry_after_seconds,
        }
        yield f"event: error\ndata: {json.dumps(payload)}\n\n"
    except LLMProviderUnavailableError as e:
        logger.warning(
            "Follow-up SSE provider unavailable : chat=%s provider=%s model=%s status_code=%s provider_status=%s",
            chat_id,
            e.provider,
            e.model,
            e.status_code or "unknown",
            e.provider_status,
            exc_info=True,
        )
        payload = {
            "error": e.user_message,
            "code": e.error_code,
        }
        if e.retry_after_seconds:
            payload["retry_after_seconds"] = e.retry_after_seconds
        yield f"event: error\ndata: {json.dumps(payload)}\n\n"
    except FollowUpAnswerIncompleteError as e:
        logger.warning("Follow-up SSE answer incomplete : chat=%s", chat_id)
        yield f"event: error\ndata: {json.dumps({'error': e.user_message, 'code': 'FOLLOW_UP_INCOMPLETE'})}\n\n"
    except asyncio.CancelledError:
        logger.info("Follow-up SSE stream cancelled : chat=%s", chat_id)
        return
    except Exception as e:
        logger.error("Follow-up SSE failed : chat=%s error_type=%s", chat_id, type(e).__name__)
        yield f"event: error\ndata: {json.dumps({'error': 'Follow-up answer failed. Please try again.', 'code': 'FOLLOW_UP_FAILED'})}\n\n"


@router.post("/{chat_id}/follow-up/stream")
async def stream_follow_up(
    chat_id: str,
    body: FollowUpRequest,
    request: Request,
    user_id: str = Depends(verify_token),
):
    question = _clean_text(body.question)
    if not question:
        raise HTTPException(status_code=400, detail="Follow-up question is required.")

    report_context = await _load_completed_report_for_chat(chat_id, user_id)
    if not report_context:
        return JSONResponse(
            status_code=400,
            content={
                "error": FOLLOW_UP_REQUIRES_REPORT_MESSAGE,
                "code": "FOLLOW_UP_REQUIRES_COMPLETED_REPORT",
            },
        )

    logger.info(
        "Follow-up SSE request accepted : chat=%s user=%s question_chars=%s report_context_chars=%s mock=%s",
        chat_id,
        user_id,
        len(question),
        len(report_context),
        settings.DEV_MOCK_EVALUATION,
    )

    return _sse_response(
        follow_up_stream_generator(
            request,
            chat_id,
            question,
            report_context,
        )
    )


async def evaluation_stream_generator(
    request: Request,
    thread_id: str,
    resume_payload: dict,
    meta: dict,
    graph,
) -> AsyncGenerator[str, None]:

    if await request.is_disconnected():
        logger.info(f"SSE client disconnected before stream start : thread={thread_id}")
        await _set_graph_evaluation_status(graph, thread_id, EVALUATION_STOPPED)
        await _release_stream_thread(thread_id, reason="prestart_disconnect")
        return

    try:
        yield f"event: meta\ndata: {json.dumps(meta)}\n\n"
        logger.info(
            "SSE stream started : thread=%s candidate_name_present=%s role_present=%s",
            thread_id,
            bool(meta.get("candidate_name")),
            bool(meta.get("role")),
        )
        last_meta = meta
        config = {"configurable": {"thread_id": thread_id}}

        result_stream = graph.astream(
            Command(resume=resume_payload),
            config=config,
            stream_mode="values",
        )

        agent_2_status_sent = False
        agent_3_status_sent = False
        report_sent = False

        async for state_snapshot in result_stream:
            if await request.is_disconnected():
                logger.info(f"SSE client disconnected : thread={thread_id}")
                await _set_graph_evaluation_status(graph, thread_id, EVALUATION_STOPPED)
                return

            current_meta = _candidate_meta(state_snapshot)
            if _meta_changed(current_meta, last_meta):
                yield f"event: meta\ndata: {json.dumps(current_meta)}\n\n"
                last_meta = current_meta

            if state_snapshot.get("error"):
                error = state_snapshot["error"]
                await _set_graph_evaluation_status(graph, thread_id, EVALUATION_FAILED)
                logger.warning(
                    "SSE pipeline state error : thread=%s error_code=%s",
                    thread_id,
                    state_snapshot.get("error_code") or "unknown",
                )
                payload = {
                    "error": error,
                    "code": state_snapshot.get("error_code") or "EVALUATION_PIPELINE_ERROR",
                }
                if state_snapshot.get("retry_after_seconds"):
                    payload["retry_after_seconds"] = state_snapshot["retry_after_seconds"]
                yield f"event: error\ndata: {json.dumps(payload)}\n\n"
                return

            if not agent_2_status_sent and state_snapshot.get("github_analysis") is not None:
                yield f"event: status\ndata: {json.dumps({'text': 'Checking GitHub Repository...'})}\n\n"
                agent_2_status_sent = True
                logger.info(f"Agent 2 completed : thread={thread_id}")

            if not agent_3_status_sent and state_snapshot.get("report") is not None:
                report: str = state_snapshot.get("report", "")
                report_role = _report_role(report)
                if report_role:
                    report_meta = {
                        "candidate_name": last_meta.get("candidate_name") or UNKNOWN_CANDIDATE,
                        "role": report_role,
                    }
                    if _meta_changed(report_meta, last_meta):
                        yield f"event: meta\ndata: {json.dumps(report_meta)}\n\n"
                        last_meta = report_meta

                yield f"event: status\ndata: {json.dumps({'text': 'Generating Recommendation...'})}\n\n"
                agent_3_status_sent = True
                logger.info(f"Agent 3 completed : thread={thread_id}")

                if report:
                    report_sent = True
                for char in report:
                    if await request.is_disconnected():
                        logger.info(f"SSE client disconnected during token stream : thread={thread_id}")
                        await _set_graph_evaluation_status(graph, thread_id, EVALUATION_STOPPED)
                        return

                    yield f"event: token\ndata: {json.dumps({'text': char})}\n\n"

        if not report_sent:
            await _set_graph_evaluation_status(graph, thread_id, EVALUATION_FAILED)
            logger.warning(f"SSE stream ended without report : thread={thread_id}")
            payload = {
                "error": "Evaluation stopped unexpectedly. Please try again.",
                "code": "EVALUATION_STOPPED_UNEXPECTEDLY",
            }
            yield f"event: error\ndata: {json.dumps(payload)}\n\n"
            return

        await _set_graph_evaluation_status(graph, thread_id, EVALUATION_COMPLETED)
        yield f"event: done\ndata: {json.dumps({})}\n\n"
        logger.info(f"SSE stream completed : thread={thread_id}")

    except GeminiQuotaExceededError as e:
        await _set_graph_evaluation_status(graph, thread_id, EVALUATION_FAILED)
        logger.warning("SSE pipeline quota failure : thread=%s error_type=%s", thread_id, type(e).__name__)
        payload = {
            "error": e.user_message,
            "code": e.code,
            "retry_after_seconds": e.retry_after_seconds,
        }
        yield f"event: error\ndata: {json.dumps(payload)}\n\n"
    except LLMProviderUnavailableError as e:
        await _set_graph_evaluation_status(graph, thread_id, EVALUATION_FAILED)
        logger.warning(
            "SSE pipeline provider unavailable : thread=%s provider=%s model=%s status_code=%s provider_status=%s",
            thread_id,
            e.provider,
            e.model,
            e.status_code or "unknown",
            e.provider_status,
            exc_info=True,
        )
        payload = {
            "error": e.user_message,
            "code": e.error_code,
        }
        if e.retry_after_seconds:
            payload["retry_after_seconds"] = e.retry_after_seconds
        yield f"event: error\ndata: {json.dumps(payload)}\n\n"
    except asyncio.CancelledError:
        await _set_graph_evaluation_status(graph, thread_id, EVALUATION_STOPPED)
        logger.info(f"SSE stream cancelled : thread={thread_id}")
        return
    except Exception as e:
        await _set_graph_evaluation_status(graph, thread_id, EVALUATION_FAILED)
        logger.error("SSE pipeline failed : thread=%s error_type=%s", thread_id, type(e).__name__)
        yield f"event: error\ndata: {json.dumps({'error': 'Evaluation failed'})}\n\n"
    finally:
        await _release_stream_thread(thread_id, reason="stream_generator_finally")


@router.get("/{chat_id}/stream")
async def stream_evaluation(
    chat_id: str,
    request: Request,
    thread_id: str = Query(..., description="LangGraph thread id"),
    resume_payload_str: str = Query(
        ...,
        alias="resume_payload",
        description="URL encoded json from /upload or /resume response",
    ),
    user_id: str = Depends(verify_token),
):
    try:
        resume_payload = json.loads(urllib.parse.unquote(resume_payload_str))
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(
            status_code=422,
            detail=EVALUATION_RESTORE_FAILED_MESSAGE,
        )

    if "scenario" not in resume_payload:
        raise HTTPException(
            status_code=422,
            detail=EVALUATION_RESTORE_FAILED_MESSAGE,
        )

    owned_chat = await _get_owned_chat(chat_id, user_id)
    _assert_chat_thread(owned_chat, thread_id)

    if settings.DEV_MOCK_EVALUATION:
        if not await _mock_run_exists(thread_id):
            raise HTTPException(status_code=404, detail=EVALUATION_SESSION_UNAVAILABLE_MESSAGE)

        mock_status = await _mock_run_status(thread_id)
        mock_report = await _mock_run_report(thread_id)

        if mock_status == EVALUATION_COMPLETED and mock_report:
            return _sse_response(
                _cached_report_stream_generator(
                    request,
                    thread_id,
                    MOCK_META,
                    mock_report,
                )
            )

        if mock_status in {
            EVALUATION_IN_PROGRESS,
            EVALUATION_COMPLETED,
            EVALUATION_STOPPED,
            EVALUATION_FAILED,
        }:
            return _sse_response(_single_error_stream(_thread_terminal_error_payload(mock_status)))

        if not await _claim_stream_thread(thread_id, chat_id=chat_id):
            return _sse_response(
                _single_error_stream(_thread_terminal_error_payload(EVALUATION_IN_PROGRESS))
            )

        return _sse_response(mock_evaluation_stream_generator(request, thread_id))

    graph = request.app.state.graph

    if not await _claim_stream_thread(thread_id, chat_id=chat_id):
        logger.info("Duplicate SSE stream rejected : chat=%s thread=%s", chat_id, thread_id)
        return _sse_response(
            _single_error_stream(_thread_terminal_error_payload(EVALUATION_IN_PROGRESS))
        )

    try:
        snapshot = await _read_graph_state_with_retry(
            graph,
            thread_id,
            "stream_checkpoint_read",
        )
    except Exception as e:
        await _release_stream_thread(thread_id, reason="checkpoint_read_failed", chat_id=chat_id)
        logger.error(
            "Failed to read checkpoint : thread=%s error_type=%s",
            thread_id,
            type(e).__name__,
        )
        return JSONResponse(
            status_code=503,
            content={
                "error": EVALUATION_STATE_TEMPORARILY_UNAVAILABLE_MESSAGE,
                "code": "EVALUATION_STATE_TEMPORARILY_UNAVAILABLE",
            },
        )

    if snapshot is None or not snapshot.values:
        await _release_stream_thread(thread_id, reason="checkpoint_missing", chat_id=chat_id)
        raise HTTPException(status_code=404, detail=EVALUATION_SESSION_UNAVAILABLE_MESSAGE)

    meta = _candidate_meta(snapshot.values, snapshot.tasks)
    evaluation_status = _evaluation_status(snapshot.values)

    if evaluation_status == EVALUATION_COMPLETED and snapshot.values.get("report"):
        await _release_stream_thread(thread_id, reason="cached_report_stream", chat_id=chat_id)
        return _sse_response(
            _cached_report_stream_generator(
                request,
                thread_id,
                meta,
                snapshot.values["report"],
            )
        )

    if evaluation_status in {
        EVALUATION_IN_PROGRESS,
        EVALUATION_COMPLETED,
        EVALUATION_STOPPED,
        EVALUATION_FAILED,
    }:
        await _release_stream_thread(thread_id, reason=f"terminal_status:{evaluation_status}", chat_id=chat_id)
        return _sse_response(
            _single_error_stream(_thread_terminal_error_payload(evaluation_status))
        )

    return _sse_response(
        evaluation_stream_generator(request, thread_id, resume_payload, meta, graph),
    )
