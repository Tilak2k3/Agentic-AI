"""In-memory pipeline job store and conditional CR / Plan / RAID orchestration."""

from __future__ import annotations

import shutil
import threading
import uuid
from pathlib import Path
from typing import Any

from agentic_ai.config import get_jira_config, get_smartsheet_config
from agentic_ai.cr_agent import run_cr_agent
from agentic_ai.inputs.documents import read_text_document
from agentic_ai.inputs.meeting_recordings import AUDIO_EXTENSIONS, extract_meeting_text
from agentic_ai.plan_agent import run_plan_agent
from agentic_ai.raid_agent import run_raid_agent

_JOBS_LOCK = threading.Lock()
_JOBS: dict[str, dict[str, Any]] = {}


def get_job(job_id: str) -> dict[str, Any] | None:
    with _JOBS_LOCK:
        j = _JOBS.get(job_id)
        return dict(j) if j else None


def _update_job(job_id: str, **kwargs: Any) -> None:
    with _JOBS_LOCK:
        if job_id in _JOBS:
            cur = dict(_JOBS[job_id])
            cur.update(kwargs)
            _JOBS[job_id] = cur


def _merge_artifacts(job_id: str, **new_art: Any) -> None:
    with _JOBS_LOCK:
        if job_id not in _JOBS:
            return
        j = dict(_JOBS[job_id])
        art = dict(j.get("artifacts") or {})
        art.update(new_art)
        j["artifacts"] = art
        _JOBS[job_id] = j


def init_job(job_id: str) -> None:
    with _JOBS_LOCK:
        _JOBS[job_id] = {
            "job_id": job_id,
            "stage": "queued",
            "message": "Job queued",
            "done": False,
            "error": None,
            "artifacts": {},
            "ran_agents": [],
        }


def _extract_meeting_like(path: Path) -> str:
    suf = path.suffix.lower()
    if suf in AUDIO_EXTENSIONS:
        return extract_meeting_text(path)
    return path.read_text(encoding="utf-8", errors="replace")


def _extract_scope_like(path: Path) -> str:
    try:
        return read_text_document(path)
    except ValueError:
        return path.read_text(encoding="utf-8", errors="replace")


