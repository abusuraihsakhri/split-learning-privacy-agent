"""API authorization and response regression tests."""
from fastapi.testclient import TestClient
from agents.api import app


def test_log_endpoint_is_disabled_without_explicit_token(monkeypatch):
    monkeypatch.delenv("AUDIT_LOG_READ_TOKEN", raising=False)
    assert TestClient(app).get("/api/audit/logs").status_code == 503


def test_log_endpoint_requires_distinct_read_token(monkeypatch):
    monkeypatch.setenv("AUDIT_LOG_READ_TOKEN", "independent-test-read-token")
    client = TestClient(app)
    assert client.get("/api/audit/logs").status_code == 403
    assert client.get("/api/audit/logs", headers={"X-Audit-Token": "wrong"}).status_code == 403
    response = client.get("/api/audit/logs", headers={"X-Audit-Token": "independent-test-read-token"})
    assert response.status_code == 200
    assert response.json()["verified"] is True


def test_api_rejects_non_finite_values():
    client = TestClient(app)
    result = client.post("/api/audit", json={
        "task_id": "T", "target_identifier": "KEY", "primary_metric": "NaN"
    })
    assert result.status_code == 422


def test_browser_assets_are_accessible_from_backend():
    client = TestClient(app)
    assert client.get("/").status_code == 200
    script = client.get("/app.js")
    assert script.status_code == 200
    assert "evaluateLocal" in script.text
