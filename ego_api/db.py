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


def ensure_user_profile(
    supabase: Client | None,
    user_id: str,
    *,
    email: str = "",
    full_name: str = "",
) -> tuple[bool, str]:
    if not supabase or not user_id:
        return False, "Cliente Supabase ou user_id em falta."
    apply_user_auth(supabase)
    display = (full_name or "").strip() or "Usuário"
    em = (email or "").strip()[:254]
    row = {
        "id": user_id,
        "full_name": display[:200],
        "email": em or None,
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
                {"full_name": row["full_name"], "email": row["email"]}
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
    prof = dict(profile) if profile else {}
    if not str(prof.get("email") or "").strip():
        sess = get_session()
        if sess and str(sess.email or "").strip():
            prof["email"] = str(sess.email).strip()
    tier = resolve_plan_tier(prof)
    return tier, plan_limits(tier)


def check_token_allowance(
    supabase: Client | None, user_id: str, profile: dict | None = None
) -> tuple[bool, str, int, int]:
    prof = profile if profile is not None else (load_profile(supabase, user_id) or {})
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


def _ensure_daily_usage(supabase: Client, user_id: str, prof: dict) -> dict:
    hoje = _today_iso()
    if (prof.get("daily_usage_date") or "").strip() == hoje:
        return prof
    try:
        supabase.table(SUPABASE_PROFILES_TABLE).update(
            {"daily_tts_count": 0, "daily_usage_date": hoje}
        ).eq("id", user_id).execute()
    except Exception:
        return prof
    prof = dict(prof)
    prof["daily_tts_count"] = 0
    prof["daily_usage_date"] = hoje
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
    supabase: Client | None, user_id: str, limits: PlanLimits
) -> tuple[bool, int]:
    if not supabase or not user_id:
        return True, 0
    uso = _count_user_messages_today(supabase, user_id, voice_only=False)
    voice = _count_user_messages_today(supabase, user_id, voice_only=True)
    text_used = max(0, uso - voice)
    if limits.unlimited_daily_text() or beta_unlimited():
        return True, text_used
    return text_used < limits.daily_text_messages, text_used


def daily_voice_messages_ok(
    supabase: Client | None, user_id: str, limits: PlanLimits
) -> tuple[bool, int]:
    if not supabase or not user_id:
        return True, 0
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
    tier, limits = user_plan_limits(prof)
    ok_access, status = check_access(supabase, user_id)
    ok_tok, msg_tok, used_tok, lim_tok = check_token_allowance(supabase, user_id, prof)
    ok_txt, txt_used = daily_text_messages_ok(supabase, user_id, limits)
    ok_voice, voice_used = daily_voice_messages_ok(supabase, user_id, limits)
    ok_tts, tts_used = daily_tts_ok(supabase, user_id, limits, prof)
    ag_ok, ag_n = agenda_limit_ok(supabase, user_id, limits)
    rem_ok, rem_n = reminders_limit_ok(supabase, user_id, limits)
    paid = tier != "essential"
    return {
        "access_allowed": ok_access,
        "access_status": status,
        "plan_tier": tier,
        "plan_label": plan_label(tier),
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
    }


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


def persona_is_configured(supabase: Client | None, user_id: str) -> bool:
    if not supabase or not user_id:
        return False
    apply_user_auth(supabase)
    try:
        res = (
            supabase.table(SUPABASE_PERSONA_TABLE)
            .select("user_id")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        return bool(res.data)
    except Exception:
        return False


def load_persona(supabase: Client | None, user_id: str) -> tuple[str, str]:
    if not supabase or not user_id:
        return "f1", "vf1"
    apply_user_auth(supabase)
    try:
        res = (
            supabase.table(SUPABASE_PERSONA_TABLE)
            .select("avatar_id,voice_id")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            return "f1", "vf1"
        data = rows[0]
        return data.get("avatar_id", "f1"), data.get("voice_id", "vf1")
    except Exception:
        return "f1", "vf1"


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
    try:
        res = (
            supabase.table(SUPABASE_PERSONA_TABLE)
            .upsert(row, on_conflict="user_id")
            .execute()
        )
        if res.data:
            return True, ""
        chk = (
            supabase.table(SUPABASE_PERSONA_TABLE)
            .select("avatar_id,voice_id")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if chk.data and chk.data[0].get("avatar_id") == aid:
            return True, ""
        return False, "Não foi possível guardar avatar/voz. Verifique a tabela user_personas."
    except Exception as exc:
        err = str(exc).lower()
        if "user_personas" in err or "42p01" in err or "does not exist" in err:
            return False, "Tabela user_personas em falta. Execute supabase/bootstrap_ego_schema.sql."
        return False, str(exc)


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


def update_profile_fields(
    supabase: Client | None, user_id: str, fields: dict
) -> tuple[bool, str]:
    if not supabase or not user_id:
        return False, "Sem cliente Supabase."
    allowed = {"full_name", "ui_state", "country", "document_type"}
    payload = {k: v for k, v in fields.items() if k in allowed}
    if not payload:
        return False, "Nenhum campo válido para atualizar."
    apply_user_auth(supabase)
    try:
        supabase.table(SUPABASE_PROFILES_TABLE).update(payload).eq("id", user_id).execute()
        return True, ""
    except Exception as exc:
        return False, str(exc)


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
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.astimezone(datetime.timezone.utc)
    parsed = _parse_ts_iso(str(value))
    return parsed


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
        res = supabase.table(SUPABASE_REMINDERS_TABLE).insert(row).select("*").execute()
        data = (res.data or [{}])[0]
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
        res = supabase.table(SUPABASE_AGENDA_TABLE).insert(row).select("*").execute()
        return True, "", (res.data or [{}])[0]
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
    recurring = list_agenda(supabase, user_id)
    reminders = list_reminders(supabase, user_id)
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
