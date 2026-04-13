"""Input extraction endpoints (meeting text/audio, documents)."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from agentic_ai.api.schemas import InputExtractResponse
from agentic_ai.inputs.documents import read_text_document
from agentic_ai.inputs.meeting_recordings import extract_meeting_text

router = APIRouter(prefix="/inputs", tags=["inputs"])


@router.post("/extract", response_model=InputExtractResponse)
async def extract_input(
    kind: Literal["meeting", "document"] = Form(
        ...,
        description="meeting = text/audio via meeting pipeline; document = SOW-style file",
    ),
    file: UploadFile = File(...),
) -> InputExtractResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="filename is required")
    suffix = Path(file.filename).suffix or ".txt"
    tmp_path: Path | None = None
    try:
        with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = Path(tmp.name)
        if kind == "meeting":
            text = extract_meeting_text(tmp_path)
        else:
            text = read_text_document(tmp_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    finally:
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    return InputExtractResponse(kind=kind, filename=file.filename, text=text)
