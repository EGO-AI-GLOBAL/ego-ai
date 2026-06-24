#!/usr/bin/env python3
"""Verificação automática de blindagem — correr antes de deploy/build."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(script: str) -> int:
    print(f"\n>>> python scripts/{script}\n")
    return subprocess.call([sys.executable, str(ROOT / "scripts" / script)], cwd=str(ROOT))


def _code_checks() -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []

    plans = (ROOT / "ego_api" / "plans.py").read_text(encoding="utf-8")
    checks.append(
        (
            "Bypass EGO_TEST_TOTAL bloqueado em produção",
            "is_production_env()" in plans and "_test_total_emails" in plans,
            "plans.py deve ignorar test emails em produção",
        )
    )

    config = (ROOT / "ego_api" / "config.py").read_text(encoding="utf-8")
    checks.append(
        (
            "EGO_BETA_SEM_LIMITE bloqueado em produção",
            "is_production_env()" in config and "beta_unlimited" in config,
            "config.py deve ignorar beta unlimited em produção",
        )
    )

    checks.append(
        (
            "Guard Play Integrity existe",
            (ROOT / "ego_api" / "integrity_guard.py").is_file(),
            "Criar ego_api/integrity_guard.py",
        )
    )

    flask = (ROOT / "flask_api.py").read_text(encoding="utf-8")
    checks.append(
        (
            "Rotas caras verificam integridade",
            "evaluate_request_integrity" in flask and "/api/v1/integrity/status" in flask,
            "Ligar integrity_guard em chat/tts/night-dump",
        )
    )

    client = (ROOT / "app" / "src" / "api" / "client.ts").read_text(encoding="utf-8")
    checks.append(
        (
            "App envia X-Play-Integrity",
            "getPlayIntegrityToken" in client and "X-Play-Integrity" in client,
            "client.ts deve enviar token em rotas caras",
        )
    )

    checks.append(
        (
            "SQL hardening RLS existe",
            (ROOT / "supabase" / "security_rls_hardening.sql").is_file(),
            "Criar supabase/security_rls_hardening.sql",
        )
    )

    return checks


def main() -> int:
    print("EGO-AI — Verificação de segurança automática\n")

    code_fail = 0
    for title, ok, fix in _code_checks():
        mark = "OK" if ok else "FALTA"
        print(f"- {mark:5} | {title}")
        if not ok:
            print(f"         -> {fix}")
            code_fail += 1

    rc_audit = _run("security_prelaunch_audit.py")
    rc_reg = _run("regression_guard.py")
    rc_smoke = _run("smoke_test_api.py")

    print("\n=== Resumo ===")
    print(f"  Checks código: {len(_code_checks()) - code_fail}/{len(_code_checks())}")
    print(f"  security_prelaunch_audit: {'OK' if rc_audit == 0 else 'FALHOU'}")
    print(f"  regression_guard:         {'OK' if rc_reg == 0 else 'FALHOU'}")
    print(f"  smoke_test_api:           {'OK' if rc_smoke == 0 else 'FALHOU'}")
    print("\n  Manual: executar supabase/security_rls_hardening.sql no Supabase")
    print("  Manual: colar RAILWAY-SEGURANCA-PRODUCAO.env.txt no Railway")

    if code_fail or rc_audit or rc_reg or rc_smoke:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
