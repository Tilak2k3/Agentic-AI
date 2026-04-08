"""Minimal Jira Cloud REST client for creating CR delivery items."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests
from requests.auth import HTTPBasicAuth


@dataclass(frozen=True)
class JiraIssue:
    key: str
    id: str
    url: str


class JiraClient:
    def __init__(
        self,
        *,
        base_url: str,
        email: str,
        api_token: str,
        verify_ssl: bool = True,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_base = f"{self.base_url}/rest/api/3"
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(email, api_token)
        self.session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )
        self.verify_ssl = verify_ssl

    def create_issue(
        self,
        *,
        project_key: str,
        issue_type: str,
        summary: str,
        description: str,
        labels: list[str] | None = None,
        extra_fields: dict[str, Any] | None = None,
    ) -> JiraIssue:
        fields: dict[str, Any] = {
            "project": {"key": project_key},
            "issuetype": {"name": issue_type},
            "summary": summary[:250],
            "description": self._adf_paragraph(description),
        }
        if labels:
            fields["labels"] = labels
        if extra_fields:
            fields.update(extra_fields)
        payload = {"fields": fields}
        r = self.session.post(
            f"{self.api_base}/issue",
            json=payload,
            timeout=60,
            verify=self.verify_ssl,
        )
        r.raise_for_status()
        data = r.json()
        key = data["key"]
        issue_id = str(data["id"])
        return JiraIssue(key=key, id=issue_id, url=f"{self.base_url}/browse/{key}")

    @staticmethod
    def _adf_paragraph(text: str) -> dict[str, Any]:
        """Wrap plain text into Jira Atlassian Document Format."""
        lines = [ln for ln in text.splitlines() if ln.strip()]
        if not lines:
            lines = [" "]
        content = [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": ln[:2000]}],
            }
            for ln in lines[:40]
        ]
        return {"type": "doc", "version": 1, "content": content}

