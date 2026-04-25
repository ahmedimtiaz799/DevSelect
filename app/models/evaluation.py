from enum import Enum
from pydantic import BaseModel, field_validator

class RedFlagSeverity(str, Enum):
    MAJOR = "MAJOR"
    MODERATE = "MODERATE"
    MILD = "MILD"

class RedFlag(BaseModel):
    severity: RedFlagSeverity
    flag_description: str
    reason: str

class RecommendationLevel(str, Enum):
    STRONG_HIRE = "STRONG_HIRE"
    HIRE = "HIRE"
    HIRE_WITH_RESERVATIONS = "HIRE_WITH_RESERVATIONS"
    NO_HIRE = "NO_HIRE"

class HiringReport(BaseModel):
    candidate_name: str
    detected_role: str
    seniority: str
    experience_duration: str
    cv_review: str
    github_review: str
    skill_match_assessment: str | None
    red_flags: list[RedFlag]
    strengths: list[str]
    recommendation: RecommendationLevel
    supporting_reasons: list[str]
    suggested_next_steps: str

    @field_validator("supporting_reasons")
    @classmethod
    def reasons_must_be_3_to_5(cls, v: list[str]) -> list[str]:
        if not 3 <= len(v) <= 5:
            raise ValueError(f"Supporting reasons must be between 3 to 5, got {len(v)}")
        return v