from unittest.mock import AsyncMock

from fastapi import HTTPException
from fastapi.testclient import TestClient

from aegis.contracts.api import ApiErrorEnvelope, DependencyStatus, ErrorCode
from apps.api.main import create_app


def test_liveness_info_and_openapi():
    app = create_app()
    with TestClient(app) as client:
        health = client.get(
            "/health",
            headers={"X-Request-ID": "test-request", "X-Correlation-ID": "test-correlation"},
        )
        assert health.status_code == 200
        assert health.json()["data"]["status"] == "ok"
        assert (
            health.json()["meta"]["request_id"] == health.headers["x-request-id"] == "test-request"
        )
        assert health.headers["x-correlation-id"] == "test-correlation"
        assert client.get("/api/v1/system/info").json()["data"]["stage"] == "foundation"
        schema = client.get("/openapi.json").json()
        assert set(schema["paths"]) == {"/health", "/ready", "/api/v1/system/info"}
        assert schema["paths"]["/ready"]["get"]["responses"]["503"]["content"]["application/json"][
            "schema"
        ]["$ref"].endswith("ApiErrorEnvelope")


def test_readiness_success_and_dependency_failure():
    app = create_app()
    with TestClient(app) as client:
        app.state.probe.check = AsyncMock(
            return_value=(DependencyStatus(name="postgres", ready=True),)
        )
        assert client.get("/ready").json()["data"]["status"] == "ready"
        app.state.probe.check = AsyncMock(
            return_value=(DependencyStatus(name="postgres", ready=False),)
        )
        response = client.get("/ready")
        assert response.status_code == 503
        assert (
            ApiErrorEnvelope.model_validate(response.json()).error.code
            == ErrorCode.SOURCE_UNAVAILABLE
        )


def test_errors_are_enveloped_and_hide_internal_details():
    app = create_app()

    @app.get("/test/invalid")
    def invalid(number: int):
        return number

    @app.get("/test/failure")
    def failure():
        raise RuntimeError("sensitive-internal-value")

    @app.get("/test/denied")
    def denied():
        raise HTTPException(
            401, detail="sensitive-internal-value", headers={"WWW-Authenticate": "Bearer"}
        )

    with TestClient(app) as client:
        for path, status, code in [
            ("/missing", 404, "NOT_FOUND"),
            ("/test/invalid?number=secret-input", 422, "INVALID_ARGUMENT"),
            ("/test/failure", 500, "INTERNAL_ERROR"),
            ("/test/denied", 401, "UNAUTHORIZED"),
        ]:
            response = client.get(path)
            assert response.status_code == status
            error = ApiErrorEnvelope.model_validate(response.json()).error
            assert error.code == code
            assert error.request_id == response.headers["x-request-id"]
            assert "sensitive-internal-value" not in response.text
            assert "secret-input" not in response.text
        assert client.get("/test/denied").headers["www-authenticate"] == "Bearer"
        response = client.post("/health")
        assert response.status_code == 405
        ApiErrorEnvelope.model_validate(response.json())


def test_metrics_do_not_label_arbitrary_urls():
    with TestClient(create_app()) as client:
        client.get("/attacker-secret-path")
        metrics = client.get("/metrics").text
        assert 'route="unmatched"' in metrics
        assert "attacker-secret-path" not in metrics
