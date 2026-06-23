from __future__ import annotations

import datetime
import json
import re
from typing import TYPE_CHECKING

from ego_api.request_ctx import get_session
from ego_api.config import (
    AGENDA_HORIZON_DAYS,
    CHAT_HISTORY_FETCH_LIMIT,
    EGO_TRIAL_DAYS,
    SUPABASE_AGENDA_TABLE,
    SUPABASE_FEEDBACK_TABLE,
    SUPABASE_HISTORY_TABLE,
    SUPABASE_PERSONA_TABLE,
    SUPABASE_PROFILES_TABLE,
    SUPABASE_REMINDERS_TABLE,
    beta_unlimited,
)
from ego_api.plans import (
    PLAN_PRICES_BRL,
    PlanLimits,
    plan_label,
    plan_limits,
    resolve_plan_tier,
)
from ego_api.supabase_client import apply_user_auth

if TYPE_CHECKING:
    from ego_supabase import Client

REMINDER_PAST_GRACE = datetime.timedelta(minutes=5)
VALID_AGENDA_DOW = frozenset({"seg", "ter", "qua", "qui", "sex", "sab", "dom"})
DOW_PT_ORDER = ("seg", "ter", "qua", "qui", "sex", "sab", "dom")
VOICE_MESSAGE_MARKER = "(mensagem de voz)"


def _table_missing(exc: BaseException) -> bool:
    err = str(exc).lower()
    return "does not exist" in err or "could not find" in err or "42p01" in err


