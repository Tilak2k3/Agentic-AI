"""Tests for read_text_document (SOW / kickoff / common docs)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from docx import Document
from pypdf import PdfWriter

from agentic_ai.inputs.documents import DOCUMENT_EXTENSIONS, read_text_document


def test_read_txt_fixture(fixtures_dir: Path) -> None:
    path = fixtures_dir / "sample_meeting.txt"
    text = read_text_document(path)
    assert "Kickoff" in text
    assert "Alice" in text


def test_read_md_and_html(tmp_path: Path) -> None:
    md = tmp_path / "n.md"
    md.write_text("# Title\n\nBody line.", encoding="utf-8")
    assert "Body line" in read_text_document(md)

    html = tmp_path / "p.html"
    html.write_text("<html><body><p>Hello HTML</p></body></html>", encoding="utf-8")
    out = read_text_document(html)
    assert "Hello HTML" in out


def test_read_json_csv_xml_log(tmp_path: Path) -> None:
    (tmp_path / "d.json").write_text(json.dumps({"a": 1}), encoding="utf-8")
    assert '"a"' in read_text_document(tmp_path / "d.json")

    (tmp_path / "d.csv").write_text("h1,h2\n1,2", encoding="utf-8")
    assert "h1" in read_text_document(tmp_path / "d.csv")

    (tmp_path / "d.xml").write_text('<?xml version="1.0"?><r><x>y</x></r>', encoding="utf-8")
    assert "y" in read_text_document(tmp_path / "d.xml")

    (tmp_path / "app.log").write_text("INFO started", encoding="utf-8")
    assert "INFO" in read_text_document(tmp_path / "app.log")


def test_read_docx(tmp_path: Path) -> None:
    docx_path = tmp_path / "scope.docx"
    doc = Document()
    doc.add_paragraph("SOW deliverable alpha")
    doc.save(docx_path)
    text = read_text_document(docx_path)
    assert "deliverable" in text


def test_read_pdf_blank_page_runs(tmp_path: Path) -> None:
    pdf_path = tmp_path / "empty.pdf"
    w = PdfWriter()
    w.add_blank_page(width=200, height=200)
    with open(pdf_path, "wb") as f:
        w.write(f)
    text = read_text_document(pdf_path)
    assert isinstance(text, str)


def test_read_rtf(tmp_path: Path) -> None:
    rtf = tmp_path / "x.rtf"
    rtf.write_text(r"{\rtf1\ansi\deff0 {\fonttbl {\f0 Times New Roman;}} \f0\fs24 Hello RTF \par}", encoding="utf-8")
    assert "Hello RTF" in read_text_document(rtf)


def test_unsupported_extension_raises(tmp_path: Path) -> None:
    p = tmp_path / "x.xyz"
    p.write_text("nope", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported"):
        read_text_document(p)


def test_document_extensions_cover_common_types() -> None:
    assert ".docx" in DOCUMENT_EXTENSIONS
    assert ".pdf" in DOCUMENT_EXTENSIONS
    assert ".txt" in DOCUMENT_EXTENSIONS
