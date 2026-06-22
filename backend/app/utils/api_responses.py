from fastapi.responses import JSONResponse

from app.utils.public_errors import public_error_payload


def rate_limit_response(
    *,
    code: str,
    retry_after_seconds: int | None = None,
) -> JSONResponse:
    retry_after = (
        max(1, int(retry_after_seconds))
        if retry_after_seconds is not None and retry_after_seconds > 0
        else None
    )
    content = public_error_payload(
        code,
        default_code="RATE_LIMIT_EXCEEDED",
        retry_after_seconds=retry_after,
    )
    headers = {}
    if retry_after is not None:
        headers["Retry-After"] = str(retry_after)

    return JSONResponse(status_code=429, content=content, headers=headers)
