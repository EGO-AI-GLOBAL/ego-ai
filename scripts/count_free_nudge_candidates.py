"""Contagem pontual: grátis Essential com telefone (sem enviar)."""
from __future__ import annotations

import re
import sys

from ego_api.plans import PLAN_ESSENTIAL, is_paid_plan, resolve_plan_tier
from ego_api.supabase_client import create_service_client


def norm_phone(raw: str) -> str | None:
    digits = re.sub(r"\D+", "", raw or "")
    if len(digits) < 10:
        return None
    if digits.startswith("55") and len(digits) >= 12:
        return digits
    return "55" + digits


def main() -> int:
    svc = create_service_client()
    if not svc:
        print("ERRO: sem service client")
        return 1
    rows = []
    start = 0
    page = 1000
    while True:
        res = (
            svc.table("profiles")
            .select("id,phone,is_pro,plan_tier,referral_bonus_until")
            .range(start, start + page - 1)
            .execute()
        )
        chunk = list(res.data or [])
        if not chunk:
            break
        rows.extend(chunk)
        if len(chunk) < page:
            break
        start += page

    free_phone = 0
    free_no_phone = 0
    paid = 0
    seen = set()
    for row in rows:
        if bool(row.get("is_pro")) or is_paid_plan(resolve_plan_tier(row)):
            paid += 1
            continue
        if resolve_plan_tier(row) != PLAN_ESSENTIAL:
            paid += 1
            continue
        phone = norm_phone(str(row.get("phone") or ""))
        if not phone or phone in seen:
            free_no_phone += 1
            continue
        seen.add(phone)
        free_phone += 1

    print(f"profiles_total={len(rows)}")
    print(f"free_essential_with_phone={free_phone}")
    print(f"free_essential_without_phone_or_dup={free_no_phone}")
    print(f"paid_or_bonus={paid}")
    print(f"ego_wa_number=5532999811376")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
