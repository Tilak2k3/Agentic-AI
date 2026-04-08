"""Tests for Jira client payload and issue creation behavior."""

from __future__ import annotations

from types import SimpleNamespace

from agentic_ai.jira_client import JiraClient


class _FakeResp:
    def __init__(self, payload: dict[str, str]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, str]:
        return self._payload


class _FakeSession:
    def __init__(self) -> None:
        self.auth = None
        self.headers = {}
        self.posts: list[SimpleNamespace] = []

    def post(self, url: str, json: dict, timeout: int, verify: bool) -> _FakeResp:
        self.posts.append(SimpleNamespace(url=url, payload=json, timeout=timeout, verify=verify))
        return _FakeResp({"id": "1001", "key": "DEMO-12"})


def test_create_issue_builds_payload(monkeypatch) -> None:
    fake_session = _FakeSession()
    monkeypatch.setattr("requests.Session", lambda: fake_session)

    client = JiraClient(
        base_url="https://example.atlassian.net",
        email="a@example.com",
        api_token="token",
        verify_ssl=True,
    )
    issue = client.create_issue(
        project_key="DEMO",
        issue_type="Task",
        summary="Create CR artifacts",
        description="desc",
        labels=["cr-agent"],
        extra_fields={"customfield_10014": "DEMO-1"},
    )

    assert issue.key == "DEMO-12"
    assert issue.url.endswith("/browse/DEMO-12")
    req = fake_session.posts[0]
    assert req.url.endswith("/rest/api/3/issue")
    assert req.payload["fields"]["project"]["key"] == "DEMO"
    assert req.payload["fields"]["issuetype"]["name"] == "Task"
    assert req.payload["fields"]["description"]["type"] == "doc"
    assert req.payload["fields"]["customfield_10014"] == "DEMO-1"
