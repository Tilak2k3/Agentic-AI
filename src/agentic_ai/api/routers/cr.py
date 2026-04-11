"""CR agent HTTP endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from agentic_ai.api.deps import materialize_meeting_scope_paths
from agentic_ai.api.schemas import CRRunBody, CRRunResponse
from agentic_ai.cr_agent import run_cr_agent

router = APIRouter(prefix="/cr", tags=["cr"])


@router.post("/run", response_model=CRRunResponse)
def run_cr(body: CRRunBody) -> CRRunResponse:
    base = Path(body.output_dir)
    try:
        meeting_p, scope_p, run_dir = materialize_meeting_scope_paths(body, base)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    try:
        art = run_cr_agent(
            meeting_path=meeting_p,
            scope_path=scope_p,
            output_dir=run_dir,
            create_jira=body.create_jira,
            use_llm=body.use_llm,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return CRRunResponse(
        cr_markdown=art.cr_markdown,
        cr_file=str(art.cr_file.resolve()),
        jira_file=str(art.jira_output_file.resolve()) if art.jira_output_file else None,
        jira_items=art.jira_items,
        llm_used=art.llm_used,
    )
