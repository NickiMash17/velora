"""Global exception handling — one error shape for every endpoint.

Per docs/architecture/API.md §7: every error response is
    {"error": {"code", "message", "details", "request_id"}}
`code` is a stable, machine-readable string; `message` is safe to display and
never leaks internal detail (stack traces, SQL, internal service names);
`request_id` ties the response back to the structured log line carrying the
same id (app.shared.middleware.RequestIDMiddleware).

Every handler here also sets the X-Request-ID *response header* directly,
rather than relying solely on RequestIDMiddleware's send-wrapping to add it.
Starlette wires the registered `Exception`/500 handler into the outermost
`ServerErrorMiddleware` (see Starlette's `Starlette.build_middleware_stack`),
which sits *outside* every `add_middleware`-added layer — so a response built
by that handler is sent through the raw ASGI `send`, bypassing our
middleware's header injection entirely. Setting the header here as well
closes that gap regardless of which layer ends up building the response.
"""

from __future__ import annotations

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.shared.middleware import REQUEST_ID_HEADER

logger = structlog.get_logger("app.errors")


class AppError(Exception):
    """Base class for application errors that should reach the client.

    Raise a specific subclass (or this directly, for a one-off) rather than
    a bare HTTPException, so every deliberate error goes through the same
    envelope with a stable `code`.
    """

    code: str = "application_error"
    status_code: int = status.HTTP_400_BAD_REQUEST

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _envelope(code: str, message: str, request_id: str | None, details: dict | None = None) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "request_id": request_id,
        }
    }


def _error_response(
    status_code: int,
    code: str,
    message: str,
    request: Request,
    details: dict | None = None,
) -> JSONResponse:
    request_id = _request_id(request)
    response = JSONResponse(
        status_code=status_code,
        content=_envelope(code, message, request_id, details),
    )
    if request_id:
        response.headers[REQUEST_ID_HEADER] = request_id
    return response


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return _error_response(exc.status_code, exc.code, exc.message, request, exc.details)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "validation_error",
            "The request could not be validated.",
            request,
            {"errors": exc.errors()},
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _error_response(
            exc.status_code,
            "http_error",
            str(exc.detail) if exc.detail else "An HTTP error occurred.",
            request,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        # Full detail (including traceback) goes to structured logs, tagged
        # with the same request_id the client receives — never in the
        # response body itself.
        logger.exception("unhandled_exception", path=request.url.path)
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "internal_error",
            "An unexpected error occurred.",
            request,
        )
