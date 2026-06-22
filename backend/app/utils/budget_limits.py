import asyncio
import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone

import httpx
from fastapi.responses import JSONResponse

from app.config import settings
from app.prompts.agent3_prompt import AGENT3_SYSTEM_PROMPT
from app.utils.api_responses import rate_limit_response
from app.utils.llm_observability import estimate_tokens_from_chars, estimate_tokens_from_text
from app.utils.public_errors import public_error_payload


logger = logging.getLogger("devselect")

GLOBAL_DAILY_EVALUATION_LIMIT_REACHED = "GLOBAL_DAILY_EVALUATION_LIMIT_REACHED"
GLOBAL_MONTHLY_EVALUATION_LIMIT_REACHED = "GLOBAL_MONTHLY_EVALUATION_LIMIT_REACHED"
USER_DAILY_EVALUATION_LIMIT_REACHED = "USER_DAILY_EVALUATION_LIMIT_REACHED"
USER_LIFETIME_EVALUATION_LIMIT_REACHED = "USER_LIFETIME_EVALUATION_LIMIT_REACHED"
FOLLOWUP_EVALUATION_LIMIT_REACHED = "FOLLOWUP_EVALUATION_LIMIT_REACHED"
FOLLOWUP_USER_DAILY_LIMIT_REACHED = "FOLLOWUP_USER_DAILY_LIMIT_REACHED"
DAILY_USER_TOKEN_LIMIT_REACHED = "DAILY_USER_TOKEN_LIMIT_REACHED"
DAILY_GLOBAL_TOKEN_LIMIT_REACHED = "DAILY_GLOBAL_TOKEN_LIMIT_REACHED"
BUDGET_REDIS_UNAVAILABLE = "BUDGET_REDIS_UNAVAILABLE"
BUDGET_ENFORCEMENT_DISABLED = "BUDGET_ENFORCEMENT_DISABLED"

BUDGET_MESSAGES = {
    GLOBAL_DAILY_EVALUATION_LIMIT_REACHED: "DevSelect has reached its evaluation capacity for today. Please try again tomorrow.",
    GLOBAL_MONTHLY_EVALUATION_LIMIT_REACHED: "DevSelect has reached its evaluation capacity for this month.",
    USER_DAILY_EVALUATION_LIMIT_REACHED: "Your daily evaluation limit has been reached. Please try again tomorrow.",
    USER_LIFETIME_EVALUATION_LIMIT_REACHED: "Your portfolio evaluation allowance has been used.",
    FOLLOWUP_EVALUATION_LIMIT_REACHED: "This evaluation has reached its follow-up limit.",
    FOLLOWUP_USER_DAILY_LIMIT_REACHED: "Your daily follow-up limit has been reached. Please try again tomorrow.",
    DAILY_USER_TOKEN_LIMIT_REACHED: "Your daily AI budget limit has been reached. Please try again tomorrow.",
    DAILY_GLOBAL_TOKEN_LIMIT_REACHED: "DevSelect has reached its daily AI budget. Please try again tomorrow.",
    BUDGET_REDIS_UNAVAILABLE: "AI quota enforcement is temporarily unavailable. Please try again later.",
    BUDGET_ENFORCEMENT_DISABLED: "AI quota enforcement is not available.",
}

_http_client = httpx.AsyncClient(timeout=5.0)
_memory_lock = asyncio.Lock()
_memory_global_daily_evaluations: dict[str, int] = {}
_memory_global_monthly_evaluations: dict[str, int] = {}
_memory_user_daily_evaluations: dict[tuple[str, str], int] = {}
_memory_user_lifetime_evaluations: dict[str, int] = {}
_memory_user_daily_tokens: dict[tuple[str, str], int] = {}
_memory_global_daily_tokens: dict[str, int] = {}
_memory_evaluation_followups: dict[str, int] = {}
_memory_user_daily_followups: dict[tuple[str, str], int] = {}

