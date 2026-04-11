"""Tests for plan agent and Smartsheet line-item derivation."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentic_ai.plan_agent import (
    build_project_plan,
    derive_plan_line_items,
    run_plan_agent,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_build_project_plan_has_sections() -> None:
    md = build_project_plan("Meeting line about rollout.", "Scope line about deliverables and timeline.")
    assert "# Project Plan:" in md
    assert "## 5. Work breakdown (line items)" in md
    assert "| Phase | Task |" in md


def test_derive_plan_line_items_from_table() -> None:
    md = build_project_plan("m", "s")
    items = derive_plan_line_items(md)
    assert len(items) >= 3
    assert all(it.name for it in items)


def test_run_plan_agent_writes_file_no_smartsheet(tmp_path: Path) -> None:
    meeting = REPO_ROOT / "tests" / "fixtures" / "sample_meeting.txt"
    scope = REPO_ROOT / "tests" / "fixtures" / "sample_scope.txt"
    art = run_plan_agent(
        meeting_path=meeting,
        scope_path=scope,
        output_dir=tmp_path,
        sync_smartsheet=False,
        use_llm=False,
    )
    assert art.plan_file.is_file()
    assert len(art.line_items) >= 1
    assert art.llm_used is False


def test_run_plan_agent_inline_text(tmp_path: Path) -> None:
    art = run_plan_agent(
        meeting_text="Notes: ship MVP by Q2.",
        scope_text="Scope: API, UI, and docs.",
        output_dir=tmp_path,
        sync_smartsheet=False,
        use_llm=False,
    )
    assert "Project Plan" in art.plan_markdown
    assert art.plan_file.exists()


def test_run_plan_agent_smartsheet_requires_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SMARTSHEET_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("SMARTSHEET_SHEET_ID", raising=False)
    with pytest.raises(ValueError, match="Smartsheet"):
        run_plan_agent(
            meeting_text="m",
            scope_text="s",
            output_dir=tmp_path,
            sync_smartsheet=True,
            use_llm=False,
        )
