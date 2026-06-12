"""E-mails automáticos pós-cadastro via SMTP (contato@egoai.com.br)."""

from __future__ import annotations

import datetime
import html
import logging
import smtplib
import ssl
import threading
from email.message import EmailMessage
from typing import Any

from ego_api.config import play_store_update_url, read_env

logger = logging.getLogger(__name__)

DEFAULT_FROM = "contato@egoai.com.br"
DEFAULT_FROM_NAME = "Ego-IA"
DEFAULT_SMTP_HOST = "smtp.uol.com.br"
DEFAULT_SMTP_PORT = 587
SUPPORT_EMAIL = DEFAULT_FROM


def signup_emails_enabled() -> bool:
    raw = read_env("EGO_SIGNUP_EMAIL_ENABLED", "1").lower()
    return raw not in ("0", "false", "no", "nao", "não")


def smtp_configured() -> bool:
    return bool(read_env("EGO_SMTP_PASSWORD"))


def _smtp_settings() -> dict[str, Any]:
    port_raw = read_env("EGO_SMTP_PORT", str(DEFAULT_SMTP_PORT))
    try:
        port = int(port_raw)
    except ValueError:
        port = DEFAULT_SMTP_PORT
    use_tls = read_env("EGO_SMTP_USE_TLS", "1").lower() not in ("0", "false", "no")
    use_ssl = read_env("EGO_SMTP_USE_SSL", "").lower() in ("1", "true", "yes")
    if port == 465 and not read_env("EGO_SMTP_USE_SSL"):
        use_ssl = True
    return {
        "host": read_env("EGO_SMTP_HOST", DEFAULT_SMTP_HOST),
        "port": port,
        "user": read_env("EGO_SMTP_USER", DEFAULT_FROM),
        "password": read_env("EGO_SMTP_PASSWORD"),
        "from_email": read_env("EGO_SMTP_FROM", DEFAULT_FROM),
        "from_name": read_env("EGO_SMTP_FROM_NAME", DEFAULT_FROM_NAME),
        "use_tls": use_tls and not use_ssl,
        "use_ssl": use_ssl,
    }


def _first_name(full_name: str, email: str) -> str:
    name = (full_name or "").strip()
    if name:
        return name.split()[0]
    if "@" in email:
        return email.split("@")[0]
    return "Olá"


def _play_url() -> str:
    return play_store_update_url()


def _welcome_bodies(name: str, play_url: str) -> tuple[str, str, str]:
    subject = "Ego-IA — instale e teste grátis no Android"
    text = f"""Oi, {name}!

Obrigado por criar sua conta no Ego-IA.

Para testar grátis no Android (mesmo e-mail do cadastro):
{play_url}

1) Tornar-se testador → Aceitar
2) Play Store → Ego-IA → Instalar
3) Abrir o app → Entrar → digite Oi no chat

Dúvida ou erro? Responda este e-mail ou escreva para {SUPPORT_EMAIL}.

App em teste. Não substitui profissionais de saúde.

Equipe Ego-IA
{SUPPORT_EMAIL}
"""
    safe_name = html.escape(name)
    safe_url = html.escape(play_url)
    html_body = f"""<!DOCTYPE html>
<html lang="pt-BR">
<body style="font-family:Segoe UI,Arial,sans-serif;line-height:1.5;color:#111;">
  <p>Oi, <strong>{safe_name}</strong>!</p>
  <p>Obrigado por criar sua conta no <strong>Ego-IA</strong>.</p>
  <p>Para testar grátis no <strong>Android</strong> (use o mesmo e-mail do cadastro):</p>
  <p><a href="{safe_url}" style="display:inline-block;padding:12px 18px;background:#0A122A;color:#fff;text-decoration:none;border-radius:8px;">Abrir teste na Play Store</a></p>
  <ol>
    <li>Tornar-se testador → Aceitar</li>
    <li>Play Store → Ego-IA → Instalar</li>
    <li>Abrir o app → Entrar → digite <strong>Oi</strong> no chat</li>
  </ol>
  <p>Dúvida ou erro? Responda este e-mail: <a href="mailto:{SUPPORT_EMAIL}">{SUPPORT_EMAIL}</a></p>
  <p style="font-size:12px;color:#666;">App em teste. Não substitui profissionais de saúde.</p>
</body>
</html>"""
    return subject, text, html_body


def _reminder_bodies(name: str, play_url: str) -> tuple[str, str, str]:
    subject = "Ego-IA — falta só instalar no Android"
    text = f"""Oi, {name}!

Vimos que você criou conta no Ego-IA mas ainda não entrou no app.

Instale no Android com o mesmo Gmail:
{play_url}

Depois abra o app, faça login e digite Oi no chat.

Precisa de ajuda? {SUPPORT_EMAIL}

Equipe Ego-IA
"""
    safe_name = html.escape(name)
    safe_url = html.escape(play_url)
    html_body = f"""<!DOCTYPE html>
<html lang="pt-BR">
<body style="font-family:Segoe UI,Arial,sans-serif;line-height:1.5;color:#111;">
  <p>Oi, <strong>{safe_name}</strong>!</p>
  <p>Você criou conta no <strong>Ego-IA</strong>, mas ainda não entrou no app.</p>
  <p><a href="{safe_url}" style="display:inline-block;padding:12px 18px;background:#0A122A;color:#fff;text-decoration:none;border-radius:8px;">Instalar teste Android</a></p>
  <p>Depois: login com o <strong>mesmo e-mail</strong> → digite <strong>Oi</strong> no chat.</p>
  <p>Ajuda: <a href="mailto:{SUPPORT_EMAIL}">{SUPPORT_EMAIL}</a></p>
</body>
</html>"""
    return subject, text, html_body


