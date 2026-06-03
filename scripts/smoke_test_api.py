#!/usr/bin/env python3
"""Smoke test da API em produção (sem credenciais)."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = "https://ego-ai-production-a2c2.up.railway.app/api/v1"


def get(path: str) -> tuple[int, dict]:
    req = urllib.request.Request(f"{BASE}{path}", method="GET")
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            body = json.loads(resp.read().decode())
            return resp.status, body
    except urllib.error.HTTPError as e:
        raw = e.read().decode() if e.fp else "{}"
        try:
            body = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            body = {"raw": raw}
        return e.code, body


def post(path: str) -> int:
    req = urllib.request.Request(f"{BASE}{path}", method="POST", data=b"")
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code


def main() -> int:
    failed = 0
    code, health = get("/health")
    ok = health.get("ok") is True
    build = health.get("api_build", "?")
    print(f"GET /health -> {code} ok={ok} api_build={build}")
    if not ok:
        failed += 1
    if build != "2026-06-02-pdf-upload-fix":
        print(
            "  AVISO: Railway ainda sem o deploy novo "
            f"(esperado 2026-06-02-pdf-upload-fix, veio {build!r})."
        )
        failed += 1

    for path in ("/shared-calendars", "/persona"):
        c, _ = get(path)
        print(f"GET {path} -> {c} (esperado 401 sem token)")
        if c != 401:
            failed += 1

    c = post("/pdf/extract")
    print(f"POST /pdf/extract -> {c} (esperado 401 sem token)")
    if c != 401:
        failed += 1

    # Código local: helper de insert
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
    print("\nTudo OK para testar no telemóvel (agenda, PDF, Leo).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
