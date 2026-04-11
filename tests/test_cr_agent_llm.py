"""Tests for LLM-driven CR agent (mocked OpenAI-compatible client)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from agentic_ai.config import JiraConfig
from agentic_ai.cr_agent import run_cr_agent
from agentic_ai.cr_agent_llm import run_llm_cr_agent


@dataclass
class _FakeMsg:
    content: str


@dataclass
class _FakeChoice:
    message: _FakeMsg


@dataclass
class _FakeResp:
    choices: list[_FakeChoice]


class _FakeCompletions:
    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)

    def create(self, model: str, messages: list, **kwargs: object) -> _FakeResp:
        if not self._responses:
            return _FakeResp([_FakeChoice(_FakeMsg('{"tool":"done"}'))])
        text = self._responses.pop(0)
        return _FakeResp([_FakeChoice(_FakeMsg(text))])


class _FakeOpenAI:
    def __init__(self, responses: list[str]) -> None:
        self.chat = SimpleNamespace(completions=_FakeCompletions(responses))


def test_run_llm_cr_agent_writes_cr_and_finishes(tmp_path: Path) -> None:
    client = _FakeOpenAI(
        [
            '{"tool":"write_cr_document","markdown":"# Change Request (CR): Test\\n\\n## Scope\\n- A\\n"}',
            '{"tool":"done"}',
        ]
    )
    md, items = run_llm_cr_agent(
        meeting_text="m",
        scope_text="s",
        output_dir=tmp_path,
        create_jira=False,
        client=client,
        model="fake-model",
        max_steps=8,
        jira_cfg=None,
    )
    assert "Change Request" in md
    assert (tmp_path / "cr_document.md").read_text(encoding="utf-8") == md
    assert items == []


def test_run_llm_cr_agent_jira_tools_with_mock_client(tmp_path: Path) -> None:
    responses = [
        '{"tool":"write_cr_document","markdown":"# Change Request (CR): LLM\\n\\n## Notes\\n- x\\n"}',
        '{"tool":"create_jira_epic","summary":"Epic sum","description":"Epic body"}',
        '{"tool":"create_jira_story","summary":"Story one","description":"S1"}',
        '{"tool":"create_jira_task","summary":"Task a","description":"T1","story_index":0}',
        '{"tool":"done"}',
    ]
    client = _FakeOpenAI(responses)
    jira_cfg = JiraConfig(
        base_url="https://example.atlassian.net",
        email="a@example.com",
        api_token="tok",
        project_key="KAN",
        epic_issue_type="Epic",
        story_issue_type="Story",
        task_issue_type="Task",
        epic_link_field="customfield_10014",
        verify_ssl=True,
    )

    def _fake_create(**kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(key="MOCK-1", id="1", url="https://example.atlassian.net/browse/MOCK-1")

    with patch("agentic_ai.cr_agent_llm.JiraClient") as jc:
        jc.return_value.create_issue.side_effect = _fake_create
        md, items = run_llm_cr_agent(
            meeting_text="meeting",
            scope_text="scope",
            output_dir=tmp_path,
            create_jira=True,
            client=client,
            model="fake-model",
            max_steps=12,
            jira_cfg=jira_cfg,
        )
    assert "Change Request" in md
    assert len(items) >= 3
    assert items[0]["type"] == "Epic"


def test_run_cr_agent_prefers_llm_when_client_injected(tmp_path: Path) -> None:
    fake = _FakeOpenAI(
        [
            '{"tool":"write_cr_document","markdown":"# Change Request (CR): Injected\\n"}',
            '{"tool":"done"}',
        ]
    )
    meeting = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "sample_meeting.txt"
    scope = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "sample_scope.txt"
    art = run_cr_agent(
        meeting_path=meeting,
        scope_path=scope,
        output_dir=tmp_path,
        create_jira=False,
        use_llm=True,
        llm_client=fake,
    )
    assert art.llm_used is True
    assert "Injected" in art.cr_markdown
