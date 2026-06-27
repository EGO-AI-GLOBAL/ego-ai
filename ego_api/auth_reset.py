"""Recuperação de senha — redirect URL e página web (/auth/reset-password)."""

from __future__ import annotations

import html
import json

from ego_api.config import read_env


def password_reset_redirect_url() -> str:
    """URL que o Supabase abre após clicar no e-mail (tokens no #hash)."""
    custom = read_env("EGO_PASSWORD_RESET_REDIRECT_URL", "").strip().rstrip("/")
    if custom:
        return custom
    base = read_env("EGO_PUBLIC_API_URL", "").strip().rstrip("/")
    if not base:
        base = "https://ego-ai-production-a2c2.up.railway.app"
    return f"{base}/auth/reset-password"


def render_reset_password_page(*, api_base: str) -> tuple[str, int, dict[str, str]]:
    api = (api_base or "").rstrip("/") or password_reset_redirect_url().rsplit("/", 1)[0]
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
    input {{
      width: 100%; box-sizing: border-box; padding: 12px 14px; border-radius: 10px;
      border: 1px solid #2a3a5c; background: #0A122A; color: #e8eef8; font-size: 1rem;
    }}
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
        <input id="pw" type="password" autocomplete="new-password" minlength="6" required />
        <label for="pw2">Confirmar senha</label>
        <input id="pw2" type="password" autocomplete="new-password" minlength="6" required />
        <button class="btn" type="submit" id="btn">Guardar senha</button>
      </form>
      <p class="err" id="err" style="display:none"></p>
    </div>
    <div id="panel-done" style="display:none">
      <h1>Senha alterada</h1>
      <p class="ok">Pode entrar no app com a nova senha.</p>
      <a class="link" href="egoai://login">Abrir EGO-AI</a>
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
