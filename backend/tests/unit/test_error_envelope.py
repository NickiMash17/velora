"""Per docs/architecture/API.md §7: every error response is
    {"error": {"code", "message", "details", "request_id"}}
and an unhandled exception's message never leaks internal detail. Built as
a standalone minimal app (rather than importing app.main, which requires
live DB/Redis config) so this stays a true unit test of the exception
handlers themselves.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.shared.errors import AppError, register_exception_handlers
from app.shared.middleware import REQUEST_ID_HEADER, RequestIDMiddleware


class _Payload(BaseModel):
    name: str


def _minimal_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)
    register_exception_handlers(app)

    @app.get("/boom")
    async def boom():
        raise RuntimeError("some internal detail that must never reach the client")

    @app.get("/app-error")
    async def app_error():
        raise AppError("Something specific went wrong.", details={"field": "value"})

    @app.post("/validate")
    async def validate(payload: _Payload):
        return payload

    return app


def _client() -> TestClient:
    return TestClient(_minimal_app(), raise_server_exceptions=False)


def test_unhandled_exception_returns_generic_500_envelope():
    response = _client().get("/boom")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_error"
    assert body["error"]["message"] == "An unexpected error occurred."
    assert "internal detail" not in body["error"]["message"]
    assert body["error"]["request_id"] == response.headers[REQUEST_ID_HEADER]


def test_app_error_returns_its_own_code_and_message():
    response = _client().get("/app-error")

    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "application_error"
    assert body["error"]["message"] == "Something specific went wrong."
    assert body["error"]["details"] == {"field": "value"}
    assert body["error"]["request_id"] is not None


def test_validation_error_returns_422_envelope():
    response = _client().post("/validate", json={"wrong_field": "x"})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert "errors" in body["error"]["details"]


def test_not_found_returns_http_error_envelope():
    response = _client().get("/does-not-exist")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "http_error"
