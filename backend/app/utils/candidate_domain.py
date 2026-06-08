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
    "finance officer",
    "finance manager",
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