def load_chat_history(
    supabase: Client | None, user_id: str, *, limit: int = 0
) -> list[dict]:
    if not supabase or not user_id:
        return []
    apply_user_auth(supabase)
    cap = limit if limit > 0 else CHAT_HISTORY_FETCH_LIMIT
    try:
        res = (
            supabase.table(SUPABASE_HISTORY_TABLE)
            .select("ego_msg_id,role,content,created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(cap)
            .execute()
        )
        rows = list(reversed(res.data or []))
        out: list[dict] = []
        for r in rows:
            if r.get("role") not in ("user", "assistant"):
                continue
            mid = r.get("ego_msg_id")
            out.append(
                {
                    "role": r.get("role", "assistant"),
                    "content": r.get("content", ""),
                    "msg_id": str(mid) if mid else None,
                    "created_at": r.get("created_at"),
                }
            )
        return out
    except Exception:
        try:
            res = (
                supabase.table(SUPABASE_HISTORY_TABLE)
                .select("role,content,created_at")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(cap)
                .execute()
            )
            rows = list(reversed(res.data or []))
            return [
                {
                    "role": r.get("role", "assistant"),
                    "content": r.get("content", ""),
                    "msg_id": None,
                    "created_at": r.get("created_at"),
                }
                for r in rows
                if r.get("role") in ("user", "assistant")
            ]
        except Exception:
            return []


def save_chat_message(
    supabase: Client | None, user_id: str, role: str, content: str
) -> str | None:
    if not supabase or not user_id:
        return None
    if not apply_user_auth(supabase):
        return None
    row = {"user_id": user_id, "role": role, "content": content}
    try:
        res = (
            supabase.table(SUPABASE_HISTORY_TABLE)
            .insert(row)
            .select("ego_msg_id")
            .execute()
        )
        if res.data and res.data[0].get("ego_msg_id"):
            return str(res.data[0]["ego_msg_id"])
    except Exception:
        pass
    try:
        res = (
            supabase.table(SUPABASE_HISTORY_TABLE)
            .insert(row)
            .select("id")
            .execute()
        )
        if res.data and res.data[0].get("id") is not None:
            return str(res.data[0]["id"])
    except Exception:
        pass
    try:
        supabase.table(SUPABASE_HISTORY_TABLE).insert(row).execute()
    except Exception:
        pass
    return None


def load_profile(supabase: Client | None, user_id: str) -> dict | None:
    if not supabase or not user_id:
        return None
    apply_user_auth(supabase)
    try:
        res = (
            supabase.table(SUPABASE_PROFILES_TABLE)
            .select("*")
            .eq("id", user_id)
            .single()
            .execute()
        )
        return res.data
    except Exception:
        return None


def load_profile_trusted(supabase: Client | None, user_id: str) -> dict | None:
    """Perfil com service role quando disponível (telefone / bootstrap)."""
    from ego_api.supabase_client import create_service_client

    admin = create_service_client()
    if admin:
        prof = _load_profile_raw(admin, user_id)
        if prof:
            return prof
    return load_profile(supabase, user_id)


def ensure_user_profile(
    supabase: Client | None,
    user_id: str,
    *,
    email: str = "",
    full_name: str = "",
    phone: str = "",
) -> tuple[bool, str]:
    if not supabase or not user_id:
        return False, "Cliente Supabase ou user_id em falta."
    apply_user_auth(supabase)
    display = (full_name or "").strip() or "Usuário"
    em = (email or "").strip()[:254]
    ph = (phone or "").strip()
    row = {
        "id": user_id,
        "full_name": display[:200],
        "email": em or None,
        "phone": ph or None,
        "country": "Brasil",
        "document_type": "",
    }
    try:
        found = (
            supabase.table(SUPABASE_PROFILES_TABLE)
            .select("id")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        if found.data:
            supabase.table(SUPABASE_PROFILES_TABLE).update(
                {
                    "full_name": row["full_name"],
                    "email": row["email"],
                    "phone": row["phone"],
                }
            ).eq("id", user_id).execute()
        else:
            supabase.table(SUPABASE_PROFILES_TABLE).insert(
                {**row, "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
            ).execute()
        return True, ""
    except Exception as exc:
        return False, str(exc)


def touch_last_login(supabase: Client | None, user_id: str) -> None:
    if not supabase or not user_id:
        return
    apply_user_auth(supabase)
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        supabase.table(SUPABASE_PROFILES_TABLE).update({"last_login_at": ts}).eq(
            "id", user_id
        ).execute()
    except Exception:
        pass


def _current_token_period_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m")


def _ensure_token_period(supabase: Client, user_id: str, prof: dict) -> dict:
    period = _current_token_period_utc()
    if (prof.get("monthly_tokens_period") or "").strip() == period:
        return prof
    try:
        supabase.table(SUPABASE_PROFILES_TABLE).update(
            {"monthly_tokens_used": 0, "monthly_tokens_period": period}
        ).eq("id", user_id).execute()
    except Exception:
        return prof
    prof = dict(prof)
    prof["monthly_tokens_used"] = 0
    prof["monthly_tokens_period"] = period
    return prof


def user_plan_limits(profile: dict | None) -> tuple[str, PlanLimits]:
    prof = _profile_with_session_email(profile)
    tier = resolve_plan_tier(prof)
    return tier, plan_limits(tier)


def _profile_with_session_email(profile: dict | None) -> dict:
    prof = dict(profile) if profile else {}
    if not str(prof.get("email") or "").strip():
        sess = get_session()
        if sess and str(sess.email or "").strip():
            prof["email"] = str(sess.email).strip()
    return prof


def refresh_test_total_quota(
    supabase: Client | None, user_id: str, profile: dict | None = None
) -> dict:
    """Conta EGO_TEST_TOTAL_EMAILS: zera contadores se bateu limite (só dev/teste)."""
    from ego_api.plans import is_test_total_email

    if not supabase or not user_id:
        return profile or {}
    prof = _profile_with_session_email(profile if profile is not None else load_profile(supabase, user_id))
    if not is_test_total_email(str(prof.get("email") or "")):
        return prof

    tier, limits = user_plan_limits(prof)
    prof = _ensure_token_period(supabase, user_id, prof)
    used = int(prof.get("monthly_tokens_used") or 0)
    text_used, voice_used = daily_message_counts_from_profile(prof)

    over_tokens = limits.monthly_tokens > 0 and used >= int(limits.monthly_tokens * 0.85)
    over_voice = (
        not limits.unlimited_daily_voice()
        and limits.daily_voice_messages > 0
        and voice_used >= limits.daily_voice_messages
    )
    over_text = (
        not limits.unlimited_daily_text()
        and limits.daily_text_messages > 0
        and text_used >= limits.daily_text_messages
    )
    if not over_tokens and not over_voice and not over_text:
        return prof

    ui = _parse_ui_state(prof)
    ui.pop("daily_messages", None)
    hoje = _today_iso()
    patch: dict = {
        "plan_tier": tier,
        "is_pro": True,
        "monthly_tokens_used": 0,
        "monthly_tokens_period": _current_token_period_utc(),
        "daily_tts_count": 0,
        "daily_usage_date": hoje,
        "ui_state": ui,
    }
    try:
        supabase.table(SUPABASE_PROFILES_TABLE).update(patch).eq("id", user_id).execute()
    except Exception:
        return prof
    prof.update(patch)
    return prof


def check_token_allowance(
    supabase: Client | None, user_id: str, profile: dict | None = None
) -> tuple[bool, str, int, int]:
    prof = _profile_with_session_email(
        profile if profile is not None else (load_profile(supabase, user_id) or {})
    )
    from ego_api.plans import is_test_total_email

    if is_test_total_email(str(prof.get("email") or "")):
        _, limits = user_plan_limits(prof)
        used = int(prof.get("monthly_tokens_used") or 0)
        return True, "", used, limits.monthly_tokens

    _, limits = user_plan_limits(prof)
    lim = limits.monthly_tokens
    if lim <= 0 or not supabase or not user_id:
        return True, "", 0, lim
    prof = _ensure_token_period(supabase, user_id, prof)
    used = int(prof.get("monthly_tokens_used") or 0)
    if used >= lim:
        label = plan_label(resolve_plan_tier(prof))
        return (
            False,
            f"Limite mensal de tokens atingido ({label}). Faça upgrade ou aguarde o próximo mês.",
            used,
            lim,
        )
    return True, "", used, lim


def add_tokens_used(
    supabase: Client | None, user_id: str, delta: int, profile: dict | None = None
) -> None:
    if not supabase or not user_id or delta <= 0:
        return
    prof = profile if profile is not None else (load_profile(supabase, user_id) or {})
    _, limits = user_plan_limits(prof)
    lim = limits.monthly_tokens
    if lim <= 0:
        return
    prof = _ensure_token_period(supabase, user_id, prof)
    used = int(prof.get("monthly_tokens_used") or 0)
    try:
        supabase.table(SUPABASE_PROFILES_TABLE).update(
            {"monthly_tokens_used": used + int(delta)}
        ).eq("id", user_id).execute()
    except Exception:
        pass


def _today_iso() -> str:
    """
    Data "de hoje" no fuso do utilizador (meia-noite local).

    Observação: usamos tz_offset_min (enviado pelo app) para calcular a data local.
    """
    sess = get_session()
    off_min = sess.tz_offset_min if sess and isinstance(sess.tz_offset_min, int) else 0
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    local = now_utc + datetime.timedelta(minutes=int(off_min))
    return local.date().isoformat()


def _today_start_utc_iso() -> str:
    """Timestamp ISO (UTC) correspondente à meia-noite local do utilizador."""
    sess = get_session()
    off_min = sess.tz_offset_min if sess and isinstance(sess.tz_offset_min, int) else 0
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    local_date = (now_utc + datetime.timedelta(minutes=int(off_min))).date()
    start_utc = datetime.datetime(
        local_date.year,
        local_date.month,
        local_date.day,
        tzinfo=datetime.timezone.utc,
    ) - datetime.timedelta(minutes=int(off_min))
    return start_utc.isoformat().replace("+00:00", "Z")


def _parse_ui_state(prof: dict) -> dict:
    raw = prof.get("ui_state")
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
    return {}


def daily_message_counts_from_profile(prof: dict) -> tuple[int, int]:
    """Contadores diários (texto, voz) quando o histórico é só no aparelho."""
    hoje = _today_iso()
    ui = _parse_ui_state(prof)
    du = ui.get("daily_messages")
    if not isinstance(du, dict) or (du.get("date") or "").strip() != hoje:
        return 0, 0
    return int(du.get("text") or 0), int(du.get("voice") or 0)


def increment_daily_message_usage(
    supabase: Client | None, user_id: str, *, is_voice: bool
) -> None:
    if not supabase or not user_id:
        return
    prof = load_profile(supabase, user_id) or {}
    prof = _ensure_daily_usage(supabase, user_id, prof)
    hoje = _today_iso()
    ui = _parse_ui_state(prof)
    du = ui.get("daily_messages")
    if not isinstance(du, dict) or (du.get("date") or "").strip() != hoje:
        du = {"date": hoje, "text": 0, "voice": 0}
    else:
        du = dict(du)
    if is_voice:
        du["voice"] = int(du.get("voice") or 0) + 1
    else:
        du["text"] = int(du.get("text") or 0) + 1
    du["date"] = hoje
    ui = dict(ui)
    ui["daily_messages"] = du
    try:
        supabase.table(SUPABASE_PROFILES_TABLE).update({"ui_state": ui}).eq(
            "id", user_id
        ).execute()
    except Exception:
        pass


def _ensure_daily_usage(supabase: Client, user_id: str, prof: dict) -> dict:
    hoje = _today_iso()
    if (prof.get("daily_usage_date") or "").strip() == hoje:
        return prof
    ui = _parse_ui_state(prof)
    ui.pop("daily_messages", None)
    try:
        supabase.table(SUPABASE_PROFILES_TABLE).update(
            {
                "daily_tts_count": 0,
                "daily_usage_date": hoje,
                "ui_state": ui,
            }
        ).eq("id", user_id).execute()
    except Exception:
        return prof
    prof = dict(prof)
    prof["daily_tts_count"] = 0
    prof["daily_usage_date"] = hoje
    if isinstance(prof.get("ui_state"), dict):
        prof["ui_state"] = ui
    return prof


def _count_user_messages_today(
    supabase: Client, user_id: str, *, voice_only: bool = False
) -> int:
    hoje = _today_start_utc_iso()
    try:
        q = (
            supabase.table(SUPABASE_HISTORY_TABLE)
            .select("id", count="exact")
            .eq("user_id", user_id)
            .eq("role", "user")
            .gte("created_at", hoje)
        )
        if voice_only:
            q = q.eq("content", VOICE_MESSAGE_MARKER)
        res = q.limit(0).execute()
        return int(res.count or 0)
    except Exception:
        return 0


def daily_text_messages_ok(
    supabase: Client | None,
    user_id: str,
    limits: PlanLimits,
    profile: dict | None = None,
) -> tuple[bool, int]:
    if not supabase or not user_id:
        return True, 0
    from ego_api.config import chat_local_history_enabled

    if chat_local_history_enabled():
        prof = profile if profile is not None else (load_profile(supabase, user_id) or {})
        prof = _ensure_daily_usage(supabase, user_id, prof)
        text_used, _voice_used = daily_message_counts_from_profile(prof)
        if limits.unlimited_daily_text() or beta_unlimited():
            return True, text_used
        return text_used < limits.daily_text_messages, text_used
    uso = _count_user_messages_today(supabase, user_id, voice_only=False)
    voice = _count_user_messages_today(supabase, user_id, voice_only=True)
    text_used = max(0, uso - voice)
    if limits.unlimited_daily_text() or beta_unlimited():
        return True, text_used
    return text_used < limits.daily_text_messages, text_used


def daily_voice_messages_ok(
    supabase: Client | None,
    user_id: str,
    limits: PlanLimits,
    profile: dict | None = None,
) -> tuple[bool, int]:
    if not supabase or not user_id:
        return True, 0
    from ego_api.config import chat_local_history_enabled

    if chat_local_history_enabled():
        prof = profile if profile is not None else (load_profile(supabase, user_id) or {})
        prof = _ensure_daily_usage(supabase, user_id, prof)
        _text_used, voice_used = daily_message_counts_from_profile(prof)
        if limits.unlimited_daily_voice() or beta_unlimited():
            return True, voice_used
        return voice_used < limits.daily_voice_messages, voice_used
    uso = _count_user_messages_today(supabase, user_id, voice_only=True)
    if limits.unlimited_daily_voice() or beta_unlimited():
        return True, uso
    return uso < limits.daily_voice_messages, uso


def daily_tts_ok(
    supabase: Client | None, user_id: str, limits: PlanLimits, profile: dict | None = None
) -> tuple[bool, int]:
    if not supabase or not user_id:
        return True, 0
    if limits.unlimited_daily_tts() or beta_unlimited():
        return True, 0
    prof = profile if profile is not None else (load_profile(supabase, user_id) or {})
    prof = _ensure_daily_usage(supabase, user_id, prof)
    used = int(prof.get("daily_tts_count") or 0)
    return used < limits.daily_tts_replies, used


def increment_daily_tts(supabase: Client | None, user_id: str) -> None:
    if not supabase or not user_id:
        return
    prof = load_profile(supabase, user_id) or {}
    prof = _ensure_daily_usage(supabase, user_id, prof)
    used = int(prof.get("daily_tts_count") or 0)
    try:
        supabase.table(SUPABASE_PROFILES_TABLE).update(
            {"daily_tts_count": used + 1, "daily_usage_date": _today_iso()}
        ).eq("id", user_id).execute()
    except Exception:
        pass


def count_agenda_items(supabase: Client | None, user_id: str) -> int:
    return len(list_agenda(supabase, user_id))


def count_active_reminders(supabase: Client | None, user_id: str) -> int:
    return len(list_reminders(supabase, user_id))


def agenda_limit_ok(
    supabase: Client | None, user_id: str, limits: PlanLimits
) -> tuple[bool, int]:
    n = count_agenda_items(supabase, user_id)
    if limits.unlimited_agenda() or beta_unlimited():
        return True, n
    return n < limits.max_agenda_items, n


def reminders_limit_ok(
    supabase: Client | None, user_id: str, limits: PlanLimits
) -> tuple[bool, int]:
    n = count_active_reminders(supabase, user_id)
    if limits.unlimited_reminders() or beta_unlimited():
        return True, n
    return n < limits.max_reminders, n


def daily_message_limit_ok(
    supabase: Client | None, user_id: str, limit: int = 0
) -> tuple[bool, int]:
    """Compatibilidade: limite global único (legado)."""
    if not supabase or not user_id:
        return True, 0
    uso = _count_user_messages_today(supabase, user_id, voice_only=False)
    if limit <= 0 or beta_unlimited():
        return True, uso
    return uso < limit, uso


def build_plan_access_payload(
    supabase: Client | None, user_id: str, profile: dict | None = None
) -> dict:
    prof = profile if profile is not None else (load_profile(supabase, user_id) or {})
    prof = refresh_test_total_quota(supabase, user_id, prof)
    prof = _profile_with_session_email(prof)
    tier, limits = user_plan_limits(prof)
    ok_access, status = check_access(supabase, user_id)
    ok_tok, msg_tok, used_tok, lim_tok = check_token_allowance(supabase, user_id, prof)
    ok_txt, txt_used = daily_text_messages_ok(supabase, user_id, limits, prof)
    ok_voice, voice_used = daily_voice_messages_ok(supabase, user_id, limits, prof)
    ok_tts, tts_used = daily_tts_ok(supabase, user_id, limits, prof)
    ag_ok, ag_n = agenda_limit_ok(supabase, user_id, limits)
    rem_ok, rem_n = reminders_limit_ok(supabase, user_id, limits)
    paid = tier != "essential"
    from ego_api.plans import is_test_total_email

    email = str(prof.get("email") or "").strip().lower()
    return {
        "access_allowed": ok_access,
        "access_status": status,
        "plan_tier": tier,
        "plan_label": plan_label(tier),
        "is_test_total": is_test_total_email(email),
        "plan_price_brl": PLAN_PRICES_BRL.get(tier, 0.0),
        "is_pro": paid,
        "monthly_tokens_ok": ok_tok,
        "monthly_tokens_message": msg_tok,
        "monthly_tokens_used": used_tok,
        "monthly_tokens_limit": lim_tok,
        "daily_text_messages_ok": ok_txt,
        "daily_text_messages_used": txt_used,
        "daily_text_messages_limit": limits.daily_text_messages,
        "daily_voice_messages_ok": ok_voice,
        "daily_voice_messages_used": voice_used,
        "daily_voice_messages_limit": limits.daily_voice_messages,
        "daily_tts_ok": ok_tts,
        "daily_tts_used": tts_used,
        "daily_tts_limit": limits.daily_tts_replies,
        "daily_messages_ok": ok_txt,
        "daily_messages_used": txt_used,
        "daily_messages_limit": limits.daily_text_messages,
        "agenda_ok": ag_ok,
        "agenda_used": ag_n,
        "agenda_limit": limits.max_agenda_items,
        "reminders_ok": rem_ok,
        "reminders_used": rem_n,
        "reminders_limit": limits.max_reminders,
        "audio_speed_allowed": list(limits.audio_speed_multipliers),
        "chat_max_turns": limits.chat_llm_max_turns,
        "chat_local_history": chat_local_history_enabled(),
        "team_seats": _team_seats_from_profile(prof),
        "plan_type": _plan_type_from_profile(prof),
    }


def _team_seats_from_profile(prof: dict) -> int | None:
    from ego_api.team_stripe_checkout import parse_team_seats

    ui = _parse_ui_state(prof)
    return parse_team_seats(ui.get("team_seats"))


def _plan_type_from_profile(prof: dict) -> str:
    ui = _parse_ui_state(prof)
    return str(ui.get("plan_type") or "individual").strip() or "individual"


def chat_local_history_enabled() -> bool:
    from ego_api.config import chat_local_history_enabled as _enabled

    return _enabled()


def _parse_ts_iso(value: str | None) -> datetime.datetime | None:
    if not value or not str(value).strip():
        return None
    try:
        dt = datetime.datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.astimezone(datetime.timezone.utc)
    except ValueError:
        return None


def check_access(supabase: Client | None, user_id: str) -> tuple[bool, str]:
    if not supabase:
        return True, "Modo Local"
    from ego_api.config import _ego_beta_deadline

    agora = datetime.datetime.now(datetime.timezone.utc)
    beta_fim = _ego_beta_deadline()
    if beta_unlimited():
        return True, "Beta (sem limite)"
    if beta_fim and agora < beta_fim:
        return True, "Beta grátis"
    try:
        res = (
            supabase.table(SUPABASE_PROFILES_TABLE)
            .select("created_at,is_pro,plan_tier")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            return True, f"Trial ({EGO_TRIAL_DAYS} dias restantes)"
        data = rows[0]
        tier = resolve_plan_tier(data)
        if tier != "essential":
            return True, plan_label(tier)
        if bool(data.get("is_pro", False)):
            return True, plan_label("connection")
        created_at = data.get("created_at")
        if not created_at:
            return True, f"Trial ({EGO_TRIAL_DAYS} dias restantes)"
        data_criacao = _parse_ts_iso(str(created_at))
        if not data_criacao:
            return True, f"Trial ({EGO_TRIAL_DAYS} dias restantes)"
        dias = max(0, (agora.date() - data_criacao.date()).days)
        restantes = EGO_TRIAL_DAYS - dias
        if restantes >= 0:
            return True, f"Trial ({restantes} dias restantes)"
        return False, "Expirado"
    except Exception:
        return True, f"Trial ({EGO_TRIAL_DAYS} dias restantes)"


def list_reminders(supabase: Client | None, user_id: str) -> list[dict]:
    if not supabase or not user_id:
        return []
    apply_user_auth(supabase)
    now = datetime.datetime.now(datetime.timezone.utc)
    start = now.isoformat()
    end = (now + datetime.timedelta(days=AGENDA_HORIZON_DAYS)).isoformat()
    try:
        res = (
            supabase.table(SUPABASE_REMINDERS_TABLE)
            .select("*")
            .eq("user_id", user_id)
            .eq("dismissed", False)
            .gte("scheduled_at", start)
            .lte("scheduled_at", end)
            .order("scheduled_at")
            .execute()
        )
        return list(res.data or [])
    except Exception:
        return []


def list_agenda(supabase: Client | None, user_id: str) -> list[dict]:
    if not supabase or not user_id:
        return []
    apply_user_auth(supabase)
    try:
        res = (
            supabase.table(SUPABASE_AGENDA_TABLE)
            .select("id,titulo,horario,dias_da_semana,data_criacao")
            .eq("user_id", user_id)
            .order("data_criacao", desc=True)
            .execute()
        )
        return list(res.data or [])
    except Exception:
        return []


def _persona_row_exists(client: Client | None, user_id: str) -> bool:
    if not client or not user_id:
        return False
    try:
        res = (
            client.table(SUPABASE_PERSONA_TABLE)
            .select("user_id")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        return bool(res.data)
    except Exception:
        return False


def persona_is_configured(supabase: Client | None, user_id: str) -> bool:
    """True só após escolha explícita (PUT /persona), não por defaults f1."""
    if not user_id:
        return False
    from ego_api.supabase_client import create_service_client

    admin = create_service_client()
    for client in (supabase, admin):
        if not client:
            continue
        prof = load_profile(client, user_id) if client is supabase else (
            _load_profile_raw(client, user_id)
        )
        if prof:
            ui = _parse_ui_state(prof)
            if str(ui.get("persona_chosen_at") or "").strip():
                return True
    if supabase and apply_user_auth(supabase) and _persona_row_exists(supabase, user_id):
        return True
    if admin and _persona_row_exists(admin, user_id):
        return True
    return False


def _read_persona_from_client(client: Client | None, user_id: str) -> tuple[str, str] | None:
    if not client or not user_id:
        return None
    try:
        res = (
            client.table(SUPABASE_PERSONA_TABLE)
            .select("avatar_id,voice_id")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            return None
        data = rows[0]
        aid = str(data.get("avatar_id") or "").strip()
        if not aid:
            return None
        vid = str(data.get("voice_id") or "").strip() or "vf1"
        return aid, vid
    except Exception:
        return None


def _load_profile_raw(client: Client | None, user_id: str) -> dict | None:
    """Perfil sem JWT do utilizador (service role)."""
    if not client or not user_id:
        return None
    try:
        res = (
            client.table(SUPABASE_PROFILES_TABLE)
            .select("*")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        return rows[0] if rows else None
    except Exception:
        return None


def _persona_pair_from_profile(prof: dict | None) -> tuple[str, str] | None:
    if not prof:
        return None
    ui = _parse_ui_state(prof)
    aid = str(ui.get("avatar_id") or "").strip()
    if not aid:
        return None
    vid = str(ui.get("voice_id") or "").strip() or "vf1"
    return aid, vid


def _read_persona_from_profile_ui(
    supabase: Client | None, user_id: str
) -> tuple[str, str] | None:
    prof = load_profile(supabase, user_id) if supabase and user_id else None
    return _persona_pair_from_profile(prof)


def load_persona(supabase: Client | None, user_id: str) -> tuple[str, str]:
    """Lê persona: user_personas primeiro (escolha guardada), depois ui_state no perfil."""
    if not user_id:
        return "f1", "vf1"

    from ego_api.persona import normalize_persona_pair
    from ego_api.supabase_client import create_service_client

    admin = create_service_client()

    def _read_pair(client: Client | None) -> tuple[str, str] | None:
        if not client:
            return None
        pair = _read_persona_from_client(client, user_id)
        if pair:
            return normalize_persona_pair(pair[0], pair[1])
        pair = _read_persona_from_profile(
            _load_profile_raw(client, user_id)
            if client is admin
            else (load_profile(client, user_id) if apply_user_auth(client) else None)
        )
        if pair:
            return normalize_persona_pair(pair[0], pair[1])
        return None

    if admin:
        got = _read_pair(admin)
        if got:
            return got

    if supabase and apply_user_auth(supabase):
        got = _read_pair(supabase)
        if got:
            return got

    return "f1", "vf1"


def _upsert_persona_row(client: Client, row: dict) -> bool:
    uid = row.get("user_id")
    aid = row.get("avatar_id")
    if not uid or not aid:
        return False
    try:
        client.table(SUPABASE_PERSONA_TABLE).upsert(
            row, on_conflict="user_id"
        ).execute()
        chk = (
            client.table(SUPABASE_PERSONA_TABLE)
            .select("avatar_id,voice_id")
            .eq("user_id", uid)
            .limit(1)
            .execute()
        )
        if not chk.data:
            return False
        got = str(chk.data[0].get("avatar_id") or "").strip()
        return got == str(aid).strip()
    except Exception:
        return False


def _mirror_persona_to_profile(
    supabase: Client | None, user_id: str, avatar_id: str, voice_id: str
) -> bool:
    """Cópia em profiles.ui_state — fonte de leitura se RLS bloquear user_personas."""
    if not supabase or not user_id:
        return False
    from ego_api.persona import assistant_display_name_for_avatar
    from ego_api.supabase_client import create_service_client

    admin = create_service_client()
    if admin is supabase:
        prof = _load_profile_raw(supabase, user_id) or {}
    else:
        prof = load_profile(supabase, user_id) or {}
    ui = _parse_ui_state(prof)
    name = assistant_display_name_for_avatar(avatar_id)
    merged = {
        **ui,
        "avatar_id": avatar_id,
        "voice_id": voice_id,
        "ego_assistant_display_name": name,
        "persona_chosen_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    ok, _ = update_profile_fields(supabase, user_id, {"ui_state": merged})
    return ok


def save_persona(
    supabase: Client | None,
    user_id: str,
    avatar_id: str,
    voice_id: str,
) -> tuple[bool, str]:
    if not supabase or not user_id:
        return False, "Sessão indisponível."
    if not apply_user_auth(supabase):
        return False, "Sessão expirada."
    aid = (avatar_id or "f1").strip()[:32]
    vid = (voice_id or "vf1").strip()[:32]
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    row = {"user_id": user_id, "avatar_id": aid, "voice_id": vid, "updated_at": now}
    user_err = ""

    from ego_api.supabase_client import create_service_client

    admin = create_service_client()

    mirrored = False
    for client in (admin, supabase):
        if not client:
            continue
        try:
            if _mirror_persona_to_profile(client, user_id, aid, vid):
                mirrored = True
        except Exception:
            pass

    saved = False
    if admin:
        try:
            if _upsert_persona_row(admin, row):
                saved = True
        except Exception as exc:
            err = str(exc).lower()
            if "user_personas" in err or "42p01" in err or "does not exist" in err:
                return False, "Tabela user_personas em falta. Execute supabase/bootstrap_ego_schema.sql."
            if not mirrored:
                user_err = str(exc)

    if not saved:
        try:
            if _upsert_persona_row(supabase, row):
                saved = True
        except Exception as exc:
            user_err = str(exc) or user_err
            err = user_err.lower()
            if "user_personas" in err or "42p01" in err or "does not exist" in err:
                return False, "Tabela user_personas em falta. Execute supabase/bootstrap_ego_schema.sql."

    if not saved and not mirrored:
        return (
            False,
            user_err
            or "Não foi possível guardar avatar/voz. Adicione SUPABASE_SERVICE_ROLE_KEY no Railway.",
        )

    loaded_a, loaded_v = load_persona(supabase, user_id)
    if loaded_a == aid and loaded_v == vid:
        return True, ""

    if mirrored:
        return True, ""

    return (
        False,
        f"A escolha não ficou guardada (servidor devolveu {loaded_a}). "
        "Configure SUPABASE_SERVICE_ROLE_KEY no Railway e faça redeploy.",
    )


def save_feedback(
    supabase: Client | None,
    user_id: str,
    message_id: str,
    vote: int,
    model_provider: str = "Gemini",
) -> bool:
    if not supabase or not user_id or vote not in (1, -1):
        return False
    apply_user_auth(supabase)
    try:
        supabase.table(SUPABASE_FEEDBACK_TABLE).insert(
            {
                "user_id": user_id,
                "chat_message_id": message_id[:500],
                "vote": vote,
                "model_provider": (model_provider or "")[:80],
            }
        ).execute()
        return True
    except Exception:
        return False


def _profile_update_error_message(exc: str) -> str:
    low = (exc or "").lower()
    if "profiles_phone_unique" in low or (
        "duplicate key" in low and "phone" in low
    ):
        return "Este telefone já está associado a outra conta."
    return exc or "Não foi possível atualizar o perfil."


def _profile_fields_match(prof: dict | None, payload: dict) -> bool:
    if not prof:
        return False
    for key, expected in payload.items():
        actual = prof.get(key)
        if key == "phone":
            if str(actual or "").strip() != str(expected or "").strip():
                return False
        elif key == "ui_state" and isinstance(expected, dict):
            current = _parse_ui_state(prof)
            for ui_key, ui_val in expected.items():
                if current.get(ui_key) != ui_val:
                    return False
        elif actual != expected:
            return False
    return True


def upsert_profile_phone(
    supabase: Client | None,
    user_id: str,
    phone: str,
    *,
    email: str = "",
    full_name: str = "",
) -> tuple[bool, str]:
    """Garante linha em profiles e grava telefone (service role)."""
    from ego_api.request_ctx import get_session
    from ego_api.supabase_client import create_service_client

    ph = str(phone or "").strip()
    if not ph:
        return False, "Telefone inválido."

    admin = create_service_client()
    sess = get_session()
    em = (email or "").strip()[:254] or (
        str(sess.email).strip()[:254] if sess and sess.email else ""
    )
    display = (full_name or "").strip()
    if not display and sess and sess.user_name:
        display = str(sess.user_name).strip()
    if not display:
        display = "Usuário"

    if not admin:
        ensure_user_profile(
            supabase, user_id, email=em, full_name=display, phone=ph
        )
        ok, err = update_profile_fields(supabase, user_id, {"phone": ph})
        if ok:
            return True, ""
        return False, err or "Não foi possível atualizar o perfil."

    prof = _load_profile_raw(admin, user_id)
    try:
        if prof:
            admin.table(SUPABASE_PROFILES_TABLE).update({"phone": ph}).eq(
                "id", user_id
            ).execute()
        else:
            admin.table(SUPABASE_PROFILES_TABLE).insert(
                {
                    "id": user_id,
                    "phone": ph,
                    "full_name": display[:200],
                    "email": em or None,
                    "country": "Brasil",
                    "document_type": "",
                }
            ).execute()
    except Exception as exc:
        return False, _profile_update_error_message(str(exc))

    saved = _load_profile_raw(admin, user_id)
    if not _profile_fields_match(saved, {"phone": ph}):
        return False, "Não foi possível atualizar o perfil."
    return True, ""


def _verify_profile_update(
    supabase: Client | None, user_id: str, payload: dict
) -> bool:
    from ego_api.supabase_client import create_service_client

    admin = create_service_client()
    if admin:
        prof = _load_profile_raw(admin, user_id)
        if _profile_fields_match(prof, payload):
            return True
    if supabase:
        prof = load_profile(supabase, user_id)
        if _profile_fields_match(prof, payload):
            return True
    return False


def update_profile_fields(
    supabase: Client | None, user_id: str, fields: dict
) -> tuple[bool, str]:
    if not supabase or not user_id:
        return False, "Sem cliente Supabase."
    allowed = {"full_name", "ui_state", "country", "document_type", "phone"}
    payload = {k: v for k, v in fields.items() if k in allowed}
    if not payload:
        return False, "Nenhum campo válido para atualizar."

    from ego_api.supabase_client import create_service_client

    admin = create_service_client()
    clients: list[tuple[Client | None, bool]] = []
    if "phone" in payload and admin:
        clients.append((admin, False))
    clients.append((supabase, True))
    if admin and not any(client is admin for client, _ in clients):
        clients.append((admin, False))

    last_err = ""
    for client, use_user_auth in clients:
        if not client:
            continue
        try:
            if use_user_auth:
                apply_user_auth(client)
            client.table(SUPABASE_PROFILES_TABLE).update(payload).eq(
                "id", user_id
            ).execute()
            if _verify_profile_update(supabase, user_id, payload):
                return True, ""
        except Exception as exc:
            last_err = _profile_update_error_message(str(exc))
            if "já está associado" in last_err:
                return False, last_err

    return False, last_err or "Não foi possível atualizar o perfil."


# --- Lembretes / agenda (lógica espelhada de app.py) ---

def _agenda_horizon_utc(ref: datetime.datetime | None = None) -> datetime.datetime:
    base = ref or datetime.datetime.now(datetime.timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=datetime.timezone.utc)
    return base + datetime.timedelta(days=AGENDA_HORIZON_DAYS)


def _coerce_reminder_to_utc(
    value: object, *, ref: datetime.datetime | None = None
) -> datetime.datetime | None:
    ref = ref or datetime.datetime.now(datetime.timezone.utc)
    if value is None or isinstance(value, (dict, list, bool)):
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.datetime.fromtimestamp(float(value), tz=datetime.timezone.utc)
        except (OSError, OverflowError, ValueError):
            return None
    if isinstance(value, datetime.datetime):
        dt = value
        if dt.tzinfo is None:
            from ego_api.schedule_tz import tzinfo_from_session
            from ego_api.request_ctx import get_session

            tz = tzinfo_from_session(get_session())
            dt = dt.replace(tzinfo=tz or datetime.timezone.utc)
        return dt.astimezone(datetime.timezone.utc)
    raw = str(value).strip()
    if not raw:
        return None
    has_tz = bool(
        re.search(r"(?:Z|[+-]\d{2}:?\d{2})$", raw.replace(" ", "T"), re.I)
    )
    try:
        clean = raw.replace("Z", "+00:00")
        if " " in clean and "T" not in clean:
            clean = clean.replace(" ", "T", 1)
        dt = datetime.datetime.fromisoformat(clean)
    except ValueError:
        return _parse_ts_iso(raw)
    if dt.tzinfo is None:
        if has_tz:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        else:
            from ego_api.schedule_tz import tzinfo_from_session
            from ego_api.request_ctx import get_session

            tz = tzinfo_from_session(get_session())
            dt = dt.replace(tzinfo=tz or datetime.timezone.utc)
    return dt.astimezone(datetime.timezone.utc)


def normalize_scheduled_at(value: object) -> datetime.datetime | None:
    dt_utc = _coerce_reminder_to_utc(value)
    if not dt_utc:
        return None
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    if dt_utc < now_utc - REMINDER_PAST_GRACE:
        return None
    if dt_utc > _agenda_horizon_utc(now_utc):
        return None
    return dt_utc


def _scheduled_at_api_iso(value: object) -> str:
    dt = _coerce_reminder_to_utc(value)
    if not dt:
        return str(value or "")
    u = dt.astimezone(datetime.timezone.utc)
    return u.strftime("%Y-%m-%dT%H:%M:%S") + (
        f".{u.microsecond // 1000:03d}" if u.microsecond else ""
    ) + "Z"


def insert_reminder(
    supabase: Client | None,
    user_id: str,
    *,
    title: str,
    scheduled_at: object,
    announce: str = "",
) -> tuple[bool, str, dict | None]:
    if not supabase or not user_id:
        return False, "Sessão indisponível.", None
    norm = normalize_scheduled_at(scheduled_at)
    if not norm:
        return False, "Data/hora inválida ou fora do horizonte permitido.", None
    if not apply_user_auth(supabase):
        return False, "Sessão expirada.", None
    row = {
        "user_id": user_id,
        "title": (title or "Lembrete")[:500],
        "scheduled_at": norm.isoformat(),
        "announce": (announce or title or "")[:2000],
    }
    try:
        from ego_api.supabase_client import insert_returning_rows, insert_with_admin_fallback

        inserted = insert_returning_rows(supabase, SUPABASE_REMINDERS_TABLE, row)
        if not inserted:
            inserted = insert_with_admin_fallback(supabase, SUPABASE_REMINDERS_TABLE, row)
        if not inserted:
            return (
                False,
                "Não foi possível gravar o compromisso. Saia e entre de novo.",
                None,
            )
        data = inserted[0]
        if isinstance(data, dict):
            from ego_api.json_util import sanitize_for_json

            data = sanitize_for_json(data)
            if data.get("scheduled_at"):
                data = {
                    **data,
                    "scheduled_at": _scheduled_at_api_iso(data.get("scheduled_at")),
                }
        return True, "", data
    except Exception as e:
        return False, str(e), None


def dismiss_reminder(supabase: Client | None, user_id: str, reminder_id: str) -> bool:
    if not supabase or not user_id:
        return False
    apply_user_auth(supabase)
    try:
        supabase.table(SUPABASE_REMINDERS_TABLE).update({"dismissed": True}).eq(
            "id", reminder_id
        ).eq("user_id", user_id).execute()
        return True
    except Exception:
        return False


def snooze_reminder(
    supabase: Client | None, user_id: str, reminder_id: str, minutes: int = 5
) -> bool:
    if not supabase or not user_id:
        return False
    until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=minutes)
    apply_user_auth(supabase)
    try:
        supabase.table(SUPABASE_REMINDERS_TABLE).update(
            {"snooze_until": until.isoformat()}
        ).eq("id", reminder_id).eq("user_id", user_id).execute()
        return True
    except Exception:
        return False


def _parse_horario_br(v: object) -> datetime.time | None:
    if v is None:
        return None
    raw = str(v).strip()
    if not raw:
        return None
    parts = raw.replace(".", ":").split(":")
    try:
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        s = int(parts[2]) if len(parts) > 2 else 0
        if not (0 <= h <= 23 and 0 <= m <= 59 and 0 <= s <= 59):
            return None
        return datetime.time(h, m, s)
    except (ValueError, IndexError):
        return None


def _normalize_agenda_dias_csv(raw: str) -> tuple[str | None, str | None]:
    if not raw or not str(raw).strip():
        return None, "dias_da_semana vazio"
    tokens: list[str] = []
    for part in re.split(r"[,;\s]+", str(raw).lower()):
        p = part.strip()[:3]
        if not p:
            continue
        aliases = {
            "segunda": "seg",
            "terça": "ter",
            "terca": "ter",
            "quarta": "qua",
            "quinta": "qui",
            "sexta": "sex",
            "sábado": "sab",
            "sabado": "sab",
            "domingo": "dom",
        }
        code = aliases.get(part.strip().lower(), p)
        if code in VALID_AGENDA_DOW and code not in tokens:
            tokens.append(code)
    if not tokens:
        return None, "Nenhum dia válido (use seg, ter, qua, qui, sex, sab, dom)."
    return ",".join(tokens), None


def insert_agenda(
    supabase: Client | None,
    user_id: str,
    *,
    titulo: str,
    horario: object,
    dias_da_semana: str,
) -> tuple[bool, str, dict | None]:
    if not supabase or not user_id:
        return False, "Sessão indisponível.", None
    t = _parse_horario_br(horario)
    if not t:
        return False, "Horário inválido (use HH:MM).", None
    dias_ok, err = _normalize_agenda_dias_csv(dias_da_semana)
    if not dias_ok:
        return False, err or "Dias inválidos.", None
    if not apply_user_auth(supabase):
        return False, "Sessão expirada.", None
    row = {
        "user_id": user_id,
        "titulo": ((titulo or "").strip()[:500] or "Compromisso"),
        "horario": t.strftime("%H:%M:%S"),
        "dias_da_semana": dias_ok[:500],
    }
    try:
        from ego_api.supabase_client import insert_returning_rows

        inserted = insert_returning_rows(supabase, SUPABASE_AGENDA_TABLE, row)
        if not inserted:
            return (
                False,
                "Não foi possível gravar o hábito. Saia e entre de novo.",
                None,
            )
        return True, "", inserted[0]
    except Exception as e:
        return False, str(e), None


def delete_agenda(supabase: Client | None, user_id: str, agenda_id: str) -> bool:
    if not supabase or not user_id or not agenda_id:
        return False
    apply_user_auth(supabase)
    try:
        supabase.table(SUPABASE_AGENDA_TABLE).delete().eq("id", agenda_id).eq(
            "user_id", user_id
        ).execute()
        return True
    except Exception:
        return False


def build_agenda_context_for_llm(supabase: Client | None, user_id: str) -> str:
    if not supabase or not user_id:
        return "\n\n=== CURRENT USER AGENDA ===\n(not logged in)\n=== END AGENDA ===\n"
    try:
        recurring = list_agenda(supabase, user_id)
        reminders = list_reminders(supabase, user_id)
    except Exception:
        return "\n\n=== CURRENT USER AGENDA ===\n(unavailable)\n=== END AGENDA ===\n"
    now = datetime.datetime.now().astimezone()
    wk = DOW_PT_ORDER[now.weekday()]
    lines = [
        "",
        "=== CURRENT USER AGENDA (Supabase) ===",
        f"Loaded at: {now.strftime('%d/%m/%Y %H:%M')}",
        "",
    ]
    if recurring:
        lines.append("Recurring weekly habits:")
        for row in recurring[:35]:
            tit = (row.get("titulo") or "—").strip()
            hor = str(row.get("horario") or "")[:5]
            dias = row.get("dias_da_semana") or ""
            lines.append(f"  - {tit} | {hor} | days: {dias}")
    else:
        lines.append("Recurring weekly habits: (none)")
    lines.append("")
    if reminders:
        lines.append("One-off meetings / reminders:")
        for row in reminders[:45]:
            tit = (row.get("title") or "—").strip()
            sch = _parse_ts_iso(row.get("scheduled_at"))
            when = sch.astimezone().strftime("%d/%m/%Y %H:%M %Z") if sch else "—"
            lines.append(f"  - {tit} | {when}")
    else:
        lines.append("One-off meetings / reminders: (none)")
    lines.append("=== END AGENDA ===")
    return "\n".join(lines)