def _run_pipeline(
    job_id: str,
    run_dir: Path,
    meeting_raw: Path | None,
    scope_raw: Path | None,
    kickoff_raw: Path | None,
    *,
    use_llm: bool,
    create_jira: bool,
    sync_smartsheet: bool,
) -> None:
    ran: list[str] = []
    try:
        _update_job(job_id, stage="preparing", message="Reading uploaded files…")

        has_meeting_file = meeting_raw is not None and meeting_raw.is_file()
        has_scope_file = scope_raw is not None and scope_raw.is_file()
        has_kickoff = kickoff_raw is not None and kickoff_raw.is_file()

        if has_meeting_file:
            meeting_body = _extract_meeting_like(meeting_raw)  # type: ignore[arg-type]
        elif has_kickoff:
            meeting_body = _extract_scope_like(kickoff_raw)  # type: ignore[arg-type]
        else:
            meeting_body = (
                "(No meeting recording, transcript, or kick-off notes were provided for this run.)\n"
            )

        if has_meeting_file and has_kickoff:
            kickoff_body = _extract_scope_like(kickoff_raw)  # type: ignore[arg-type]
            if kickoff_body.strip():
                meeting_body = (
                    meeting_body.rstrip()
                    + "\n\n## Kick-off meeting notes\n\n"
                    + kickoff_body.strip()
                )

        if has_scope_file:
            scope_body = _extract_scope_like(scope_raw)  # type: ignore[arg-type]
        else:
            scope_body = "(No SOW or scope document was provided for this run.)\n"

        meeting_agent_path = run_dir / "meeting_for_agents.txt"
        meeting_agent_path.write_text(meeting_body, encoding="utf-8")

        if has_scope_file and scope_raw is not None:
            scope_agent_path = run_dir / ("scope_for_agents" + scope_raw.suffix)
            shutil.copy2(scope_raw, scope_agent_path)
        else:
            scope_agent_path = run_dir / "scope_for_agents_placeholder.txt"
            scope_agent_path.write_text(scope_body, encoding="utf-8")

        cr_dir = run_dir / "cr"
        plan_dir = run_dir / "plan"
        raid_dir = run_dir / "raid"

        # CR and Plan need a scope/SOW baseline; meeting-only runs produce RAID only.
        run_cr = has_scope_file
        run_plan = has_scope_file

        if run_cr:
            _update_job(
                job_id,
                stage="cr",
                message="Running CR agent…",
                ran_agents=ran,
            )
            cr_art = run_cr_agent(
                meeting_path=meeting_agent_path,
                scope_path=scope_agent_path,
                output_dir=cr_dir,
                create_jira=create_jira and (get_jira_config() is not None),
                use_llm=use_llm,
            )
            ran.append("cr")
            jira_urls = [it["url"] for it in cr_art.jira_items if it.get("url")]
            _update_job(job_id, stage="cr_done", message="CR agent finished.", ran_agents=list(ran))
            _merge_artifacts(
                job_id,
                cr_markdown=cr_art.cr_markdown,
                cr_markdown_file=str(cr_art.cr_file.resolve()),
                cr_docx=str(cr_art.cr_docx_file.resolve()),
                cr_file=str(cr_art.cr_docx_file.resolve()),
                jira_items=cr_art.jira_items,
                jira_urls=jira_urls,
                jira_primary_url=jira_urls[0] if jira_urls else None,
            )
        else:
            _update_job(job_id, stage="cr_skipped", message="Skipping CR (scope document required).", ran_agents=list(ran))

        if run_plan:
            _update_job(job_id, stage="plan", message="Running Plan agent…", ran_agents=list(ran))
            plan_art = run_plan_agent(
                meeting_path=meeting_agent_path,
                scope_path=scope_agent_path,
                output_dir=plan_dir,
                sync_smartsheet=sync_smartsheet and (get_smartsheet_config() is not None),
                use_llm=use_llm,
            )
            ran.append("plan")
            ss_cfg = get_smartsheet_config()
            smartsheet_url = (
                f"https://app.smartsheet.com/sheets/{ss_cfg.sheet_id}" if ss_cfg and sync_smartsheet else None
            )
            _update_job(job_id, stage="plan_done", message="Plan agent finished.", ran_agents=list(ran))
            _merge_artifacts(
                job_id,
                plan_markdown=plan_art.plan_markdown,
                plan_file=str(plan_art.plan_file.resolve()),
                line_items_count=len(plan_art.line_items),
                smartsheet_rows=len(plan_art.smartsheet_results),
                smartsheet_url=smartsheet_url,
            )
        else:
            _update_job(
                job_id,
                stage="plan_skipped",
                message="Skipping Plan (requires scope document).",
                ran_agents=list(ran),
            )

        _update_job(job_id, stage="raid", message="Running RAID agent…", ran_agents=list(ran))
        raid_art = run_raid_agent(
            meeting_path=meeting_agent_path,
            scope_path=scope_agent_path,
            output_dir=raid_dir,
            use_llm=use_llm,
        )
        ran.append("raid")
        raid_summary_text = ""
        try:
            raid_summary_text = raid_art.summary_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
        _merge_artifacts(
            job_id,
            raid_excel=str(raid_art.excel_file.resolve()),
            raid_summary=str(raid_art.summary_file.resolve()),
            raid_title=str(raid_art.raid.get("title") or "RAID"),
            raid_markdown=raid_summary_text,
        )
        _update_job(
            job_id,
            stage="done",
            message="Pipeline finished.",
            done=True,
            ran_agents=list(ran),
        )
    except Exception as e:
        _update_job(
            job_id,
            stage="error",
            message=str(e),
            error=str(e),
            done=True,
            ran_agents=list(ran),
        )


def start_pipeline_thread(
    job_id: str,
    run_dir: Path,
    meeting_saved: Path | None,
    scope_saved: Path | None,
    kickoff_saved: Path | None,
    *,
    use_llm: bool,
    create_jira: bool,
    sync_smartsheet: bool,
) -> None:
    t = threading.Thread(
        target=_run_pipeline,
        args=(job_id, run_dir, meeting_saved, scope_saved, kickoff_saved),
        kwargs={
            "use_llm": use_llm,
            "create_jira": create_jira,
            "sync_smartsheet": sync_smartsheet,
        },
        daemon=True,
    )
    t.start()


def new_job_id() -> str:
    return uuid.uuid4().hex[:16]
