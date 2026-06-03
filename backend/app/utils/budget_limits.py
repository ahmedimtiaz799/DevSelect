from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
import asyncio
import logging

import httpx

from app.config import settings
from app.prompts.agent3_prompt import AGENT3_SYSTEM_PROMPT
from app.utils.llm_observability import estimate_tokens_from_chars, estimate_tokens_from_text

logger = logging.getLogger("devselect")

DAILY_EVALUATION_LIMIT_REACHED = "DAILY_EVALUATION_LIMIT_REACHED"
DAILY_USER_TOKEN_LIMIT_REACHED = "DAILY_USER_TOKEN_LIMIT_REACHED"
DAILY_GLOBAL_TOKEN_LIMIT_REACHED = "DAILY_GLOBAL_TOKEN_LIMIT_REACHED"
BUDGET_REDIS_UNAVAILABLE = "BUDGET_REDIS_UNAVAILABLE"

BUDGET_MESSAGES = {
    DAILY_EVALUATION_LIMIT_REACHED: "Daily evaluation limit reached. Please try again tomorrow.",
    DAILY_USER_TOKEN_LIMIT_REACHED: "Daily AI budget limit reached. Please try again tomorrow.",
    DAILY_GLOBAL_TOKEN_LIMIT_REACHED: "Daily AI budget limit reached. Please try again tomorrow.",
    BUDGET_REDIS_UNAVAILABLE: "Daily AI budget tracking is temporarily unavailable. Please try again later.",
}

_http_client = httpx.AsyncClient(timeout=5.0)
_memory_lock = asyncio.Lock()
_memory_user_evaluations: dict[tuple[str, str], int] = {}
_memory_user_tokens: dict[tuple[str, str], int] = {}
_memory_global_tokens: dict[str, int] = {}

BUDGET_LUA = """
local estimated_tokens = tonumber(ARGV[1])
local user_evaluation_limit = tonumber(ARGV[2])
local user_token_limit = tonumber(ARGV[3])
local global_token_limit = tonumber(ARGV[4])
local ttl_seconds = tonumber(ARGV[5])

local user_evaluations = tonumber(redis.call("GET", KEYS[1]) or "0")
local user_tokens = tonumber(redis.call("GET", KEYS[2]) or "0")
local global_tokens = tonumber(redis.call("GET", KEYS[3]) or "0")

local next_user_evaluations = user_evaluations + 1
local next_user_tokens = user_tokens + estimated_tokens
local next_global_tokens = global_tokens + estimated_tokens

if next_user_evaluations > user_evaluation_limit then
    return {"denied", "DAILY_EVALUATION_LIMIT_REACHED", tostring(user_evaluations), tostring(user_tokens), tostring(global_tokens)}
end

if next_user_tokens > user_token_limit then
    return {"denied", "DAILY_USER_TOKEN_LIMIT_REACHED", tostring(user_evaluations), tostring(user_tokens), tostring(global_tokens)}
end

if next_global_tokens > global_token_limit then
    return {"denied", "DAILY_GLOBAL_TOKEN_LIMIT_REACHED", tostring(user_evaluations), tostring(user_tokens), tostring(global_tokens)}
end

redis.call("SET", KEYS[1], next_user_evaluations, "EX", ttl_seconds)
redis.call("SET", KEYS[2], next_user_tokens, "EX", ttl_seconds)
redis.call("SET", KEYS[3], next_global_tokens, "EX", ttl_seconds)

return {"allowed", "OK", tostring(next_user_evaluations), tostring(next_user_tokens), tostring(next_global_tokens)}
"""


@dataclass(frozen=True)
class BudgetSnapshot:
    user_evaluation_count: int
    user_estimated_tokens: int
    global_estimated_tokens: int
    date_key: str
    storage: str


@dataclass(frozen=True)
class BudgetDecision:
    allowed: bool
    estimated_tokens: int
    date_key: str
    storage: str
    code: str | None = None
    error: str | None = None


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


