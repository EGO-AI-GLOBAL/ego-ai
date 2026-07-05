"""
API REST do EGO-AI (Flask + JSON + CORS).

O painel Streamlit (`app.py`) permanece inalterado. Esta API espelha as operações
principais para o app mobile consumir via HTTP.

Executar:
  pip install flask flask-cors
  python flask_api.py

Ou:
  flask --app flask_api run --host 0.0.0.0 --port 5000
"""

from __future__ import annotations

import base64
import json
import os
import time
from functools import wraps
from typing import Any, Callable

import html as html_lib
import re

from flask import Flask, Response, g, jsonify, request
from flask_cors import CORS

from ego_api.config import (
    GEMINI_MODEL_FLASH,
    cors_origins,
    gemini_api_key,
    is_production_env,
    production_bypass_warnings,
    read_env,
    supabase_anon_key,
    supabase_url,
)
from ego_api.request_ctx import UserSession, get_session, set_session
from ego_api import db, services
from ego_api.supabase_client import apply_user_auth, create_anon_client, supabase_env_status

try:
    from legal_copy import (
        privacy_policy_markdown,
        refund_policy_markdown,
        terms_of_use_markdown,
    )
except ImportError:

    def terms_of_use_markdown() -> str:
        return "Termos indisponíveis."

    def privacy_policy_markdown() -> str:
        return "Privacidade indisponível."

    def refund_policy_markdown() -> str:
        return "Reembolso indisponível."


app = Flask(__name__)
from ego_api.monitoring import init_sentry, register_flask_handlers  # noqa: E402

_sentry_boot = init_sentry()
register_flask_handlers(app)
_sb_boot = supabase_env_status()
print(
    "EGO_BOOT",
    f"service={os.getenv('RAILWAY_SERVICE_NAME', '?')}",
    f"env={os.getenv('RAILWAY_ENVIRONMENT', '?')}",
    f"sentry={_sentry_boot}",
    f"url_set={_sb_boot.get('url_set')}",
    f"key_set={_sb_boot.get('key_set')}",
    f"key_len={_sb_boot.get('key_len')}",
    f"client_ok={_sb_boot.get('client_ok')}",
    flush=True,
)
for _sec_warn in production_bypass_warnings():
    print("EGO_SECURITY_WARN", _sec_warn, flush=True)
CORS(
    app,
    resources={r"/api/*": {"origins": cors_origins()}},
    supports_credentials=False,
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-Refresh-Token",
        "X-Play-Integrity",
        "X-EGO-Platform",
        "X-Admin-Key",
    ],
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)

_RATE_BUCKETS: dict[str, list[float]] = {}


def _is_secure_request() -> bool:
    if request.is_secure:
        return True
    proto = (request.headers.get("X-Forwarded-Proto") or "").lower()
    return proto == "https"


@app.before_request
def _enforce_https_if_enabled():
    if request.method == "OPTIONS":
        return None
    path = (request.path or "").rstrip("/")
    if path in ("/api/health", "/api/v1/health", "/stripe/webhook"):
        return None
    enforce_https = os.getenv("EGO_ENFORCE_HTTPS", "").lower() in ("1", "true", "yes")
    if not enforce_https:
        return None
    if _is_secure_request():
        return None
    return _json_error("HTTPS obrigatório.", 426)


