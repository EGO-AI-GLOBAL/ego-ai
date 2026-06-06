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
    email: str, password: str, full_name: str = "", phone: str = ""
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
    phone_norm = ""
    if (phone or "").strip():
        from ego_api.phone_utils import normalize_phone_br

        phone_norm, phone_err = normalize_phone_br(phone)
        if phone_err:
            return None, phone_err
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
        ensure_user_profile(
            client, uid, email=email_norm, full_name=display, phone=phone_norm
        )
        if phone_norm:
            from ego_api import shared_calendars as sc

            sc.link_shared_memberships_for_user_phone(client, uid, phone_norm)
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

    if speak_reply:
        ok_tts, _tts_used = db.daily_tts_ok(supabase, user_id, limits, prof)
        if not ok_tts:
            return None, _daily_limit_message(supabase, user_id)

    casual = _is_casual_chat_message(user_display) and not audio_bytes
    client_hist = _history_from_client(client_history)
    if client_hist:
        history = client_hist
    else:
        history = db.load_chat_history(supabase, user_id, limit=16)
    lang, _conf = gemini.detect_language(user_display)
    history_for_llm = [*history, {"role": "user", "content": user_display}]

    from ego_api import chat_schedule as cs

    schedule = cs.load_chat_schedule(prof)
    from ego_api.schedule_tz import local_now_from_session

    schedule_ref = local_now_from_session(sess)

    # Agenda pessoal clara (ex.: «marca na agenda pessoal … às 9h»): grava sem LLM.
    if not casual and not audio_bytes and cs.looks_like_schedule_intent(user_display):
        personal_scope = cs.detect_scope_from_user_text(
            user_display, supabase, user_id
        ) == "personal" or cs.only_personal_schedule_available(
            supabase, user_id
        )
        if personal_scope and not cs.schedule_scope_is_ambiguous(
            user_display, supabase, user_id
        ):
            if not cs.user_message_has_schedule_time(user_display):
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
                user_display,
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

    # Marcação ambígua (pessoal vs grupo): responde já, sem chamar o LLM (evita erro e demora).
    if not casual and not audio_bytes:
        scope_reply = cs.build_schedule_scope_choice_reply(
            supabase, user_id, user_display
        )
        if scope_reply:
            schedule = cs.stash_pending_schedule_from_text(
                schedule, user_display, schedule_ref
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

    scope_hint = None if casual else cs.detect_scope_from_user_text(
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
    else:
        agenda_ctx = db.build_agenda_context_for_llm(supabase, user_id)
        agenda_ctx += cs.build_shared_calendars_context(supabase, user_id)
        agenda_ctx += cs.build_schedule_wizard_context(
            schedule, user_display, supabase, user_id
        )

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

    mid_u = db.save_chat_message(supabase, user_id, "user", user_display)

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

    schedule = cs.apply_scope_follow_up_if_pending(
        schedule, user_display, supabase, user_id, schedule_ref
    ) or schedule

    scope_choice_reply = cs.build_schedule_scope_choice_reply(
        supabase, user_id, user_display
    )
    if scope_choice_reply:
        schedule = cs.stash_pending_schedule_from_text(
            schedule, user_display, schedule_ref
        )

    skip_schedule_save = bool(scope_choice_reply) or casual
    reply_clean = scope_choice_reply or reply

    effective_scope = cs.resolve_effective_schedule_scope(
        schedule, user_display, supabase, user_id
    )

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
    # Áudio inline atrasa o texto no telemóvel; o app pede TTS depois (/tts ou playVoice).
    from ego_api.config import read_env

    inline_tts = read_env("EGO_CHAT_INLINE_TTS", "0").lower() in (
        "1",
        "true",
        "yes",
        "sim",
    )
    if inline_tts and speak_reply and reply_clean.strip():
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
        "shared_calendars": _list_shared_calendars_safe(supabase, user_id),
        "messages": [],
    }


def bootstrap_payload(supabase: Client | None, user_id: str) -> dict:
    """Um único payload para o painel (evita vários GET no cliente)."""
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
            "reminders", lambda: db.list_reminders(supabase, user_id), []
        ),
        "agenda": _bootstrap_section("agenda", lambda: db.list_agenda(supabase, user_id), []),
        "shared_calendars": _list_shared_calendars_safe(supabase, user_id),
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
    prof = db.load_profile(supabase, user_id) or {}
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
    from ego_api.team_stripe_checkout import team_checkout_nested

    urls = stripe_checkout_urls()
    legacy_m = _stripe_link(STRIPE_MENSAL_URL, user_id)
    legacy_a = _stripe_link(STRIPE_ANUAL_URL, user_id)
    connection = _stripe_link(urls.get(PLAN_CONNECTION) or "", user_id) or legacy_m
    int_connection = _stripe_link(urls.get("int_connection") or "", user_id)
    launch = _stripe_link(urls.get("launch") or "", user_id)
    team: dict[str, dict[str, dict[str, str | None]]] = {"br": {}, "int": {}}
    try:
        team_raw = team_checkout_nested()
        for market in ("br", "int"):
            for tier, seat_map in (team_raw.get(market) or {}).items():
                team[market][tier] = {
                    seats: _stripe_link(url, user_id) for seats, url in seat_map.items()
                }
    except Exception as exc:
        print(f"[EGO] team_checkout_nested error: {exc}", flush=True)
    return {
        "monthly_url": connection,
        "annual_url": legacy_a,
        "connection_url": connection,
        "launch_url": launch,
        "premium_url": _stripe_link(urls.get(PLAN_PREMIUM) or "", user_id),
        "total_url": _stripe_link(urls.get(PLAN_TOTAL) or "", user_id),
        "enterprise_url": _stripe_link(urls.get(PLAN_ENTERPRISE) or "", user_id),
        "int_connection_url": int_connection,
        "int_premium_url": _stripe_link(urls.get("int_premium") or "", user_id),
        "int_premium_annual_url": _stripe_link(
            urls.get("int_premium_annual") or "", user_id
        ),
        "int_total_url": _stripe_link(urls.get("int_total") or "", user_id),
        "int_total_annual_url": _stripe_link(
            urls.get("int_total_annual") or "", user_id
        ),
        "int_enterprise_url": _stripe_link(urls.get("int_enterprise") or "", user_id),
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
