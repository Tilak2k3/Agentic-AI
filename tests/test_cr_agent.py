"""Tests for CR agent generation and output artifacts."""

from __future__ import annotations

from pathlib import Path

from agentic_ai.cr_agent import build_cr_document, derive_jira_items, run_cr_agent

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_build_cr_document_contains_required_sections() -> None:
    meeting = """Kickoff decisions\n- Add security review step\n- Move timeline by one sprint\n"""
    scope = """SOW baseline\n- Implement intake pipeline\n- Generate output docs\n"""
    md = build_cr_document(meeting_text=meeting, scope_text=scope)
    assert "# Change Request (CR):" in md
    assert "## 1. Scope Baseline (from SOW/Scope Document)" in md
    assert "## 2. Meeting Findings" in md
    assert "## 5. Proposed Epic / User Stories / Tasks" in md
    assert "### Epic" in md
    assert "### User Stories" in md
    assert "### Tasks" in md


def test_derive_jira_items_extracts_epic_story_task() -> None:
    md = build_cr_document("Meeting notes line", "Scope title line")
    title, stories, tasks = derive_jira_items(md)
    assert title
    assert len(stories) >= 1
    assert len(tasks) >= 1


def test_run_cr_agent_generates_cr_file_without_jira(tmp_path: Path) -> None:
    meeting = REPO_ROOT / "tests" / "fixtures" / "sample_meeting.txt"
    scope = REPO_ROOT / "tests" / "fixtures" / "sample_scope.txt"
    artifacts = run_cr_agent(
        meeting_path=meeting,
        scope_path=scope,
        output_dir=tmp_path,
        create_jira=False,
        use_llm=False,
    )
    assert artifacts.cr_file.is_file()
    assert artifacts.jira_output_file is None
    assert "Change Request" in artifacts.cr_markdown
