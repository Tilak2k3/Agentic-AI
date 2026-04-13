"""CR agent LLM requirement when use_llm=True."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from agentic_ai.cr_agent import run_cr_agent

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_run_cr_agent_use_llm_raises_without_credentials(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("HUGGINGFACE_API_KEY", raising=False)
    meeting = REPO_ROOT / "tests" / "fixtures" / "sample_meeting.txt"
    scope = REPO_ROOT / "tests" / "fixtures" / "sample_scope.txt"
    with (
        patch("agentic_ai.cr_agent.get_openai_router_client", return_value=None),
        patch("agentic_ai.cr_agent.get_llm_router_config", return_value=None),
    ):
        with pytest.raises(ValueError, match="LLM"):
            run_cr_agent(
                meeting_path=meeting,
                scope_path=scope,
                output_dir=tmp_path,
                create_jira=False,
                use_llm=True,
            )
