from __future__ import annotations

import base64
import re
from typing import TYPE_CHECKING, Any

from ego_api import db, gemini
from ego_api.config import GEMINI_MODEL_FLASH, STRIPE_ANUAL_URL, STRIPE_MENSAL_URL
from ego_api.plans import (
    PLAN_CONNECTION,
    PLAN_ESSENTIAL,
    PLAN_PREMIUM,
    PLAN_TOTAL,
    plan_label,
    stripe_checkout_urls,
)
from ego_api.request_ctx import UserSession, get_session, set_session
from ego_api.supabase_client import apply_user_auth, create_anon_client

if TYPE_CHECKING:
    from ego_supabase import Client
else:
    Client = object  # noqa: A001


def normalize_email(raw: str) -> tuple[str, str | None]:
    email = (raw or "").strip()
    if not email or "@" not in email or email.startswith("@") or email.endswith("@"):
        return "", "Informe um e-mail válido."
    if len(email) > 254:
        return "", "E-mail demasiado longo (máx. 254)."
    return email, None


def format_auth_error(exc: BaseException) -> str:
    msg = str(exc).strip()
    low = msg.lower()
    if "already registered" in low or "user already exists" in low:
        return "Este e-mail já está cadastrado."
    if "invalid login" in low or "invalid credentials" in low:
        return "E-mail ou senha incorretos."
    return msg or "Erro de autenticação."


def _session_payload(res: object) -> dict[str, Any]:
    session = getattr(res, "session", None)
    user = getattr(res, "user", None)
    if not session or not user:
        return {}
    return {
        "access_token": str(getattr(session, "access_token", "") or ""),
        "refresh_token": str(getattr(session, "refresh_token", "") or ""),
        "expires_at": getattr(session, "expires_at", None),
        "user": {
            "id": str(getattr(user, "id", "") or ""),
            "email": str(getattr(user, "email", "") or ""),
        },
    }


def login(email: str, password: str) -> tuple[dict | None, str | None]:
    client = create_anon_client()
    if not client:
        return None, "Supabase não configurado (SUPABASE_URL / SUPABASE_KEY)."
    email_norm, err = normalize_email(email)
    if err:
        return None, err
    if not (password or "").strip():
        return None, "Informe a senha."
    try:
        res = client.auth.sign_in_with_password(
            {"email": email_norm, "password": password}
        )
        payload = _session_payload(res)
        if not payload.get("access_token"):
            return None, "Não foi possível autenticar."
        uid = payload["user"]["id"]
        set_session(
            UserSession(
                user_id=uid,
                email=email_norm,
                access_token=payload["access_token"],
                refresh_token=payload.get("refresh_token", ""),
            )
        )
        apply_user_auth(client)
        ensure_user_profile(client, uid, email=email_norm)
        touch_last_login(client, uid)
        return payload, None
    except Exception as e:  # noqa: BLE001
        return None, format_auth_error(e)


def signup(
    email: str, password: str, full_name: str = ""
) -> tuple[dict | None, str | None]:
    client = create_anon_client()
    if not client:
        return None, "Supabase não configurado."
    email_norm, err = normalize_email(email)
    if err:
        return None, err
    if not (password or "").strip():
        return None, "Informe a senha."
    display = (full_name or "").strip() or email_norm.split("@")[0] or "Usuário"
    try:
        res = client.auth.sign_up(
            {
                "email": email_norm,
                "password": password,
                "options": {"data": {"full_name": display, "country": "Brasil"}},
            }
        )
        payload = _session_payload(res)
        if not payload.get("access_token"):
            return {
                "message": "Conta criada. Confirme o e-mail se necessário e faça login.",
                "user": payload.get("user"),
            }, None
        uid = payload["user"]["id"]
        set_session(
            UserSession(
                user_id=uid,
                email=email_norm,
                access_token=payload["access_token"],
                refresh_token=payload.get("refresh_token", ""),
                user_name=display,
            )
        )
        apply_user_auth(client)
        ensure_user_profile(client, uid, email=email_norm, full_name=display)
        return payload, None
    except Exception as e:  # noqa: BLE001
        return None, format_auth_error(e)


