"""Smoke tests for collector helpers."""

from __future__ import annotations

from pathlib import Path

from agentic_ai.inputs.collector import load_kickoff_notes, load_meeting_recording, load_sow_or_scope

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_load_sow_and_kickoff_same_pipeline() -> None:
    path = REPO_ROOT / "tests" / "fixtures" / "sample_meeting.txt"
    assert load_sow_or_scope(path) == load_kickoff_notes(path)


def test_load_meeting_recording_text() -> None:
    path = REPO_ROOT / "tests" / "fixtures" / "sample_meeting.txt"
    assert "phase one" in load_meeting_recording(path)
