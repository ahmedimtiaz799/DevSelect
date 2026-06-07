import json
import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx
from pydantic import ValidationError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.agents.state import DevSelectState
from app.config import settings
from app.models.candidate import GitHubAnalysis, GitHubAnalysisStatus, GitHubScenario
from app.prompts.agent2_prompt import AGENT2_PROMPT
from app.utils.llm_observability import (
    cap_text_for_llm,
    estimate_tokens_from_text,
    log_llm_request,
    log_llm_usage,
)
from app.utils.llm_provider import (
    GROQ_PROVIDER,
    LLMProviderConfigurationError,
    create_chat_llm,
    current_ai_provider,
    llm_error_details,
    llm_model_name,
    llm_rate_limit_code,
    llm_rate_limit_message,
    llm_unavailable_code,
    llm_unavailable_message,
    structured_output_kwargs,
)

logger = logging.getLogger("devselect")

GITHUB_GRAPHQL_QUERY = """
query FetchDeveloperProfile($login: String!) {
  user(login: $login) {
    login
    name
    bio
    location
    createdAt
    repositories(
      first: 30
      isFork: false
      orderBy: { field: PUSHED_AT, direction: DESC }
      privacy: PUBLIC
    ) {
      totalCount
      nodes {
        name
        description
        primaryLanguage {
          name
        }
        languages(first: 5, orderBy: { field: SIZE, direction: DESC }) {
          edges {
            size
            node {
              name
            }
          }
        }
        stargazerCount
        forkCount
        pushedAt
        createdAt
        isFork
        object(expression: "HEAD:README.md") {
          ... on Blob {
            text
            byteSize
          }
        }
        defaultBranchRef {
          target {
            ... on Commit {
              history(first: 10) {
                totalCount
                nodes {
                  message
                  committedDate
                }
              }
            }
          }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            contributionCount
            date
          }
        }
      }
    }
  }
}
"""


def _extract_username(github_url: str) -> str:
    clean_url = github_url.strip().rstrip("/")
    if not clean_url:
        raise ValueError("Could not extract username from empty GitHub URL")

    if not clean_url.startswith(("http://", "https://")):
        clean_url = f"https://{clean_url}"

    parsed = urlparse(clean_url)
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]

    if host != "github.com":
        raise ValueError(f"Could not extract username from URL: {github_url}")

    path_parts = [part for part in parsed.path.split("/") if part]
    username = path_parts[0] if path_parts else ""
    if not username:
        raise ValueError(f"Could not extract username from URL: {github_url}")
    return username


class GitHubRateLimitError(Exception):
    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        provider_status: str = "rate_limited",
        retry_after_seconds: int | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.provider_status = provider_status
        self.retry_after_seconds = retry_after_seconds


class GitHubTransientError(Exception):
    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        provider_status: str = "unavailable",
    ):
        super().__init__(message)
        self.status_code = status_code
        self.provider_status = provider_status


class GeminiProviderError(Exception):
    def __init__(
        self,
        error_type: str,
        status_code: int | None,
        provider_status: str,
        retry_after_seconds: int | None,
        retryable: bool,
    ):
        super().__init__("LLM provider request failed.")
        self.error_type = error_type
        self.status_code = status_code
        self.provider_status = provider_status
        self.retry_after_seconds = retry_after_seconds
        self.retryable = retryable


class GeminiRateLimitError(GeminiProviderError):
    pass


class GeminiTransientError(GeminiProviderError):
    pass


class Agent2StructuredOutputError(Exception):
    pass


def _gemini_error_details(error: Exception) -> dict[str, Any]:
    details = llm_error_details(error)
    return {
        "error_type": details.error_type,
        "status_code": details.status_code,
        "provider_status": details.provider_status,
        "retry_after_seconds": details.retry_after_seconds,
        "rate_limited": details.rate_limited,
        "transient": details.transient,
    }


