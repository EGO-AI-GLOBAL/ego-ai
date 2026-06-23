#!/usr/bin/env python3
"""Verifica variáveis essenciais no .env da raiz e no app/.env."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
except ImportError:
    print("Instale python-dotenv ou use pip install -r requirements.txt")
    sys.exit(1)

load_dotenv(ROOT / ".env", override=False)
load_dotenv(ROOT / "app" / ".env", override=False)

import os


def ok(name: str, *, app_only: bool = False) -> bool:
    if app_only:
        path = ROOT / "app" / ".env"
        if not path.is_file():
            return False
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            if line.strip().startswith(f"{name}="):
                val = line.split("=", 1)[-1].strip()
                return bool(val) and "SUA_CHAVE" not in val and "sk-proj-COLE" not in val
        return False
    val = (os.getenv(name) or "").strip()
    return bool(val)


def main() -> int:
    print("=== .env raiz (Flask / API) ===\n")
    root_required = [
        ("SUPABASE_URL", False),
        ("SUPABASE_KEY", False),
        ("GOOGLE_API_KEY", False),
        ("OPENAI_API_KEY", False),
        ("EGO_TEST_TOTAL_EMAILS", False),
    ]
    root_optional = [
        "EGO_OPENAI_REALTIME",
        "EGO_REALTIME_WEBRTC",
    ]
    errors = 0
    for name, _ in root_required:
        status = "OK" if ok(name) else "FALTA"
        if status == "FALTA":
            errors += 1
        print(f"  [{status}] {name}")
    for name in root_optional:
        print(f"  [{'OK' if ok(name) else 'opcional'}] {name}")

    print("\n=== app/.env (Expo / telemóvel / browser) ===\n")
    for name in ("EXPO_PUBLIC_API_URL", "EXPO_PUBLIC_ALLOW_HTTP", "EXPO_PUBLIC_FLASK_PROXY"):
        status = "OK" if ok(name, app_only=True) or ok(name) else "FALTA"
        if status == "FALTA":
            errors += 1
        print(f"  [{status}] {name}")

    print()
    if errors:
        print(f"Corrija {errors} item(ns) antes de testar.")
        print("Guias: CONFIGURACAO.md | Modelos: .env.example e app/.env.example")
        return 1
    print("Tudo essencial presente.")
    print("Iniciar: scripts\\dev-local.ps1  ou  COMO_LANCAR.md (Fase 1)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