def check_daily_budget(snapshot: BudgetSnapshot, estimated_tokens: int) -> BudgetDecision:
    next_user_evaluation_count = snapshot.user_evaluation_count + 1
    next_user_estimated_tokens = snapshot.user_estimated_tokens + estimated_tokens
    next_global_estimated_tokens = snapshot.global_estimated_tokens + estimated_tokens

    if next_user_evaluation_count > settings.DAILY_USER_EVALUATION_LIMIT:
        return _blocked_decision(
            DAILY_EVALUATION_LIMIT_REACHED,
            estimated_tokens,
            snapshot.date_key,
            snapshot.storage,
        )

    if next_user_estimated_tokens > settings.DAILY_USER_ESTIMATED_TOKEN_LIMIT:
        return _blocked_decision(
            DAILY_USER_TOKEN_LIMIT_REACHED,
            estimated_tokens,
            snapshot.date_key,
            snapshot.storage,
        )

    if next_global_estimated_tokens > settings.DAILY_GLOBAL_ESTIMATED_TOKEN_LIMIT:
        return _blocked_decision(
            DAILY_GLOBAL_TOKEN_LIMIT_REACHED,
            estimated_tokens,
            snapshot.date_key,
            snapshot.storage,
        )

    return BudgetDecision(
        allowed=True,
        estimated_tokens=estimated_tokens,
        date_key=snapshot.date_key,
        storage=snapshot.storage,
    )


async def record_budget_usage(user_id: str, estimated_tokens: int) -> BudgetDecision:
    date_key = _date_key()

    if not settings.DAILY_BUDGET_ENABLED:
        return BudgetDecision(
            allowed=True,
            estimated_tokens=estimated_tokens,
            date_key=date_key,
            storage="disabled",
        )

    if _upstash_configured():
        try:
            decision = await _record_upstash_budget_usage(user_id, estimated_tokens, date_key)
            _log_budget_decision(user_id, decision)
            return decision
        except Exception as e:
            if settings.BUDGET_REDIS_FALLBACK_ENABLED:
                logger.warning("Daily budget Redis unavailable, using memory fallback : error=%s", type(e).__name__)
            else:
                logger.warning("Daily budget Redis unavailable, blocking evaluation : error=%s", type(e).__name__)
                decision = _blocked_decision(BUDGET_REDIS_UNAVAILABLE, estimated_tokens, date_key, "redis_unavailable")
                _log_budget_decision(user_id, decision)
                return decision

    if not settings.BUDGET_REDIS_FALLBACK_ENABLED:
        decision = _blocked_decision(BUDGET_REDIS_UNAVAILABLE, estimated_tokens, date_key, "redis_unavailable")
        _log_budget_decision(user_id, decision)
        return decision

    decision = await _record_memory_budget_usage(user_id, estimated_tokens, date_key)
    _log_budget_decision(user_id, decision)
    return decision


def budget_error_payload(decision: BudgetDecision) -> dict:
    return {
        "error": decision.error or "Daily AI budget limit reached. Please try again tomorrow.",
        "code": decision.code or DAILY_GLOBAL_TOKEN_LIMIT_REACHED,
    }


def budget_error_status_code(decision: BudgetDecision) -> int:
    if decision.code == BUDGET_REDIS_UNAVAILABLE:
        return 503

    return 429


