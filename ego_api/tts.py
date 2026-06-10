"""Síntese de voz (Edge TTS) para respostas da IA no app mobile."""

from __future__ import annotations

import asyncio
import hashlib
import re
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

_EDGE_EXECUTOR = ThreadPoolExecutor(max_workers=2)

# 12 avatares → 12 vozes Edge distintas (texto sempre pt-BR).
# Só vozes multilíngues ou pt-BR/pt-PT — vozes árabe/japonês/hindi falavam outro idioma.
EDGE_TTS_VOICE_MAP: dict[str, str] = {
    # Grátis
    "vf1": "pt-BR-FranciscaNeural",  # Luna — acolhedora BR
    "vm1": "pt-BR-AntonioNeural",  # Leo — profissional BR
    # Conexão
    "vf2": "en-US-EmmaMultilingualNeural",  # Aisha — feminina calorosa, fala pt-BR
    "vf3": "pt-BR-ThalitaMultilingualNeural",  # Hana — feminina suave, fala pt-BR
    "vm2": "en-US-BrianMultilingualNeural",  # Kai — jovem energético
    "vm3": "pt-PT-DuarteNeural",  # Omar — masculina calma, fala português
    # Premium
    "vf4": "en-US-AvaMultilingualNeural",  # Amara — feminina calorosa
    "vm4": "pt-PT-DuarteNeural",  # Ravi — português nativo (europeu)
    "vg1": "de-DE-SeraphinaMultilingualNeural",  # Alex — neutra jovem
    # Total
    "vf5": "pt-PT-RaquelNeural",  # Sara — feminina europeia madura
    "vm5": "ko-KR-HyunsuMultilingualNeural",  # Malik — masculina urbana
    "vg2": "fr-FR-VivienneMultilingualNeural",  # Jordan — neutra calma
    # Legado / fase 2
    "vm6": "pt-PT-DuarteNeural",
    "vm7": "en-US-GuyNeural",
    "vm8": "en-US-ChristopherNeural",
    "vm9": "en-US-EricNeural",
    "vm10": "en-US-RogerNeural",
    "vf6": "pt-BR-ThalitaMultilingualNeural",
    "vf7": "en-US-JennyNeural",
    "vf8": "en-US-AriaNeural",
    "vf9": "en-US-EmmaMultilingualNeural",
    "vf10": "en-US-MichelleNeural",
    "pvm1": "en-US-AndrewMultilingualNeural",
    "pvf1": "en-US-EmmaMultilingualNeural",
}

EDGE_TTS_VOICE_LABELS: dict[str, str] = {
    "vf1": "Francisca (BR)",
    "vm1": "António (BR)",
    "vf2": "Emma (pt-BR)",
    "vf3": "Thalita (pt-BR)",
    "vm2": "Brian (jovem)",
    "vm3": "Duarte (PT)",
    "vf4": "Ava (calorosa)",
    "vm4": "Duarte (PT)",
    "vg1": "Seraphina (neutra)",
    "vf5": "Raquel (PT)",
    "vm5": "Hyunsu (urbano)",
    "vg2": "Vivienne (neutra)",
}

EDGE_TTS_FALLBACKS: dict[str, tuple[str, ...]] = {
    "vf1": ("pt-BR-ThalitaMultilingualNeural", "pt-PT-RaquelNeural"),
    "vf2": ("pt-BR-ThalitaMultilingualNeural", "pt-BR-FranciscaNeural"),
    "vf3": ("pt-BR-FranciscaNeural", "en-US-EmmaMultilingualNeural"),
    "vf4": ("en-US-EmmaMultilingualNeural", "pt-BR-FranciscaNeural"),
    "vf5": ("pt-BR-FranciscaNeural", "pt-BR-ThalitaMultilingualNeural"),
    "vm1": ("pt-PT-DuarteNeural", "en-US-AndrewMultilingualNeural"),
    "vm2": ("en-US-AndrewMultilingualNeural", "pt-BR-AntonioNeural"),
    "vm3": ("pt-BR-AntonioNeural", "en-US-AndrewMultilingualNeural"),
    "vm4": ("pt-BR-AntonioNeural", "en-US-AndrewMultilingualNeural"),
    "vm5": ("ko-KR-InJoonNeural", "en-US-BrianMultilingualNeural"),
    "vg1": ("en-US-EmmaMultilingualNeural", "pt-BR-ThalitaMultilingualNeural"),
    "vg2": ("fr-FR-RemyMultilingualNeural", "pt-PT-RaquelNeural"),
}

DEFAULT_EDGE_VOICE = "pt-BR-FranciscaNeural"
EDGE_TTS_FALLBACK_FEMALE = ("pt-BR-ThalitaMultilingualNeural", "pt-BR-FranciscaNeural")
EDGE_TTS_FALLBACK_MALE = ("pt-BR-AntonioNeural", "pt-PT-DuarteNeural")
EDGE_TTS_FALLBACK_NEUTRAL = ("pt-BR-ThalitaMultilingualNeural", "pt-BR-AntonioNeural")

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


def edge_voice_label(voice_id: str, avatar_id: str | None = None) -> str:
    from ego_api.persona import resolve_tts_voice

    vid = resolve_tts_voice(voice_id, avatar_id)
    return EDGE_TTS_VOICE_LABELS.get(vid, vid)


def _fallbacks_for_voice(voice_id: str, avatar_id: str | None = None) -> tuple[str, ...]:
    from ego_api.persona import is_male_avatar, is_neutral_avatar, resolve_tts_voice

    vid = resolve_tts_voice(voice_id, avatar_id)
    custom = EDGE_TTS_FALLBACKS.get(vid)
    if custom:
        return custom
    if vid.startswith("vg") or is_neutral_avatar(avatar_id):
        return EDGE_TTS_FALLBACK_NEUTRAL
    if is_male_avatar(avatar_id) or vid.startswith("vm") or vid.startswith("pvm"):
        return EDGE_TTS_FALLBACK_MALE
    return EDGE_TTS_FALLBACK_FEMALE


def _cache_key(text: str, voice_id: str) -> str:
    # v8: avatares Conexão/Premium — vozes pt-BR/pt-PT nativas
    payload = f"v8:{voice_id}:{text[:2400]}".encode("utf-8", errors="ignore")
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
    from ego_api.persona import resolve_tts_voice

    plain = plain_text_for_speech(text)
    if not plain:
        return None
    vid = resolve_tts_voice(voice_id, avatar_id)
    edge_voice = edge_voice_for_id(vid, avatar_id)
    fallbacks = _fallbacks_for_voice(vid, avatar_id)
    key = _cache_key(plain, vid)
    return _synthesize_cached(key, plain, edge_voice, fallbacks)


_synthesize_cached.cache_clear()