def _log_gemini_provider_failure(
    details: dict[str, Any],
    thread_id: str | None,
    retryable: bool,
    attempt: int,
) -> None:
    provider = current_ai_provider()
    model_name = llm_model_name("agent2")
    logger.warning(
        "Agent 2 provider failure : thread=%s step=structured_analysis provider=%s model=%s error_type=%s status_code=%s provider_status=%s retry_after_seconds=%s retryable=%s attempt=%s fallback=%s",
        thread_id or "unknown",
        provider,
        model_name,
        details["error_type"],
        details["status_code"] or "unknown",
        details["provider_status"],
        details["retry_after_seconds"] or "unknown",
        retryable,
        attempt,
        False,
    )


def _log_gemini_retry(retry_state) -> None:
    error = retry_state.outcome.exception()
    if not isinstance(error, GeminiTransientError):
        return

    _log_gemini_provider_failure(
        {
            "error_type": error.error_type,
            "status_code": error.status_code,
            "provider_status": error.provider_status,
            "retry_after_seconds": error.retry_after_seconds,
        },
        retry_state.args[2] if len(retry_state.args) > 2 else None,
        True,
        retry_state.attempt_number,
    )


def _candidate_field(candidate: Any, name: str, default=None):
    if isinstance(candidate, dict):
        return candidate.get(name, default)

    return getattr(candidate, name, default)


def _github_analysis_state(analysis: GitHubAnalysis) -> dict[str, Any]:
    return analysis.model_dump(mode="json")


def _response_text(response: Any) -> str:
    content = getattr(response, "content", "")
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        return "".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in content
        )

    return str(content or "")


def _response_finish_reason(response: Any) -> str:
    metadata = getattr(response, "response_metadata", None)
    if isinstance(metadata, dict):
        for key in ("finish_reason", "finishReason", "finish_reasons"):
            value = metadata.get(key)
            if value:
                return str(value)

    return "unknown"


def _response_usage_summary(response: Any) -> str:
    usage = getattr(response, "usage_metadata", None)
    if not usage:
        metadata = getattr(response, "response_metadata", None)
        if isinstance(metadata, dict):
            usage = metadata.get("usage_metadata") or metadata.get("token_usage")

    if not usage:
        return "unavailable"

    keys = (
        "input_tokens",
        "prompt_tokens",
        "output_tokens",
        "candidate_tokens",
        "total_tokens",
        "cached_tokens",
    )
    parts = []
    for key in keys:
        value = usage.get(key) if isinstance(usage, dict) else getattr(usage, key, None)
        if value is not None:
            parts.append(f"{key}={value}")

    return ", ".join(parts) if parts else str(type(usage).__name__)


def _validation_summary(error: Exception) -> str:
    if isinstance(error, ValidationError):
        summary = []
        for item in error.errors()[:5]:
            loc = ".".join(str(part) for part in item.get("loc", ()))
            err_type = item.get("type", "unknown")
            summary.append(f"{loc or 'root'}:{err_type}")
        return "; ".join(summary)

    return type(error).__name__


def _log_structured_output_failure(
    raw_response: Any,
    error: Exception,
    thread_id: str | None,
) -> None:
    text = _response_text(raw_response)
    logger.error(
        "Agent 2 structured GitHub analysis failed : thread=%s model=%s response_chars=%s first_200=%r last_200=%r finish_reason=%s usage=%s validation=%s error_type=%s",
        thread_id or "unknown",
        llm_model_name("agent2"),
        len(text),
        text[:200],
        text[-200:] if text else "",
        _response_finish_reason(raw_response),
        _response_usage_summary(raw_response),
        _validation_summary(error),
        type(error).__name__,
    )


