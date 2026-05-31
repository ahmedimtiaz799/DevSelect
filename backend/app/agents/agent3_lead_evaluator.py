import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.state import DevSelectState
from app.config import settings
from app.prompts.agent3_prompt import AGENT3_SYSTEM_PROMPT
from app.utils.llm_observability import (
    estimate_tokens_from_messages,
    log_llm_request,
    log_llm_usage,
)

logger = logging.getLogger("devselect")

PRIMARY_MODEL = "gemini-2.5-pro"
FALLBACK_MODEL = "gemini-2.5-flash"
GEMINI_QUOTA_RETRY_AFTER_SECONDS = 20


class GeminiQuotaExceededError(Exception):
    code = "GEMINI_QUOTA_EXCEEDED"
    user_message = "Gemini quota reached. Please wait and try again."
    retry_after_seconds = GEMINI_QUOTA_RETRY_AFTER_SECONDS

    def __init__(self, model_name: str, original_error: Exception):
        super().__init__(f"Gemini quota exceeded for {model_name}: {original_error}")


def _is_gemini_quota_error(error: Exception) -> bool:
    error_str = str(error).lower()
    return (
        "429" in error_str
        or "quota" in error_str
        or "resource_exhausted" in error_str
        or "rate limit" in error_str
        or "too many requests" in error_str
    )


async def _stream_with_fallback(messages: list, thread_id: str | None = None) -> str:
    estimated_input_tokens = estimate_tokens_from_messages(messages)

    for model_name in [PRIMARY_MODEL, FALLBACK_MODEL]:
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.2,
            streaming=True,
            max_tokens=settings.AGENT3_MAX_OUTPUT_TOKENS,
            request_timeout=settings.GEMINI_TIMEOUT_SECONDS,
            max_retries=0,
        )
        try:
            log_llm_request(
                logger,
                "agent3",
                model_name,
                thread_id,
                estimated_input_tokens,
                settings.AGENT3_MAX_OUTPUT_TOKENS,
            )
            report_text = ""
            usage_source = None
            async for chunk in llm.astream(messages):
                if (
                    getattr(chunk, "usage_metadata", None)
                    or getattr(chunk, "response_metadata", None)
                ):
                    usage_source = chunk
                if chunk.content:
                    report_text += chunk.content
            log_llm_usage(logger, "agent3", model_name, thread_id, usage_source)
            if model_name == FALLBACK_MODEL:
                logger.warning(f"Agent 3: used fallback model {FALLBACK_MODEL} — primary quota exhausted.")
            return report_text
        except Exception as e:
            if _is_gemini_quota_error(e):
                logger.warning(f"Agent 3: {model_name} quota/rate limit error: {e}")
                if model_name == PRIMARY_MODEL:
                    logger.warning(f"Agent 3: {PRIMARY_MODEL} quota exhausted, retrying with {FALLBACK_MODEL}.")
                    continue
                raise GeminiQuotaExceededError(model_name, e) from e
            raise

    raise GeminiQuotaExceededError(PRIMARY_MODEL, RuntimeError("Fallback was not attempted."))


async def agent3_lead_evaluator(state: DevSelectState) -> dict:
    thread_id = state.get("thread_id", "unknown")
    candidate = state.get("candidate")
    github = state.get("github_analysis")
    error = state.get("error")

    logger.info(f"Agent 3 generating report for thread {thread_id}")

    candidate_section = _format_candidate(candidate)
    github_section = _format_github(github)

    user_message = f"""
Please evaluate the following candidate and generate a structured hiring report.

--- CANDIDATE DATA (from CV) ---
{candidate_section}

--- GITHUB ANALYSIS DATA ---
{github_section}
"""

    messages = [
        SystemMessage(content=AGENT3_SYSTEM_PROMPT),
        HumanMessage(content=user_message),
    ]

    try:
        report_text = await _stream_with_fallback(messages, thread_id=thread_id)
    except GeminiQuotaExceededError as e:
        logger.exception(f"Agent 3 quota exhausted for thread {thread_id}: {e}")
        raise
    except Exception as e:
        logger.exception(f"Agent 3 failed for thread {thread_id}: {e}")
        raise

    logger.info(f"Agent 3 completed report for thread {thread_id}")

    return {
        "report": report_text,
        "error": error,
    }


def _format_candidate(candidate) -> str:
    if not candidate:
        return "Candidate extraction failed because no data is available in CV."

    education_str = (
        "; ".join(
            f"{e.degree or 'N/A'} from {e.institution or 'N/A'} ({e.year or 'N/A'})"
            for e in candidate.education
        )
        if candidate.education
        else "Not found"
    )

    return f"""
Name:           {candidate.full_name or 'Not found'}
Email:          {candidate.email or 'Not found'}
Phone:          {candidate.phone or 'Not found'}
Role:           {candidate.current_title or 'Not detected'}
Years of Exp:   {candidate.years_of_experience or 'Not found'}
Skills:         {', '.join(candidate.skills) if candidate.skills else 'None listed'}
Education:      {education_str}
GitHub URL:     {str(candidate.github_url) if candidate.github_url else 'Not found'}

Work Experience:
{_format_experience(candidate.work_experience)}

Summary:
{candidate.summary or 'No summary found in CV'}
""".strip()


def _format_github(github) -> str:
    if not github:
        return "Github analysis was not performed."

    scenario = github.scenario

    if scenario == "NOT_FOUND":
        return "GitHub Not Found. No GitHub link was present in the CV."

    if scenario == "COULD_NOT_BE_ACCESSED":
        return "GitHub Profile Could Not Be Accessed. The link in the CV was broken or invalid."

    if scenario == "PRIVATE":
        return "GitHub Profile Is Private. Skill Match Assessment Could Not Be Completed."

    return f"""
Scenario:               {scenario}
Overall Score:          {github.overall_score}/10
Summary:                {github.summary}
Total Commits:          {github.total_commits}
Active Days/Month:      {github.active_days_per_month}

Scores:
  Original Repos:       {github.original_repo_score}/10
  Commit Frequency:     {github.commit_frequency_score}/10
  Commit Messages:      {github.commit_message_score}/10
  Language Relevance:   {github.language_relevance_score}/10
  README Quality:       {github.readme_quality_score}/10
  Project Complexity:   {github.project_complexity_score}/10
  Recency:              {github.recency_score}/10
  Community:            {github.community_score}/10

Language Breakdown:     {github.language_breakdown}
Top Repos:              {', '.join(github.top_repos) if github.top_repos else 'None identified'}
Strengths:              {'; '.join(github.strengths) if github.strengths else 'None noted'}
Red Flags:              {'; '.join(github.red_flags) if github.red_flags else 'None'}
""".strip()


def _format_experience(work_experience) -> str:
    if not work_experience:
        return "Work experience is not found in CV."

    lines = []
    for job in work_experience:
        title = job.title or "Unknown Title"
        company = job.company or "Unknown Company"
        duration = job.duration or "N/A"
        lines.append(f"  - {title} at {company} ({duration})")
    return "\n".join(lines)
