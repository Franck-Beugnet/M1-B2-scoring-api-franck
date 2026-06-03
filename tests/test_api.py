"""M1-B2 — API tests.

3 tests required (health, predict valid, predict invalid).
Bonus tests welcome (deterministic, info schema, etc.).
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_ok(client: TestClient) -> None:
    """/health returns 200 and the expected status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_predict_valid_payload(client: TestClient, valid_payload: dict) -> None:
    """/predict returns 200 with a well-formed response on valid input.
    """
    response = client.post("/predict", json=valid_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["prediction"] in (0, 1)
    assert 0.0 <= data["probability"] <= 1.0
    assert data["request_id"]
    assert data["model_version"]


def test_predict_missing_field_returns_422(
    client: TestClient, valid_payload: dict
) -> None:
    """/predict returns 422 on missing required field.
    """
    invalid = {k: v for k, v in valid_payload.items() if k != "loan_amnt"}
    response = client.post("/predict", json=invalid)
    assert response.status_code == 422


def test_health_returns_503_when_model_not_loaded(client: TestClient) -> None:
    """/health returns 503 when model is absent from app state."""
    original_model = app.state.model
    app.state.model = None
    try:
        response = client.get("/health")
    finally:
        app.state.model = original_model
    assert response.status_code == 503
    assert response.json()["detail"] == "Model not loaded"


def test_info_contains_required_non_null_keys(client: TestClient) -> None:
    """/info exposes mandatory metadata keys plus api_version."""
    response = client.get("/info")
    assert response.status_code == 200
    data = response.json()

    required_keys = [
        "api_version",
        "model_version",
        "created_at",
        "sklearn_version",
        "dataset_sha256",
        "metrics_holdout",
    ]
    for key in required_keys:
        assert key in data
        assert data[key] is not None


def test_x_request_id_header_in_response(client: TestClient) -> None:
    """Bonus: X-Request-ID header is present in all responses.

    - If provided in request, same ID is returned.
    - If missing, auto-generated UUID is returned.
    """
    # Case 1: provided request ID
    response = client.get("/health", headers={"X-Request-ID": "my-custom-id"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "my-custom-id"

    # Case 2: auto-generated request ID
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    # Ensure it looks like a UUID (standard UUID is 36 chars including hyphens)
    assert len(response.headers["X-Request-ID"]) == 36
