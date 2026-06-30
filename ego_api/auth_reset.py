"""Recuperação de senha — Brevo, redirect URL e página web (/auth/reset-password)."""

from __future__ import annotations

import html
import json
import logging
from typing import Any

from ego_api.config import read_env

_LOG = logging.getLogger("ego.auth_reset")


def public_api_base() -> str:
    """Origem HTTPS da API Flask (sem sufixo /auth/reset-password)."""
    base = read_env("EGO_PUBLIC_API_URL", "").strip().rstrip("/")
    if not base:
        return "https://ego-ai-production-a2c2.up.railway.app"
    if base.endswith("/auth"):
        return base[: -len("/auth")]
    return base


def password_reset_redirect_url() -> str:
    """URL que o Supabase abre após clicar no e-mail (tokens no #hash)."""
    custom = read_env("EGO_PASSWORD_RESET_REDIRECT_URL", "").strip().rstrip("/")
    if custom:
        return custom
    base = public_api_base()
    return f"{base}/auth/reset-password"


def service_role_configured() -> bool:
    return bool(read_env("SUPABASE_SERVICE_ROLE_KEY", "").strip())


def brevo_reset_available() -> bool:
    from ego_api.signup_emails import brevo_configured

    return brevo_configured() and service_role_configured()


def password_reset_emails_status() -> dict[str, Any]:
    from ego_api.signup_emails import brevo_configured

    brevo = brevo_configured()
    svc = service_role_configured()
    return {
        "via_brevo_api": bool(brevo and svc),
        "brevo_configured": brevo,
        "service_role": svc,
        "redirect_url": password_reset_redirect_url(),
    }


def _extract_action_link(link_res: Any) -> str:
    if isinstance(link_res, dict):
        props = link_res.get("properties") or link_res
        if isinstance(props, dict):
            return str(props.get("action_link") or link_res.get("action_link") or "").strip()
        return str(link_res.get("action_link") or "").strip()
    props = getattr(link_res, "properties", None)
    if props is not None:
        if isinstance(props, dict):
            return str(props.get("action_link") or "").strip()
        return str(getattr(props, "action_link", "") or "").strip()
    return str(getattr(link_res, "action_link", "") or "").strip()


def _password_reset_bodies(reset_link: str, email: str) -> tuple[str, str, str]:
    from ego_api.signup_emails import DEFAULT_FROM_NAME, SUPPORT_EMAIL

    subject = "Ego-IA — criar nova senha"
    text = f"""Olá!

Recebemos um pedido para redefinir a senha da sua conta Ego-IA ({email}).

Crie uma nova senha aqui (link válido por tempo limitado):
{reset_link}

Se não pediu isto, ignore este e-mail — a senha actual mantém-se.

Dúvida? {SUPPORT_EMAIL}

Equipe {DEFAULT_FROM_NAME}
"""
    safe_link = html.escape(reset_link)
    html_body = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="font-family:Segoe UI,Arial,sans-serif;line-height:1.55;color:#111;margin:0;padding:16px;">
  <div style="max-width:560px;">
    <p>Olá!</p>
    <p>Recebemos um pedido para redefinir a senha da sua conta <strong>Ego-IA</strong>.</p>
    <p><a href="{safe_link}" style="display:inline-block;padding:12px 18px;background:#0A122A;color:#fff;text-decoration:none;border-radius:8px;">Criar nova senha</a></p>
    <p style="font-size:0.9rem;color:#555;">Se o botão não abrir, copie este link:<br>{safe_link}</p>
    <p style="font-size:0.9rem;color:#555;">Se não pediu isto, ignore este e-mail.</p>
    <p>Equipe {html.escape(DEFAULT_FROM_NAME)} · {html.escape(SUPPORT_EMAIL)}</p>
  </div>
