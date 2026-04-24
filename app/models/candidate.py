from enum import Enum
from pydantic import BaseModel, field_validator

class GitHubScenario(str, Enum):
    NOT_FOUND = "NOT_FOUND"
    COULD_NOT_BE_ACCESSED = "COULD_NOT_BE_ACCESSED"
    PRIVATE = "PRIVATE"
    MULTIPLE_FOUND = "MULTIPLE_FOUND"
    ACCESSIBLE = "ACCESSIBLE"

class CandidateExtraction(BaseModel):
    name: str | None
    role: str
    seniority: str
    skills: list[str]
    github_links: list[str]
    experience_years: float | None

    @field_validator("seniority")
    @classmethod
    def validate_seniority(cls, v: str) -> str:
        allowed = {"Junior", "Mid Level", "Senior", "Managerial"}
        normalized = v.strip().title()
        if normalized not in allowed:
            raise ValueError(f"Seniority must be one of {allowed}, got '{v}'")
        return normalized
    
    @field_validator("skills", "github_links")
    @classmethod
    def lists_must_not_be_empty_strings(cls, v: list[str]) -> list[str]:
        return [item.strip() for item in v if item.strip()]

class GitHubAnalysis(BaseModel):
    scenario: GitHubScenario
    selected_url: str | None
    original_repo_count: int
    commit_frequency_score: int
    language_match_score: int
    readme_quality_score: int
    complexity_score: int
    code_quality_score: int
    recency_score: int
    commit_message_quality: int
    summary: str

    @field_validator(
        "commit_frequency_score",
        "language_match_score",
        "readme_quality_score",
        "complexity_score",
        "code_quality_score",
        "recency_score",
        "commit_message_quality",
    )
    @classmethod
    def score_must_be_0_to_10(cls, v: int) -> int:
        if not 0 <= v <= 10:
            raise ValueError(f"Score must be between 0 and 10, got {v}")
        return v
