"""E-mails automáticos pós-cadastro via SMTP (contato@egoai.com.br)."""

from __future__ import annotations

import datetime
import html
import logging
import smtplib
import ssl
import threading
import time
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Any

from ego_api.config import play_store_update_url, read_env

logger = logging.getLogger(__name__)

_welcome_locks: dict[str, threading.Lock] = {}
_welcome_locks_guard = threading.Lock()

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


def email_provider() -> str:
    """brevo (HTTPS), resend (HTTPS) ou smtp (porta 587 — costuma falhar no Railway)."""
    explicit = read_env("EGO_EMAIL_PROVIDER", "").strip().lower()
    if explicit:
        return explicit
    if brevo_configured():
        return "brevo"
    if resend_configured():
        return "resend"
    return "smtp"


def brevo_configured() -> bool:
    return bool(
        read_env("BREVO_API_KEY", "").strip()
        or read_env("SENDINBLUE_API_KEY", "").strip()
    )


def resend_configured() -> bool:
    return bool(read_env("RESEND_API_KEY", "").strip())


def email_configured() -> bool:
    provider = email_provider()
    if provider == "brevo":
        return brevo_configured()
    if provider == "resend":
        return resend_configured()
    return smtp_configured()


def signup_emails_status() -> dict[str, Any]:
    ready = signup_emails_enabled() and email_configured()
    provider = email_provider()
    return {
        "enabled": signup_emails_enabled(),
        "provider": provider,
        "configured": email_configured(),
        "smtp_configured": smtp_configured(),
        "brevo_configured": brevo_configured(),
        "resend_configured": resend_configured(),
        "automatic_on_signup": ready,
        "background_jobs": ready,
    }


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
    subject = "Bem-vindo ao Ego-IA — instale e comece em 2 minutos"
    text = f"""Oi, {name}!

Obrigado por criar sua conta no Ego-IA — seu assistente com rosto e voz no celular.

INSTALAR (Android — use o mesmo e-mail do cadastro):
{play_url}
1) Tornar-se testador → Aceitar
2) Play Store → Ego-IA → Instalar
3) Abrir o app → Entrar

O QUE O APP FAZ:
• Chat — converse por texto ou microfone; o avatar fala com você
• Agenda — marque compromissos e hábitos (ex.: «marcar dentista terça 15h»)
• Lembretes — avisos no celular para não esquecer
• Agenda compartilhada — convide família por telefone ou e-mail
• Descarrego da noite (21h) — grave o que está na cabeça; confirme de manhã na Agenda
• Lista de compras — ligada ao compromisso do mercado

COMO COMEÇAR (2 minutos):
1) Escolha seu assistente (Luna, Leo ou outro)
2) No chat, digite Oi ou segure o microfone
3) Peça algo simples: «lembrar de comprar leite amanhã» ou «o que tenho na agenda?»

Menu ☰ → Agenda, Planos e Conta.

Dúvida ou erro? Responda este e-mail: {SUPPORT_EMAIL}

App em teste. Não substitui profissionais de saúde.

Equipe Ego-IA
{SUPPORT_EMAIL}
"""
    safe_name = html.escape(name)
    safe_url = html.escape(play_url)
    html_body = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body style="font-family:Segoe UI,Arial,sans-serif;line-height:1.55;color:#111111;margin:0;padding:16px;">
  <div style="max-width:560px;">
  <p>Oi, <strong>{safe_name}</strong>!</p>
  <p>Obrigado por criar sua conta no <strong>Ego-IA</strong> — seu assistente com <strong>rosto e voz</strong> no celular.</p>

  <p><strong>Instalar no Android</strong> (mesmo e-mail do cadastro):</p>
  <p><a href="{safe_url}" style="display:inline-block;padding:12px 18px;background:#0A122A;color:#ffffff;text-decoration:none;border-radius:8px;">Abrir teste na Play Store</a></p>
  <ol style="padding-left:1.2em;">
    <li>Tornar-se testador → Aceitar</li>
    <li>Play Store → Ego-IA → Instalar</li>
    <li>Abrir o app → Entrar</li>
  </ol>

  <p><strong>O que o app faz</strong></p>
  <ul style="padding-left:1.2em;">
    <li><strong>Chat</strong> — texto ou microfone; o avatar responde com voz</li>
    <li><strong>Agenda</strong> — compromissos e hábitos</li>
    <li><strong>Lembretes</strong> — avisos no celular</li>
    <li><strong>Agenda compartilhada</strong> — convide por telefone ou e-mail</li>
    <li><strong>Descarrego da noite (21h)</strong> — grave à noite; confirme de manhã na Agenda</li>
    <li><strong>Lista de compras</strong> — no compromisso do mercado</li>
  </ul>

  <p><strong>Como começar (2 min)</strong></p>
  <ol style="padding-left:1.2em;">
    <li>Escolha seu assistente (Luna, Leo…)</li>
    <li>No chat: digite <strong>Oi</strong> ou use o microfone</li>
    <li>Peça: «lembrar de comprar leite» ou «o que tenho na agenda?»</li>
  </ol>
  <p>Menu ☰ → Agenda, Planos e Conta.</p>

  <p>Dúvida? <a href="mailto:{SUPPORT_EMAIL}">{SUPPORT_EMAIL}</a></p>
  <p style="font-size:12px;color:#666666;">App em teste. Não substitui profissionais de saúde.</p>
  </div>
