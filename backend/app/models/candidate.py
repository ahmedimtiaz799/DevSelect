import re
from enum import Enum
from typing import Any
from pydantic import BaseModel, field_validator


class GitHubScenario(str, Enum):
    NOT_FOUND = "NOT_FOUND"
    COULD_NOT_BE_ACCESSED = "COULD_NOT_BE_ACCESSED"
    PRIVATE = "PRIVATE"
    MULTIPLE_FOUND = "MULTIPLE_FOUND"
    ACCESSIBLE = "ACCESSIBLE"


class GitHubAnalysisStatus(str, Enum):
    VERIFIED = "VERIFIED"
    NOT_FOUND = "NOT_FOUND"
    UNAVAILABLE = "UNAVAILABLE"
    PRIVATE = "PRIVATE"


class WorkExperience(BaseModel):
    title: str | None = None
    company: str | None = None
    duration: str | None = None
    description: str | None = None


class Education(BaseModel):
    degree: str | None = None
    institution: str | None = None
    year: int | None = None

    @field_validator("year", mode="before")
    @classmethod
    def year_must_be_int(cls, v: Any) -> Any:
        if v is None or isinstance(v, int):
            return v

        text = str(v).strip()
        if not text:
            return None

        match = re.search(r"\b(19|20)\d{2}\b", text)
        return int(match.group(0)) if match else None


class CandidateExtraction(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    years_of_experience: float | None = None
    current_title: str | None = None
    summary: str | None = None
    skills: list[str] = []
    languages: list[str] = []
    frameworks: list[str] = []
    projects: list[str] = []
    education: list[Education] = []
    work_experience: list[WorkExperience] = []
    github_urls: list[str] = []
    github_url: str | None = None
    linkedin_url: str | None = None
    certifications: list[str] = []

    @field_validator("projects", mode="before")
    @classmethod
    def project_items_must_be_strings(cls, v: Any) -> Any:
        if not isinstance(v, list):
            return v

        projects = []
        for item in v:
            if isinstance(item, str):
                projects.append(item)
                continue

            if isinstance(item, dict):
                name = item.get("project") or item.get("name") or item.get("title")
                detail = (
                    item.get("technologies")
                    or item.get("tech_stack")
                    or item.get("purpose")
                    or item.get("description")
                )
                text = " - ".join(str(part).strip() for part in (name, detail) if part)
                if text:
                    projects.append(text)
                continue

            if item is not None:
                projects.append(str(item))

        return projects

    @field_validator("skills", "languages", "frameworks", "projects", "certifications")
    @classmethod
    def lists_must_not_be_empty_strings(cls, v: list[str]) -> list[str]:
        return [item.strip() for item in v if item.strip()]


class GitHubAnalysis(BaseModel):
    scenario: GitHubScenario
    analysis_status: GitHubAnalysisStatus = GitHubAnalysisStatus.UNAVAILABLE
    summary: str = ""
    overall_score: int = 0
    original_repo_score: int = 0
    commit_frequency_score: int = 0
    commit_message_score: int = 0
    language_relevance_score: int = 0
    readme_quality_score: int = 0
    project_complexity_score: int = 0
    recency_score: int = 0
    community_score: int = 0
    strengths: list[str] = []
    red_flags: list[str] = []
    top_repos: list[str] = []
    language_breakdown: dict[str, float] = {}
    original_repo_count: int | None = None
    repos_with_readme: int | None = None
    total_commits: int | None = None
    profile_contribution_count: int | None = None
    repository_commit_count: int | None = None
    commit_message_sample_count: int | None = None
    recent_activity_days: int | None = None
    active_days_per_month: float | None = None

    @field_validator(
        "overall_score",
        "original_repo_score",
        "commit_frequency_score",
        "commit_message_score",
        "language_relevance_score",
        "readme_quality_score",
        "project_complexity_score",
        "recency_score",
        "community_score",
    )
    @classmethod
    def score_must_be_0_to_10(cls, v: int) -> int:
        if not 0 <= v <= 10:
            raise ValueError(f"Score must be between 0 and 10, got {v}")
        return v
