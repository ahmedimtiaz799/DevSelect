from typing import Any


GENERIC_ERROR_CODE = "REQUEST_FAILED"
GENERIC_ERROR_MESSAGE = "The request could not be completed. Please try again."
GENERIC_SERVER_ERROR_MESSAGE = "An unexpected error occurred. Please try again."

PUBLIC_ERROR_MESSAGES = {
    "REQUEST_FAILED": GENERIC_ERROR_MESSAGE,
    "EVALUATION_FAILED": "Evaluation failed. Please try again.",
    "EVALUATION_PIPELINE_ERROR": "Evaluation failed. Please try again.",
    "EVALUATION_UPLOAD_FAILED": "Evaluation could not be started. Please try again.",
    "EVALUATION_PREPARATION_FAILED": "Evaluation could not be prepared. Please try again.",
    "EVALUATION_LOCK_UNAVAILABLE": "Evaluation admission is temporarily unavailable. Please try again later.",
    "EVALUATION_ALREADY_IN_PROGRESS": "An evaluation is already in progress for this chat.",
    "PDF_PARSE_TIMEOUT": "This file took too long to process. Please upload a standard PDF CV.",
    "PDF_PROCESSING_FAILED": "This file could not be processed safely. Please upload a standard PDF CV.",
    "NOT_A_CV": "This PDF does not look like a candidate CV. Please upload a CV or resume PDF.",
    "CV_EXTRACTION_INVALID": "This PDF could not be read as a candidate CV. Please upload a standard CV or resume PDF.",
    "CANDIDATE_EVIDENCE_INCOMPLETE": "The CV evidence could not be prepared reliably. Please try another CV.",
    "GROQ_VALIDATION_FAILED": "The AI response could not be validated. Please try again.",
    "GITHUB_RATE_LIMITED": "GitHub is temporarily rate-limited. Please try again later.",
    "GITHUB_DATA_UNAVAILABLE": "GitHub data is temporarily unavailable. Please try again later.",
    "GITHUB_ANALYSIS_INVALID": "GitHub analysis could not be completed reliably. Please try again.",
    "GITHUB_ANALYSIS_FAILED": "GitHub analysis is temporarily unavailable. Please try again.",
    "REPORT_EVIDENCE_VALIDATION_FAILED": "The evaluation report could not be verified against the available evidence. Please try again.",
    "LLM_PROVIDER_CONFIGURATION_ERROR": "AI evaluation is temporarily unavailable. Please try again later.",
    "GEMINI_RATE_LIMITED": "Gemini is temporarily rate-limited. Please try again in a few minutes.",
    "GROQ_RATE_LIMITED": "Groq is temporarily rate-limited. Please try again in a few minutes.",
    "GEMINI_QUOTA_EXCEEDED": "The AI provider is temporarily rate-limited. Please try again in a few minutes.",
    "GEMINI_PROVIDER_UNAVAILABLE": "Gemini is temporarily overloaded. Please try again in a few minutes.",
    "GROQ_TEMPORARILY_UNAVAILABLE": "Groq is temporarily unavailable. Please try again in a few minutes.",
    "GEMINI_TIMEOUT": "Gemini timed out while generating the evaluation. Please try again in a few minutes.",
    "FOLLOW_UP_FAILED": "Follow-up answer failed. Please try again.",
    "FOLLOW_UP_INCOMPLETE": "Follow-up answer could not be completed. Please try again.",
    "RATE_LIMIT_EXCEEDED": "Too many requests. Please slow down.",
    "GLOBAL_DAILY_EVALUATION_LIMIT_REACHED": "DevSelect has reached its evaluation capacity for today. Please try again tomorrow.",
    "GLOBAL_MONTHLY_EVALUATION_LIMIT_REACHED": "DevSelect has reached its evaluation capacity for this month.",
    "USER_DAILY_EVALUATION_LIMIT_REACHED": "Your daily evaluation limit has been reached. Please try again tomorrow.",
    "USER_LIFETIME_EVALUATION_LIMIT_REACHED": "Your portfolio evaluation allowance has been used.",
    "FOLLOWUP_EVALUATION_LIMIT_REACHED": "This evaluation has reached its follow-up limit.",
    "FOLLOWUP_USER_DAILY_LIMIT_REACHED": "Your daily follow-up limit has been reached. Please try again tomorrow.",
    "DAILY_USER_TOKEN_LIMIT_REACHED": "Your daily AI budget limit has been reached. Please try again tomorrow.",
    "DAILY_GLOBAL_TOKEN_LIMIT_REACHED": "DevSelect has reached its daily AI budget. Please try again tomorrow.",
    "BUDGET_REDIS_UNAVAILABLE": "AI quota enforcement is temporarily unavailable. Please try again later.",
    "BUDGET_ENFORCEMENT_DISABLED": "AI quota enforcement is not available.",
}

SAFE_HTTP_DETAILS = {
    "Authorization header missing",
    "Invalid token",
    "Token has expired",
    "Invalid token payload",
    "You do not have access to this chat.",
    "This evaluation session is no longer available. Please start a new evaluation.",
    "This evaluation session could not be restored. Please upload the CV again.",
    "Evaluation state is temporarily unavailable. Please try again.",
    "Follow-up question is required.",
    "Stop the active evaluation before deleting this chat.",
    "Chat cleanup is temporarily unavailable. Please try again.",
    "Invalid admin secret.",
}


def public_error_payload(
    code: str | None,
    *,
    default_code: str = GENERIC_ERROR_CODE,
    retry_after_seconds: Any = None,
) -> dict[str, Any]:
    safe_default = (
        default_code
        if default_code in PUBLIC_ERROR_MESSAGES
        else GENERIC_ERROR_CODE
    )
    safe_code = code if code in PUBLIC_ERROR_MESSAGES else safe_default
    payload: dict[str, Any] = {
        "error": PUBLIC_ERROR_MESSAGES[safe_code],
        "code": safe_code,
    }

    try:
        retry_after = int(retry_after_seconds)
    except (TypeError, ValueError):
        retry_after = 0
    if retry_after > 0:
        payload["retry_after_seconds"] = retry_after

    return payload


def sanitize_http_exception_detail(detail: Any, status_code: int) -> str:
    if status_code >= 500:
        return GENERIC_SERVER_ERROR_MESSAGE
    if isinstance(detail, str) and detail in SAFE_HTTP_DETAILS:
        return detail
    if status_code == 401:
        return "Authentication is required."
    if status_code == 403:
        return "You do not have permission to perform this action."
    if status_code == 404:
        return "The requested resource was not found."
    if status_code == 409:
        return "The request conflicts with the current state."
    if status_code == 429:
        return PUBLIC_ERROR_MESSAGES["RATE_LIMIT_EXCEEDED"]
    if status_code in {400, 422}:
        return "Invalid request data."
    return GENERIC_ERROR_MESSAGE
