import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.state import DevSelectState
from app.config import settings
from app.prompts.agent3_prompt import AGENT3_SYSTEM_PROMPT

logger = logging.getLogger("devselect")

PRIMARY_MODEL = "gemini-2.5-pro"
FALLBACK_MODEL = "gemini-2.5-flash"


async def _stream_with_fallback(messages: list) -> str:
    for model_name in [PRIMARY_MODEL, FALLBACK_MODEL]:
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.2,
            streaming=True,
            max_retries=0,
        )
        try:
            report_text = ""
            async for chunk in llm.astream(messages):
                if chunk.content:
                    report_text += chunk.content
            if model_name == FALLBACK_MODEL:
                logger.warning(f"Agent 3: used fallback model {FALLBACK_MODEL} — primary quota exhausted.")
            return report_text
        except Exception as e:
            error_str = str(e).lower()
            is_quota_error = "429" in error_str or "quota" in error_str or "resource_exhausted" in error_str
            if is_quota_error and model_name == PRIMARY_MODEL:
                logger.warning(f"Agent 3: {PRIMARY_MODEL} quota exhausted, retrying with {FALLBACK_MODEL}.")
                continue
            raise

    raise RuntimeError(
        f"Both {PRIMARY_MODEL} and {FALLBACK_MODEL} failed due to quota limits. "
        "Please try again later or enable billing on your Google AI project."
    )


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
        report_text = await _stream_with_fallback(messages)
    except Exception as e:
        logger.error(f"Agent 3 failed for thread {thread_id}: {e}")
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