def rate_limit(max_requests: int, window_seconds: int, scope: str = "ip"):
    def deco(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            if scope == "user":
                user_id = getattr(g, "user_id", "") or ""
                ident = str(user_id) if user_id else (request.remote_addr or "unknown")
            else:
                ident = request.remote_addr or "unknown"
            now = time.time()
            key = f"{scope}:{f.__name__}:{ident}"
            bucket = _RATE_BUCKETS.setdefault(key, [])
            cutoff = now - window_seconds
            bucket[:] = [t for t in bucket if t >= cutoff]
            if len(bucket) >= max_requests:
                retry_after = max(1, int(window_seconds - (now - bucket[0])))
                return _json_error(
                    "Muitas tentativas. Tente novamente em instantes.",
                    429,
                    retry_after=retry_after,
                )
            bucket.append(now)
            return f(*args, **kwargs)

        return wrapper

    return deco


def _json_error(message: str, status: int = 400, **extra: Any):
    body: dict[str, Any] = {"ok": False, "error": message}
    body.update(extra)
    return jsonify(body), status


def _json_ok(data: dict | None = None, status: int = 200):
    from ego_api.json_util import sanitize_for_json

    body: dict[str, Any] = {"ok": True}
    if data:
        body.update(sanitize_for_json(data))
    return jsonify(body), status


def _journey_after_agenda_step(step: str) -> dict[str, Any] | None:
    """EGO de Bolso: compromisso ou hábito marcado manualmente na agenda."""
    try:
        from ego_api import wellness_journey

        prof = db.load_profile(g.supabase, g.user_id) or {}
        tier, _ = db.user_plan_limits(prof)
        wellness_journey.record_step(g.supabase, g.user_id, step, plan_tier=tier)
        return wellness_journey.get_journey(g.supabase, g.user_id, plan_tier=tier)
    except Exception as exc:
        print(f"[EGO] journey agenda step error ({step}): {exc}", flush=True)
        return None


def _journey_snapshot() -> dict[str, Any] | None:
    """Estado actual da jornada (sem incrementar passo)."""
    try:
        from ego_api import wellness_journey

        prof = db.load_profile(g.supabase, g.user_id) or {}
        tier, _ = db.user_plan_limits(prof)
        return wellness_journey.get_journey(g.supabase, g.user_id, plan_tier=tier)
    except Exception:
        return None


def _request_client_body() -> dict:
    """JSON ou campos de formulário (voz multipart) com timezone do aparelho."""
    if request.is_json:
        data = request.get_json(silent=True) or {}
        return data if isinstance(data, dict) else {}
    body: dict = {}
    tz_name = request.form.get("timezone")
    if tz_name:
        body["timezone"] = tz_name
    raw_off = request.form.get("tz_offset_min")
    if raw_off not in (None, ""):
        try:
            body["tz_offset_min"] = int(raw_off)
        except (TypeError, ValueError):
            pass
    return body


def _parse_bearer() -> tuple[str, str]:
    """access_token, refresh_token (opcional, header X-Refresh-Token)."""
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        access = auth[7:].strip()
    else:
        access = ""
    refresh = request.headers.get("X-Refresh-Token", "").strip()
    # Upload nativo (FileSystem.uploadAsync) às vezes não envia Authorization no Android.
    if not access:
        form = request.form or {}
        raw = str(form.get("access_token") or form.get("authorization") or "").strip()
        if raw.lower().startswith("bearer "):
            raw = raw[7:].strip()
        if raw:
            access = raw
        if not refresh:
            refresh = str(
                form.get("refresh_token") or form.get("x_refresh_token") or ""
            ).strip()
    return access, refresh


def _multipart_voice_audio() -> tuple[bytes | None, str]:
    """Lê áudio de multipart — tolera nomes de campo alternativos e base64 no form."""
    audio_mime = str(request.form.get("audio_mime") or "audio/mp4")
    for key in ("audio", "file", "voice", "recording"):
        upload = request.files.get(key)
        if not upload:
            continue
        data = upload.read()
        if upload.content_type:
            audio_mime = upload.content_type
        if data:
            return data, audio_mime
    raw_b64 = str(request.form.get("audio_base64") or "").strip()
    if raw_b64:
        try:
            data = base64.b64decode(raw_b64, validate=False)
            if data:
                return data, audio_mime
        except (ValueError, TypeError):
            pass
    return None, audio_mime


def _optional_authenticated_profile() -> dict | None:
    """Perfil do utilizador logado (opcional) — para /plans personalizado."""
    access, refresh = _parse_bearer()
    if not access:
        return None
    client = create_anon_client()
    if not client:
        return None
    try:
        if refresh:
            try:
                client.auth.set_session(access, refresh)
            except Exception:
                client.postgrest.auth(access)
        else:
            client.postgrest.auth(access)
        user_resp = client.auth.get_user(access)
        user = getattr(user_resp, "user", None)
        uid = str(getattr(user, "id", "") or "") if user else ""
        if not uid:
            return None
        return db.load_profile(client, uid)
    except Exception:  # noqa: BLE001
        return None


def require_auth(f: Callable) -> Callable:
    @wraps(f)
    def wrapper(*args, **kwargs):
        access, refresh = _parse_bearer()
        if not access:
            return _json_error("Token ausente. Envie Authorization: Bearer <access_token>.", 401)
        client = create_anon_client()
        if not client:
            st = supabase_env_status()
            if not st.get("url_set") or not st.get("key_set"):
                return _json_error(
                    "Supabase não configurado no servidor. "
                    "No Railway, defina SUPABASE_URL e SUPABASE_KEY (sem aspas) e faça Redeploy.",
                    503,
                )
            return _json_error(
                "Supabase: variáveis presentes mas o cliente falhou ao iniciar. "
                "Confira se SUPABASE_KEY é a chave anon/publishable do projeto.",
                503,
            )
        try:
            if refresh:
                try:
                    client.auth.set_session(access, refresh)
                except Exception:
                    client.postgrest.auth(access)
            else:
                client.postgrest.auth(access)
            user_resp = client.auth.get_user(access)
            user = getattr(user_resp, "user", None)
            if not user:
                return _json_error("Sessão inválida ou expirada.", 401)
            uid = str(getattr(user, "id", "") or "")
            if not uid:
                return _json_error("Utilizador inválido.", 401)
        except Exception:  # noqa: BLE001
            return _json_error("Sessão inválida ou expirada.", 401)

        body = _request_client_body()
        meta = getattr(user, "user_metadata", None) or {}
        if not isinstance(meta, dict):
            meta = getattr(user, "raw_user_meta_data", None) or {}
        if not isinstance(meta, dict):
            meta = {}
        meta_name = ""
        user_email = str(getattr(user, "email", "") or "").strip()
        email_local = user_email.split("@")[0].strip().lower() if "@" in user_email else ""
        if isinstance(meta, dict):
            meta_name = str(
                meta.get("full_name") or meta.get("name") or meta.get("first_name") or ""
            ).strip()
        set_session(
            UserSession(
                user_id=uid,
                email=str(getattr(user, "email", "") or ""),
                access_token=access,
                refresh_token=refresh,
            )
        )
        g.supabase = client
        g.user_id = uid

        try:
            prof = db.load_profile(client, uid) or {}
            ui = services.ui_state_from_profile(prof)
            from ego_api.persona import (
                apply_assistant_name_from_avatar,
                assistant_display_name_for_avatar,
                normalize_persona_pair,
            )

            stored_a, stored_v = db.load_persona(client, uid)
            persona_avatar, _persona_voice = normalize_persona_pair(stored_a, stored_v)
            persona_name = assistant_display_name_for_avatar(persona_avatar)
            sess = get_session()
            if sess:
                prof_name = str(prof.get("full_name") or "").strip()
                prof_name_is_email_alias = bool(
                    prof_name and email_local and prof_name.lower() == email_local
                )
                sess.user_name = str(
                    body.get("user_name")
                    or meta_name
                    or ("" if prof_name_is_email_alias else prof_name)
                    or ui.get("user_name")
                    or ""
                )[:200]
                sess.assistant_name = str(
                    body.get("assistant_name")
                    or persona_name
                    or ui.get("ego_assistant_display_name")
                    or "EGO-AI"
                )[:48]
                apply_assistant_name_from_avatar(persona_avatar)
                sess.timezone = str(
                    body.get("timezone") or ui.get("ego_client_timezone") or ""
                )[:120]
                raw_tz = body.get("tz_offset_min", ui.get("ego_client_tz_offset_min"))
                try:
                    sess.tz_offset_min = int(raw_tz) if raw_tz is not None else None
                except (TypeError, ValueError):
                    sess.tz_offset_min = None
                sess.pdf_context = str(
                    body.get("pdf_context") or ui.get("pdf_context") or ""
                )
                sess.gemini_model_preference = str(
                    body.get("gemini_model")
                    or ui.get("gemini_model_preference")
                    or GEMINI_MODEL_FLASH
                )
                if body.get("timezone") or body.get("tz_offset_min") is not None:
                    services.persist_client_timezone(
                        client,
                        uid,
                        timezone=str(sess.timezone or ""),
                        tz_offset_min=sess.tz_offset_min,
                    )
        except Exception as exc:  # noqa: BLE001
            from ego_api.monitoring import log_api_exception

            log_api_exception(exc, route=f"{request.path} (session enrich)")

        return f(*args, **kwargs)

    return wrapper


# --- Rotas públicas ---


@app.post("/stripe/webhook")
def stripe_webhook_route():
    """Stripe → ativa plano + comissão indicação (mesmo serviço ego-ai)."""
    sig = request.headers.get("Stripe-Signature", "").strip()
    try:
        from ego_api.stripe_webhook_handler import handle_stripe_webhook_payload
    except Exception as exc:  # noqa: BLE001
        return _json_error(f"Webhook indisponível: {exc}", 503)

    body, status = handle_stripe_webhook_payload(request.get_data(), sig or None)
    if status >= 400:
        return _json_error(str(body.get("error") or "Webhook Stripe falhou."), status)
    return _json_ok(body, status)


@app.get("/api/health")
@app.get("/api/v1/health")
def health():
    sb = supabase_env_status()
    service_role_set = bool(read_env("SUPABASE_SERVICE_ROLE_KEY"))
    payload: dict[str, Any] = {
        "service": "ego-ai-api",
        "ok": True,
        "api_build": "2026-07-05-pausa-exercises-push",
        "checks": {
            "supabase": bool(sb.get("client_ok")),
            "supabase_url_set": bool(sb.get("url_set")),
            "supabase_key_set": bool(sb.get("key_set")),
            "service_role_set": service_role_set,
            "shared_calendars_api": True,
        },
    }
    if not service_role_set:
        payload["deploy_hint"] = (
            "Adicione SUPABASE_SERVICE_ROLE_KEY no Railway e redeploy"
        )
    elif not sb.get("client_ok") and sb.get("url_set") and sb.get("key_set"):
        payload["deploy_hint"] = (
            "SUPABASE_URL ou SUPABASE_KEY invalidos no Railway — "
            "URL: https://SEU-PROJETO.supabase.co | KEY: Publishable (anon), nao service_role"
        )
        err = sb.get("client_error")
        if err:
            payload["supabase_error"] = str(err)[:200]
    try:
        from ego_api.monitoring import monitoring_status

        payload["monitoring"] = monitoring_status()
    except Exception:
        payload["monitoring"] = {"sentry": False}
    try:
        from ego_api.config import (
            app_update_payload,
            maintenance_message,
            maintenance_mode,
        )

        payload["app_update"] = app_update_payload()
        if maintenance_mode():
            payload["maintenance"] = True
            payload["maintenance_message"] = maintenance_message()
    except Exception:
        pass
    try:
        from ego_api.signup_emails import signup_emails_status

        payload["signup_emails"] = signup_emails_status()
    except Exception:
        pass
    try:
        from ego_api.auth_reset import password_reset_emails_status

        payload["password_reset_emails"] = password_reset_emails_status()
    except Exception:
        pass
    try:
        from ego_api.ego_de_bolso_push import ego_de_bolso_push_status

        payload["ego_de_bolso_push"] = ego_de_bolso_push_status()
    except Exception:
        pass
    try:
        from ego_api.pausa_push import pausa_push_status

        payload["pausa_push"] = pausa_push_status()
    except Exception:
        pass
    try:
        from ego_api.plan_retention import plan_retention_status

        payload["plan_retention"] = plan_retention_status()
    except Exception:
        pass
    try:
        from ego_api.config import (
            chat_defer_tts_on_voice,
            voice_fast_mode,
            voice_max_output_tokens,
        )

        payload["voice"] = {
            "fast_path": voice_fast_mode(),
            "defer_tts_on_voice": chat_defer_tts_on_voice(),
            "inline_tts": read_env("EGO_CHAT_INLINE_TTS", "0").lower()
            in ("1", "true", "yes", "sim"),
            "max_tokens": voice_max_output_tokens(),
        }
    except Exception:
        payload["voice"] = {"fast_path": False}
    try:
        from ego_api.openai_realtime import is_available as realtime_available

        payload["realtime"] = {"available": realtime_available()}
    except Exception:
        pass
    try:
        from ego_api.play_integrity import status_payload

        payload["play_integrity"] = status_payload()
    except Exception:
        pass
    try:
        from ego_api import openai_realtime

        payload["realtime"] = {"available": openai_realtime.is_available()}
    except Exception:
        payload["realtime"] = {"available": False}
    include_details = os.getenv("EGO_HEALTH_DETAILS", "").lower() in ("1", "true", "yes")
    if include_details:
        payload["checks"].update(
            {
                "supabase_key_len": int(sb.get("key_len") or 0),
                "gemini": bool(gemini_api_key()),
                "railway_service": os.getenv("RAILWAY_SERVICE_NAME", ""),
                "railway_environment": os.getenv("RAILWAY_ENVIRONMENT", ""),
            }
        )
        err = sb.get("client_error")
        if err:
            payload["checks"]["supabase_client_error"] = str(err)
    return _json_ok(payload)


@app.get("/api/v1/integrity/status")
def integrity_status():
    from ego_api.play_integrity import status_payload

    return _json_ok(status_payload())


@app.post("/api/v1/auth/login")
@rate_limit(15, 60, scope="ip")
def auth_login():
    data = request.get_json(silent=True) or {}
    payload, err = services.login(data.get("email", ""), data.get("password", ""))
    if err:
        return _json_error(err, 401)
    return _json_ok({"session": payload})


@app.post("/api/v1/auth/signup-check")
@rate_limit(30, 60, scope="ip")
def auth_signup_check():
    data = request.get_json(silent=True) or {}
    result = services.signup_check(data.get("email", ""), data.get("phone", ""))
    if result.get("ok"):
        return _json_ok(result)
    return _json_ok({**result, "ok": False})


@app.post("/api/v1/auth/signup")
@rate_limit(10, 60, scope="ip")
def auth_signup():
    data = request.get_json(silent=True) or {}
    payload, err = services.signup(
        data.get("email", ""),
        data.get("password", ""),
        data.get("full_name", ""),
        data.get("phone", ""),
        referral_code=str(data.get("referral_code") or data.get("referralCode") or ""),
    )
    if err:
        return _json_error(err, 400)
    if payload.get("access_token"):
        return _json_ok({"session": payload})
    return _json_ok({"session": None, "message": payload.get("message"), "user": payload.get("user")})


def _check_admin_key() -> str | None:
    from ego_api.referrals import admin_api_key

    expected = admin_api_key()
    if not expected:
        return "Admin não configurado (REFERRAL_ADMIN_SECRET)."
    provided = request.headers.get("X-Admin-Key", "").strip()
    if not provided:
        auth = request.headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            provided = auth[7:].strip()
    if not provided or provided != expected:
        return "Chave de admin inválida."
    return None


def require_admin(f: Callable) -> Callable:
    @wraps(f)
    def wrapper(*args, **kwargs):
        err = _check_admin_key()
        if err:
            return _json_error(err, 401)
        return f(*args, **kwargs)

    return wrapper


@app.get("/api/v1/referrals/validate")
@rate_limit(60, 60, scope="ip")
def referrals_validate():
    from ego_api.referrals import validate_referral_code

    code = str(request.args.get("code") or request.args.get("ref") or "")
    if not code.strip():
        return _json_ok({"valid": False})
    info, err = validate_referral_code(code)
    if err:
        return _json_ok({"valid": False, "error": err})
    if not info:
        return _json_ok({"valid": False, "error": "Código não encontrado."})
    return _json_ok({"valid": True, **info})


@app.post("/api/v1/admin/test-signup-email")
@require_admin
def admin_test_signup_email():
    """Envia e-mail de boas-vindas de teste (não cria conta, não grava no perfil)."""
    from ego_api.signup_emails import (
        _first_name,
        _play_url,
        _welcome_bodies,
        email_configured,
        email_provider,
        send_signup_email,
        signup_emails_enabled,
    )

    if not signup_emails_enabled():
        return _json_error("EGO_SIGNUP_EMAIL_ENABLED está desligado.", 503)
    if not email_configured():
        return _json_error(
            "E-mail não configurado: BREVO_API_KEY, RESEND_API_KEY ou EGO_SMTP_PASSWORD.",
            503,
        )
    data = request.get_json(silent=True) or {}
    email = str(data.get("email") or "").strip()
    if not email or "@" not in email:
        return _json_error("Informe um e-mail válido no JSON: {\"email\":\"...\"}", 400)
    display = str(data.get("full_name") or data.get("fullName") or "").strip()
    name = _first_name(display, email)
    subject, text_body, html_body = _welcome_bodies(name, _play_url())
    try:
        send_signup_email(
            to_email=email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )
        return _json_ok(
            {
                "ok": True,
                "sent_to": email,
                "subject": subject,
                "provider": email_provider(),
            }
        )
    except Exception as exc:
        return _json_error(str(exc)[:400], 500)


@app.post("/api/v1/admin/cron/signup-reminders")
@require_admin
def admin_cron_signup_reminders():
    """Lembretes: 24h + semanal até login (máx. 4) para quem não fez login."""
    from ego_api.signup_emails import process_signup_reminders

    data = request.get_json(silent=True) or {}
    try:
        min_hours = int(data.get("min_hours") or request.args.get("min_hours") or 24)
        max_days = int(data.get("max_days") or request.args.get("max_days") or 7)
        limit = int(data.get("limit") or request.args.get("limit") or 50)
    except (TypeError, ValueError):
        return _json_error("min_hours, max_days e limit devem ser números.", 400)
    stats = process_signup_reminders(
        min_hours=max(1, min_hours),
        max_days=max(1, max_days),
        limit=min(200, max(1, limit)),
    )
    return _json_ok({"ok": True, "stats": stats})


@app.post("/api/v1/admin/cron/daily-stats")
@require_admin
def admin_cron_daily_stats():
    """Relatório diário de cadastros por e-mail (cron Railway)."""
    from ego_api.daily_stats_report import process_daily_stats_report

    data = request.get_json(silent=True) or {}
    try:
        history_days = int(data.get("history_days") or request.args.get("history_days") or 14)
    except (TypeError, ValueError):
        return _json_error("history_days deve ser número.", 400)
    dry_run = str(data.get("dry_run") or request.args.get("dry_run") or "").lower() in (
        "1",
        "true",
        "yes",
    )
    result = process_daily_stats_report(
        history_days=max(7, min(30, history_days)),
        dry_run=dry_run,
    )
    if result.get("error") and not result.get("ok"):
        code = 503 if "configurado" in str(result.get("error") or "").lower() else 500
        return _json_error(str(result["error"]), code)
    return _json_ok(result)


@app.post("/api/v1/admin/cron/ego-de-bolso-care")
@require_admin
def admin_cron_ego_de_bolso_care():
    """Push 10h/18h (fuso do aparelho): EGO de Bolso com missões pendentes."""
    from ego_api.ego_de_bolso_push import (
        process_ego_de_bolso_care_pushes,
        process_ego_de_bolso_morning_pushes,
        process_ego_de_bolso_pushes,
    )

    data = request.get_json(silent=True) or {}
    try:
        limit = int(data.get("limit") or request.args.get("limit") or 200)
    except (TypeError, ValueError):
        return _json_error("limit deve ser número.", 400)
    force = str(data.get("force") or request.args.get("force") or "").lower() in (
        "1",
        "true",
        "yes",
    )
    slot = str(data.get("slot") or request.args.get("slot") or "all").strip().lower()
    capped = min(500, max(1, limit))
    if slot == "morning":
        stats = process_ego_de_bolso_morning_pushes(limit=capped, force=force)
    elif slot in ("care", "evening", "18h"):
        stats = process_ego_de_bolso_care_pushes(limit=capped, force=force)
    elif slot == "all":
        stats = process_ego_de_bolso_pushes(limit=capped, force=force)
    else:
        return _json_error("slot inválido — use morning, care ou all.", 400)
    return _json_ok({"ok": True, "slot": slot, "stats": stats})


@app.post("/api/v1/admin/cron/pausa-ego-push")
@require_admin
def admin_cron_pausa_ego_push():
    """Push 10h/18h (fuso do aparelho): PAUSA EGO quando ainda não fez hoje."""
    from ego_api.pausa_push import (
        process_pausa_evening_pushes,
        process_pausa_morning_pushes,
        process_pausa_pushes,
    )

    data = request.get_json(silent=True) or {}
    try:
        limit = int(data.get("limit") or request.args.get("limit") or 200)
    except (TypeError, ValueError):
        return _json_error("limit deve ser número.", 400)
    force = str(data.get("force") or request.args.get("force") or "").lower() in (
        "1",
        "true",
        "yes",
    )
    slot = str(data.get("slot") or request.args.get("slot") or "all").strip().lower()
    capped = min(500, max(1, limit))
    if slot == "morning":
        stats = process_pausa_morning_pushes(limit=capped, force=force)
    elif slot in ("evening", "care", "18h"):
        stats = process_pausa_evening_pushes(limit=capped, force=force)
    elif slot == "all":
        stats = process_pausa_pushes(limit=capped, force=force)
    else:
        return _json_error("slot inválido — use morning, evening ou all.", 400)
    return _json_ok({"ok": True, "slot": slot, "stats": stats})


@app.post("/api/v1/admin/cron/plan-retention")
@require_admin
def admin_cron_plan_retention():
    """E-mail + push: trial 3 dias antes, trial expirado (varredura). Limite diário via chat."""
    from ego_api.plan_retention import process_plan_retention_cron

    data = request.get_json(silent=True) or {}
    try:
        limit = int(data.get("limit") or request.args.get("limit") or 150)
    except (TypeError, ValueError):
        return _json_error("limit deve ser número.", 400)
    stats = process_plan_retention_cron(limit=min(300, max(1, limit)))
    return _json_ok({"ok": True, "stats": stats})


@app.post("/api/v1/admin/referrals/partners")
@require_admin
def admin_referrals_create_partner():
    from ego_api.referrals import create_partner, partner_signup_link

    data = request.get_json(silent=True) or {}
    row, err = create_partner(
        code=str(data.get("code") or ""),
        display_name=str(data.get("display_name") or data.get("displayName") or ""),
        contact_email=str(data.get("contact_email") or data.get("contactEmail") or ""),
        payout_pix=str(data.get("payout_pix") or data.get("payoutPix") or ""),
        notes=str(data.get("notes") or ""),
    )
    if err:
        return _json_error(err, 400)
    code = str((row or {}).get("code") or "")
    return _json_ok(
        {
            "partner": row,
            "signup_link": partner_signup_link(code),
        },
        201,
    )


@app.get("/api/v1/admin/referrals/report.csv")
@require_admin
def admin_referrals_report_csv():
    from ego_api.referrals import commissions_report_csv

    month = str(request.args.get("month") or "").strip()
    csv_text, err = commissions_report_csv(month)
    if err:
        return _json_error(err, 400)
    return Response(
        csv_text,
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="indicacoes-{month}.csv"'
        },
    )


