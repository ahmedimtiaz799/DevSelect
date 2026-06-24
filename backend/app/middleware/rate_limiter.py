import hashlib
import time
import logging
import httpx
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings
from app.dependencies import verify_supabase_token
from app.utils.api_responses import rate_limit_response

logger = logging.getLogger("devselect")

BUCKET_CAPACITY = 10
REFILL_RATE = 1 / 6

_http_client = httpx.AsyncClient(timeout=5.0)

RATE_LIMIT_LUA = """
local key         = KEYS[1]
local now         = tonumber(ARGV[1])
local capacity    = tonumber(ARGV[2])
local refill_rate = tonumber(ARGV[3])

local bucket      = redis.call("HMGET", key, "tokens", "last_refill")
local tokens      = tonumber(bucket[1])
local last_refill = tonumber(bucket[2])

if tokens == nil then
    tokens      = capacity
    last_refill = now
end

local elapsed       = now - last_refill
local refill_amount = elapsed * refill_rate
tokens      = math.min(capacity, tokens + refill_amount)
last_refill = now

if tokens >= 1 then
    tokens = tokens - 1
    redis.call("HMSET", key, "tokens", tokens, "last_refill", last_refill)
    redis.call("EXPIRE", key, 3600)
    return {"allowed", tostring(math.floor(tokens))}
else
    local wait = math.ceil((1 - tokens) / refill_rate)
    redis.call("HMSET", key, "tokens", tokens, "last_refill", last_refill)
    redis.call("EXPIRE", key, 3600)
    return {"denied", tostring(wait)}
end
"""


async def _run_lua_on_upstash(key: str, now: float) -> tuple[str, int]:
    url = settings.UPSTASH_REDIS_REST_URL
    payload = ["EVAL", RATE_LIMIT_LUA, 1, key, str(now), str(BUCKET_CAPACITY), str(REFILL_RATE)]
    headers = {
        "Authorization": f"Bearer {settings.UPSTASH_REDIS_REST_TOKEN}",
        "Content-Type": "application/json",
    }

    response = await _http_client.post(url, json=payload, headers=headers)

    if response.status_code != 200:
        raise RuntimeError(f"status={response.status_code}")

    result = response.json().get("result", [])
    if len(result) < 2:
        raise RuntimeError("empty Redis rate-limit result")

    status = result[0]
    value = int(result[1])
    return (status, value)


def _extract_bearer_token(request: Request) -> str | None:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    return auth_header.removeprefix("Bearer ").strip() or None


def _hash_rate_limit_identifier(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8", errors="replace")).hexdigest()


def _anonymous_rate_limit_key(request: Request) -> str:
    client_host = request.client.host if request.client else "unknown"
    return f"rate_limit:anonymous:{_hash_rate_limit_identifier(client_host)}"


async def _rate_limit_key_for_request(request: Request) -> str:
    token = _extract_bearer_token(request)
    if not token:
        return _anonymous_rate_limit_key(request)

    try:
        user_id = await verify_supabase_token(token)
        return f"rate_limit:user:{_hash_rate_limit_identifier(user_id)}"
    except Exception as e:
        logger.warning("Rate limiter using anonymous bucket for unverified token : error=%s", type(e).__name__)
        return _anonymous_rate_limit_key(request)


def _redis_unavailable_response() -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"error": "Rate limiting is temporarily unavailable. Please try again later."},
    )


class RateLimiterMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/api/chat"):
            return await call_next(request)

        key = await _rate_limit_key_for_request(request)

        now = time.time()

        try:
            status, value = await _run_lua_on_upstash(key, now)
        except Exception as e:
            if settings.RATE_LIMIT_FAIL_OPEN and not settings.is_production:
                logger.warning("Rate limiter Redis unavailable; failing open : key=%s error=%s", key, type(e).__name__)
                return await call_next(request)

            logger.warning("Rate limiter Redis unavailable; failing closed : key=%s error=%s", key, type(e).__name__)
            return _redis_unavailable_response()

        if status == "denied":
            logger.warning(f"Rate limit exceeded : key={key} retry_after={value}s")
            response = rate_limit_response(
                code="RATE_LIMIT_EXCEEDED",
                retry_after_seconds=value,
            )
            response.headers["X-RateLimit-Limit"] = str(BUCKET_CAPACITY)
            response.headers["X-RateLimit-Remaining"] = "0"
            return response

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(BUCKET_CAPACITY)
        response.headers["X-RateLimit-Remaining"] = str(value)
        return response
