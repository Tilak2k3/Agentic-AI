"""FastAPI app tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from agentic_ai.api.main import app

client = TestClient(app)


def test_health() -> None:
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_integration_status() -> None:
    r = client.get("/api/v1/integrations/status")
    assert r.status_code == 200
    data = r.json()
    assert "jira_configured" in data
    assert "smartsheet_configured" in data


def test_plan_generate_with_text() -> None:
    r = client.post(
        "/api/v1/plan/generate",
        json={
            "meeting_text": "Kickoff: deliver portal in 3 sprints.",
            "scope_text": "Scope: auth, dashboard, reporting.",
            "sync_smartsheet": False,
            "use_llm": False,
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "plan_markdown" in data
    assert data["line_items_count"] >= 0
    assert data["llm_used"] is False


def test_plan_generate_validation_error() -> None:
    r = client.post("/api/v1/plan/generate", json={"sync_smartsheet": False})
    assert r.status_code == 422


def test_cr_run_with_text_no_jira() -> None:
    r = client.post(
        "/api/v1/cr/run",
        json={
            "meeting_text": "Meeting decisions for CR.",
            "scope_text": "Scope baseline for CR.",
            "create_jira": False,
            "use_llm": False,
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "cr_markdown" in data
    assert data["jira_file"] is None
    assert data["llm_used"] is False
