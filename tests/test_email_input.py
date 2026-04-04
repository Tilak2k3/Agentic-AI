"""Tests for .eml parsing; IMAP/Graph only when configured."""

from __future__ import annotations

import email.policy
import os
from email.message import EmailMessage
from pathlib import Path

import pytest

from agentic_ai.config import get_azure_graph_config, get_imap_config
from agentic_ai.inputs.email_input import (
    extract_text_from_eml_bytes,
    extract_text_from_eml_path,
    fetch_graph_messages_as_text,
    fetch_imap_messages_as_thread_text,
)


def _sample_eml_bytes() -> bytes:
    msg = EmailMessage()
    msg["Subject"] = "Re: Project scope"
    msg["From"] = "alice@example.com"
    msg["To"] = "bob@example.com"
    msg.set_content("Please see the attached timeline.\nSecond line.")
    return msg.as_bytes(policy=email.policy.SMTP)


def test_extract_text_from_eml_bytes() -> None:
    text = extract_text_from_eml_bytes(_sample_eml_bytes())
    assert "Project scope" in text
    assert "timeline" in text
    assert "alice@example.com" in text


def test_extract_text_from_eml_file(tmp_path: Path) -> None:
    p = tmp_path / "thread.eml"
    p.write_bytes(_sample_eml_bytes())
    text = extract_text_from_eml_path(p)
    assert "Second line" in text


@pytest.mark.integration
def test_fetch_imap_when_configured() -> None:
    if get_imap_config() is None:
        pytest.skip("Set IMAP_HOST, IMAP_USER, IMAP_PASSWORD to run live IMAP test.")
    try:
        text = fetch_imap_messages_as_thread_text(max_messages=3)
    except RuntimeError as e:
        if "could not select folder" in str(e).lower():
            pytest.skip(f"IMAP folder misconfigured: {e}")
        raise
    assert isinstance(text, str)


@pytest.mark.integration
def test_fetch_graph_when_configured() -> None:
    if get_azure_graph_config() is None:
        pytest.skip("Set AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET.")
    user = os.environ.get("TEST_GRAPH_MAIL_USER")
    if not user:
        pytest.skip("Set TEST_GRAPH_MAIL_USER to a mailbox UPN or user id for Graph mail test.")

    text = fetch_graph_messages_as_text(user_id=user, top=3)
    assert isinstance(text, str)
