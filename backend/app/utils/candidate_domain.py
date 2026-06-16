from __future__ import annotations

import re
from typing import Any


TECHNICAL = "technical"
SEMI_TECHNICAL = "semi_technical"
NON_TECHNICAL = "non_technical"
UNCLEAR = "unclear"

SKIP_NON_TECHNICAL = "skip_non_technical"
SKIP_UNCLEAR = "skip_unclear"

TECHNICAL_ROLE_KEYWORDS = (
    "software engineer",
    "software developer",
    "full stack",
    "full-stack",
    "frontend",
    "front-end",
    "backend",
    "back-end",
    "web developer",
    "mobile developer",
    "android developer",
    "ios developer",
    "devops",
    "site reliability",
    "sre",
    "qa engineer",
    "test engineer",
    "automation engineer",
    "machine learning",
    "ml engineer",
    "data engineer",
    "data scientist",
    "cloud engineer",
    "security engineer",
    "platform engineer",
    "solutions architect",
    "technical architect",
)

NON_TECHNICAL_ROLE_KEYWORDS = (
    "account executive",
    "banking",
    "banking and finance",
    "banking operations",
    "program manager",
    "recruiter",
    "talent acquisition",
    "human resources",
    "hr officer",
    "hr manager",
    "admin officer",
    "operations manager",
    "operations executive",
    "marketing",
    "marketing executive",
    "marketing manager",
    "sales executive",
    "sales manager",
    "account manager",
    "customer support",
    "customer success",
    "digital banking",
    "financial sector",
    "financial analyst",
    "financial services",
    "finance officer",
    "finance manager",
    "finance candidate",
    "risk assessment",
    "accountant",
    "teacher",
    "lecturer",
    "instructor",
    "doctor",
    "physician",
    "nurse",
    "lawyer",
    "attorney",
    "paralegal",
    "driver",
    "delivery driver",
    "transport",
    "logistics",
    "chef",
    "cook",
    "hospitality",
    "security guard",
    "security officer",
    "electrician",
    "mechanic",
    "plumber",
    "welder",
    "warehouse supervisor",
    "warehouse manager",
    "store manager",
    "retail",
    "pharmacist",
    "lab technician",
    "laboratory technician",
    "procurement",
    "legal",
    "administrator",
    "coordinator",
)

BANKING_FINANCE_ROLE_TITLE = "Entry-Level Banking & Finance Candidate"

BANKING_FINANCE_FOCUS_KEYWORDS = (
    "banking",
    "banking and finance",
    "financial sector",
    "financial services",
    "digital banking",
    "banking operations",
    "finance sector",
    "finance industry",
)

BANKING_FINANCE_EDUCATION_KEYWORDS = (
    "bba",
    "bachelor of business administration",
    "banking and finance",
    "business administration",
    "finance",
)

BANKING_FINANCE_SKILL_KEYWORDS = (
    "financial analysis",
    "finance",
    "banking",
    "digital banking",
    "risk assessment",
    "spreadsheet",
    "excel",
    "financial reporting",
    "accounting",
    "banking operations",
    "financial inclusion",
)

TRAINING_OR_VOLUNTEER_ROLE_KEYWORDS = (
    "volunteer",
    "trainer",
    "training",
    "teacher",
    "teaching",
    "instructor",
    "mentor",
    "tutor",
)

DISPLAY_ROLE_STOP_LINES = {
    "certifications",
    "contact",
    "education",
    "experience",
    "professional summary",
    "projects",
    "skills",
    "summary",
    "work experience",
}

DISPLAY_ROLE_UNKNOWN_VALUES = {
    "n/a",
    "na",
    "none",
    "not detected",
    "not found",
    "null",
    "unknown",
    "unknown role",
    "unknown title",
}

SEMI_TECHNICAL_ROLE_KEYWORDS = (
    "project manager",
    "scrum master",
    "product manager",
    "product owner",
    "business analyst",
    "ui/ux",
    "ux designer",
    "ui designer",
    "product designer",
    "graphic designer",
    "data analyst",
    "analytics analyst",
    "bi analyst",
    "business intelligence",
    "technical consultant",
    "solutions consultant",
    "implementation consultant",
    "technical project manager",
)

