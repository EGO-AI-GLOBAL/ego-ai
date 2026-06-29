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
    email = (raw or "").strip().lower()
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
    if "expired" in low or "invalid jwt" in low or "token is invalid" in low:
        return "Link expirado ou inválido. Peça um novo e-mail em Esqueci a senha."
    if "password should be at least" in low or "weak password" in low:
        return "A senha deve ter pelo menos 6 caracteres."
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


def _signup_user_id(res: object) -> str:
    payload = _session_payload(res)
    uid = str((payload.get("user") or {}).get("id") or "")
    if uid:
        return uid
    user = getattr(res, "user", None)
    if user:
        return str(getattr(user, "id", "") or "")
    return ""


def _apply_referral_after_signup(user_id: str, referral_code: str) -> str | None:
    code = (referral_code or "").strip()
    if not user_id or not code:
        return None
    from ego_api.referrals import attach_referral_to_profile
    from ego_api.supabase_client import create_service_client

    svc = create_service_client()
    if not svc:
        return "Indicação indisponível no momento. Tente novamente."
    ok, err = attach_referral_to_profile(svc, user_id, code)
    if not ok and err:
        return err
    return None


def signup(
    email: str,
    password: str,
    full_name: str = "",
    phone: str = "",
    referral_code: str = "",
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
    from ego_api.phone_utils import normalize_phone_br

    phone_norm, phone_err = normalize_phone_br(phone)
    if phone_err:
        return None, phone_err
    if not phone_norm:
        return None, "Informe o telefone com DDD."

    from ego_api.shared_calendars import resolve_user_id_by_email, resolve_user_id_by_phone

    if resolve_user_id_by_email(email_norm):
        return None, "Este e-mail já está cadastrado."
    if resolve_user_id_by_phone(phone_norm):
        return None, "Este telefone já está cadastrado."

    try:
        res = client.auth.sign_up(
            {
                "email": email_norm,
                "password": password,
                "options": {"data": {"full_name": display, "country": "Brasil"}},
            }
        )
        payload = _session_payload(res)
        uid = _signup_user_id(res)
        if not payload.get("access_token"):
            if uid:
                from ego_api.supabase_client import create_service_client

                profile_client = create_service_client() or client
                ok, prof_err = ensure_user_profile(
                    profile_client,
                    uid,
                    email=email_norm,
                    full_name=display,
                    phone=phone_norm,
                )
                if not ok:
                    return None, prof_err or "Não foi possível criar o perfil."
                ref_err = _apply_referral_after_signup(uid, referral_code)
                if ref_err:
                    return None, ref_err
                from ego_api.signup_emails import queue_welcome_email

                queue_welcome_email(uid, email_norm, display)
            user_obj = payload.get("user")
            if not user_obj and uid:
                user_obj = {"id": uid, "email": email_norm}
            return {
                "message": "Conta criada. Confirme o e-mail se necessário e faça login.",
                "user": user_obj,
            }, None
        if not uid:
            return None, "Não foi possível criar a conta."
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
        ok, prof_err = ensure_user_profile(
            client, uid, email=email_norm, full_name=display, phone=phone_norm
        )
        if not ok:
            return None, prof_err or "Não foi possível criar o perfil."
        ref_err = _apply_referral_after_signup(uid, referral_code)
        if ref_err:
            return None, ref_err
        from ego_api import shared_calendars as sc

        sc.link_shared_memberships_for_user(client, uid, email_norm, source="signup")
        if phone_norm:
            sc.link_shared_memberships_for_user_phone(
                client, uid, phone_norm, source="signup"
            )
        from ego_api.signup_emails import queue_welcome_email

        queue_welcome_email(uid, email_norm, display)
        return payload, None
    except Exception as e:  # noqa: BLE001
        return None, format_auth_error(e)


def request_password_reset(email: str, redirect_to: str = "") -> tuple[bool, str | None]:
    """Envia e-mail de recuperação via Supabase Auth."""
    from ego_api.auth_reset import password_reset_redirect_url

    client = create_anon_client()
    if not client:
        return False, "Supabase não configurado."
    email_norm, err = normalize_email(email)
    if err:
        return False, err
    try:
        target = (redirect_to or "").strip() or password_reset_redirect_url()
        client.auth.reset_password_for_email(email_norm, {"redirect_to": target})
        return True, None
    except Exception as e:  # noqa: BLE001
        return False, format_auth_error(e)


def complete_password_reset(
    access_token: str, refresh_token: str, password: str
) -> tuple[dict | None, str | None]:
    """Define nova senha com tokens do link de recuperação (Supabase)."""
    client = create_anon_client()
    if not client:
        return None, "Supabase não configurado."
    at = (access_token or "").strip()
    rt = (refresh_token or "").strip()
    if not at or not rt:
        return None, "Link inválido ou incompleto. Peça um novo e-mail."
    if not (password or "").strip():
        return None, "Informe a senha."
    if len(password.strip()) < 6:
        return None, "A senha deve ter pelo menos 6 caracteres."
    try:
        client.auth.set_session(at, rt)
        res = client.auth.update_user({"password": password.strip()})
        session = getattr(res, "session", None)
        user = getattr(res, "user", None) or getattr(session, "user", None)
        if session and user:
            payload = {
                "access_token": str(getattr(session, "access_token", "") or at),
                "refresh_token": str(getattr(session, "refresh_token", "") or rt),
                "expires_at": getattr(session, "expires_at", None),
                "user": {
                    "id": str(getattr(user, "id", "") or ""),
                    "email": str(getattr(user, "email", "") or ""),
                },
            }
        else:
            sess = client.auth.get_session()
            session = getattr(sess, "session", None) if sess else None
            user = getattr(sess, "user", None) if sess else None
            payload = _session_payload(
                type("_R", (), {"session": session, "user": user})()
            )
        if not payload.get("access_token"):
            return None, "Não foi possível confirmar a nova senha."
        return payload, None
    except Exception as e:  # noqa: BLE001
        return None, format_auth_error(e)


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
    supabase: Client | None,
    user_id: str,
    *,
    email: str = "",
    full_name: str = "",
    phone: str = "",
) -> tuple[bool, str]:
    return db.ensure_user_profile(
        supabase, user_id, email=email, full_name=full_name, phone=phone
    )


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


def _is_casual_chat_message(text: str) -> bool:
    """Mensagens curtas sem agenda — resposta mais rápida (menos DB/parsing)."""
    t = (text or "").strip().lower()
    if not t or len(t) > 100:
        return False
    keys = (
        "agenda",
        "marcar",
        "reuni",
        "lembr",
        "convid",
        "compromis",
        "calend",
        "compartilh",
        "evento",
        "stripe",
        "plano",
        "pdf",
    )
    return not any(k in t for k in keys)