def send_smtp_email(*, to_email: str, subject: str, text_body: str, html_body: str) -> None:
    if not signup_emails_enabled():
        return
    cfg = _smtp_settings()
    if not cfg["password"]:
        raise RuntimeError("EGO_SMTP_PASSWORD não configurado no Railway.")
    to_email = (to_email or "").strip()
    if not to_email or "@" not in to_email:
        raise ValueError("E-mail de destino inválido.")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f'{cfg["from_name"]} <{cfg["from_email"]}>'
    msg["To"] = to_email
    msg["Reply-To"] = SUPPORT_EMAIL
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    if cfg["use_ssl"]:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(cfg["host"], cfg["port"], context=context, timeout=30) as smtp:
            smtp.login(cfg["user"], cfg["password"])
            smtp.send_message(msg)
        return

    with smtplib.SMTP(cfg["host"], cfg["port"], timeout=30) as smtp:
        if cfg["use_tls"]:
            smtp.starttls(context=ssl.create_default_context())
        smtp.login(cfg["user"], cfg["password"])
        smtp.send_message(msg)


def _mark_profile_email_flag(user_id: str, column: str) -> None:
    from ego_api.supabase_client import create_service_client

    svc = create_service_client()
    if not svc or not user_id:
        return
    if column not in ("welcome_email_sent_at", "signup_reminder_sent_at"):
        return
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        svc.table("profiles").update({column: ts}).eq("id", user_id).execute()
    except Exception as exc:
        logger.warning("signup_email mark %s failed: %s", column, exc)


def send_welcome_email(user_id: str, email: str, full_name: str = "") -> bool:
    if not signup_emails_enabled() or not smtp_configured():
        return False
    name = _first_name(full_name, email)
    play_url = _play_url()
    subject, text_body, html_body = _welcome_bodies(name, play_url)
    try:
        send_smtp_email(
            to_email=email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )
        _mark_profile_email_flag(user_id, "welcome_email_sent_at")
        logger.info("welcome_email sent to %s", email)
        return True
    except Exception as exc:
        logger.warning("welcome_email failed for %s: %s", email, exc)
        return False


def send_reminder_email(user_id: str, email: str, full_name: str = "") -> bool:
    if not signup_emails_enabled() or not smtp_configured():
        return False
    name = _first_name(full_name, email)
    play_url = _play_url()
    subject, text_body, html_body = _reminder_bodies(name, play_url)
    try:
        send_smtp_email(
            to_email=email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )
        _mark_profile_email_flag(user_id, "signup_reminder_sent_at")
        logger.info("signup_reminder sent to %s", email)
        return True
    except Exception as exc:
        logger.warning("signup_reminder failed for %s: %s", email, exc)
        return False


def queue_welcome_email(user_id: str, email: str, full_name: str = "") -> None:
    if not user_id or not (email or "").strip():
        return
    if not signup_emails_enabled() or not smtp_configured():
        return

    def _run() -> None:
        send_welcome_email(user_id, email, full_name)

    threading.Thread(target=_run, daemon=True).start()


def process_signup_reminders(
    *,
    min_hours: int = 24,
    max_days: int = 7,
    limit: int = 50,
) -> dict[str, int]:
    """Envia lembrete a quem criou conta, recebeu boas-vindas e nunca fez login."""
    from ego_api.supabase_client import create_service_client

    stats = {"candidates": 0, "sent": 0, "failed": 0, "skipped": 0}
    if not signup_emails_enabled() or not smtp_configured():
        stats["skipped"] = 1
        return stats

    svc = create_service_client()
    if not svc:
        stats["skipped"] = 1
        return stats

    now = datetime.datetime.now(datetime.timezone.utc)
    min_created = now - datetime.timedelta(days=max_days)
    max_created = now - datetime.timedelta(hours=min_hours)

    try:
        res = (
            svc.table("profiles")
            .select("id,email,full_name,welcome_email_sent_at,signup_reminder_sent_at,last_login_at,created_at")
            .not_.is_("welcome_email_sent_at", "null")
            .is_("signup_reminder_sent_at", "null")
            .is_("last_login_at", "null")
            .lte("created_at", max_created.isoformat())
            .gte("created_at", min_created.isoformat())
            .limit(limit)
            .execute()
        )
    except Exception as exc:
        logger.warning("signup_reminder query failed: %s", exc)
        stats["failed"] = 1
        return stats

    rows = res.data or []
    stats["candidates"] = len(rows)
    for row in rows:
        uid = str(row.get("id") or "")
        email = str(row.get("email") or "").strip()
        if not uid or not email:
            stats["skipped"] += 1
            continue
        if send_reminder_email(uid, email, str(row.get("full_name") or "")):
            stats["sent"] += 1
        else:
            stats["failed"] += 1
    return stats
