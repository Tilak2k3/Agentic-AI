"""RAID agent HTTP endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from agentic_ai.api.deps import materialize_meeting_scope_paths
from agentic_ai.api.schemas import RaidGenerateBody, RaidGenerateResponse
from agentic_ai.raid_agent import run_raid_agent

router = APIRouter(prefix="/raid", tags=["raid"])


@router.post("/generate", response_model=RaidGenerateResponse)
def generate_raid(body: RaidGenerateBody) -> RaidGenerateResponse:
    base = Path(body.output_dir)
    try:
        meeting_p, scope_p, run_dir = materialize_meeting_scope_paths(body, base)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    try:
        art = run_raid_agent(
            meeting_path=meeting_p,
            scope_path=scope_p,
            output_dir=run_dir,
            use_llm=body.use_llm,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    r = art.raid
    return RaidGenerateResponse(
        title=str(r.get("title") or "RAID Log"),
        excel_file=str(art.excel_file.resolve()),
        summary_file=str(art.summary_file.resolve()),
        risk_count=len(r.get("risks") or []),
        assumption_count=len(r.get("assumptions") or []),
        issue_count=len(r.get("issues") or []),
        dependency_count=len(r.get("dependencies") or []),
        llm_used=art.llm_used,
    )