def _history_from_client(client_history: list | None) -> list[dict[str, str]]:
    if not client_history:
        return []
    out: list[dict[str, str]] = []
    for item in client_history:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = str(item.get("content") or "").strip()
        if role not in ("user", "assistant") or not content or content == "…":
            continue
        out.append({"role": role, "content": content[:8000]})
    return out[-16:]


def _access_expired_message(supabase: Client | None, user_id: str) -> str:
    """Mensagem de paywall com contexto de progresso (streak/jornada)."""
    from ego_api import daily_care, streaks, wellness_journey

    parts = ["Seu teste grátis de 20 dias terminou."]
    try:
        st = streaks.get_streak(supabase, user_id)
        days = int(st.get("current") or 0)
        if days > 0:
            parts.append(f"Você tinha {days} dias de cuidado seguidos.")
    except Exception:
        pass
    try:
        care = daily_care.get_daily_care(supabase, user_id)
        cd = int(care.get("current") or 0)
        if cd > 0:
            parts.append(f"Monstrinhos do Humor: {cd} dias.")
    except Exception:
        pass
    try:
        prof = db.load_profile(supabase, user_id) or {}
        tier, _ = db.user_plan_limits(prof)
        j = wellness_journey.get_journey(supabase, user_id, plan_tier=tier)
        lv = int(j.get("level") or 0)
        if lv > 1:
            parts.append(
                f"🥚 Seu EGO de Bolso está no nível {lv}/{j.get('max_level', 500)} — não perca seu bichinho."
            )
    except Exception:
        pass
    parts.append("Assine um plano para continuar.")
    return " ".join(parts)


