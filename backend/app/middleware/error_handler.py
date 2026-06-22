import asyncio
import logging
import sentry_sdk
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from app.config import settings
from app.utils.logging_hygiene import scrub_sentry_event
from app.utils.public_errors import sanitize_http_exception_detail

logger = logging.getLogger("devselect")
USER_INPUT_TOO_LONG_MESSAGE = f"Message is too long. Please keep it under {settings.MAX_USER_INPUT_CHARS} characters."


def init_sentry() -> None:
    if not settings.SENTRY_DSN:
        logger.info("Sentry DSN not set : error monitoring disabled.")
        return

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=0.1,
        ignore_errors=[GeneratorExit, asyncio.CancelledError],
        integrations=[
            StarletteIntegration(),
            FastApiIntegration(),
        ],
        send_default_pii=False,
        before_send=scrub_sentry_event,
    )
    logger.info("Sentry initialised.")


async def handle_unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "Unhandled exception : method=%s path=%s error_type=%s",
        request.method,
        request.url.path,
        type(exc).__name__,
    )
    sentry_sdk.capture_exception(exc)

    return JSONResponse(
        status_code=500,
        content={
            "error": "An unexpected error occurred. Our team has been notified."
        },
    )


async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    logger.warning(
        "HTTP exception : status=%s method=%s path=%s",
        exc.status_code,
        request.method,
        request.url.path,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": sanitize_http_exception_detail(
                exc.detail,
                exc.status_code,
            )
        },
        headers=exc.headers,
    )


async def handle_validation_exception(request: Request, exc: RequestValidationError) -> JSONResponse:
    if any(USER_INPUT_TOO_LONG_MESSAGE in str(error.get("msg", "")) for error in exc.errors()):
        logger.warning(f"User input too long on {request.method} {request.url.path}")
        return JSONResponse(
            status_code=400,
            content={
                "error": USER_INPUT_TOO_LONG_MESSAGE,
                "code": "MESSAGE_TOO_LONG",
            },
        )

    errors = [
        {
            "field": " -> ".join(str(loc) for loc in error["loc"]),
            "message": "Invalid value.",
        }
        for error in exc.errors()
    ]
    logger.warning(
        "Validation error : method=%s path=%s fields=%s",
        request.method,
        request.url.path,
        len(errors),
    )

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
