"""Pydantic request/response models for the HTTP API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


class PlanGenerateBody(BaseModel):
    meeting_path: str | None = None
    scope_path: str | None = None
    meeting_text: str | None = None
    scope_text: str | None = None
    output_dir: str = Field(default="outputs/api-plan", description="Base directory for artifacts")
    sync_smartsheet: bool = False
    use_llm: bool = True

    @model_validator(mode="after")
    def _paths_or_texts(self) -> PlanGenerateBody:
        has_paths = bool(self.meeting_path and self.scope_path)
        has_texts = bool(self.meeting_text and self.scope_text)
        if not has_paths and not has_texts:
            raise ValueError("Provide meeting_path+scope_path or meeting_text+scope_text")
        return self


class PlanGenerateResponse(BaseModel):
    plan_markdown: str
    plan_file: str
    line_items_count: int
    smartsheet_rows_created: int
    llm_used: bool


class CRRunBody(BaseModel):
    meeting_path: str | None = None
    scope_path: str | None = None
    meeting_text: str | None = None
    scope_text: str | None = None
    output_dir: str = "outputs/api-cr"
    create_jira: bool = True
    use_llm: bool = True

    @model_validator(mode="after")
    def _paths_or_texts(self) -> CRRunBody:
        has_paths = bool(self.meeting_path and self.scope_path)
        has_texts = bool(self.meeting_text and self.scope_text)
        if not has_paths and not has_texts:
            raise ValueError("Provide meeting_path+scope_path or meeting_text+scope_text")
        return self


class CRRunResponse(BaseModel):
    cr_markdown: str
    cr_file: str
    cr_docx_file: str
    jira_file: str | None = None
    jira_items: list[dict[str, Any]] = Field(default_factory=list)
    llm_used: bool


class IntegrationStatusResponse(BaseModel):
    jira_configured: bool
    smartsheet_configured: bool
    llm_router_configured: bool
    imap_configured: bool
    azure_graph_configured: bool
    sharepoint_configured: bool


class RaidGenerateBody(BaseModel):
    meeting_path: str | None = None
    scope_path: str | None = None
    meeting_text: str | None = None
    scope_text: str | None = None
    output_dir: str = "outputs/api-raid"
    use_llm: bool = True

    @model_validator(mode="after")
    def _paths_or_texts(self) -> RaidGenerateBody:
        has_paths = bool(self.meeting_path and self.scope_path)
        has_texts = bool(self.meeting_text and self.scope_text)
        if not has_paths and not has_texts:
            raise ValueError("Provide meeting_path+scope_path or meeting_text+scope_text")
        return self


class RaidGenerateResponse(BaseModel):
    title: str
    excel_file: str
    summary_file: str
    risk_count: int
    assumption_count: int
    issue_count: int
    dependency_count: int
    llm_used: bool


class InputExtractResponse(BaseModel):
    kind: str
    filename: str | None
    text: str


class PipelineJobCreateResponse(BaseModel):
    job_id: str