@app.post("/api/v1/auth/forgot-password")
@rate_limit(5, 60, scope="ip")
def auth_forgot_password():
    from ego_api.auth_signup import MSG_RESET_SENT

    data = request.get_json(silent=True) or {}
    ok, err = services.request_password_reset(
        data.get("email", ""),
        redirect_to=str(data.get("redirect_to") or data.get("redirect_url") or ""),
    )
    if not ok:
        return _json_error(err or "Não foi possível enviar o e-mail.", 400)
    return _json_ok({"sent": True, "message": MSG_RESET_SENT})


@app.post("/api/v1/auth/reset-password")
@rate_limit(10, 60, scope="ip")
def auth_reset_password():
    data = request.get_json(silent=True) or {}
    payload, err = services.complete_password_reset(
        str(data.get("access_token") or ""),
        str(data.get("refresh_token") or ""),
        str(data.get("password") or ""),
    )
    if err:
        return _json_error(err, 400)
    return _json_ok({"session": payload, "message": "Senha alterada com sucesso."})


@app.get("/auth/reset-password")
def auth_reset_password_page():
    from ego_api.auth_reset import render_reset_password_page
    from ego_api.config import read_env

    api_base = read_env("EGO_PUBLIC_API_URL", "").strip()
    body, status, headers = render_reset_password_page(api_base=api_base)
    return Response(body, status=status, headers=headers)