def request_password_reset(email: str, redirect_to: str = "") -> tuple[bool, str | None]:
    """Envia e-mail de recuperação via Supabase Auth."""
    client = create_anon_client()
    if not client:
        return False, "Supabase não configurado."
    email_norm, err = normalize_email(email)
    if err:
        return False, err
    try:
        opts: dict[str, str] = {}
        if (redirect_to or "").strip():
            opts["redirect_to"] = redirect_to.strip()
        client.auth.reset_password_for_email(email_norm, opts)
        return True, None
    except Exception as e:  # noqa: BLE001
        return False, format_auth_error(e)


def refresh_session(refresh_token: str) -> tuple[dict | None, str | None]:
    client = create_anon_client()
    if not client:
        return None, "Supabase não configurado."
    if not (refresh_token or "").strip():
        return None, "refresh_token em falta."
    try:
        res = client.auth.refresh_session(refresh_token.strip())
        payload = _session_payload(res)
        if not payload.get("access_token"):
            return None, "Não foi possível renovar a sessão."
        return payload, None
    except Exception as e:  # noqa: BLE001
        return None, format_auth_error(e)


def ensure_user_profile(
    supabase: Client | None, user_id: str, *, email: str = "", full_name: str = ""
) -> tuple[bool, str]:
    return db.ensure_user_profile(supabase, user_id, email=email, full_name=full_name)


def touch_last_login(supabase: Client | None, user_id: str) -> None:
    db.touch_last_login(supabase, user_id)


def _daily_limit_message(supabase: Client | None, user_id: str) -> str:
    base = (
        "Limite diário atingido, assine um plano mensal para continuar usando "
        "ou espere até 00 horas para usar novamente."
    )
    try:
        _ok, status = db.check_access(supabase, user_id)
        m = re.search(r"(\d+)\s+dias?\s+restantes", str(status or ""), re.IGNORECASE)
        if m:
            return f"{base} Você ainda tem {int(m.group(1))} dias grátis."
    except Exception:
        pass
    return base