def process_chat_message(
    supabase: Client | None,
    user_id: str,
    message: str,
    *,
    audio_b64: str | None = None,
    audio_bytes: bytes | None = None,
    audio_mime: str | None = None,
    speak_reply: bool = False,
    client_history: list | None = None,
) -> tuple[dict | None, str | None]:
    sess = get_session()
    if not sess or sess.user_id != user_id:
        return None, "Sessão inválida."

    prof = db.load_profile(supabase, user_id) or {}
    tier, limits = db.user_plan_limits(prof)
    ok_access, status = db.check_access(supabase, user_id)
    if not ok_access:
        return None, _access_expired_message(supabase, user_id)

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
            from ego_api import gemini as gmi
            from ego_api.db import VOICE_MESSAGE_MARKER

            transcript = gmi.transcribe_voice_audio(audio_bytes, audio_mime)
            user_display = (transcript or "").strip() or VOICE_MESSAGE_MARKER
    elif audio_b64:
        return None, (
            "Áudio inválido. Fale 2–3 segundos, toque na seta para enviar e tente outra vez."
        )

    if not user_display and not audio_bytes:
        return None, (
            "Não recebemos o áudio. Toque no microfone, fale 3 segundos e toque na seta ↑."
        )

    is_voice_msg = bool(audio_bytes)
    if is_voice_msg:
        ok_voice, _voice_used = db.daily_voice_messages_ok(supabase, user_id, limits)
        if not ok_voice:
            return None, _daily_limit_message(supabase, user_id)
    else:
        ok_txt, _txt_used = db.daily_text_messages_ok(supabase, user_id, limits)
        if not ok_txt:
            return None, _daily_limit_message(supabase, user_id)

    # Não bloquear mensagem de voz/texto por limite TTS — o áudio da resposta é opcional.
    speak_reply_effective = False
    if speak_reply:
        ok_tts, _tts_used = db.daily_tts_ok(supabase, user_id, limits, prof)
        speak_reply_effective = ok_tts

    casual = _is_casual_chat_message(user_display) and not audio_bytes
    client_hist = _history_from_client(client_history)
    if client_hist:
        history = client_hist
    else:
        history = db.load_chat_history(supabase, user_id, limit=16)
    lang = "pt-BR"
    history_for_llm = [*history, {"role": "user", "content": user_display}]

    from ego_api import chat_schedule as cs
    from ego_api.config import chat_agenda_actions_enabled

    chat_agenda = chat_agenda_actions_enabled()

    schedule = cs.load_chat_schedule(prof)
    from ego_api.schedule_tz import local_now_from_session

    schedule_ref = local_now_from_session(sess)
    from ego_api.db import VOICE_MESSAGE_MARKER

    voice_transcript = (
        user_display if is_voice_msg and user_display != VOICE_MESSAGE_MARKER else ""
    )
    schedule_text = cs.user_text_for_schedule_actions(
        user_display,
        is_voice=is_voice_msg,
        voice_marker=VOICE_MESSAGE_MARKER,
    )

    if chat_agenda and schedule_text and cs.should_clear_stale_schedule_wizard(
        schedule_text, schedule, supabase, user_id
    ):
        schedule = {"step": "", "draft": {}}

    def _save_personal_reminder_fast(
        rem: dict,
    ) -> tuple[dict | None, str | None]:
        from ego_api.schedule_tz import format_scheduled_for_user

        rem_cap = enforce_reminder_limit(supabase, user_id, prof)
        if rem_cap:
            return None, rem_cap
        ok, err, row = db.insert_reminder(
            supabase,
            user_id,
            title=str(rem.get("title") or "Compromisso"),
            scheduled_at=rem.get("scheduled_at"),
            announce=str(rem.get("announce") or rem.get("title") or ""),
        )
        if ok and row:
            title = (row.get("title") or row.get("announce") or "Compromisso").strip()
            when = format_scheduled_for_user(row.get("scheduled_at"))
            return row, f"Pronto! Agendei «{title}»{when} na agenda pessoal."
        return None, (
            f"Não consegui agendar: {err or 'tente de novo'}. "
            "Ex.: «marca na agenda pessoal consulta amanhã às 9h»."
        )

    # Completar «pessoal ou família?» ou «qual hora?» (voz ou texto).
    if chat_agenda and schedule_text and schedule.get("step") == "choose_scope":
        schedule, time_hint = cs.absorb_scope_choice_reply(
            schedule, schedule_text, supabase, user_id, schedule_ref
        )
        if time_hint:
            mid_u = db.save_chat_message(supabase, user_id, "user", user_display)
            cs.save_chat_schedule(supabase, user_id, prof, schedule)
            mid_a = db.save_chat_message(supabase, user_id, "assistant", time_hint)
            return {
                "reply": time_hint,
                "user_message_id": mid_u,
                "assistant_message_id": mid_a,
                "user_transcript": voice_transcript or None,
                "language": lang,
                "warnings": [],
                "reminders_saved": [],
                "agenda_saved": [],
                "shared_calendars_saved": [],
                "shared_events_saved": [],
                "shared_members_saved": [],
                "shared_calendars_deleted": [],
                "access": db.build_plan_access_payload(supabase, user_id, prof),
            }, None
        pending_rem = cs.try_save_personal_from_schedule_draft(
            schedule, schedule_text, schedule_ref
        )
        if pending_rem:
            row, reply_fast = _save_personal_reminder_fast(pending_rem)
            mid_u = db.save_chat_message(supabase, user_id, "user", user_display)
            cs.save_chat_schedule(supabase, user_id, prof, None)
            mid_a = db.save_chat_message(supabase, user_id, "assistant", reply_fast or "")
            prof = db.load_profile(supabase, user_id) or prof
            return {
                "reply": reply_fast or "",
                "user_message_id": mid_u,
                "assistant_message_id": mid_a,
                "user_transcript": voice_transcript or None,
                "language": lang,
                "warnings": [],
                "reminders_saved": [row] if row else [],
                "agenda_saved": [],
                "shared_calendars_saved": [],
                "shared_events_saved": [],
                "shared_members_saved": [],
                "shared_calendars_deleted": [],
                "access": db.build_plan_access_payload(supabase, user_id, prof),
            }, None

    if chat_agenda and schedule_text and schedule.get("step") in (
        "collect_personal",
        "collect_shared",
    ):
        merged = cs.complete_collect_schedule_step(
            schedule, schedule_text, schedule_ref
        )
        if merged:
            schedule = merged
            pending_rem = cs.try_save_personal_from_schedule_draft(
                schedule, schedule_text, schedule_ref
            )
            if pending_rem:
                row, reply_fast = _save_personal_reminder_fast(pending_rem)
                mid_u = db.save_chat_message(supabase, user_id, "user", user_display)
                cs.save_chat_schedule(supabase, user_id, prof, None)
                mid_a = db.save_chat_message(
                    supabase, user_id, "assistant", reply_fast or ""
                )
                prof = db.load_profile(supabase, user_id) or prof
                return {
                    "reply": reply_fast or "",
                    "user_message_id": mid_u,
                    "assistant_message_id": mid_a,
                    "user_transcript": voice_transcript or None,
                    "language": lang,
                    "warnings": [],
                    "reminders_saved": [row] if row else [],
                    "agenda_saved": [],
                    "shared_calendars_saved": [],
                    "shared_events_saved": [],
                    "shared_members_saved": [],
                    "shared_calendars_deleted": [],
                    "access": db.build_plan_access_payload(supabase, user_id, prof),
                }, None

    # Apagar/cancelar compromisso por comando (texto ou voz transcrita).
    if chat_agenda and not casual and cs.looks_like_dismiss_commitment_intent(user_display):
        rem_d, ev_d, hab_d, dismiss_warns = cs.process_dismiss_commitments(
            supabase, user_id, user_display, ref=schedule_ref
        )
        from ego_api.chat_reply import build_dismiss_confirmation_reply

        reply_dismiss = build_dismiss_confirmation_reply(
            dismissed_reminders=rem_d,
            dismissed_events=ev_d,
            dismissed_habits=hab_d,
            warnings=dismiss_warns,
        )
        mid_u = db.save_chat_message(supabase, user_id, "user", user_display)
        mid_a = db.save_chat_message(supabase, user_id, "assistant", reply_dismiss)
        prof = db.load_profile(supabase, user_id) or prof
        return {
            "reply": reply_dismiss,
            "user_message_id": mid_u,
            "assistant_message_id": mid_a,
            "user_transcript": voice_transcript or None,
            "language": lang,
            "warnings": dismiss_warns,
            "reminders_saved": [],
            "reminders_dismissed": rem_d,
            "agenda_deleted": hab_d,
            "agenda_saved": [],
            "shared_calendars_saved": [],
            "shared_events_saved": [],
            "shared_events_dismissed": ev_d,
            "shared_members_saved": [],
            "shared_calendars_deleted": [],
            "access": db.build_plan_access_payload(supabase, user_id, prof),
        }, None

    # Agenda pessoal clara (ex.: «marca na agenda pessoal … às 9h»): grava sem LLM (texto ou voz).
    if chat_agenda and not casual and schedule_text and cs.looks_like_schedule_intent(
        schedule_text
    ):
        personal_scope = cs.detect_scope_from_user_text(
            schedule_text, supabase, user_id
        ) == "personal" or cs.only_personal_schedule_available(
            supabase, user_id
        )
        if personal_scope and not cs.schedule_scope_is_ambiguous(
            schedule_text, supabase, user_id
        ):
            if not cs.user_message_has_schedule_time(schedule_text):
                hint = (
                    "Qual horário? Ex.: «marca na agenda pessoal atendimento "
                    "amanhã às 9h»."
                )
                mid_u = db.save_chat_message(supabase, user_id, "user", user_display)
                mid_a = db.save_chat_message(supabase, user_id, "assistant", hint)
                return {
                    "reply": hint,
                    "user_message_id": mid_u,
                    "assistant_message_id": mid_a,
                    "language": lang,
                    "warnings": [],
                    "reminders_saved": [],
                    "agenda_saved": [],
                    "shared_calendars_saved": [],
                    "shared_events_saved": [],
                    "shared_members_saved": [],
                    "shared_calendars_deleted": [],
                    "access": db.build_plan_access_payload(supabase, user_id, prof),
                }, None
            personal_rem = cs.parse_personal_reminder_request(
                schedule_text,
                schedule_ref,
                implicit_personal=cs.only_personal_schedule_available(
                    supabase, user_id
                ),
            )
            if personal_rem:
                from ego_api.schedule_tz import format_scheduled_for_user

                rem_cap = enforce_reminder_limit(supabase, user_id, prof)
                reminders_saved: list[dict] = []
                reply_fast = ""
                if rem_cap:
                    reply_fast = rem_cap
                else:
                    ok, err, row = db.insert_reminder(
                        supabase,
                        user_id,
                        title=str(personal_rem.get("title") or "Compromisso"),
                        scheduled_at=personal_rem.get("scheduled_at"),
                        announce=str(
                            personal_rem.get("announce")
                            or personal_rem.get("title")
                            or ""
                        ),
                    )
                    if ok and row:
                        reminders_saved.append(row)
                        title = (
                            row.get("title") or row.get("announce") or "Compromisso"
                        ).strip()
                        when = format_scheduled_for_user(row.get("scheduled_at"))
                        reply_fast = (
                            f"Pronto! Agendei «{title}»{when} na agenda pessoal."
                        )
                    else:
                        reply_fast = (
                            f"Não consegui agendar: {err or 'tente de novo'}. "
                            "Ex.: «marca na agenda pessoal consulta amanhã às 9h»."
                        )
                mid_u = db.save_chat_message(
                    supabase, user_id, "user", user_display
                )
                cs.save_chat_schedule(supabase, user_id, prof, None)
                mid_a = db.save_chat_message(
                    supabase, user_id, "assistant", reply_fast
                )
                db.add_tokens_used(
                    supabase, user_id, gemini.count_tokens_approx(user_display, reply_fast), prof
                )
                prof = db.load_profile(supabase, user_id) or prof
                return {
                    "reply": reply_fast,
                    "user_message_id": mid_u,
                    "assistant_message_id": mid_a,
                    "language": lang,
                    "warnings": [],
                    "reminders_saved": reminders_saved,
                    "agenda_saved": [],
                    "shared_calendars_saved": [],
                    "shared_events_saved": [],
                    "shared_members_saved": [],
                    "shared_calendars_deleted": [],
                    "access": db.build_plan_access_payload(supabase, user_id, prof),
                }, None

    # Marcação ambígua (pessoal vs grupo): responde já, sem chamar o LLM (texto ou voz).
    if chat_agenda and not casual and schedule_text:
        scope_reply = cs.build_schedule_scope_choice_reply(
            supabase, user_id, schedule_text
        )
        if scope_reply:
            schedule = cs.stash_pending_schedule_from_text(
                schedule, schedule_text, schedule_ref
            )
            mid_u = db.save_chat_message(supabase, user_id, "user", user_display)
            cs.save_chat_schedule(supabase, user_id, prof, schedule)
            mid_a = db.save_chat_message(
                supabase, user_id, "assistant", scope_reply
            )
            return {
                "reply": scope_reply,
                "user_message_id": mid_u,
                "assistant_message_id": mid_a,
                "language": lang,
                "warnings": [],
                "reminders_saved": [],
                "agenda_saved": [],
                "shared_calendars_saved": [],
                "shared_events_saved": [],
                "shared_members_saved": [],
                "shared_calendars_deleted": [],
                "access": db.build_plan_access_payload(supabase, user_id, prof),
            }, None

    # Chat sem agenda: pedido de marcação → redireciona à aba Agenda (sem LLM).
    if (
        not chat_agenda
        and not casual
        and schedule_text
        and cs.looks_like_schedule_intent(schedule_text)
    ):
        from ego_api.app_guide import manual_agenda_redirect_reply

        reply_redirect = manual_agenda_redirect_reply()
        mid_u = db.save_chat_message(supabase, user_id, "user", user_display)
        cs.save_chat_schedule(supabase, user_id, prof, None)
        mid_a = db.save_chat_message(supabase, user_id, "assistant", reply_redirect)
        prof = db.load_profile(supabase, user_id) or prof
        return {
            "reply": reply_redirect,
            "user_message_id": mid_u,
            "assistant_message_id": mid_a,
            "user_transcript": voice_transcript or None,
            "language": lang,
            "warnings": [],
            "reminders_saved": [],
            "agenda_saved": [],
            "shared_calendars_saved": [],
            "shared_events_saved": [],
            "shared_members_saved": [],
            "shared_calendars_deleted": [],
            "access": db.build_plan_access_payload(supabase, user_id, prof),
        }, None

    scope_hint = None
    if chat_agenda and not casual:
        scope_hint = cs.detect_scope_from_user_text(
            user_display, supabase, user_id
        )
    if scope_hint:
        schedule = cs.merge_schedule_draft(schedule, {"draft": {"scope": scope_hint}})
        if scope_hint == "shared":
            schedule["step"] = "collect_shared"
        elif scope_hint == "personal":
            schedule["step"] = "collect_personal"

    if casual:
        agenda_ctx = ""
    elif not chat_agenda:
        from ego_api.app_guide import app_guide_context_block

        agenda_ctx = app_guide_context_block()
    else:
        agenda_ctx = db.build_agenda_context_for_llm(supabase, user_id)
        agenda_ctx += cs.build_shared_calendars_context(supabase, user_id)
        agenda_ctx += cs.build_schedule_wizard_context(
            schedule, user_display, supabase, user_id
        )

    from ego_api.avatar_memory import memory_context_block

    try:
        agenda_ctx += memory_context_block(supabase, user_id, avatar_id)
    except Exception:
        pass

    from ego_api.bolso_chat import bolso_mission_prompt_block

    try:
        agenda_ctx += bolso_mission_prompt_block(supabase, user_id, plan_tier=tier)
    except Exception:
        pass

    lang, _conf = gemini.detect_language(user_display)

    if cs.looks_like_today_agenda_query(user_display):
        reply = cs.build_today_commitments_reply(supabase, user_id)
    else:
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

    if not chat_agenda or is_voice_msg:
        reply = gemini.strip_agenda_markers_from_reply(reply)

    mid_u = db.save_chat_message(supabase, user_id, "user", user_display)

    from ego_api.avatar_memory import save_avatar_memory

    try:
        save_avatar_memory(supabase, user_id, avatar_id, user_display)
    except Exception:
        pass

    warnings: list[str] = []
    reminders_saved: list[dict] = []
    agenda_saved: list[dict] = []
    shared_calendars_saved: list[dict] = []
    shared_events_saved: list[dict] = []
    shared_members_saved: list[dict] = []
    shared_invite_payload: dict | None = None
    shared_event_payload: dict | None = None
    shared_delete_payload: dict | None = None
    shared_setup_payload: dict | None = None
    shared_calendars_created: list[dict] = []
    shared_calendars_deleted: list[str] = []

    user_wants_personal = (
        cs.detect_scope_from_user_text(user_display, supabase, user_id) == "personal"
    )
    only_personal_agenda = cs.only_personal_schedule_available(supabase, user_id)

    if chat_agenda:
        schedule = cs.apply_scope_follow_up_if_pending(
            schedule, schedule_text or user_display, supabase, user_id, schedule_ref
        ) or schedule

    scope_choice_reply = None
    if chat_agenda and schedule_text:
        scope_choice_reply = cs.build_schedule_scope_choice_reply(
            supabase, user_id, schedule_text
        )
        if scope_choice_reply:
            schedule = cs.stash_pending_schedule_from_text(
                schedule, schedule_text, schedule_ref
            )
        if scope_choice_reply and cs.try_save_personal_from_schedule_draft(
            schedule, schedule_text, schedule_ref
        ):
            scope_choice_reply = None

    skip_schedule_save = (
        bool(scope_choice_reply) or casual or not chat_agenda or is_voice_msg
    )
    reply_clean = scope_choice_reply or reply

    effective_scope = (
        cs.resolve_effective_schedule_scope(
            schedule, user_display, supabase, user_id
        )
        if chat_agenda
        else None
    )

    draft_patch = None
    if chat_agenda:
        reply_clean, draft_patch = cs.extract_schedule_draft(reply_clean)
    if draft_patch:
        schedule = cs.merge_schedule_draft(schedule, draft_patch)

    user_create_payload = (
        cs.parse_create_shared_calendar_from_plain_text(user_display)
        if not skip_schedule_save
        else None
    )

    if not skip_schedule_save:
        reply_clean, shared_setup = cs.extract_shared_setup(reply_clean)
    else:
        shared_setup = None

    if user_create_payload and cs._user_requests_new_calendar(user_display):
        shared_setup = cs.apply_user_create_calendar_intent(
            user_display, shared_setup
        )

    if shared_setup:
        shared_setup = cs.override_title_from_user_message(user_display, shared_setup)
        shared_setup = cs.override_scheduled_from_user_message(
            user_display, shared_setup, ref=schedule_ref
        )
        shared_setup = cs.fill_shared_calendar_name(
            supabase, user_id, shared_setup, prefer_text=user_display
        )
        shared_setup_payload = shared_setup
        cals, evs, setup_members, shared_warns = cs.process_shared_setup(
            supabase, user_id, shared_setup, user_message=user_display
        )
        shared_calendars_created.extend(cals)
        shared_calendars_saved.extend(cals)
        shared_events_saved.extend(evs)
        shared_members_saved.extend(setup_members)
        warnings.extend(shared_warns)
        if cals or evs or setup_members:
            schedule = {"step": "", "draft": {}}
        elif shared_warns:
            warnings.append(
                "O assistente respondeu no chat, mas a agenda só entra "
                "quando o servidor grava. Detalhe: " + shared_warns[0]
            )
        elif user_create_payload and cs._user_requests_new_calendar(user_display):
            retry = cs.override_title_from_user_message(user_display, user_create_payload)
            retry = cs.override_scheduled_from_user_message(
                user_display, retry, ref=schedule_ref
            )
            retry = cs.fill_shared_calendar_name(
                supabase, user_id, retry, prefer_text=user_display
            )
            cals2, evs2, mem2, warn2 = cs.process_shared_setup(
                supabase, user_id, retry, user_message=user_display
            )
            shared_calendars_created.extend(cals2)
            shared_calendars_saved.extend(cals2)
            shared_events_saved.extend(evs2)
            shared_members_saved.extend(mem2)
            warnings.extend(warn2)
            if cals2 or evs2 or mem2:
                schedule = {"step": "", "draft": {}}
    elif user_create_payload:
        fallback_create = cs.override_title_from_user_message(
            user_display, user_create_payload
        )
        fallback_create = cs.override_scheduled_from_user_message(
            user_display, fallback_create, ref=schedule_ref
        )
        fallback_create = cs.fill_shared_calendar_name(
            supabase, user_id, fallback_create, prefer_text=user_display
        )
        shared_setup_payload = fallback_create
        cals, evs, setup_members, shared_warns = cs.process_shared_setup(
            supabase, user_id, fallback_create, user_message=user_display
        )
        shared_calendars_created.extend(cals)
        shared_calendars_saved.extend(cals)
        shared_events_saved.extend(evs)
        shared_members_saved.extend(setup_members)
        warnings.extend(shared_warns)
        if cals or evs or setup_members:
            schedule = {"step": "", "draft": {}}
        elif shared_warns:
            warnings.append(
                "O assistente respondeu no chat, mas a agenda só entra "
                "quando o servidor grava. Detalhe: " + shared_warns[0]
            )

    user_delete_payload = (
        cs.parse_delete_shared_calendar_from_plain_text(user_display)
        if not skip_schedule_save
        else None
    )

    if not skip_schedule_save:
        reply_clean, shared_delete = cs.extract_shared_delete(reply_clean)
    else:
        shared_delete = None
    if user_delete_payload:
        shared_delete = cs.apply_user_delete_calendar_intent(
            user_display, shared_delete
        )
    if shared_delete:
        shared_delete = cs.fill_shared_calendar_name(
            supabase, user_id, shared_delete, prefer_text=user_display
        )
        shared_delete_payload = shared_delete
        deleted_name, del_warns, deleted = cs.process_shared_delete(
            supabase, user_id, shared_delete
        )
        if deleted and deleted_name:
            shared_calendars_deleted.append(deleted_name)
            schedule = {"step": "", "draft": {}}
        warnings.extend(del_warns)
    elif not skip_schedule_save and (
        fallback_delete := cs.parse_delete_shared_calendar_from_plain_text(user_display)
    ):
        fallback_delete = cs.fill_shared_calendar_name(
            supabase, user_id, fallback_delete, prefer_text=user_display
        )
        shared_delete_payload = fallback_delete
        deleted_name, del_warns, deleted = cs.process_shared_delete(
            supabase, user_id, fallback_delete
        )
        if deleted and deleted_name:
            shared_calendars_deleted.append(deleted_name)
            schedule = {"step": "", "draft": {}}
        elif del_warns:
            warnings.append(
                "O assistente respondeu no chat, mas a agenda só some "
                "quando o servidor apaga. Detalhe: " + del_warns[0]
            )
        else:
            warnings.extend(del_warns)

    if not skip_schedule_save:
        reply_clean, shared_invite = cs.extract_shared_invite(reply_clean)
    else:
        shared_invite = None
    if shared_invite:
        shared_invite = cs.fill_shared_calendar_name(
            supabase, user_id, shared_invite, prefer_text=user_display
        )
        shared_invite_payload = shared_invite
        invited_cal, invite_warns, invite_added = cs.process_shared_invite(
            supabase, user_id, shared_invite
        )
        shared_members_saved.extend(invite_added)
        if invited_cal:
            shared_calendars_saved.append(invited_cal)
        warnings.extend(invite_warns)
        schedule = {"step": "", "draft": {}}
    elif not skip_schedule_save and (
        fallback_invite := cs.parse_invite_from_plain_text(user_display)
    ):
        fallback_invite = cs.fill_shared_calendar_name(
            supabase, user_id, fallback_invite, prefer_text=user_display
        )
        shared_invite_payload = fallback_invite
        invited_cal, invite_warns, invite_added = cs.process_shared_invite(
            supabase, user_id, fallback_invite
        )
        shared_members_saved.extend(invite_added)
        if invited_cal:
            shared_calendars_saved.append(invited_cal)
        warnings.extend(invite_warns)
        if invite_added:
            schedule = {"step": "", "draft": {}}
        elif invite_warns:
            warnings.append(
                "O assistente respondeu no chat, mas o convite só entra "
                "quando o servidor grava o e-mail. Detalhe: "
                + invite_warns[0]
            )

    if not skip_schedule_save:
        reply_clean, shared_event = cs.extract_shared_event(reply_clean)
    else:
        shared_event = None
    if user_wants_personal or only_personal_agenda or effective_scope == "personal":
        shared_event = None
    if shared_event and effective_scope != "personal":
        shared_event = cs.override_title_from_user_message(user_display, shared_event)
        shared_event = cs.override_scheduled_from_user_message(
            user_display, shared_event, ref=schedule_ref
        )
        shared_event = cs.fill_shared_calendar_name(
            supabase, user_id, shared_event, prefer_text=user_display
        )
        shared_event_payload = shared_event
        evs, shared_warns = cs.process_shared_event(
            supabase, user_id, shared_event, user_message=user_display
        )
        shared_events_saved.extend(evs)
        warnings.extend(shared_warns)
        if evs:
            schedule = {"step": "", "draft": {}}
    elif effective_scope != "personal" and (
        draft_event := cs.shared_event_from_schedule_draft(schedule)
    ):
        draft_event = cs.override_title_from_user_message(user_display, draft_event)
        draft_event = cs.override_scheduled_from_user_message(
            user_display, draft_event, ref=schedule_ref
        )
        draft_event = cs.fill_shared_calendar_name(
            supabase, user_id, draft_event, prefer_text=user_display
        )
        shared_event_payload = draft_event
        evs, shared_warns = cs.process_shared_event(
            supabase, user_id, draft_event, user_message=user_display
        )
        shared_events_saved.extend(evs)
        warnings.extend(shared_warns)
        if evs:
            schedule = {"step": "", "draft": {}}
        elif shared_warns:
            warnings.append(
                "O assistente respondeu no chat, mas o compromisso compartilhado "
                "só entra quando o servidor grava. Detalhe: " + shared_warns[0]
            )
    elif (
        not skip_schedule_save
        and effective_scope != "personal"
        and not user_wants_personal
        and not only_personal_agenda
        and (
            fallback_event := cs.parse_shared_event_from_plain_text(
                user_display, ref=schedule_ref
            )
        )
    ):
        fallback_event = cs.override_title_from_user_message(
            user_display, fallback_event
        )
        fallback_event = cs.override_scheduled_from_user_message(
            user_display, fallback_event, ref=schedule_ref
        )
        fallback_event = cs.fill_shared_calendar_name(
            supabase, user_id, fallback_event, prefer_text=user_display
        )
        shared_event_payload = fallback_event
        evs, shared_warns = cs.process_shared_event(
            supabase, user_id, fallback_event, user_message=user_display
        )
        shared_events_saved.extend(evs)
        warnings.extend(shared_warns)
        if evs:
            schedule = {"step": "", "draft": {}}
        elif shared_warns:
            warnings.append(
                "O assistente respondeu no chat, mas o compromisso compartilhado "
                "só entra quando o servidor grava. Detalhe: " + shared_warns[0]
            )

    if not skip_schedule_save:
        reply_clean, rem_items = gemini.extract_reminders(reply_clean)
        if effective_scope == "shared":
            rem_items = []
        rem_items = cs.override_scheduled_from_user_message(
            user_display, rem_items, ref=schedule_ref
        ) or []
    else:
        rem_items = []
    if not skip_schedule_save and not rem_items and effective_scope != "shared":
        if draft_rem := cs.reminder_from_schedule_draft(schedule):
            rem_items = [draft_rem]
    if (
        not skip_schedule_save
        and not rem_items
        and effective_scope != "shared"
        and (user_wants_personal or only_personal_agenda)
    ):
        if fallback_rem := cs.parse_reminder_from_plain_text(
            user_display,
            ref=schedule_ref,
            implicit_personal=only_personal_agenda or user_wants_personal,
        ):
            rem_items = [fallback_rem]
    if not skip_schedule_save and rem_items:
        patched_rem = cs.override_title_from_user_message(user_display, rem_items)
        if patched_rem is not None:
            rem_items = (
                patched_rem if isinstance(patched_rem, list) else [patched_rem]
            )
    rem_cap = enforce_reminder_limit(supabase, user_id, prof)
    for it in rem_items if not skip_schedule_save else []:
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
            schedule = {"step": "", "draft": {}}
        elif err:
            warnings.append(f"Lembrete: {err}")

    if not skip_schedule_save:
        reply_clean, ag_items = gemini.extract_agenda_markers(reply_clean)
    else:
        ag_items = []
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

    from ego_api.chat_reply import ensure_visible_chat_reply

    user_requested_cal_name = ""
    if user_create_payload:
        user_requested_cal_name = str(
            user_create_payload.get("calendar_name") or ""
        ).strip()

    reply_clean = ensure_visible_chat_reply(
        reply_clean,
        reminders_saved=reminders_saved,
        agenda_saved=agenda_saved,
        rem_items=rem_items,
        ag_items=ag_items,
        warnings=warnings,
        shared_calendars_saved=shared_calendars_saved,
        shared_events_saved=shared_events_saved,
        shared_members_saved=shared_members_saved,
        shared_setup=shared_setup_payload,
        shared_invite=shared_invite_payload,
        shared_event=shared_event_payload,
        shared_delete=shared_delete_payload,
        shared_calendars_deleted=shared_calendars_deleted,
        shared_calendars_created=shared_calendars_created,
        user_requested_cal_name=user_requested_cal_name,
    )

    if not chat_agenda:
        schedule = {"step": "", "draft": {}}

    cs.save_chat_schedule(
        supabase,
        user_id,
        prof,
        schedule
        if (schedule.get("step") or (schedule.get("draft") or {}))
        else None,
    )

    mid_a = db.save_chat_message(supabase, user_id, "assistant", reply_clean)
    tok_n = gemini.count_tokens_approx(user_display, reply_clean)
    db.add_tokens_used(supabase, user_id, tok_n, prof)
    prof = db.load_profile(supabase, user_id) or prof

    payload: dict = {
        "reply": reply_clean,
        "user_message_id": mid_u,
        "assistant_message_id": mid_a,
        "language": lang,
        "warnings": warnings,
        "reminders_saved": reminders_saved,
        "agenda_saved": agenda_saved,
        "shared_calendars_saved": shared_calendars_saved,
        "shared_events_saved": shared_events_saved,
        "shared_members_saved": shared_members_saved,
        "shared_calendars_deleted": shared_calendars_deleted,
        "access": db.build_plan_access_payload(supabase, user_id, prof),
    }
    if voice_transcript:
        payload["user_transcript"] = voice_transcript
    # Áudio inline atrasa o texto no telemóvel; o app pede TTS depois (/tts ou playVoice).
    from ego_api.config import read_env

    inline_tts = read_env("EGO_CHAT_INLINE_TTS", "0").lower() in (
        "1",
        "true",
        "yes",
        "sim",
    )
    if inline_tts and speak_reply_effective and reply_clean.strip():
        from ego_api import tts
        from ego_api.persona import resolve_tts_voice

        avatar_id, voice_id = ensure_persona_normalized(supabase, user_id)
        resolved_voice = resolve_tts_voice(voice_id, avatar_id)
        mp3 = tts.synthesize_speech_mp3(reply_clean, resolved_voice, avatar_id)
        payload["tts_voice_id"] = resolved_voice
        if mp3:
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


