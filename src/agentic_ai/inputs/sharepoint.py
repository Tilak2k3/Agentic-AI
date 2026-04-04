"""SharePoint file input via Microsoft Graph (drive items)."""

from __future__ import annotations

from typing import Any

import requests

from agentic_ai.config import get_azure_graph_config, get_sharepoint_config
from agentic_ai.inputs.documents import DOCUMENT_EXTENSIONS, read_text_document
from agentic_ai.inputs.graph_auth import get_graph_token


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def list_drive_folder_children(
    folder_path: str = "",
    *,
    site_id: str | None = None,
    drive_id: str | None = None,
    tenant_id: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
) -> list[dict[str, Any]]:
    """
    List files and folders under ``folder_path`` (use '' for drive root).

    Returns Graph driveItem dicts (id, name, folder/file, webUrl, etc.).
    """
    sp = get_sharepoint_config()
    sid = site_id or (sp.site_id if sp else None)
    did = drive_id or (sp.drive_id if sp else None)
    g = get_azure_graph_config()
    tid = tenant_id or (g.tenant_id if g else None)
    cid = client_id or (g.client_id if g else None)
    secret = client_secret or (g.client_secret if g else None)
    if not all((sid, did, tid, cid, secret)):
        raise ValueError(
            "SharePoint/Graph not fully configured. Set SHAREPOINT_SITE_ID, SHAREPOINT_DRIVE_ID, "
            "and AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET."
        )
    token = get_graph_token(tid, cid, secret)
    path_seg = "" if not folder_path.strip() else f":/{folder_path.strip().strip('/')}:"
    url = f"https://graph.microsoft.com/v1.0/sites/{sid}/drives/{did}/root{path_seg}/children"
    out: list[dict[str, Any]] = []
    while url:
        r = requests.get(url, headers=_headers(token), timeout=60)
        r.raise_for_status()
        payload = r.json()
        out.extend(payload.get("value") or [])
        url = payload.get("@odata.nextLink") or ""
    return out


def download_drive_item_content(
    item_id: str,
    *,
    site_id: str | None = None,
    drive_id: str | None = None,
    tenant_id: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
) -> bytes:
    """Download raw file bytes for a drive item id."""
    sp = get_sharepoint_config()
    sid = site_id or (sp.site_id if sp else None)
    did = drive_id or (sp.drive_id if sp else None)
    g = get_azure_graph_config()
    tid = tenant_id or (g.tenant_id if g else None)
    cid = client_id or (g.client_id if g else None)
    secret = client_secret or (g.client_secret if g else None)
    if not all((sid, did, tid, cid, secret)):
        raise ValueError("SharePoint/Graph not fully configured.")
    token = get_graph_token(tid, cid, secret)
    url = f"https://graph.microsoft.com/v1.0/sites/{sid}/drives/{did}/items/{item_id}/content"
    r = requests.get(url, headers=_headers(token), timeout=120)
    r.raise_for_status()
    return r.content


def read_sharepoint_document_text(
    item_id: str,
    filename_hint: str,
    *,
    site_id: str | None = None,
    drive_id: str | None = None,
    tenant_id: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
) -> str:
    """
    Download a drive item and parse text if the extension is supported by :func:`read_text_document`.

    ``filename_hint`` should include the file extension (e.g. ``'SOW.docx'``).
    """
    from tempfile import NamedTemporaryFile

    suffix = ""
    for ext in sorted(DOCUMENT_EXTENSIONS, key=len, reverse=True):
        if filename_hint.lower().endswith(ext):
            suffix = ext
            break
    if not suffix:
        raise ValueError(f"Unsupported extension for {filename_hint!r}; supported: {sorted(DOCUMENT_EXTENSIONS)}")

    data = download_drive_item_content(
        item_id,
        site_id=site_id,
        drive_id=drive_id,
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
    )
    with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(data)
        path = tmp.name
    try:
        return read_text_document(path)
    finally:
        import os

        try:
            os.unlink(path)
        except OSError:
            pass
