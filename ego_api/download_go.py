"""Página /go — um link para Android, iPhone ou app já instalado."""

from __future__ import annotations

import html
import re
from urllib.parse import urlencode

from ego_api.config import play_store_update_url, testflight_update_url

_REF_RE = re.compile(r"^[A-Za-z0-9_-]{2,32}$")
_NEXT_ALLOWED = frozenset({"agenda", "signup", "chat"})


def json_escape(value: str) -> str:
    import json

    return json.dumps(value)


def _clean_ref(raw: str) -> str:
    code = (raw or "").strip().upper()
    if not code or not _REF_RE.match(code):
        return ""
    return code


def _clean_next(raw: str) -> str:
    step = (raw or "").strip().lower()
    return step if step in _NEXT_ALLOWED else ""


def public_go_base() -> str:
    from ego_api.config import read_env

    custom = read_env("EGO_SMART_DOWNLOAD_URL", "").strip().rstrip("/")
    if custom:
        return custom
    api = read_env("EGO_PUBLIC_API_URL", "").strip().rstrip("/")
    if api:
        return api
    return "https://ego-ai-production-a2c2.up.railway.app"


def public_go_url(*, ref: str = "", next_step: str = "", utm_campaign: str = "share") -> str:
    return build_go_url(
        public_go_base(), ref=ref, next_step=next_step, utm_campaign=utm_campaign
    )


def build_go_url(
    base: str,
    *,
    ref: str = "",
    next_step: str = "",
    utm_campaign: str = "share",
) -> str:
    root = (base or "").rstrip("/")
    if not root:
        root = "https://ego-ai-production-a2c2.up.railway.app"
    params: dict[str, str] = {"utm_source": "egoai", "utm_medium": "go", "utm_campaign": utm_campaign}
    ref_code = _clean_ref(ref)
    nxt = _clean_next(next_step)
    if ref_code:
        params["ref"] = ref_code
    if nxt:
        params["next"] = nxt
    return f"{root}/go?{urlencode(params)}"


def _app_deep_link(ref: str, next_step: str) -> str:
    q: dict[str, str] = {}
    if ref:
        q["ref"] = ref
    if next_step:
        q["next"] = next_step
    path = "signup"
    if q:
        return "egoai://" + path + "?" + urlencode(q)
    return "egoai://" + path


def render_go_page(
    *,
    ref: str = "",
    next_step: str = "",
    user_agent: str = "",
    force_format: str = "",
) -> tuple[str, int, dict[str, str]]:
    """Devolve (body, status, headers)."""
    ref_code = _clean_ref(ref)
    nxt = _clean_next(next_step)
    play = play_store_update_url()
    ios = testflight_update_url()
    app_link = _app_deep_link(ref_code, nxt)

    ua = (user_agent or "").lower()
    is_ios = "iphone" in ua or "ipad" in ua or "ipod" in ua
    is_android = "android" in ua

    if force_format == "redirect":
        target = ios if is_ios else play if is_android else play
        return "", 302, {"Location": target}

    store_url = ios if is_ios else play if is_android else play
    store_label = "TestFlight" if is_ios else "Google Play" if is_android else "loja"

    title = "Baixar EGO-AI"
    subtitle = "Grátis · bem-estar · cadastro em 1 minuto"
    if nxt == "agenda":
        subtitle = "Baixe, cadastre-se e aceite o convite na Agenda"

    ref_line = ""
    if ref_code:
        ref_line = f'<p class="hint">Código de indicação: <strong>{html.escape(ref_code)}</strong></p>'

    body = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="theme-color" content="#0A122A" />
  <title>{html.escape(title)}</title>
  <style>
    body {{
      margin: 0; font-family: system-ui, sans-serif; background: #0A122A; color: #e8eef8;
      min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 24px;
    }}
    .card {{
      max-width: 420px; width: 100%; background: #121c2c; border: 1px solid #2a3a5c;
      border-radius: 16px; padding: 28px 22px; text-align: center;
    }}
    h1 {{ margin: 0 0 8px; font-size: 1.45rem; }}
    p {{ margin: 0 0 14px; line-height: 1.5; color: #a8b4cc; font-size: 0.95rem; }}
    .btn {{
      display: block; width: 100%; box-sizing: border-box; margin: 10px 0; padding: 14px 16px;
      border-radius: 12px; text-decoration: none; font-weight: 700; font-size: 1rem;
    }}
    .primary {{ background: #22D3EE; color: #0A122A; }}
    .secondary {{ background: transparent; color: #22D3EE; border: 1.5px solid #22D3EE; }}
    .hint {{ font-size: 0.82rem; margin-top: 16px; }}
    .spin {{ margin: 18px auto 8px; width: 28px; height: 28px; border: 3px solid #2a3a5c;
      border-top-color: #22D3EE; border-radius: 50%; animation: r 0.8s linear infinite; }}
    @keyframes r {{ to {{ transform: rotate(360deg); }} }}
  </style>
</head>
<body>
  <div class="card">
    <h1>{html.escape(title)}</h1>
    <p>{html.escape(subtitle)}</p>
    {ref_line}
    <div class="spin" id="spin"></div>
    <p id="status">A abrir o EGO-AI…</p>
    <a class="btn primary" id="btn-store" href="{html.escape(store_url, quote=True)}">
      Baixar no {html.escape(store_label)}
    </a>
    <a class="btn secondary" id="btn-app" href="{html.escape(app_link, quote=True)}">
      Já tenho o app — criar conta
    </a>
    <p class="hint">Android: Google Play (teste) · iPhone: TestFlight</p>
  </div>
  <script>
    (function () {{
      var appUrl = {json_escape(app_link)};
      var storeUrl = {json_escape(store_url)};
      var isMobile = {str(is_ios or is_android).lower()};
      var status = document.getElementById("status");
      var spin = document.getElementById("spin");

      function goStore() {{
        if (status) status.textContent = "A abrir a loja para baixar…";
        window.location.replace(storeUrl);
      }}

      if (isMobile) {{
        var started = Date.now();
        window.location.href = appUrl;
        setTimeout(function () {{
          if (Date.now() - started < 2800) goStore();
        }}, 1600);
        setTimeout(function () {{
          if (spin) spin.style.display = "none";
          if (status) status.textContent = "Não abriu? Toque em Baixar acima.";
        }}, 2200);
      }} else {{
        if (spin) spin.style.display = "none";
        if (status) status.textContent = "Escolha Android ou iPhone abaixo.";
      }}
    }})();
  </script>
</body>
</html>"""
    return body, 200, {"Content-Type": "text/html; charset=utf-8"}
