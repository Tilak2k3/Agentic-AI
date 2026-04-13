"""RAID agent: LLM-generated Risks, Assumptions, Issues, Dependencies → Excel workbook."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openpyxl import Workbook

from agentic_ai.config import get_llm_router_config
from agentic_ai.inputs.collector import load_meeting_recording, load_sow_or_scope
from agentic_ai.llm_client import OpenAIClientPort, get_openai_router_client

RAID_JSON_SYSTEM = """You are a delivery RAID analyst. Output ONLY a single JSON object (no markdown fences, no commentary).

Schema:
{
  "title": "short RAID log title",
  "risks": [ { "id": "R1", "title": "...", "description": "...", "severity": "High|Medium|Low", "owner": "TBD or role", "mitigation": "...", "due": "" } ],
  "assumptions": [ { "id": "A1", "title": "...", "description": "...", "severity": "Low", "owner": "...", "mitigation": "validate assumption", "due": "" } ],
  "issues": [ { "id": "I1", "title": "...", "description": "...", "severity": "Medium", "owner": "...", "mitigation": "resolution approach", "due": "" } ],
  "dependencies": [ { "id": "D1", "title": "...", "description": "...", "severity": "Medium", "owner": "...", "mitigation": "contingency", "due": "" } ]
}

Rules:
- Arrays may be empty only if truly unsupported by the inputs; otherwise include at least 2 items per array.
- severity must be one of: High, Medium, Low.
- due is ISO date string or empty string.
- If only meeting or only scope text is substantive, derive RAID items solely from that side; do not invent project facts absent from the inputs.
"""


def _extract_json_object(text: str) -> dict[str, Any]:
    t = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", t)
    if fence:
        t = fence.group(1).strip()
    try:
        out = json.loads(t)
        if isinstance(out, dict):
            return out
    except json.JSONDecodeError:
        pass
    start, end = t.find("{"), t.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("LLM output did not contain a JSON object")
    return json.loads(t[start : end + 1])


def _fallback_raid_template(meeting_text: str, scope_text: str) -> dict[str, Any]:
    """Non-LLM fallback for tests only."""
    return {
        "title": "RAID Log (template)",
        "risks": [
            {
                "id": "R1",
                "title": "Schedule slip",
                "description": "Derived from inputs; confirm timeline.",
                "severity": "Medium",
                "owner": "PM",
                "mitigation": "Re-baseline plan and escalate early.",
                "due": "",
            }
        ],
        "assumptions": [
            {
                "id": "A1",
                "title": "Stakeholder availability",
                "description": "Key reviewers available for sign-off windows.",
                "severity": "Low",
                "owner": "PM",
                "mitigation": "Book reviews in advance.",
                "due": "",
            }
        ],
        "issues": [
            {
                "id": "I1",
                "title": "Open integration dependency",
                "description": "Third-party API contract not finalized.",
                "severity": "High",
                "owner": "Tech Lead",
                "mitigation": "Timebox vendor alignment workshop.",
                "due": "",
            }
        ],
        "dependencies": [
            {
                "id": "D1",
                "title": "Infrastructure readiness",
                "description": "Cloud tenancy and access controls.",
                "severity": "Medium",
                "owner": "Ops",
                "mitigation": "Track in weekly RAID review.",
                "due": "",
            }
        ],
    }


def generate_raid_via_llm(
    client: OpenAIClientPort,
    model: str,
    meeting_text: str,
    scope_text: str,
) -> dict[str, Any]:
    resp = client.chat.completions.create(
        model=model,
        temperature=0.2,
        messages=[
            {"role": "system", "content": RAID_JSON_SYSTEM},
            {
                "role": "user",
                "content": (
                    "Meeting / transcript:\n"
                    f"{meeting_text[:25000]}\n\n"
                    "Scope / SOW:\n"
                    f"{scope_text[:25000]}"
                ),
            },
        ],
    )
    raw = (resp.choices[0].message.content or "").strip()
    if not raw:
        raise RuntimeError("LLM returned empty RAID payload")
    return _extract_json_object(raw)


def write_raid_excel(path: Path, data: dict[str, Any]) -> None:
    """Write one worksheet with all RAID rows and a Category column."""
    wb = Workbook()
    ws = wb.active
    ws.title = "RAID"
    headers = ["Category", "ID", "Title", "Description", "Severity", "Owner", "Mitigation", "Due"]
    ws.append(headers)
    sections = [
        ("Risk", "risks"),
        ("Assumption", "assumptions"),
        ("Issue", "issues"),
        ("Dependency", "dependencies"),
    ]
    for label, key in sections:
        for item in data.get(key) or []:
            if not isinstance(item, dict):
                continue
            ws.append(
                [
                    label,
                    str(item.get("id") or ""),
                    str(item.get("title") or "")[:500],
                    str(item.get("description") or "")[:4000],
                    str(item.get("severity") or "Medium"),
                    str(item.get("owner") or "TBD")[:200],
                    str(item.get("mitigation") or "")[:2000],
                    str(item.get("due") or "")[:50],
                ]
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def raid_dict_to_markdown(data: dict[str, Any]) -> str:
    lines = [f"# {data.get('title') or 'RAID Log'}", ""]
    for label, key in [
        ("## Risks", "risks"),
        ("## Assumptions", "assumptions"),
        ("## Issues", "issues"),
        ("## Dependencies", "dependencies"),
    ]:
        lines.append(label)
        for item in data.get(key) or []:
            if isinstance(item, dict):
                t = item.get("title") or item.get("id")
                lines.append(f"- **{t}**: {item.get('description', '')}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


@dataclass(frozen=True)
class RAIDArtifacts:
    raid: dict[str, Any]
    excel_file: Path
    summary_file: Path
    llm_used: bool


def run_raid_agent(
    *,
    meeting_path: str | Path | None = None,
    scope_path: str | Path | None = None,
    meeting_text: str | None = None,
    scope_text: str | None = None,
    output_dir: str | Path = "outputs",
    use_llm: bool = True,
    llm_client: OpenAIClientPort | None = None,
) -> RAIDArtifacts:
    if meeting_path is not None and scope_path is not None:
        m = load_meeting_recording(meeting_path)
        s = load_sow_or_scope(scope_path)
    elif meeting_text is not None and scope_text is not None:
        m, s = meeting_text, scope_text
    else:
        raise ValueError("Provide (meeting_path, scope_path) or (meeting_text, scope_text).")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    excel_path = out_dir / "raid_log.xlsx"
    summary_path = out_dir / "raid_summary.md"

    router = llm_client if llm_client is not None else get_openai_router_client()
    llm_cfg = get_llm_router_config()

    llm_used = False
    if use_llm:
        if router is None or llm_cfg is None:
            raise ValueError(
                "RAID agent requires LLM credentials: set HF_TOKEN or HUGGINGFACE_API_KEY "
                "and LLM_BASE_URL / LLM_MODEL."
            )
        data = generate_raid_via_llm(router, llm_cfg.model, m, s)
        llm_used = True
    else:
        data = _fallback_raid_template(m, s)

    write_raid_excel(excel_path, data)
    summary_path.write_text(raid_dict_to_markdown(data), encoding="utf-8")

    return RAIDArtifacts(raid=data, excel_file=excel_path, summary_file=summary_path, llm_used=llm_used)