EVALUATION_QUOTA_LUA = """
local estimated_tokens = tonumber(ARGV[1])
local global_daily_limit = tonumber(ARGV[2])
local global_monthly_limit = tonumber(ARGV[3])
local user_daily_limit = tonumber(ARGV[4])
local user_lifetime_limit = tonumber(ARGV[5])
local user_token_limit = tonumber(ARGV[6])
local global_token_limit = tonumber(ARGV[7])
local daily_ttl = tonumber(ARGV[8])
local monthly_ttl = tonumber(ARGV[9])

local global_daily = tonumber(redis.call("GET", KEYS[1]) or "0")
local global_monthly = tonumber(redis.call("GET", KEYS[2]) or "0")
local user_daily = tonumber(redis.call("GET", KEYS[3]) or "0")
local user_lifetime = tonumber(redis.call("GET", KEYS[4]) or "0")
local user_tokens = tonumber(redis.call("GET", KEYS[5]) or "0")
local global_tokens = tonumber(redis.call("GET", KEYS[6]) or "0")

if user_lifetime + 1 > user_lifetime_limit then
    return {"denied", "USER_LIFETIME_EVALUATION_LIMIT_REACHED"}
end
if user_daily + 1 > user_daily_limit then
    return {"denied", "USER_DAILY_EVALUATION_LIMIT_REACHED"}
end
if global_daily + 1 > global_daily_limit then
    return {"denied", "GLOBAL_DAILY_EVALUATION_LIMIT_REACHED"}
end
if global_monthly + 1 > global_monthly_limit then
    return {"denied", "GLOBAL_MONTHLY_EVALUATION_LIMIT_REACHED"}
end
if user_tokens + estimated_tokens > user_token_limit then
    return {"denied", "DAILY_USER_TOKEN_LIMIT_REACHED"}
end
if global_tokens + estimated_tokens > global_token_limit then
    return {"denied", "DAILY_GLOBAL_TOKEN_LIMIT_REACHED"}
end

redis.call("SET", KEYS[1], global_daily + 1, "EX", daily_ttl)
redis.call("SET", KEYS[2], global_monthly + 1, "EX", monthly_ttl)
redis.call("SET", KEYS[3], user_daily + 1, "EX", daily_ttl)
redis.call("SET", KEYS[4], user_lifetime + 1)
redis.call("SET", KEYS[5], user_tokens + estimated_tokens, "EX", daily_ttl)
redis.call("SET", KEYS[6], global_tokens + estimated_tokens, "EX", daily_ttl)
return {"allowed", "OK"}
"""

FOLLOWUP_QUOTA_LUA = """
local evaluation_limit = tonumber(ARGV[1])
local user_daily_limit = tonumber(ARGV[2])
local daily_ttl = tonumber(ARGV[3])
local evaluation_count = tonumber(redis.call("GET", KEYS[1]) or "0")
local user_daily_count = tonumber(redis.call("GET", KEYS[2]) or "0")

if evaluation_count + 1 > evaluation_limit then
    return {"denied", "FOLLOWUP_EVALUATION_LIMIT_REACHED"}
end
if user_daily_count + 1 > user_daily_limit then
    return {"denied", "FOLLOWUP_USER_DAILY_LIMIT_REACHED"}
end

redis.call("SET", KEYS[1], evaluation_count + 1)
redis.call("SET", KEYS[2], user_daily_count + 1, "EX", daily_ttl)
return {"allowed", "OK"}
"""


@dataclass(frozen=True)
class BudgetDecision:
    allowed: bool
    storage: str
    scope: str
    estimated_tokens: int = 0
    code: str | None = None
    error: str | None = None
    retry_after_seconds: int | None = None


@dataclass(frozen=True)
class EvaluationQuotaSnapshot:
    global_daily: int = 0
    global_monthly: int = 0
    user_daily: int = 0
    user_lifetime: int = 0
    user_daily_tokens: int = 0
    global_daily_tokens: int = 0


@dataclass(frozen=True)
class FollowUpQuotaSnapshot:
    evaluation_count: int = 0
    user_daily_count: int = 0


