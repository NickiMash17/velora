"""Request-scoped correlation ID and access logging.

Per docs/architecture/Observability.md §2 and §4, every log line and error
response within one request carries the same request_id (called
correlation_id at the platform/event level in docs/architecture/EventCatalog.md
§3 — the same identifier, this is its origin point for a synchronous HTTP
request). Clients may supply X-Request-ID for their own trace correlation;
if absent, one is generated. Either way it is echoed back in the response
header so it's the first thing support/engineering asks a customer for
(docs/architecture/API.md §7).

Implemented as pure ASGI middleware rather than Starlette's
`BaseHTTPMiddleware`: FastAPI wires a registered `Exception` handler into
the outermost `ServerErrorMiddleware`, which sits *outside* every
`add_middleware`-added layer — and `BaseHTTPMiddleware`'s call_next/task
mechanism does not reliably let an unhandled exception reach that outer
layer, so the global exception handler (app.shared.errors) was silently
bypassed under `BaseHTTPMiddleware`, confirmed by
tests/unit/test_error_envelope.py. Pure ASGI middleware has no such gap.
"""

from __future__ import annotations

import time
import uuid

import structlog
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_ID_HEADER = "X-Request-ID"

logger = structlog.get_logger("app.request")


class RequestIDMiddleware:
    """Binds a request_id to structlog's contextvars and `request.state`
    for the life of the request, and echoes it in the response header."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = Headers(scope=scope).get(REQUEST_ID_HEADER)
        request_id = incoming if incoming else str(uuid.uuid4())

        scope.setdefault("state", {})
        scope["state"]["request_id"] = request_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message).append(REQUEST_ID_HEADER, request_id)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            structlog.contextvars.clear_contextvars()


class RequestLoggingMiddleware:
    """One structured access-log line per request: method, path, status, duration."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        status_holder: dict[str, int] = {}

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_holder["status_code"] = message["status"]
            await send(message)

        await self.app(scope, receive, send_wrapper)

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "http_request",
            method=scope["method"],
            path=scope["path"],
            status_code=status_holder.get("status_code"),
            duration_ms=duration_ms,
        )
