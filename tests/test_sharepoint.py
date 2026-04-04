"""SharePoint helpers: live tests only when Azure + SharePoint env is set."""

from __future__ import annotations

import os

import pytest

from agentic_ai.config import get_azure_graph_config, get_sharepoint_config
from agentic_ai.inputs.sharepoint import list_drive_folder_children


@pytest.mark.integration
def test_list_sharepoint_folder_when_configured() -> None:
    if get_azure_graph_config() is None or get_sharepoint_config() is None:
        pytest.skip(
            "Set AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, "
            "SHAREPOINT_SITE_ID, SHAREPOINT_DRIVE_ID."
        )
    folder = os.environ.get("TEST_SHAREPOINT_FOLDER_PATH", "").strip()
    items = list_drive_folder_children(folder)
    assert isinstance(items, list)