def estimate_evaluation_budget(pdf_size_bytes: int | None) -> int:
    agent1_input_chars = settings.AGENT1_MAX_INPUT_CHARS
    if pdf_size_bytes and pdf_size_bytes > 0:
        agent1_input_chars = min(pdf_size_bytes, settings.AGENT1_MAX_INPUT_CHARS)

    estimated_input_tokens = (
        estimate_tokens_from_chars(agent1_input_chars)
        + estimate_tokens_from_chars(settings.AGENT2_MAX_INPUT_CHARS)
        + estimate_tokens_from_chars(settings.AGENT3_MAX_INPUT_CHARS)
        + estimate_tokens_from_text(AGENT3_SYSTEM_PROMPT)
    )
    estimated_output_tokens = (
        settings.AGENT1_MAX_OUTPUT_TOKENS
        + settings.AGENT2_MAX_OUTPUT_TOKENS
        + settings.AGENT3_MAX_OUTPUT_TOKENS
    )
    return estimated_input_tokens + estimated_output_tokens


def check_evaluation_quota(
    snapshot: EvaluationQuotaSnapshot,
    estimated_tokens: int,
    *,
    storage: str = "memory",
) -> BudgetDecision:
    checks = (
        (snapshot.user_lifetime + 1 > settings.USER_EVALS_LIFETIME, USER_LIFETIME_EVALUATION_LIMIT_REACHED),
        (snapshot.user_daily + 1 > settings.USER_EVALS_PER_DAY, USER_DAILY_EVALUATION_LIMIT_REACHED),
        (snapshot.global_daily + 1 > settings.GLOBAL_EVALS_PER_DAY, GLOBAL_DAILY_EVALUATION_LIMIT_REACHED),
        (snapshot.global_monthly + 1 > settings.GLOBAL_EVALS_PER_MONTH, GLOBAL_MONTHLY_EVALUATION_LIMIT_REACHED),
        (snapshot.user_daily_tokens + estimated_tokens > settings.DAILY_USER_ESTIMATED_TOKEN_LIMIT, DAILY_USER_TOKEN_LIMIT_REACHED),
        (snapshot.global_daily_tokens + estimated_tokens > settings.DAILY_GLOBAL_ESTIMATED_TOKEN_LIMIT, DAILY_GLOBAL_TOKEN_LIMIT_REACHED),
    )
    for blocked, code in checks:
        if blocked:
            return _blocked_decision(code, storage=storage, scope="evaluation", estimated_tokens=estimated_tokens)
    return BudgetDecision(
        allowed=True,
        storage=storage,
        scope="evaluation",
        estimated_tokens=estimated_tokens,
    )


def check_follow_up_quota(
    snapshot: FollowUpQuotaSnapshot,
    *,
    storage: str = "memory",
) -> BudgetDecision:
    if snapshot.evaluation_count + 1 > settings.FOLLOWUPS_PER_EVALUATION:
        return _blocked_decision(
            FOLLOWUP_EVALUATION_LIMIT_REACHED,
            storage=storage,
            scope="follow_up",
        )
    if snapshot.user_daily_count + 1 > settings.FOLLOWUPS_PER_USER_DAY:
        return _blocked_decision(
            FOLLOWUP_USER_DAILY_LIMIT_REACHED,
            storage=storage,
            scope="follow_up",
        )
    return BudgetDecision(allowed=True, storage=storage, scope="follow_up")


