"""Extração de texto de PDF (PyPDF2) — mesma lógica do Streamlit."""

from __future__ import annotations

import os
from io import BytesIO

try:
    from PyPDF2 import PdfReader
except ImportError:  # pragma: no cover
    PdfReader = None  # type: ignore[misc, assignment]

PDF_EXTRACT_MAX_CHARS = int(os.getenv("EGO_PDF_EXTRACT_MAX_CHARS", "120000"))
PDF_EXTRACT_MAX_PAGES = int(os.getenv("EGO_PDF_EXTRACT_MAX_PAGES", "24"))
UI_STATE_PDF_MAX_CHARS = int(os.getenv("EGO_UI_STATE_PDF_MAX_CHARS", "800000"))
PDF_UPLOAD_MAX_BYTES = int(os.getenv("EGO_PDF_UPLOAD_MAX_BYTES", str(12 * 1024 * 1024)))
PDF_UPLOAD_MAX_FILES = int(os.getenv("EGO_PDF_UPLOAD_MAX_FILES", "5"))


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
            if total_chars >= PDF_EXTRACT_MAX_CHARS:
                text_parts.append("\n[… limite de caracteres atingido neste PDF]\n")
                break
    except Exception as exc:  # noqa: BLE001
        text_parts.append(f"\n[Erro ao ler PDF: {exc}]\n")
    return "\n".join(text_parts).strip()


def extract_text_from_uploads(files: list[tuple[str, bytes]]) -> tuple[str, list[str]]:
    """Agrega vários PDFs; devolve texto e avisos por ficheiro."""
    warnings: list[str] = []
    chunks: list[str] = []
    total = 0
    for name, raw in files:
        if len(raw) > PDF_UPLOAD_MAX_BYTES:
            warnings.append(f"{name}: ficheiro demasiado grande (máx. {PDF_UPLOAD_MAX_BYTES // (1024 * 1024)} MB).")
            continue
        part = extract_text_from_pdf_bytes(raw)
        if not part.strip():
            warnings.append(f"{name}: sem texto legível.")
            continue
        if total + len(part) > PDF_EXTRACT_MAX_CHARS:
            room = max(0, PDF_EXTRACT_MAX_CHARS - total)
            if room > 0:
                chunks.append(part[:room])
            chunks.append("\n[… limite global de caracteres atingido]\n")
            total = PDF_EXTRACT_MAX_CHARS
            break
        chunks.append(part)
        total += len(part)
    return "\n\n".join(chunks).strip(), warnings


def cap_pdf_context_for_profile(text: str) -> tuple[str, bool]:
    raw = (text or "").strip()
    if len(raw) <= UI_STATE_PDF_MAX_CHARS:
        return raw, False
    return raw[:UI_STATE_PDF_MAX_CHARS], True
