"""Input sources: meetings, documents, email, SharePoint."""

from agentic_ai.inputs.documents import read_text_document
from agentic_ai.inputs.email_input import (
    extract_text_from_eml_bytes,
    extract_text_from_eml_path,
    fetch_graph_messages_as_text,
    fetch_imap_messages_as_thread_text,
)
from agentic_ai.inputs.meeting_recordings import extract_meeting_text
from agentic_ai.inputs.sharepoint import (
    download_drive_item_content,
    list_drive_folder_children,
    read_sharepoint_document_text,
)

__all__ = [
    "extract_meeting_text",
    "read_text_document",
    "extract_text_from_eml_path",
    "extract_text_from_eml_bytes",
    "fetch_imap_messages_as_thread_text",
    "fetch_graph_messages_as_text",
    "list_drive_folder_children",
    "download_drive_item_content",
    "read_sharepoint_document_text",
]
