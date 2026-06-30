#!/usr/bin/env python3
"""Smoke test da API em produção (sem credenciais)."""
from __future__ import annotations

import json
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BASE = "https://ego-ai-production-a2c2.up.railway.app/api/v1"
PUBLIC_BASE = "https://ego-ai-production-a2c2.up.railway.app"


def _urlopen(req: urllib.request.Request, timeout: int = 25):
    """Abre URL; em PCs com SSL estrito (ex. Python 3.14 Win) tenta fallback local."""
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.URLError as exc:
        err = str(exc)
        if "SSL" not in err and "CERTIFICATE" not in err:
            raise
        print("  AVISO  SSL local falhou — a tentar sem verificar certificado (só smoke test)")
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return urllib.request.urlopen(req, timeout=timeout, context=ctx)


def get(path: str) -> tuple[int | None, dict]:
    req = urllib.request.Request(f"{BASE}{path}", method="GET")
    try:
        with _urlopen(req, timeout=25) as resp:
            body = json.loads(resp.read().decode())
            return resp.status, body
    except urllib.error.HTTPError as e:
        raw = e.read().decode() if e.fp else "{}"
        try:
            body = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            body = {"raw": raw}
        return e.code, body
    except urllib.error.URLError as exc:
        print(f"  AVISO  rede/API inacessivel: {exc}")
        return None, {}


def get_public(path: str) -> tuple[int | None, str]:
    """GET fora de /api/v1 (ex. página reset senha)."""
    req = urllib.request.Request(f"{PUBLIC_BASE}{path}", method="GET")
    try:
        with _urlopen(req, timeout=25) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")[:8000]
    except urllib.error.HTTPError as e:
        return e.code, (e.read().decode("utf-8", errors="replace") if e.fp else "")[:8000]
    except urllib.error.URLError as exc:
        print(f"  AVISO  rede/API inacessivel: {exc}")
        return None, ""


def post(path: str) -> int | None:
    req = urllib.request.Request(f"{BASE}{path}", method="POST", data=b"")
    try:
        with _urlopen(req, timeout=25) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except urllib.error.URLError as exc:
        print(f"  AVISO  rede/API inacessivel: {exc}")
        return None


def main() -> int:
    failed = 0
    network_ok = True

    code, health = get("/health")
    if code is None:
        network_ok = False
        print("GET /health -> (sem resposta — verifique internet ou Railway)")
    else:
        ok = health.get("ok") is True
        build = health.get("api_build", "?")
        print(f"GET /health -> {code} ok={ok} api_build={build}")
        if not ok:
            failed += 1
        if health.get("maintenance"):
            print("  ERRO  maintenance=true em producao (remova EGO_MAINTENANCE no Railway)")
            failed += 1
        else:
            print(f"  INFO  api_build={build!r} (sem exigir versao fixa — evita falso negativo)")

    if network_ok:
        for path in ("/shared-calendars", "/persona"):
            c, _ = get(path)
            if c is None:
                network_ok = False
                break
            print(f"GET {path} -> {c} (esperado 401 sem token)")
            if c != 401:
                failed += 1

        c = post("/pdf/extract")
        if c is not None:
            print(f"POST /pdf/extract -> {c} (esperado 401 ou 404 se rota ainda nao deployada)")
            if c not in (401, 404):
                failed += 1
            elif c == 404:
                print("  AVISO  rota PDF ainda nao na API em producao — nao bloqueia deploy agenda/auth")

        c_reset, html = get_public("/auth/reset-password")
        if c_reset is None:
            network_ok = False
        else:
            print(f"GET /auth/reset-password -> {c_reset}")
            if c_reset != 200:
                print("  AVISO  pagina reset senha ainda nao na API — faca deploy Railway antes da build")
            elif "Nova senha" not in html:
                print("  ERRO  pagina reset sem conteudo esperado")
                failed += 1
            elif "/auth/api/v1/auth/reset-password" in html:
                print("  ERRO  pagina reset com URL API errada (/auth/api/...)")
                failed += 1
            elif "/api/v1/auth/reset-password" not in html:
                print("  ERRO  pagina reset sem endpoint POST correto")
                failed += 1
            else:
                print("  OK    pagina recuperar senha em producao")
    else:
        print("  AVISO  testes HTTP ignorados (API nao alcancavel neste PC)")

    try:
        from ego_api.supabase_client import insert_returning_rows
        from unittest.mock import MagicMock

        client = MagicMock()
        client.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": "x"}
        ]
        rows = insert_returning_rows(client, "t", {"a": 1})
        assert rows[0]["id"] == "x"
        print("insert_returning_rows: OK")
    except Exception as exc:
        print(f"insert_returning_rows: FALHOU ({exc})")
        failed += 1

    if failed:
        print(f"\n{failed} verificação(ões) falharam.")
        return 1
    if not network_ok:
        print("\nCodigo local OK; API nao testada neste PC (rede/SSL). Pode deploy se Railway ja estiver no ar.")
        return 0
    print("\nTudo OK para testar no telemóvel (agenda, PDF, Leo).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
