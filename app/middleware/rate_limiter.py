import time
import logging
import httpx
import base64
import json
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings

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
        logger.error(f"Upstash Redis unreachable : status={response.status_code}. Failing open.")
        return ("allowed", BUCKET_CAPACITY)

    result = response.json().get("result", [])
    status = result[0]
    value = int(result[1])
    return (status, value)


def _extract_user_id_from_header(request: Request) -> str | None:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header.removeprefix("Bearer ")

    try:
        payload_segment = token.split(".")[1]
        padding = 4 - len(payload_segment) % 4
        payload_segment += "=" * padding
        payload = json.loads(base64.urlsafe_b64decode(payload_segment))
        return payload.get("sub")
    except Exception:
        return None


class RateLimiterMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/api/chat"):
            return await call_next(request)

        user_id = _extract_user_id_from_header(request)
        if user_id is None:
            return await call_next(request)

        key = f"rate_limit:{user_id}"
        now = time.time()

        try:
            status, value = await _run_lua_on_upstash(key, now)
        except Exception as e:
            logger.error(f"Rate limiter error for user={user_id}: {e}. Failing open.")
            return await call_next(request)

        if status == "denied":
            logger.warning(f"Rate limit exceeded : user={user_id} retry_after={value}s")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too many requests. Please slow down.",
                    "retry_after_seconds": value,
                },
                headers={
                    "Retry-After": str(value),
                    "X-RateLimit-Limit": str(BUCKET_CAPACITY),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(BUCKET_CAPACITY)
        response.headers["X-RateLimit-Remaining"] = str(value)
        return response