GITHUB_ANALYSIS_FAILED_MESSAGE = "We could not complete the GitHub analysis. Please try again."
GITHUB_ANALYSIS_TEMPORARILY_UNAVAILABLE_MESSAGE = "We could not complete the GitHub analysis. Please try again in a few minutes."
GITHUB_DATA_TEMPORARILY_UNAVAILABLE_MESSAGE = "GitHub data is temporarily unavailable. Please try again in a few minutes."
GITHUB_PROFILE_ACCESS_FAILED_MESSAGE = "We could not access this GitHub profile. Please try again."
EVALUATION_PREPARATION_FAILED_MESSAGE = "We could not prepare this evaluation. Please upload the CV again."
GROQ_VALIDATION_FAILED_MESSAGE = "Groq returned an incomplete structured response. Please try again."


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(GitHubTransientError),
    reraise=True,
)
async def _query_github_graphql(username: str) -> dict:
    headers = {
        "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "query": GITHUB_GRAPHQL_QUERY,
        "variables": {"login": username},
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.github.com/graphql",
                headers=headers,
                json=payload,
            )

        logger.info(
            "Agent 2 GitHub GraphQL response : username=%s status_code=%s rate_remaining=%s",
            username,
            response.status_code,
            response.headers.get("X-RateLimit-Remaining", "unknown"),
        )

        if response.status_code == 403:
            remaining = response.headers.get("X-RateLimit-Remaining", "unknown")
            if remaining == "0" or "rate limit" in response.text.lower():
                raise GitHubRateLimitError(
                    "GitHub is temporarily limiting requests. Please retry in 60 seconds.",
                    status_code=response.status_code,
                    retry_after_seconds=60,
                )
            raise GitHubRateLimitError(
                GITHUB_PROFILE_ACCESS_FAILED_MESSAGE,
                status_code=response.status_code,
                provider_status="forbidden",
            )

        if response.status_code >= 500:
            raise GitHubTransientError(
                "GitHub API server error",
                status_code=response.status_code,
                provider_status="server_error",
            )

        response.raise_for_status()
        payload = response.json()
        errors = payload.get("errors") if isinstance(payload, dict) else None
        if errors:
            first_error = errors[0] if isinstance(errors, list) and errors else {}
            error_type = str(first_error.get("type") or "graphql_error")
            message = str(first_error.get("message") or "")
            lowered = message.lower()
            logger.warning(
                "Agent 2 GitHub GraphQL errors : username=%s error_type=%s",
                username,
                error_type,
            )
            if "rate limit" in lowered or "rate_limit" in error_type.lower():
                raise GitHubRateLimitError(
                    "GitHub is temporarily limiting requests. Please retry in 60 seconds.",
                    status_code=response.status_code,
                    provider_status=error_type,
                    retry_after_seconds=60,
                )
            raise GitHubTransientError(
                "GitHub GraphQL returned errors",
                status_code=response.status_code,
                provider_status=error_type,
            )

        return payload

    except httpx.TimeoutException as e:
        raise GitHubTransientError("GitHub API timeout", provider_status="timeout") from e
    except httpx.NetworkError as e:
        raise GitHubTransientError("GitHub API network error", provider_status="network_error") from e
    except httpx.HTTPStatusError as e:
        raise GitHubTransientError(
            "GitHub API returned an unexpected HTTP status",
            status_code=e.response.status_code,
            provider_status="http_error",
        ) from e
    except (GitHubRateLimitError, GitHubTransientError):
        raise
    except Exception as e:
        raise GitHubTransientError("Unexpected GitHub API error") from e