async def _record_upstash_budget_usage(
    user_id: str,
    estimated_tokens: int,
    date_key: str,
) -> BudgetDecision:
    keys = _budget_keys(user_id, date_key)
    payload = [
        "EVAL",
        BUDGET_LUA,
        3,
        keys["user_evaluations"],
        keys["user_tokens"],
        keys["global_tokens"],
        str(estimated_tokens),
        str(settings.DAILY_USER_EVALUATION_LIMIT),
        str(settings.DAILY_USER_ESTIMATED_TOKEN_LIMIT),
        str(settings.DAILY_GLOBAL_ESTIMATED_TOKEN_LIMIT),
        str(_ttl_seconds()),
    ]
    headers = {
        "Authorization": f"Bearer {settings.UPSTASH_REDIS_REST_TOKEN}",
        "Content-Type": "application/json",
    }

    response = await _http_client.post(
        settings.UPSTASH_REDIS_REST_URL.rstrip("/"),
        json=payload,
        headers=headers,
    )

    if response.status_code != 200:
        raise RuntimeError(f"status={response.status_code}")

    result = response.json().get("result") or []
    if len(result) < 2:
        raise RuntimeError("empty Redis budget result")

    status = result[0]
    code = result[1]

    if status == "allowed":
        return BudgetDecision(
            allowed=True,
            estimated_tokens=estimated_tokens,
            date_key=date_key,
            storage="upstash",
        )

    return _blocked_decision(str(code), estimated_tokens, date_key, "upstash")


async def _record_memory_budget_usage(
    user_id: str,
    estimated_tokens: int,
    date_key: str,
) -> BudgetDecision:
    user_key = (date_key, user_id)

    async with _memory_lock:
        snapshot = BudgetSnapshot(
            user_evaluation_count=_memory_user_evaluations.get(user_key, 0),
            user_estimated_tokens=_memory_user_tokens.get(user_key, 0),
            global_estimated_tokens=_memory_global_tokens.get(date_key, 0),
            date_key=date_key,
            storage="memory",
        )
        decision = check_daily_budget(snapshot, estimated_tokens)

        if not decision.allowed:
            return decision

        _memory_user_evaluations[user_key] = snapshot.user_evaluation_count + 1
        _memory_user_tokens[user_key] = snapshot.user_estimated_tokens + estimated_tokens
        _memory_global_tokens[date_key] = snapshot.global_estimated_tokens + estimated_tokens

    return decision


def _blocked_decision(
    code: str,
    estimated_tokens: int,
    date_key: str,
    storage: str,
) -> BudgetDecision:
    return BudgetDecision(
        allowed=False,
        estimated_tokens=estimated_tokens,
        date_key=date_key,
        storage=storage,
        code=code,
        error=BUDGET_MESSAGES.get(code, "Daily AI budget limit reached. Please try again tomorrow."),
    )


def _log_budget_decision(user_id: str, decision: BudgetDecision) -> None:
    if decision.allowed:
        logger.info(
            "Daily budget recorded : user=%s date=%s storage=%s estimated_tokens=%s",
            user_id,
            decision.date_key,
            decision.storage,
            decision.estimated_tokens,
        )
        return

    logger.warning(
        "Daily budget blocked : user=%s date=%s storage=%s code=%s estimated_tokens=%s",
        user_id,
        decision.date_key,
        decision.storage,
        decision.code,
        decision.estimated_tokens,
    )


def _date_key() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _ttl_seconds() -> int:
    now = datetime.now(timezone.utc)
    next_midnight = datetime.combine(
        now.date() + timedelta(days=1),
        time.min,
        tzinfo=timezone.utc,
    )
    return int((next_midnight - now).total_seconds()) + 86400


def _budget_keys(user_id: str, date_key: str) -> dict[str, str]:
    return {
        "user_evaluations": f"daily_budget:{date_key}:user:{user_id}:evaluations",
        "user_tokens": f"daily_budget:{date_key}:user:{user_id}:estimated_tokens",
        "global_tokens": f"daily_budget:{date_key}:global:estimated_tokens",
    }


def _upstash_configured() -> bool:
    url = settings.UPSTASH_REDIS_REST_URL.strip()
    token = settings.UPSTASH_REDIS_REST_TOKEN.strip()

    return (
        url.startswith("http")
        and bool(token)
        and "your-redis-instance" not in url
        and "your_upstash_redis_token_here" not in token
    )
