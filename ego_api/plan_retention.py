"""E-mail + push automáticos: trial (3 dias antes / expirado) e limite diário.

Funciona para iOS e Android (mesma API).

WhatsApp automático (Meta Business API / Twilio): FASE 2 — fora do scope por custo.
Não implementar nem activar vars até decisão explícita. Agora: só e-mail (Brevo) + push (Expo).

Partilha manual no app (botão «enviar no WhatsApp») continua — é grátis, iniciada pelo utilizador.
"""

from __future__ import annotations

import datetime
import html
import logging
import threading
import time
from typing import Any, Literal

from ego_api.config import EGO_TRIAL_DAYS, read_env
from ego_api.db import _parse_ui_state, load_profile
from ego_api.expo_push import send_expo_push
from ego_api.signup_emails import (
    _first_name,
    _parse_profile_ts,
    email_configured,
    send_signup_email,
    signup_emails_enabled,
)
from ego_api.supabase_client import create_service_client

_LOG = logging.getLogger(__name__)

RetentionKind = Literal["trial_3d", "trial_expired", "daily_limit"]

KEY_TRIAL_3D_EMAIL = "retention_trial_3d_email_at"
KEY_TRIAL_3D_PUSH = "retention_trial_3d_push_at"
KEY_TRIAL_END_EMAIL = "retention_trial_end_email_at"
KEY_TRIAL_END_PUSH = "retention_trial_end_push_at"
KEY_DAILY_LIMIT_EMAIL = "retention_daily_limit_email_date"
KEY_DAILY_LIMIT_PUSH = "retention_daily_limit_push_date"

_background_started = False


def plan_retention_enabled() -> bool:
    return read_env("EGO_PLAN_RETENTION_ENABLED", "1").lower() not in (
        "0",
        "false",
        "no",
        "off",
    )


def plan_retention_push_enabled() -> bool:
    return read_env("EGO_PLAN_RETENTION_PUSH", "1").lower() not in (
        "0",
        "false",
        "no",
        "off",
    )


def plans_checkout_url() -> str:
    raw = read_env("EGO_APP_PLANS_URL", "").strip()
    if raw:
        return raw.rstrip("/")
    site = read_env("EGO_APP_SIGNUP_URL", "https://egoai.com.br").strip().rstrip("/")
    return f"{site}/planos"


def plan_retention_status() -> dict[str, Any]:
    return {
        "enabled": plan_retention_enabled(),
        "email": signup_emails_enabled() and email_configured(),
        "push": plan_retention_push_enabled(),
        "plans_url": plans_checkout_url(),
        "trial_days": EGO_TRIAL_DAYS,
        "whatsapp": "not_configured",
    }


def trial_days_remaining(created_at: str | None) -> int | None:
    dt = _parse_profile_ts(created_at)
    if not dt:
        return None
    agora = datetime.datetime.now(datetime.timezone.utc)
    dias = max(0, (agora.date() - dt.astimezone(datetime.timezone.utc).date()).days)
    return EGO_TRIAL_DAYS - dias


def _is_paid_essential(prof: dict[str, Any]) -> bool:
    from ego_api.plans import resolve_plan_tier

    tier = resolve_plan_tier(prof)
    if tier != "essential":
        return True
    return bool(prof.get("is_pro"))


def _profile_email(prof: dict[str, Any]) -> str:
    return str(prof.get("email") or "").strip()


def _expo_token(prof: dict[str, Any]) -> str:
    ui = _parse_ui_state(prof)
    tok = str(ui.get("expo_push_token") or "").strip()
    if tok.startswith("ExponentPushToken[") or tok.startswith("ExpoPushToken["):
        return tok
    return ""


def _today_utc_date() -> str:
    return datetime.datetime.now(datetime.timezone.utc).date().isoformat()


def _mark_ui_flags(user_id: str, patch: dict[str, str]) -> None:
    svc = create_service_client()
    if not svc or not user_id or not patch:
        return
    try:
        prof = load_profile(svc, user_id) or {}
        ui = _parse_ui_state(prof)
        ui.update(patch)
        svc.table("profiles").update({"ui_state": ui}).eq("id", user_id).execute()
    except Exception as exc:
        _LOG.warning("plan_retention ui_state patch failed %s: %s", user_id[:8], exc)


def _already_sent(ui: dict[str, Any], kind: RetentionKind) -> bool:
    if kind == "trial_3d":
        return bool(ui.get(KEY_TRIAL_3D_EMAIL) or ui.get(KEY_TRIAL_3D_PUSH))
    if kind == "trial_expired":
        return bool(ui.get(KEY_TRIAL_END_EMAIL) or ui.get(KEY_TRIAL_END_PUSH))
    today = _today_utc_date()
    return ui.get(KEY_DAILY_LIMIT_EMAIL) == today or ui.get(KEY_DAILY_LIMIT_PUSH) == today


