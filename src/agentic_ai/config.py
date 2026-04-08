"""Load settings from environment (optional .env for local dev)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)


def _env(name: str, default: str | None = None) -> str | None:
    v = os.environ.get(name)
    if v is None or v.strip() == "":
        return default
    return v


@dataclass(frozen=True)
class HuggingFaceASRConfig:
    api_key: str | None
    """HF token; required for Inference API / fal-ai routed ASR."""

    provider: str | None
    """``fal-ai``, ``hf-inference``, or ``None`` (HF auto router; often prefers fal-ai)."""

    model: str


def get_hf_asr_config() -> HuggingFaceASRConfig:
    key = _env("HUGGINGFACE_API_KEY") or _env("HF_TOKEN")
    backend = (_env("ASR_BACKEND") or "hf").lower().strip()
    if backend in ("fal-ai", "fal", "fal_ai"):
        provider = "fal-ai"
    elif backend in ("auto",):
        provider = None
    elif backend in ("hf-inference", "hf_inference"):
        provider = "hf-inference"
    else:
        # "hf", "huggingface", or default: use HF's own inference API (avoids auto-routing to paid fal-ai).
        provider = "hf-inference"
    model = _env("ASR_MODEL") or "openai/whisper-large-v3"
    return HuggingFaceASRConfig(api_key=key, provider=provider, model=model)


@dataclass(frozen=True)
class IMAPConfig:
    host: str
    user: str
    password: str
    folder: str


def get_imap_config() -> IMAPConfig | None:
    host, user, password = _env("IMAP_HOST"), _env("IMAP_USER"), _env("IMAP_PASSWORD")
    if not all((host, user, password)):
        return None
    return IMAPConfig(
        host=host,
        user=user,
        password=password,
        folder=_env("IMAP_FOLDER") or "INBOX",
    )


@dataclass(frozen=True)
class AzureGraphConfig:
    tenant_id: str
    client_id: str
    client_secret: str


def get_azure_graph_config() -> AzureGraphConfig | None:
    tid, cid, secret = _env("AZURE_TENANT_ID"), _env("AZURE_CLIENT_ID"), _env("AZURE_CLIENT_SECRET")
    if not all((tid, cid, secret)):
        return None
    return AzureGraphConfig(tenant_id=tid, client_id=cid, client_secret=secret)


@dataclass(frozen=True)
class SharePointConfig:
    site_id: str
    drive_id: str


def get_sharepoint_config() -> SharePointConfig | None:
    site, drive = _env("SHAREPOINT_SITE_ID"), _env("SHAREPOINT_DRIVE_ID")
    if not all((site, drive)):
        return None
    return SharePointConfig(site_id=site, drive_id=drive)


@dataclass(frozen=True)
class JiraConfig:
    base_url: str
    email: str
    api_token: str
    project_key: str
    epic_issue_type: str
    story_issue_type: str
    task_issue_type: str
    epic_link_field: str
    verify_ssl: bool


def get_jira_config() -> JiraConfig | None:
    base_url = _env("JIRA_BASE_URL")
    email = _env("JIRA_EMAIL")
    api_token = _env("JIRA_API_TOKEN")
    project_key = _env("JIRA_PROJECT_KEY")
    if not all((base_url, email, api_token, project_key)):
        return None
    verify_raw = (_env("JIRA_VERIFY_SSL") or "true").strip().lower()
    verify_ssl = verify_raw not in {"0", "false", "no", "off"}
    return JiraConfig(
        base_url=base_url.rstrip("/"),
        email=email,
        api_token=api_token,
        project_key=project_key,
        epic_issue_type=_env("JIRA_EPIC_ISSUE_TYPE") or "Epic",
        story_issue_type=_env("JIRA_STORY_ISSUE_TYPE") or "Story",
        task_issue_type=_env("JIRA_TASK_ISSUE_TYPE") or "Task",
        epic_link_field=_env("JIRA_EPIC_LINK_FIELD") or "customfield_10014",
        verify_ssl=verify_ssl,
    )
