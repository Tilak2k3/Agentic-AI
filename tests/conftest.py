"""Shared fixtures for input ingestion tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# Repo root: tests/conftest.py -> parent is repo root
REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    return FIXTURES_DIR


def audio_test_path() -> Path | None:
    """Path from env for manual ASR checks; see tests/test_meeting_recordings.py."""
    raw = os.environ.get("TEST_AUDIO_PATH", "").strip()
    if not raw:
        return None
    p = Path(raw).expanduser().resolve()
    return p if p.is_file() else None


@pytest.fixture
def optional_audio_path() -> Path | None:
    return audio_test_path()
