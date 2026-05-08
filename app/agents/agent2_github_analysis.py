import json
import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from langchain_google_genai import ChatGoogleGenerativeAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.agents.state import DevSelectState
from app.config import settings
from app.models.candidate import GitHubAnalysis
from app.prompts.agent2_prompt import AGENT2_PROMPT
from app.utils.json_parser import parse_llm_json

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
    url = github_url.strip().rstrip("/")
    username = url.split("/")[-1]
    if not username:
        raise ValueError(f"Could not extract username from URL: {github_url}")
    return username


class GitHubRateLimitError(Exception):
    pass


class GitHubTransientError(Exception):
    pass


class GeminiTransientError(Exception):
    pass


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

        if response.status_code == 403:
            remaining = response.headers.get("X-RateLimit-Remaining", "unknown")
            if remaining == "0" or "rate limit" in response.text.lower():
                raise GitHubRateLimitError(
                    "GitHub API rate limit reached. Please retry in 60 seconds."
                )
            raise GitHubRateLimitError(
                f"GitHub API returned 403. Response: {response.text[:200]}"
            )

        if response.status_code >= 500:
            raise GitHubTransientError(
                f"GitHub API server error: {response.status_code}"
            )

        response.raise_for_status()
        return response.json()

    except httpx.TimeoutException as e:
        raise GitHubTransientError(f"GitHub API timeout: {e}")
    except httpx.NetworkError as e:
        raise GitHubTransientError(f"GitHub API network error: {e}")
    except (GitHubRateLimitError, GitHubTransientError):
        raise
    except Exception as e:
        raise GitHubTransientError(f"Unexpected GitHub API error: {e}")


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
    for repo in original_repos[:10]:
        branch = repo.get("defaultBranchRef")
        if branch:
            history = branch.get("target", {}).get("history", {})
            for node in history.get("nodes", []):
                commit_messages.append(node.get("message", "")[:100])

    total_commits = contributions.get("totalCommitContributions", 0)

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
        "total_commits": total_commits,
        "days_since_last_push": days_since_last_push,
        "total_stars": total_stars,
        "repos_with_readme": repos_with_readme,
    }


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    retry=retry_if_exception_type(GeminiTransientError),
    reraise=True,
)
async def _analyse_with_gemini(raw_github_data: dict, cv_skills: list[str]) -> str:
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=settings.GEMINI_API_KEY,
        temperature=0.2,
        timeout=30,
        max_retries=0,
    )

    prompt = AGENT2_PROMPT.format(
        cv_skills=", ".join(cv_skills) if cv_skills else "Not specified",
        github_data=json.dumps(raw_github_data, indent=2, default=str),
    )

    try:
        response = await llm.ainvoke(prompt)
        return response.content
    except Exception as e:
        error_str = str(e).lower()
        if "429" in error_str or "quota" in error_str:
            raise ValueError(
                "Gemini API rate limit exceeded. Please try again in a few minutes."
            )
        raise GeminiTransientError(f"Gemini transient error: {e}")


async def agent2_github_analysis(state: DevSelectState) -> dict[str, Any]:
    logger.info(f"Agent 2 starting for thread_id={state['thread_id']}")

    if state.get("error"):
        logger.warning("Agent 2 skipping — error already set in state.")
        return {}

    candidate = state.get("candidate")
    if not candidate:
        return {"error": "Agent 2: No candidate data in state. Agent 1 may have failed."}

    github_url = candidate.github_url
    if not github_url:
        logger.info("Agent 2: No GitHub URL — creating minimal analysis.")
        return {
            "github_analysis": GitHubAnalysis(
                scenario="NOT_FOUND",
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
                total_commits=0,
                active_days_per_month=0,
            )
        }

    try:
        username = _extract_username(github_url)
    except ValueError as e:
        return {"error": f"Agent 2: {e}"}

    try:
        logger.info(f"Agent 2: Querying GitHub GraphQL for '{username}'...")
        raw_data = await _query_github_graphql(username)
        logger.info("Agent 2: GitHub GraphQL responded")
    except GitHubRateLimitError as e:
        logger.error(f"Agent 2 rate limit: {e}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Agent 2 Step A failed after retries: {e}")
        return {
            "error": (
                "GitHub profile could not be fetched after 3 attempts. "
                "Please check the URL and try again."
            )
        }

    user_data = raw_data.get("data", {}).get("user")
    if user_data is None:
        logger.warning(f"Agent 2: GitHub user '{username}' not found.")
        return {
            "github_analysis": GitHubAnalysis(
                scenario="COULD_NOT_BE_ACCESSED",
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
                total_commits=0,
                active_days_per_month=0,
            )
        }

    repos = user_data.get("repositories", {}).get("nodes", [])
    total_repo_count = user_data.get("repositories", {}).get("totalCount", 0)
    if total_repo_count > 0 and len(repos) == 0:
        logger.warning(f"Agent 2: GitHub profile '{username}' appears private.")
        return {
            "github_analysis": GitHubAnalysis(
                scenario="PRIVATE",
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
                total_commits=0,
                active_days_per_month=0,
            )
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

    cv_skills = (candidate.skills or []) + (candidate.languages or [])

    try:
        logger.info("Agent 2: Sending GitHub data to Gemini Flash...")
        raw_json_str = await _analyse_with_gemini(analysis_payload, cv_skills)
        logger.info("Agent 2: Gemini Flash responded")
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Agent 2 Step C failed: {e}")
        return {
            "error": (
                "GitHub analysis failed after 2 attempts. "
                "Please try again in a few minutes."
            )
        }

    try:
        logger.info("Agent 2: Parsing and validating Gemini response...")
        parsed_dict = parse_llm_json(raw_json_str)
        github_analysis = GitHubAnalysis(**parsed_dict)
        logger.info(
            f"Agent 2: Analysis complete — "
            f"overall_score={github_analysis.overall_score}, "
            f"scenario={github_analysis.scenario}"
        )
    except ValueError as e:
        logger.error(f"Agent 2 Step D JSON error: {e}")
        return {"error": "GitHub analysis produced invalid output. Please try again."}
    except Exception as e:
        logger.error(f"Agent 2 Step D Pydantic error: {e}")
        return {"error": f"GitHub analysis validation failed: {e}"}

    return {"github_analysis": github_analysis}