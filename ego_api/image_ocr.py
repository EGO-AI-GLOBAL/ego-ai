"""OCR de imagens via Gemini (mesma API key do chat)."""

from __future__ import annotations

import os

from ego_api.config import GEMINI_MODEL_FLASH, gemini_api_key

try:
    import google.generativeai as genai
except ImportError:
    genai = None  # type: ignore[misc, assignment]

IMAGE_OCR_MAX_BYTES = int(os.getenv("EGO_IMAGE_OCR_MAX_BYTES", str(8 * 1024 * 1024)))

_OCR_PROMPT = (
    "Extraia TODO o texto legível desta imagem, na ordem natural de leitura. "
    "Mantenha quebras de linha e parágrafos. Não resuma, não traduza e não comente. "
    "Devolva apenas o texto extraído. "
    "Se não houver texto legível, responda apenas: [sem texto visível]"
)

_MIME_BY_SUFFIX: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".heic": "image/heic",
    ".heif": "image/heif",
}


def image_mime_from_filename(filename: str) -> str:
    ext = (filename or "").lower().rsplit(".", 1)[-1]
    key = f".{ext}" if ext else ""
    return _MIME_BY_SUFFIX.get(key, "image/jpeg")


def is_image_filename(filename: str) -> bool:
    ext = (filename or "").lower()
    return any(ext.endswith(s) for s in _MIME_BY_SUFFIX)


def extract_text_from_image_bytes(raw: bytes, filename: str = "image.jpg") -> str:
    if not raw:
        return ""
    if len(raw) > IMAGE_OCR_MAX_BYTES:
        raise ValueError(
            f"Imagem demasiado grande (máx. {IMAGE_OCR_MAX_BYTES // (1024 * 1024)} MB)."
        )
    key = gemini_api_key()
    if not key or genai is None:
        raise RuntimeError(
            "OCR de imagens indisponível (GOOGLE_API_KEY / GEMINI_API_KEY em falta)."
        )
    mime = image_mime_from_filename(filename)
    genai.configure(api_key=key)
    model_name = (GEMINI_MODEL_FLASH or "gemini-2.0-flash").strip()
    if not model_name.startswith("models/"):
        model_name = f"models/{model_name}"
    model = genai.GenerativeModel(model_name)
    try:
        gen_cfg = genai.GenerationConfig(
            temperature=0.1,
            max_output_tokens=8192,
        )
    except Exception:  # noqa: BLE001
        gen_cfg = None
    resp = model.generate_content(
        [
            _OCR_PROMPT,
            {"mime_type": mime, "data": raw},
        ],
        generation_config=gen_cfg,
    )
    text = (resp.text or "").strip()
    if text == "[sem texto visível]":
        return ""
    return text
