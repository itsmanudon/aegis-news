import os

import httpx
import pytest

pytestmark = pytest.mark.e2e


def test_running_api_and_web_status():
    api = os.getenv("AEGIS_TEST_API_URL", "http://localhost:8000")
    web = os.getenv("AEGIS_TEST_WEB_URL", "http://localhost:3000")
    with httpx.Client(timeout=15) as client:
        health = client.get(f"{api}/health", headers={"X-Request-ID": "foundation-e2e"})
        assert health.status_code == 200
        assert health.json()["meta"]["request_id"] == "foundation-e2e"
        assert client.get(f"{api}/ready").status_code == 200
        assert client.get(f"{api}/openapi.json").json()["info"]["title"] == "AegisNews"
        page = client.get(web)
        assert page.status_code == 200
        assert "Aegis News" in page.text
        assert "A Wider View." in page.text
        assert "A Closer Read." in page.text
        assert 'href="/operations"' in page.text
        operations = client.get(f"{web}/operations")
        assert operations.status_code == 200
        assert "Operational Overview" in operations.text
        assert "Review Queue" in operations.text
