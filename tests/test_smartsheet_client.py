"""Tests for Smartsheet client (mocked HTTP)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from agentic_ai.config import SmartsheetConfig
from agentic_ai.smartsheet_client import PlanLineItem, SmartsheetClient


def _sheet_json() -> dict:
    return {
        "id": 999,
        "name": "Plan",
        "columns": [
            {"id": 111, "title": "Task Name", "type": "TEXT_NUMBER", "primary": True},
            {"id": 222, "title": "Phase", "type": "TEXT_NUMBER", "primary": False},
            {"id": 333, "title": "Start", "type": "DATE", "primary": False},
            {"id": 444, "title": "End", "type": "DATE", "primary": False},
        ],
    }


def test_append_plan_rows_builds_post_payload() -> None:
    cfg = SmartsheetConfig(
        access_token="tok",
        sheet_id="12345",
        api_base="https://api.smartsheet.com/2.0",
        verify_ssl=True,
        phase_column_title="Phase",
        start_column_title="Start",
        end_column_title="End",
    )
    client = SmartsheetClient(cfg)

    fake_get = MagicMock()
    fake_get.return_value.json.return_value = _sheet_json()
    fake_get.return_value.raise_for_status = lambda: None

    fake_post = MagicMock()
    fake_post.return_value.json.return_value = {"result": [{"id": 1, "rowNumber": 2}]}
    fake_post.return_value.raise_for_status = lambda: None

    with patch.object(client.session, "get", fake_get), patch.object(client.session, "post", fake_post):
        out = client.append_plan_rows(
            [PlanLineItem(name="T1", phase="P1", start="2026-01-01", end="2026-01-02")],
            sheet_id="12345",
        )

    assert len(out) == 1
    args, kwargs = fake_post.call_args
    assert "/sheets/12345/rows" in args[0]
    body = kwargs["json"]
    assert body["toBottom"] is True
    assert len(body["rows"]) == 1
    cells = body["rows"][0]["cells"]
    col_ids = {c["columnId"] for c in cells}
    assert 111 in col_ids and 222 in col_ids