def _list_shared_calendars_safe(supabase: Client | None, user_id: str) -> list:
    try:
        from ego_api import shared_calendars as sc

        return sc.list_calendars_for_user(supabase, user_id)
    except Exception as exc:
        print(f"[EGO] bootstrap shared_calendars error user={user_id}: {exc}", flush=True)
        return []


def _list_pending_calendar_invites_safe(supabase: Client | None, user_id: str) -> list:
    try:
        from ego_api import shared_calendars as sc

        return sc.list_pending_invites_for_user(supabase, user_id)
    except Exception as exc:
        print(
            f"[EGO] bootstrap pending_calendar_invites error user={user_id}: {exc}",
            flush=True,
        )
        return []


def _bootstrap_section(label: str, fn, default):  # noqa: ANN001
    try:
        return fn()
    except Exception as exc:
        print(f"[EGO] bootstrap {label} error: {exc}", flush=True)
        return default


def bootstrap_payload_fallback(supabase: Client | None, user_id: str) -> dict:
    """Resposta mínima 200 — evita ecrã vermelho em todo o app se algo falhar."""
    from ego_api.config import gemini_api_key, supabase_anon_key, supabase_url

    me = _bootstrap_section("me", lambda: me_payload(supabase, user_id), None)
    access = _bootstrap_section(
        "access",
        lambda: db.build_plan_access_payload(supabase, user_id),
        {
            "access_allowed": True,
            "plan_tier": "essential",
            "plan_label": "EGO Essencial",
            "monthly_tokens_used": 0,
            "monthly_tokens_limit": 200_000,
            "monthly_tokens_ok": True,
        },
    )
    return {
        "health": {
            "ok": True,
            "service": "ego-ai-api",
            "supabase_configured": bool(supabase_url() and supabase_anon_key()),
            "gemini_configured": bool(gemini_api_key()),
            "degraded": True,
        },
        "me": me,
        "access": {"ok": True, **access},
        "reminders": [],
        "agenda": [],
        "agenda_drafts": [],
        "shopping_orphans": [],
        "shared_calendars": _list_shared_calendars_safe(supabase, user_id),
        "pending_calendar_invites": _list_pending_calendar_invites_safe(
            supabase, user_id
        ),
        "messages": [],
    }