def _email_bodies(
    kind: RetentionKind, name: str, plans_url: str
) -> tuple[str, str, str]:
    safe_name = html.escape(name)
    safe_url = html.escape(plans_url)
    if kind == "trial_3d":
        subject = "Faltam 3 dias do seu teste grátis no EGO-AI"
        text = f"""Oi, {name}!

Faltam 3 dias do seu teste grátis de {EGO_TRIAL_DAYS} dias no EGO-AI.

Para continuar com chat, voz, agenda e Monstrinhos sem interrupção, escolha um plano:

{plans_url}

Use o mesmo e-mail do cadastro ({name}) ao assinar.

Equipe EGO-AI
"""
        html_body = f"""<!DOCTYPE html><html lang="pt-BR"><body style="font-family:Segoe UI,Arial,sans-serif;line-height:1.55;">
<p>Oi, <strong>{safe_name}</strong>!</p>
<p>Faltam <strong>3 dias</strong> do seu teste grátis de {EGO_TRIAL_DAYS} dias no EGO-AI.</p>
<p><a href="{safe_url}">Ver planos e assinar</a> — use o mesmo e-mail do app.</p>
</body></html>"""
        return subject, text, html_body

    if kind == "trial_expired":
        subject = "Seu teste EGO-AI terminou — continue com um plano"
        text = f"""Oi, {name}!

Seu teste grátis de {EGO_TRIAL_DAYS} dias no EGO-AI terminou.

Para voltar a conversar com seu avatar, usar voz e agenda:

{plans_url}

Assine com o mesmo e-mail da sua conta no app.

Equipe EGO-AI
"""
        html_body = f"""<!DOCTYPE html><html lang="pt-BR"><body style="font-family:Segoe UI,Arial,sans-serif;line-height:1.55;">
<p>Oi, <strong>{safe_name}</strong>!</p>
<p>Seu teste grátis terminou. <a href="{safe_url}">Escolha um plano</a> com o mesmo e-mail do app.</p>
</body></html>"""
        return subject, text, html_body

    subject = "Limite de hoje atingido — planos com mais uso"
    text = f"""Oi, {name}!

Você atingiu o limite de mensagens de hoje no plano gratuito.

Amanhã o contador zera à meia-noite — ou assine um plano para usar mais agora:

{plans_url}

Equipe EGO-AI
"""
    html_body = f"""<!DOCTYPE html><html lang="pt-BR"><body style="font-family:Segoe UI,Arial,sans-serif;line-height:1.55;">
<p>Oi, <strong>{safe_name}</strong>!</p>
<p>Limite diário atingido. Amanhã libera de novo — ou <a href="{safe_url}">veja os planos</a>.</p>
</body></html>"""
    return subject, text, html_body


def _push_copy(kind: RetentionKind) -> tuple[str, str]:
    if kind == "trial_3d":
        return (
            "EGO-AI",
            f"Faltam 3 dias do seu teste grátis ({EGO_TRIAL_DAYS} dias).",
        )
    if kind == "trial_expired":
        return (
            "EGO-AI",
            "Seu teste grátis terminou. Veja os detalhes no app.",
        )
    return (
        "EGO-AI",
        "Limite de hoje atingido. Amanhã você pode usar de novo.",
    )


def _send_email(user_id: str, email: str, full_name: str, kind: RetentionKind) -> bool:
    if not signup_emails_enabled() or not email_configured():
        return False
    name = _first_name(full_name, email)
    plans_url = plans_checkout_url()
    subject, text_body, html_body = _email_bodies(kind, name, plans_url)
    try:
        send_signup_email(
            to_email=email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )
        ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if kind == "trial_3d":
            _mark_ui_flags(user_id, {KEY_TRIAL_3D_EMAIL: ts})
        elif kind == "trial_expired":
            _mark_ui_flags(user_id, {KEY_TRIAL_END_EMAIL: ts})
        else:
            _mark_ui_flags(user_id, {KEY_DAILY_LIMIT_EMAIL: _today_utc_date()})
        _LOG.info("plan_retention email %s → %s", kind, email)
        return True
    except Exception as exc:
        _LOG.warning("plan_retention email %s failed %s: %s", kind, email, exc)
        return False


def _send_push(user_id: str, prof: dict[str, Any], kind: RetentionKind) -> bool:
    if not plan_retention_push_enabled():
        return False
    tok = _expo_token(prof)
    if not tok:
        return False
    title, body = _push_copy(kind)
    sent = send_expo_push([tok], title=title, body=body, data={"type": f"retention_{kind}"})
    if sent <= 0:
        return False
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if kind == "trial_3d":
        _mark_ui_flags(user_id, {KEY_TRIAL_3D_PUSH: ts})
    elif kind == "trial_expired":
        _mark_ui_flags(user_id, {KEY_TRIAL_END_PUSH: ts})
    else:
        _mark_ui_flags(user_id, {KEY_DAILY_LIMIT_PUSH: _today_utc_date()})
    _LOG.info("plan_retention push %s → %s", kind, user_id[:8])
    return True


