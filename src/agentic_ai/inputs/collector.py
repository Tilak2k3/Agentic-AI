"""High-level helpers mapping logical inputs to file loaders."""

from __future__ import annotations

from pathlib import Path

from agentic_ai.inputs.documents import read_text_document
from agentic_ai.inputs.meeting_recordings import extract_meeting_text


def load_sow_or_scope(path: str | Path) -> str:
    """Load a statement-of-work or scope document from disk."""
    return read_text_document(path)


def load_kickoff_notes(path: str | Path) -> str:
    """Load kickoff meeting notes from disk (same supported types as SOW)."""
    return read_text_document(path)


def load_meeting_recording(path: str | Path) -> str:
    """Load meeting content from a text or audio file."""
    return extract_meeting_text(path)
