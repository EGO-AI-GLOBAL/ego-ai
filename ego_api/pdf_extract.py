"""Compat: reexporta extração de documentos (nome histórico pdf_extract)."""

from ego_api.document_extract import (  # noqa: F401
    ALLOWED_SUFFIXES,
    ALLOWED_SUFFIXES_LABEL,
    DOC_EXTRACT_MAX_CHARS,
    DOC_UPLOAD_MAX_BYTES,
    DOC_UPLOAD_MAX_FILES,
    PDF_EXTRACT_MAX_CHARS,
    PDF_EXTRACT_MAX_PAGES,
    PDF_UPLOAD_MAX_BYTES,
    PDF_UPLOAD_MAX_FILES,
    UI_STATE_PDF_MAX_CHARS,
    cap_pdf_context_for_profile,
    extract_text_from_file_bytes,
    extract_text_from_pdf_bytes,
    extract_text_from_uploads,
    is_allowed_document,
)

# Alias antigos
PDF_EXTRACT_MAX_CHARS = DOC_EXTRACT_MAX_CHARS
PDF_UPLOAD_MAX_BYTES = DOC_UPLOAD_MAX_BYTES
PDF_UPLOAD_MAX_FILES = DOC_UPLOAD_MAX_FILES
