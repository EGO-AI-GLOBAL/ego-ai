"""Verifica dependências antes do deploy no Streamlit Cloud."""
from __future__ import annotations

import importlib
import sys

MODULES = (
    "streamlit",
    "dotenv",
    "google.generativeai",
    "PyPDF2",
    "supabase",
    "stripe",
    "langdetect",
    "tiktoken",
)


def main() -> int:
    failed: list[str] = []
    for name in MODULES:
        try:
            importlib.import_module(name)
            print("OK", name)
        except ImportError as e:
            failed.append(name)
            print("FAIL", name, "-", e)
    try:
        importlib.import_module("edge_tts")
        print("OK edge_tts (opcional)")
    except ImportError:
        print("SKIP edge_tts (opcional — voz no servidor desativada)")
    if failed:
        print("\nInstale: pip install -r requirements.txt")
        return 1
    print("\nPronto para deploy (app.py na raiz do repositório).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