def deliver_plan_retention(user_id: str, kind: RetentionKind) -> dict[str, bool]:
    """Envia e-mail + push (se aplicável) uma vez por evento."""
    stats = {"email": False, "push": False, "skipped": False}
    if not plan_retention_enabled():
        stats["skipped"] = True
        return stats

    svc = create_service_client()
    if not svc or not user_id:
        stats["skipped"] = True
        return stats

    prof = load_profile(svc, user_id) or {}
    if _is_paid_essential(prof):
        stats["skipped"] = True
        return stats

    ui = _parse_ui_state(prof)
    if _already_sent(ui, kind):
        stats["skipped"] = True
        return stats

    email = _profile_email(prof)
    full_name = str(prof.get("full_name") or "")

    if kind == "trial_3d":
        rest = trial_days_remaining(prof.get("created_at"))
        if rest is None or rest != 3:
            stats["skipped"] = True
            return stats
    elif kind == "trial_expired":
        rest = trial_days_remaining(prof.get("created_at"))
        if rest is None or rest >= 0:
            stats["skipped"] = True
            return stats
    # daily_limit: caller garante que limite foi atingido

    if email:
        stats["email"] = _send_email(user_id, email, full_name, kind)
    stats["push"] = _send_push(user_id, prof, kind)
    return stats


def queue_plan_retention(user_id: str, kind: RetentionKind) -> None:
    if not plan_retention_enabled() or not user_id:
        return

    def _run() -> None:
        try:
            deliver_plan_retention(user_id, kind)
        except Exception as exc:
            _LOG.warning("plan_retention queue %s %s: %s", kind, user_id[:8], exc)

    threading.Thread(
        target=_run,
        daemon=True,
        name=f"plan-retention-{kind}-{user_id[:8]}",
    ).start()


def on_trial_access_denied(user_id: str) -> None:
    queue_plan_retention(user_id, "trial_expired")


def on_daily_limit_hit(user_id: str) -> None:
    queue_plan_retention(user_id, "daily_limit")


def process_plan_retention_cron(*, limit: int = 150) -> dict[str, int]:
    """Varre contas essential em trial — aviso 3 dias antes e pós-expiração."""
    stats = {
        "scanned": 0,
        "trial_3d": 0,
        "trial_expired": 0,
        "skipped": 0,
        "errors": 0,
    }
    if not plan_retention_enabled():
        stats["skipped"] = 1
        return stats

    svc = create_service_client()
    if not svc:
        stats["errors"] = 1
        return stats

    since = (
        datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=90)
    ).isoformat()

    try:
        res = (
            svc.table("profiles")
            .select("id,email,full_name,created_at,plan_tier,is_pro,ui_state,last_login_at")
            .gte("created_at", since)
            .not_.is_("email", "null")
            .order("created_at", desc=False)
            .limit(min(500, max(1, limit * 2)))
            .execute()
        )
    except Exception as exc:
        _LOG.warning("plan_retention cron query: %s", exc)
        stats["errors"] = 1
        return stats

    processed = 0
    for row in res.data or []:
        if processed >= limit:
            break
        uid = str(row.get("id") or "")
        if not uid or _is_paid_essential(row):
            stats["skipped"] += 1
            continue
        if not row.get("last_login_at"):
            stats["skipped"] += 1
            continue

        stats["scanned"] += 1
        rest = trial_days_remaining(row.get("created_at"))
        if rest is None:
            stats["skipped"] += 1
            continue

        ui = _parse_ui_state(row)
        try:
            if rest == 3 and not _already_sent(ui, "trial_3d"):
                r = deliver_plan_retention(uid, "trial_3d")
                if r.get("email") or r.get("push"):
                    stats["trial_3d"] += 1
                    processed += 1
            elif rest < 0 and not _already_sent(ui, "trial_expired"):
                r = deliver_plan_retention(uid, "trial_expired")
                if r.get("email") or r.get("push"):
                    stats["trial_expired"] += 1
                    processed += 1
            else:
                stats["skipped"] += 1
        except Exception:
            stats["errors"] += 1

    return stats


def start_background_jobs() -> None:
    global _background_started
    if _background_started:
        return
    _background_started = True
    if not plan_retention_enabled():
        _LOG.info("plan_retention: desligado (EGO_PLAN_RETENTION_ENABLED=0)")
        return

    def _loop() -> None:
        time.sleep(120)
        while True:
            try:
                stats = process_plan_retention_cron(limit=120)
                if stats.get("trial_3d") or stats.get("trial_expired"):
                    _LOG.info("plan_retention cron: %s", stats)
            except Exception as exc:
                _LOG.warning("plan_retention background: %s", exc)
            time.sleep(6 * 3600)

    threading.Thread(target=_loop, daemon=True, name="plan-retention-bg").start()
    _LOG.info("plan_retention: jobs automáticos (trial 3d + expirado)")
