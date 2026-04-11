"""Plan agent HTTP endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from agentic_ai.api.deps import materialize_meeting_scope_paths
from agentic_ai.api.schemas import PlanGenerateBody, PlanGenerateResponse
from agentic_ai.plan_agent import run_plan_agent

router = APIRouter(prefix="/plan", tags=["plan"])


@router.post("/generate", response_model=PlanGenerateResponse)
def generate_plan(body: PlanGenerateBody) -> PlanGenerateResponse:
    base = Path(body.output_dir)
    try:
        meeting_p, scope_p, run_dir = materialize_meeting_scope_paths(body, base)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    try:
        art = run_plan_agent(
            meeting_path=meeting_p,
            scope_path=scope_p,
            output_dir=run_dir,
            sync_smartsheet=body.sync_smartsheet,
            use_llm=body.use_llm,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return PlanGenerateResponse(
        plan_markdown=art.plan_markdown,
        plan_file=str(art.plan_file.resolve()),
        line_items_count=len(art.line_items),
        smartsheet_rows_created=len(art.smartsheet_results),
        llm_used=art.llm_used,
    )