def _pre_score_profile(raw_data: dict) -> dict:
    user = raw_data.get("data", {}).get("user")
    if not user:
        return {}

    repos = user.get("repositories", {}).get("nodes", [])
    contributions = user.get("contributionsCollection", {})

    original_repos = [r for r in repos if not r.get("isFork")]
    repo_count = len(original_repos)

    language_sizes: dict[str, int] = {}
    for repo in original_repos:
        for edge in repo.get("languages", {}).get("edges", []):
            lang = edge["node"]["name"]
            size = edge["size"]
            language_sizes[lang] = language_sizes.get(lang, 0) + size

    total_size = sum(language_sizes.values()) or 1
    language_breakdown = {
        lang: round((size / total_size) * 100, 1)
        for lang, size in sorted(
            language_sizes.items(), key=lambda x: x[1], reverse=True
        )[:8]
    }

    repos_with_readme = sum(
        1 for r in original_repos
        if r.get("object") and r["object"].get("byteSize", 0) > 100
    )
    readme_ratio = repos_with_readme / repo_count if repo_count > 0 else 0

    commit_messages = []
    repository_commit_count = 0
    for repo in original_repos[:10]:
        branch = repo.get("defaultBranchRef")
        if branch:
            history = branch.get("target", {}).get("history", {})
            repository_commit_count += int(history.get("totalCount", 0) or 0)
            for node in history.get("nodes", []):
                commit_messages.append(node.get("message", "")[:100])

    profile_contribution_count = contributions.get("totalCommitContributions", 0)

    last_push = None
    for repo in original_repos:
        pushed = repo.get("pushedAt")
        if pushed:
            dt = datetime.fromisoformat(pushed.replace("Z", "+00:00"))
            if last_push is None or dt > last_push:
                last_push = dt

    days_since_last_push = None
    if last_push:
        days_since_last_push = (datetime.now(timezone.utc) - last_push).days

    total_stars = sum(r.get("stargazerCount", 0) for r in original_repos)

    return {
        "repo_count": repo_count,
        "language_breakdown": language_breakdown,
        "readme_ratio": readme_ratio,
        "commit_messages_sample": commit_messages[:20],
        "commit_message_sample_count": len(commit_messages[:20]),
        "profile_contribution_count": profile_contribution_count,
        "repository_commit_count": repository_commit_count,
        "total_commits": repository_commit_count,
        "days_since_last_push": days_since_last_push,
        "total_stars": total_stars,
        "repos_with_readme": repos_with_readme,
    }


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    retry=retry_if_exception_type(GeminiTransientError),
    before_sleep=_log_gemini_retry,
    reraise=True,
)
async def _analyse_with_gemini(
    raw_github_data: dict,
    cv_skills: list[str],
    thread_id: str | None = None,
) -> GitHubAnalysis:
    model_name = llm_model_name("agent2")
    llm = create_chat_llm(
        "agent2",
        temperature=0.2,
        max_tokens=settings.AGENT2_MAX_OUTPUT_TOKENS,
        max_retries=0,
    )
    structured_llm = llm.with_structured_output(
        GitHubAnalysis,
        **structured_output_kwargs(include_raw=True),
    )

    cv_skills_str = ", ".join(cv_skills) if cv_skills else "Not specified"
    github_data_str = json.dumps(raw_github_data, indent=2, default=str)
    github_data_str, original_github_chars, capped_github_chars, was_truncated = cap_text_for_llm(
        github_data_str,
        settings.AGENT2_MAX_INPUT_CHARS,
    )
    logger.info(
        "Agent 2: GitHub payload input cap thread=%s original_chars=%s capped_chars=%s truncated=%s",
        thread_id or "unknown",
        original_github_chars,
        capped_github_chars,
        was_truncated,
    )

    prompt = (
        AGENT2_PROMPT
        .replace("{cv_skills}", cv_skills_str)
        .replace("{github_data}", github_data_str)
    )
    estimated_input_tokens = estimate_tokens_from_text(prompt)

    try:
        log_llm_request(
            logger,
            "agent2",
            model_name,
            thread_id,
            estimated_input_tokens,
            settings.AGENT2_MAX_OUTPUT_TOKENS,
        )
        result = await structured_llm.ainvoke(prompt)
    except Exception as e:
        details = _gemini_error_details(e)
        if details["rate_limited"]:
            _log_gemini_provider_failure(details, thread_id, False, 1)
            raise GeminiRateLimitError(
                details["error_type"],
                details["status_code"],
                details["provider_status"],
                details["retry_after_seconds"],
                False,
            ) from e
        error_str = str(e).lower()
        if any(marker in error_str for marker in ("json", "parse", "parser", "validation", "schema")):
            _log_structured_output_failure(None, e, thread_id)
            raise Agent2StructuredOutputError("Agent 2 structured GitHub analysis failed.") from e
        if details["transient"]:
            raise GeminiTransientError(
                details["error_type"],
                details["status_code"],
                details["provider_status"],
                details["retry_after_seconds"],
                True,
            ) from e
        _log_gemini_provider_failure(details, thread_id, False, 1)
        raise GeminiProviderError(
            details["error_type"],
            details["status_code"],
            details["provider_status"],
            details["retry_after_seconds"],
            False,
        ) from e

    raw_response = result.get("raw") if isinstance(result, dict) else None
    log_llm_usage(logger, "agent2", model_name, thread_id, raw_response or result)
    finish_reason = _response_finish_reason(raw_response)
    if "MAX_TOKENS" in finish_reason.upper():
        error = Agent2StructuredOutputError("Agent 2 structured GitHub analysis reached the output limit.")
        _log_structured_output_failure(raw_response, error, thread_id)
        raise error

    if isinstance(result, GitHubAnalysis):
        return result

    if isinstance(result, dict):
        parsed = result.get("parsed")
        parsing_error = result.get("parsing_error")

        if parsing_error:
            _log_structured_output_failure(raw_response, parsing_error, thread_id)
            raise Agent2StructuredOutputError("Agent 2 structured GitHub analysis failed.") from parsing_error

        if isinstance(parsed, GitHubAnalysis):
            return parsed

        if isinstance(parsed, dict):
            try:
                return GitHubAnalysis.model_validate(parsed)
            except ValidationError as e:
                _log_structured_output_failure(raw_response, e, thread_id)
                raise Agent2StructuredOutputError("Agent 2 structured GitHub analysis failed.") from e

        if isinstance(parsed, str):
            try:
                return GitHubAnalysis.model_validate_json(parsed)
            except ValidationError as e:
                _log_structured_output_failure(raw_response, e, thread_id)
                raise Agent2StructuredOutputError("Agent 2 structured GitHub analysis failed.") from e

        error = TypeError(type(parsed).__name__)
        _log_structured_output_failure(raw_response, error, thread_id)
        raise Agent2StructuredOutputError("Agent 2 structured GitHub analysis failed.") from error

    error = TypeError(type(result).__name__)
    _log_structured_output_failure(None, error, thread_id)
    raise Agent2StructuredOutputError("Agent 2 structured GitHub analysis failed.") from error


