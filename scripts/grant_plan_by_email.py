#!/usr/bin/env python3
"""Concede plano Total a um e-mail em public.profiles (requer SUPABASE_SERVICE_ROLE_KEY)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore[misc, assignment]

if load_dotenv:
    load_dotenv(ROOT / ".env")

DEFAULT_EMAIL = "reidasacolapersonalizada@uol.com.br"
SQL_PATH = ROOT / "scripts" / "grant_plan_total.sql"


def main() -> int:
    email = (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_EMAIL).strip().lower()
    url = (os.getenv("SUPABASE_URL") or "").strip()
    service_key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()

    print(f"Email alvo: {email}")
    if not url:
        print("SUPABASE_URL ausente no .env")
        return 1

    if not service_key:
        print("SUPABASE_SERVICE_ROLE_KEY ausente no .env.")
        print("Use o SQL em scripts/grant_plan_total.sql no Supabase SQL Editor.")
        print(f"Ou defina EGO_TEST_TOTAL_EMAILS={email} no .env e reinicie a API.")
        return 1

    from supabase import create_client

    client = create_client(url, service_key)
    res = (
        client.table("profiles")
        .update({"plan_tier": "total", "is_pro": True})
        .eq("email", email)
        .execute()
    )
    rows = res.data or []
    if not rows:
        res2 = (
            client.table("profiles")
            .select("id,email,plan_tier,is_pro")
            .ilike("email", email)
            .execute()
        )
        found = res2.data or []
        if not found:
            print("Nenhum perfil encontrado com esse e-mail.")
            return 1
        print("Perfil existe mas update não retornou linhas. Rode grant_plan_total.sql manualmente.")
        print(found)
        return 1

    print("Plano Total aplicado:")
    for row in rows:
        print(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
