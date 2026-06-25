#!/usr/bin/env python3
"""Envia relatório diário de cadastros (local ou após deploy)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Relatório diário EGO-AI")
    parser.add_argument("--dry-run", action="store_true", help="Só mostra números, não envia e-mail")
    parser.add_argument("--days", type=int, default=14, help="Dias no histórico (default 14)")
    args = parser.parse_args()

    from ego_api.daily_stats_report import process_daily_stats_report

    result = process_daily_stats_report(history_days=args.days, dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    if result.get("error") and not result.get("ok"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
