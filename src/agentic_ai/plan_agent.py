"""Plan agent: project plan from meeting + scope; optional Smartsheet line items."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from agentic_ai.config import get_llm_router_config, get_smartsheet_config
from agentic_ai.inputs.collector import load_meeting_recording, load_sow_or_scope
from agentic_ai.llm_client import OpenAIClientPort, get_openai_router_client
from agentic_ai.smartsheet_client import PlanLineItem, SmartsheetClient


@dataclass(frozen=True)
class PlanArtifacts:
    plan_markdown: str
    plan_file: Path
    line_items: list[PlanLineItem]
    smartsheet_results: list[dict[str, object]]
    llm_used: bool = False


def _normalize_lines(text: str) -> list[str]:
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def _extract_title(scope_text: str, meeting_text: str) -> str:
    for src in (scope_text, meeting_text):
        for line in _normalize_lines(src):
            if len(line) > 12:
                return re.sub(r"\s+", " ", line)[:90]
    return "Project Plan"


def build_project_plan(meeting_text: str, scope_text: str) -> str:
    """Deterministic project plan markdown from inputs."""
    title = _extract_title(scope_text, meeting_text)
    scope_bullets = [ln.lstrip("-* ").strip() for ln in _normalize_lines(scope_text)[:8]]
    meet_bullets = [ln.lstrip("-* ").strip() for ln in _normalize_lines(meeting_text)[:8]]

    phases = ["Discovery", "Design", "Build", "Test", "Rollout"]
    tasks = [
        ("Discovery", "Confirm scope, stakeholders, and success criteria", "Week 1", "Week 2"),
        ("Design", "Produce solution design and delivery backlog", "Week 2", "Week 4"),
        ("Build", "Implement agreed scope with incremental demos", "Week 4", "Week 10"),
        ("Test", "QA, UAT, and defect burn-down", "Week 10", "Week 12"),
        ("Rollout", "Production deployment and handover", "Week 12", "Week 13"),
    ]
    if scope_bullets:
        tasks = [
            ("Discovery", scope_bullets[0][:120], "Week 1", "Week 2"),
            *tasks[1:],
        ]

    scope_lines = [f"- {b}" for b in scope_bullets] if scope_bullets else ["- (No scope bullets extracted.)"]
    meet_lines = [f"- {b}" for b in meet_bullets] if meet_bullets else ["- (No meeting bullets extracted.)"]

    lines = [
        f"# Project Plan: {title}",
        "",
        "## 1. Objectives",
        "- Deliver scope aligned with the SOW and meeting commitments.",
        "- Maintain traceable milestones and execution line items.",
        "",
        "## 2. Scope summary (from document)",
        *scope_lines,
        "",
        "## 3. Meeting-driven priorities",
        *meet_lines,
        "",
        "## 4. Phases",
        *[f"- **{p}**" for p in phases],
        "",
        "## 5. Work breakdown (line items)",
        "| Phase | Task | Start | End |",
        "|-------|------|-------|-----|",
        *[f"| {p} | {t} | {s} | {e} |" for p, t, s, e in tasks],
        "",
        "## 6. Risks & dependencies",
        "- Dependencies on third-party integrations or approvals.",
        "- Resource availability across phases.",
        "",
        "## 7. Communication",
        "- Weekly status; escalate blockers within 24h.",
    ]
    return "\n".join(lines).strip() + "\n"


def derive_plan_line_items(plan_markdown: str) -> list[PlanLineItem]:
    """Parse the markdown table under Work breakdown into `PlanLineItem` rows."""
    items: list[PlanLineItem] = []
    in_table = False
    for line in plan_markdown.splitlines():
        if "| Phase |" in line and "Task" in line:
            in_table = True
            continue
        if in_table:
            if line.strip().startswith("|--") or line.strip().startswith("| ---") or line.strip().startswith("|---"):
                continue
            if not line.strip().startswith("|"):
                break
            parts = [p.strip() for p in line.strip().strip("|").split("|")]
            if len(parts) >= 4 and parts[0].lower() != "phase":
                phase, task, start, end = parts[0], parts[1], parts[2], parts[3]
                phase = re.sub(r"^\*+|\*+$", "", phase).strip()
                task = re.sub(r"^\*+|\*+$", "", task).strip()
                if task and task != "------":
                    items.append(PlanLineItem(name=task, phase=phase, start=start, end=end))
    if not items:
        for line in _normalize_lines(plan_markdown):
            if line.startswith("- ") and len(line) > 4:
                items.append(PlanLineItem(name=line[2:].strip()[:400], phase="General"))
            if len(items) >= 8:
                break
    return items[:50]


def _try_llm_plan(client: OpenAIClientPort, model: str, meeting_text: str, scope_text: str) -> str | None:
    resp = client.chat.completions.create(
        model=model,
        temperature=0.25,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a project planning assistant. Output ONLY valid Markdown for a project plan. "
                    "Include sections: Objectives, Scope summary, Meeting priorities, Phases, "
                    "and a markdown table named exactly '## 5. Work breakdown (line items)' with columns "
                    "| Phase | Task | Start | End | and at least 4 data rows. No code fences. "
                    "Align tasks and priorities with the supplied meeting and scope text; flag gaps explicitly "
                    "instead of fabricating requirements."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Meeting notes / transcript:\n"
                    f"{meeting_text[:25000]}\n\n"
                    "Scope / SOW:\n"
                    f"{scope_text[:25000]}"
                ),
            },
        ],
    )
    raw = (resp.choices[0].message.content or "").strip()
    return raw if raw else None


def run_plan_agent(
    *,
    meeting_path: str | Path | None = None,
    scope_path: str | Path | None = None,
    meeting_text: str | None = None,
    scope_text: str | None = None,
    output_dir: str | Path = "outputs",
    sync_smartsheet: bool = False,
    use_llm: bool = True,
    llm_client: OpenAIClientPort | None = None,
) -> PlanArtifacts:
    if meeting_path is not None and scope_path is not None:
        m = load_meeting_recording(meeting_path)
        s = load_sow_or_scope(scope_path)
    elif meeting_text is not None and scope_text is not None:
        m, s = meeting_text, scope_text
    else:
        raise ValueError("Provide (meeting_path, scope_path) or (meeting_text, scope_text).")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    plan_file = out_dir / "project_plan.md"

    llm_used = False
    plan_md = ""
    router = llm_client if llm_client is not None else get_openai_router_client()
    llm_cfg = get_llm_router_config()
    if use_llm:
        if router is None or llm_cfg is None:
            raise ValueError(
                "Plan agent requires LLM credentials: set HF_TOKEN or HUGGINGFACE_API_KEY "
                "and LLM_BASE_URL / LLM_MODEL (see .env.example)."
            )
        plan_try = _try_llm_plan(router, llm_cfg.model, m, s)
        if not plan_try or not str(plan_try).strip():
            raise RuntimeError("LLM returned an empty project plan; check model availability and quotas.")
        plan_md = str(plan_try).strip()
        llm_used = True
    else:
        plan_md = build_project_plan(m, s)

    plan_file.write_text(plan_md, encoding="utf-8")
    line_items = derive_plan_line_items(plan_md)

    smartsheet_results: list[dict[str, object]] = []
    if sync_smartsheet:
        sc = get_smartsheet_config()
        if sc is None:
            raise ValueError(
                "Smartsheet sync requested but not configured. "
                "Set SMARTSHEET_ACCESS_TOKEN and SMARTSHEET_SHEET_ID (and optional column title env vars)."
            )
        client = SmartsheetClient(sc)
        smartsheet_results = client.append_plan_rows(line_items)

    meta_file = out_dir / "plan_smartsheet_meta.json"
    if smartsheet_results:
        meta_file.write_text(json.dumps(smartsheet_results, indent=2, default=str), encoding="utf-8")

    return PlanArtifacts(
        plan_markdown=plan_md,
        plan_file=plan_file,
        line_items=line_items,
        smartsheet_results=smartsheet_results,
        llm_used=llm_used,
    )