DISPLAY_ROLE_KEYWORDS = (
    TECHNICAL_ROLE_KEYWORDS
    + SEMI_TECHNICAL_ROLE_KEYWORDS
    + NON_TECHNICAL_ROLE_KEYWORDS
    + BANKING_FINANCE_FOCUS_KEYWORDS
    + (
        "accountant",
        "administrator",
        "advisor",
        "analyst",
        "architect",
        "assistant",
        "associate",
        "banking",
        "business",
        "candidate",
        "consultant",
        "coordinator",
        "designer",
        "developer",
        "engineer",
        "executive",
        "finance",
        "financial",
        "instructor",
        "manager",
        "officer",
        "operations",
        "specialist",
        "supervisor",
        "teacher",
        "technician",
        "trainer",
    )
)

TECHNICAL_SIGNAL_KEYWORDS = (
    "python",
    "java",
    "javascript",
    "typescript",
    "react",
    "next.js",
    "node",
    "node.js",
    "fastapi",
    "django",
    "flask",
    "spring",
    "laravel",
    "php",
    "c++",
    "c#",
    ".net",
    "sql",
    "postgres",
    "mysql",
    "mongodb",
    "docker",
    "kubernetes",
    "aws",
    "azure",
    "gcp",
    "rest api",
    "graphql",
    "microservice",
    "ci/cd",
    "terraform",
    "pandas",
    "numpy",
    "machine learning",
    "deep learning",
    "llm",
    "rag",
)


def _field(value: Any, name: str, default=None):
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def _count_keyword_hits(text: str, keywords: tuple[str, ...]) -> int:
    return sum(1 for keyword in keywords if keyword in text)


def _candidate_evidence_text(candidate: Any, raw_cv_text: str | None) -> str:
    evidence: list[str] = [
        _field(candidate, "current_title"),
        _field(candidate, "summary"),
        raw_cv_text,
    ]

    for list_field in ("skills", "languages", "frameworks", "projects", "certifications"):
        evidence.extend(str(item or "") for item in (_field(candidate, list_field, []) or []))

    for education in _field(candidate, "education", []) or []:
        evidence.append(_field(education, "degree"))
        evidence.append(_field(education, "institution"))

    for experience in _field(candidate, "work_experience", []) or []:
        evidence.append(_field(experience, "title"))
        evidence.append(_field(experience, "company"))
        evidence.append(_field(experience, "description"))

    return _normalize_text(" ".join(str(part or "") for part in evidence))


def is_training_or_volunteer_role(role: str | None) -> bool:
    return _contains_any(_normalize_text(role), TRAINING_OR_VOLUNTEER_ROLE_KEYWORDS)


def _clean_display_role(value: Any) -> str | None:
    role = re.sub(r"\s+", " ", str(value or "").strip(" :-|•\t"))
    if not role or len(role) > 80:
        return None

    lowered = role.lower()
    if lowered in DISPLAY_ROLE_STOP_LINES or lowered in DISPLAY_ROLE_UNKNOWN_VALUES:
        return None

    if any(marker in lowered for marker in ("@", "http://", "https://", "github.com", "linkedin.com")):
        return None

    if not _contains_any(lowered, DISPLAY_ROLE_KEYWORDS):
        return None

    return role


def _role_from_summary(summary: str | None) -> str | None:
    text = re.sub(r"\s+", " ", (summary or "").strip())
    if not text:
        return None

    leading = re.split(r"\bwith\b|\bwho\b|,|\.|;", text, maxsplit=1, flags=re.IGNORECASE)[0]
    role = _clean_display_role(leading)
    if role:
        return role

    match = re.search(
        r"\b([A-Z][A-Za-z0-9+/# .-]{2,80}?\b(?:Engineer|Developer|Architect|Designer|Manager|Analyst|Scientist|Specialist|Consultant|DevOps|QA|Trainer|Teacher|Instructor|Officer|Executive|Accountant)\b)",
        text,
    )
    if match:
        return _clean_display_role(match.group(1))

    return None


def _role_from_experience(candidate: Any) -> str | None:
    for experience in _field(candidate, "work_experience", []) or []:
        role = _clean_display_role(_field(experience, "title"))
        if role:
            return role

    return None