def list_reminders_enriched(supabase: Client | None, user_id: str) -> list[dict]:
    from ego_api import habits_db

    rows = db.list_reminders(supabase, user_id)
    ids = [str(r.get("id") or "") for r in rows if r.get("id")]
    by_rem = habits_db.shopping_by_reminder_ids(supabase, user_id, ids)
    for row in rows:
        rid = str(row.get("id") or "")
        row["shopping_items"] = by_rem.get(rid, [])
    return rows


def shopping_list_for_dashboard(supabase: Client | None, user_id: str) -> list[dict]:
    """Lista de compras persistente — inclui itens de compromissos já passados."""
    from ego_api import habits_db

    if not supabase or not user_id:
        return []
    rows = db.list_reminders(supabase, user_id)
    visible_ids = {str(r.get("id") or "") for r in rows if r.get("id")}
    return habits_db.list_persistent_shopping_items(supabase, user_id, visible_ids)


def _wellness_journey_default() -> dict:
    from ego_api.wellness_journey import JOURNEY_LEVELS

    first = JOURNEY_LEVELS[0]
    return {
        "level": 1,
        "max_level": len(JOURNEY_LEVELS),
        "title": first["title"],
        "subtitle": first["subtitle"],
        "emoji": first["emoji"],
        "today_task": first["today_task"],
        "why": first["why"],
        "progress": 0.0,
        "level_complete": False,
        "steps": [],
        "show_level_up": False,
        "share_challenge": first["share_challenge"],
        "plan_nudge": None,
        "journey_finished": False,
        "companion_stage": "egg",
        "companion_stage_label": "Ovo",
        "companion_sprite_emoji": "🥚",
        "care_percent": 0,
    }


