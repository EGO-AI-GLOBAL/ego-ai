#!/usr/bin/env python3
"""Lista últimos erros em error_reports (Supabase)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
        print("Defina SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY.", file=sys.stderr)
        return 1
    from ego_api.supabase_client import create_service_client

    client = create_service_client()
    if not client:
        print("Sem client Supabase.", file=sys.stderr)
        return 1
    limit = int(os.getenv("ERROR_LIST_LIMIT", "20"))
    r = (
        client.table("error_reports")
        .select("created_at, source, level, message, route, platform, app_version")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    rows = r.data or []
    if not rows:
        print("Nenhum erro registrado.")
        return 0
    for row in rows:
        print(
            f"{(row.get('created_at') or '')[:19]} | {row.get('source')} | "
            f"{row.get('level')} | {row.get('route') or '-'} | "
            f"{(row.get('message') or '')[:120]}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
