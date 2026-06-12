"""
Monitoramento: Sentry, Supabase (error_reports) e webhook (Discord/Slack).
"""

from __future__ import annotations

import logging
import os
import traceback
from datetime import datetime, timezone
from typing import Any

_LOG = logging.getLogger("ego.monitoring")
_sentry_ready = False


def sentry_enabled() -> bool:
    return bool((os.getenv("SENTRY_DSN") or "").strip())


def init_sentry() -> bool:
    global _sentry_ready
    dsn = (os.getenv("SENTRY_DSN") or "").strip()
    if not dsn:
        return False
    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration

        sentry_sdk.init(
            dsn=dsn,
            integrations=[FlaskIntegration()],
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
            profiles_sample_rate=0.0,
            environment=(
                os.getenv("SENTRY_ENVIRONMENT")
                or os.getenv("RAILWAY_ENVIRONMENT")
                or "production"
            ),
            release=(os.getenv("SENTRY_RELEASE") or os.getenv("RAILWAY_GIT_COMMIT_SHA") or "")[
                :40
            ]
            or None,
            send_default_pii=False,
        )
        _sentry_ready = True
        return True
    except Exception as exc:  # noqa: BLE001
        _LOG.warning("Sentry não iniciou: %s", exc)
        return False


def capture_exception(exc: BaseException, **extra: Any) -> str | None:
    if _sentry_ready:
        import sentry_sdk

        with sentry_sdk.push_scope() as scope:
            for k, v in extra.items():
                scope.set_extra(k, v)
            return sentry_sdk.capture_exception(exc)
    return None


def capture_message(message: str, level: str = "error", **extra: Any) -> str | None:
    if _sentry_ready:
        import sentry_sdk

        with sentry_sdk.push_scope() as scope:
            for k, v in extra.items():
                scope.set_extra(k, v)
            return sentry_sdk.capture_message(message, level=level)
    return None


def _alert_webhook(title: str, body: str) -> None:
    url = (os.getenv("ERROR_ALERT_WEBHOOK_URL") or "").strip()
    if not url or len(body) > 1800:
        body = body[:1800] + "…"
    if not url:
        return
    try:
        import httpx

        text = f"**EGO-AI — {title}**\n{body}"
        if "hooks.slack.com" in url:
            payload: dict[str, Any] = {"text": text.replace("**", "*")}
        else:
            payload = {"content": text}
        httpx.post(url, json=payload, timeout=8.0)
    except Exception as exc:  # noqa: BLE001
        _LOG.warning("Webhook alerta falhou: %s", exc)


def _supabase_admin():
    from ego_api.supabase_client import create_service_client

    return create_service_client()


def record_error_report(
    *,
    source: str,
    message: str,
    level: str = "error",
    stack: str = "",
    route: str = "",
    user_id: str | None = None,
    app_version: str = "",
    platform: str = "",
    meta: dict[str, Any] | None = None,
    alert: bool = True,
) -> dict[str, Any]:
    """Grava em Supabase e opcionalmente alerta (webhook + Sentry)."""
    message = (message or "erro")[:2000]
    stack = (stack or "")[:8000]
    route = (route or "")[:500]
    row = {
        "source": (source or "app")[:32],
        "level": (level or "error")[:16],
        "message": message,
        "stack": stack or None,
        "route": route or None,
        "user_id": user_id,
        "app_version": (app_version or "")[:32] or None,
        "platform": (platform or "")[:64] or None,
        "meta": meta or {},
    }
    stored = False
    report_id = None
    client = _supabase_admin()
    if client:
        try:
            res = client.table("error_reports").insert(row).execute()
            if res.data:
                report_id = res.data[0].get("id")
            stored = True
        except Exception as exc:  # noqa: BLE001
            _LOG.warning("error_reports insert: %s", exc)

    capture_message(
        f"[{source}] {message}",
        level="error" if level == "error" else "warning",
        route=route,
        user_id=user_id,
    )

    if alert and level == "error":
        _alert_webhook(
            f"{source} — {route or 'sem rota'}",
            f"{message}\n\nuser={user_id or '?'}\nplatform={platform}\nid={report_id or 'local'}",
        )

    return {"stored": stored, "id": report_id, "sentry": _sentry_ready}


def register_flask_handlers(app) -> None:
    """Handlers Flask: 500 → Sentry + log."""

    @app.errorhandler(500)
    def _handle_500(err):  # type: ignore[no-untyped-def]
        from flask import jsonify, request

        capture_exception(err)
        record_error_report(
            source="api",
            message=str(err),
            stack=traceback.format_exc(),
            route=request.path,
            alert=True,
        )
        from ego_api.api_errors import friendly_api_error

        return jsonify({"ok": False, "error": friendly_api_error(err, context="api")}), 500


def log_api_exception(exc: BaseException, *, route: str = "") -> None:
    """Chame em rotas críticas no except."""
    capture_exception(exc, route=route)
    record_error_report(
        source="api",
        message=str(exc),
        stack=traceback.format_exc(),
        route=route,
        alert=True,
    )


def monitoring_status() -> dict[str, Any]:
    return {
        "sentry": _sentry_ready,
        "sentry_dsn_set": sentry_enabled(),
        "alert_webhook_set": bool((os.getenv("ERROR_ALERT_WEBHOOK_URL") or "").strip()),
        "error_reports_table": "error_reports",
        "ts": datetime.now(timezone.utc).isoformat(),
    }
