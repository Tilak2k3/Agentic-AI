"""Email: .eml files, IMAP fetch, optional Microsoft Graph mail (thread-style export)."""

from __future__ import annotations

import email
import email.policy
import imaplib
from pathlib import Path

from agentic_ai.config import get_azure_graph_config, get_imap_config
from agentic_ai.inputs.graph_auth import get_graph_token


def _decode_payload(part: email.message.Message) -> str:
    try:
        return part.get_content()
    except Exception:
        payload = part.get_payload(decode=True)
        if payload is None:
            return ""
        charset = part.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")


def message_to_plain_text(msg: email.message.Message) -> str:
    """Best-effort plain text from a MIME message."""
    if msg.is_multipart():
        texts: list[str] = []
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain" and "attachment" not in str(part.get("Content-Disposition", "")).lower():
                texts.append(_decode_payload(part))
            elif ctype == "text/html" and not texts:
                raw = _decode_payload(part)
                texts.append(raw)
        return "\n\n".join(t for t in texts if t).strip()
    if msg.get_content_type() == "text/plain":
        return _decode_payload(msg).strip()
    return _decode_payload(msg).strip()


def extract_text_from_eml_bytes(data: bytes) -> str:
    msg = email.message_from_bytes(data, policy=email.policy.default)
    return _format_email_for_context(msg)


def extract_text_from_eml_path(path: str | Path) -> str:
    p = Path(path)
    return extract_text_from_eml_bytes(p.read_bytes())


def _format_email_for_context(msg: email.message.Message) -> str:
    subj = msg.get("Subject", "")
    frm = msg.get("From", "")
    to = msg.get("To", "")
    date = msg.get("Date", "")
    body = message_to_plain_text(msg)
    lines = [
        f"Subject: {subj}",
        f"From: {frm}",
        f"To: {to}",
        f"Date: {date}",
        "",
        body,
    ]
    return "\n".join(lines).strip()


def fetch_imap_messages_as_thread_text(
    *,
    subject_contains: str | None = None,
    max_messages: int = 50,
) -> str:
    """
    Fetch recent messages from IMAP and concatenate as one text blob (newest last).

    Uses IMAP_* variables from the environment via :func:`get_imap_config`.
    """
    cfg = get_imap_config()
    if cfg is None:
        raise ValueError("IMAP not configured. Set IMAP_HOST, IMAP_USER, IMAP_PASSWORD.")

    with imaplib.IMAP4_SSL(cfg.host) as M:
        M.login(cfg.user, cfg.password)
        sel_status, sel_data = M.select(cfg.folder)
        if sel_status != "OK":
            detail = sel_data[0].decode(errors="replace") if sel_data and sel_data[0] else sel_status
            raise RuntimeError(
                f"IMAP could not select folder {cfg.folder!r} ({detail}). "
                "Fix IMAP_FOLDER (exact mailbox/label name) or create the folder."
            )
        status, data = M.search(None, "ALL")
        if status != "OK" or not data or not data[0]:
            return ""
        ids = data[0].split()
        ids = ids[-max_messages:]
        blocks: list[str] = []
        for mid in ids:
            status, fetched = M.fetch(mid, "(RFC822)")
            if status != "OK" or not fetched or not fetched[0]:
                continue
            raw = fetched[0][1]
            if not isinstance(raw, (bytes, bytearray)):
                continue
            msg = email.message_from_bytes(bytes(raw), policy=email.policy.default)
            if subject_contains and subject_contains.lower() not in (msg.get("Subject") or "").lower():
                continue
            blocks.append(_format_email_for_context(msg))
        return "\n\n---\n\n".join(blocks)


def fetch_graph_messages_as_text(
    *,
    user_id: str,
    top: int = 25,
    search: str | None = None,
    tenant_id: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
) -> str:
    """
    List messages from a mailbox via Microsoft Graph (application permissions).

    Requires Mail.Read application permission and a user principal name or id in ``user_id``.
    Optional ``search`` uses ``$search`` query parameter (Graph).
    """
    import requests

    g = get_azure_graph_config()
    tid = tenant_id or (g.tenant_id if g else None)
    cid = client_id or (g.client_id if g else None)
    secret = client_secret or (g.client_secret if g else None)
    if not all((tid, cid, secret)):
        raise ValueError("Azure Graph not configured. Set AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET.")

    token = get_graph_token(tid, cid, secret)
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://graph.microsoft.com/v1.0/users/{user_id}/messages"
    params: dict[str, str | int] = {"$top": top, "$orderby": "receivedDateTime asc"}
    headers_req = dict(headers)
    if search:
        # $search requires the ConsistencyLevel header on this endpoint.
        headers_req["ConsistencyLevel"] = "eventual"
        params["$search"] = f'"{search}"'
    r = requests.get(url, headers=headers_req, params=params, timeout=60)
    r.raise_for_status()
    data = r.json()
    items = data.get("value") or []
    parts: list[str] = []
    for m in items:
        subj = m.get("subject") or ""
        frm = (m.get("from") or {}).get("emailAddress", {}).get("address", "")
        received = m.get("receivedDateTime") or ""
        body = (m.get("body") or {}).get("content") or ""
        is_html = (m.get("body") or {}).get("contentType", "").lower() == "html"
        if is_html and body:
            from html.parser import HTMLParser

            class P(HTMLParser):
                def __init__(self) -> None:
                    super().__init__()
                    self._b: list[str] = []

                def handle_data(self, d: str) -> None:
                    if d.strip():
                        self._b.append(d)

                def text(self) -> str:
                    return "\n".join(self._b)

            p = P()
            p.feed(body)
            body = p.text()
        parts.append(
            "\n".join(
                [
                    f"Subject: {subj}",
                    f"From: {frm}",
                    f"Received: {received}",
                    "",
                    body.strip(),
                ]
            )
        )
    return "\n\n---\n\n".join(parts)
