"""Relatório diário de cadastros — e-mail operacional para o admin."""

from __future__ import annotations

import html
import logging
import os
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from ego_api.config import read_env

logger = logging.getLogger(__name__)

BR_TZ = ZoneInfo("America/Sao_Paulo")


def daily_stats_recipient() -> str:
    return (
        read_env("EGO_DAILY_STATS_EMAIL", "").strip()
        or read_env("EGO_STATS_REPORT_EMAIL", "").strip()
        or read_env("EGO_SMTP_FROM", "contato@egoai.com.br").strip()
    )


def daily_stats_enabled() -> bool:
    raw = read_env("EGO_DAILY_STATS_ENABLED", "1").lower()
    return raw not in ("0", "false", "no", "nao", "não")


def _count_table(client, table: str, *, gte: str | None = None, column: str = "created_at") -> int:
    import ssl

    url = (read_env("SUPABASE_URL") or os.getenv("SUPABASE_URL") or "").rstrip("/")
    key = read_env("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or ""
    if not url or not key:
        res = client.table(table).select("id", count="exact").limit(1).execute()
        return int(getattr(res, "count", None) or len(res.data or []))

    filters = ""
    if gte:
        filters = f"&{column}=gte.{urllib.parse.quote(gte, safe='')}"
    path = f"/rest/v1/{table}?select=id{filters}"
    req = urllib.request.Request(
        url + path,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Prefer": "count=exact",
            "Range": "0-0",
        },
        method="HEAD",
    )
    try:
        with urllib.request.urlopen(req, context=ssl._create_default_context()) as resp:
            cr = resp.headers.get("Content-Range", "")
        if "/" in cr:
            return int(cr.split("/")[-1])
    except Exception as exc:
        logger.warning("count_table HEAD failed (%s): %s", table, exc)

    q = client.table(table).select("id", count="exact").limit(1)
    if gte:
        q = q.gte(column, gte)
    res = q.execute()
    return int(getattr(res, "count", None) or len(res.data or []))


def _count_logged_since(client, since_iso: str) -> int:
    import ssl

    url = (read_env("SUPABASE_URL") or os.getenv("SUPABASE_URL") or "").rstrip("/")
    key = read_env("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or ""
    filters = f"&last_login_at=not.is.null&last_login_at=gte.{urllib.parse.quote(since_iso, safe='')}"
    if url and key:
        path = f"/rest/v1/profiles?select=id{filters}"
        req = urllib.request.Request(
            url + path,
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Prefer": "count=exact",
                "Range": "0-0",
            },
            method="HEAD",
        )
        try:
            with urllib.request.urlopen(req, context=ssl._create_default_context()) as resp:
                cr = resp.headers.get("Content-Range", "")
            if "/" in cr:
                return int(cr.split("/")[-1])
        except Exception as exc:
            logger.warning("count_logged HEAD failed: %s", exc)

    res = (
        client.table("profiles")
        .select("id", count="exact")
        .not_.is_("last_login_at", "null")
        .gte("last_login_at", since_iso)
        .limit(1)
        .execute()
    )
    return int(getattr(res, "count", None) or len(res.data or []))


def _signup_series(client, days: int = 14) -> list[tuple[date, int]]:
    now_br = datetime.now(BR_TZ)
    start = (now_br - timedelta(days=days - 1)).date()
    start_utc = datetime.combine(start, datetime.min.time(), tzinfo=BR_TZ).astimezone(timezone.utc)
    try:
        res = (
            client.table("profiles")
            .select("created_at")
            .gte("created_at", start_utc.isoformat())
            .order("created_at", desc=False)
            .limit(5000)
            .execute()
        )
    except Exception as exc:
        logger.warning("signup_series query failed: %s", exc)
        return []

    counts: Counter[date] = Counter()
    for row in res.data or []:
        raw = row.get("created_at")
        if not raw:
            continue
        try:
            dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            counts[dt.astimezone(BR_TZ).date()] += 1
        except ValueError:
            continue

    out: list[tuple[date, int]] = []
    for i in range(days):
        d = start + timedelta(days=i)
        out.append((d, counts.get(d, 0)))
    return out


def _platform_breakdown(client) -> list[tuple[str, int]]:
    try:
        res = (
            client.table("profiles")
            .select("last_platform")
            .not_.is_("last_login_at", "null")
            .limit(3000)
            .execute()
        )
    except Exception as exc:
        logger.warning("platform breakdown failed: %s", exc)
        return []

    counts: Counter[str] = Counter()
    for row in res.data or []:
        plat = (row.get("last_platform") or "").strip().lower() or "desconhecido"
        counts[plat] += 1
    return sorted(counts.items(), key=lambda x: (-x[1], x[0]))


