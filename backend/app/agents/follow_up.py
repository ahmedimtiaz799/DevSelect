import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.agents.agent3_lead_evaluator import GeminiQuotaExceededError
from app.config import settings
from app.utils.llm_observability import (
    cap_text_for_llm,
    estimate_tokens_from_messages,
    log_llm_request,
    log_llm_usage,
)

logger = logging.getLogger("devselect")

FOLLOW_UP_MODEL = "gemini-2.5-flash"
FOLLOW_UP_SYSTEM_PROMPT = """
You are DevSelect's hiring evaluation assistant.
Answer the recruiter's follow-up question using only the completed evaluation report and available stored evaluation context.
Do not rerun the evaluation.
Do not invent facts not present in the report or context.
If the question asks for a new judgment requiring new information, explain that re-evaluation requires new candidate data.
Keep the answer concise, professional, and useful.
""".strip()


async def answer_follow_up_question(
    report_context: str,
    question: str,
    chat_id: str | None = None,
) -> str:
    capped_report, original_report_chars, report_chars, report_truncated = cap_text_for_llm(
        report_context,
        settings.FOLLOW_UP_MAX_CONTEXT_CHARS,
    )
    capped_question, original_question_chars, question_chars, question_truncated = cap_text_for_llm(
        question,
        settings.FOLLOW_UP_MAX_QUESTION_CHARS,
    )
    logger.info(
        "Follow-up prompt input : chat=%s report_context_chars=%s capped_report_context_chars=%s report_truncated=%s follow_up_question_chars=%s capped_follow_up_question_chars=%s question_truncated=%s",
        chat_id or "unknown",
        original_report_chars,
        report_chars,
        report_truncated,
        original_question_chars,
        question_chars,
        question_truncated,
    )

    human_message = f"""
Context:
{capped_report}

Recruiter question:
{capped_question}
""".strip()
    messages = [
        SystemMessage(content=FOLLOW_UP_SYSTEM_PROMPT),
        HumanMessage(content=human_message),
    ]
    estimated_input_tokens = estimate_tokens_from_messages(messages)
    llm = ChatGoogleGenerativeAI(
        model=FOLLOW_UP_MODEL,
        google_api_key=settings.GEMINI_API_KEY,
        temperature=0.2,
        max_tokens=settings.FOLLOW_UP_MAX_OUTPUT_TOKENS,
        request_timeout=settings.GEMINI_TIMEOUT_SECONDS,
        max_retries=0,
    )

    try:
        log_llm_request(
            logger,
            "follow_up",
            FOLLOW_UP_MODEL,
            chat_id,
            estimated_input_tokens,
            settings.FOLLOW_UP_MAX_OUTPUT_TOKENS,
        )
        response = await llm.ainvoke(messages)
        log_llm_usage(logger, "follow_up", FOLLOW_UP_MODEL, chat_id, response)
    except Exception as e:
        if _is_gemini_quota_error(e):
            logger.warning(f"Follow-up Gemini quota/rate limit error : chat={chat_id} error={e}")
            raise GeminiQuotaExceededError(FOLLOW_UP_MODEL, e) from e
        raise

    answer = str(response.content or "").strip()
    return answer or "I could not generate a follow-up answer. Please try again."


def mock_follow_up_answer(question: str) -> str:
    question_lower = question.lower()
    if "strong hire" in question_lower:
        return "I cannot change the recommendation without new evidence. Based on the completed report, the recommendation should remain tied to the documented strengths, risks, and validation gaps."

    if "interview" in question_lower or "ask" in question_lower:
        return "Focus the interview on the areas highlighted in the report: practical project ownership, technical depth in the target stack, testing habits, and how the candidate explains tradeoffs in shipped work."

    if "risk" in question_lower:
        return "The main risk is the area the report flags as least proven. Use the interview to validate that gap with concrete examples rather than relying on claims alone."

    return "Based on the completed report, the candidate should be assessed against the documented strengths, risks, and role fit. I would keep the decision evidence-based and ask follow-up interview questions around any unclear areas."


def _is_gemini_quota_error(error: Exception) -> bool:
    error_str = str(error).lower()
    return (
        "429" in error_str
        or "quota" in error_str
        or "resource_exhausted" in error_str
        or "rate limit" in error_str
        or "too many requests" in error_str
    )
