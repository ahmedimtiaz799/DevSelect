from fastapi.responses import JSONResponse


def rate_limit_response(
    *,
    error: str,
    code: str,
    retry_after_seconds: int | None = None,
) -> JSONResponse:
    retry_after = (
        max(1, int(retry_after_seconds))
        if retry_after_seconds is not None and retry_after_seconds > 0
        else None
    )
    content = {
        "error": error,
        "code": code,
    }
    headers = {}
    if retry_after is not None:
        content["retry_after_seconds"] = retry_after
        headers["Retry-After"] = str(retry_after)

    return JSONResponse(status_code=429, content=content, headers=headers)