def infer_banking_finance_role(candidate: Any, raw_cv_text: str | None = None) -> str | None:
    evidence_text = _candidate_evidence_text(candidate, raw_cv_text)
    if not evidence_text:
        return None

    if _contains_any(evidence_text, TECHNICAL_ROLE_KEYWORDS) or _contains_any(
        evidence_text,
        SEMI_TECHNICAL_ROLE_KEYWORDS,
    ):
        return None

    has_focus = _contains_any(evidence_text, BANKING_FINANCE_FOCUS_KEYWORDS)
    has_education = _contains_any(evidence_text, BANKING_FINANCE_EDUCATION_KEYWORDS) and (
        "banking" in evidence_text or "finance" in evidence_text or "financial" in evidence_text
    )
    skill_hits = _count_keyword_hits(evidence_text, BANKING_FINANCE_SKILL_KEYWORDS)

    if has_education and (has_focus or skill_hits >= 1):
        return BANKING_FINANCE_ROLE_TITLE

    if has_focus and skill_hits >= 2:
        return BANKING_FINANCE_ROLE_TITLE

    return None


def resolve_candidate_display_role_with_source(
    candidate: Any,
    raw_cv_text: str | None = None,
) -> tuple[str | None, str]:
    banking_finance_role = infer_banking_finance_role(candidate, raw_cv_text)
    schema_role = _clean_display_role(_field(candidate, "current_title"))

    if schema_role:
        if banking_finance_role and is_training_or_volunteer_role(schema_role):
            return banking_finance_role, "banking_finance_profile"
        return schema_role, "schema"

    if banking_finance_role:
        return banking_finance_role, "banking_finance_profile"

    summary_role = _role_from_summary(_field(candidate, "summary"))
    if summary_role:
        return summary_role, "summary"

    experience_role = _role_from_experience(candidate)
    if experience_role:
        return experience_role, "work_experience"

    return None, "missing"


def resolve_candidate_display_role(
    candidate: Any,
    raw_cv_text: str | None = None,
) -> str | None:
    role, _source = resolve_candidate_display_role_with_source(candidate, raw_cv_text)
    return role


def _technical_signal_score(candidate: Any, raw_cv_text: str | None) -> int:
    evidence = []
    evidence.extend(_field(candidate, "skills", []) or [])
    evidence.extend(_field(candidate, "languages", []) or [])
    evidence.extend(_field(candidate, "frameworks", []) or [])
    evidence.extend(_field(candidate, "projects", []) or [])
    evidence.append(_field(candidate, "summary"))
    evidence.append(raw_cv_text)
    haystack = _normalize_text(" ".join(str(part or "") for part in evidence))

    hits = 0
    for keyword in TECHNICAL_SIGNAL_KEYWORDS:
        if keyword in haystack:
            hits += 1

    return hits


def classify_candidate_domain(candidate: Any, raw_cv_text: str | None = None) -> tuple[str, str]:
    role_evidence = [
        _field(candidate, "current_title"),
        _field(candidate, "summary"),
    ]
    for experience in _field(candidate, "work_experience", []) or []:
        role_evidence.append(_field(experience, "title"))
        break

    role_text = _normalize_text(" ".join(str(part or "") for part in role_evidence))
    technical_signal_score = _technical_signal_score(candidate, raw_cv_text)

    if _contains_any(role_text, TECHNICAL_ROLE_KEYWORDS):
        return TECHNICAL, "technical_role_keyword"

    if _contains_any(role_text, NON_TECHNICAL_ROLE_KEYWORDS):
        if technical_signal_score >= 3:
            return SEMI_TECHNICAL, "non_technical_role_with_technical_signals"
        return NON_TECHNICAL, "non_technical_role_keyword"

    if _contains_any(role_text, SEMI_TECHNICAL_ROLE_KEYWORDS):
        if technical_signal_score >= 2:
            return SEMI_TECHNICAL, "semi_technical_role_keyword_with_code_signals"
        return SEMI_TECHNICAL, "semi_technical_role_keyword"

    if technical_signal_score >= 4:
        return TECHNICAL, "technical_skill_signals"

    if technical_signal_score >= 2:
        return SEMI_TECHNICAL, "mixed_skill_signals"

    return UNCLEAR, "insufficient_role_signals"


def github_review_policy(candidate_domain: str | None) -> str | None:
    if candidate_domain == NON_TECHNICAL:
        return SKIP_NON_TECHNICAL
    if candidate_domain == UNCLEAR:
        return SKIP_UNCLEAR
    return None


def should_skip_github_review(candidate_domain: str | None) -> bool:
    return github_review_policy(candidate_domain) is not None
