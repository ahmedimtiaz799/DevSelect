import logging
import sentry_sdk
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from app.config import settings

logger = logging.getLogger("devselect")


def init_sentry() -> None:
    if not settings.SENTRY_DSN:
        logger.info("Sentry DSN not set : error monitoring disabled.")
        return

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=0.1,
        integrations=[
            StarletteIntegration(),
            FastApiIntegration(),
        ],
        send_default_pii=False,
    )
    logger.info("Sentry initialised.")


async def handle_unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"Unhandled exception on {request.method} {request.url.path} : {exc}")
    sentry_sdk.capture_exception(exc)

    return JSONResponse(
        status_code=500,
        content={
            "error": "An Unexpected error occurred. Our team has been notified."
        },
    )


async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    logger.warning(f"HTTP {exc.status_code} on {request.method} {request.url.path} : {exc.detail}")

    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )


async def handle_validation_exception(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [
        {
            "field": " -> ".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
        }
        for error in exc.errors()
    ]
    logger.warning(f"Validation error on {request.method} {request.url.path}: {errors}")

    return JSONResponse(
        status_code=422,
        content={
            "error": "Invalid request data.",
            "details": errors,
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(Exception, handle_unhandled_exception)
    app.add_exception_handler(HTTPException, handle_http_exception)
    app.add_exception_handler(RequestValidationError, handle_validation_exception)