def _wellness_journey_bootstrap(supabase, user_id: str) -> dict:  # noqa: ANN001
    from ego_api import wellness_journey

    prof = db.load_profile(supabase, user_id) or {}
    tier, _ = db.user_plan_limits(prof)
    journey = wellness_journey.sync_streak_levels(supabase, user_id, plan_tier=tier)
    return journey


def _daily_care_default() -> dict:
    from ego_api.daily_care import MOODS, question_for_today

    return {
        "current": 0,
        "longest": 0,
        "last_date": "",
        "checked_today": False,
        "at_risk": False,
        "last_mood": "",
        "last_mood_emoji": "",
        "last_mood_label": "",
        "total_checkins": 0,
        "question": question_for_today(),
        "moods": MOODS,
        "can_share": False,
        "share_hook": "Faça o check-in de hoje para subir no ranking.",
        "garden_stage": 1,
        "garden_label": "Semente",
        "garden_emoji": "🌱",
        "monster_line": "Escolha o monstrinho do seu humor hoje.",
        "daily_mission": "Missão: conhecer seu primeiro monstrinho do humor.",
        "daily_mission_action": "checkin",
        "ranking": {
            "tier_index": 0,
            "tier_total": 500,
            "tier_emoji": "🌱",
            "tier_label": "Iniciante",
            "next_tier_days": 1,
            "next_tier_label": "Iniciante",
            "personal_best": 0,
            "community_top_days": 21,
            "days_to_next_tier": 1,
            "challenge_line": "Comece hoje — dia 1 no ranking.",
            "ladder": [],
        },
    }


