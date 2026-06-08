from __future__ import annotations
from typing import Any, TypedDict


class DevSelectState(TypedDict):
    pdf_bytes: bytes | None
    pdf_temp_path: str | None
    pdf_preview_text: str | None
    thread_id: str
    raw_cv_text: str
    recruiter_instruction: str | None
    evaluation_date: str | None
    evaluation_timezone: str | None
    evaluation_datetime_iso: str | None
    evaluation_timezone_source: str | None
    candidate: dict[str, Any] | None
    candidate_domain: str | None
    candidate_domain_source: str | None
    github_review_policy: str | None
    github_analysis: dict[str, Any] | None
    report: str | None
    error: str | None
    error_code: str | None
    retry_after_seconds: int | None
    evaluation_status: str | None
