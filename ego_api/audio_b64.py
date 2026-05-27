"""Decodificação tolerante de áudio base64 (Safari / ngrok / data URLs)."""

from __future__ import annotations

import base64
import binascii
import re


def sniff_audio_mime(data: bytes) -> str | None:
    if len(data) < 12:
        return None
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return "audio/wav"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBM":
        return "audio/webm"
    if data[:4] == b"\x1a\x45\xdf\xa3":
        return "audio/webm"
    if len(data) >= 8 and data[4:8] == b"ftyp":
        return "audio/mp4"
    return None


def normalize_audio_mime(mime: str | None, data: bytes | None = None) -> str:
    m = (mime or "").lower().strip()
    if "mp4" in m or "m4a" in m or "aac" in m:
        return "audio/mp4"
    if "webm" in m:
        return "audio/webm"
    if "wav" in m:
        return "audio/wav"
    if "mpeg" in m or "mp3" in m:
        return "audio/mpeg"
    sniffed = sniff_audio_mime(data) if data else None
    if sniffed:
        return sniffed
    return m or "audio/webm"


def decode_audio_base64(value: object) -> bytes | None:
    if value is None:
        return None
    if isinstance(value, (bytes, bytearray)):
        return bytes(value) if value else None
    if not isinstance(value, str):
        value = str(value)
    s = value.strip()
    if not s:
        return None
    if s.startswith("data:") and "," in s:
        s = s.split(",", 1)[1]
    s = re.sub(r"\s+", "", s)
    s = s.replace("-", "+").replace("_", "/")
    pad = len(s) % 4
    if pad:
        s += "=" * (4 - pad)
    try:
        data = base64.b64decode(s, validate=False)
    except (binascii.Error, ValueError):
        return None
    return data if data else None
