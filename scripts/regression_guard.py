#!/usr/bin/env python3
"""
Verifica que símbolos críticos (já em produção) ainda existem no código.
Correr ANTES de deploy Railway ou build EAS.

  python scripts/regression_guard.py
"""
from __future__ import annotations

import json
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_HEALTH = "https://ego-ai-production-a2c2.up.railway.app/api/v1/health"

# (ficheiro relativo à raiz, substrings que DEVEM existir)
STABLE_SYMBOLS: list[tuple[str, list[str]]] = [
    (
        "app/src/api/client.ts",
        [
            "export async function login",
            "export async function refreshSessionToken",
            "sendChatVoiceFromUri",
            "sendChatVoiceFileNative",
            "export async function sendChatMessage",
            "export async function dismissReminder",
            "export async function createReminder",
            "deviceTimezonePayload",
        ],
    ),
    (
        "app/src/context/AuthContext.tsx",
        ["refreshSessionToken", "saveSecureItem", "STORAGE_KEY"],
    ),
    (
        "app/src/hooks/useVoiceChat.ts",
        ["sendChatVoiceFromUri", "stopRecordingAndSend"],
    ),
    (
        "app/src/components/agenda/PersonalAgendaManual.tsx",
        ["createReminder", "dismissReminder", "createAgendaItem", "+ Novo compromisso"],
    ),
    (
        "app/src/components/agenda/SharedAgendaManual.tsx",
        ["createSharedCalendar", "createSharedCalendarEvent", "dismissSharedCalendarEvent"],
    ),
    (
        "flask_api.py",
        [
            '@app.post("/api/v1/auth/login")',
            '@app.post("/api/v1/auth/refresh")',
            '@app.post("/api/v1/reminders")',
            "reminders_dismiss",
            '@app.delete("/api/v1/agenda/<agenda_id>")',
            "shared_calendars_events_dismiss",
        ],
    ),
    (
        "ego_api/services.py",
        [
            "def login(",
            "def refresh_session(",
            "def process_chat_message",
            "check_token_allowance",
        ],
    ),
    (
        "ego_api/tts.py",
        ["EDGE_TTS_VOICE_MAP", "synthesize_speech_mp3"],
    ),
    (
        "ego_api/db.py",
        ["def dismiss_reminder", "def insert_reminder", "def check_token_allowance"],
    ),
]

# Ficheiros que mudaram muito numa sessão — aviso (não falha)
WATCH_LARGE_TOUCH = [
    "ego_api/services.py",
    "ego_api/chat_schedule.py",
    "app/app/(main)/agenda.tsx",
]


def read_text(rel: str) -> str:
    path = ROOT / rel.replace("/", "\\") if "\\" not in rel else ROOT / rel
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def check_symbols() -> int:
    failed = 0
    print("=== Símbolos estáveis (código local) ===")
    for rel, needles in STABLE_SYMBOLS:
        text = read_text(rel)
        if not text:
            print(f"  ERRO  ficheiro em falta: {rel}")
            failed += 1
            continue
        for needle in needles:
            if needle not in text:
                print(f"  ERRO  {rel}: em falta '{needle}'")
                failed += 1
            else:
                print(f"  OK    {rel} :: {needle[:48]}")
    return failed


def _urlopen_health(req: urllib.request.Request):
    try:
        return urllib.request.urlopen(req, timeout=25)
    except urllib.error.URLError as exc:
        err = str(exc)
        if "SSL" not in err and "CERTIFICATE" not in err:
            raise
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return urllib.request.urlopen(req, timeout=25, context=ctx)


def check_health() -> int:
    print("\n=== API produção (/health) ===")
    try:
        req = urllib.request.Request(API_HEALTH, method="GET")
        with _urlopen_health(req) as resp:
            body = json.loads(resp.read().decode())
        if body.get("maintenance"):
            print("  ERRO  EGO_MAINTENANCE ligado em produção")
            return 1
        if body.get("ok") is not True:
            print(f"  ERRO  ok != true: {body}")
            return 1
        print(f"  OK    ok=true api_build={body.get('api_build', '?')}")
        return 0
    except urllib.error.HTTPError as e:
        print(f"  ERRO  HTTP {e.code}")
        return 1
    except Exception as exc:
        print(f"  AVISO  não foi possível contactar API ({exc}) — verifique rede")
        return 0


def main() -> int:
    failed = check_symbols()
    failed += check_health()
    print()
    if failed:
        print(f"REGRESSION GUARD: {failed} falha(s). NÃO faça deploy/build até corrigir.")
        return 1
    print("REGRESSION GUARD: tudo OK — pode deploy/build (teste manual ainda recomendado).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
