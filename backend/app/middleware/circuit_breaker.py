import time as _time
import logging
import secrets
import httpx
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.config import settings

logger = logging.getLogger("devselect")

CIRCUIT_FLAG_KEY = "ai_circuit_open"

_http_client = httpx.AsyncClient(timeout=5.0)
_flag_cache: dict = {"value": None, "ts": 0.0}


def _redis_configured() -> bool:
    url = settings.UPSTASH_REDIS_REST_URL.strip()
    token = settings.UPSTASH_REDIS_REST_TOKEN.strip()

    return bool(
        url.startswith("http")
        and token
        and "your-redis-instance" not in url
        and "your_upstash_redis_token_here" not in token
    )


async def _fetch_flag() -> str | None:
    url = f"{settings.UPSTASH_REDIS_REST_URL}/get/{CIRCUIT_FLAG_KEY}"
    headers = {"Authorization": f"Bearer {settings.UPSTASH_REDIS_REST_TOKEN}"}

    response = await _http_client.get(url, headers=headers)

    if response.status_code != 200:
        raise RuntimeError(f"status={response.status_code}")

    return response.json().get("result")


async def _get_flag() -> str | None:
    now = _time.monotonic()
    if now - _flag_cache["ts"] < 1.0:
        return _flag_cache["value"]

    result = await _fetch_flag()
    _flag_cache["value"] = result
    _flag_cache["ts"] = now
    return result


async def _set_flag(value: str) -> None:
    url = f"{settings.UPSTASH_REDIS_REST_URL}/set/{CIRCUIT_FLAG_KEY}/{value}"
    headers = {"Authorization": f"Bearer {settings.UPSTASH_REDIS_REST_TOKEN}"}

    response = await _http_client.post(url, headers=headers)

    if response.status_code != 200:
        logger.error(f"Circuit breaker: Redis unreachable on SET : status={response.status_code}.")
        raise HTTPException(status_code=503, detail="Could not update AI availability. Please try again.")

    _flag_cache["value"] = value
    _flag_cache["ts"] = _time.monotonic()


async def _delete_flag() -> None:
    url = f"{settings.UPSTASH_REDIS_REST_URL}/del/{CIRCUIT_FLAG_KEY}"
    headers = {"Authorization": f"Bearer {settings.UPSTASH_REDIS_REST_TOKEN}"}

    response = await _http_client.post(url, headers=headers)

    if response.status_code != 200:
        logger.error(f"Circuit breaker: Redis unreachable on DEL : status={response.status_code}.")
        raise HTTPException(status_code=503, detail="Could not update AI availability. Please try again.")

    _flag_cache["value"] = None
    _flag_cache["ts"] = _time.monotonic()


class CircuitBreakerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/api/chat"):
            return await call_next(request)

        if request.url.path.startswith("/admin"):
            return await call_next(request)

        try:
            flag = await _get_flag()
        except Exception as e:
            if settings.CIRCUIT_BREAKER_FAIL_OPEN and not settings.is_production:
                logger.warning("Circuit breaker Redis unavailable; failing open : error=%s", type(e).__name__)
                return await call_next(request)

            logger.warning("Circuit breaker Redis unavailable; failing closed : error=%s", type(e).__name__)
            return JSONResponse(
                status_code=503,
                content={"error": "AI evaluation is temporarily unavailable. Please try again later."},
            )

        if flag == "true":
            logger.warning(f"Circuit OPEN : blocking request to {request.url.path}")
            return JSONResponse(
                status_code=503,
                content={"error": "AI evaluation is temporarily unavailable. The rest of DevSelect remains online."},
            )

        return await call_next(request)


admin_router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin_secret(x_admin_secret: str | None, expected_secret: str) -> None:
    provided_secret = x_admin_secret or ""
    if not provided_secret or not secrets.compare_digest(provided_secret, expected_secret):
        raise HTTPException(status_code=403, detail="Invalid admin secret.")


@admin_router.post("/circuit/open")
async def open_circuit(request: Request, x_admin_secret: str | None = Header(None)):
    _require_admin_secret(x_admin_secret, request.app.state.settings.ADMIN_SECRET)
    await _set_flag("true")
    logger.warning("Circuit breaker OPENED by admin.")
    return JSONResponse(
        status_code=200,
        content={"status": "circuit_open", "message": "AI evaluation is now temporarily unavailable."},
    )


@admin_router.post("/circuit/close")
async def close_circuit(request: Request, x_admin_secret: str | None = Header(None)):
    _require_admin_secret(x_admin_secret, request.app.state.settings.ADMIN_SECRET)
    await _delete_flag()
    logger.info("Circuit breaker CLOSED by admin.")
    return JSONResponse(
        status_code=200,
        content={"status": "circuit_closed", "message": "AI evaluation is now available."},
    )


@admin_router.get("/reliability/status")
async def reliability_status(request: Request, x_admin_secret: str | None = Header(None)):
    _require_admin_secret(x_admin_secret, request.app.state.settings.ADMIN_SECRET)

    redis_reachable = False
    circuit_open: bool | None = None
    if _redis_configured():
        try:
            flag = await _fetch_flag()
            redis_reachable = True
            circuit_open = flag == "true"
        except Exception as e:
            logger.warning("Reliability status Redis check failed : error=%s", type(e).__name__)

    return {
        "redis_configured": _redis_configured(),
        "redis_reachable": redis_reachable,
        "circuit_open": circuit_open,
        "daily_budget_enabled": settings.DAILY_BUDGET_ENABLED,
        "budget_fallback_enabled": settings.BUDGET_REDIS_FALLBACK_ENABLED,
        "rate_limit_fail_open": settings.RATE_LIMIT_FAIL_OPEN,
        "circuit_breaker_fail_open": settings.CIRCUIT_BREAKER_FAIL_OPEN,
    }