</body>
</html>"""
    return subject, text, html_body


def _reminder_bodies(name: str, play_url: str) -> tuple[str, str, str]:
    subject = "Ego-IA — falta só instalar e dizer Oi"
    text = f"""Oi, {name}!

Você criou conta no Ego-IA mas ainda não entrou no app.

Instale no Android (mesmo e-mail do cadastro):
{play_url}

Depois:
1) Entrar no app
2) Escolher assistente (Luna ou Leo)
3) Digitar Oi no chat — ele responde com voz

O app ajuda com chat, agenda, lembretes e lista de compras.

Ajuda: {SUPPORT_EMAIL}

Equipe Ego-IA
"""
    safe_name = html.escape(name)
    safe_url = html.escape(play_url)
    html_body = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body style="font-family:Segoe UI,Arial,sans-serif;line-height:1.55;color:#111111;margin:0;padding:16px;">
  <div style="max-width:560px;">
  <p>Oi, <strong>{safe_name}</strong>!</p>
  <p>Você criou conta no <strong>Ego-IA</strong>, mas ainda não entrou no app.</p>
  <p><a href="{safe_url}" style="display:inline-block;padding:12px 18px;background:#0A122A;color:#ffffff;text-decoration:none;border-radius:8px;">Instalar teste Android</a></p>
  <p><strong>Depois:</strong></p>
  <ol style="padding-left:1.2em;">
    <li>Entrar com o <strong>mesmo e-mail</strong></li>
    <li>Escolher assistente (Luna ou Leo)</li>
    <li>Digitar <strong>Oi</strong> no chat — resposta com voz</li>
  </ol>
  <p>Chat, agenda, lembretes e lista de compras — tudo no bolso.</p>
  <p>Ajuda: <a href="mailto:{SUPPORT_EMAIL}">{SUPPORT_EMAIL}</a></p>
  </div>
</body>
</html>"""
    return subject, text, html_body


