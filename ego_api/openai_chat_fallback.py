"""Fallback de chat em texto quando Gemini atinge cota (usa OPENAI_API_KEY no Railway)."""

from __future__ import annotations

import requests

from ego_api.config import CHAT_LLM_MAX_TURNS, openai_api_key, read_env


def openai_chat_fallback_enabled() -> bool:
    raw = read_env("EGO_CHAT_OPENAI_FALLBACK", "1").lower()
    return raw not in ("0", "false", "no", "nao", "não")


def _openai_chat_model() -> str:
    return read_env("OPENAI_CHAT_MODEL", "gpt-4o-mini") or "gpt-4o-mini"


def generate_openai_text_reply(
    user_text: str,
    *,
    conversation_messages: list | None,
    system_instruction: str,
) -> str | None:
    """
    Retorna texto do assistente ou None se OpenAI indisponível/erro.
    Só para mensagens de texto (sem áudio).
    """
    if not openai_chat_fallback_enabled():
        return None
    key = openai_api_key()
    if not key or not (user_text or "").strip():
        return None

    messages: list[dict[str, str]] = [
        {"role": "system", "content": (system_instruction or "").strip()[:12000]}
    ]
    prior = conversation_messages or []
    if len(prior) > CHAT_LLM_MAX_TURNS:
        prior = prior[-CHAT_LLM_MAX_TURNS:]
    for m in prior:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if not content:
            continue
        if role == "user":
            messages.append({"role": "user", "content": content})
        elif role == "assistant":
            messages.append({"role": "assistant", "content": content})
    messages.append({"role": "user", "content": (user_text or "").strip()})

    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": _openai_chat_model(),
                "messages": messages,
                "max_tokens": 720,
                "temperature": 0.75,
            },
            timeout=75,
        )
    except requests.RequestException:
        return None

    if resp.status_code != 200:
        return None
    try:
        data = resp.json()
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        text = (msg.get("content") or "").strip()
        return text or None
    except (ValueError, TypeError, KeyError):
        return None
