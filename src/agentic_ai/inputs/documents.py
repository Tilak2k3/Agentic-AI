"""SOW / scope / kickoff notes: common text-bearing document formats."""

from __future__ import annotations

import zipfile
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree as ET

from pypdf import PdfReader

DOCUMENT_EXTENSIONS = frozenset(
    {
        ".txt",
        ".md",
        ".markdown",
        ".log",
        ".csv",
        ".json",
        ".xml",
        ".html",
        ".htm",
        ".docx",
        ".pdf",
        ".rtf",
        ".odt",
    }
)


class _HTMLToText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self._parts.append(data)

    def get_text(self) -> str:
        return "\n".join(self._parts)


def _read_plain(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _read_html(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    parser = _HTMLToText()
    parser.feed(raw)
    return parser.get_text().strip() or raw


def _read_docx(path: Path) -> str:
    from docx import Document

    doc = Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def _read_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    pages: list[str] = []
    for page in reader.pages:
        t = page.extract_text() or ""
        pages.append(t)
    return "\n\n".join(pages).strip()


def _read_rtf(path: Path) -> str:
    from striprtf.striprtf import rtf_to_text

    raw = path.read_text(encoding="utf-8", errors="replace")
    return rtf_to_text(raw).strip()


def _read_odt(path: Path) -> str:
    """Extract text from ODT (OpenDocument Text) via content.xml."""
    with zipfile.ZipFile(path, "r") as zf:
        with zf.open("content.xml") as f:
            tree = ET.parse(f)
    root = tree.getroot()
    chunks: list[str] = []
    for el in root.iter():
        tag = el.tag
        if tag.endswith("}p") or tag.endswith("}h"):
            texts = [t for t in el.itertext()]
            line = "".join(texts).strip()
            if line:
                chunks.append(line)
    return "\n".join(chunks).strip()


def read_text_document(path: str | Path) -> str:
    """
    Read SOW, scope, kickoff notes, or similar from a supported file.

    Supported: .txt, .md, .html, .docx, .pdf, .rtf, .odt, and plain UTF-8 text types
    (.csv, .json, .xml, .log).
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(p)
    suffix = p.suffix.lower()
    if suffix not in DOCUMENT_EXTENSIONS:
        raise ValueError(
            f"Unsupported document extension {suffix!r}. Supported: {sorted(DOCUMENT_EXTENSIONS)}."
        )
    if suffix in {".txt", ".md", ".markdown", ".log", ".csv", ".json", ".xml"}:
        return _read_plain(p)
    if suffix in {".html", ".htm"}:
        return _read_html(p)
    if suffix == ".docx":
        return _read_docx(p)
    if suffix == ".pdf":
        return _read_pdf(p)
    if suffix == ".rtf":
        return _read_rtf(p)
    if suffix == ".odt":
        return _read_odt(p)
    raise ValueError(f"No reader implemented for {suffix}")
