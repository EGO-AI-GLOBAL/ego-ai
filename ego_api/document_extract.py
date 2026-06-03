"""Extração de texto de documentos (PDF, texto plano, DOCX) — app e Streamlit."""

from __future__ import annotations

import os
import zipfile
from io import BytesIO
from pathlib import Path
import xml.etree.ElementTree as ET

try:
    from PyPDF2 import PdfReader
except ImportError:  # pragma: no cover
    PdfReader = None  # type: ignore[misc, assignment]

DOC_EXTRACT_MAX_CHARS = int(os.getenv("EGO_PDF_EXTRACT_MAX_CHARS", "120000"))
PDF_EXTRACT_MAX_PAGES = int(os.getenv("EGO_PDF_EXTRACT_MAX_PAGES", "24"))
UI_STATE_PDF_MAX_CHARS = int(os.getenv("EGO_UI_STATE_PDF_MAX_CHARS", "800000"))
DOC_UPLOAD_MAX_BYTES = int(os.getenv("EGO_PDF_UPLOAD_MAX_BYTES", str(12 * 1024 * 1024)))
DOC_UPLOAD_MAX_FILES = int(os.getenv("EGO_PDF_UPLOAD_MAX_FILES", "5"))

_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

# Sufixos aceites no upload (minúsculas).
IMAGE_SUFFIXES: frozenset[str] = frozenset(
    {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
)

TEXT_SUFFIXES: frozenset[str] = frozenset(
    {
        ".txt",
        ".md",
        ".markdown",
        ".csv",
        ".tsv",
        ".json",
        ".xml",
        ".html",
        ".htm",
        ".log",
        ".rst",
    }
)

ALLOWED_SUFFIXES: frozenset[str] = frozenset({".pdf", ".docx", *TEXT_SUFFIXES, *IMAGE_SUFFIXES})

ALLOWED_SUFFIXES_LABEL = (
    "PDF, Word (.docx), TXT, MD, CSV, JSON, HTML, fotos (JPG, PNG, WEBP)"
)


def _suffix(filename: str) -> str:
    return Path(filename or "").suffix.lower()


def is_allowed_document(filename: str) -> bool:
    return _suffix(filename) in ALLOWED_SUFFIXES


def decode_text_bytes(raw: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def extract_text_from_pdf_bytes(raw: bytes) -> str:
    if not PdfReader:
        return ""
    text_parts: list[str] = []
    total_chars = 0
    try:
        reader = PdfReader(BytesIO(raw))
        for i, page in enumerate(reader.pages):
            if i >= PDF_EXTRACT_MAX_PAGES:
                text_parts.append("\n[… páginas extra omitidas para velocidade]\n")
                break
            page_text = page.extract_text() or ""
            if not page_text.strip():
                continue
            text_parts.append(page_text)
            total_chars += len(page_text)
            if total_chars >= DOC_EXTRACT_MAX_CHARS:
                text_parts.append("\n[… limite de caracteres atingido neste PDF]\n")
                break
    except Exception as exc:  # noqa: BLE001
        text_parts.append(f"\n[Erro ao ler PDF: {exc}]\n")
    return "\n".join(text_parts).strip()


def extract_text_from_docx_bytes(raw: bytes) -> str:
    lines: list[str] = []
    try:
        with zipfile.ZipFile(BytesIO(raw)) as zf:
            xml_bytes = zf.read("word/document.xml")
    except Exception:
        return ""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return ""
    for para in root.iter(f"{{{_W_NS}}}p"):
        parts: list[str] = []
        for node in para.iter(f"{{{_W_NS}}}t"):
            if node.text:
                parts.append(node.text)
        line = "".join(parts).strip()
        if line:
            lines.append(line)
    return "\n".join(lines).strip()


def extract_text_from_file_bytes(filename: str, raw: bytes) -> str:
    ext = _suffix(filename)
    if ext == ".pdf":
        return extract_text_from_pdf_bytes(raw)
    if ext == ".docx":
        return extract_text_from_docx_bytes(raw)
    if ext in IMAGE_SUFFIXES:
        from ego_api.image_ocr import extract_text_from_image_bytes

        return extract_text_from_image_bytes(raw, filename)
    if ext in TEXT_SUFFIXES:
        return decode_text_bytes(raw).strip()
    return ""


def extract_text_from_uploads(files: list[tuple[str, bytes]]) -> tuple[str, list[str]]:
    """Agrega vários ficheiros; devolve texto e avisos por ficheiro."""
    warnings: list[str] = []
    chunks: list[str] = []
    total = 0
    for name, raw in files:
        if not is_allowed_document(name):
            warnings.append(
                f"{name}: formato não suportado. Use {ALLOWED_SUFFIXES_LABEL}."
            )
            continue
        if len(raw) > DOC_UPLOAD_MAX_BYTES:
            warnings.append(
                f"{name}: ficheiro demasiado grande "
                f"(máx. {DOC_UPLOAD_MAX_BYTES // (1024 * 1024)} MB)."
            )
            continue
        part = extract_text_from_file_bytes(name, raw)
        if not part.strip():
            warnings.append(f"{name}: sem texto legível.")
            continue
        if total + len(part) > DOC_EXTRACT_MAX_CHARS:
            room = max(0, DOC_EXTRACT_MAX_CHARS - total)
            if room > 0:
                chunks.append(part[:room])
            chunks.append("\n[… limite global de caracteres atingido]\n")
            total = DOC_EXTRACT_MAX_CHARS
            break
        chunks.append(part)
        total += len(part)
    return "\n\n".join(chunks).strip(), warnings


def cap_pdf_context_for_profile(text: str) -> tuple[str, bool]:
    raw = (text or "").strip()
    if len(raw) <= UI_STATE_PDF_MAX_CHARS:
        return raw, False
    return raw[:UI_STATE_PDF_MAX_CHARS], True
