from collections.abc import Mapping
from typing import Any

from fastapi import Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from service.observability import CORRELATION_ID_HEADER, correlation_id


def _error(
    status_code: int,
    message: str,
    code: str,
    detail: Any = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"message": message, "code": code, "detail": jsonable_encoder(detail)},
        headers=headers,
    )


async def handle_validation_error(req: Request, exc: RequestValidationError) -> JSONResponse:
    return _error(
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        message="Request validation failed",
        code="ValidationError",
        detail=exc.errors(),
    )


async def handle_http_error(req: Request, exc: StarletteHTTPException) -> JSONResponse:
    endpoint = f"'{req.method} {req.url.path}'"
    if exc.status_code == status.HTTP_404_NOT_FOUND:
        message, code = f"Endpoint {endpoint} does not exist", "EndpointNotFound"
    elif exc.status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
        message, code = f"Method not allowed on {endpoint}", "MethodNotAllowed"
    else:
        message, code = str(exc.detail), "HTTPError"

    return _error(exc.status_code, message=message, code=code, headers=exc.headers)


async def handle_generic(req: Request, exc: Exception) -> JSONResponse:
    # No logging here: Starlette re-raises after this response is sent, and uvicorn logs the
    # traceback (as JSON, with the correlation ID).
    # This handler runs outside the request middleware, so it sets the correlation header itself.
    request_id = correlation_id.get()
    return _error(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="Internal server error",
        code="InternalServerError",
        headers={CORRELATION_ID_HEADER: request_id} if request_id else None,
    )


handlers: dict[int | type[Exception], Any] = {
    RequestValidationError: handle_validation_error,
    StarletteHTTPException: handle_http_error,
    Exception: handle_generic,
}
