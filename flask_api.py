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
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024
_sb_boot = supabase_env_status()
_test_total = (os.getenv("EGO_TEST_TOTAL_EMAILS") or "").strip()
print(
    "EGO_BOOT",
    f"service={os.getenv('RAILWAY_SERVICE_NAME', '?')}",
    f"env={os.getenv('RAILWAY_ENVIRONMENT', '?')}",
    f"url_set={_sb_boot.get('url_set')}",
    f"key_set={_sb_boot.get('key_set')}",
    f"key_len={_sb_boot.get('key_len')}",
    f"client_ok={_sb_boot.get('client_ok')}",
    f"test_total_emails={_test_total or 'off'}",
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
    path = request.path.rstrip("/") or "/"
    if path in ("/api/health", "/api/v1/health"):
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

        # POST /chat/messages: nunca parsear corpo aqui (voz multipart / base64 grande).
        path_tail = request.path.rstrip("/")
        skip_json_body = request.method == "POST" and (
            path_tail.endswith("/chat/messages")
            or path_tail.endswith("/chat/voice")
            or path_tail.endswith("/chat/voice/stream")
            or path_tail.endswith("/pdf/extract")
        )
        if skip_json_body:
            body = {}
        elif request.is_json:
            body = request.get_json(silent=True) or {}
        else:
            body = {}
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
            sess.tz_offset_min = body.get("tz_offset_min", ui.get("ego_client_tz_offset_min"))
            sess.pdf_context = str(body.get("pdf_context") or ui.get("pdf_context") or "")
            sess.gemini_model_preference = str(
                body.get("gemini_model")
                or ui.get("gemini_model_preference")
                or GEMINI_MODEL_FLASH
            )
        g.supabase = client
        g.user_id = uid
        return f(*args, **kwargs)

    return wrapper


def require_play_integrity(f: Callable) -> Callable:
    """Valida token Play Integrity (Android) quando EGO_PLAY_INTEGRITY=1."""

    @wraps(f)
    def wrapper(*args, **kwargs):
        from ego_api import play_integrity

        if not play_integrity.play_integrity_enabled():
            return f(*args, **kwargs)
        if not play_integrity.server_configured():
            print("[EGO] play_integrity: servidor sem credenciais Google", flush=True)
            if play_integrity.play_integrity_enforced():
                return _json_error("Integridade do app indisponível no servidor.", 503)
            return f(*args, **kwargs)

        token = request.headers.get("X-Play-Integrity", "").strip()
        ok, reason = play_integrity.verify_integrity_token(token)
        user_id = getattr(g, "user_id", "") or "?"
        if ok:
            print(f"[EGO] play_integrity ok user={user_id}", flush=True)
            return f(*args, **kwargs)

        print(f"[EGO] play_integrity fail user={user_id} reason={reason}", flush=True)
        if play_integrity.play_integrity_enforced():
            return _json_error(
                "Integridade do app não verificada. Instale o app oficial pela Play Store ou APK de teste.",
                403,
            )
        return f(*args, **kwargs)

    return wrapper


# --- Rotas públicas ---


@app.get("/api/health")
@app.get("/api/v1/health")
def health():
    sb = supabase_env_status()
    payload: dict[str, Any] = {
        "service": "ego-ai-api",
        "ok": True,
        "api_build": "2026-06-02-bootstrap-500-fix",
        "pdf_extract": True,
        "deploy_hint": "Adicione SUPABASE_SERVICE_ROLE_KEY no Railway e redeploy",
        "checks": {
            "supabase": bool(sb.get("client_ok")),
            "supabase_url_set": bool(sb.get("url_set")),
            "supabase_key_set": bool(sb.get("key_set")),
            "service_role_set": bool(read_env("SUPABASE_SERVICE_ROLE_KEY")),
        },
    }
    include_details = os.getenv("EGO_HEALTH_DETAILS", "").lower() in ("1", "true", "yes")
    if include_details:
        from ego_api import openai_realtime

        payload["checks"].update(
            {
                "supabase_key_len": int(sb.get("key_len") or 0),
                "gemini": bool(gemini_api_key()),
                "openai_realtime": openai_realtime.is_available(),
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
    from ego_api import play_integrity

    return _json_ok(play_integrity.status_payload())


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
        data.get("referral_code", "") or data.get("referral", ""),
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
    """HTML simples para crawlers (Google Play) e browser."""
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
    try:
        return _json_ok(services.bootstrap_payload(g.supabase, g.user_id))
    except Exception as exc:  # noqa: BLE001
        import traceback

        print(f"[EGO] bootstrap error user={getattr(g, 'user_id', '')}: {exc}", flush=True)
        traceback.print_exc()
        return _json_error(
            "Não foi possível carregar a agenda. Confirme SUPABASE_SERVICE_ROLE_KEY no Railway "
            "e as tabelas no Supabase (shared_calendars).",
            500,
        )


@app.post("/api/v1/app/bootstrap")
@require_auth
def app_bootstrap():
    """Carrega painel inteiro num único pedido (substitui vários GET no cliente)."""
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
    from ego_api.config import chat_local_history_enabled

    if chat_local_history_enabled():
        return _json_ok({"messages": [], "chat_local_history": True})
    messages = db.load_chat_history(g.supabase, g.user_id)
    return _json_ok({"messages": messages, "chat_local_history": False})


@app.post("/api/v1/chat/messages")
@require_auth
@require_play_integrity
@rate_limit(30, 60, scope="user")
def chat_send():
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
        from ego_api.chat_local import parse_client_history

        client_history = parse_client_history(request.form.get("history"))
        audio_mime = str(request.form.get("audio_mime") or "audio/webm")
        upload = request.files.get("audio")
        if upload:
            audio_bytes = upload.read()
            if upload.content_type:
                audio_mime = upload.content_type
            if not audio_bytes:
                return _json_error(
                    "Áudio vazio no envio. Grave de novo (microfone → falar → Enviar voz).",
                    400,
                )
        if not audio_bytes:
            from ego_api.audio_b64 import decode_audio_base64

            form_b64 = request.form.get("audio_base64")
            if form_b64:
                audio_bytes = decode_audio_base64(form_b64)
                if not audio_bytes:
                    return _json_error(
                        "Áudio inválido. Grave de novo: microfone → fale 2–3 s → Enviar voz.",
                        400,
                    )
        if not audio_bytes and not message.strip():
            hint = (
                "Áudio não chegou ao servidor. "
                "Confirme: (1) python flask_api.py a correr, "
                "(2) recarregue o browser com Ctrl+Shift+R, "
                "(3) microfone → fale 2–3 s → Enviar voz."
            )
            return _json_error(hint, 400)
    else:
        data = request.get_json(silent=True) or {}
        message = str(data.get("message") or "")
        audio_b64 = data.get("audio_base64")
        audio_mime = str(data.get("audio_mime") or "audio/wav")
        speak_reply = bool(data.get("speak") or data.get("speak_reply"))
        from ego_api.chat_local import parse_client_history

        client_history = parse_client_history(data.get("history"))
        if audio_b64 and not audio_bytes:
            from ego_api.audio_b64 import decode_audio_base64, normalize_audio_mime

            audio_bytes = decode_audio_base64(audio_b64)
            if audio_bytes:
                audio_mime = normalize_audio_mime(audio_mime, audio_bytes)
                audio_b64 = None
            else:
                return _json_error(
                    "Áudio inválido. Grave de novo: microfone → fale 2–3 s → Enviar voz.",
                    400,
                )

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
    if err:
        return _json_error(err, 402 if "Limite" in err or "expirado" in err.lower() else 400)
    return _json_ok(result)


@app.post("/api/v1/chat/voice")
@require_auth
@require_play_integrity
@rate_limit(30, 60, scope="user")
def chat_voice():
    """Mensagem de voz — só multipart (ficheiro binário), sem JSON/base64."""
    from ego_api.chat_local import parse_client_history

    print("[EGO] chat/voice: pedido recebido", flush=True)
    speak_reply = str(request.form.get("speak", "true")).lower() in ("1", "true", "yes")
    client_history = parse_client_history(request.form.get("history"))
    audio_mime = str(request.form.get("audio_mime") or "audio/webm")
    audio_bytes: bytes | None = None

    upload = request.files.get("audio")
    if upload:
        audio_bytes = upload.read()
        if upload.content_type:
            audio_mime = upload.content_type

    size = len(audio_bytes or b"")
    if size < 128:
        return _json_error(
            f"Áudio não recebido ({size} bytes). "
            "Reinicie python flask_api.py e o Expo, fale 3 segundos e toque Enviar voz.",
            400,
        )

    result, err = services.process_chat_message(
        g.supabase,
        g.user_id,
        "",
        audio_bytes=audio_bytes,
        audio_mime=audio_mime,
        speak_reply=speak_reply,
        client_history=client_history,
    )
    if err:
        print(f"[EGO] chat/voice: erro — {err}", flush=True)
        return _json_error(err, 402 if "Limite" in err or "expirado" in err.lower() else 400)
    print("[EGO] chat/voice: resposta OK", flush=True)
    return _json_ok(result)


@app.post("/api/v1/chat/voice/stream")
@require_auth
@require_play_integrity
@rate_limit(30, 60, scope="user")
def chat_voice_stream():
    """Voz com streaming NDJSON — texto aparece enquanto o Gemini gera."""
    from ego_api.chat_local import parse_client_history
    from ego_api.config import voice_stream_enabled
    from flask import stream_with_context

    if not voice_stream_enabled():
        return _json_error("Streaming de voz desativado no servidor.", 503)

    speak_reply = str(request.form.get("speak", "true")).lower() in ("1", "true", "yes")
    client_history = parse_client_history(request.form.get("history"))
    audio_mime = str(request.form.get("audio_mime") or "audio/webm")
    audio_bytes: bytes | None = None

    upload = request.files.get("audio")
    if upload:
        audio_bytes = upload.read()
        if upload.content_type:
            audio_mime = upload.content_type

    size = len(audio_bytes or b"")
    if size < 128:
        return _json_error(
            f"Áudio não recebido ({size} bytes). Grave 2–3 segundos e envie de novo.",
            400,
        )

    def generate():
        for event in services.iter_voice_chat_stream(
            g.supabase,
            g.user_id,
            audio_bytes=audio_bytes or b"",
            audio_mime=audio_mime,
            speak_reply=speak_reply,
            client_history=client_history,
        ):
            yield json.dumps(event, ensure_ascii=False) + "\n"

    return Response(
        stream_with_context(generate()),
        mimetype="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/v1/voice/realtime/status")
@require_auth
def voice_realtime_status():
    from ego_api import openai_realtime
    from ego_api.config import openai_realtime_model, openai_realtime_phone_fast, openai_realtime_use_webrtc

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
@require_play_integrity
@rate_limit(30, 60, scope="user")
def voice_realtime_client_secret():
    from ego_api import openai_realtime
    from ego_api.chat_local import parse_client_history

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
@require_play_integrity
@rate_limit(30, 60, scope="user")
def voice_realtime_webrtc():
    """WebRTC SDP answer — latência mínima (OpenAI /v1/realtime/calls)."""
    from ego_api import openai_realtime
    from ego_api.chat_local import parse_client_history

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
@require_play_integrity
@rate_limit(30, 60, scope="user")
def voice_realtime_finish():
    from ego_api.chat_local import parse_client_history

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


@app.post("/api/v1/pdf/extract")
@require_auth
def pdf_extract():
    from ego_api.document_extract import ALLOWED_SUFFIXES_LABEL, extract_text_from_uploads
    from ego_api.pdf_upload import collect_upload_file_bytes, filter_allowed_uploads

    try:
        raw_files, diag = collect_upload_file_bytes(request)
        if not raw_files:
            return _json_error(diag or "Nenhum documento recebido.")
        files, fmt_warnings = filter_allowed_uploads(raw_files)
        if not files:
            return _json_error(
                fmt_warnings[0]
                if fmt_warnings
                else f"Formato não suportado. Envie: {ALLOWED_SUFFIXES_LABEL}."
            )
        text, warnings = extract_text_from_uploads(files)
        warnings = fmt_warnings + list(warnings)
        if not text.strip():
            detail = "; ".join(warnings) if warnings else "Não foi possível extrair texto."
            return _json_error(detail)

        prof = db.load_profile(g.supabase, g.user_id) or {}
        ui = services.ui_state_from_profile(prof)
        prev = str(ui.get("pdf_context") or "").strip()
        from ego_api.document_extract import DOC_UPLOAD_MAX_FILES

        sep = "\n\n---\n\n"
        merged = sep.join([p for p in [prev, text.strip()] if p])
        count = int(ui.get("pdf_attachment_count") or 0)
        if prev:
            count = max(count, 1) + len(files)
        else:
            count = len(files)
        stored = False
        stored_chars = len(text)
        truncated = False
        try:
            capped, truncated = services.persist_pdf_context(
                g.supabase,
                g.user_id,
                merged,
                prof,
                attachment_count=count,
            )
            stored = True
            stored_chars = len(capped)
        except Exception as store_exc:
            warnings.append(f"Texto lido; perfil não sincronizado: {store_exc}")
        return _json_ok(
            {
                "text": text,
                "char_count": len(text),
                "warnings": warnings,
                "stored": stored,
                "stored_char_count": stored_chars,
                "stored_truncated": truncated,
                "pdf_attachment_count": min(count, DOC_UPLOAD_MAX_FILES * 24),
            }
        )
    except Exception as exc:  # noqa: BLE001
        return _json_error(str(exc) or "Falha ao processar documento.", 500)


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
        existing = services.ui_state_from_profile(prof)
        merged = {**existing, **data["ui_state"]}
        fields["ui_state"] = merged
    if "country" in data:
        fields["country"] = str(data["country"])[:80]
    ok, err = db.update_profile_fields(g.supabase, g.user_id, fields)
    if not ok:
        return _json_error(err or "Falha ao atualizar perfil.")
    return _json_ok({"updated": True})


@app.get("/api/v1/plans")
def plans_catalog():
    from ego_api.plans import PLAN_LABELS, PLAN_PRICES_BRL, PLAN_TIERS, plan_limits

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
    return _json_ok({"plans": items})


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
    return _json_ok({"member": row}, 201)


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


@app.post("/api/v1/referrals/validate")
@rate_limit(30, 60, scope="ip")
def referrals_validate():
    from ego_api import referrals

    data = request.get_json(silent=True) or {}
    code = str(data.get("code") or data.get("referral_code") or "")
    info, err = referrals.validate_referral_code(code)
    if err:
        return _json_error(err, 400)
    if not info:
        return _json_ok({"valid": False})
    return _json_ok({"valid": True, **info})


def _require_referral_admin() -> tuple[bool, Any]:
    from ego_api import referrals

    key = referrals.admin_api_key()
    if not key:
        return False, _json_error("Admin de indicações não configurado.", 503)
    sent = (
        request.headers.get("X-Admin-Key") or request.args.get("admin_key") or ""
    ).strip()
    if sent != key:
        return False, _json_error("Não autorizado.", 401)
    return True, None


@app.post("/api/v1/admin/referrals/partners")
def admin_referral_create_partner():
    ok, err_resp = _require_referral_admin()
    if not ok:
        return err_resp
    from ego_api import referrals

    data = request.get_json(silent=True) or {}
    partner, err = referrals.create_partner(
        code=str(data.get("code") or ""),
        display_name=str(data.get("display_name") or data.get("name") or ""),
        contact_email=str(data.get("contact_email") or data.get("email") or ""),
        payout_pix=str(data.get("payout_pix") or data.get("pix") or ""),
        notes=str(data.get("notes") or ""),
    )
    if err:
        return _json_error(err, 400)
    link = referrals.partner_signup_link(str(partner.get("code") or ""))
    return _json_ok({"partner": partner, "signup_link": link})


@app.get("/api/v1/admin/referrals/report.csv")
def admin_referral_report_csv():
    ok, err_resp = _require_referral_admin()
    if not ok:
        return err_resp
    from datetime import datetime, timezone

    from flask import Response

    from ego_api import referrals

    month = str(request.args.get("month") or "").strip()
    if not month:
        month = datetime.now(timezone.utc).strftime("%Y-%m")
    csv_text, err = referrals.commissions_report_csv(month)
    if err:
        return _json_error(err, 400)
    return Response(
        csv_text,
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="ego-indicacoes-{month}.csv"'
        },
    )


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
