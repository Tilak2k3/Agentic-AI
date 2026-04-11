"""CR agent: build CR document and create Jira epic/story/task items."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import requests

from agentic_ai.config import JiraConfig, get_jira_config, get_llm_router_config
from agentic_ai.cr_agent_llm import run_llm_cr_agent
from agentic_ai.inputs.collector import load_meeting_recording, load_sow_or_scope
from agentic_ai.jira_client import JiraClient, JiraIssue
from agentic_ai.llm_client import OpenAIClientPort, get_openai_router_client


@dataclass(frozen=True)
class CRArtifacts:
    cr_markdown: str
    cr_file: Path
    jira_output_file: Path | None
    jira_items: list[dict[str, str]]
    llm_used: bool = False


def _normalize_lines(text: str) -> list[str]:
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def _take_bullets(text: str, limit: int = 6) -> list[str]:
    lines = _normalize_lines(text)
    out: list[str] = []
    for line in lines:
        clean = line.lstrip("-* ").strip()
        if len(clean) < 8:
            continue
        out.append(clean)
        if len(out) >= limit:
            break
    return out


def _extract_title(scope_text: str, meeting_text: str) -> str:
    for src in (scope_text, meeting_text):
        for line in _normalize_lines(src):
            if len(line) > 12:
                return re.sub(r"\s+", " ", line)[:90]
    return "Change Request"


def build_cr_document(meeting_text: str, scope_text: str) -> str:
    title = _extract_title(scope_text, meeting_text)
    scope_points = _take_bullets(scope_text, limit=6)
    meeting_points = _take_bullets(meeting_text, limit=6)
    impact_points = [
        "Scope and requirements alignment updates are required before delivery.",
        "Implementation plan needs Jira traceability through Epic, Stories, and Tasks.",
        "Validation and sign-off criteria should be updated based on meeting outcomes.",
    ]
    if meeting_points:
        impact_points[0] = f"Scope updates inferred from meeting: {meeting_points[0]}"

    stories = [
        "As a project manager, I need a formal CR document so stakeholders can approve scope updates.",
        "As a delivery team member, I need Jira stories from the CR so implementation can be tracked.",
        "As a QA lead, I need task-level breakdowns so validation and sign-off are auditable.",
    ]
    tasks = [
        "Draft and review CR summary and proposed scope changes.",
        "Create Jira Epic and link derived user stories.",
        "Create implementation and QA tasks for each story.",
    ]

    lines = [
        f"# Change Request (CR): {title}",
        "",
        "## 1. Scope Baseline (from SOW/Scope Document)",
        *([f"- {p}" for p in scope_points] or ["- No scope points detected from source document."]),
        "",
        "## 2. Meeting Findings",
        *([f"- {p}" for p in meeting_points] or ["- No meeting findings detected from recording transcript."]),
        "",
        "## 3. Change Summary",
        "- Update project scope to incorporate the latest meeting decisions and constraints.",
        "- Align implementation priorities with agreed business outcomes and timelines.",
        "",
        "## 4. Impact Assessment",
        *[f"- {p}" for p in impact_points],
        "",
        "## 5. Proposed Epic / User Stories / Tasks",
        "### Epic",
        f"- Deliver CR updates for: {title}",
        "",
        "### User Stories",
        *[f"- {s}" for s in stories],
        "",
        "### Tasks",
        *[f"- {t}" for t in tasks],
        "",
        "## 6. Acceptance Criteria",
        "- CR document is reviewed and approved by relevant stakeholders.",
        "- Jira Epic, Stories, and Tasks are created and linked to CR scope.",
        "- Delivery and QA teams confirm readiness against updated scope.",
    ]
    return "\n".join(lines).strip() + "\n"


def derive_jira_items(cr_markdown: str) -> tuple[str, list[str], list[str]]:
    title_match = re.search(r"^#\s+Change Request \(CR\):\s+(.+)$", cr_markdown, re.M)
    title = title_match.group(1).strip() if title_match else "CR Delivery"
    story_matches = re.findall(r"^- As .+$", cr_markdown, re.M)
    task_matches = re.findall(r"^- (?:Draft|Create|Implement|Validate).+$", cr_markdown, re.M)
    stories = [s[2:] for s in story_matches[:3]]
    if not stories:
        stories = [
            "As a stakeholder, I need CR updates implemented and tracked in Jira.",
            "As a delivery lead, I need story-level requirements from CR decisions.",
            "As a QA member, I need traceable tasks for CR validation.",
        ]
    tasks = [t[2:] for t in task_matches[:6]]
    if not tasks:
        tasks = [
            "Create story-level implementation checklist.",
            "Create testing checklist for CR scope changes.",
            "Capture stakeholder review comments in Jira.",
        ]
    return title, stories, tasks


def create_jira_items_from_cr(cr_markdown: str, jira_cfg: JiraConfig) -> list[dict[str, str]]:
    client = JiraClient(
        base_url=jira_cfg.base_url,
        email=jira_cfg.email,
        api_token=jira_cfg.api_token,
        verify_ssl=jira_cfg.verify_ssl,
    )
    title, stories, tasks = derive_jira_items(cr_markdown)
    labels = ["cr-agent", "change-request"]

    epic: JiraIssue = client.create_issue(
        project_key=jira_cfg.project_key,
        issue_type=jira_cfg.epic_issue_type,
        summary=f"CR Epic: {title}",
        description=cr_markdown[:30000],
        labels=labels,
    )
    results: list[dict[str, str]] = [
        {"type": "Epic", "key": epic.key, "url": epic.url, "summary": f"CR Epic: {title}"}
    ]

    for i, story in enumerate(stories, start=1):
        try:
            story_issue = client.create_issue(
                project_key=jira_cfg.project_key,
                issue_type=jira_cfg.story_issue_type,
                summary=f"CR Story {i}: {story[:180]}",
                description=f"Derived from CR:\n\n{story}\n\nLinked Epic: {epic.key}",
                labels=labels,
                extra_fields={jira_cfg.epic_link_field: epic.key},
            )
        except requests.HTTPError as e:
            body = (e.response.text if e.response is not None else "").lower()
            # Some Jira projects (team-managed) do not expose Epic Link custom fields on create.
            if "cannot be set" in body or "unknown" in body or jira_cfg.epic_link_field.lower() in body:
                story_issue = client.create_issue(
                    project_key=jira_cfg.project_key,
                    issue_type=jira_cfg.story_issue_type,
                    summary=f"CR Story {i}: {story[:180]}",
                    description=f"Derived from CR:\n\n{story}\n\nLinked Epic: {epic.key}",
                    labels=labels,
                    extra_fields={"parent": {"key": epic.key}},
                )
            else:
                raise
        results.append(
            {"type": "Story", "key": story_issue.key, "url": story_issue.url, "summary": story}
        )
        story_tasks = tasks[(i - 1) * 2 : i * 2] or tasks[:2]
        for task in story_tasks:
            task_issue = client.create_issue(
                project_key=jira_cfg.project_key,
                issue_type=jira_cfg.task_issue_type,
                summary=f"Task: {task[:210]}",
                description=f"Task derived from Story {story_issue.key}:\n\n{task}",
                labels=labels,
            )
            results.append(
                {
                    "type": "Task",
                    "key": task_issue.key,
                    "url": task_issue.url,
                    "summary": task,
                }
            )
    return results


def run_cr_agent(
    *,
    meeting_path: str | Path,
    scope_path: str | Path,
    output_dir: str | Path = "outputs",
    create_jira: bool = True,
    use_llm: bool = True,
    llm_client: OpenAIClientPort | None = None,
) -> CRArtifacts:
    meeting_text = load_meeting_recording(meeting_path)
    scope_text = load_sow_or_scope(scope_path)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cr_file = out_dir / "cr_document.md"

    jira_cfg = get_jira_config() if create_jira else None
    if create_jira and jira_cfg is None:
        raise ValueError(
            "Jira is not configured. Set JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN, JIRA_PROJECT_KEY."
        )

    llm_used = False
    cr_markdown = ""
    jira_items: list[dict[str, str]] = []

    router = llm_client if llm_client is not None else get_openai_router_client()
    llm_cfg = get_llm_router_config()

    if use_llm and router is not None and llm_cfg is not None:
        try:
            cr_markdown, jira_items = run_llm_cr_agent(
                meeting_text=meeting_text,
                scope_text=scope_text,
                output_dir=out_dir,
                create_jira=bool(create_jira and jira_cfg),
                client=router,
                model=llm_cfg.model,
                max_steps=llm_cfg.max_agent_steps,
                jira_cfg=jira_cfg if create_jira else None,
            )
            llm_used = True
            if create_jira and jira_cfg:
                has_epic = any(item.get("type") == "Epic" for item in jira_items)
                if not has_epic:
                    jira_items = create_jira_items_from_cr(cr_markdown, jira_cfg)
        except Exception:
            llm_used = False
            cr_markdown = ""
            jira_items = []

    if not llm_used:
        cr_markdown = build_cr_document(meeting_text, scope_text)
        cr_file.write_text(cr_markdown, encoding="utf-8")
        if create_jira and jira_cfg is not None:
            jira_items = create_jira_items_from_cr(cr_markdown, jira_cfg)

    jira_file: Path | None = None
    if create_jira and jira_cfg is not None and jira_items:
        jira_file = out_dir / "jira_items.json"
        jira_file.write_text(json.dumps(jira_items, indent=2), encoding="utf-8")

    return CRArtifacts(
        cr_markdown=cr_markdown,
        cr_file=cr_file,
        jira_output_file=jira_file,
        jira_items=jira_items,
        llm_used=llm_used,
    )