def _build_mime_message(
    *,
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str,
    from_name: str,
    from_email: str,
) -> MIMEMultipart:
    plain = (text_body or "").strip()
    html_part = (html_body or "").strip()
    if not plain and not html_part:
        raise ValueError("Corpo do e-mail vazio.")
    if not plain:
        plain = (
            "Obrigado por criar sua conta no Ego-IA. "
            "Abra este e-mail em um app que suporte HTML ou acesse a Play Store pelo link no site."
        )
    if not html_part:
        html_part = f"<html><body><pre>{html.escape(plain)}</pre></body></html>"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = str(Header(subject, "utf-8"))
    msg["From"] = formataddr((from_name, from_email))
    msg["To"] = to_email
    msg["Reply-To"] = SUPPORT_EMAIL
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html_part, "html", "utf-8"))
    return msg


def _smtp_timeout() -> int:
    raw = read_env("EGO_SMTP_TIMEOUT", "60")
    try:
        return max(15, int(raw))
    except ValueError:
        return 60


def send_smtp_email(
    *,
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str,
    require_signup_enabled: bool = True,
) -> None:
    if require_signup_enabled and not signup_emails_enabled():
        return
    cfg = _smtp_settings()
    if not cfg["password"]:
        raise RuntimeError("EGO_SMTP_PASSWORD não configurado no Railway.")
    to_email = (to_email or "").strip()
    if not to_email or "@" not in to_email:
        raise ValueError("E-mail de destino inválido.")

    msg = _build_mime_message(
        to_email=to_email,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        from_name=str(cfg["from_name"]),
        from_email=str(cfg["from_email"]),
    )
    bcc_self = read_env("EGO_SMTP_BCC_SELF", "1").lower() not in ("0", "false", "no")
    recipients = [to_email]
    if bcc_self and cfg["from_email"]:
        msg["Bcc"] = cfg["from_email"]
        recipients.append(cfg["from_email"])

    timeout = _smtp_timeout()

    if cfg["use_ssl"]:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(
            cfg["host"], cfg["port"], context=context, timeout=timeout
        ) as smtp:
            smtp.login(cfg["user"], cfg["password"])
            smtp.sendmail(cfg["from_email"], recipients, msg.as_string())
        return

    with smtplib.SMTP(cfg["host"], cfg["port"], timeout=timeout) as smtp:
        if cfg["use_tls"]:
            smtp.starttls(context=ssl.create_default_context())
        smtp.login(cfg["user"], cfg["password"])
        smtp.sendmail(cfg["from_email"], recipients, msg.as_string())


def _resend_from() -> str:
    custom = read_env("EGO_RESEND_FROM", "").strip()
    if custom:
        return custom
    cfg = _smtp_settings()
    return f'{cfg["from_name"]} <{cfg["from_email"]}>'


def send_resend_email(*, to_email: str, subject: str, text_body: str, html_body: str) -> None:
    import requests

    api_key = read_env("RESEND_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("RESEND_API_KEY não configurado no Railway.")
    to_email = (to_email or "").strip()
    if not to_email or "@" not in to_email:
        raise ValueError("E-mail de destino inválido.")

    payload: dict[str, Any] = {
        "from": _resend_from(),
        "to": [to_email],
        "subject": subject,
        "html": (html_body or "").strip() or f"<pre>{html.escape(text_body)}</pre>",
        "text": (text_body or "").strip() or "Ego-IA",
        "reply_to": SUPPORT_EMAIL,
    }
    bcc = read_env("EGO_SMTP_FROM", DEFAULT_FROM).strip()
    if read_env("EGO_SMTP_BCC_SELF", "1").lower() not in ("0", "false", "no") and bcc:
        payload["bcc"] = [bcc]

    resp = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=45,
    )
    if resp.status_code >= 400:
        detail = resp.text[:400] if resp.text else resp.reason
        raise RuntimeError(f"Resend HTTP {resp.status_code}: {detail}")


