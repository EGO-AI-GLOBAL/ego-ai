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

init_sentry()
register_flask_handlers(app)
_sb_boot = supabase_env_status()
print(
    "EGO_BOOT",
    f"service={os.getenv('RAILWAY_SERVICE_NAME', '?')}",
    f"env={os.getenv('RAILWAY_ENVIRONMENT', '?')}",
    f"url_set={_sb_boot.get('url_set')}",
    f"key_set={_sb_boot.get('key_set')}",
    f"key_len={_sb_boot.get('key_len')}",
    f"client_ok={_sb_boot.get('client_ok')}",
    flush=True,
)
CORS(
    app,
    resources={r"/api/*": {"origins": cors_origins()}},
    supports_credentials=False,
    allow_headers=["Content-Type", "Authorization", "X-Refresh-Token", "X-Play-Integrity"],
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
    body: dict[str, Any] = {"ok": True}
    if data:
        body.update(data)
    return jsonify(body), status


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
    return access, refresh


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
                client.auth.set_session(access, refresh)
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
                body.get("assistant_name") or persona_name or ui.get("ego_assistant_display_name") or "EGO-AI"
            )[:48]
            apply_assistant_name_from_avatar(persona_avatar)
            sess.timezone = str(body.get("timezone") or ui.get("ego_client_timezone") or "")[
                :120
            ]
            raw_tz = body.get("tz_offset_min", ui.get("ego_client_tz_offset_min"))
            try:
                sess.tz_offset_min = int(raw_tz) if raw_tz is not None else None
            except (TypeError, ValueError):
                sess.tz_offset_min = None
            sess.pdf_context = str(body.get("pdf_context") or ui.get("pdf_context") or "")
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
        g.supabase = client
        g.user_id = uid
        return f(*args, **kwargs)

    return wrapper


# --- Rotas públicas ---


