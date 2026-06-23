#!/usr/bin/env python3
"""Relatório de contas, login e uso (chat) — executar após lançamento.

Requer SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY no .env (não commitar a chave).
"""

from __future__ import annotations

import argparse
import os
import ssl
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass


def _client():
    url = (os.getenv("SUPABASE_URL") or "").strip()
    key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not url or not key:
        print(
            "Defina SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY no .env.",
            file=sys.stderr,
        )
        sys.exit(1)
    ssl._create_default_https_context = ssl._create_unverified_context
    from supabase import create_client

    return create_client(url, key)


def _count_rest(client, table: str, filters: str = "") -> int:
    import json
    import urllib.request

    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    path = f"/rest/v1/{table}?select=id{filters}"
    req = urllib.request.Request(
        url + path,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Prefer": "count=exact",
            "Range": "0-0",
        },
        method="HEAD",
    )
    try:
        with urllib.request.urlopen(req, context=ssl._create_unverified_context()) as r:
            cr = r.headers.get("Content-Range", "")
        if "/" in cr:
            return int(cr.split("/")[-1])
    except Exception:
        pass
    res = client.table(table).select("id", count="exact").limit(1).execute()
    return int(getattr(res, "count", None) or len(res.data or []))


def main() -> int:
    parser = argparse.ArgumentParser(description="Relatório de uso EGO-AI")
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Janela para 'ativo' (login e chat). Default: 7",
    )
    args = parser.parse_args()
    days = max(1, args.days)
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    client = _client()

    print(f"=== EGO-AI uso (últimos {days} dias) ===\n")

    profiles = (
        client.table("profiles")
        .select("id,email,created_at,last_login_at,plan_tier,last_platform,last_app_version")
        .order("last_login_at", desc=True)
        .execute()
    )
    rows = profiles.data or []
    print(f"Perfis (cadastro completo): {len(rows)}")

    login_active = [
        r
        for r in rows
        if r.get("last_login_at") and str(r["last_login_at"]) >= since[:10]
    ]
    print(f"Com login na janela:       {len(login_active)}")

    try:
        ch = (
            client.table("chat_history")
            .select("user_id")
            .eq("role", "user")
            .gte("created_at", since)
            .execute()
        )
        chat_users = {r.get("user_id") for r in (ch.data or []) if r.get("user_id")}
        print(f"Enviaram chat na janela:  {len(chat_users)}")
    except Exception as e:
        print(f"Chat (erro): {e}")

    print("\n--- Últimos perfis (login) ---")
    for r in rows[:25]:
        em = (r.get("email") or "").strip()
        login = (r.get("last_login_at") or "—")[:19]
        plan = r.get("plan_tier") or "?"
        plat = r.get("last_platform") or "—"
        ver = r.get("last_app_version") or "—"
        print(f"  {login} | {plan:10} | {plat:7} | {ver:8} | {em}")

    if rows:
        never = [r for r in rows if not r.get("last_login_at")]
        if never:
            print(f"\n--- Cadastraram mas nunca logaram ({len(never)}) ---")
            for r in never[:15]:
                print(f"  {(r.get('created_at') or '')[:19]} | {r.get('email')}")

    print(
        "\nDownloads totais: Play Console + App Store Connect (não vêm do Supabase)."
    )
    print("Doc: marketing/ANALYTICS-POS-LANCAMENTO.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
