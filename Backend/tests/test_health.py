import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    with TestClient(create_app()) as test_client:
        yield test_client


def test_health_is_live_without_database_or_model_credentials(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-request-id"]


def test_unknown_api_route_returns_the_shared_error_envelope(client):
    response = client.get("/api/v1/missing")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "NOT_FOUND",
            "message": "Not Found",
            "request_id": response.headers["x-request-id"],
        }
    }


def test_wrong_method_returns_json_and_preserves_allow_header(client):
    response = client.post("/api/v1/health")

    assert response.status_code == 405
    assert response.headers["allow"] == "GET"
    assert response.json()["error"]["code"] == "METHOD_NOT_ALLOWED"


def test_health_openapi_matches_the_agreed_operation(client):
    schema = client.get("/openapi.json").json()
    operation = schema["paths"]["/api/v1/health"]["get"]

    assert operation["operationId"] == "getHealth"
    assert "404" in operation["responses"]
