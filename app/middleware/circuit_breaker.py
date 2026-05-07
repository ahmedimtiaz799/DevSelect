import logging
import httpx
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.config import settings

logger = logging.getLogger("devselect")

CIRCUIT_FLAG_KEY = "ai_circuit_open"


async def _get_flag() -> str | None:
    url = f"{settings.UPSTASH_REDIS_REST_URL}/get/{CIRCUIT_FLAG_KEY}"
    headers = {"Authorization": f"Bearer {settings.UPSTASH_REDIS_REST_TOKEN}"}

    async with httpx.AsyncClient(timeout=2.0) as client:
        response = await client.get(url, headers=headers)

    if response.status_code != 200:
        logger.error(f"Circuit breaker: Redis unreachable on GET : status={response.status_code}. Failing open.")
        return None

    return response.json().get("result")


async def _set_flag(value: str) -> None:
    url = f"{settings.UPSTASH_REDIS_REST_URL}/set/{CIRCUIT_FLAG_KEY}/{value}"
    headers = {"Authorization": f"Bearer {settings.UPSTASH_REDIS_REST_TOKEN}"}

    async with httpx.AsyncClient(timeout=2.0) as client:
        response = await client.post(url, headers=headers)  # FIX: post not get

    if response.status_code != 200:
        logger.error(f"Circuit breaker: Redis unreachable on SET : status={response.status_code}.")
        raise HTTPException(status_code=503, detail="Could not update circuit breaker state.")


async def _delete_flag() -> None:
    url = f"{settings.UPSTASH_REDIS_REST_URL}/del/{CIRCUIT_FLAG_KEY}"
    headers = {"Authorization": f"Bearer {settings.UPSTASH_REDIS_REST_TOKEN}"}

    async with httpx.AsyncClient(timeout=2.0) as client:
        response = await client.post(url, headers=headers)

    if response.status_code != 200:
        logger.error(f"Circuit breaker: Redis unreachable on DEL : status={response.status_code}.")
        raise HTTPException(status_code=503, detail="Could not update circuit breaker state.")


class CircuitBreakerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        if not request.url.path.startswith("/api/chat"):  # FIX: added leading /
            return await call_next(request)

        if request.url.path.startswith("/admin"):
            return await call_next(request)

        try:
            flag = await _get_flag()
        except Exception as e:
            logger.error(f"Circuit breaker check failed unexpectedly: {e}. Failing open.")
            return await call_next(request)

        if flag == "true":
            logger.warning(f"Circuit OPEN : blocking request to {request.url.path}")
            return JSONResponse(
                status_code=503,
                content={
                    "error": "AI evaluation is temporarily unavailable. The rest of DevSelect remains online."
                },
            )

        return await call_next(request)


admin_router = APIRouter(prefix="/admin", tags=["admin"])


@admin_router.post("/circuit/open")
async def open_circuit(x_admin_secret: str = Header(...)):
    if x_admin_secret != settings.ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Invalid admin secret.")
    await _set_flag("true")
    logger.warning("Circuit breaker OPENED by admin.")
    return JSONResponse(
        status_code=200,
        content={"status": "circuit_open", "message": "AI routes are now returning 503."},
    )


@admin_router.post("/circuit/close")
async def close_circuit(x_admin_secret: str = Header(...)):
    if x_admin_secret != settings.ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Invalid admin secret.")
    await _delete_flag()
    logger.info("Circuit breaker CLOSED by admin.")
    return JSONResponse(
        status_code=200,
        content={"status": "circuit_closed", "message": "AI routes are now operational."},
    )
        