def _daily_care_bootstrap(supabase, user_id: str) -> dict:  # noqa: ANN001
    from ego_api import daily_care

    return daily_care.get_daily_care(supabase, user_id)


def bootstrap_payload(supabase: Client | None, user_id: str) -> dict:
    """Um único payload para o painel (evita vários GET no cliente)."""
    from ego_api import delegation_db, habits_db, streaks
    from ego_api.config import gemini_api_key, supabase_anon_key, supabase_url

    access = _bootstrap_section(
        "access",
        lambda: db.build_plan_access_payload(supabase, user_id),
        {"access_allowed": True, "plan_tier": "essential", "plan_label": "EGO Essencial"},
    )
    me = _bootstrap_section("me", lambda: me_payload(supabase, user_id), None)
    return {
        "health": {
            "ok": True,
            "service": "ego-ai-api",
            "supabase_configured": bool(supabase_url() and supabase_anon_key()),
            "gemini_configured": bool(gemini_api_key()),
        },
        "me": me,
        "access": {"ok": True, **access},
        "reminders": _bootstrap_section(
            "reminders", lambda: list_reminders_enriched(supabase, user_id), []
        ),
        "agenda": _bootstrap_section("agenda", lambda: db.list_agenda(supabase, user_id), []),
        "agenda_drafts": _bootstrap_section(
            "agenda_drafts",
            lambda: habits_db.list_pending_drafts(supabase, user_id),
            [],
        ),
        "shopping_orphans": _bootstrap_section(
            "shopping_orphans",
            lambda: shopping_list_for_dashboard(supabase, user_id),
            [],
        ),
        "delegation_requests": _bootstrap_section(
            "delegation_requests",
            lambda: delegation_db.list_pending_incoming(supabase, user_id),
            [],
        ),
        "streak": _bootstrap_section(
            "streak",
            lambda: streaks.get_streak(supabase, user_id),
            {
                "current": 0,
                "longest": 0,
                "last_date": "",
                "active_today": False,
                "at_risk": False,
            },
        ),
        "wellness_journey": _bootstrap_section(
            "wellness_journey",
            lambda: _wellness_journey_bootstrap(supabase, user_id),
            _wellness_journey_default(),
        ),
        "daily_care": _bootstrap_section(
            "daily_care",
            lambda: _daily_care_bootstrap(supabase, user_id),
            _daily_care_default(),
        ),
        "shared_calendars": _list_shared_calendars_safe(supabase, user_id),
        "pending_calendar_invites": _list_pending_calendar_invites_safe(
            supabase, user_id
        ),
        "messages": _bootstrap_section(
            "messages", lambda: db.load_chat_history(supabase, user_id), []
        ),
    }