def send_brevo_api_email(
    *, to_email: str, subject: str, text_body: str, html_body: str
) -> None:
    """Brevo via HTTPS (api.brevo.com) — funciona no Railway sem porta SMTP."""
    import requests

    api_key = (
        read_env("BREVO_API_KEY", "").strip()
        or read_env("SENDINBLUE_API_KEY", "").strip()
    )
    if not api_key:
        raise RuntimeError("BREVO_API_KEY não configurado no Railway.")
    to_email = (to_email or "").strip()
    if not to_email or "@" not in to_email:
        raise ValueError("E-mail de destino inválido.")

    cfg = _smtp_settings()
    payload: dict[str, Any] = {
        "sender": {"name": str(cfg["from_name"]), "email": str(cfg["from_email"])},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": (html_body or "").strip()
        or f"<pre>{html.escape(text_body)}</pre>",
        "textContent": (text_body or "").strip() or "Ego-IA",
        "replyTo": {"email": SUPPORT_EMAIL, "name": str(cfg["from_name"])},
    }
    bcc = str(cfg["from_email"]).strip()
    if read_env("EGO_SMTP_BCC_SELF", "1").lower() not in ("0", "false", "no") and bcc:
        payload["bcc"] = [{"email": bcc}]

    resp = requests.post(
        "https://api.brevo.com/v3/smtp/email",
        headers={"api-key": api_key, "Content-Type": "application/json"},
        json=payload,
        timeout=45,
    )
    if resp.status_code >= 400:
        detail = resp.text[:400] if resp.text else resp.reason
        raise RuntimeError(f"Brevo API HTTP {resp.status_code}: {detail}")


def send_ops_email(*, to_email: str, subject: str, text_body: str, html_body: str) -> None:
    """E-mail operacional (relatórios admin) — não depende de EGO_SIGNUP_EMAIL_ENABLED."""
    if not email_configured():
        raise RuntimeError("E-mail não configurado: BREVO_API_KEY, RESEND_API_KEY ou EGO_SMTP_PASSWORD.")
    provider = email_provider()
    if provider == "brevo":
        send_brevo_api_email(
            to_email=to_email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )
        return
    if provider == "resend":
        send_resend_email(
            to_email=to_email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )
        return
    send_smtp_email(
        to_email=to_email,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        require_signup_enabled=False,
    )


def send_signup_email(*, to_email: str, subject: str, text_body: str, html_body: str) -> None:
    """Envia boas-vindas/lembrete — Brevo API, Resend ou SMTP."""
    if not signup_emails_enabled():
        return
    provider = email_provider()
    if provider == "brevo":
        send_brevo_api_email(
            to_email=to_email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )
        return
    if provider == "resend":
        send_resend_email(
            to_email=to_email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )
        return
    send_smtp_email(
        to_email=to_email,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )


def _welcome_user_lock(user_id: str) -> threading.Lock:
    with _welcome_locks_guard:
        lock = _welcome_locks.get(user_id)
        if lock is None:
            lock = threading.Lock()
            _welcome_locks[user_id] = lock
        return lock


