"""Plan agent with mocked LLM (required when use_llm=True)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from agentic_ai.plan_agent import run_plan_agent


@dataclass
class _Msg:
    content: str


@dataclass
class _Choice:
    message: _Msg


@dataclass
class _Resp:
    choices: list[_Choice]


class _FakeCompletions:
    def create(self, model: str, messages: list, **kwargs: object) -> _Resp:
        md = (
            "# Project Plan: Mock\n\n"
            "## 5. Work breakdown (line items)\n"
            "| Phase | Task | Start | End |\n"
            "|-------|------|-------|-----|\n"
            "| P1 | Task one | W1 | W2 |\n"
            "| P2 | Task two | W2 | W3 |\n"
        )
        return _Resp([_Choice(_Msg(md))])


class _FakeOpenAI:
    def __init__(self) -> None:
        self.chat = SimpleNamespace(completions=_FakeCompletions())


def test_run_plan_agent_use_llm_requires_client_or_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("HUGGINGFACE_API_KEY", raising=False)
    with (
        patch("agentic_ai.plan_agent.get_openai_router_client", return_value=None),
        patch("agentic_ai.plan_agent.get_llm_router_config", return_value=None),
    ):
        with pytest.raises(ValueError, match="LLM"):
            run_plan_agent(
                meeting_text="a",
                scope_text="b",
                output_dir=tmp_path,
                use_llm=True,
            )


def test_run_plan_agent_with_injected_llm(tmp_path: Path) -> None:
    art = run_plan_agent(
        meeting_text="Meeting content for plan.",
        scope_text="Scope content for plan.",
        output_dir=tmp_path,
        use_llm=True,
        llm_client=_FakeOpenAI(),
        sync_smartsheet=False,
    )
    assert art.llm_used is True
    assert "| Phase | Task |" in art.plan_markdown
    assert len(art.line_items) >= 1
