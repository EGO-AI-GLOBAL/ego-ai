"""Caminho de voz turbo — 1× Gemini + TTS inline (app 1.0.74 ouve num só pedido)."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ego_supabase import Client

from ego_api import db, gemini
from ego_api.db import VOICE_MESSAGE_MARKER
from ego_api.persona import (
    apply_assistant_name_from_avatar,
    normalize_persona_pair,
    resolve_tts_voice,
)
from ego_api.request_ctx import get_session
from ego_api.services import (
    _access_expired_message,
    _daily_limit_message,
    _history_from_client,
    _safe_plan_access_payload,
)


def process_voice_message_fast(
    supabase: Client | None,
    user_id: str,
    *,
    audio_bytes: bytes,
    audio_mime: str,
    speak_reply: bool = False,
    client_history: list | None = None,
) -> tuple[dict | None, str | None]:
    """Voz push-to-talk: sem STT duplicado, sem agenda, áudio inline se speak=true."""
    sess = get_session()
    if not sess or sess.user_id != user_id:
        return None, "Sessão inválida."

    prof = db.load_profile(supabase, user_id) or {}
    _tier, limits = db.user_plan_limits(prof)
    ok_access, _status = db.check_access(supabase, user_id)
    if not ok_access:
        from ego_api.plan_retention import on_trial_access_denied

        on_trial_access_denied(user_id)
        return None, _access_expired_message(supabase, user_id)

    ok_tok, msg_tok, used_tok, lim_tok = db.check_token_allowance(supabase, user_id, prof)
    if not ok_tok:
        return None, f"{msg_tok} Uso: {used_tok:,}/{lim_tok:,}."

    ok_voice, _voice_used = db.daily_voice_messages_ok(supabase, user_id, limits, prof)
    if not ok_voice:
        from ego_api.plan_retention import on_daily_limit_hit

        on_daily_limit_hit(user_id)
        return None, _daily_limit_message(supabase, user_id)

    from ego_api.config import chat_defer_tts_on_voice

    defer_tts = chat_defer_tts_on_voice()
    speak_effective = False
    if speak_reply and not defer_tts:
        ok_tts, _tts_used = db.daily_tts_ok(supabase, user_id, limits, prof)
        if not ok_tts:
            from ego_api.plan_retention import on_daily_limit_hit

            on_daily_limit_hit(user_id)
            return None, _daily_limit_message(supabase, user_id)
        speak_effective = True

    stored_a, stored_v = db.load_persona(supabase, user_id)
    avatar_id, voice_id = normalize_persona_pair(stored_a, stored_v)
    apply_assistant_name_from_avatar(avatar_id)

    client_hist = _history_from_client(client_history)
    history = client_hist if client_hist else db.load_chat_history(supabase, user_id, limit=4)
    if len(history) > 2:
        history = history[-2:]
    history_for_llm = [*history, {"role": "user", "content": VOICE_MESSAGE_MARKER}]

    reply = gemini.generate_reply(
        "",
        conversation_messages=history_for_llm,
        lang_code="pt-BR",
        agenda_context="",
        audio_bytes=audio_bytes,
        audio_mime=audio_mime,
    )

    if gemini.is_gemini_error_reply(reply):
        return None, str(reply or "Erro ao chamar o Gemini.").strip()

    reply_clean = gemini.strip_agenda_markers_from_reply(reply).strip()
    if not reply_clean:
        return None, "Resposta vazia do assistente."

    mid_u = db.save_chat_message(supabase, user_id, "user", VOICE_MESSAGE_MARKER)
    mid_a = db.save_chat_message(supabase, user_id, "assistant", reply_clean)
    tok_n = gemini.count_tokens_approx(VOICE_MESSAGE_MARKER, reply_clean)
    db.add_tokens_used(supabase, user_id, tok_n, prof)
    prof = db.load_profile(supabase, user_id) or prof

    payload: dict = {
        "reply": reply_clean,
        "user_message_id": mid_u,
        "assistant_message_id": mid_a,
        "language": "pt-BR",
        "warnings": [],
        "reminders_saved": [],
        "agenda_saved": [],
        "shared_calendars_saved": [],
        "shared_events_saved": [],
        "shared_members_saved": [],
        "shared_calendars_deleted": [],
        "access": _safe_plan_access_payload(supabase, user_id, prof),
        "voice_engine": "gemini_fast",
    }

    if defer_tts and speak_reply:
        payload["tts_deferred"] = True
    elif speak_effective:
        from ego_api import tts

        resolved_voice = resolve_tts_voice(voice_id, avatar_id)
        mp3 = tts.synthesize_speech_mp3(reply_clean, resolved_voice, avatar_id)
        payload["tts_voice_id"] = resolved_voice
        if mp3:
            db.increment_daily_tts(supabase, user_id)
            payload["tts_audio_base64"] = base64.b64encode(mp3).decode("ascii")
            payload["tts_mime"] = "audio/mpeg"
        else:
            payload["tts_error"] = "Áudio indisponível no servidor."

    return payload, None
