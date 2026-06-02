"""Recebe uploads de documentos (multipart ou JSON base64)."""

from __future__ import annotations

import base64
import re
from typing import Any

from flask import Request

from ego_api.document_extract import DOC_UPLOAD_MAX_FILES, is_allowed_document


def _safe_filename(name: str, fallback: str = "documento.pdf") -> str:
    raw = (name or "").strip()
    if not raw:
        return fallback
    # Evita paths vindos do SO (content://, etc.)
    raw = raw.replace("\\", "/").split("/")[-1]
    raw = re.sub(r"[^\w.\- ()áàâãéêíóôõúçÁÀÂÃÉÊÍÓÔÕÚÇ]", "_", raw)
    return raw[:200] or fallback


def collect_upload_file_bytes(request: Request) -> tuple[list[tuple[str, bytes]], str]:
    """
    Devolve lista (filename, raw_bytes) e mensagem de erro vazia ou texto de diagnóstico.
  """
    files: list[tuple[str, bytes]] = []
    errors: list[str] = []

    # 1) multipart — qualquer chave (React Native pode variar)
    if request.files:
        keys = list(request.files.keys())
        for key in keys:
            for up in request.files.getlist(key):
                if not up:
                    continue
                name = _safe_filename(
                    str(up.filename or ""),
                    fallback=f"upload{len(files) + 1}.bin",
                )
                try:
                    raw = up.read()
                except Exception as exc:
                    errors.append(f"{name}: leitura falhou ({exc})")
                    continue
                if raw:
                    files.append((name, raw))

    # 2) JSON { "files": [ { "name", "content_base64" } ] }
    if not files and request.is_json:
        data = request.get_json(silent=True) or {}
        items = data.get("files")
        if isinstance(items, list):
            for i, item in enumerate(items[:DOC_UPLOAD_MAX_FILES]):
                if not isinstance(item, dict):
                    continue
                name = _safe_filename(
                    str(item.get("name") or item.get("filename") or ""),
                    fallback=f"documento{i + 1}.pdf",
                )
                b64 = item.get("content_base64") or item.get("data_base64") or ""
                if not b64:
                    continue
                try:
                    raw = base64.b64decode(str(b64), validate=False)
                except Exception as exc:
                    errors.append(f"{name}: base64 inválido ({exc})")
                    continue
                if raw:
                    files.append((name, raw))

    # 3) Campos de formulário (fallback)
    if not files:
        b64 = request.form.get("content_base64") or request.form.get("data_base64")
        if b64:
            name = _safe_filename(
                str(request.form.get("filename") or request.form.get("name") or ""),
                fallback="documento.pdf",
            )
            try:
                raw = base64.b64decode(str(b64), validate=False)
                if raw:
                    files.append((name, raw))
            except Exception as exc:
                errors.append(f"base64 inválido ({exc})")

    if files:
        return files[:DOC_UPLOAD_MAX_FILES], ""

    if errors:
        return [], "; ".join(errors)

    ctype = (request.content_type or "").lower()
    keys = list(request.files.keys()) if request.files else []
    return (
        [],
        "Nenhum documento recebido. "
        f"Content-Type={ctype or 'ausente'}; campos multipart={keys or 'nenhum'}.",
    )


def filter_allowed_uploads(
    files: list[tuple[str, bytes]],
) -> tuple[list[tuple[str, bytes]], list[str]]:
    ok: list[tuple[str, bytes]] = []
    warnings: list[str] = []
    for name, raw in files:
        if not is_allowed_document(name):
            warnings.append(f"{name}: formato não suportado.")
            continue
        ok.append((name, raw))
    return ok, warnings
