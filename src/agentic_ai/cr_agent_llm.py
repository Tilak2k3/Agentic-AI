"""LLM-driven CR agent loop using Hugging Face OpenAI-compatible router."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests

from agentic_ai.config import JiraConfig
from agentic_ai.jira_client import JiraClient
from agentic_ai.llm_client import OpenAIClientPort

TOOL_SYSTEM = """You are a change-request (CR) automation agent. Each reply must be ONE JSON object only (no markdown fences, no extra text).

Tools you can emit, one per turn:
1) {"tool":"write_cr_document","markdown":"<complete markdown CR document>"}
2) {"tool":"create_jira_epic","summary":"<short title>","description":"<plain text>"}
3) {"tool":"create_jira_story","summary":"<short>","description":"<plain text>"}
4) {"tool":"create_jira_task","summary":"<short>","description":"<plain text>","story_index":<0-based int>}
5) {"tool":"done"}

Workflow:
- Start by writing the CR markdown from the meeting transcript and scope document (sections: scope baseline, meeting findings, change summary, impact, proposed work, acceptance criteria).
- If Jira is ENABLED for this run: after the CR, create exactly one epic summarizing the CR, then create user stories, then tasks. Use story_index on tasks to attach each task to the Nth story you created (0 = first story).
- If Jira is DISABLED: after write_cr_document, respond with {"tool":"done"}.
- End with {"tool":"done"} when everything requested is finished.