</body>
</html>"""
    return subject, text, html_body


def dispatch_password_reset_email(email: str, *, redirect_to: str = "") -> None:
    """Gera link recovery (service role) e envia via Brevo — remetente Ego-IA."""
    from ego_api.signup_emails import send_brevo_api_email
    from ego_api.supabase_client import create_service_client

    if not brevo_reset_available():
        raise RuntimeError("Reset via Brevo indisponível (BREVO_API_KEY ou service role).")

    admin = create_service_client()
    if not admin:
        raise RuntimeError("Supabase service role indisponível.")

    email_norm = (email or "").strip().lower()
    if not email_norm or "@" not in email_norm:
        raise ValueError("E-mail inválido.")

    target = (redirect_to or "").strip() or password_reset_redirect_url()

    try:
        link_res = admin.auth.admin.generate_link(
            {
                "type": "recovery",
                "email": email_norm,
                "options": {"redirect_to": target},
            }
        )
    except Exception as exc:  # noqa: BLE001
        err = str(exc).lower()
        if "user" in err and ("not found" in err or "not exist" in err or "invalid" in err):
            _LOG.info("password_reset skip unknown email domain=%s", email_norm.split("@")[-1])
            return
        raise

    action_link = _extract_action_link(link_res)
    if not action_link:
        raise RuntimeError("Link de recuperação não gerado pelo Supabase.")

    subject, text, html_body = _password_reset_bodies(action_link, email_norm)
    send_brevo_api_email(
        to_email=email_norm,
        subject=subject,
        text_body=text,
        html_body=html_body,
    )
    _LOG.info("password_reset sent via brevo email=%s", email_norm)


def render_reset_password_page(*, api_base: str = "") -> tuple[str, int, dict[str, str]]:
    _ = api_base  # legado: flask passa EGO_PUBLIC_API_URL — usar public_api_base()
    api = public_api_base()
    endpoint = f"{api}/api/v1/auth/reset-password"
    body = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="theme-color" content="#0A122A" />
  <title>Nova senha — EGO-AI</title>
  <style>
    body {{
      margin: 0; font-family: system-ui, sans-serif; background: #0A122A; color: #e8eef8;
      min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px;
    }}
    .card {{
      max-width: 400px; width: 100%; background: #121c2c; border: 1px solid #2a3a5c;
      border-radius: 16px; padding: 24px 20px;
    }}
    h1 {{ margin: 0 0 8px; font-size: 1.35rem; text-align: center; }}
    p {{ margin: 0 0 14px; line-height: 1.5; color: #a8b4cc; font-size: 0.92rem; text-align: center; }}
    label {{ display: block; font-size: 0.82rem; color: #a8b4cc; margin: 12px 0 6px; }}
    .pw-field {{
      display: flex; align-items: center; width: 100%; box-sizing: border-box;
      border-radius: 10px; border: 1px solid #2a3a5c; background: #0A122A;
    }}
    .pw-input {{
      flex: 1; min-width: 0; border: none; background: transparent;
      padding: 12px 8px 12px 14px; color: #e8eef8; font-size: 1rem; outline: none;
    }}
    .pw-toggle {{
      flex-shrink: 0; width: 44px; height: 44px; border: none; background: transparent;
      cursor: pointer; color: #a8b4cc; display: flex; align-items: center; justify-content: center;
      padding: 0; margin-right: 2px;
    }}
    .pw-toggle.visible {{ color: #22D3EE; }}
    .pw-toggle svg {{ width: 22px; height: 22px; fill: none; stroke: currentColor; stroke-width: 1.8; }}
    .btn {{
      width: 100%; margin-top: 18px; padding: 14px; border: none; border-radius: 12px;
      background: #22D3EE; color: #0A122A; font-weight: 700; font-size: 1rem; cursor: pointer;
    }}
    .btn:disabled {{ opacity: 0.6; cursor: wait; }}
    .err {{ color: #f87171; font-size: 0.88rem; margin-top: 12px; text-align: center; }}
    .ok {{ color: #4ade80; font-size: 0.92rem; margin-top: 12px; text-align: center; line-height: 1.45; }}
    .link {{
      display: block; text-align: center; margin-top: 16px; color: #22D3EE;
      text-decoration: none; font-weight: 600;
    }}
    #loading {{ text-align: center; color: #a8b4cc; padding: 24px 0; }}
  </style>
</head>
<body>
  <div class="card">
    <div id="panel-wait">
      <h1>Nova senha</h1>
      <p id="loading">A validar o link…</p>
    </div>
    <div id="panel-form" style="display:none">
      <h1>Nova senha</h1>
      <p>Escolha uma senha com pelo menos 6 caracteres.</p>
      <form id="form">
        <label for="pw">Nova senha</label>
        <div class="pw-field">
          <input id="pw" class="pw-input" type="password" autocomplete="new-password" minlength="6" required />
          <button type="button" class="pw-toggle" id="pw-toggle" aria-label="Mostrar senha" title="Mostrar senha">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z"/><circle cx="12" cy="12" r="3"/></svg>
          </button>
        </div>
        <label for="pw2">Confirmar senha</label>
        <div class="pw-field">
          <input id="pw2" class="pw-input" type="password" autocomplete="new-password" minlength="6" required />
          <button type="button" class="pw-toggle" id="pw2-toggle" aria-label="Mostrar senha" title="Mostrar senha">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z"/><circle cx="12" cy="12" r="3"/></svg>
          </button>
        </div>
        <button class="btn" type="submit" id="btn">Guardar senha</button>
      </form>
      <p class="err" id="err" style="display:none"></p>
    </div>
    <div id="panel-done" style="display:none">
      <h1>Senha guardada</h1>
      <p class="ok" id="done-msg">A abrir o EGO-AI…</p>
      <p class="ok" id="done-email" style="display:none"></p>
      <a class="link" id="open-app" href="egoai://login">Abrir EGO-AI</a>
      <p class="err" id="done-fallback" style="display:none;font-size:0.85rem;margin-top:14px">
        Se o app não abrir sozinho, toque em «Abrir EGO-AI» ou entre manualmente com o e-mail acima e a senha nova.
      </p>
    </div>
    <div id="panel-bad" style="display:none">
      <h1>Link inválido</h1>
      <p class="err" id="bad-msg">Peça um novo e-mail em Esqueci a senha no app.</p>
      <a class="link" href="egoai://login">Voltar ao login</a>
    </div>
  </div>
  <script>
    (function () {{
      var endpoint = {json.dumps(endpoint)};
      var tokens = {{ access: "", refresh: "" }};

      function parseTokens() {{
        var h = (window.location.hash || "").replace(/^#/, "");
        var q = window.location.search.replace(/^\\?/, "");
        function ingest(chunk) {{
          if (!chunk) return;
          chunk.split("&").forEach(function (pair) {{
            var i = pair.indexOf("=");
            if (i < 1) return;
            var k = decodeURIComponent(pair.slice(0, i));
            var v = decodeURIComponent(pair.slice(i + 1));
            if (k === "access_token") tokens.access = v;
            if (k === "refresh_token") tokens.refresh = v;
          }});
        }}
        ingest(h);
        ingest(q);
      }}

      function show(id) {{
        ["panel-wait", "panel-form", "panel-done", "panel-bad"].forEach(function (pid) {{
          var el = document.getElementById(pid);
          if (el) el.style.display = pid === id ? "block" : "none";
        }});
      }}

      function bindPasswordToggle(btnId, inputId) {{
        var btn = document.getElementById(btnId);
        var input = document.getElementById(inputId);
        if (!btn || !input) return;
        btn.addEventListener("click", function () {{
          var reveal = input.type === "password";
          input.type = reveal ? "text" : "password";
          btn.classList.toggle("visible", reveal);
          btn.setAttribute("aria-label", reveal ? "Ocultar senha" : "Mostrar senha");
          btn.setAttribute("title", reveal ? "Ocultar senha" : "Mostrar senha");
        }});
      }}

      bindPasswordToggle("pw-toggle", "pw");
      bindPasswordToggle("pw2-toggle", "pw2");

      function sessionDeepLink(sess) {{
        var s = sess || {{}};
        var u = s.user || {{}};
        var parts = [
          "access_token=" + encodeURIComponent(s.access_token || ""),
          "refresh_token=" + encodeURIComponent(s.refresh_token || ""),
          "type=login"
        ];
        if (u.email) parts.push("email=" + encodeURIComponent(u.email));
        if (u.id) parts.push("user_id=" + encodeURIComponent(u.id));
        return "egoai://session#" + parts.join("&");
      }}

      function openAppAfterReset(sess) {{
        var deep = sessionDeepLink(sess);
        var openLink = document.getElementById("open-app");
        var doneMsg = document.getElementById("done-msg");
        var doneEmail = document.getElementById("done-email");
        var fallback = document.getElementById("done-fallback");
        var email = (sess && sess.user && sess.user.email) ? sess.user.email : "";
        if (openLink) openLink.setAttribute("href", deep);
        if (doneEmail && email) {{
          doneEmail.textContent = "Conta: " + email;
          doneEmail.style.display = "block";
        }}
        if (fallback) fallback.style.display = "block";
        show("panel-done");
        if (doneMsg) doneMsg.textContent = "Senha guardada. A abrir o EGO-AI…";
        window.setTimeout(function () {{
          window.location.href = deep;
        }}, 500);
      }}

      parseTokens();
      if (tokens.access && tokens.refresh) {{
        show("panel-form");
      }} else {{
        show("panel-bad");
      }}

      var form = document.getElementById("form");
      if (form) {{
        form.addEventListener("submit", function (ev) {{
          ev.preventDefault();
          var pw = document.getElementById("pw").value;
          var pw2 = document.getElementById("pw2").value;
          var err = document.getElementById("err");
          var btn = document.getElementById("btn");
          if (pw.length < 6) {{
            err.textContent = "A senha deve ter pelo menos 6 caracteres.";
            err.style.display = "block";
            return;
          }}
          if (pw !== pw2) {{
            err.textContent = "As senhas não coincidem.";
            err.style.display = "block";
            return;
          }}
          err.style.display = "none";
          btn.disabled = true;
          btn.textContent = "A guardar…";
          fetch(endpoint, {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{
              access_token: tokens.access,
              refresh_token: tokens.refresh,
              password: pw
            }})
          }})
            .then(function (r) {{ return r.json().then(function (j) {{ return {{ ok: r.ok, j: j }}; }}); }})
            .then(function ({{ ok, j }}) {{
              if (ok && (j.ok || j.session)) {{
                var sess = j.session || null;
                if (sess && sess.access_token) {{
                  openAppAfterReset(sess);
                  return;
                }}
                show("panel-done");
                return;
              }}
              var msg = (j.error || j.message || "Não foi possível alterar a senha.").toString();
              err.textContent = msg;
              err.style.display = "block";
              btn.disabled = false;
              btn.textContent = "Guardar senha";
            }})
            .catch(function () {{
              err.textContent = "Erro de rede. Tente de novo.";
              err.style.display = "block";
              btn.disabled = false;
              btn.textContent = "Guardar senha";
            }});
        }});
      }}
    }})();
  </script>
</body>
</html>"""
    return body, 200, {"Content-Type": "text/html; charset=utf-8"}
