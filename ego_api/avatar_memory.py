"""Memória leve por avatar — 1–2 frases por persona, sem misturar."""

from __future__ import annotations

import re
from typing import Any

from supabase import Client

from ego_api.db import load_profile, update_profile_fields

_UI_KEY = "avatar_memories"
_MAX_SNIPPET = 140
_SKIP_PREFIXES = (
    "[ritual",
    "[desabafo",
    "marca na agenda",
    "marca ",
)


def _parse_memories(prof: dict | None) -> dict[str, str]:
    if not prof:
        return {}
    from ego_api.db import _parse_ui_state

    ui = _parse_ui_state(prof)
    raw = ui.get(_UI_KEY)
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in raw.items():
        key = str(k or "").strip().lower()[:32]
        val = str(v or "").strip()[: _MAX_SNIPPET]
        if key and val:
            out[key] = val
    return out


def _should_remember(text: str) -> bool:
    t = (text or "").strip()
    if len(t) < 12:
        return False
    low = t.lower()
    if any(low.startswith(p) for p in _SKIP_PREFIXES):
        return False
    if re.match(r"^(oi|olá|ola|hey|ok|sim|não|nao|obrigad)\b", low):
        return len(t) < 40
    return True


def _summarize_for_memory(text: str) -> str:
    t = re.sub(r"\s+", " ", (text or "").strip())
    if len(t) <= _MAX_SNIPPET:
        return t
    return t[: _MAX_SNIPPET - 1].rstrip() + "…"


def memory_context_block(supabase: Client | None, user_id: str, avatar_id: str) -> str:
    """Injecta no prompt — só memória deste avatar."""
    prof = load_profile(supabase, user_id) if supabase and user_id else None
    mem = _parse_memories(prof)
    aid = (avatar_id or "").strip().lower()[:32]
    snippet = mem.get(aid)
    if not snippet:
        return ""
    return (
        "\n\n=== MEMÓRIA DESTE AVATAR (só referência suave) ===\n"
        f"Na última conversa com este utilizador, ele(a) mencionou: «{snippet}»\n"
        "Se couber, pergunte com gentileza como foi — sem insistir nem inventar detalhes.\n"
        "=== FIM MEMÓRIA ===\n"
    )


def save_avatar_memory(
    supabase: Client | None,
    user_id: str,
    avatar_id: str,
    user_message: str,
) -> None:
    """Grava 1 frase por avatar_id após mensagem substantiva."""
    if not supabase or not user_id or not _should_remember(user_message):
        return
    aid = (avatar_id or "").strip().lower()[:32]
    if not aid:
        return
    prof = load_profile(supabase, user_id)
    if not prof:
        return
    from ego_api.db import _parse_ui_state

    ui = _parse_ui_state(prof)
    mem = _parse_memories(prof)
    mem[aid] = _summarize_for_memory(user_message)
    # Mantém no máximo 12 entradas (uma por avatar).
    if len(mem) > 12:
        keys = list(mem.keys())
        for old in keys[:-12]:
            mem.pop(old, None)
    merged = {**ui, _UI_KEY: mem}
    update_profile_fields(supabase, user_id, {"ui_state": merged})


__all__ = ["memory_context_block", "save_avatar_memory"]