async def record_evaluation_usage(user_id: str, estimated_tokens: int) -> BudgetDecision:
    if not settings.DAILY_BUDGET_ENABLED:
        if settings.is_production:
            return _blocked_decision(
                BUDGET_ENFORCEMENT_DISABLED,
                storage="disabled",
                scope="evaluation",
                estimated_tokens=estimated_tokens,
            )
        return BudgetDecision(
            allowed=True,
            storage="disabled",
            scope="evaluation",
            estimated_tokens=estimated_tokens,
        )

    if _upstash_configured():
        try:
            decision = await _record_upstash_evaluation(user_id, estimated_tokens)
            _log_decision(user_id, decision)
            return decision
        except Exception as error:
            logger.warning(
                "Evaluation quota Redis unavailable : error_type=%s",
                type(error).__name__,
            )
            if not _memory_fallback_allowed():
                return _redis_unavailable_decision("evaluation", estimated_tokens)
    elif not _memory_fallback_allowed():
        return _redis_unavailable_decision("evaluation", estimated_tokens)

    decision = await _record_memory_evaluation(user_id, estimated_tokens)
    _log_decision(user_id, decision)
    return decision


async def record_budget_usage(user_id: str, estimated_tokens: int) -> BudgetDecision:
    return await record_evaluation_usage(user_id, estimated_tokens)


async def record_follow_up_usage(user_id: str, chat_id: str) -> BudgetDecision:
    if not settings.DAILY_BUDGET_ENABLED:
        if settings.is_production:
            return _blocked_decision(
                BUDGET_ENFORCEMENT_DISABLED,
                storage="disabled",
                scope="follow_up",
            )
        return BudgetDecision(allowed=True, storage="disabled", scope="follow_up")

    if _upstash_configured():
        try:
            decision = await _record_upstash_follow_up(user_id, chat_id)
            _log_decision(user_id, decision)
            return decision
        except Exception as error:
            logger.warning(
                "Follow-up quota Redis unavailable : error_type=%s",
                type(error).__name__,
            )
            if not _memory_fallback_allowed():
                return _redis_unavailable_decision("follow_up")
    elif not _memory_fallback_allowed():
        return _redis_unavailable_decision("follow_up")

    decision = await _record_memory_follow_up(user_id, chat_id)
    _log_decision(user_id, decision)
    return decision


def budget_response(decision: BudgetDecision) -> JSONResponse:
    if decision.code in {BUDGET_REDIS_UNAVAILABLE, BUDGET_ENFORCEMENT_DISABLED}:
        return JSONResponse(
            status_code=503,
            content=public_error_payload(
                decision.code,
                default_code=BUDGET_REDIS_UNAVAILABLE,
            ),
        )
    return rate_limit_response(
        code=decision.code or GLOBAL_DAILY_EVALUATION_LIMIT_REACHED,
        retry_after_seconds=decision.retry_after_seconds,
    )


async def clear_evaluation_follow_up_usage(chat_id: str) -> None:
    key = _follow_up_evaluation_key(chat_id)
    if _upstash_configured():
        try:
            await _http_client.post(
                settings.UPSTASH_REDIS_REST_URL.rstrip("/"),
                json=["DEL", key],
                headers={
                    "Authorization": f"Bearer {settings.UPSTASH_REDIS_REST_TOKEN}",
                    "Content-Type": "application/json",
                },
            )
        except Exception as error:
            logger.warning(
                "Follow-up quota cleanup failed : error_type=%s",
                type(error).__name__,
            )
    async with _memory_lock:
        _memory_evaluation_followups.pop(key, None)


async def _record_upstash_evaluation(user_id: str, estimated_tokens: int) -> BudgetDecision:
    keys = _evaluation_keys(user_id)
    payload = [
        "EVAL",
        EVALUATION_QUOTA_LUA,
        6,
        keys["global_daily"],
        keys["global_monthly"],
        keys["user_daily"],
        keys["user_lifetime"],
        keys["user_tokens"],
        keys["global_tokens"],
        str(estimated_tokens),
        str(settings.GLOBAL_EVALS_PER_DAY),
        str(settings.GLOBAL_EVALS_PER_MONTH),
        str(settings.USER_EVALS_PER_DAY),
        str(settings.USER_EVALS_LIFETIME),
        str(settings.DAILY_USER_ESTIMATED_TOKEN_LIMIT),
        str(settings.DAILY_GLOBAL_ESTIMATED_TOKEN_LIMIT),
        str(_daily_ttl_seconds()),
        str(_monthly_ttl_seconds()),
    ]
    result = await _run_upstash(payload)
    return _decision_from_result(
        result,
        storage="upstash",
        scope="evaluation",
        estimated_tokens=estimated_tokens,
    )