def _welcome_already_sent(user_id: str) -> bool:
    from ego_api.supabase_client import create_service_client

    svc = create_service_client()
    if not svc or not user_id:
        return False
    try:
        res = (
            svc.table("profiles")
            .select("welcome_email_sent_at")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        row = (res.data or [None])[0]
        return bool(row and row.get("welcome_email_sent_at"))
    except Exception as exc:
        logger.warning("welcome_email check failed: %s", exc)
        return False


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
    if not signup_emails_enabled() or not email_configured():
        return False
    with _welcome_user_lock(user_id):
        if _welcome_already_sent(user_id):
            logger.info("welcome_email skip (já enviado): %s", email)
            return False
        name = _first_name(full_name, email)
        play_url = _play_url()
        subject, text_body, html_body = _welcome_bodies(name, play_url)
        for attempt in range(3):
            try:
                send_signup_email(
                    to_email=email,
                    subject=subject,
                    text_body=text_body,
                    html_body=html_body,
                )
                _mark_profile_email_flag(user_id, "welcome_email_sent_at")
                logger.info("welcome_email sent to %s", email)
                return True
            except Exception as exc:
                if attempt >= 2:
                    logger.warning("welcome_email failed for %s: %s", email, exc)
                    return False
                time.sleep(2 * (attempt + 1))
        return False


def send_reminder_email(user_id: str, email: str, full_name: str = "") -> bool:
    if not signup_emails_enabled() or not email_configured():
        return False
    name = _first_name(full_name, email)
    play_url = _play_url()
    subject, text_body, html_body = _reminder_bodies(name, play_url)
    try:
        send_signup_email(
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
    """Dispara boas-vindas em background — automático no cadastro, sem ação manual."""
    if not user_id or not (email or "").strip():
        return
    if not signup_emails_enabled():
        logger.warning("welcome_email não enviado (EGO_SIGNUP_EMAIL_ENABLED=0): %s", email)
        return
    if not email_configured():
        logger.warning(
            "welcome_email não enviado (SMTP/Resend não configurado no servidor): %s",
            email,
        )
        return

    def _run() -> None:
        send_welcome_email(user_id, email, full_name)

    threading.Thread(
        target=_run,
        daemon=True,
        name=f"welcome-email-{user_id[:8]}",
    ).start()


def process_pending_welcome_emails(*, max_days: int = 7, limit: int = 30) -> dict[str, int]:
    """Reenvia boas-vindas a quem cadastrou mas não recebeu (falha SMTP transitória)."""
    from ego_api.supabase_client import create_service_client

    stats = {"candidates": 0, "sent": 0, "failed": 0, "skipped": 0}
    if not signup_emails_enabled() or not email_configured():
        stats["skipped"] = 1
        return stats

    svc = create_service_client()
    if not svc:
        stats["skipped"] = 1
        return stats

    since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=max_days)
    try:
        res = (
            svc.table("profiles")
            .select("id,email,full_name,welcome_email_sent_at,created_at")
            .is_("welcome_email_sent_at", "null")
            .not_.is_("email", "null")
            .gte("created_at", since.isoformat())
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
    except Exception as exc:
        logger.warning("pending_welcome query failed: %s", exc)
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
        if send_welcome_email(uid, email, str(row.get("full_name") or "")):
            stats["sent"] += 1
        else:
            stats["failed"] += 1
    return stats


_background_jobs_started = False


def start_background_jobs() -> None:
    """Cron interno: pendentes + lembrete 24h — sem cron externo nem ação manual."""
    global _background_jobs_started
    if _background_jobs_started:
        return
    _background_jobs_started = True

    if not signup_emails_enabled():
        logger.info("signup_emails: desligado (EGO_SIGNUP_EMAIL_ENABLED=0)")
        return
    if not email_configured():
        logger.warning(
            "signup_emails: SMTP/Resend não configurado — cadastros NÃO recebem e-mail automático"
        )
        return

    def _run_loop() -> None:
        time.sleep(45)
        while True:
            try:
                pending = process_pending_welcome_emails()
                if pending.get("sent"):
                    logger.info("pending_welcome batch: %s", pending)
                reminders = process_signup_reminders()
                if reminders.get("sent"):
                    logger.info("signup_reminder batch: %s", reminders)
            except Exception as exc:
                logger.warning("signup_email background loop: %s", exc)
            time.sleep(4 * 3600)

    threading.Thread(
        target=_run_loop,
        daemon=True,
        name="signup-email-background",
    ).start()
    logger.info("signup_emails: jobs automáticos iniciados (boas-vindas + lembrete 24h)")


def process_signup_reminders(
    *,
    min_hours: int = 24,
    max_days: int = 7,
    limit: int = 50,
) -> dict[str, int]:
    """Envia lembrete a quem criou conta, recebeu boas-vindas e nunca fez login."""
    from ego_api.supabase_client import create_service_client

    stats = {"candidates": 0, "sent": 0, "failed": 0, "skipped": 0}
    if not signup_emails_enabled() or not email_configured():
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
