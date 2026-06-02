import re


CONTACT_PATTERNS = {
    "email": re.compile(r"\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b", re.IGNORECASE),
    "phone": re.compile(r"(?:\+?\d[\d\s().-]{7,}\d)"),
    "linkedin": re.compile(r"\blinkedin\.com/in/|\blinkedin\b", re.IGNORECASE),
    "github": re.compile(r"\bgithub\.com/|\bgithub\b", re.IGNORECASE),
    "portfolio": re.compile(r"\bportfolio\b|\bpersonal website\b|\bwebsite\b|https?://", re.IGNORECASE),
}

SIGNAL_GROUPS = {
    "education": [
        "university",
        "college",
        "school",
        "degree",
        "bachelor",
        "bs",
        "bsc",
        "ms",
        "msc",
        "masters",
        "cgpa",
        "gpa",
        "graduation",
        "academic background",
        "qualification",
    ],
    "career": [
        "experience",
        "employment",
        "work history",
        "professional background",
        "internship",
        "intern",
        "company",
        "role",
        "responsibilities",
        "achievements",
    ],
    "skills": [
        "skills",
        "technical skills",
        "tools",
        "technologies",
        "programming",
        "react",
        "javascript",
        "python",
        "fastapi",
        "sql",
        "docker",
        "git",
        "machine learning",
        "ai",
        "langgraph",
        "rag",
    ],
    "projects": [
        "projects",
        "portfolio",
        "selected work",
        "built",
        "developed",
        "implemented",
        "deployed",
        "github",
    ],
}

NEGATIVE_GROUPS = {
    "billing": [
        "invoice",
        "bill to",
        "tax invoice",
        "subtotal",
        "total amount",
        "payment terms",
        "receipt",
        "purchase order",
    ],
    "legal": [
        "contract agreement",
        "service agreement",
        "terms and conditions",
        "whereas",
        "party of the first part",
        "governing law",
    ],
    "article": [
        "table of contents",
        "chapter",
        "abstract",
        "references",
        "bibliography",
        "journal",
        "doi",
    ],
    "certificate": [
        "certificate of completion",
        "certificate of achievement",
        "awarded to",
        "certifies that",
    ],
}


def assess_cv_likeness(
    text: str,
    min_text_chars: int = 300,
    min_score: int = 3,
) -> dict:
    value = text or ""
    compact = re.sub(r"\s+", " ", value).strip()
    lowered = compact.lower()
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    text_chars = len(compact)

    if text_chars < min_text_chars:
        return {
            "is_likely_cv": True,
            "should_reject": False,
            "score": 0,
            "negative_score": 0,
            "reasons": ["low_text_allowed"],
            "decision_reason": "low_text_allowed",
            "signal_categories": [],
            "negative_categories": [],
            "text_chars": text_chars,
            "low_text": True,
        }

    score = 0
    signal_categories = []
    reasons = []

    contact_matches = [
        name for name, pattern in CONTACT_PATTERNS.items()
        if pattern.search(compact)
    ]
    if contact_matches:
        score += 2 if len(contact_matches) >= 2 else 1
        signal_categories.append("contact")
        reasons.extend(f"contact:{name}" for name in contact_matches[:3])

    for category, terms in SIGNAL_GROUPS.items():
        matches = _matched_terms(lowered, terms)
        if matches:
            score += 2 if category in {"career", "skills"} else 1
            signal_categories.append(category)
            reasons.append(f"{category}:{','.join(matches[:3])}")

    structure_score, structure_reasons = _structure_score(lines, compact)
    if structure_score:
        score += structure_score
        signal_categories.append("structure")
        reasons.extend(structure_reasons)

    negative_score = 0
    negative_categories = []
    for category, terms in NEGATIVE_GROUPS.items():
        matches = _matched_terms(lowered, terms)
        if matches:
            negative_categories.append(category)
            negative_score += min(2, len(matches))

    positive_categories = set(signal_categories)
    content_categories = positive_categories - {"structure"}
    core_categories = content_categories & {"career", "education", "skills", "projects"}
    has_multiple_content_groups = len(content_categories) >= 2
    has_contact_core_combo = "contact" in content_categories and bool(core_categories)
    has_cv_signal_shape = has_multiple_content_groups or has_contact_core_combo
    strong_negative_signal = negative_score >= 3 or len(set(negative_categories)) >= 2
    negative_dominates = strong_negative_signal and (
        not has_cv_signal_shape or negative_score >= score
    )
    clearly_low_cv_signal = (
        score < min_score
        or (not has_cv_signal_shape and score < min_score + 2)
    )
    should_reject = negative_dominates or clearly_low_cv_signal
    if negative_dominates:
        decision_reason = "negative_categories_dominated"
    elif clearly_low_cv_signal:
        decision_reason = "insufficient_cv_signal_groups"
    else:
        decision_reason = "cv_signal_groups_present"

    return {
        "is_likely_cv": not should_reject,
        "should_reject": should_reject,
        "score": score,
        "negative_score": negative_score,
        "reasons": reasons,
        "decision_reason": decision_reason,
        "signal_categories": sorted(set(signal_categories)),
        "negative_categories": sorted(set(negative_categories)),
        "text_chars": text_chars,
        "low_text": False,
    }


def _matched_terms(lowered: str, terms: list[str]) -> list[str]:
    matches = []
    for term in terms:
        pattern = r"\b" + re.escape(term).replace(r"\ ", r"\s+") + r"\b"
        if re.search(pattern, lowered):
            matches.append(term)
    return matches


def _structure_score(lines: list[str], compact: str) -> tuple[int, list[str]]:
    score = 0
    reasons = []

    bullet_count = sum(1 for line in lines if re.match(r"^\s*(?:[-*]|\u2022)\s+", line))
    if bullet_count >= 3:
        score += 1
        reasons.append("structure:bullets")

    if re.search(r"\b(?:19|20)\d{2}\s*(?:-|to|\u2013|\u2014)\s*(?:present|current|(?:19|20)\d{2})\b", compact, re.IGNORECASE):
        score += 1
        reasons.append("structure:date_ranges")

    heading_count = sum(
        1 for line in lines
        if 2 <= len(line) <= 45
        and len(line.split()) <= 5
        and not line.endswith(".")
        and re.search(r"[A-Za-z]", line)
    )
    if heading_count >= 3:
        score += 1
        reasons.append("structure:headings")

    top_text = "\n".join(lines[:12])
    if re.search(r"@|https?://|github|linkedin|\+?\d[\d\s().-]{7,}\d", top_text, re.IGNORECASE):
        score += 1
        reasons.append("structure:top_contact")

    return min(score, 2), reasons[:2]