def process_chat_message(
    supabase: Client | None,
    user_id: str,
    message: str,
    *,
    audio_b64: str | None = None,
    audio_bytes: bytes | None = None,
    audio_mime: str | None = None,
    speak_reply: bool = False,
    client_history: list[dict] | None = None,
) -> tuple[dict | None, str | None]:
    sess = get_session()
    if not sess or sess.user_id != user_id:
        return None, "Sessão inválida."

    prof = db.refresh_test_total_quota(
        supabase, user_id, db.load_profile(supabase, user_id) or {}
    )
    tier, limits = db.user_plan_limits(prof)
    ok_access, status = db.check_access(supabase, user_id)
    if not ok_access:
        return None, f"Acesso expirado ({status})."

    ok_tok, msg_tok, used_tok, lim_tok = db.check_token_allowance(supabase, user_id, prof)
    if not ok_tok:
        return None, f"{msg_tok} Uso: {used_tok:,}/{lim_tok:,}."

    from ego_api.persona import apply_assistant_name_from_avatar, normalize_persona_pair

    stored_a, stored_v = db.load_persona(supabase, user_id)
    avatar_id, _voice_id = normalize_persona_pair(stored_a, stored_v)
    apply_assistant_name_from_avatar(avatar_id)

    user_display = (message or "").strip()
    from ego_api.audio_b64 import decode_audio_base64, normalize_audio_mime

    if audio_bytes is None and audio_b64:
        audio_bytes = decode_audio_base64(audio_b64)

    if audio_bytes:
        if len(audio_bytes) < 128:
            return None, "Gravação demasiado curta. Fale pelo menos 1 segundo."
        audio_mime = normalize_audio_mime(audio_mime, audio_bytes)
        if not user_display:
            from ego_api.db import VOICE_MESSAGE_MARKER

            user_display = VOICE_MESSAGE_MARKER
    elif audio_b64:
        return None, (
            "Áudio inválido. Grave de novo: microfone → fale 2–3 s → Enviar voz."
        )

    if not user_display and not audio_bytes:
        return None, (
            "Áudio não chegou ao servidor. Reinicie python flask_api.py, "
            "recarregue o browser (Ctrl+Shift+R) e grave 2–3 segundos antes de enviar."
        )

    is_voice_msg = bool(audio_bytes)
    if is_voice_msg:
        ok_voice, _voice_used = db.daily_voice_messages_ok(
            supabase, user_id, limits, prof
        )
        if not ok_voice:
            return None, _daily_limit_message(supabase, user_id)
    else:
        ok_txt, _txt_used = db.daily_text_messages_ok(supabase, user_id, limits, prof)
        if not ok_txt:
            return None, _daily_limit_message(supabase, user_id)

    if speak_reply:
        ok_tts, _tts_used = db.daily_tts_ok(supabase, user_id, limits, prof)
        if not ok_tts:
            return None, _daily_limit_message(supabase, user_id)

    from ego_api.chat_local import local_history_active, parse_client_history
    from ego_api.config import chat_local_history_enabled

    use_local = local_history_active(client_history)
    if use_local:
        history = parse_client_history(client_history)
    else:
        history = db.load_chat_history(supabase, user_id)
    cap = limits.chat_llm_max_turns
    if cap > 0 and len(history) > cap:
        history = history[-cap:]
    if is_voice_msg:
        lang = "pt-BR"
    else:
        lang, _conf = gemini.detect_language(user_display)
    history_for_llm = [*history, {"role": "user", "content": user_display}]

    # Voz: sem agenda no prompt (acelera o Gemini com áudio).
    agenda_ctx = (
        "" if is_voice_msg else db.build_agenda_context_for_llm(supabase, user_id)
    )
    reply = gemini.generate_reply(
        user_display if not audio_bytes else "",
        conversation_messages=history_for_llm,
        lang_code=lang,
        agenda_context=agenda_ctx,
        audio_bytes=audio_bytes,
        audio_mime=audio_mime,
    )

    if gemini.is_gemini_error_reply(reply):
        return None, str(reply or "Erro ao chamar o Gemini.").strip()
    if is_voice_msg and reply.strip().startswith("A IA demorou demais"):
        return None, reply.strip()

    import uuid

    local_ids = use_local or chat_local_history_enabled()
    mid_u: str | None
    if local_ids:
        mid_u = str(uuid.uuid4())
    else:
        mid_u = db.save_chat_message(supabase, user_id, "user", user_display)

    warnings: list[str] = []
    reminders_saved: list[dict] = []
    agenda_saved: list[dict] = []

    reply_clean, rem_items = gemini.extract_reminders(reply)
    rem_cap = enforce_reminder_limit(supabase, user_id, prof)
    for it in rem_items:
        if rem_cap:
            warnings.append(rem_cap)
            break
        ok, err, row = db.insert_reminder(
            supabase,
            user_id,
            title=str(it.get("title") or "Lembrete"),
            scheduled_at=it.get("scheduled_at"),
            announce=str(it.get("announce") or it.get("title") or ""),
        )
        if ok and row:
            reminders_saved.append(row)
        elif err:
            warnings.append(f"Lembrete: {err}")

    reply_clean, ag_items = gemini.extract_agenda_markers(reply_clean)
    ag_cap = enforce_agenda_limit(supabase, user_id, prof)
    for it in ag_items:
        if ag_cap:
            warnings.append(ag_cap)
            break
        ok, err, row = db.insert_agenda(
            supabase,
            user_id,
            titulo=str(it.get("titulo") or it.get("title") or ""),
            horario=it.get("horario") or it.get("time"),
            dias_da_semana=str(
                it.get("dias_da_semana") or it.get("dias") or it.get("weekdays") or ""
            ),
        )
        if ok and row:
            agenda_saved.append(row)
        elif err:
            warnings.append(f"Agenda: {err}")

    if local_ids:
        mid_a = str(uuid.uuid4())
        db.increment_daily_message_usage(supabase, user_id, is_voice=is_voice_msg)
    else:
        mid_a = db.save_chat_message(supabase, user_id, "assistant", reply_clean)
    tok_n = gemini.count_tokens_approx(user_display, reply_clean)
    db.add_tokens_used(supabase, user_id, tok_n, prof)

    payload: dict = {
        "reply": reply_clean,
        "user_message_id": mid_u,
        "assistant_message_id": mid_a,
        "language": lang,
        "warnings": warnings,
        "reminders_saved": reminders_saved,
        "agenda_saved": agenda_saved,
        "chat_local_history": local_ids,
    }
    if speak_reply and reply_clean.strip():
        from ego_api.config import chat_defer_tts_on_voice
        from ego_api.persona import resolve_tts_voice

        avatar_id, voice_id = ensure_persona_normalized(supabase, user_id)
        resolved_voice = resolve_tts_voice(voice_id, avatar_id)
        payload["tts_voice_id"] = resolved_voice

        # Voz no Gemini já demora; TTS na mesma requisição estoura 120s no Railway.
        defer_tts = is_voice_msg and chat_defer_tts_on_voice()
        if defer_tts:
            payload["tts_deferred"] = True
        else:
            from ego_api import tts

            mp3 = tts.synthesize_speech_mp3(reply_clean, resolved_voice, avatar_id)
            if mp3:
                import base64

                db.increment_daily_tts(supabase, user_id)
                payload["tts_audio_base64"] = base64.b64encode(mp3).decode("ascii")
                payload["tts_mime"] = "audio/mpeg"
            else:
                payload["tts_error"] = (
                    "Áudio indisponível. No servidor: pip install edge-tts"
                )

    return payload, None