async def _record_upstash_follow_up(user_id: str, chat_id: str) -> BudgetDecision:
    payload = [
        "EVAL",
        FOLLOWUP_QUOTA_LUA,
        2,
        _follow_up_evaluation_key(chat_id),
        _follow_up_user_daily_key(user_id),
        str(settings.FOLLOWUPS_PER_EVALUATION),
        str(settings.FOLLOWUPS_PER_USER_DAY),
        str(_daily_ttl_seconds()),
    ]
    result = await _run_upstash(payload)
    return _decision_from_result(result, storage="upstash", scope="follow_up")


async def _run_upstash(payload: list) -> list:
    response = await _http_client.post(
        settings.UPSTASH_REDIS_REST_URL.rstrip("/"),
        json=payload,
        headers={
            "Authorization": f"Bearer {settings.UPSTASH_REDIS_REST_TOKEN}",
            "Content-Type": "application/json",
        },
    )
    if response.status_code != 200:
        raise RuntimeError(f"status={response.status_code}")
    result = response.json().get("result") or []
    if len(result) < 2:
        raise RuntimeError("empty Redis quota result")
    return result


async def _record_memory_evaluation(user_id: str, estimated_tokens: int) -> BudgetDecision:
    date_key = _date_key()
    month_key = _month_key()
    user_key = _subject_key(user_id)
    async with _memory_lock:
        snapshot = EvaluationQuotaSnapshot(
            global_daily=_memory_global_daily_evaluations.get(date_key, 0),
            global_monthly=_memory_global_monthly_evaluations.get(month_key, 0),
            user_daily=_memory_user_daily_evaluations.get((date_key, user_key), 0),
            user_lifetime=_memory_user_lifetime_evaluations.get(user_key, 0),
            user_daily_tokens=_memory_user_daily_tokens.get((date_key, user_key), 0),
            global_daily_tokens=_memory_global_daily_tokens.get(date_key, 0),
        )
        decision = check_evaluation_quota(snapshot, estimated_tokens)
        if not decision.allowed:
            return decision
        _memory_global_daily_evaluations[date_key] = snapshot.global_daily + 1
        _memory_global_monthly_evaluations[month_key] = snapshot.global_monthly + 1
        _memory_user_daily_evaluations[(date_key, user_key)] = snapshot.user_daily + 1
        _memory_user_lifetime_evaluations[user_key] = snapshot.user_lifetime + 1
        _memory_user_daily_tokens[(date_key, user_key)] = snapshot.user_daily_tokens + estimated_tokens
        _memory_global_daily_tokens[date_key] = snapshot.global_daily_tokens + estimated_tokens
    return decision


async def _record_memory_follow_up(user_id: str, chat_id: str) -> BudgetDecision:
    date_key = _date_key()
    user_key = _subject_key(user_id)
    evaluation_key = _follow_up_evaluation_key(chat_id)
    async with _memory_lock:
        snapshot = FollowUpQuotaSnapshot(
            evaluation_count=_memory_evaluation_followups.get(evaluation_key, 0),
            user_daily_count=_memory_user_daily_followups.get((date_key, user_key), 0),
        )
        decision = check_follow_up_quota(snapshot)
        if not decision.allowed:
            return decision
        _memory_evaluation_followups[evaluation_key] = snapshot.evaluation_count + 1
        _memory_user_daily_followups[(date_key, user_key)] = snapshot.user_daily_count + 1
    return decision


def _decision_from_result(
    result: list,
    *,
    storage: str,
    scope: str,
    estimated_tokens: int = 0,
) -> BudgetDecision:
    if result[0] == "allowed":
        return BudgetDecision(
            allowed=True,
            storage=storage,
            scope=scope,
            estimated_tokens=estimated_tokens,
        )
    return _blocked_decision(
        str(result[1]),
        storage=storage,
        scope=scope,
        estimated_tokens=estimated_tokens,
    )