def fetch_daily_stats(*, history_days: int = 14) -> dict[str, Any]:
    from ego_api.supabase_client import create_service_client

    client = create_service_client()
    if not client:
        raise RuntimeError("Supabase service role indisponível no servidor.")

    now_br = datetime.now(BR_TZ)
    today_start_br = datetime.combine(now_br.date(), datetime.min.time(), tzinfo=BR_TZ)
    today_start_utc = today_start_br.astimezone(timezone.utc).isoformat()
    week_ago_utc = (today_start_br - timedelta(days=7)).astimezone(timezone.utc).isoformat()

    profiles_total = _count_table(client, "profiles")
    logged_ever = 0
    try:
        res = (
            client.table("profiles")
            .select("id", count="exact")
            .not_.is_("last_login_at", "null")
            .limit(1)
            .execute()
        )
        logged_ever = int(getattr(res, "count", None) or 0)
    except Exception as exc:
        logger.warning("logged_ever count failed: %s", exc)

    signups_today = _count_table(client, "profiles", gte=today_start_utc)
    signups_7d = _count_table(client, "profiles", gte=week_ago_utc)
    logins_today = _count_logged_since(client, today_start_utc)
    logins_7d = _count_logged_since(client, week_ago_utc)

    chat_users_7d = 0
    try:
        ch = (
            client.table("chat_history")
            .select("user_id")
            .eq("role", "user")
            .gte("created_at", week_ago_utc)
            .limit(5000)
            .execute()
        )
        chat_users_7d = len({r.get("user_id") for r in (ch.data or []) if r.get("user_id")})
    except Exception as exc:
        logger.warning("chat_users_7d failed: %s", exc)

    series = _signup_series(client, days=max(7, history_days))
    platforms = _platform_breakdown(client)

    return {
        "generated_at_br": now_br.strftime("%d/%m/%Y %H:%M"),
        "date_br": now_br.strftime("%d/%m/%Y"),
        "profiles_total": profiles_total,
        "logged_ever": logged_ever,
        "never_logged": max(0, profiles_total - logged_ever),
        "signups_today": signups_today,
        "signups_7d": signups_7d,
        "logins_today": logins_today,
        "logins_7d": logins_7d,
        "chat_users_7d": chat_users_7d,
        "signup_series": [{"date": d.isoformat(), "count": n} for d, n in series],
        "platforms": [{"platform": p, "count": n} for p, n in platforms],
    }


def _format_series_text(series: list[dict[str, Any]]) -> str:
    lines = ["Cadastros por dia (Brasil):"]
    for row in reversed(series):
        d = row.get("date") or ""
        try:
            label = datetime.fromisoformat(d).strftime("%d/%m")
        except ValueError:
            label = d
        lines.append(f"  {label}: {row.get('count', 0)}")
    return "\n".join(lines)


def _format_series_html(series: list[dict[str, Any]]) -> str:
    rows = []
    for row in reversed(series):
        d = row.get("date") or ""
        try:
            label = datetime.fromisoformat(d).strftime("%d/%m")
        except ValueError:
            label = html.escape(str(d))
        rows.append(
            f"<tr><td style='padding:4px 12px;border-bottom:1px solid #eee'>{label}</td>"
            f"<td style='padding:4px 12px;border-bottom:1px solid #eee;text-align:right'>"
            f"{int(row.get('count') or 0)}</td></tr>"
        )
    body = "".join(rows)
    return (
        "<table style='border-collapse:collapse;margin-top:12px'>"
        "<tr><th align='left' style='padding:4px 12px'>Dia</th>"
        "<th align='right' style='padding:4px 12px'>Novos</th></tr>"
        f"{body}</table>"
    )


