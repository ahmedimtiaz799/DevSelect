from __future__ import annotations
from typing import TypedDict

from app.models import CandidateExtraction,GitHubAnalysis,HiringReport

class DevSelectState(TypedDict):
    pdf_bytes: bytes
    thread_id: str
    raw_cv_text: str
    candidate: CandidateExtraction | None
    github_analysis: GitHubAnalysis | None
    report: HiringReport | None
    error: str | None
