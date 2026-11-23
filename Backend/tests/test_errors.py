from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.errors import ApplicationError
from app.main import create_app


class Payload(BaseModel):
    amount: int


@pytest.fixture
def client():
    app = create_app()

    @app.post("/test/validation")
    async def validate_payload(payload: Payload):
        return payload

    @app.get("/test/unexpected")
    async def unexpected():
        raise RuntimeError("private-database-password")

    @app.get("/test/unavailable")
    async def unavailable():
        raise ApplicationError(503, "SERVICE_UNAVAILABLE", "Database is not configured.")

    @app.get("/test/auth")
    async def auth():
        raise HTTPException(401, "private session value", headers={"WWW-Authenticate": "Bearer"})

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def test_validation_error_omits_the_submitted_payload(client):
    response = client.post("/test/validation", json={"amount": "private-customer-input"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "private-customer-input" not in response.text


def test_unexpected_error_has_safe_body_and_request_context(client):
    response = client.get("/test/unexpected")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert response.json()["error"]["request_id"] == response.headers["x-request-id"]
    assert response.headers["cache-control"] == "no-store"
    assert "private-database-password" not in response.text


def test_application_error_preserves_its_public_code(client):
    response = client.get("/test/unavailable")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"


def test_http_error_preserves_auth_headers_without_disclosing_detail(client):
    response = client.get("/test/auth")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["error"]["code"] == "SESSION_EXPIRED"
    assert "private session value" not in response.text


def test_request_ids_are_server_generated_and_distinct(client):
    first = client.get("/api/v1/health", headers={"X-Request-ID": "untrusted-value"})
    second = client.get("/api/v1/health")

    assert UUID(first.headers["x-request-id"])
    assert first.headers["x-request-id"] != "untrusted-value"
    assert first.headers["x-request-id"] != second.headers["x-request-id"]
