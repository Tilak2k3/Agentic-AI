"""Shared helpers for API routers."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import HTTPException

from typing import Union

from agentic_ai.api.schemas import CRRunBody, PlanGenerateBody, RaidGenerateBody

_MeetingScopeBody = Union[PlanGenerateBody, CRRunBody, RaidGenerateBody]


def materialize_meeting_scope_paths(body: _MeetingScopeBody, base_out: Path) -> tuple[Path, Path, Path]:
    """Return (meeting_path, scope_path, run_dir). Creates temp files when inline text is used."""
    run_dir = base_out / uuid.uuid4().hex[:10]
    run_dir.mkdir(parents=True, exist_ok=True)
    if body.meeting_path and body.scope_path:
        mp, sp = Path(body.meeting_path), Path(body.scope_path)
        if not mp.is_file() or not sp.is_file():
            raise HTTPException(status_code=400, detail="meeting_path or scope_path is not a readable file")
        return mp, sp, run_dir
    if body.meeting_text is not None and body.scope_text is not None:
        mp = run_dir / "_meeting.txt"
        sp = run_dir / "_scope.txt"
        mp.write_text(body.meeting_text, encoding="utf-8")
        sp.write_text(body.scope_text, encoding="utf-8")
        return mp, sp, run_dir
    raise HTTPException(status_code=422, detail="Provide meeting_path+scope_path or meeting_text+scope_text")