def process_realtime_voice_turn(
    supabase: Client | None,
    user_id: str,
    *,
    user_message: str,
    assistant_reply: str,
    speak_reply: bool = False,
    client_history: list[dict] | None = None,
) -> tuple[dict | None, str | None]:
    """Persiste turno de voz feito via OpenAI Realtime (sem Gemini)."""
    sess = get_session()
    if not sess or sess.user_id != user_id:
        return None, "Sessão inválida."

    prof = db.refresh_test_total_quota(
        supabase, user_id, db.load_profile(supabase, user_id) or {}
    )
    tier, limits = db.user_plan_limits(prof)
    ok_access, status = db.check_access(supabase, user_id)
    if not ok_access:
        return None, f"Acesso expirado ({status})."

    ok_tok, msg_tok, used_tok, lim_tok = db.check_token_allowance(supabase, user_id, prof)
    if not ok_tok:
        return None, f"{msg_tok} Uso: {used_tok:,}/{lim_tok:,}."

    ok_voice, _voice_used = db.daily_voice_messages_ok(supabase, user_id, limits, prof)
    if not ok_voice:
        return None, _daily_limit_message(supabase, user_id)

    if speak_reply:
        ok_tts, _tts_used = db.daily_tts_ok(supabase, user_id, limits, prof)
        if not ok_tts:
            return None, _daily_limit_message(supabase, user_id)

    from ego_api.db import VOICE_MESSAGE_MARKER

    user_display = (user_message or "").strip()
    if not user_display:
        user_display = VOICE_MESSAGE_MARKER

    reply = (assistant_reply or "").strip()
    if not reply:
        return None, "Resposta vazia do assistente de voz."

    from ego_api.chat_local import local_history_active, parse_client_history
    from ego_api.config import chat_local_history_enabled

    use_local = local_history_active(client_history)
    lang = "pt-BR"

    import uuid

    local_ids = use_local or chat_local_history_enabled()
    if local_ids:
        mid_u = str(uuid.uuid4())
    else:
        mid_u = db.save_chat_message(supabase, user_id, "user", user_display)

    warnings: list[str] = []
    reminders_saved: list[dict] = []
    agenda_saved: list[dict] = []

    reply_clean, rem_items = gemini.extract_reminders(reply)
    rem_cap = enforce_reminder_limit(supabase, user_id, prof)
    for it in rem_items:
        if rem_cap:
            warnings.append(rem_cap)
            break
        ok, err, row = db.insert_reminder(
            supabase,
            user_id,
            title=str(it.get("title") or "Lembrete"),
            scheduled_at=it.get("scheduled_at"),
            announce=str(it.get("announce") or it.get("title") or ""),
        )
        if ok and row:
            reminders_saved.append(row)
        elif err:
            warnings.append(f"Lembrete: {err}")

    reply_clean, ag_items = gemini.extract_agenda_markers(reply_clean)
    ag_cap = enforce_agenda_limit(supabase, user_id, prof)
    for it in ag_items:
        if ag_cap:
            warnings.append(ag_cap)
            break
        ok, err, row = db.insert_agenda(
            supabase,
            user_id,
            titulo=str(it.get("titulo") or it.get("title") or ""),
            horario=it.get("horario") or it.get("time"),
            dias_da_semana=str(
                it.get("dias_da_semana") or it.get("dias") or it.get("weekdays") or ""
            ),
        )
        if ok and row:
            agenda_saved.append(row)
        elif err:
            warnings.append(f"Agenda: {err}")

    if local_ids:
        mid_a = str(uuid.uuid4())
        db.increment_daily_message_usage(supabase, user_id, is_voice=True)
    else:
        mid_a = db.save_chat_message(supabase, user_id, "assistant", reply_clean)
    tok_n = gemini.count_tokens_approx(user_display, reply_clean)
    db.add_tokens_used(supabase, user_id, tok_n, prof)

    payload: dict = {
        "reply": reply_clean,
        "user_message_id": mid_u,
        "assistant_message_id": mid_a,
        "language": lang,
        "warnings": warnings,
        "reminders_saved": reminders_saved,
        "agenda_saved": agenda_saved,
        "chat_local_history": local_ids,
        "voice_engine": "openai_realtime",
    }
    if user_display and user_display != VOICE_MESSAGE_MARKER:
        payload["user_transcript"] = user_display

    if speak_reply and reply_clean.strip():
        from ego_api.config import chat_defer_tts_on_voice
        from ego_api.persona import resolve_tts_voice

        avatar_id, voice_id = ensure_persona_normalized(supabase, user_id)
        resolved_voice = resolve_tts_voice(voice_id, avatar_id)
        payload["tts_voice_id"] = resolved_voice
        if chat_defer_tts_on_voice():
            payload["tts_deferred"] = True
        else:
            from ego_api import tts

            mp3 = tts.synthesize_speech_mp3(reply_clean, resolved_voice, avatar_id)
            if mp3:
                import base64

                db.increment_daily_tts(supabase, user_id)
                payload["tts_audio_base64"] = base64.b64encode(mp3).decode("ascii")
                payload["tts_mime"] = "audio/mpeg"
            else:
                payload["tts_error"] = (
                    "Áudio indisponível. No servidor: pip install edge-tts"
                )

    return payload, None


