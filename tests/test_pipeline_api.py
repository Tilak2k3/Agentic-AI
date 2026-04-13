"""Pipeline job API (multipart + optional status)."""

from __future__ import annotations

import time

from fastapi.testclient import TestClient

from agentic_ai.api.main import app

client = TestClient(app)


def test_create_pipeline_job_requires_meeting_or_scope() -> None:
    r = client.post("/api/v1/pipeline/jobs", data={"use_llm": "false"})
    assert r.status_code == 400


def test_create_pipeline_job_returns_id() -> None:
    files = {
        "meeting": ("m.txt", b"Kickoff meeting notes line one.", "text/plain"),
        "scope": ("s.txt", b"Scope bullet one for delivery.", "text/plain"),
    }
    data = {"use_llm": "false", "create_jira": "false", "sync_smartsheet": "false"}
    r = client.post("/api/v1/pipeline/jobs", files=files, data=data)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "job_id" in body
    assert len(body["job_id"]) >= 8


def test_pipeline_job_completes_offline() -> None:
    files = {
        "meeting": ("m.txt", b"Meeting transcript for pipeline.", "text/plain"),
        "scope": ("s.txt", b"SOW scope for pipeline test.", "text/plain"),
    }
    data = {"use_llm": "false", "create_jira": "false", "sync_smartsheet": "false"}
    r = client.post("/api/v1/pipeline/jobs", files=files, data=data)
    assert r.status_code == 200
    job_id = r.json()["job_id"]

    deadline = time.time() + 90
    while time.time() < deadline:
        st = client.get(f"/api/v1/pipeline/jobs/{job_id}")
        if st.status_code != 200:
            break
        j = st.json()
        if j.get("done"):
            assert j.get("stage") in ("done", "error")
            if j.get("stage") == "done":
                art = j.get("artifacts") or {}
                assert art.get("cr_docx", "").endswith(".docx")
                assert "plan_file" in art and "raid_excel" in art
                ran = j.get("ran_agents") or []
                assert "cr" in ran and "plan" in ran and "raid" in ran
            return
        time.sleep(0.5)

    raise AssertionError("pipeline job did not finish in time")


def test_pipeline_meeting_only_skips_cr_and_plan() -> None:
    files = {"meeting": ("m.txt", b"Only a meeting transcript for RAID.", "text/plain")}
    data = {"use_llm": "false", "create_jira": "false", "sync_smartsheet": "false"}
    r = client.post("/api/v1/pipeline/jobs", files=files, data=data)
    assert r.status_code == 200, r.text
    job_id = r.json()["job_id"]

    deadline = time.time() + 90
    while time.time() < deadline:
        st = client.get(f"/api/v1/pipeline/jobs/{job_id}")
        if st.status_code != 200:
            break
        j = st.json()
        if j.get("done") and j.get("stage") == "done":
            art = j.get("artifacts") or {}
            assert "raid_excel" in art and art["raid_excel"].endswith(".xlsx")
            assert not art.get("cr_docx")
            ran = j.get("ran_agents") or []
            assert ran == ["raid"]
            return
        time.sleep(0.5)

    raise AssertionError("meeting-only pipeline did not finish in time")
