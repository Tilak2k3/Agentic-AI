"""Smartsheet REST API v2 — append plan line items as sheet rows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

from agentic_ai.config import SmartsheetConfig


@dataclass(frozen=True)
class PlanLineItem:
    """One schedulable line for Smartsheet."""

    name: str
    phase: str = ""
    start: str = ""
    end: str = ""
    notes: str = ""


class SmartsheetClient:
    def __init__(self, cfg: SmartsheetConfig) -> None:
        self.cfg = cfg
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {cfg.access_token}",
                "Content-Type": "application/json",
            }
        )

    def get_sheet(self, sheet_id: str | None = None) -> dict[str, Any]:
        sid = sheet_id or self.cfg.sheet_id
        url = f"{self.cfg.api_base}/sheets/{sid}"
        r = self.session.get(url, params={"include": "columns"}, timeout=60, verify=self.cfg.verify_ssl)
        r.raise_for_status()
        return r.json()

    def _resolve_column_ids(self, sheet: dict[str, Any]) -> dict[str, int]:
        """Map logical keys (primary, phase, start, end) to Smartsheet column ids."""
        cols = sheet.get("columns") or []
        by_title: dict[str, int] = {}
        primary_id: int | None = None
        for c in cols:
            cid = int(c["id"])
            title = str(c.get("title") or "").strip()
            by_title[title.lower()] = cid
            if c.get("primary"):
                primary_id = cid
        if primary_id is None and cols:
            primary_id = int(cols[0]["id"])
        if primary_id is None:
            raise ValueError("Sheet has no columns; cannot append rows.")

        out: dict[str, int] = {"primary": primary_id}
        pt = self.cfg.phase_column_title.lower()
        st = self.cfg.start_column_title.lower()
        et = self.cfg.end_column_title.lower()
        if pt in by_title:
            out["phase"] = by_title[pt]
        if st in by_title:
            out["start"] = by_title[st]
        if et in by_title:
            out["end"] = by_title[et]
        return out

    def append_plan_rows(self, items: list[PlanLineItem], sheet_id: str | None = None) -> list[dict[str, Any]]:
        """Append rows to the bottom of the sheet. Returns Smartsheet result rows metadata."""
        if not items:
            return []
        sheet = self.get_sheet(sheet_id)
        cmap = self._resolve_column_ids(sheet)
        sid = sheet_id or self.cfg.sheet_id

        rows_payload: list[dict[str, Any]] = []
        for it in items:
            cells: list[dict[str, Any]] = [{"columnId": cmap["primary"], "value": it.name[:4000]}]
            if "phase" in cmap and it.phase:
                cells.append({"columnId": cmap["phase"], "value": it.phase[:4000]})
            if "start" in cmap and it.start:
                cells.append({"columnId": cmap["start"], "value": it.start[:4000]})
            if "end" in cmap and it.end:
                cells.append({"columnId": cmap["end"], "value": it.end[:4000]})
            rows_payload.append({"cells": cells})

        body = {"toBottom": True, "rows": rows_payload}
        url = f"{self.cfg.api_base}/sheets/{sid}/rows"
        r = self.session.post(url, json=body, timeout=120, verify=self.cfg.verify_ssl)
        r.raise_for_status()
        data = r.json()
        result = data.get("result") or []
        return result if isinstance(result, list) else [result]