def enforce_agenda_limit(
    supabase: Client | None, user_id: str, profile: dict | None = None
) -> str | None:
    prof = profile if profile is not None else (db.load_profile(supabase, user_id) or {})
    _, limits = db.user_plan_limits(prof)
    ok, n = db.agenda_limit_ok(supabase, user_id, limits)
    if ok:
        return None
    return (
        f"Limite de hábitos na agenda ({n}/{limits.max_agenda_items}). "
        f"Faça upgrade do plano."
    )


def enforce_reminder_limit(
    supabase: Client | None, user_id: str, profile: dict | None = None
) -> str | None:
    prof = profile if profile is not None else (db.load_profile(supabase, user_id) or {})
    _, limits = db.user_plan_limits(prof)
    ok, n = db.reminders_limit_ok(supabase, user_id, limits)
    if ok:
        return None
    return (
        f"Limite de lembretes ({n}/{limits.max_reminders}). "
        f"Faça upgrade do plano."
    )


def enforce_tts_limit(
    supabase: Client | None, user_id: str, profile: dict | None = None
) -> str | None:
    prof = profile if profile is not None else (db.load_profile(supabase, user_id) or {})
    _, limits = db.user_plan_limits(prof)
    ok, used = db.daily_tts_ok(supabase, user_id, limits, prof)
    if ok:
        return None
    return (
        f"Limite diário de áudio atingido ({used}/{limits.daily_tts_replies}). "
        f"Faça upgrade do plano."
    )


def bootstrap_payload(supabase: Client | None, user_id: str) -> dict:
    """Um único payload para o painel (evita vários GET no cliente)."""
    from ego_api.config import (
        chat_local_history_enabled,
        gemini_api_key,
        openai_realtime_enabled,
        supabase_anon_key,
        supabase_url,
    )
    from ego_api import openai_realtime

    access = db.build_plan_access_payload(supabase, user_id)
    local = chat_local_history_enabled()
    messages = [] if local else db.load_chat_history(supabase, user_id)
    return {
        "health": {
            "ok": True,
            "service": "ego-ai-api",
            "supabase_configured": bool(supabase_url() and supabase_anon_key()),
            "gemini_configured": bool(gemini_api_key()),
            "openai_realtime_configured": openai_realtime.is_available(),
        },
        "me": me_payload(supabase, user_id),
        "access": {"ok": True, **access},
        "reminders": db.list_reminders(supabase, user_id),
        "agenda": db.list_agenda(supabase, user_id),
        "messages": messages,
        "chat_local_history": local,
    }


def ensure_persona_normalized(supabase: Client | None, user_id: str) -> tuple[str, str]:
    """Garante par avatar/voz coerente no Supabase (ex.: Leo m1 + vm1)."""
    from ego_api.persona import normalize_persona_pair

    stored_a, stored_v = db.load_persona(supabase, user_id)
    avatar_id, voice_id = normalize_persona_pair(stored_a, stored_v)
    if db.persona_is_configured(supabase, user_id) and (
        stored_a != avatar_id or stored_v != voice_id
    ):
        db.save_persona(supabase, user_id, avatar_id, voice_id)
    return avatar_id, voice_id