@app.post("/api/v1/auth/refresh")
@rate_limit(20, 60, scope="ip")
def auth_refresh():
    data = request.get_json(silent=True) or {}
    token = data.get("refresh_token") or request.headers.get("X-Refresh-Token", "")
    payload, err = services.refresh_session(token)
    if err:
        return _json_error(err, 401)
    return _json_ok({"session": payload})


def _markdown_to_html_body(md: str) -> str:
    out: list[str] = []
    for raw in (md or "").splitlines():
        line = raw.rstrip()
        if not line.strip():
            out.append("<p>&nbsp;</p>")
            continue
        if line.startswith("### "):
            out.append(f"<h3>{html_lib.escape(line[4:].strip())}</h3>")
        elif line.startswith("## "):
            out.append(f"<h2>{html_lib.escape(line[3:].strip())}</h2>")
        elif line.startswith("# "):
            out.append(f"<h1>{html_lib.escape(line[2:].strip())}</h1>")
        elif line.startswith("- "):
            out.append(f"<li>{html_lib.escape(line[2:].strip())}</li>")
        else:
            text = html_lib.escape(line)
            text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
            out.append(f"<p>{text}</p>")
    return "\n".join(out)


def _legal_html_page(title: str, markdown_text: str) -> Response:
    body = _markdown_to_html_body(markdown_text)
    page = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html_lib.escape(title)} — EGO-AI</title>
</head>
<body>
  <article style="max-width:720px;margin:2rem auto;padding:0 1rem;font-family:system-ui,sans-serif;line-height:1.55;color:#111">
    <h1>{html_lib.escape(title)}</h1>
    {body}
  </article>
