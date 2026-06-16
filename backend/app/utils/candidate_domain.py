from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


TECHNICAL = "technical"
SEMI_TECHNICAL = "semi_technical"
NON_TECHNICAL = "non_technical"
UNCLEAR = "unclear"

SKIP_NON_TECHNICAL = "skip_non_technical"
SKIP_UNCLEAR = "skip_unclear"

ROLE_FOCUS_NEEDS_CLARIFICATION = "Role focus needs clarification"

ROLE_FAMILY_SOFTWARE_ENGINEERING = "software_engineering"
ROLE_FAMILY_DATA_AI = "data_ai"
ROLE_FAMILY_PRODUCT = "product"
ROLE_FAMILY_DESIGN = "design"
ROLE_FAMILY_BUSINESS_ANALYSIS = "business_analysis"
ROLE_FAMILY_BANKING_FINANCE = "banking_finance"
ROLE_FAMILY_ACCOUNTING_AUDIT = "accounting_audit"
ROLE_FAMILY_SALES_MARKETING = "sales_marketing"
ROLE_FAMILY_HR_ADMIN = "hr_admin"
ROLE_FAMILY_OPERATIONS_SUPPLY_CHAIN = "operations_supply_chain"
ROLE_FAMILY_EDUCATION_TRAINING = "education_training"
ROLE_FAMILY_HEALTHCARE = "healthcare"
ROLE_FAMILY_LEGAL = "legal"
ROLE_FAMILY_CUSTOMER_SUPPORT = "customer_support"
ROLE_FAMILY_SKILLED_TRADE = "skilled_trade"
ROLE_FAMILY_UNCLEAR = "unclear"


@dataclass(frozen=True)
class RoleResolution:
    display_role: str
    role_family: str
    domain: str
    confidence: str
    source: str
    github_policy: str | None
    overrode_current_title: bool
    reason: str

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

ROLE_FAMILY_DOMAINS = {
    ROLE_FAMILY_SOFTWARE_ENGINEERING: TECHNICAL,
    ROLE_FAMILY_DATA_AI: TECHNICAL,
    ROLE_FAMILY_PRODUCT: SEMI_TECHNICAL,
    ROLE_FAMILY_DESIGN: SEMI_TECHNICAL,
    ROLE_FAMILY_BUSINESS_ANALYSIS: SEMI_TECHNICAL,
    ROLE_FAMILY_BANKING_FINANCE: NON_TECHNICAL,
    ROLE_FAMILY_ACCOUNTING_AUDIT: NON_TECHNICAL,
    ROLE_FAMILY_SALES_MARKETING: NON_TECHNICAL,
    ROLE_FAMILY_HR_ADMIN: NON_TECHNICAL,
    ROLE_FAMILY_OPERATIONS_SUPPLY_CHAIN: NON_TECHNICAL,
    ROLE_FAMILY_EDUCATION_TRAINING: NON_TECHNICAL,
    ROLE_FAMILY_HEALTHCARE: NON_TECHNICAL,
    ROLE_FAMILY_LEGAL: NON_TECHNICAL,
    ROLE_FAMILY_CUSTOMER_SUPPORT: NON_TECHNICAL,
    ROLE_FAMILY_SKILLED_TRADE: NON_TECHNICAL,
    ROLE_FAMILY_UNCLEAR: UNCLEAR,
}

ROLE_FAMILY_DISPLAY_ROLES = {
    ROLE_FAMILY_SOFTWARE_ENGINEERING: "Software Engineering Candidate",
    ROLE_FAMILY_DATA_AI: "Data / AI Candidate",
    ROLE_FAMILY_PRODUCT: "Product Candidate",
    ROLE_FAMILY_DESIGN: "Design Candidate",
    ROLE_FAMILY_BUSINESS_ANALYSIS: "Business Analyst",
    ROLE_FAMILY_BANKING_FINANCE: BANKING_FINANCE_ROLE_TITLE,
    ROLE_FAMILY_ACCOUNTING_AUDIT: "Accounting / Audit Candidate",
    ROLE_FAMILY_SALES_MARKETING: "Sales / Marketing Candidate",
    ROLE_FAMILY_HR_ADMIN: "HR / Admin Candidate",
    ROLE_FAMILY_OPERATIONS_SUPPLY_CHAIN: "Operations Candidate",
    ROLE_FAMILY_EDUCATION_TRAINING: "Education / Training Candidate",
    ROLE_FAMILY_HEALTHCARE: "Healthcare Candidate",
    ROLE_FAMILY_LEGAL: "Legal Candidate",
    ROLE_FAMILY_CUSTOMER_SUPPORT: "Customer Support Candidate",
    ROLE_FAMILY_SKILLED_TRADE: "Skilled Trade Candidate",
    ROLE_FAMILY_UNCLEAR: ROLE_FOCUS_NEEDS_CLARIFICATION,
}