async def agent2_github_analysis(state: DevSelectState) -> dict[str, Any]:
    thread_id = state.get("thread_id", "unknown")
    logger.info(f"Agent 2 starting for thread_id={thread_id}")

    if state.get("error"):
        logger.warning("Agent 2 skipping — error already set in state.")
        return {}

    candidate = state.get("candidate")
    if not candidate:
        return {"error": EVALUATION_PREPARATION_FAILED_MESSAGE}

    github_url = _candidate_field(candidate, "github_url")
    if not github_url:
        logger.info("Agent 2: No GitHub URL — creating minimal analysis.")
        return {
            "github_analysis": _github_analysis_state(GitHubAnalysis(
                scenario="NOT_FOUND",
                analysis_status="NOT_FOUND",
                summary="No GitHub profile was provided for this candidate.",
                overall_score=0,
                original_repo_score=0,
                commit_frequency_score=0,
                commit_message_score=0,
                language_relevance_score=0,
                readme_quality_score=0,
                project_complexity_score=0,
                recency_score=0,
                community_score=0,
                strengths=[],
                red_flags=["No GitHub profile available for analysis."],
                top_repos=[],
                language_breakdown={},
                original_repo_count=None,
                repos_with_readme=None,
                total_commits=None,
                profile_contribution_count=None,
                repository_commit_count=None,
                commit_message_sample_count=None,
                recent_activity_days=None,
                active_days_per_month=None,
            ))
        }

    try:
        username = _extract_username(github_url)
    except ValueError:
        return {"error": "We could not read the GitHub profile URL. Please check the URL and try again."}

    try:
        logger.info(f"Agent 2: Querying GitHub GraphQL for '{username}'...")
        raw_data = await _query_github_graphql(username)
        logger.info("Agent 2: GitHub GraphQL responded")
    except GitHubRateLimitError as e:
        logger.warning(
            "Agent 2 GitHub rate limit : thread=%s username=%s status_code=%s provider_status=%s retry_after_seconds=%s",
            thread_id,
            username,
            e.status_code or "unknown",
            e.provider_status,
            e.retry_after_seconds or "unknown",
        )
        return {
            "error": GITHUB_DATA_TEMPORARILY_UNAVAILABLE_MESSAGE,
            "error_code": "GITHUB_RATE_LIMITED",
            "retry_after_seconds": e.retry_after_seconds,
        }
    except GitHubTransientError as e:
        logger.warning(
            "Agent 2 GitHub unavailable : thread=%s username=%s status_code=%s provider_status=%s",
            thread_id,
            username,
            e.status_code or "unknown",
            e.provider_status,
        )
        return {
            "error": GITHUB_DATA_TEMPORARILY_UNAVAILABLE_MESSAGE,
            "error_code": "GITHUB_DATA_UNAVAILABLE",
        }
    except Exception as e:
        logger.error(
            "Agent 2 Step A failed : thread=%s username=%s error_type=%s",
            thread_id,
            username,
            type(e).__name__,
        )
        return {
            "error": GITHUB_DATA_TEMPORARILY_UNAVAILABLE_MESSAGE,
            "error_code": "GITHUB_DATA_UNAVAILABLE",
        }

    user_data = raw_data.get("data", {}).get("user")
    if user_data is None:
        logger.warning(f"Agent 2: GitHub user '{username}' not found.")
        return {
            "github_analysis": _github_analysis_state(GitHubAnalysis(
                scenario="COULD_NOT_BE_ACCESSED",
                analysis_status="UNAVAILABLE",
                summary=f"GitHub profile '{username}' was not found or is inaccessible.",
                overall_score=0,
                original_repo_score=0,
                commit_frequency_score=0,
                commit_message_score=0,
                language_relevance_score=0,
                readme_quality_score=0,
                project_complexity_score=0,
                recency_score=0,
                community_score=0,
                strengths=[],
                red_flags=[f"GitHub profile '{username}' returned 404."],
                top_repos=[],
                language_breakdown={},
                original_repo_count=None,
                repos_with_readme=None,
                total_commits=None,
                profile_contribution_count=None,
                repository_commit_count=None,
                commit_message_sample_count=None,
                recent_activity_days=None,
                active_days_per_month=None,
            ))
        }

    repos = user_data.get("repositories", {}).get("nodes", [])
    total_repo_count = user_data.get("repositories", {}).get("totalCount", 0)
    if total_repo_count > 0 and len(repos) == 0:
        logger.warning(f"Agent 2: GitHub profile '{username}' appears private.")
        return {
            "github_analysis": _github_analysis_state(GitHubAnalysis(
                scenario="PRIVATE",
                analysis_status="PRIVATE",
                summary=f"GitHub profile '{username}' exists but all repositories are private.",
                overall_score=0,
                original_repo_score=0,
                commit_frequency_score=0,
                commit_message_score=0,
                language_relevance_score=0,
                readme_quality_score=0,
                project_complexity_score=0,
                recency_score=0,
                community_score=0,
                strengths=[],
                red_flags=["All GitHub repositories are private — profile cannot be evaluated."],
                top_repos=[],
                language_breakdown={},
                original_repo_count=None,
                repos_with_readme=None,
                total_commits=None,
                profile_contribution_count=None,
                repository_commit_count=None,
                commit_message_sample_count=None,
                recent_activity_days=None,
                active_days_per_month=None,
            ))
        }

    logger.info("Agent 2: Running pre-scoring...")
    pre_scores = _pre_score_profile(raw_data)

    analysis_payload = {
        "user_profile": {
            "login": user_data.get("login"),
            "name": user_data.get("name"),
            "bio": user_data.get("bio"),
        },
        "pre_scores": pre_scores,
        "repositories": [
            {
                "name": r.get("name"),
                "description": r.get("description"),
                "primary_language": (r.get("primaryLanguage", {}) or {}).get("name"),
                "stars": r.get("stargazerCount", 0),
                "forks": r.get("forkCount", 0),
                "pushed_at": r.get("pushedAt"),
                "has_readme": bool(
                    r.get("object") and
                    (r["object"].get("byteSize", 0) or 0) > 100
                ),
                "commit_count": (
                    (r.get("defaultBranchRef") or {})
                    .get("target", {})
                    .get("history", {})
                    .get("totalCount", 0)
                ),
                "recent_commit_messages": [
                    node.get("message", "")[:80]
                    for node in (
                        (r.get("defaultBranchRef") or {})
                        .get("target", {})
                        .get("history", {})
                        .get("nodes", [])
                    )
                ],
            }
            for r in repos[:20]
        ],
    }

    cv_skills = (_candidate_field(candidate, "skills", []) or []) + (
        _candidate_field(candidate, "languages", []) or []
    ) + (
        _candidate_field(candidate, "frameworks", []) or []
    )

    try:
        logger.info("Agent 2: Sending GitHub data to LLM...")
        github_analysis = await _analyse_with_gemini(
            analysis_payload,
            cv_skills,
            thread_id=thread_id,
        )
        github_analysis = github_analysis.model_copy(
            update={
                "scenario": GitHubScenario.ACCESSIBLE,
                "analysis_status": GitHubAnalysisStatus.VERIFIED,
                "original_repo_count": pre_scores.get("repo_count", 0),
                "repos_with_readme": pre_scores.get("repos_with_readme", 0),
                "total_commits": pre_scores.get("total_commits", 0),
                "profile_contribution_count": pre_scores.get("profile_contribution_count", 0),
                "repository_commit_count": pre_scores.get("repository_commit_count", 0),
                "commit_message_sample_count": pre_scores.get("commit_message_sample_count", 0),
                "recent_activity_days": pre_scores.get("days_since_last_push"),
                "language_breakdown": pre_scores.get("language_breakdown", {}),
            }
        )
        logger.info(
            "Agent 2: Analysis complete thread=%s username=%s status=%s scenario=%s original_repos=%s profile_contributions=%s repository_commits=%s commit_message_samples=%s repos_with_readme=%s recent_activity_days=%s overall_score=%s",
            thread_id,
            username,
            github_analysis.analysis_status,
            github_analysis.scenario,
            github_analysis.original_repo_count,
            github_analysis.profile_contribution_count,
            github_analysis.repository_commit_count,
            github_analysis.commit_message_sample_count,
            pre_scores.get("repos_with_readme", 0),
            github_analysis.recent_activity_days,
            github_analysis.overall_score,
        )
    except GeminiRateLimitError as e:
        provider = current_ai_provider()
        return {
            "error": llm_rate_limit_message(provider),
            "error_code": llm_rate_limit_code(provider),
            "retry_after_seconds": e.retry_after_seconds,
        }
    except Agent2StructuredOutputError as e:
        logger.error(f"Agent 2 Step D structured output error: {e}")
        if current_ai_provider() == GROQ_PROVIDER:
            return {
                "error": GROQ_VALIDATION_FAILED_MESSAGE,
                "error_code": "GROQ_VALIDATION_FAILED",
            }
        return {
            "error": GITHUB_ANALYSIS_FAILED_MESSAGE,
            "error_code": "GITHUB_ANALYSIS_INVALID",
        }
    except GeminiTransientError as e:
        provider = current_ai_provider()
        _log_gemini_provider_failure(
            {
                "error_type": e.error_type,
                "status_code": e.status_code,
                "provider_status": e.provider_status,
                "retry_after_seconds": e.retry_after_seconds,
            },
            thread_id,
            False,
            2,
        )
        return {
            "error": llm_unavailable_message(provider, e.status_code),
            "error_code": llm_unavailable_code(provider, e.status_code),
            "retry_after_seconds": e.retry_after_seconds,
        }
    except GeminiProviderError as e:
        provider = current_ai_provider()
        _log_gemini_provider_failure(
            {
                "error_type": e.error_type,
                "status_code": e.status_code,
                "provider_status": e.provider_status,
                "retry_after_seconds": e.retry_after_seconds,
            },
            thread_id,
            False,
            1,
        )
        return {
            "error": llm_unavailable_message(provider, e.status_code),
            "error_code": llm_unavailable_code(provider, e.status_code),
            "retry_after_seconds": e.retry_after_seconds,
        }
    except LLMProviderConfigurationError:
        logger.error("Agent 2 provider configuration failed : thread=%s", thread_id)
        return {
            "error": GITHUB_ANALYSIS_TEMPORARILY_UNAVAILABLE_MESSAGE,
            "error_code": "LLM_PROVIDER_CONFIGURATION_ERROR",
        }
    except Exception as e:
        logger.error(
            "Agent 2 Step D failed : thread=%s error_type=%s",
            thread_id,
            type(e).__name__,
        )
        return {
            "error": GITHUB_ANALYSIS_TEMPORARILY_UNAVAILABLE_MESSAGE,
            "error_code": "GITHUB_ANALYSIS_FAILED",
        }

    return {"github_analysis": _github_analysis_state(github_analysis)}
