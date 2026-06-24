#!/usr/bin/env python3
"""Checklist automático mínimo de segurança pré-lançamento."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _ok(v: bool) -> str:
    return "OK" if v else "FALTA"


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    checks.append(
        (
            "Checklist de segurança existe",
            (ROOT / "SECURITY_PRELAUNCH_CHECKLIST.md").is_file(),
            "Criar SECURITY_PRELAUNCH_CHECKLIST.md",
        )
    )
    checks.append(
        (
            "Auditoria RLS SQL existe",
            (ROOT / "supabase" / "security_rls_audit.sql").is_file(),
            "Criar supabase/security_rls_audit.sql",
        )
    )
    checks.append(
        (
            ".env.example sem links Stripe reais",
            "buy.stripe.com/" not in (ROOT / ".env.example").read_text(encoding="utf-8"),
            "Substituir por placeholders antes de publicar",
        )
    )
    checks.append(
        (
            "CORS não está com origem '*' no Flask",
            'origins": "*"' not in (ROOT / "flask_api.py").read_text(encoding="utf-8"),
            "Fechar CORS por allowlist",
        )
    )
    checks.append(
        (
            "Rate limit configurado no Flask",
            "def rate_limit(" in (ROOT / "flask_api.py").read_text(encoding="utf-8"),
            "Adicionar rate limit nas rotas críticas",
        )
    )
    webhook_src = (ROOT / "ego_api" / "stripe_webhook_handler.py").read_text(encoding="utf-8")
    checks.append(
        (
            "Webhook exige service role key",
            "SUPABASE_SERVICE_ROLE_KEY" in webhook_src
            and "create_service_client" in webhook_src
            and "SUPABASE_KEY" not in webhook_src.replace("SUPABASE_SERVICE_ROLE_KEY", ""),
            "Webhook deve usar create_service_client (service role only)",
        )
    )

    checks.append(
        (
            "Módulo Play Integrity no backend",
            (ROOT / "ego_api" / "play_integrity.py").is_file(),
            "Criar ego_api/play_integrity.py",
        )
    )
    checks.append(
        (
            "Guia Play Integrity existe",
            (ROOT / "PLAY_INTEGRITY_SETUP.md").is_file(),
            "Criar PLAY_INTEGRITY_SETUP.md",
        )
    )

    print("EGO-AI — Security Prelaunch Audit\n")
    missing = 0
    for title, passed, fix in checks:
        if not passed:
            missing += 1
        print(f"- {_ok(passed):5} | {title}")
        if not passed:
            print(f"         -> {fix}")

    print("\nResumo:")
    print(f"  OK: {len(checks) - missing}/{len(checks)}")
    if missing:
        print(f"  Pendências: {missing}")
        return 1
    print("  Projeto pronto para checklist final de release.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