ROLE_FAMILY_SIGNAL_KEYWORDS = {
    ROLE_FAMILY_SOFTWARE_ENGINEERING: (
        "software engineer",
        "software developer",
        "full stack",
        "frontend",
        "backend",
        "web developer",
        "mobile developer",
        "devops",
        "qa engineer",
        "react",
        "fastapi",
        "api",
    ),
    ROLE_FAMILY_DATA_AI: (
        "ai engineer",
        "machine learning",
        "ml engineer",
        "data engineer",
        "data scientist",
        "analytics",
        "rag",
        "llm",
        "langgraph",
    ),
    ROLE_FAMILY_PRODUCT: (
        "product manager",
        "product owner",
        "roadmap",
        "backlog",
        "user stories",
        "product strategy",
    ),
    ROLE_FAMILY_DESIGN: (
        "ui/ux",
        "ux designer",
        "ui designer",
        "product designer",
        "graphic designer",
        "portfolio",
        "wireframe",
    ),
    ROLE_FAMILY_BUSINESS_ANALYSIS: (
        "business analyst",
        "requirements",
        "stakeholder",
        "process mapping",
        "dashboard",
        "documentation",
    ),
    ROLE_FAMILY_BANKING_FINANCE: BANKING_FINANCE_FOCUS_KEYWORDS + BANKING_FINANCE_SKILL_KEYWORDS,
    ROLE_FAMILY_ACCOUNTING_AUDIT: (
        "accountant",
        "accounting",
        "audit",
        "bookkeeping",
        "ledger",
        "tax",
        "treasury",
    ),
    ROLE_FAMILY_SALES_MARKETING: (
        "sales",
        "marketing",
        "account executive",
        "business development",
        "client relationship",
        "campaign",
        "brand",
    ),
    ROLE_FAMILY_HR_ADMIN: (
        "human resources",
        "hr",
        "recruiter",
        "talent acquisition",
        "admin",
        "administrator",
        "office",
    ),
    ROLE_FAMILY_OPERATIONS_SUPPLY_CHAIN: (
        "operations",
        "supply chain",
        "logistics",
        "warehouse",
        "procurement",
        "inventory",
        "retail",
    ),
    ROLE_FAMILY_EDUCATION_TRAINING: (
        "teacher",
        "teaching",
        "trainer",
        "training",
        "instructor",
        "classroom",
        "curriculum",
        "lesson",
        "education",
        "coaching",
    ),
    ROLE_FAMILY_HEALTHCARE: (
        "doctor",
        "physician",
        "nurse",
        "pharmacist",
        "clinical",
        "healthcare",
        "lab technician",
    ),
    ROLE_FAMILY_LEGAL: (
        "lawyer",
        "attorney",
        "legal",
        "paralegal",
        "compliance",
    ),
    ROLE_FAMILY_CUSTOMER_SUPPORT: (
        "customer support",
        "customer service",
        "customer success",
        "support",
        "helpdesk",
    ),
    ROLE_FAMILY_SKILLED_TRADE: (
        "electrician",
        "mechanic",
        "plumber",
        "welder",
        "technician",
        "maintenance",
    ),
}

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


def _candidate_evidence_groups(candidate: Any, raw_cv_text: str | None) -> dict[str, str]:
    formal_experience: list[str] = []
    volunteer_experience: list[str] = []

    for experience in _field(candidate, "work_experience", []) or []:
        parts = [
            _field(experience, "title"),
            _field(experience, "company"),
            _field(experience, "description"),
        ]
        text = " ".join(str(part or "") for part in parts)
        title = _field(experience, "title")
        if is_training_or_volunteer_role(title) or "volunteer" in _normalize_text(text):
            volunteer_experience.append(text)
        else:
            formal_experience.append(text)

    education = []
    for item in _field(candidate, "education", []) or []:
        education.append(_field(item, "degree"))
        education.append(_field(item, "institution"))

    return {
        "current_title": _normalize_text(_field(candidate, "current_title")),
        "summary": _normalize_text(_field(candidate, "summary")),
        "education": _normalize_text(" ".join(str(part or "") for part in education)),
        "skills": _normalize_text(
            " ".join(
                str(item or "")
                for field_name in ("skills", "languages", "frameworks")
                for item in (_field(candidate, field_name, []) or [])
            )
        ),
        "certifications_projects": _normalize_text(
            " ".join(
                str(item or "")
                for field_name in ("certifications", "projects")
                for item in (_field(candidate, field_name, []) or [])
            )
        ),
        "formal_experience": _normalize_text(" ".join(formal_experience)),
        "volunteer_experience": _normalize_text(" ".join(volunteer_experience)),
        "raw_cv_text": _normalize_text(raw_cv_text),
    }


