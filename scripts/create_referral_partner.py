#!/usr/bin/env python3
"""Cadastra parceiro/influencer (cupom de indicação)."""

from __future__ import annotations

import argparse
import os
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
    parser = argparse.ArgumentParser(description="Criar parceiro EGO-AI (cupom)")
    parser.add_argument("--code", required=True, help="Ex.: MARIA10")
    parser.add_argument("--name", required=True, help="Nome exibição")
    parser.add_argument("--email", default="", help="E-mail contato")
    parser.add_argument("--pix", default="", help="PIX repasse")
    parser.add_argument("--notes", default="", help="Observações")
    args = parser.parse_args()

    from ego_api.referrals import create_partner, partner_signup_link

    row, err = create_partner(
        code=args.code,
        display_name=args.name,
        contact_email=args.email,
        payout_pix=args.pix,
        notes=args.notes,
    )
    if err:
        print(f"ERRO: {err}", file=sys.stderr)
        return 1
    code = str((row or {}).get("code") or args.code).upper()
    link = partner_signup_link(code)
    print("OK — parceiro criado")
    print(f"  Código:  {code}")
    print(f"  Nome:    {row.get('display_name')}")
    print(f"  Link:    {link}")
    print(f"  PIX:     {args.pix or '(não informado)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