def build_daily_stats_email(stats: dict[str, Any]) -> tuple[str, str, str]:
    date_br = stats.get("date_br") or ""
    subject = f"EGO-AI — {stats.get('profiles_total', 0)} cadastros ({date_br})"

    plat_lines = stats.get("platforms") or []
    plat_text = "\n".join(
        f"  {p.get('platform', '?')}: {p.get('count', 0)}" for p in plat_lines[:6]
    ) or "  (sem dados)"

    text_body = f"""EGO-AI — relatório diário de cadastros
Gerado em: {stats.get('generated_at_br', '')} (horário de Brasília)

TOTAIS ATÉ AGORA
  Cadastros (perfis):     {stats.get('profiles_total', 0)}
  Já fizeram login:       {stats.get('logged_ever', 0)}
  Cadastraram e não logaram: {stats.get('never_logged', 0)}

HOJE ({date_br})
  Novos cadastros:        {stats.get('signups_today', 0)}
  Logins:                 {stats.get('logins_today', 0)}

ÚLTIMOS 7 DIAS
  Novos cadastros:        {stats.get('signups_7d', 0)}
  Logins:                 {stats.get('logins_7d', 0)}
  Usaram chat (texto):    {stats.get('chat_users_7d', 0)}

Plataforma (quem já logou):
{plat_text}

{_format_series_text(stats.get('signup_series') or [])}

---
Instalações brutas (APK/IPA): Play Console + TestFlight (não vêm do Supabase).
Este e-mail fica no seu inbox como histórico de crescimento.
"""

    html_body = f"""<!DOCTYPE html><html><body style="font-family:Segoe UI,Arial,sans-serif;color:#222">
<h2 style="margin:0 0 8px">EGO-AI — relatório diário</h2>
<p style="color:#666;margin:0 0 16px">Gerado em {html.escape(str(stats.get('generated_at_br') or ''))} (Brasília)</p>
<table style="border-collapse:collapse">
<tr><td style="padding:6px 16px 6px 0"><strong>Cadastros totais</strong></td><td>{int(stats.get('profiles_total') or 0)}</td></tr>
<tr><td style="padding:6px 16px 6px 0">Já fizeram login</td><td>{int(stats.get('logged_ever') or 0)}</td></tr>
<tr><td style="padding:6px 16px 6px 0">Cadastraram e não logaram</td><td>{int(stats.get('never_logged') or 0)}</td></tr>
<tr><td style="padding:6px 16px 6px 0"><strong>Novos hoje</strong></td><td>{int(stats.get('signups_today') or 0)}</td></tr>
<tr><td style="padding:6px 16px 6px 0">Logins hoje</td><td>{int(stats.get('logins_today') or 0)}</td></tr>
<tr><td style="padding:6px 16px 6px 0">Novos (7 dias)</td><td>{int(stats.get('signups_7d') or 0)}</td></tr>
<tr><td style="padding:6px 16px 6px 0">Logins (7 dias)</td><td>{int(stats.get('logins_7d') or 0)}</td></tr>
<tr><td style="padding:6px 16px 6px 0">Usaram chat (7 dias)</td><td>{int(stats.get('chat_users_7d') or 0)}</td></tr>
</table>
<h3 style="margin:20px 0 8px">Cadastros por dia</h3>
{_format_series_html(stats.get('signup_series') or [])}
<p style="color:#888;font-size:12px;margin-top:24px">Instalações brutas: Play Console + TestFlight. Histórico guardado nos seus e-mails.</p>
</body></html>"""

    return subject, text_body, html_body


def process_daily_stats_report(*, history_days: int = 14, dry_run: bool = False) -> dict[str, Any]:
    """Busca métricas e envia e-mail operacional. Usado pelo cron Railway."""
    from ego_api.signup_emails import email_configured, send_ops_email

    result: dict[str, Any] = {
        "ok": False,
        "sent": False,
        "dry_run": dry_run,
        "recipient": "",
        "error": "",
    }

    if not daily_stats_enabled():
        result["error"] = "EGO_DAILY_STATS_ENABLED=0"
        return result

    recipient = daily_stats_recipient()
    if not recipient or "@" not in recipient:
        result["error"] = "Defina EGO_DAILY_STATS_EMAIL no Railway."
        return result

    if not dry_run and not email_configured():
        result["error"] = "E-mail não configurado (Brevo/Resend/SMTP)."
        return result

    stats = fetch_daily_stats(history_days=history_days)
    subject, text_body, html_body = build_daily_stats_email(stats)
    result["stats"] = stats
    result["subject"] = subject
    result["recipient"] = recipient

    if dry_run:
        result["ok"] = True
        return result

    try:
        send_ops_email(
            to_email=recipient,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )
        result["ok"] = True
        result["sent"] = True
        logger.info("daily_stats_report sent to %s", recipient)
    except Exception as exc:
        result["error"] = str(exc)[:400]
        logger.warning("daily_stats_report failed: %s", exc)

    return result
