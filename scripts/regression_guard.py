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
            "submitNightDumpFromUri",
            "fetchPendingAgendaDrafts",
            "createShoppingItem",
            "recordStreakActivity",
            "confirmDelegationRequest",
            "respondEntreNosEvent",
            "submitDailyCareCheckin",
            "completeWellnessJourneyStep",
        ],
    ),
    (
        "app/src/components/DailyCareChallenge.tsx",
        ["MONSTRINHOS DO HUMOR", "MoodMonsterScene", "RankingLadder"],
    ),
    (
        "app/src/components/EgoDeBolsoChatCard.tsx",
        ["EGO DE BOLSO", "PocketCompanionShareModal", "Cuidar agora"],
    ),
    (
        "app/src/utils/egoDeBolsoCareRoute.ts",
        ["resolveEgoDeBolsoCareRoute", "/(main)/agenda"],
    ),
    (
        "app/src/utils/egoDeBolsoNotifications.ts",
        ["syncEgoDeBolsoCareNotification", "ego-de-bolso-care-18h"],
    ),
    (
        "app/src/utils/moodMonsterNotifications.ts",
        ["syncMoodMonsterNotifications", "mood-monster-streak-risk-20h", "mood-monster-goals-16h"],
    ),
    (
        "app/src/components/EgoDeBolsoTrialNudge.tsx",
        ["EGO de Bolso", "Ver planos"],
    ),
    (
        "app/src/components/SocialShareModal.tsx",
        ["Instagram Stories", "Instagram Post", "Instagram Reels", "WhatsApp"],
    ),
    (
        "app/src/components/PocketCompanionShareModal.tsx",
        ["EGO de Bolso", "Eu estou no nível", "sharePocketCompanionWhatsApp"],
    ),
    (
        "app/src/components/WellnessJourneyCard.tsx",
        ["EGO DE BOLSO", "Postar e desafiar amigos"],
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
        "app/src/components/agenda/ClassicSharedAgendaSection.tsx",
        ["createSharedCalendar", "createSharedCalendarEvent", "dismissSharedCalendarEvent", "+ Nova agenda compartilhada"],
    ),
    (
        "app/src/components/agenda/EntreNosAgendaSection.tsx",
        ["createSharedCalendar", "createSharedCalendarEvent", "respondEntreNosEvent", "Criar Entre Nós"],
    ),
    (
        "app/src/components/agenda/SharedAgendaManual.tsx",
        ["ClassicSharedAgendaSection", "EntreNosAgendaSection"],
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
            "shared_calendars_events_respond",
            '@app.post("/api/v1/night-dump")',
            "agenda_drafts_pending",
            "delegation_requests_pending",
            "streaks_record_activity",
            "shopping_list_get",
            '@app.post("/api/v1/daily-care/checkin")',
            '@app.post("/api/v1/daily-care/goal")',
            '@app.post("/api/v1/daily-care/shop")',
            '@app.post("/api/v1/wellness-journey/step")',
            '@app.get("/go")',
        ],
    ),
    (
        "ego_api/progression.py",
        ["get_cap", "maybe_expand_cap", "daily_ladder_window"],
    ),
    (
        "ego_api/daily_care.py",
        ["get_daily_care", "record_checkin", "record_goal", "purchase_shop_item", "CARE_MILESTONES"],
    ),
    (
        "ego_api/wellness_journey.py",
        ["get_journey", "record_step", "JOURNEY_LEVELS"],
    ),
    (
        "ego_api/download_go.py",
        ["public_go_url"],
    ),
    (
        "ego_api/services.py",
        [
            "def login(",
            "def refresh_session(",
            "def signup(",
            "Este e-mail já está cadastrado",
            "Este telefone já está cadastrado",
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
    (
        "ego_api/habits_db.py",
        [
            "list_pending_drafts",
            "insert_shopping_item",
            "list_persistent_shopping_items",
            "orphanize_shopping_for_reminder",
            "SUPABASE_AGENDA_DRAFTS_TABLE",
        ],
    ),
    (
        "ego_api/night_dump.py",
        ["process_night_dump", "confirm_draft_items", "dismiss_draft_item", "NIGHT_DUMP_EXTRACT_PROMPT", "assign_to"],
    ),
    (
        "ego_api/streaks.py",
        ["record_streak_activity", "get_streak", "get_night_dump_streak", "record_night_dump_streak", "evening_streak_notification_body"],
    ),
    (
        "ego_api/shared_calendar_notify.py",
        ["notify_members_new_event", "notify_member_invited_to_calendar", "notify_invite_response"],
    ),
    (
        "ego_api/family_pilot.py",
        ["enrich_family_items", "family_event_title_from_item"],
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