def ensure_persona_normalized(supabase: Client | None, user_id: str) -> tuple[str, str]:
    """Garante par avatar/voz coerente no Supabase (ex.: Leo m1 + vm1)."""
    from ego_api.persona import normalize_persona_pair

    stored_a, stored_v = db.load_persona(supabase, user_id)
    avatar_id, voice_id = normalize_persona_pair(stored_a, stored_v)
    if db.persona_is_configured(supabase, user_id) and (
        stored_a != avatar_id or stored_v != voice_id
    ):
        try:
            db.save_persona(supabase, user_id, avatar_id, voice_id)
        except Exception as exc:
            print(f"[EGO] ensure_persona_normalized save error: {exc}", flush=True)
    return avatar_id, voice_id


def me_payload(supabase: Client | None, user_id: str) -> dict:
    prof = db.load_profile_trusted(supabase, user_id) or {}
    sess = get_session()
    email = (sess.email if sess else None) or str(prof.get("email") or "")
    if email and supabase and user_id:
        try:
            from ego_api import shared_calendars as sc

            sc.link_shared_memberships_for_user(supabase, user_id, email)
            ph = str(prof.get("phone") or "").strip()
            if ph:
                sc.link_shared_memberships_for_user_phone(supabase, user_id, ph)
        except Exception:
            pass
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
    prof_phone = str(prof.get("phone") or "").strip()
    if prof_phone:
        prof = dict(prof)
        prof["phone"] = prof_phone
    return {
        "user_id": user_id,
        "email": email or prof.get("email"),
        "profile": prof,
        "profile_phone": prof_phone,
        "persona_configured": configured,
        "persona": {"avatar_id": avatar_id, "voice_id": voice_id},
        "access": {"allowed": ok_access, "status": status},
        "stripe_checkout": _stripe_checkout_payload(user_id),
    }


def _stripe_checkout_payload(user_id: str) -> dict:
    from ego_api.referrals import append_referral_promo_to_url, should_hide_launch_offer
    from ego_api.supabase_client import create_service_client
    from ego_api.team_stripe_checkout import team_checkout_nested

    prof: dict = {}
    try:
        svc = create_service_client()
        if svc and user_id:
            prof = db.load_profile(svc, user_id) or {}
    except Exception as exc:
        print(f"[EGO] checkout profile load error: {exc}", flush=True)

    def checkout_link(base: str) -> str | None:
        url = _stripe_link(base, user_id)
        if not url:
            return None
        return append_referral_promo_to_url(url, prof)

    urls = stripe_checkout_urls()
    legacy_m = checkout_link(STRIPE_MENSAL_URL)
    legacy_a = checkout_link(STRIPE_ANUAL_URL)
    connection = checkout_link(urls.get(PLAN_CONNECTION) or "") or legacy_m
    int_connection = checkout_link(urls.get("int_connection") or "")
    launch_raw = urls.get("launch") or ""
    launch = None if should_hide_launch_offer(prof) else checkout_link(launch_raw)
    team: dict[str, dict[str, dict[str, str | None]]] = {"br": {}, "int": {}}
    try:
        team_raw = team_checkout_nested()
        for market in ("br", "int"):
            for tier, seat_map in (team_raw.get(market) or {}).items():
                team[market][tier] = {
                    seats: checkout_link(url) for seats, url in seat_map.items()
                }
    except Exception as exc:
        print(f"[EGO] team_checkout_nested error: {exc}", flush=True)
    return {
        "monthly_url": connection,
        "annual_url": legacy_a,
        "connection_url": connection,
        "launch_url": launch,
        "premium_url": checkout_link(urls.get(PLAN_PREMIUM) or ""),
        "total_url": checkout_link(urls.get(PLAN_TOTAL) or ""),
        "enterprise_url": checkout_link(urls.get(PLAN_ENTERPRISE) or ""),
        "int_connection_url": int_connection,
        "int_premium_url": checkout_link(urls.get("int_premium") or ""),
        "int_premium_annual_url": checkout_link(urls.get("int_premium_annual") or ""),
        "int_total_url": checkout_link(urls.get("int_total") or ""),
        "int_total_annual_url": checkout_link(urls.get("int_total_annual") or ""),
        "int_enterprise_url": checkout_link(urls.get("int_enterprise") or ""),
        "essential": None,
        "team": team,
    }


def _stripe_link(base: str, user_id: str) -> str | None:
    base = (base or "").strip()
    if not base or "COLOQUE" in base.upper() or "URL_DO" in base.upper():
        return None
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}client_reference_id={user_id}"


def persist_client_timezone(
    supabase: Client | None,
    user_id: str,
    *,
    timezone: str = "",
    tz_offset_min: int | None = None,
) -> None:
    """Grava fuso do aparelho no perfil (cada bootstrap/chat/voz actualiza)."""
    if not supabase or not user_id:
        return
    if not (timezone or "").strip() and tz_offset_min is None:
        return
    try:
        prof = db.load_profile(supabase, user_id) or {}
        ui = dict(ui_state_from_profile(prof))
        changed = False
        tz_clean = (timezone or "").strip()[:120]
        if tz_clean and ui.get("ego_client_timezone") != tz_clean:
            ui["ego_client_timezone"] = tz_clean
            changed = True
        if tz_offset_min is not None and ui.get("ego_client_tz_offset_min") != tz_offset_min:
            ui["ego_client_tz_offset_min"] = int(tz_offset_min)
            changed = True
        if changed:
            db.update_profile_fields(supabase, user_id, {"ui_state": ui})
    except Exception:
        pass


# Campos que só o servidor/Stripe podem gravar — nunca aceitar do app.
UI_STATE_SERVER_ONLY_KEYS = frozenset(
    {
        "plan_tier",
        "plan_type",
        "is_pro",
        "team_seats",
        "monthly_tokens_used",
        "ego_de_bolso_push_date",
        "ego_de_bolso_push_morning_date",
        "ego_de_bolso_mission_push_count",
        "ego_de_bolso_mission_push_date",
        "monthly_tokens_period",
    }
)


def sanitize_user_ui_state(patch: dict | None) -> dict:
    """Remove chaves sensíveis antes de persistir ui_state vindo do cliente."""
    if not isinstance(patch, dict):
        return {}
    return {k: v for k, v in patch.items() if k not in UI_STATE_SERVER_ONLY_KEYS}


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
