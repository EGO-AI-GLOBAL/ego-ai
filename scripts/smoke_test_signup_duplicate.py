#!/usr/bin/env python3
"""Smoke test: cadastro exige telefone e bloqueia e-mail/telefone duplicados."""
from __future__ import annotations

import json
import ssl
import sys
import uuid
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BASE = "https://ego-ai-production-a2c2.up.railway.app/api/v1"


def _urlopen(req: urllib.request.Request, timeout: int = 30):
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


def post_signup(payload: dict) -> tuple[int | None, dict]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}/auth/signup",
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with _urlopen(req) as resp:
            raw = resp.read().decode()
            body = json.loads(raw) if raw else {}
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


def _err(body: dict) -> str:
    return str(body.get("error") or body.get("message") or "").strip()


def main() -> int:
    failed = 0

    code, body = post_signup(
        {
            "email": "smoke-no-phone@example.com",
            "password": "smoke123456",
            "full_name": "Smoke Test",
            "phone": "",
        }
    )
    if code is None:
        print("POST /auth/signup (sem telefone) -> rede indisponivel")
        print("\nTeste ignorado (sem rede). Codigo local OK se regression_guard passou.")
        return 0
    err = _err(body).lower()
    print(f"POST /auth/signup sem telefone -> {code} error={_err(body)!r}")
    if code != 400 or "telefone" not in err:
        failed += 1

    tag = uuid.uuid4().hex[:10]
    email = f"ego.smoke.{tag}@example.com"
    suffix = f"{uuid.uuid4().int % 100_000_000:08d}"
    phone = f"(11) 9{suffix[:4]}-{suffix[4:]}"
    password = f"Smoke{tag}1!"
    payload = {
        "email": email,
        "password": password,
        "full_name": "Smoke Dup",
        "phone": phone,
    }

    code1, body1 = post_signup(payload)
    err1 = _err(body1).lower()
    print(f"POST /auth/signup 1a conta -> {code1} ok={body1.get('ok')}")
    first_ok = code1 in (200, 201) or body1.get("ok") is True
    if not first_ok and "cadastrado" not in err1:
        print(f"  AVISO  1o cadastro inesperado: {_err(body1)!r}")
        failed += 1
    elif not first_ok and "cadastrado" in err1:
        print("  INFO  conta smoke ja existia — testes de duplicado seguem validos")

    code2, body2 = post_signup(payload)
    err2 = _err(body2).lower()
    print(f"POST /auth/signup repetido (email) -> {code2} error={_err(body2)!r}")
    if code2 != 400 or ("cadastrado" not in err2 and "e-mail" not in err2 and "email" not in err2):
        failed += 1

    email2 = f"ego.smoke.other.{tag}@example.com"
    code3, body3 = post_signup({**payload, "email": email2})
    err3 = _err(body3).lower()
    print(f"POST /auth/signup mesmo telefone -> {code3} error={_err(body3)!r}")
    if code3 != 400 or "telefone" not in err3:
        failed += 1

    if failed:
        print(f"\n{failed} verificacao(oes) de cadastro falharam.")
        print("Confirme SUPABASE_SERVICE_ROLE_KEY no Railway e indice profiles_phone_unique.")
        return 1
    print("\nCadastro duplicado: OK (telefone obrigatorio + bloqueio email/telefone).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