def _blocked_decision(
    code: str,
    *,
    storage: str,
    scope: str,
    estimated_tokens: int = 0,
) -> BudgetDecision:
    return BudgetDecision(
        allowed=False,
        storage=storage,
        scope=scope,
        estimated_tokens=estimated_tokens,
        code=code,
        error=BUDGET_MESSAGES.get(code, "AI quota limit reached."),
        retry_after_seconds=_retry_after_for_code(code),
    )


def _redis_unavailable_decision(scope: str, estimated_tokens: int = 0) -> BudgetDecision:
    return _blocked_decision(
        BUDGET_REDIS_UNAVAILABLE,
        storage="redis_unavailable",
        scope=scope,
        estimated_tokens=estimated_tokens,
    )


def _retry_after_for_code(code: str) -> int | None:
    if code in {
        GLOBAL_DAILY_EVALUATION_LIMIT_REACHED,
        USER_DAILY_EVALUATION_LIMIT_REACHED,
        FOLLOWUP_USER_DAILY_LIMIT_REACHED,
        DAILY_USER_TOKEN_LIMIT_REACHED,
        DAILY_GLOBAL_TOKEN_LIMIT_REACHED,
    }:
        return _seconds_until_next_day()
    if code == GLOBAL_MONTHLY_EVALUATION_LIMIT_REACHED:
        return _seconds_until_next_month()
    return None


def _log_decision(user_id: str, decision: BudgetDecision) -> None:
    level = logger.info if decision.allowed else logger.warning
    level(
        "AI quota decision : scope=%s allowed=%s storage=%s code=%s estimated_tokens=%s",
        decision.scope,
        decision.allowed,
        decision.storage,
        decision.code or "OK",
        decision.estimated_tokens,
    )


def _date_key() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _month_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _seconds_until_next_day() -> int:
    now = datetime.now(timezone.utc)
    next_day = datetime.combine(now.date() + timedelta(days=1), time.min, tzinfo=timezone.utc)
    return max(1, int((next_day - now).total_seconds()))


def _seconds_until_next_month() -> int:
    now = datetime.now(timezone.utc)
    if now.month == 12:
        next_month = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        next_month = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
    return max(1, int((next_month - now).total_seconds()))


def _daily_ttl_seconds() -> int:
    return _seconds_until_next_day() + 86400


def _monthly_ttl_seconds() -> int:
    return _seconds_until_next_month() + 86400


def _subject_key(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _evaluation_keys(user_id: str) -> dict[str, str]:
    date_key = _date_key()
    month_key = _month_key()
    subject = _subject_key(user_id)
    return {
        "global_daily": f"portfolio_beta:{date_key}:global:evaluations",
        "global_monthly": f"portfolio_beta:{month_key}:global:evaluations",
        "user_daily": f"portfolio_beta:{date_key}:user:{subject}:evaluations",
        "user_lifetime": f"portfolio_beta:user:{subject}:lifetime_evaluations",
        "user_tokens": f"portfolio_beta:{date_key}:user:{subject}:estimated_tokens",
        "global_tokens": f"portfolio_beta:{date_key}:global:estimated_tokens",
    }


def _follow_up_evaluation_key(chat_id: str) -> str:
    return f"portfolio_beta:evaluation:{_subject_key(chat_id)}:followups"


def _follow_up_user_daily_key(user_id: str) -> str:
    return f"portfolio_beta:{_date_key()}:user:{_subject_key(user_id)}:followups"


def _upstash_configured() -> bool:
    url = settings.UPSTASH_REDIS_REST_URL.strip()
    token = settings.UPSTASH_REDIS_REST_TOKEN.strip()
    return bool(
        url.startswith("http")
        and token
        and "your-redis-instance" not in url
        and "your_upstash_redis_token_here" not in token
    )


def _memory_fallback_allowed() -> bool:
    return not settings.is_production and settings.BUDGET_REDIS_FALLBACK_ENABLED