@app.get("/api/health")
@app.get("/api/v1/health")
def health():
    sb = supabase_env_status()
    service_role_set = bool(read_env("SUPABASE_SERVICE_ROLE_KEY"))
    payload: dict[str, Any] = {
        "service": "ego-ai-api",
        "ok": True,
        "api_build": "2026-06-03-shared-calendars",
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
    try:
        from ego_api.monitoring import monitoring_status

        payload["monitoring"] = monitoring_status()
    except Exception:
        payload["monitoring"] = {"sentry": False}
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


@app.post("/api/v1/auth/login")
@rate_limit(15, 60, scope="ip")
def auth_login():
    data = request.get_json(silent=True) or {}
    payload, err = services.login(data.get("email", ""), data.get("password", ""))
    if err:
        return _json_error(err, 401)
    return _json_ok({"session": payload})


@app.post("/api/v1/auth/signup")
@rate_limit(10, 60, scope="ip")
def auth_signup():
    data = request.get_json(silent=True) or {}
    payload, err = services.signup(
        data.get("email", ""),
        data.get("password", ""),
        data.get("full_name", ""),
    )
    if err:
        return _json_error(err, 400)
    return _json_ok({"session": payload})


@app.post("/api/v1/auth/forgot-password")
@rate_limit(5, 60, scope="ip")
def auth_forgot_password():
    data = request.get_json(silent=True) or {}
    ok, err = services.request_password_reset(
        data.get("email", ""),
        redirect_to=str(data.get("redirect_to") or data.get("redirect_url") or ""),
    )
    if err:
        return _json_error(err, 400)
    return _json_ok(
        {
            "sent": ok,
            "message": "Se o e-mail existir, receberá instruções para redefinir a senha.",
        }
    )


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


@app.get("/api/v1/chat/messages")
@require_auth
def chat_list():
    messages = db.load_chat_history(g.supabase, g.user_id)
    return _json_ok({"messages": messages})


@app.post("/api/v1/chat/messages")
@require_auth
@rate_limit(30, 60, scope="user")
def chat_send():
    message = ""
    audio_b64 = None
    audio_bytes: bytes | None = None
    audio_mime = "audio/wav"
    speak_reply = False

    ctype = (request.content_type or "").lower()
    if "multipart/form-data" in ctype:
        message = str(request.form.get("message") or "")
        speak_reply = str(request.form.get("speak", "true")).lower() in (
            "1",
            "true",
            "yes",
        )
        audio_mime = str(request.form.get("audio_mime") or "audio/mp4")
        upload = request.files.get("audio")
        if upload:
            audio_bytes = upload.read()
            if upload.content_type:
                audio_mime = upload.content_type
            if not audio_bytes:
                return _json_error(
                    "Áudio vazio no envio. Grave de novo (microfone → falar → seta).",
                    400,
                )
        elif not message.strip():
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

    result, err = services.process_chat_message(
        g.supabase,
        g.user_id,
        message,
        audio_b64=audio_b64,
        audio_bytes=audio_bytes,
        audio_mime=audio_mime,
        speak_reply=speak_reply,
    )
    if err:
        return _json_error(err, 402 if "Limite" in err or "expirado" in err.lower() else 400)
    return _json_ok(result)


@app.post("/api/v1/tts")
@require_auth
@rate_limit(20, 60, scope="user")
def tts_speak():
    """Converte texto em áudio MP3 (Edge TTS) para o app reproduzir."""
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
        fields["ui_state"] = data["ui_state"]
    if "country" in data:
        fields["country"] = str(data["country"])[:80]
    ok, err = db.update_profile_fields(g.supabase, g.user_id, fields)
    if not ok:
        return _json_error(err or "Falha ao atualizar perfil.")
    return _json_ok({"updated": True})


@app.get("/api/v1/plans")
def plans_catalog():
    from ego_api.plans import (
        PLAN_CONNECTION,
        PLAN_LABELS,
        PLAN_PRICES_BRL,
        PLAN_TIERS,
        plan_limits,
        stripe_launch_checkout_url,
    )

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
    launch_url = stripe_launch_checkout_url()
    launch_offer = None
    if launch_url:
        lim = plan_limits(PLAN_CONNECTION)
        launch_offer = {
            "tier": PLAN_CONNECTION,
            "label": "EGO Conexão — Oferta de lançamento",
            "price_brl": 9.9,
            "price_label": "R$ 9,90/mês",
            "tagline": "Mesmos benefícios da Conexão · depois R$ 29,90/mês",
            "checkout_url": launch_url,
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
    return _json_ok({"plans": items, "launch_offer": launch_offer})


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
    prof = db.load_profile(g.supabase, g.user_id)
    user_tier = resolve_plan_tier(prof)

    preset = str(data.get("preset") or "").strip().lower()
    if preset:
        match = next((p for p in PERSONA_PRESETS if p["id"] == preset), None)
        if not match:
            return _json_error("preset inválido. Use male ou female.", 400)
        avatar_id, voice_id = match["avatar_id"], match["voice_id"]
    else:
        raw_avatar = str(data.get("avatar_id") or "f1")
        raw_voice = str(data.get("voice_id") or "") or None
        avatar_id, voice_id, block = validate_avatar_choice(
            user_tier, raw_avatar, raw_voice
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
    rows = db.list_reminders(g.supabase, g.user_id)
    return _json_ok({"reminders": rows})


@app.post("/api/v1/reminders")
@require_auth
def reminders_create():
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
        return _json_error(err or "Não foi possível criar o lembrete.")
    return _json_ok({"reminder": row}, 201)


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
            data.get("dias_da_semana") or data.get("weekdays") or data.get("dias") or ""
        ),
    )
    if not ok:
        return _json_error(err or "Não foi possível criar na agenda.")
    return _json_ok({"item": row}, 201)


@app.delete("/api/v1/agenda/<agenda_id>")
@require_auth
def agenda_delete(agenda_id: str):
    ok = db.delete_agenda(g.supabase, g.user_id, agenda_id)
    return _json_ok({"deleted": ok})


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
    email = str(data.get("email") or "").strip()
    if not email:
        return _json_error("Informe o e-mail do utilizador.")
    ok, err, row = sc.add_member_by_email(
        g.supabase, g.user_id, calendar_id, email
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
    return _json_ok({"event": row}, 201)


@app.post("/api/v1/shared-calendars/<calendar_id>/events/<event_id>/dismiss")
@require_auth
def shared_calendars_events_dismiss(calendar_id: str, event_id: str):
    from ego_api import shared_calendars as sc

    ok = sc.dismiss_event(g.supabase, g.user_id, calendar_id, event_id)
    return _json_ok({"dismissed": ok})


@app.post("/api/v1/auth/logout")
@require_auth
def auth_logout():
    try:
        g.supabase.auth.sign_out()
    except Exception:
        pass
    set_session(None)
    return _json_ok({"logged_out": True})


if __name__ == "__main__":
    host = os.getenv("EGO_API_HOST", "127.0.0.1")
    port = int(os.getenv("EGO_API_PORT") or os.getenv("PORT", "5000"))
    debug = os.getenv("EGO_API_DEBUG", "").lower() in ("1", "true", "yes")
    if is_production_env():
        debug = False
    app.run(host=host, port=port, debug=debug)
