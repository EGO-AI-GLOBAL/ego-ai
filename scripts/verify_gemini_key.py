#!/usr/bin/env python3
"""Testa GOOGLE_API_KEY do .env (chat Gemini). Uso: python scripts/verify_gemini_key.py"""

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

from ego_api.config import GEMINI_MODEL_FLASH, gemini_api_key


def main() -> int:
    key = gemini_api_key()
    if not key:
        print("GOOGLE_API_KEY ausente no .env")
        return 1

    model_name = (os.getenv("EGO_GEMINI_MODEL_FLASH") or GEMINI_MODEL_FLASH).strip()
    print(f"Modelo: {model_name}")
    print(f"Chave: {key[:8]}...{key[-4:]}")

    try:
        import google.generativeai as genai
    except ImportError:
        print("Instale: pip install google-generativeai")
        return 1

    genai.configure(api_key=key)
    model = genai.GenerativeModel(model_name)
    try:
        resp = model.generate_content("Responda apenas: ok")
        text = (resp.text or "").strip()
        print(f"Resposta: {text[:120]}")
        if not text:
            print("API respondeu sem texto.")
            return 1
        print("\nGemini OK — pode reiniciar: python flask_api.py")
        return 0
    except Exception as exc:
        err = str(exc)
        print(f"\nFalhou: {err[:500]}")
        low = err.lower()
        if "429" in err or "quota" in low or "resource exhausted" in low:
            print(
                "\nCota esgotada. Ative billing no projeto Google Cloud ligado à chave:\n"
                "  https://aistudio.google.com/apikey\n"
                "  https://console.cloud.google.com/billing\n"
                "Depois crie chave nova, cole em GOOGLE_API_KEY e rode este script de novo."
            )
        elif "api key" in low and "invalid" in low:
            print("\nChave inválida. Gere outra em https://aistudio.google.com/apikey")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
