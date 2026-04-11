"""Integration configuration status (no secrets)."""

from __future__ import annotations

from fastapi import APIRouter

from agentic_ai.api.schemas import IntegrationStatusResponse
from agentic_ai.config import (
    get_azure_graph_config,
    get_imap_config,
    get_jira_config,
    get_llm_router_config,
    get_sharepoint_config,
    get_smartsheet_config,
)

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("/status", response_model=IntegrationStatusResponse)
def integration_status() -> IntegrationStatusResponse:
    return IntegrationStatusResponse(
        jira_configured=get_jira_config() is not None,
        smartsheet_configured=get_smartsheet_config() is not None,
        llm_router_configured=get_llm_router_config() is not None,
        imap_configured=get_imap_config() is not None,
        azure_graph_configured=get_azure_graph_config() is not None,
        sharepoint_configured=get_sharepoint_config() is not None,
    )