def me_payload(supabase: Client | None, user_id: str) -> dict:
    prof = db.load_profile(supabase, user_id) or {}
    sess = get_session()
    email = (sess.email if sess else None) or str(prof.get("email") or "")
    email_local = email.split("@")[0].strip().lower() if "@" in email else ""
    prof_full_name = str(prof.get("full_name") or "").strip()
    prof_name_is_email_alias = bool(
        prof_full_name and email_local and prof_full_name.lower() == email_local
    )
    if sess and sess.user_name and (not prof_full_name or prof_name_is_email_alias):
        prof = dict(prof)
        prof["full_name"] = sess.user_name
    elif prof_name_is_email_alias:
        prof = dict(prof)
        prof["full_name"] = ""
    configured = db.persona_is_configured(supabase, user_id)
    avatar_id, voice_id = ensure_persona_normalized(supabase, user_id)
    ok_access, status = db.check_access(supabase, user_id)
    return {
        "user_id": user_id,
        "email": email or prof.get("email"),
        "profile": prof,
        "persona_configured": configured,
        "persona": {"avatar_id": avatar_id, "voice_id": voice_id},
        "access": {"allowed": ok_access, "status": status},
        "stripe_checkout": _stripe_checkout_payload(user_id),
    }


def _stripe_checkout_payload(user_id: str) -> dict:
    urls = stripe_checkout_urls()
    legacy_m = _stripe_link(STRIPE_MENSAL_URL, user_id)
    legacy_a = _stripe_link(STRIPE_ANUAL_URL, user_id)
    connection = _stripe_link(urls.get(PLAN_CONNECTION) or "", user_id) or legacy_m
    int_connection = _stripe_link(urls.get("int_connection") or "", user_id)
    return {
        "monthly_url": connection,
        "annual_url": legacy_a,
        "connection_url": connection,
        "premium_url": _stripe_link(urls.get(PLAN_PREMIUM) or "", user_id),
        "total_url": _stripe_link(urls.get(PLAN_TOTAL) or "", user_id),
        "int_connection_url": int_connection,
        "int_premium_url": _stripe_link(urls.get("int_premium") or "", user_id),
        "int_premium_annual_url": _stripe_link(
            urls.get("int_premium_annual") or "", user_id
        ),
        "int_total_url": _stripe_link(urls.get("int_total") or "", user_id),
        "int_total_annual_url": _stripe_link(
            urls.get("int_total_annual") or "", user_id
        ),
        "essential": None,
    }


def _stripe_link(base: str, user_id: str) -> str | None:
    base = (base or "").strip()
    if not base or "COLOQUE" in base.upper() or "URL_DO" in base.upper():
        return None
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}client_reference_id={user_id}"


def ui_state_from_profile(prof: dict | None) -> dict:
    if not prof:
        return {}
    raw = prof.get("ui_state")
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            import json

            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def persist_pdf_context(
    supabase: Client | None, user_id: str, pdf_context: str, profile: dict | None = None
) -> tuple[str, bool]:
    """Guarda texto de PDF em profiles.ui_state (sincroniza com Streamlit e app)."""
    from ego_api.pdf_extract import cap_pdf_context_for_profile

    capped, truncated = cap_pdf_context_for_profile(pdf_context)
    if not supabase or not user_id:
        return capped, truncated
    ui = ui_state_from_profile(profile)
    if ui.get("pdf_context") == capped:
        return capped, truncated
    merged = dict(ui)
    merged["pdf_context"] = capped
    merged["pdf_truncated"] = truncated
    db.update_profile_fields(supabase, user_id, {"ui_state": merged})
    sess = get_session()
    if sess:
        sess.pdf_context = capped
    return capped, truncated


def persist_assistant_name_for_persona(
    supabase: Client | None,
    user_id: str,
    profile: dict | None,
    avatar_id: str,
) -> str:
    """Sincroniza nome do assistente (Leo/Luna/…) na sessão e em profiles.ui_state."""
    from ego_api.persona import apply_assistant_name_from_avatar

    name = apply_assistant_name_from_avatar(avatar_id)
    if not supabase or not user_id:
        return name
    ui = ui_state_from_profile(profile)
    if ui.get("ego_assistant_display_name") == name:
        return name
    merged = dict(ui)
    merged["ego_assistant_display_name"] = name
    db.update_profile_fields(supabase, user_id, {"ui_state": merged})
    return name