def is_training_or_volunteer_role(role: str | None) -> bool:
    return _contains_any(_normalize_text(role), TRAINING_OR_VOLUNTEER_ROLE_KEYWORDS)


def _family_hits(text: str, family: str) -> int:
    return _count_keyword_hits(text, ROLE_FAMILY_SIGNAL_KEYWORDS.get(family, ()))


def _role_family_scores(candidate: Any, raw_cv_text: str | None) -> dict[str, int]:
    groups = _candidate_evidence_groups(candidate, raw_cv_text)
    weights = {
        "current_title": 4,
        "summary": 5,
        "education": 4,
        "skills": 3,
        "certifications_projects": 2,
        "formal_experience": 2,
        "volunteer_experience": 1,
        "raw_cv_text": 1,
    }
    scores: dict[str, int] = {}

    for family in ROLE_FAMILY_SIGNAL_KEYWORDS:
        score = 0
        for source, text in groups.items():
            hits = _family_hits(text, family)
            if hits:
                score += hits * weights[source]
        scores[family] = score

    return scores


def _best_role_family(candidate: Any, raw_cv_text: str | None) -> tuple[str, int]:
    scores = _role_family_scores(candidate, raw_cv_text)
    if not scores:
        return ROLE_FAMILY_UNCLEAR, 0

    family, score = max(scores.items(), key=lambda item: item[1])
    if score <= 0:
        return ROLE_FAMILY_UNCLEAR, 0

    return family, score


def _role_family_from_text(text: str | None) -> str | None:
    normalized = _normalize_text(text)
    if not normalized:
        return None

    scores = {
        family: _family_hits(normalized, family)
        for family in ROLE_FAMILY_SIGNAL_KEYWORDS
    }
    family, score = max(scores.items(), key=lambda item: item[1])
    return family if score > 0 else None


def _github_policy_for_domain(domain: str) -> str | None:
    if domain == NON_TECHNICAL:
        return SKIP_NON_TECHNICAL
    if domain == UNCLEAR:
        return SKIP_UNCLEAR
    return None


def _domain_for_role_family(family: str, candidate: Any, raw_cv_text: str | None) -> str:
    domain = ROLE_FAMILY_DOMAINS.get(family, UNCLEAR)
    if domain == NON_TECHNICAL and _technical_signal_score(candidate, raw_cv_text) >= 3:
        return SEMI_TECHNICAL
    return domain


def _confidence_for_score(score: int) -> str:
    if score >= 10:
        return "high"
    if score >= 5:
        return "medium"
    if score > 0:
        return "low"
    return "unknown"


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

    groups = _candidate_evidence_groups(candidate, raw_cv_text)
    focus_score = _family_hits(groups["summary"], ROLE_FAMILY_BANKING_FINANCE)
    education_score = _count_keyword_hits(groups["education"], BANKING_FINANCE_EDUCATION_KEYWORDS)
    skill_score = _family_hits(groups["skills"], ROLE_FAMILY_BANKING_FINANCE)
    project_score = _family_hits(groups["certifications_projects"], ROLE_FAMILY_BANKING_FINANCE)
    raw_score = _family_hits(groups["raw_cv_text"], ROLE_FAMILY_BANKING_FINANCE)

    if education_score and (focus_score or skill_score or project_score or raw_score):
        return BANKING_FINANCE_ROLE_TITLE

    if focus_score and skill_score >= 2:
        return BANKING_FINANCE_ROLE_TITLE

    return None


