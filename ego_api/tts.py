"""Síntese de voz (Edge TTS) para respostas da IA no app mobile."""

from __future__ import annotations

import asyncio
import hashlib
import re
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

_EDGE_EXECUTOR = ThreadPoolExecutor(max_workers=2)

# Vozes Edge TTS verificadas (2025+); outras caem no fallback por género.
EDGE_TTS_VOICE_MAP: dict[str, str] = {
    "vm1": "pt-BR-AntonioNeural",
    "vm2": "pt-BR-AntonioNeural",
    "vm3": "pt-BR-AntonioNeural",
    "vm4": "pt-BR-AntonioNeural",
    "vm5": "pt-BR-AntonioNeural",
    "vm6": "pt-BR-AntonioNeural",
    "vm7": "en-US-GuyNeural",
    "vm8": "en-US-ChristopherNeural",
    "vm9": "en-US-EricNeural",
    "vm10": "en-US-RogerNeural",
    "vf1": "pt-BR-FranciscaNeural",
    "vf2": "pt-BR-ThalitaNeural",
    "vf3": "pt-BR-ThalitaNeural",
    "vf4": "pt-BR-ThalitaNeural",
    "vf5": "pt-BR-ThalitaNeural",
    "vf6": "pt-BR-ThalitaNeural",
    "vf7": "en-US-JennyNeural",
    "vf8": "en-US-AriaNeural",
    "vf9": "en-US-EmmaNeural",
    "vf10": "en-US-MichelleNeural",
    "pvm1": "en-US-DavisNeural",
    "pvf1": "en-US-AmberNeural",
    "vg1": "pt-BR-AntonioNeural",
    "vg2": "pt-BR-ThalitaNeural",
}
DEFAULT_EDGE_VOICE = "pt-BR-FranciscaNeural"
EDGE_TTS_FALLBACK_FEMALE = ("pt-BR-ThalitaNeural", "pt-BR-FranciscaNeural")
EDGE_TTS_FALLBACK_MALE = ("pt-BR-AntonioNeural",)

_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "\U0001F900-\U0001F9FF"
    "\U00002600-\U000026FF"
    "\u200d"
    "\ufe0f"
    "]+",
    flags=re.UNICODE,
)


def plain_text_for_speech(text: str, max_len: int = 3000) -> str:
    """Texto limpo para TTS: sem markdown, marcadores EGO nem emojis."""
    t = (text or "").strip()
    if not t:
        return ""
    t = re.sub(r"\[\[EGO_[^\]]+\]\]", "", t)
    t = re.sub(r"```[\s\S]*?```", " ", t)
    t = re.sub(r"`([^`]+)`", r"\1", t)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    t = re.sub(r"[*_#>|]+", " ", t)
    t = _EMOJI_RE.sub("", t)
    t = re.sub(r"[\u2600-\u27BF]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:max_len]


def edge_voice_for_id(voice_id: str, avatar_id: str | None = None) -> str:
    from ego_api.persona import is_male_avatar, resolve_tts_voice

    vid = resolve_tts_voice(voice_id, avatar_id)
    mapped = EDGE_TTS_VOICE_MAP.get(vid)
    if mapped:
        return mapped
    if is_male_avatar(avatar_id) or vid.startswith("vm") or vid.startswith("pvm"):
        return EDGE_TTS_FALLBACK_MALE[0]
    return DEFAULT_EDGE_VOICE


def _cache_key(text: str, voice_id: str) -> str:
    # v3: mapa de vozes corrigido (Brenda/indisponíveis → Thalita/Antonio)
    payload = f"v3:{voice_id}:{text[:2400]}".encode("utf-8", errors="ignore")
    return hashlib.sha256(payload).hexdigest()


async def _edge_tts_async(plain: str, edge_voice: str) -> bytes:
    import edge_tts

    communicate = edge_tts.Communicate(plain, edge_voice)
    data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            data += chunk["data"]
    return data


def _run_edge_tts(plain: str, edge_voice: str, fallbacks: tuple[str, ...] = ()) -> bytes | None:
    voices = (edge_voice, *fallbacks)
    seen: set[str] = set()
    for voice in voices:
        if not voice or voice in seen:
            continue
        seen.add(voice)
        try:
            data = asyncio.run(_edge_tts_async(plain, voice))
            if data:
                return data
        except Exception:
            continue
    return None


@lru_cache(maxsize=64)
def _synthesize_cached(
    cache_key: str, text: str, edge_voice: str, fallbacks: tuple[str, ...] = ()
) -> bytes | None:
    del cache_key
    plain = plain_text_for_speech(text)
    if not plain:
        return None
    future = _EDGE_EXECUTOR.submit(_run_edge_tts, plain, edge_voice, fallbacks)
    try:
        return future.result(timeout=90)
    except Exception:
        return None


def synthesize_speech_mp3(
    text: str, voice_id: str = "vf1", avatar_id: str | None = None
) -> bytes | None:
    """Gera MP3 com Edge TTS (requer: pip install edge-tts)."""
    from ego_api.persona import is_male_avatar, resolve_tts_voice

    plain = plain_text_for_speech(text)
    if not plain:
        return None
    vid = resolve_tts_voice(voice_id, avatar_id)
    edge_voice = edge_voice_for_id(vid, avatar_id)
    fallbacks = (
        EDGE_TTS_FALLBACK_MALE if is_male_avatar(avatar_id) or vid.startswith("vm") else EDGE_TTS_FALLBACK_FEMALE
    )
    key = _cache_key(plain, vid)
    return _synthesize_cached(key, plain, edge_voice, fallbacks)


_synthesize_cached.cache_clear()