</body>
</html>"""
    return Response(page, mimetype="text/html; charset=utf-8")


@app.get("/go")
@app.get("/baixar")
@app.get("/cadastro")
@app.get("/api/v1/go")
def download_go_page():
    from ego_api.download_go import render_go_page

    ref = str(request.args.get("ref") or "")
    nxt = str(request.args.get("next") or "")
    fmt = str(request.args.get("format") or "").strip().lower()
    body, status, headers = render_go_page(
        ref=ref,
        next_step=nxt,
        user_agent=str(request.headers.get("User-Agent") or ""),
        force_format=fmt,
    )
    return Response(body, status=status, headers=headers)


@app.get("/privacy")
@app.get("/privacidade")
@app.get("/politica-de-privacidade")
def privacy_policy_page():
    return _legal_html_page("Política de Privacidade", privacy_policy_markdown())


@app.get("/terms")
@app.get("/termos")
def terms_page():
    return _legal_html_page("Termos de Uso", terms_of_use_markdown())


@app.get("/api/v1/legal/<doc>")
def legal(doc: str):
    docs = {
        "terms": ("terms", terms_of_use_markdown),
        "privacy": ("privacy", privacy_policy_markdown),
        "refund": ("refund", refund_policy_markdown),
    }
    entry = docs.get(doc.lower())
    if not entry:
        return _json_error("Documento não encontrado. Use terms, privacy ou refund.", 404)
    accept = (request.headers.get("Accept") or "").lower()
    if "text/html" in accept and doc.lower() in ("privacy", "terms", "refund"):
        titles = {
            "privacy": "Política de Privacidade",
            "terms": "Termos de Uso",
            "refund": "Política de Reembolso",
        }
        return _legal_html_page(titles[doc.lower()], entry[1]())
    return _json_ok({"document": entry[0], "markdown": entry[1]()})


# --- Rotas autenticadas ---


def _dashboard_payload():
    uid = getattr(g, "user_id", "") or ""
    try:
        return _json_ok(services.bootstrap_payload(g.supabase, uid))
    except Exception as exc:  # noqa: BLE001
        import traceback

        print(f"[EGO] bootstrap error user={uid}: {exc}", flush=True)
        traceback.print_exc()
        return _json_ok(services.bootstrap_payload_fallback(g.supabase, uid))


@app.post("/api/v1/app/bootstrap")
@require_auth
def app_bootstrap():
    """Carrega painel inteiro num único pedido (substitui vários GET no cliente)."""
    body = request.get_json(silent=True) or {}
    tz_off = body.get("tz_offset_min")
    tz_name = body.get("timezone")
    if tz_off is not None or tz_name:
        try:
            prof = db.load_profile(g.supabase, g.user_id) or {}
            ui = dict(services.ui_state_from_profile(prof))
            changed = False
            if tz_off is not None:
                ui["ego_client_tz_offset_min"] = int(tz_off)
                changed = True
            if tz_name:
                ui["ego_client_timezone"] = str(tz_name)[:120]
                changed = True
            if changed:
                db.update_profile_fields(g.supabase, g.user_id, {"ui_state": ui})
        except Exception:
            pass
    return _dashboard_payload()


@app.get("/api/v1/dashboard")
@require_auth
def app_dashboard_get():
    """Mesmo payload que bootstrap (compatível se o Flask não foi reiniciado após atualizar)."""
    return _dashboard_payload()


@app.get("/api/v1/me")
@require_auth
def me():
    return _json_ok(services.me_payload(g.supabase, g.user_id))


@app.delete("/api/v1/me")
@require_auth
@rate_limit(5, 3600, scope="user")
def me_delete():
    """Exclusão de conta in-app (Apple Guideline 5.1.1)."""
    from ego_api.account_delete import MSG_DELETE_OK, delete_user_account

    ok, err = delete_user_account(g.user_id)
    if not ok:
        return _json_error(err or "Não foi possível excluir a conta.", 400)
    return _json_ok({"deleted": True, "message": MSG_DELETE_OK})


@app.post("/api/v1/billing/apple/verify")
@require_auth
@rate_limit(12, 60, scope="user")
def billing_apple_verify():
    """Valida recibo Apple IAP e activa plano no perfil."""
    from ego_api.apple_iap import AppleIapError, verify_and_grant_plan
    from ego_api.stripe_webhook_handler import get_supabase_admin

    data = request.get_json(silent=True) or {}
    receipt = str(data.get("receipt_data") or data.get("receipt") or "").strip()
    product_id = str(data.get("product_id") or "").strip() or None
    transaction_id = str(data.get("transaction_id") or "").strip() or None
    try:
        supabase = get_supabase_admin()
        result = verify_and_grant_plan(
            supabase,
            g.user_id,
            receipt_data=receipt,
            product_id=product_id,
            transaction_id=transaction_id,
        )
    except AppleIapError as exc:
        return _json_error(str(exc), exc.status_code)
    except Exception as exc:  # noqa: BLE001
        return _json_error(str(exc)[:200], 500)
    return _json_ok(result)


@app.get("/api/v1/chat/messages")
@require_auth
def chat_list():
    messages = db.load_chat_history(g.supabase, g.user_id)
    return _json_ok({"messages": messages})


@app.post("/api/v1/chat/messages")
@require_auth
@rate_limit(30, 60, scope="user")
def chat_send():
    from ego_api.integrity_guard import evaluate_request_integrity

    allow, reason, blocked = evaluate_request_integrity()
    if blocked:
        return _json_error(
            "App não verificado. Instale pela Play Store (teste interno) e actualize.",
            403,
            integrity_reason=reason,
            play_store_url="https://play.google.com/apps/testing/com.egoai.app",
        )
    message = ""
    audio_b64 = None
    audio_bytes: bytes | None = None
    audio_mime = "audio/wav"
    speak_reply = False
    client_history = None

    ctype = (request.content_type or "").lower()
    if "multipart/form-data" in ctype:
        message = str(request.form.get("message") or "")
        speak_reply = str(request.form.get("speak", "true")).lower() in (
            "1",
            "true",
            "yes",
        )
        raw_hist = request.form.get("history")
        if raw_hist:
            try:
                client_history = json.loads(raw_hist)
            except (json.JSONDecodeError, TypeError):
                client_history = None
        audio_bytes, audio_mime = _multipart_voice_audio()
        if audio_bytes is not None and len(audio_bytes) < 128:
            return _json_error(
                "Áudio vazio no envio. Grave de novo (microfone → falar → seta).",
                400,
            )
        if audio_bytes is None and not message.strip():
            return _json_error(
                "Áudio não chegou ao servidor. Toque no microfone, fale e toque outra vez.",
                400,
            )
    else:
        data = request.get_json(silent=True) or {}
        message = str(data.get("message") or "")
        audio_b64 = data.get("audio_base64")
        audio_mime = str(data.get("audio_mime") or "audio/wav")
        speak_reply = bool(data.get("speak") or data.get("speak_reply"))
        client_history = data.get("history")

    try:
        result, err = services.process_chat_message(
            g.supabase,
            g.user_id,
            message,
            audio_b64=audio_b64,
            audio_bytes=audio_bytes,
            audio_mime=audio_mime,
            speak_reply=speak_reply,
            client_history=client_history,
        )
    except Exception as exc:
        from ego_api.api_errors import friendly_api_error
        from ego_api.monitoring import log_api_exception

        log_api_exception(exc, route="/api/v1/chat/messages")
        return _json_error(friendly_api_error(exc, context="chat"), 500)
    if err:
        return _json_error(err, 402 if "Limite" in err or "expirado" in err.lower() else 400)
    try:
        return _json_ok(result)
    except Exception as exc:
        from ego_api.api_errors import friendly_api_error
        from ego_api.monitoring import log_api_exception

        log_api_exception(exc, route="/api/v1/chat/messages")
        reply = (result or {}).get("reply") if isinstance(result, dict) else None
        if isinstance(reply, str) and reply.strip():
            try:
                return _json_ok(
                    {
                        "reply": reply.strip(),
                        "user_message_id": result.get("user_message_id"),
                        "assistant_message_id": result.get("assistant_message_id"),
                        "language": result.get("language") or "pt-BR",
                        "warnings": result.get("warnings") or [],
                        "reminders_saved": [],
                        "agenda_saved": [],
                        "shared_calendars_saved": [],
                        "shared_events_saved": [],
                        "shared_members_saved": [],
                        "shared_calendars_deleted": [],
                        "access": {},
                    }
                )
            except Exception:
                pass
        return _json_error(friendly_api_error(exc, context="chat"), 500)


@app.get("/api/v1/voice/realtime/status")
@require_auth
def voice_realtime_status():
    from ego_api import openai_realtime
    from ego_api.config import (
        openai_realtime_model,
        openai_realtime_phone_fast,
        openai_realtime_use_webrtc,
    )

    return _json_ok(
        {
            "available": openai_realtime.is_available(),
            "model": openai_realtime_model(),
            "webrtc": openai_realtime_use_webrtc(),
            "profile": "turbo" if openai_realtime_phone_fast() else "natural",
            "phone_fast": openai_realtime_phone_fast(),
        }
    )


@app.post("/api/v1/voice/realtime/client-secret")
@require_auth
@rate_limit(30, 60, scope="user")
def voice_realtime_client_secret():
    from ego_api import openai_realtime
    from ego_api.chat_local import parse_client_history
    from ego_api.integrity_guard import evaluate_request_integrity

    allow, reason, blocked = evaluate_request_integrity()
    if blocked:
        return _json_error(
            "App não verificado. Instale pela Play Store (teste interno) e actualize.",
            403,
            integrity_reason=reason,
            play_store_url="https://play.google.com/apps/testing/com.egoai.app",
        )
    if not openai_realtime.is_available():
        return _json_error("OpenAI Realtime não configurado no servidor.", 503)

    data = request.get_json(silent=True) or {}
    client_history = parse_client_history(data.get("history"))
    mode = str(data.get("mode") or "push").strip().lower()
    phone_call = mode in ("call", "phone", "telefone", "chamada")
    avatar_id, _ = services.ensure_persona_normalized(g.supabase, g.user_id)
    payload, err = openai_realtime.prepare_session_for_user(
        g.user_id,
        avatar_id,
        client_history=client_history,
        phone_call=phone_call,
    )
    if err:
        return _json_error(err, 502)
    print("[EGO] voice/realtime: client secret OK", flush=True)
    return _json_ok(payload)


@app.post("/api/v1/voice/realtime/webrtc")
@require_auth
@rate_limit(30, 60, scope="user")
def voice_realtime_webrtc():
    """WebRTC SDP answer — latência mínima (OpenAI /v1/realtime/calls)."""
    from ego_api import openai_realtime
    from ego_api.chat_local import parse_client_history
    from ego_api.integrity_guard import evaluate_request_integrity

    allow, reason, blocked = evaluate_request_integrity()
    if blocked:
        return _json_error(
            "App não verificado. Instale pela Play Store (teste interno) e actualize.",
            403,
            integrity_reason=reason,
            play_store_url="https://play.google.com/apps/testing/com.egoai.app",
        )
    if not openai_realtime.is_available():
        return _json_error("OpenAI Realtime não configurado no servidor.", 503)

    sdp_offer = ""
    client_history: list[dict] = []
    if request.content_type and "multipart" in request.content_type:
        sdp_offer = str(request.form.get("sdp") or "")
        client_history = parse_client_history(request.form.get("history"))
    else:
        sdp_offer = request.get_data(as_text=True) or ""
        if request.is_json:
            data = request.get_json(silent=True) or {}
            sdp_offer = str(data.get("sdp") or sdp_offer)
            client_history = parse_client_history(data.get("history"))

    avatar_id, _ = services.ensure_persona_normalized(g.supabase, g.user_id)
    answer, err = openai_realtime.prepare_webrtc_for_user(
        g.user_id,
        avatar_id,
        sdp_offer,
        client_history=client_history,
    )
    if err:
        return _json_error(err, 502)
    print("[EGO] voice/realtime: WebRTC SDP OK", flush=True)
    return answer, 200, {"Content-Type": "application/sdp"}


@app.post("/api/v1/voice/realtime/finish")
@require_auth
@rate_limit(30, 60, scope="user")
def voice_realtime_finish():
    from ego_api.chat_local import parse_client_history
    from ego_api.integrity_guard import evaluate_request_integrity

    allow, reason, blocked = evaluate_request_integrity()
    if blocked:
        return _json_error(
            "App não verificado. Instale pela Play Store (teste interno) e actualize.",
            403,
            integrity_reason=reason,
            play_store_url="https://play.google.com/apps/testing/com.egoai.app",
        )

    data = request.get_json(silent=True) or {}
    speak_reply = bool(data.get("speak"))
    user_message = str(data.get("user_message") or data.get("user_transcript") or "")
    assistant_reply = str(data.get("assistant_reply") or data.get("reply") or "")
    client_history = parse_client_history(data.get("history"))

    result, err = services.process_realtime_voice_turn(
        g.supabase,
        g.user_id,
        user_message=user_message,
        assistant_reply=assistant_reply,
        speak_reply=speak_reply,
        client_history=client_history,
    )
    if err:
        return _json_error(err, 402 if "Limite" in err or "expirado" in err.lower() else 400)
    print("[EGO] voice/realtime: turno guardado", flush=True)
    return _json_ok(result)


@app.post("/api/v1/tts")
@require_auth
@rate_limit(20, 60, scope="user")
def tts_speak():
    """Converte texto em áudio MP3 (Edge TTS) para o app reproduzir."""
    from ego_api.integrity_guard import evaluate_request_integrity

    allow, reason, blocked = evaluate_request_integrity()
    if blocked:
        return _json_error(
            "App não verificado. Instale pela Play Store (teste interno) e actualize.",
            403,
            integrity_reason=reason,
            play_store_url="https://play.google.com/apps/testing/com.egoai.app",
        )
    import base64

    from ego_api import tts

    data = request.get_json(silent=True) or {}
    from ego_api.tts import plain_text_for_speech

    text = plain_text_for_speech(str(data.get("text") or ""))
    if not text:
        return _json_error("text obrigatório.")
    prof = db.load_profile(g.supabase, g.user_id) or {}
    tts_err = services.enforce_tts_limit(g.supabase, g.user_id, prof)
    if tts_err:
        return _json_error(tts_err, 402)
    from ego_api.persona import resolve_tts_voice

    persona_avatar, persona_voice = db.load_persona(g.supabase, g.user_id)
    avatar_id = str(data.get("avatar_id") or persona_avatar or "f1").strip()
    voice_id = resolve_tts_voice(
        str(data.get("voice_id") or persona_voice or ""),
        avatar_id,
    )
    mp3 = tts.synthesize_speech_mp3(text, voice_id, avatar_id)
    if not mp3:
        return _json_error(
            "Não foi possível gerar áudio. Instale edge-tts no servidor: pip install edge-tts",
            503,
        )
    db.increment_daily_tts(g.supabase, g.user_id)
    return _json_ok(
        {
            "audio_base64": base64.b64encode(mp3).decode("ascii"),
            "mime": "audio/mpeg",
            "voice_id": voice_id,
        }
    )


@app.post("/api/v1/chat/feedback")
@require_auth
def chat_feedback():
    data = request.get_json(silent=True) or {}
    vote = data.get("vote")
    msg_id = str(data.get("message_id") or "")
    if vote not in (1, -1):
        return _json_error("vote deve ser 1 ou -1.")
    if not msg_id:
        return _json_error("message_id obrigatório.")
    ok = db.save_feedback(g.supabase, g.user_id, msg_id, int(vote))
    return _json_ok({"saved": ok})


@app.get("/api/v1/access")
@require_auth
def access_status():
    access = db.build_plan_access_payload(g.supabase, g.user_id)
    return _json_ok(access)


@app.get("/api/v1/profile")
@require_auth
def profile_get():
    prof = db.load_profile(g.supabase, g.user_id)
    return _json_ok({"profile": prof, "ui_state": services.ui_state_from_profile(prof)})


@app.patch("/api/v1/profile")
@require_auth
def profile_patch():
    data = request.get_json(silent=True) or {}
    fields: dict[str, Any] = {}
    if "full_name" in data:
        fields["full_name"] = str(data["full_name"])[:200]
    if "ui_state" in data and isinstance(data["ui_state"], dict):
        prof = db.load_profile(g.supabase, g.user_id) or {}
        current = services.ui_state_from_profile(prof)
        merged = {**current, **services.sanitize_user_ui_state(data["ui_state"])}
        fields["ui_state"] = merged
    if "country" in data:
        fields["country"] = str(data["country"])[:80]
    phone_norm: str | None = None
    if "phone" in data:
        from ego_api.phone_utils import normalize_phone_br

        phone_norm, phone_err = normalize_phone_br(str(data.get("phone") or ""))
        if phone_err:
            return _json_error(phone_err, 400)
        sess = get_session()
        ok, err = db.upsert_profile_phone(
            g.supabase,
            g.user_id,
            phone_norm,
            email=str(sess.email or "") if sess else "",
            full_name=str(sess.user_name or "") if sess and sess.user_name else "",
        )
        if not ok:
            return _json_error(err or "Falha ao atualizar telefone.")
        try:
            from ego_api import shared_calendars as sc

            sc.link_shared_memberships_for_user_phone(
                g.supabase, g.user_id, phone_norm
            )
        except Exception:
            pass
    if fields:
        ok, err = db.update_profile_fields(g.supabase, g.user_id, fields)
        if not ok:
            return _json_error(err or "Falha ao atualizar perfil.")
    prof = db.load_profile_trusted(g.supabase, g.user_id) or {}
    if phone_norm is not None:
        saved_ph = str(prof.get("phone") or "").strip()
        if saved_ph != phone_norm:
            return _json_error(
                "Não foi possível guardar o telefone. "
                "Pode já estar associado a outra conta.",
                400,
            )
    return _json_ok({"updated": True, "profile": prof})


@app.get("/api/v1/plans")
def plans_catalog():
    from ego_api.plans import (
        PLAN_LABELS,
        PLAN_PRICES_BRL,
        PLAN_TIERS,
        build_launch_offer_payload,
        plan_limits,
    )
    from ego_api.referrals import build_referral_offer_payload, should_hide_launch_offer
    from ego_api.supabase_client import create_service_client

    items = []
    for tier in PLAN_TIERS:
        lim = plan_limits(tier)
        items.append(
            {
                "tier": tier,
                "label": PLAN_LABELS[tier],
                "price_brl": PLAN_PRICES_BRL[tier],
                "limits": {
                    "monthly_tokens": lim.monthly_tokens,
                    "daily_text_messages": lim.daily_text_messages,
                    "daily_voice_messages": lim.daily_voice_messages,
                    "daily_tts_replies": lim.daily_tts_replies,
                    "max_agenda_items": lim.max_agenda_items,
                    "max_reminders": lim.max_reminders,
                    "audio_speed_multipliers": list(lim.audio_speed_multipliers),
                },
            }
        )
    items.sort(key=lambda row: float(row.get("price_brl") or 0))
    prof = _optional_authenticated_profile()
    launch_offer = None if should_hide_launch_offer(prof) else build_launch_offer_payload()
    referral_offer = build_referral_offer_payload(create_service_client(), prof)
    return _json_ok(
        {
            "plans": items,
            "launch_offer": launch_offer,
            "referral_offer": referral_offer,
        }
    )


@app.get("/api/v1/persona/options")
def persona_options():
    from ego_api.persona import persona_options_payload

    return _json_ok(persona_options_payload())


@app.get("/api/v1/persona")
@require_auth
def persona_get():
    from ego_api.persona import normalize_persona_pair

    avatar_id, voice_id = db.load_persona(g.supabase, g.user_id)
    avatar_id, voice_id = normalize_persona_pair(avatar_id, voice_id)
    return _json_ok({"avatar_id": avatar_id, "voice_id": voice_id})


@app.put("/api/v1/persona")
@app.post("/api/v1/persona")
@require_auth
def persona_put():
    from ego_api.persona import PERSONA_PRESETS, normalize_persona_pair, validate_avatar_choice
    from ego_api.plans import resolve_plan_tier

    data = request.get_json(silent=True) or {}
    prof = db.load_profile(g.supabase, g.user_id) or {}
    prof = db._profile_with_session_email(prof)
    prof = db.refresh_test_total_quota(g.supabase, g.user_id, prof)
    access = db.build_plan_access_payload(g.supabase, g.user_id, prof)
    user_tier = str(access.get("plan_tier") or resolve_plan_tier(prof))

    preset = str(data.get("preset") or "").strip().lower()
    raw_avatar = str(data.get("avatar_id") or "").strip()
    raw_voice = str(data.get("voice_id") or "").strip() or None

    # App 1.0.9: ao escolher Hana/Sara/etc. chama PUT {preset} e cai em Luna/Leo.
    # Rejeitar preset sem avatar_id faz o cliente usar savePersonaChoice (avatar_id/voice_id).
    if preset and not raw_avatar:
        return _json_error(
            "Envie avatar_id e voice_id para trocar o assistente.",
            400,
        )

    if preset:
        match = next((p for p in PERSONA_PRESETS if p["id"] == preset), None)
        if not match:
            return _json_error("preset inválido. Use male ou female.", 400)
        avatar_id, voice_id = match["avatar_id"], match["voice_id"]
    else:
        avatar_id, voice_id, block = validate_avatar_choice(
            user_tier, raw_avatar or "f1", raw_voice
        )
        if block:
            return _json_error(block, 402)
        avatar_id, voice_id = normalize_persona_pair(avatar_id, voice_id)

    avatar_id, voice_id, block = validate_avatar_choice(user_tier, avatar_id, voice_id)
    if block:
        return _json_error(block, 402)

    ok, err = db.save_persona(g.supabase, g.user_id, avatar_id, voice_id)
    if not ok:
        return _json_error(err or "Não foi possível guardar avatar e voz.", 500)
    services.persist_assistant_name_for_persona(
        g.supabase, g.user_id, prof, avatar_id
    )
    return _json_ok({"saved": True, "avatar_id": avatar_id, "voice_id": voice_id})


@app.get("/api/v1/reminders")
@require_auth
def reminders_list():
    rows = services.list_reminders_enriched(g.supabase, g.user_id)
    return _json_ok({"reminders": rows})


def _audio_from_request():
    """Extrai áudio (multipart ou JSON base64) do pedido atual."""
    import base64

    audio_b64 = None
    audio_bytes: bytes | None = None
    audio_mime = "audio/wav"
    ctype = (request.content_type or "").lower()
    if "multipart/form-data" in ctype:
        audio_mime = str(request.form.get("audio_mime") or "audio/mp4")
        upload = request.files.get("audio")
        if upload:
            audio_bytes = upload.read()
            if upload.content_type:
                audio_mime = upload.content_type
    else:
        data = request.get_json(silent=True) or {}
        audio_b64 = data.get("audio_base64")
        audio_mime = str(data.get("audio_mime") or "audio/wav")
        if audio_b64 and not audio_bytes:
            try:
                audio_bytes = base64.b64decode(str(audio_b64))
            except Exception:
                audio_bytes = None
    return audio_bytes, audio_mime


@app.post("/api/v1/night-dump")
@require_auth
@rate_limit(12, 60, scope="user")
def night_dump_submit():
    from ego_api.integrity_guard import evaluate_request_integrity

    allow, reason, blocked = evaluate_request_integrity()
    if blocked:
        return _json_error(
            "App não verificado. Instale pela Play Store (teste interno) e actualize.",
            403,
            integrity_reason=reason,
            play_store_url="https://play.google.com/apps/testing/com.egoai.app",
        )
    from ego_api import night_dump
    from ego_api.api_errors import friendly_api_error
    from ego_api.monitoring import log_api_exception

    data = request.get_json(silent=True) or {}
    text = str(request.form.get("text") or data.get("text") or "").strip()
    audio_bytes, audio_mime = _audio_from_request()
    try:
        result, err = night_dump.process_night_dump(
            g.supabase,
            g.user_id,
            text=text,
            audio_bytes=audio_bytes,
            audio_mime=audio_mime,
        )
    except Exception as exc:
        log_api_exception(exc, route="/api/v1/night-dump")
        return _json_error(friendly_api_error(exc, context="chat"), 500)
    if err:
        return _json_error(err, 400)
    try:
        journey = _journey_snapshot()
    except Exception:
        journey = None
    payload = dict(result or {})
    if journey:
        payload["wellness_journey"] = journey
    return _json_ok(payload, 201)


@app.get("/api/v1/agenda-drafts/pending")
@require_auth
def agenda_drafts_pending():
    from ego_api import habits_db

    rows = habits_db.list_pending_drafts(g.supabase, g.user_id)
    return _json_ok({"drafts": rows})


@app.post("/api/v1/agenda-drafts/<draft_id>/confirm")
@require_auth
def agenda_drafts_confirm(draft_id: str):
    from ego_api import night_dump

    data = request.get_json(silent=True) or {}
    indices = data.get("item_indices")
    if indices is not None and not isinstance(indices, list):
        indices = None
    reminders, shared_events, shopping, errors = night_dump.confirm_draft_items(
        g.supabase, g.user_id, draft_id, indices
    )
    confirmed = bool(reminders or shared_events or shopping)
    journey = None
    if confirmed:
        try:
            journey = _journey_after_agenda_step("draft_confirm")
        except Exception:
            journey = None
    payload: dict[str, Any] = {
        "reminders": reminders,
        "shared_events": shared_events,
        "shopping": shopping,
        "errors": errors,
        "confirmed": confirmed,
    }
    if journey:
        payload["wellness_journey"] = journey
    return _json_ok(payload)


@app.post("/api/v1/agenda-drafts/<draft_id>/dismiss")
@require_auth
def agenda_drafts_dismiss(draft_id: str):
    from ego_api import habits_db

    ok = habits_db.dismiss_draft(g.supabase, g.user_id, draft_id)
    return _json_ok({"dismissed": ok})


@app.post("/api/v1/agenda-drafts/<draft_id>/items/<int:item_index>/dismiss")
@require_auth
def agenda_drafts_dismiss_item(draft_id: str, item_index: int):
    from ego_api import night_dump

    ok, err = night_dump.dismiss_draft_item(
        g.supabase, g.user_id, draft_id, item_index
    )
    if not ok:
        return _json_error(err or "Não foi possível excluir o item.", 400)
    return _json_ok({"dismissed": True})


@app.get("/api/v1/shopping-list")
@require_auth
def shopping_list_get():
    from ego_api import habits_db

    orphan = request.args.get("orphans") in ("1", "true", "yes")
    persistent = request.args.get("persistent") in ("1", "true", "yes")
    reminder_id = str(request.args.get("reminder_id") or "").strip() or None
    if persistent:
        from ego_api import services as ego_services

        rows = ego_services.shopping_list_for_dashboard(g.supabase, g.user_id)
    else:
        rows = habits_db.list_shopping_items(
            g.supabase,
            g.user_id,
            reminder_id=reminder_id,
            orphans_only=orphan,
        )
    return _json_ok({"items": rows})


@app.post("/api/v1/shopping-list")
@require_auth
def shopping_list_create():
    from ego_api import habits_db

    data = request.get_json(silent=True) or {}
    title = str(data.get("title") or "").strip()
    if not title:
        return _json_error("title é obrigatório.")
    reminder_id = str(data.get("reminder_id") or "").strip() or None
    row = habits_db.insert_shopping_item(
        g.supabase,
        g.user_id,
        title=title,
        category=str(data.get("category") or "mercado"),
        reminder_id=reminder_id,
    )
    if not row:
        return _json_error("Não foi possível adicionar o item.")
    return _json_ok({"item": row}, 201)


@app.patch("/api/v1/shopping-list/<item_id>")
@require_auth
def shopping_list_patch(item_id: str):
    from ego_api import habits_db

    data = request.get_json(silent=True) or {}
    ok = habits_db.patch_shopping_item(
        g.supabase,
        g.user_id,
        item_id,
        done=data.get("done") if "done" in data else None,
        title=str(data.get("title")) if data.get("title") is not None else None,
    )
    return _json_ok({"updated": ok})


@app.delete("/api/v1/shopping-list/<item_id>")
@require_auth
def shopping_list_delete(item_id: str):
    from ego_api import habits_db

    ok = habits_db.delete_shopping_item(g.supabase, g.user_id, item_id)
    return _json_ok({"deleted": ok})


@app.get("/api/v1/delegation-requests/pending")
@require_auth
def delegation_requests_pending():
    from ego_api import delegation_db

    rows = delegation_db.list_pending_incoming(g.supabase, g.user_id)
    return _json_ok({"requests": rows})


@app.post("/api/v1/delegation-requests/<request_id>/confirm")
@require_auth
def delegation_requests_confirm(request_id: str):
    from ego_api import family_pilot
    from ego_api.api_errors import friendly_api_error
    from ego_api.monitoring import log_api_exception

    try:
        rem, err = family_pilot.confirm_delegation(g.supabase, g.user_id, request_id)
    except Exception as exc:
        log_api_exception(exc, route="/api/v1/delegation-requests/confirm")
        return _json_error(friendly_api_error(exc, context="reminder"), 500)
    if err:
        return _json_error(err, 400)
    return _json_ok({"reminder": rem, "confirmed": True})


@app.post("/api/v1/delegation-requests/<request_id>/dismiss")
@require_auth
def delegation_requests_dismiss(request_id: str):
    from ego_api import delegation_db

    ok = delegation_db.mark_dismissed(g.supabase, g.user_id, request_id)
    return _json_ok({"dismissed": ok})


@app.post("/api/v1/streaks/activity")
@require_auth
@rate_limit(24, 60, scope="user")
def streaks_record_activity():
    from ego_api import streaks

    data = request.get_json(silent=True) or {}
    source = str(data.get("source") or "habit").strip()[:32]
    streak = streaks.record_streak_activity(g.supabase, g.user_id, source=source)
    payload: dict[str, Any] = {"streak": streak}
    if str(source).strip() in ("habit", "reminder"):
        journey = _journey_snapshot()
        if journey:
            payload["wellness_journey"] = journey
    return _json_ok(payload)


@app.post("/api/v1/wellness-journey/step")
@require_auth
@rate_limit(48, 60, scope="user")
def wellness_journey_record_step():
    from ego_api import wellness_journey

    data = request.get_json(silent=True) or {}
    step = str(data.get("step") or "").strip()[:32]
    if not step:
        return _json_error("Informe o passo (step).")
    prof = db.load_profile(g.supabase, g.user_id) or {}
    tier, _ = db.user_plan_limits(prof)
    journey = wellness_journey.record_step(g.supabase, g.user_id, step, plan_tier=tier)
    journey = wellness_journey.sync_streak_levels(g.supabase, g.user_id, plan_tier=tier)
    return _json_ok({"wellness_journey": journey})


@app.post("/api/v1/wellness-journey/dismiss-level-up")
@require_auth
@rate_limit(12, 60, scope="user")
def wellness_journey_dismiss_level_up():
    from ego_api import wellness_journey

    journey = wellness_journey.clear_level_up_flag(g.supabase, g.user_id)
    return _json_ok({"wellness_journey": journey})


@app.post("/api/v1/wellness-journey/shop")
@require_auth
@rate_limit(20, 60, scope="user")
def wellness_journey_shop():
    from ego_api.companion_shop import purchase_egg_color

    data = request.get_json(silent=True) or {}
    color = str(data.get("color") or data.get("color_id") or data.get("item") or "").strip()[:24]
    if not color:
        return _json_error("Informe a cor do ovo (color).")
    prof = db.load_profile(g.supabase, g.user_id) or {}
    tier, _ = db.user_plan_limits(prof)
    journey = purchase_egg_color(g.supabase, g.user_id, color, plan_tier=tier)
    return _json_ok({"wellness_journey": journey})


@app.post("/api/v1/pausa-ego/complete")
@require_auth
@rate_limit(24, 60, scope="user")
def pausa_ego_complete():
    from ego_api import pausa_ego

    data = request.get_json(silent=True) or {}
    kind = str(data.get("kind") or "breath60").strip()[:16]
    pausa = pausa_ego.complete_session(g.supabase, g.user_id, kind=kind)
    return _json_ok({"pausa_ego": pausa})


@app.post("/api/v1/daily-care/quiz")
@require_auth
@rate_limit(8, 60, scope="user")
def daily_care_quiz():
    from ego_api import mood_quiz

    data = request.get_json(silent=True) or {}
    answer = str(data.get("answer") or data.get("answer_key") or "").strip()[:16]
    if not answer:
        return _json_error("Informe a resposta (answer).")
    result = mood_quiz.submit_answer(g.supabase, g.user_id, answer_key=answer)
    if not result.get("ok"):
        return _json_error(str(result.get("error") or "Resposta inválida."))
    body: dict = {"weekly_quiz": result.get("weekly_quiz")}
    if result.get("daily_care"):
        body["daily_care"] = result["daily_care"]
    if result.get("seeds_awarded"):
        body["seeds_awarded"] = result["seeds_awarded"]
    return _json_ok(body)


@app.post("/api/v1/daily-care/checkin")
@require_auth
@rate_limit(12, 60, scope="user")
def daily_care_checkin():
    from ego_api import daily_care, wellness_journey

    data = request.get_json(silent=True) or {}
    mood = str(data.get("mood") or data.get("mood_key") or "").strip()[:16]
    if not mood:
        return _json_error("Informe o humor (mood).")
    note_raw = data.get("note")
    note = str(note_raw).strip()[:280] if note_raw is not None else None
    if note == "":
        note = None
    care = daily_care.record_checkin(g.supabase, g.user_id, mood, note=note)
    prof = db.load_profile(g.supabase, g.user_id) or {}
    tier, _ = db.user_plan_limits(prof)
    journey = wellness_journey.sync_streak_levels(g.supabase, g.user_id, plan_tier=tier)
    return _json_ok({"daily_care": care, "wellness_journey": journey})


@app.post("/api/v1/daily-care/journal-note")
@require_auth
@rate_limit(12, 60, scope="user")
def daily_care_journal_note():
    from ego_api import daily_care

    data = request.get_json(silent=True) or {}
    note = str(data.get("note") or "")
    care = daily_care.record_journal_note(g.supabase, g.user_id, note)
    return _json_ok({"daily_care": care})


@app.post("/api/v1/daily-care/goal")
@require_auth
@rate_limit(20, 60, scope="user")
def daily_care_goal():
    from ego_api import daily_care

    data = request.get_json(silent=True) or {}
    goal = str(data.get("goal") or data.get("goal_key") or "").strip()[:24]
    if not goal:
        return _json_error("Informe a missão (goal).")
    care = daily_care.record_goal(g.supabase, g.user_id, goal)
    return _json_ok({"daily_care": care})


@app.post("/api/v1/daily-care/shop")
@require_auth
@rate_limit(20, 60, scope="user")
def daily_care_shop():
    from ego_api import daily_care

    data = request.get_json(silent=True) or {}
    item = str(data.get("item") or data.get("item_id") or "").strip()[:24]
    if not item:
        return _json_error("Informe o item da loja (item).")
    care = daily_care.purchase_shop_item(g.supabase, g.user_id, item)
    return _json_ok({"daily_care": care})


@app.post("/api/v1/reminders")
@require_auth
def reminders_create():
    from ego_api.api_errors import friendly_api_error
    from ego_api.monitoring import log_api_exception

    try:
        data = request.get_json(silent=True) or {}
        title = str(data.get("title") or "").strip()
        scheduled_at = data.get("scheduled_at")
        if not title or scheduled_at is None:
            return _json_error("title e scheduled_at são obrigatórios.")
        cap = services.enforce_reminder_limit(g.supabase, g.user_id)
        if cap:
            return _json_error(cap, 402)
        ok, err, row = db.insert_reminder(
            g.supabase,
            g.user_id,
            title=title,
            scheduled_at=scheduled_at,
            announce=str(data.get("announce") or title),
        )
        if not ok:
            return _json_error(
                friendly_api_error(err or "", context="reminder")
                or "Não foi possível criar o lembrete."
            )
        try:
            journey = _journey_after_agenda_step("reminder")
        except Exception:
            journey = None
        payload: dict[str, Any] = {"reminder": row}
        if journey:
            payload["wellness_journey"] = journey
        return _json_ok(payload, 201)
    except Exception as exc:  # noqa: BLE001
        log_api_exception(exc, route="/api/v1/reminders")
        return _json_error(friendly_api_error(exc, context="reminder"), 500)


@app.post("/api/v1/reminders/<reminder_id>/dismiss")
@require_auth
def reminders_dismiss(reminder_id: str):
    ok = db.dismiss_reminder(g.supabase, g.user_id, reminder_id)
    return _json_ok({"dismissed": ok})


@app.post("/api/v1/reminders/<reminder_id>/snooze")
@require_auth
def reminders_snooze(reminder_id: str):
    data = request.get_json(silent=True) or {}
    minutes = int(data.get("minutes", 5))
    ok = db.snooze_reminder(g.supabase, g.user_id, reminder_id, minutes)
    return _json_ok({"snoozed": ok})


@app.get("/api/v1/agenda")
@require_auth
def agenda_list():
    rows = db.list_agenda(g.supabase, g.user_id)
    return _json_ok({"agenda": rows})


@app.post("/api/v1/agenda")
@require_auth
def agenda_create():
    from ego_api.api_errors import friendly_api_error
    from ego_api.monitoring import log_api_exception

    try:
        data = request.get_json(silent=True) or {}
        cap = services.enforce_agenda_limit(g.supabase, g.user_id)
        if cap:
            return _json_error(cap, 402)
        ok, err, row = db.insert_agenda(
            g.supabase,
            g.user_id,
            titulo=str(data.get("titulo") or data.get("title") or ""),
            horario=data.get("horario") or data.get("time"),
            dias_da_semana=str(
                data.get("dias_da_semana")
                or data.get("weekdays")
                or data.get("dias")
                or ""
            ),
        )
        if not ok:
            return _json_error(
                friendly_api_error(err or "", context="agenda")
                or "Não foi possível criar na agenda."
            )
        journey = _journey_after_agenda_step("habit")
        payload: dict[str, Any] = {"item": row}
        if journey:
            payload["wellness_journey"] = journey
        return _json_ok(payload, 201)
    except Exception as exc:  # noqa: BLE001
        log_api_exception(exc, route="/api/v1/agenda")
        return _json_error(friendly_api_error(exc, context="agenda"), 500)


@app.delete("/api/v1/agenda/<agenda_id>")
@require_auth
def agenda_delete(agenda_id: str):
    ok = db.delete_agenda(g.supabase, g.user_id, agenda_id)
    return _json_ok({"deleted": ok})


@app.get("/api/v1/shared-calendars/pending-invites")
@require_auth
def shared_calendars_pending_invites():
    from ego_api import shared_calendars as sc

    rows = sc.list_pending_invites_for_user(g.supabase, g.user_id)
    return _json_ok({"pending_calendar_invites": rows})


@app.post("/api/v1/shared-calendars/member-invites/<member_id>/respond")
@require_auth
def shared_calendars_respond_member_invite(member_id: str):
    from ego_api import shared_calendars as sc

    data = request.get_json(silent=True) or {}
    accept = bool(data.get("accept"))
    ok, err, row = sc.respond_member_invite(
        g.supabase, g.user_id, member_id, accept=accept
    )
    if not ok:
        return _json_error(err or "Não foi possível responder ao convite.", 400)
    return _json_ok({"member": row, "accepted": accept})


@app.get("/api/v1/shared-calendars")
@require_auth
def shared_calendars_list():
    from ego_api import shared_calendars as sc

    rows = sc.list_calendars_for_user(g.supabase, g.user_id)
    return _json_ok({"shared_calendars": rows})


@app.post("/api/v1/shared-calendars")
@require_auth
def shared_calendars_create():
    from ego_api import shared_calendars as sc

    data = request.get_json(silent=True) or {}
    name = str(data.get("name") or "").strip()
    ok, err, row = sc.create_calendar(g.supabase, g.user_id, name=name)
    if not ok:
        return _json_error(err or "Não foi possível criar a agenda compartilhada.")
    return _json_ok({"calendar": row}, 201)


@app.get("/api/v1/shared-calendars/<calendar_id>")
@require_auth
def shared_calendars_get(calendar_id: str):
    from ego_api import shared_calendars as sc

    cal = sc.get_calendar(g.supabase, g.user_id, calendar_id)
    if not cal:
        return _json_error("Agenda não encontrada ou sem acesso.", 404)
    return _json_ok({"calendar": cal})


@app.delete("/api/v1/shared-calendars/<calendar_id>")
@require_auth
def shared_calendars_delete(calendar_id: str):
    from ego_api import shared_calendars as sc

    ok, err = sc.delete_calendar(g.supabase, g.user_id, calendar_id)
    if not ok:
        return _json_error(err or "Não foi possível apagar a agenda.", 400)
    return _json_ok({"deleted": True})


@app.post("/api/v1/shared-calendars/<calendar_id>/members")
@require_auth
def shared_calendars_add_member(calendar_id: str):
    from ego_api import shared_calendars as sc

    data = request.get_json(silent=True) or {}
    contact = str(
        data.get("email") or data.get("phone") or data.get("contact") or ""
    ).strip()
    if not contact:
        return _json_error("Informe e-mail ou telefone do utilizador.")
    ok, err, row = sc.add_member_by_contact(
        g.supabase, g.user_id, calendar_id, contact
    )
    if not ok:
        return _json_error(err or "Não foi possível adicionar o membro.")
    pending = str((row or {}).get("status") or "") == "pending"
    return _json_ok(
        {"member": row, "pending": pending, "message": err or ""},
        201,
    )


@app.delete("/api/v1/shared-calendars/<calendar_id>/members/<member_id>")
@require_auth
def shared_calendars_remove_member(calendar_id: str, member_id: str):
    from ego_api import shared_calendars as sc

    ok, err = sc.remove_member(g.supabase, g.user_id, calendar_id, member_id)
    if not ok:
        return _json_error(err or "Não foi possível remover.", 400)
    return _json_ok({"removed": True})


@app.get("/api/v1/shared-calendars/<calendar_id>/events")
@require_auth
def shared_calendars_events_list(calendar_id: str):
    from ego_api import shared_calendars as sc

    rows = sc.list_events(g.supabase, g.user_id, calendar_id)
    return _json_ok({"events": rows})


@app.post("/api/v1/shared-calendars/<calendar_id>/events")
@require_auth
def shared_calendars_events_create(calendar_id: str):
    from ego_api import shared_calendars as sc

    data = request.get_json(silent=True) or {}
    title = str(data.get("title") or "").strip()
    scheduled_at = data.get("scheduled_at")
    if not title or scheduled_at is None:
        return _json_error("title e scheduled_at são obrigatórios.")
    ok, err, row = sc.insert_event(
        g.supabase,
        g.user_id,
        calendar_id,
        title=title,
        scheduled_at=scheduled_at,
        announce=str(data.get("announce") or title),
    )
    if not ok:
        return _json_error(err or "Não foi possível marcar a reunião.")
    journey = _journey_after_agenda_step("reminder")
    payload: dict[str, Any] = {"event": row}
    if journey:
        payload["wellness_journey"] = journey
    return _json_ok(payload, 201)


@app.post("/api/v1/shared-calendars/<calendar_id>/events/<event_id>/dismiss")
@require_auth
def shared_calendars_events_dismiss(calendar_id: str, event_id: str):
    from ego_api import shared_calendars as sc

    ok = sc.dismiss_event(g.supabase, g.user_id, calendar_id, event_id)
    return _json_ok({"dismissed": ok})


@app.post("/api/v1/shared-calendars/<calendar_id>/events/<event_id>/respond")
@require_auth
def shared_calendars_events_respond(calendar_id: str, event_id: str):
    from ego_api import shared_calendars as sc

    data = request.get_json(silent=True) or {}
    accept = bool(data.get("accept"))
    ok, err, row = sc.respond_to_event(
        g.supabase,
        g.user_id,
        calendar_id,
        event_id,
        accept=accept,
    )
    if not ok:
        return _json_error(err or "Não foi possível registar a resposta.", 400)
    payload: dict[str, Any] = {"event": row, "accepted": accept}
    if accept:
        journey = _journey_after_agenda_step("reminder")
        if journey:
            payload["wellness_journey"] = journey
    return _json_ok(payload)


@app.post("/api/v1/auth/logout")
@require_auth
def auth_logout():
    try:
        g.supabase.auth.sign_out()
    except Exception:
        pass
    set_session(None)
    return _json_ok({"logged_out": True})


from ego_api.signup_emails import start_background_jobs as start_signup_background_jobs
from ego_api.ego_de_bolso_push import start_background_jobs as start_ego_bolso_push_jobs
from ego_api.pausa_push import start_background_jobs as start_pausa_push_jobs
from ego_api.plan_retention import start_background_jobs as start_plan_retention_jobs

start_signup_background_jobs()
start_ego_bolso_push_jobs()
start_pausa_push_jobs()
start_plan_retention_jobs()


if __name__ == "__main__":
    host = os.getenv("EGO_API_HOST", "127.0.0.1")
    port = int(os.getenv("EGO_API_PORT") or os.getenv("PORT", "5000"))
    debug = os.getenv("EGO_API_DEBUG", "").lower() in ("1", "true", "yes")
    if is_production_env():
        debug = False
    app.run(host=host, port=port, debug=debug)
