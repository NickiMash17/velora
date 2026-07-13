"""Per docs/architecture/API.md §7 and Observability.md §2: every response
carries an X-Request-ID, echoed back if the client supplied one, generated
otherwise, and it is this id that ties a response to its structured log
line and (for errors) to the error envelope's request_id field."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.shared.middleware import REQUEST_ID_HEADER, RequestIDMiddleware


def _minimal_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)

    @app.get("/ping")
    async def ping():
        return {"pong": True}

    return app


def test_request_id_is_generated_when_absent():
    client = TestClient(_minimal_app())

    response = client.get("/ping")

    assert response.status_code == 200
    assert REQUEST_ID_HEADER in response.headers
    assert len(response.headers[REQUEST_ID_HEADER]) > 0


def test_request_id_is_echoed_when_supplied():
    client = TestClient(_minimal_app())

    response = client.get("/ping", headers={REQUEST_ID_HEADER: "client-supplied-id-123"})

    assert response.headers[REQUEST_ID_HEADER] == "client-supplied-id-123"


def test_request_id_differs_across_independent_requests():
    client = TestClient(_minimal_app())

    first = client.get("/ping").headers[REQUEST_ID_HEADER]
    second = client.get("/ping").headers[REQUEST_ID_HEADER]

    assert first != second
