"""Histórico de chat só no dispositivo — parsing e limites sem gravar conteúdo."""

from __future__ import annotations

import json
from typing import Any

from ego_api.config import CHAT_HISTORY_FETCH_LIMIT, chat_local_history_enabled


def parse_client_history(raw: Any) -> list[dict]:
    if raw is None:
        return []
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return []
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return []
    if not isinstance(raw, list):
        return []
    cap = CHAT_HISTORY_FETCH_LIMIT
    out: list[dict] = []
    for item in raw[-cap:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        if role not in ("user", "assistant"):
            continue
        content = str(item.get("content") or "").strip()
        if not content or content == "…":
            continue
        out.append({"role": role, "content": content[:8000]})
    return out


def local_history_active(client_history: list[dict] | None) -> bool:
    return chat_local_history_enabled() or bool(client_history)
