r"""
Meeting inputs: text files always; audio only when TEST_AUDIO_PATH + HF token are set.

Where to put your audio path (choose one):
  1. Environment variable (recommended):
       PowerShell:  $env:TEST_AUDIO_PATH = "D:\path\to\recording.flac"
       CMD:         set TEST_AUDIO_PATH=D:\path\to\recording.flac
     Also set HUGGINGFACE_API_KEY (or HF_TOKEN) in .env or the environment.

  2. Before running pytest in one line:
       TEST_AUDIO_PATH="C:/audio/sample.wav" pytest tests/test_meeting_recordings.py -m integration -v
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from huggingface_hub.errors import HfHubHTTPError

from agentic_ai.inputs.meeting_recordings import extract_meeting_text, transcribe_audio_file


def _skip_if_hf_billing_error(exc: BaseException) -> None:
    msg = str(exc).lower()
    if "402" in str(exc) or "payment required" in msg or "pre-paid credits" in msg:
        pytest.skip(
            "Hugging Face returned 402 (e.g. fal-ai needs credits). "
            "Set ASR_BACKEND=hf in .env or add fal-ai prepaid credits."
        )

REPO_ROOT = Path(__file__).resolve().parent.parent


def _audio_path_from_env() -> Path | None:
    raw = os.environ.get("TEST_AUDIO_PATH", "").strip()
    if not raw:
        return None
    p = Path(raw).expanduser().resolve()
    return p if p.is_file() else None


def test_extract_meeting_text_from_txt_fixture() -> None:
    path = REPO_ROOT / "tests" / "fixtures" / "sample_meeting.txt"
    text = extract_meeting_text(path)
    assert "Kickoff" in text


def test_extract_meeting_text_missing_file() -> None:
    with pytest.raises(FileNotFoundError):
        extract_meeting_text("/nonexistent/meeting.txt")


def test_extract_meeting_text_bad_extension(tmp_path: Path) -> None:
    p = tmp_path / "x.bin"
    p.write_bytes(b"\x00\x01")
    with pytest.raises(ValueError, match="Unsupported"):
        extract_meeting_text(p)


@pytest.mark.integration
def test_transcribe_audio_manual_path() -> None:
    """
    Runs only when TEST_AUDIO_PATH points to a real audio file and HF credentials exist.
    """
    path = _audio_path_from_env()
    if path is None:
        pytest.skip(
            "Set TEST_AUDIO_PATH to your audio file (full path), e.g. "
            'TEST_AUDIO_PATH=D:\\recordings\\call.flac'
        )
    key = os.environ.get("HUGGINGFACE_API_KEY") or os.environ.get("HF_TOKEN")
    if not key:
        pytest.skip("Set HUGGINGFACE_API_KEY or HF_TOKEN for live ASR.")

    try:
        text = transcribe_audio_file(path)
    except HfHubHTTPError as e:
        _skip_if_hf_billing_error(e)
        raise
    assert isinstance(text, str)
    assert len(text.strip()) >= 0


@pytest.mark.integration
def test_extract_meeting_text_audio_end_to_end() -> None:
    """Same as above but through extract_meeting_text (audio branch)."""
    path = _audio_path_from_env()
    if path is None:
        pytest.skip("Set TEST_AUDIO_PATH to your audio file.")
    key = os.environ.get("HUGGINGFACE_API_KEY") or os.environ.get("HF_TOKEN")
    if not key:
        pytest.skip("Set HUGGINGFACE_API_KEY or HF_TOKEN for live ASR.")

    try:
        text = extract_meeting_text(path)
    except HfHubHTTPError as e:
        _skip_if_hf_billing_error(e)
        raise
    assert isinstance(text, str)
