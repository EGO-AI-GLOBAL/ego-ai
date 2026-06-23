#!/usr/bin/env python3
"""Gera CSV mensal de comissões de indicação (repasse a influenciadores)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ego_api.referrals import commissions_report_csv  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Relatório mensal de indicações EGO-AI")
    parser.add_argument(
        "--month",
        default="",
        help="Mês YYYY-MM (padrão: mês atual UTC)",
    )
    parser.add_argument(
        "--out",
        default="",
        help="Arquivo de saída .csv (padrão: stdout)",
    )
    args = parser.parse_args()
    month = (args.month or "").strip()
    if not month:
        from datetime import datetime, timezone

        month = datetime.now(timezone.utc).strftime("%Y-%m")

    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
        print(
            "Defina SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY no ambiente.",
            file=sys.stderr,
        )
        return 1

    csv_text, err = commissions_report_csv(month)
    if err:
        print(err, file=sys.stderr)
        return 1

    out_path = (args.out or "").strip()
    if out_path:
        Path(out_path).write_text(csv_text, encoding="utf-8")
        print(f"Gravado: {out_path}")
    else:
        print(csv_text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