def resolve_candidate_role_resolution(
    candidate: Any,
    raw_cv_text: str | None = None,
) -> RoleResolution:
    best_family, best_family_score = _best_role_family(candidate, raw_cv_text)
    banking_finance_role = infer_banking_finance_role(candidate, raw_cv_text)
    schema_role = _clean_display_role(_field(candidate, "current_title"))

    if schema_role:
        schema_family = _role_family_from_text(schema_role) or best_family
        if banking_finance_role and is_training_or_volunteer_role(schema_role):
            domain = _domain_for_role_family(ROLE_FAMILY_BANKING_FINANCE, candidate, raw_cv_text)
            return RoleResolution(
                display_role=banking_finance_role,
                role_family=ROLE_FAMILY_BANKING_FINANCE,
                domain=domain,
                confidence="high",
                source="banking_finance_profile",
                github_policy=_github_policy_for_domain(domain),
                overrode_current_title=True,
                reason="banking_finance_evidence_overrode_short_training_title",
            )

        if (
            is_training_or_volunteer_role(schema_role)
            and best_family not in {ROLE_FAMILY_UNCLEAR, ROLE_FAMILY_EDUCATION_TRAINING}
            and best_family_score >= 6
        ):
            domain = _domain_for_role_family(best_family, candidate, raw_cv_text)
            return RoleResolution(
                display_role=ROLE_FAMILY_DISPLAY_ROLES[best_family],
                role_family=best_family,
                domain=domain,
                confidence=_confidence_for_score(best_family_score),
                source="evidence_family",
                github_policy=_github_policy_for_domain(domain),
                overrode_current_title=True,
                reason="stronger_non_training_evidence_overrode_training_title",
            )

        family = schema_family or ROLE_FAMILY_UNCLEAR
        domain = _domain_for_role_family(family, candidate, raw_cv_text)
        return RoleResolution(
            display_role=schema_role,
            role_family=family,
            domain=domain,
            confidence=_confidence_for_score(best_family_score or 4),
            source="schema",
            github_policy=_github_policy_for_domain(domain),
            overrode_current_title=False,
            reason="specific_current_title_used",
        )

    if banking_finance_role:
        domain = _domain_for_role_family(ROLE_FAMILY_BANKING_FINANCE, candidate, raw_cv_text)
        return RoleResolution(
            display_role=banking_finance_role,
            role_family=ROLE_FAMILY_BANKING_FINANCE,
            domain=domain,
            confidence="high",
            source="banking_finance_profile",
            github_policy=_github_policy_for_domain(domain),
            overrode_current_title=False,
            reason="banking_finance_evidence_from_summary_education_skills",
        )

    summary_role = _role_from_summary(_field(candidate, "summary"))
    if summary_role:
        family = _role_family_from_text(summary_role) or best_family
        domain = _domain_for_role_family(family, candidate, raw_cv_text)
        return RoleResolution(
            display_role=summary_role,
            role_family=family,
            domain=domain,
            confidence=_confidence_for_score(best_family_score),
            source="summary",
            github_policy=_github_policy_for_domain(domain),
            overrode_current_title=False,
            reason="summary_role_used",
        )

    if best_family != ROLE_FAMILY_UNCLEAR and best_family_score >= 6:
        domain = _domain_for_role_family(best_family, candidate, raw_cv_text)
        return RoleResolution(
            display_role=ROLE_FAMILY_DISPLAY_ROLES[best_family],
            role_family=best_family,
            domain=domain,
            confidence=_confidence_for_score(best_family_score),
            source="evidence_family",
            github_policy=_github_policy_for_domain(domain),
            overrode_current_title=False,
            reason="multi_signal_role_family_used",
        )

    experience_role = _role_from_experience(candidate)
    if experience_role:
        family = _role_family_from_text(experience_role) or best_family
        domain = _domain_for_role_family(family, candidate, raw_cv_text)
        return RoleResolution(
            display_role=experience_role,
            role_family=family,
            domain=domain,
            confidence=_confidence_for_score(best_family_score),
            source="work_experience",
            github_policy=_github_policy_for_domain(domain),
            overrode_current_title=False,
            reason="experience_role_used",
        )

    return RoleResolution(
        display_role=ROLE_FOCUS_NEEDS_CLARIFICATION,
        role_family=ROLE_FAMILY_UNCLEAR,
        domain=UNCLEAR,
        confidence="unknown",
        source="missing",
        github_policy=SKIP_UNCLEAR,
        overrode_current_title=False,
        reason="insufficient_role_evidence",
    )


def resolve_candidate_display_role_with_source(
    candidate: Any,
    raw_cv_text: str | None = None,
) -> tuple[str | None, str]:
    resolution = resolve_candidate_role_resolution(candidate, raw_cv_text)
    return resolution.display_role, resolution.source


def resolve_candidate_display_role(
    candidate: Any,
    raw_cv_text: str | None = None,
) -> str | None:
    return resolve_candidate_role_resolution(candidate, raw_cv_text).display_role


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
    resolution = resolve_candidate_role_resolution(candidate, raw_cv_text)
    if resolution.role_family != ROLE_FAMILY_UNCLEAR:
        return resolution.domain, f"{resolution.source}:{resolution.role_family}"

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
