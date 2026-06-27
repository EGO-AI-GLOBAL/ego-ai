#!/usr/bin/env python3
"""
Monitoramento de segurança automático — EGO-AI.

Verifica produção (health + integridade), código local e erros recentes.
Escreve marketing/SEGURANCA-STATUS.txt e alerta webhook se configurado.

Uso:
  python scripts/security_monitor.py
  MONITOR-SEGURANCA-AUTO.bat   (Task Scheduler — a cada 1h)
"""

from __future__ import annotations

import json
import os
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "marketing" / "SEGURANCA-STATUS.txt"
API_BASE = (
    os.getenv("EGO_API_HEALTH_URL", "https://ego-ai-production-a2c2.up.railway.app/api/v1")
    .rstrip("/")
)


def _urlopen(req: urllib.request.Request, timeout: int = 25):
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.URLError as exc:
        err = str(exc)
        if "SSL" not in err and "CERTIFICATE" not in err:
            raise
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return urllib.request.urlopen(req, timeout=timeout, context=ctx)


def fetch_json(path: str) -> tuple[int | None, dict[str, Any]]:
    url = f"{API_BASE}{path}"
    req = urllib.request.Request(url, method="GET")
    try:
        with _urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode() if exc.fp else "{}"
        try:
            body = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            body = {"raw": raw[:500]}
        return exc.code, body
    except urllib.error.URLError as exc:
        return None, {"error": str(exc)}


def _recent_error_count() -> tuple[int | None, str]:
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
        return None, "sem credenciais Supabase local"
    sys.path.insert(0, str(ROOT))
    try:
        from ego_api.supabase_client import create_service_client

        client = create_service_client()
        if not client:
            return None, "client Supabase indisponível"
        since = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        # últimas 24h — filtro simples por created_at
        day_ago = datetime.now(timezone.utc).timestamp() - 86400
        r = (
            client.table("error_reports")
            .select("created_at, level")
            .order("created_at", desc=True)
            .limit(200)
            .execute()
        )
        rows = r.data or []
        recent = 0
        errors_24h = 0
        for row in rows:
            ts = row.get("created_at") or ""
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                if dt.timestamp() >= day_ago:
                    errors_24h += 1
                    if row.get("level") == "error":
                        recent += 1
            except ValueError:
                continue
        return errors_24h, f"{recent} erros críticos / {errors_24h} total (24h)"
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)[:120]


def _run_audit() -> tuple[bool, str]:
    script = ROOT / "scripts" / "security_prelaunch_audit.py"
    if not script.is_file():
        return False, "security_prelaunch_audit.py em falta"
    r = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    return r.returncode == 0, (r.stdout or r.stderr or "")[-400:]


def _alert_webhook(title: str, body: str) -> None:
    url = (os.getenv("ERROR_ALERT_WEBHOOK_URL") or "").strip()
    if not url:
        return
    try:
        import httpx

        text = f"**EGO-AI Segurança — {title}**\n{body[:1700]}"
        if "hooks.slack.com" in url:
            payload: dict[str, Any] = {"text": text.replace("**", "*")}
        else:
            payload = {"content": text}
        httpx.post(url, timeout=8.0, json=payload)
    except Exception:
        pass


def evaluate_production(health: dict[str, Any]) -> tuple[list[str], list[str]]:
    critical: list[str] = []
    warn: list[str] = []

    if health.get("error"):
        critical.append(f"API inacessível: {health['error']}")
        return critical, warn

    if health.get("maintenance"):
        critical.append("EGO_MAINTENANCE=1 em produção — app pausado")

    if health.get("ok") is not True:
        critical.append("health ok != true")

    checks = health.get("checks") or {}
    if not checks.get("supabase"):
        critical.append("Supabase offline ou mal configurado")
    if not checks.get("service_role_set"):
        critical.append("SUPABASE_SERVICE_ROLE_KEY em falta no Railway")

    mon = health.get("monitoring") or {}
    if mon.get("sentry_dsn_set") and not mon.get("sentry"):
        warn.append(
            "Sentry DSN definido mas sentry=false — instalar sentry-sdk no deploy "
            "(requirements-api.txt)"
        )
    if not mon.get("alert_webhook_set"):
        warn.append("ERROR_ALERT_WEBHOOK_URL não configurado — sem alertas Discord")

    pi = health.get("play_integrity") or {}
    if not pi.get("enabled"):
        warn.append("EGO_PLAY_INTEGRITY=0 — APK clonado pode abusar da API")
    elif pi.get("enabled") and not pi.get("server_configured"):
        warn.append("Play Integrity ligado mas Google JSON/project_number em falta")
    elif pi.get("mode") == "monitor" and pi.get("enabled"):
        warn.append("Play Integrity em modo monitor (normal até enforce)")

    return critical, warn


def main() -> int:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines: list[str] = [
        f"EGO-AI — monitor segurança · {now}",
        "=" * 55,
        "",
    ]
    critical: list[str] = []
    warn: list[str] = []

    status, health = fetch_json("/health")
    if status is None:
        critical.append(f"API offline: {health.get('error', '?')}")
        health = {}
    elif status != 200:
        critical.append(f"health HTTP {status}")
    else:
        c, w = evaluate_production(health)
        critical.extend(c)
        warn.extend(w)
        lines.append("PRODUÇÃO (/health)")
        lines.append(f"  ok={health.get('ok')} build={health.get('api_build', '?')}")
        lines.append(f"  maintenance={health.get('maintenance', False)}")
        mon = health.get("monitoring") or {}
        lines.append(
            f"  sentry={mon.get('sentry')} webhook={mon.get('alert_webhook_set')}"
        )
        pi = health.get("play_integrity") or {}
        lines.append(
            f"  play_integrity enabled={pi.get('enabled')} mode={pi.get('mode')}"
        )
        lines.append("")

    _, integrity = fetch_json("/integrity/status")
    if integrity.get("enabled") is not None:
        lines.append("INTEGRIDADE (/integrity/status)")
        lines.append(f"  {json.dumps(integrity, ensure_ascii=False)}")
        lines.append("")

    audit_ok, audit_tail = _run_audit()
    lines.append(f"CÓDIGO LOCAL (security_prelaunch_audit): {'OK' if audit_ok else 'FALHOU'}")
    if not audit_ok:
        critical.append("security_prelaunch_audit falhou")
        lines.append(audit_tail)
    lines.append("")

    err_count, err_msg = _recent_error_count()
    lines.append(f"ERROS SUPABASE (24h): {err_msg}")
    if err_count is not None and err_count > 50:
        warn.append(f"Muitos erros nas últimas 24h: {err_count}")
    lines.append("")

    if critical:
        lines.append("CRÍTICO:")
        for x in critical:
            lines.append(f"  [!] {x}")
        lines.append("")
    if warn:
        lines.append("AVISOS:")
        for x in warn:
            lines.append(f"  [~] {x}")
        lines.append("")
    if not critical and not warn:
        lines.append("Tudo OK — nenhum alerta de segurança.")
        lines.append("")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nGravado em: {OUT}")

    if critical:
        _alert_webhook("CRÍTICO", "\n".join(critical + warn))
        return 1
    if warn and os.getenv("SECURITY_ALERT_ON_WARN", "").lower() in ("1", "true", "yes"):
        _alert_webhook("Aviso", "\n".join(warn))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
