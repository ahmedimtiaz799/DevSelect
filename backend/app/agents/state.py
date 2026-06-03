from __future__ import annotations
from typing import TypedDict
from app.models.candidate import CandidateExtraction, GitHubAnalysis


class DevSelectState(TypedDict):
    pdf_bytes: bytes | None
    pdf_temp_path: str | None
    thread_id: str
    raw_cv_text: str
    recruiter_instruction: str | None
    evaluation_date: str | None
    evaluation_timezone: str | None
    evaluation_datetime_iso: str | None
    evaluation_timezone_source: str | None
    candidate: CandidateExtraction | None
    github_analysis: GitHubAnalysis | None
    report: str | None
    error: str | None
    error_code: str | None
    evaluation_status: str | None
