"""Full pipeline: CR → Plan → RAID with SSE job progress."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from agentic_ai.api.pipeline_jobs import (
    get_job,
    init_job,
    new_job_id,
    start_pipeline_thread,
)
from agentic_ai.api.schemas import PipelineJobCreateResponse

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


def _form_bool(v: str | bool) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("1", "true", "yes", "on")


@router.post("/jobs", response_model=PipelineJobCreateResponse)
async def create_pipeline_job(
    meeting: UploadFile | None = File(None, description="Meeting recording (audio or text)"),
    scope: UploadFile | None = File(None, description="SOW / scope document"),
    kickoff: UploadFile | None = File(None, description="Kick-off meeting notes (optional)"),
    use_llm: str | bool = Form("true"),
    create_jira: str | bool = Form("true"),
    sync_smartsheet: str | bool = Form("false"),
) -> PipelineJobCreateResponse:
    has_m = meeting is not None and bool(meeting.filename)
    has_s = scope is not None and bool(scope.filename)
    if not has_m and not has_s:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one of: meeting recording or scope/SOW document.",
        )

    job_id = new_job_id()
    run_dir = Path("outputs") / "pipeline" / job_id
    run_dir.mkdir(parents=True, exist_ok=True)

    meeting_path: Path | None = None
    scope_path: Path | None = None
    if has_m:
        assert meeting is not None and meeting.filename
        suf_m = Path(meeting.filename).suffix or ".bin"
        meeting_path = run_dir / f"upload_meeting{suf_m}"
        meeting_path.write_bytes(await meeting.read())
    if has_s:
        assert scope is not None and scope.filename
        suf_s = Path(scope.filename).suffix or ".bin"
        scope_path = run_dir / f"upload_scope{suf_s}"
        scope_path.write_bytes(await scope.read())

    kick_path: Path | None = None
    if kickoff is not None and kickoff.filename:
        suf_k = Path(kickoff.filename).suffix or ".bin"
        kick_path = run_dir / f"upload_kickoff{suf_k}"
        kick_path.write_bytes(await kickoff.read())

    init_job(job_id)
    start_pipeline_thread(
        job_id,
        run_dir,
        meeting_path,
        scope_path,
        kick_path,
        use_llm=_form_bool(use_llm),
        create_jira=_form_bool(create_jira),
        sync_smartsheet=_form_bool(sync_smartsheet),
    )
    return PipelineJobCreateResponse(job_id=job_id)


@router.get("/jobs/{job_id}")
def get_pipeline_job(job_id: str) -> dict:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown job")
    return job


@router.get("/jobs/{job_id}/events")
async def pipeline_events(job_id: str) -> StreamingResponse:
    async def gen():
        while True:
            job = get_job(job_id)
            if job is None:
                yield f"data: {json.dumps({'error': 'unknown job', 'done': True})}\n\n"
                return
            yield f"data: {json.dumps(job, default=str)}\n\n"
            if job.get("done"):
                return
            await asyncio.sleep(0.35)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.get("/jobs/{job_id}/download/{kind}")
def download_artifact(
    job_id: str,
    kind: Literal["cr", "plan", "raid"],
) -> FileResponse:
    job = get_job(job_id)
    if not job or not job.get("done"):
        raise HTTPException(status_code=404, detail="Job not ready")
    if job.get("error"):
        raise HTTPException(status_code=400, detail="Job failed; no artifacts to download")
    art = job.get("artifacts") or {}
    key = {"cr": "cr_file", "plan": "plan_file", "raid": "raid_excel"}.get(kind)
    if not key:
        raise HTTPException(status_code=400, detail="Invalid kind")
    if kind == "cr":
        path_str = art.get("cr_docx") or art.get("cr_file")
    else:
        path_str = art.get(key)
    if not path_str:
        raise HTTPException(status_code=404, detail="Artifact missing")
    path = Path(path_str)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File not found on server")
    if kind == "raid":
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif kind == "cr":
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        media = "text/markdown; charset=utf-8"
    return FileResponse(path, filename=path.name, media_type=media)
