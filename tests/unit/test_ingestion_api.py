import base64

from fastapi.testclient import TestClient

from aegis.domain.ids import new_id
from aegis.settings import Settings
from apps.api.main import create_app


class SubmissionClient:
    def __init__(self):
        self.requests = []

    async def submit(self, request):
        self.requests.append(request)
        return {"workflow_id": "ingestion-test"}

    async def status(self, workflow_id):
        return {"workflow_id": workflow_id, "status": "RUNNING", "result": None}


def test_submit_and_batch_use_temporal_and_response_envelope():
    app = create_app(Settings())
    client = SubmissionClient()
    app.state.ingestion_submissions = client
    request = {
        "source_id": new_id("src"),
        "idempotency_key": "test",
        "content_base64": base64.b64encode(b"Title\nBody").decode(),
    }
    with TestClient(app) as http:
        response = http.post("/api/v1/ingestions", json=request)
        assert response.status_code == 202
        assert response.json()["data"]["workflow_id"] == "ingestion-test"
        assert response.json()["meta"]["api_version"] == "v1"
        batch = http.post("/api/v1/ingestions/batch", json={"items": [request, request]})
        assert batch.status_code == 202
        assert len(batch.json()["data"]["submissions"]) == 2
        assert len(client.requests) == 3
        status = http.get("/api/v1/ingestion-runs/ingestion-test")
        assert status.json()["data"]["status"] == "RUNNING"


def test_invalid_content_and_worker_paths_are_rejected():
    app = create_app(Settings())
    client = SubmissionClient()
    app.state.ingestion_submissions = client
    request = {"source_id": new_id("src"), "idempotency_key": "test", "content_base64": "////"}
    with TestClient(app) as http:
        invalid = http.post("/api/v1/ingestions", json=request)
        assert invalid.status_code == 422
        assert invalid.json()["error"]["code"] == "INVALID_ARGUMENT"
        request["path"] = "../../secret"
        assert http.post("/api/v1/ingestions", json=request).status_code == 422
        assert client.requests == []


def test_disabled_temporal_returns_source_unavailable():
    with TestClient(create_app(Settings(temporal_enabled=False))) as client:
        response = client.post(
            "/api/v1/ingestions",
            json={
                "source_id": new_id("src"),
                "idempotency_key": "test",
                "content_base64": "VGl0bGU=",
            },
        )
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "SOURCE_UNAVAILABLE"


def test_body_limit_before_json_parsing():
    from aegis.ingestion.http import MAX_HTTP_BODY_BYTES

    with TestClient(create_app(Settings())) as client:
        result = client.post("/api/v1/ingestions", content=b"x" * (MAX_HTTP_BODY_BYTES + 1))
        assert result.status_code == 422
        assert result.json()["error"]["code"] == "INVALID_ARGUMENT"
        assert result.json()["error"]["request_id"] == result.headers["x-request-id"]


def test_temporal_connection_failure_uses_existing_error_contract(monkeypatch):
    from temporalio.client import Client

    async def unavailable(*args, **kwargs):
        raise RuntimeError("Failed client connect: private host info")

    monkeypatch.setattr(Client, "connect", unavailable)
    with TestClient(create_app(Settings(temporal_enabled=True))) as client:
        response = client.post(
            "/api/v1/ingestions",
            json={
                "source_id": new_id("src"),
                "idempotency_key": "test",
                "content_base64": "VGl0bGU=",
            },
        )
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "SOURCE_UNAVAILABLE"
        assert "private" not in response.text
