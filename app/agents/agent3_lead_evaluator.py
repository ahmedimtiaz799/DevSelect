import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.state import DevSelectState
from app.config import settings
from app.prompts.agent3_prompt import AGENT3_SYSTEM_PROMPT

logger = logging.getLogger("devselect")


async def agent_3_lead_evaluator(state: DevSelectState) -> dict:
    thread_id = state.get("thread_id", "unknown")
    candidate = state.get("candidate")
    github = state.get("github_analysis")
    error = state.get("error")

    logger.info(f"Agent 3 generating report for thread {thread_id}")

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-pro",
        google_api_key=settings.GEMINI_API_KEY,
        temperature=0.2,
        streaming=True,
    )

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

    report_text = ""
    try:
        async for chunk in llm.astream(messages):
            if chunk.content:
                report_text += chunk.content
    except Exception as e:
        logger.error(f"Gemini call failed: {e}")
        raise

    logger.info(f"Agent 3 completed report for thread {thread_id}")

    return {
        "report": report_text,
        "error": error,
    }


def _format_candidate(candidate) -> str:
    if not candidate:
        return "Candidate extraction failed because no data is available in CV."

    return f"""
Name:           {candidate.name or 'Not found'}
Email:          {candidate.email or 'Not found'}
Phone:          {candidate.phone or 'Not found'}
Role:           {candidate.role or 'Not detected'}
Seniority:      {candidate.seniority or 'Not detected'}
Years of Exp:   {candidate.years_of_experience or 'Not found'}
Skills:         {', '.join(candidate.skills) if candidate.skills else 'None listed'}
Education:      {candidate.education or 'Not found'}
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
Profile URL:            {github.profile_url or 'N/A'}
Total Repositories:     {github.total_repos}
Original Repos:         {github.original_repos}
Forked Repos:           {github.forked_repos}
Primary Languages:      {', '.join(github.primary_languages) if github.primary_languages else 'None detected'}
Last Active:            {github.last_active or 'Unknown'}
Account Created:        {github.account_created or 'Unknown'}
Total Commits:          {github.total_commits}
Commit Consistency:     {github.commit_consistency or 'Not assessed'}
README Quality:         {github.readme_quality or 'Not assessed'}
Avg Commit Msg Quality: {github.avg_commit_message_quality or 'Not assessed'}

Repository Highlights:
{_format_repos(github.repositories)}

Raw Analysis Notes:
{github.raw_analysis or 'None'}
""".strip()


def _format_experience(work_experience) -> str:
    if not work_experience:
        return "Work experience is not found in CV."

    lines = []
    for job in work_experience:
        lines.append(
            f"  - {job.title} at {job.company} "
            f"({job.start_date} — {job.end_date or 'Present'})"
        )
    return "\n".join(lines)


def _format_repos(repositories) -> str:
    if not repositories:
        return "Repository data is not available."

    lines = []
    for repo in repositories[:5]:
        lines.append(
            f"  - {repo.name} | Stars: {repo.stars} | "
            f"Language: {repo.language} | "
            f"Description: {repo.description or 'None'}"
        )
    return "\n".join(lines)