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


@dataclass(frozen=True)
class LLMRouterConfig:
    base_url: str
    api_key: str
    model: str
    max_agent_steps: int


def get_llm_router_config() -> LLMRouterConfig | None:
    """Hugging Face OpenAI-compatible router (chat completions)."""
    key = _env("HF_TOKEN") or _env("HUGGINGFACE_API_KEY")
    if not key:
        return None
    base = (_env("LLM_BASE_URL") or "https://router.huggingface.co/v1").rstrip("/")
    model = _env("LLM_MODEL") or "google/gemma-4-31B-it:novita"
    try:
        max_steps = int(_env("LLM_MAX_AGENT_STEPS") or "12")
    except ValueError:
        max_steps = 12
    max_steps = max(4, min(max_steps, 24))
    return LLMRouterConfig(base_url=base, api_key=key, model=model, max_agent_steps=max_steps)


@dataclass(frozen=True)
class SmartsheetConfig:
    access_token: str
    sheet_id: str
    api_base: str
    verify_ssl: bool
    phase_column_title: str
    start_column_title: str
    end_column_title: str


def get_smartsheet_config() -> SmartsheetConfig | None:
    token = _env("SMARTSHEET_ACCESS_TOKEN")
    sheet_id = _env("SMARTSHEET_SHEET_ID")
    if not token or not sheet_id:
        return None
    base = (_env("SMARTSHEET_API_BASE") or "https://api.smartsheet.com/2.0").rstrip("/")
    verify_raw = (_env("SMARTSHEET_VERIFY_SSL") or "true").strip().lower()
    verify_ssl = verify_raw not in {"0", "false", "no", "off"}
    return SmartsheetConfig(
        access_token=token,
        sheet_id=sheet_id.strip(),
        api_base=base,
        verify_ssl=verify_ssl,
        phase_column_title=(_env("SMARTSHEET_PHASE_COLUMN_TITLE") or "Phase").strip(),
        start_column_title=(_env("SMARTSHEET_START_COLUMN_TITLE") or "Start").strip(),
        end_column_title=(_env("SMARTSHEET_END_COLUMN_TITLE") or "End").strip(),
    )


def get_api_cors_origins() -> list[str]:
    raw = _env("CORS_ALLOW_ORIGINS") or "*"
    return [o.strip() for o in raw.split(",") if o.strip()] or ["*"]
