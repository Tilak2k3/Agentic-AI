"""Acquire Microsoft Graph access tokens (client credentials)."""

from __future__ import annotations

import msal

GRAPH_SCOPE = ["https://graph.microsoft.com/.default"]


def get_graph_token(tenant_id: str, client_id: str, client_secret: str) -> str:
    app = msal.ConfidentialClientApplication(
        client_id,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
        client_credential=client_secret,
    )
    result = app.acquire_token_silent(GRAPH_SCOPE, account=None)
    if not result:
        result = app.acquire_token_for_client(scopes=GRAPH_SCOPE)
    if "access_token" not in result:
        err = result.get("error_description") or result.get("error") or str(result)
        raise RuntimeError(f"Graph token failed: {err}")
    return result["access_token"]
