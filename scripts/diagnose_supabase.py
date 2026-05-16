# -*- coding: utf-8 -*-
"""Diagnostico local: Supabase + credenciais (nao imprime chaves completas)."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    print("FAIL dotenv: pip install python-dotenv")

url = (os.getenv("SUPABASE_URL") or "").strip()
key = (os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_PUBLISHABLE_KEY") or "").strip()

print("=== Ficheiros ===")
for p in (ROOT / ".env", ROOT / ".streamlit" / "secrets.toml"):
    print(f"  {p.name}: {'existe' if p.exists() else 'AUSENTE'}")

print("\n=== Variaveis (.env) ===")
print(f"  SUPABASE_URL: {url or '(vazio)'}")
print(f"  SUPABASE_KEY: {'(vazio)' if not key else key[:18] + '...' + key[-4:]}")
if key.startswith("sb_publishable_"):
    print("  tipo chave: publishable OK")
elif key.startswith("eyJ"):
    print("  tipo chave: anon JWT OK")
else:
    print("  tipo chave: desconhecido")

try:
    import supabase as sb_pkg

    print(f"\n=== Pacote supabase versao {getattr(sb_pkg, '__version__', '?')} ===")
except ImportError:
    print("\nFAIL: pip install -r requirements.txt")
    sys.exit(1)

ver = getattr(sb_pkg, "__version__", "0")
parts = [int(x) for x in ver.split(".")[:3] if x.isdigit()]
if key.startswith("sb_publishable_") and (parts < [2, 28, 0] if len(parts) >= 2 else True):
    print("  FAIL: publishable precisa supabase>=2.28 (voce tem", ver + ")")
    print("  FIX: pip install -U \"supabase>=2.28.0\"")
    sys.exit(4)

print("\n=== create_client ===")
try:
    from supabase import create_client

    client = create_client(url, key)
    print("  OK create_client")
except Exception as e:
    print(f"  FAIL create_client: {e}")
    if "Invalid API key" in str(e):
        print("  FIX: pip install -U \"supabase>=2.28.0\" para chave sb_publishable_")
    sys.exit(3)

print("\n=== Tabelas EGO-AI ===")
missing = []
for table in ("profiles", "chat_history", "user_personas", "agenda", "reminders"):
    try:
        client.table(table).select("*").limit(1).execute()
        print(f"  OK {table}")
    except Exception as e:
        print(f"  FAIL {table}: {str(e)[:100]}")
        missing.append(table)

if missing:
    print("\n=== ACAO NECESSARIA ===")
    print("  Execute no Supabase SQL Editor:")
    print("  supabase/bootstrap_ego_schema.sql")
    if "reminders" in missing or "agenda" in missing:
        print("  (bootstrap ja inclui agenda + reminders)")
    sys.exit(5)

print("\n=== SUCESSO ===")
print("  Credenciais e schema OK. Rode: streamlit run app.py")