Rules:
- Descriptions are plain text; the runtime converts them for Jira.
- Summaries must be under 200 characters.
- Grounding: only state scope baseline facts supported by the scope text; only state meeting findings supported by the transcript. If a section has no evidence, say what is unknown rather than inventing detail.
- Before write_cr_document, mentally verify each major claim is traceable to the provided meeting or scope text.
"""


def _extract_json_object(text: str) -> dict[str, Any]:
    t = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", t, re.DOTALL)
    if fence:
        t = fence.group(1)
    start, end = t.find("{"), t.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model output")
    return json.loads(t[start : end + 1])


@dataclass
class _AgentState:
    out_dir: Path
    cr_file: Path
    cr_markdown: str = ""
    create_jira: bool = True
    jira_cfg: JiraConfig | None = None
    jira_client: JiraClient | None = None
    epic_key: str | None = None
    story_keys: list[str] = field(default_factory=list)
    jira_items: list[dict[str, str]] = field(default_factory=list)
    labels: list[str] = field(default_factory=lambda: ["cr-agent", "change-request", "llm"])


def _execute_tool(action: dict[str, Any], state: _AgentState) -> dict[str, Any]:
    tool = action.get("tool")
    if tool == "write_cr_document":
        md = str(action.get("markdown") or "").strip()
        if not md:
            return {"ok": False, "error": "missing markdown"}
        state.cr_markdown = md
        state.cr_file.parent.mkdir(parents=True, exist_ok=True)
        state.cr_file.write_text(md, encoding="utf-8")
        return {"ok": True, "path": str(state.cr_file), "chars": len(md)}

    if not state.create_jira or state.jira_cfg is None or state.jira_client is None:
        return {"ok": False, "error": "Jira is disabled or not configured for this run"}

    cfg = state.jira_cfg
    client = state.jira_client

    if tool == "create_jira_epic":
        summary = str(action.get("summary") or "CR Epic")[:250]
        description = str(action.get("description") or state.cr_markdown[:29000] or summary)
        epic = client.create_issue(
            project_key=cfg.project_key,
            issue_type=cfg.epic_issue_type,
            summary=summary,
            description=description,
            labels=state.labels,
        )
        state.epic_key = epic.key
        state.jira_items.append({"type": "Epic", "key": epic.key, "url": epic.url, "summary": summary})
        return {"ok": True, "key": epic.key, "url": epic.url}

    if tool == "create_jira_story":
        if not state.epic_key:
            return {"ok": False, "error": "create_jira_epic must run before stories"}
        summary = str(action.get("summary") or "CR Story")[:250]
        description = str(action.get("description") or summary)
        try:
            story_issue = client.create_issue(
                project_key=cfg.project_key,
                issue_type=cfg.story_issue_type,
                summary=summary,
                description=f"{description}\n\nLinked Epic: {state.epic_key}",
                labels=state.labels,
                extra_fields={cfg.epic_link_field: state.epic_key},
            )
        except requests.HTTPError as e:
            body = (e.response.text if e.response is not None else "").lower()
            if "cannot be set" in body or "unknown" in body or cfg.epic_link_field.lower() in body:
                story_issue = client.create_issue(
                    project_key=cfg.project_key,
                    issue_type=cfg.story_issue_type,
                    summary=summary,
                    description=f"{description}\n\nLinked Epic: {state.epic_key}",
                    labels=state.labels,
                    extra_fields={"parent": {"key": state.epic_key}},
                )
            else:
                raise
        state.story_keys.append(story_issue.key)
        state.jira_items.append(
            {"type": "Story", "key": story_issue.key, "url": story_issue.url, "summary": summary}
        )
        return {"ok": True, "key": story_issue.key, "story_index": len(state.story_keys) - 1}

    if tool == "create_jira_task":
        idx = action.get("story_index")
        if not isinstance(idx, int) or idx < 0 or idx >= len(state.story_keys):
            return {"ok": False, "error": f"invalid story_index {idx!r}; stories so far: {len(state.story_keys)}"}
        story_key = state.story_keys[idx]
        summary = str(action.get("summary") or "CR Task")[:250]
        description = str(action.get("description") or summary)
        task_issue = client.create_issue(
            project_key=cfg.project_key,
            issue_type=cfg.task_issue_type,
            summary=summary,
            description=f"For story {story_key}:\n\n{description}",
            labels=state.labels,
        )
        state.jira_items.append(
            {"type": "Task", "key": task_issue.key, "url": task_issue.url, "summary": summary}
        )
        return {"ok": True, "key": task_issue.key, "story_key": story_key}

    if tool == "done":
        return {"ok": True, "finished": True}

    return {"ok": False, "error": f"unknown tool {tool!r}"}


def run_llm_cr_agent(
    *,
    meeting_text: str,
    scope_text: str,
    output_dir: Path,
    create_jira: bool,
    client: OpenAIClientPort,
    model: str,
    max_steps: int,
    jira_cfg: JiraConfig | None,
) -> tuple[str, list[dict[str, str]]]:
    """
    Multi-turn loop: model emits one JSON tool call per turn; runtime executes and returns results.

    Returns (cr_markdown, jira_items).
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cr_file = out_dir / "cr_document.md"

    jira_client: JiraClient | None = None
    if create_jira and jira_cfg is not None:
        jira_client = JiraClient(
            base_url=jira_cfg.base_url,
            email=jira_cfg.email,
            api_token=jira_cfg.api_token,
            verify_ssl=jira_cfg.verify_ssl,
        )

    state = _AgentState(
        out_dir=out_dir,
        cr_file=cr_file,
        create_jira=create_jira,
        jira_cfg=jira_cfg,
        jira_client=jira_client,
    )

    user_block = "\n".join(
        [
            "Meeting transcript:",
            meeting_text.strip()[:50000] or "(empty)",
            "",
            "Scope / SOW document:",
            scope_text.strip()[:50000] or "(empty)",
            "",
            f"Jira enabled for this run: {str(bool(create_jira and jira_cfg)).lower()}",
        ]
    )

    messages: list[dict[str, str]] = [
        {"role": "system", "content": TOOL_SYSTEM},
        {"role": "user", "content": user_block},
    ]

    for _ in range(max_steps):
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
        )
        raw = (resp.choices[0].message.content or "").strip()
        if not raw:
            raise RuntimeError("LLM returned empty content")
        action = _extract_json_object(raw)
        tool = action.get("tool")
        messages.append({"role": "assistant", "content": raw})

        if tool == "done":
            _execute_tool(action, state)
            break

        result = _execute_tool(action, state)
        payload: dict[str, Any] = {"tool_result": result}
        if not result.get("ok"):
            payload["hint"] = "Fix the last tool call; next message must be one JSON object only."
        messages.append({"role": "user", "content": json.dumps(payload)})

    if not state.cr_markdown.strip():
        raise RuntimeError("LLM did not produce a CR document (write_cr_document never succeeded)")

    return state.cr_markdown, state.jira_items
