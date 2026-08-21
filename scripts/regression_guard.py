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
            "submitDailyCareJournalNote",
            "completeWellnessJourneyStep",
            "export async function purchaseCompanionEggColor",
            "export async function requestPasswordReset",
            "export async function completePasswordReset",
            "export async function deleteMyAccount",
        ],
    ),
    (
        "app/src/components/DailyCareChallenge.tsx",
        ["MONSTRINHOS DO HUMOR", "MoodMonsterScene", "RankingLadder", "1º PASSO"],
    ),
    (
        "app/src/components/moodMonsters/MoodGardenAmbient.tsx",
        ["MoodGardenAmbient", "cloud"],
    ),
    (
        "app/src/components/moodMonsters/MoodJournalWeek.tsx",
        ["MoodJournalWeek", "Diário de humor", "Ver histórico completo"],
    ),
    (
        "app/src/components/moodMonsters/MoodJournalHistory.tsx",
        ["MoodJournalHistory", "Ainda sem entradas"],
    ),
    (
        "app/app/(main)/mood-journal.tsx",
        ["Diário de humor", "Falar com meu avatar sobre isso"],
    ),
    (
        "app/src/components/moodMonsters/MoodGardenWidgetCard.tsx",
        ["MoodGardenWidgetCard", "if (!care?.question) return null", "useMemo", "streak em risco"],
    ),
    (
        "app/src/components/AvatarEngagementCard.tsx",
        ["AvatarEngagementCard", "colors.bgCard", "onOpenAvatar"],
    ),
    (
        "app/src/components/companion/CompanionPocketAmbient.tsx",
        ["CompanionPocketAmbient", "cloud"],
    ),
    (
        "app/src/components/companion/CompanionPocketScene.tsx",
        ["CompanionPocketScene", "CompanionPocketAmbient"],
    ),
    (
        "app/src/components/companion/CompanionSprite.tsx",
        ["CompanionSprite", "celebrate", "eggColor"],
    ),
    (
        "app/src/components/companion/CompanionEggColorShop.tsx",
        ["CompanionEggColorShop", "purchaseCompanionEggColor"],
    ),
    (
        "app/src/components/companion/CompanionWeeklyBar.tsx",
        ["CompanionWeeklyBar", "DESAFIO DA SEMANA", "estrelas na loja de cores"],
    ),
    (
        "app/src/utils/companionEggPalettes.ts",
        ["EGG_COLOR_PALETTES", "resolveEggPalette"],
    ),
    (
        "app/src/components/companion/CompanionNameChip.tsx",
        ["CompanionNameChip", "saveCompanionName"],
    ),
    (
        "app/src/utils/egoDeBolsoCompanionName.ts",
        ["saveCompanionName", "ego_companion_name"],
    ),
    (
        "app/src/components/AppGradientBackground.tsx",
        ["AppGradientBackground"],
    ),
    (
        "app/src/storage/moodGardenWidgetSnapshot.ts",
        ["buildMoodGardenWidgetSnapshot", "goalsLine", "MOOD_GARDEN_WIDGET_STORAGE_KEY"],
    ),
    (
        "app/src/utils/monsterChatNotice.ts",
        ["queueMonsterChatNotice", "consumeMonsterChatNotice"],
    ),
    (
        "app/src/widgets/syncMoodGardenHomeWidget.tsx",
        ["syncMoodGardenHomeWidget", "MoodGardenAndroidWidget"],
    ),
    (
        "app/src/widgets/syncEgoDeBolsoHomeWidget.tsx",
        ["syncEgoDeBolsoHomeWidget", "EgoDeBolsoAndroidWidget", "EgoDeBolso"],
    ),
    (
        "app/src/widgets/EgoDeBolsoAndroidWidget.tsx",
        ["EgoDeBolsoAndroidWidget", "EGO DE BOLSO"],
    ),
    (
        "app/src/storage/egoDeBolsoWidgetSnapshot.ts",
        ["EGO_DE_BOLSO_ANDROID_WIDGET_NAME", "buildEgoDeBolsoWidgetSnapshot"],
    ),
    (
        "app/index.ts",
        ["registerWidgetTaskHandler", "androidWidgetTaskHandler", "expo-router/entry"],
    ),
    (
        "app/targets/mood-garden/expo-target.config.js",
        ['type: "widget"', "MoodGardenWidget"],
    ),
    (
        "app/src/components/PersonaGate.tsx",
        ["PersonaGate", "choose-avatar", "personaGateOk"],
    ),
    (
        "app/src/components/ProfilePhoneGate.tsx",
        ["ProfilePhoneGate", "Telefone já é pedido no signup"],
    ),
    (
        "app/src/components/EgoDeBolsoChatCard.tsx",
        ["EGO DE BOLSO", "PocketCompanionShareModal", "Cuidar agora", "Falar disso", "Semana:", "pendingHighlight", "onTalkMission", "celebrate", "buildBolsoTalkDraft"],
    ),
    (
        "app/src/utils/buildBolsoTalkDraft.ts",
        ["buildBolsoTalkDraft", "missions_per_day"],
    ),
    (
        "app/src/utils/egoDeBolsoCareRoute.ts",
        ["resolveEgoDeBolsoCareRoute", "/(main)/agenda"],
    ),
    (
        "app/src/utils/egoDeBolsoNotifications.ts",
        ["syncEgoDeBolsoCareNotification", "ego-de-bolso-care-18h", "ego_daily_checkin_enabled"],
    ),
    (
        "app/src/utils/egoDeBolsoDailyCare.ts",
        ["egoDeBolsoDailyCarePercent", "missions_per_day"],
    ),
    (
        "app/src/utils/egoDeBolsoStepHints.ts",
        ["formatWellnessPendingLine", "Monstrinhos", "missão fecha quando entrar"],
    ),
    (
        "ego_api/shared_calendars.py",
        [
            "_finalize_invited_member_join",
            "_credit_inviter_shared_calendar_mission",
            "reconcile_uncredited_invite_missions",
            "link_shared_memberships_for_user",
        ],
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
        "app/src/utils/egoDeBolsoShare.ts",
        [
            "buildPocketCompanionWhatsAppText",
            "buildPocketCompanionInstagramCaption",
            "pocketCompanionCardHeadline",
        ],
    ),
    (
        "app/src/components/PocketCompanionShareModal.tsx",
        ["EGO de Bolso", "Desafiar amigos", "sharePocketCompanionWhatsApp", "pocketCompanionCardChallenge"],
    ),
    (
        "app/src/components/WellnessJourneyCard.tsx",
        ["EGO DE BOLSO", "Postar e desafiar amigos"],
    ),
    (
        "app/src/context/AuthContext.tsx",
        ["refreshSessionToken", "saveSecureItem", "STORAGE_KEY", "sessionNeedsRefresh", "saveLocalProfilePhone"],
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
        ["createSharedCalendar", "createSharedCalendarEvent", "respondEntreNosEvent", "Convidar pessoa", "+ Novo Entre Nós"],
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
            '@app.post("/api/v1/auth/forgot-password")',
            '@app.post("/api/v1/auth/reset-password")',
            '@app.get("/auth/reset-password")',
            '@app.delete("/api/v1/me")',
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
            '@app.post("/api/v1/daily-care/journal-note")',
            '@app.post("/api/v1/daily-care/goal")',
            '@app.post("/api/v1/daily-care/calm-mark")',
            '@app.post("/api/v1/daily-care/shop")',
            '@app.post("/api/v1/wellness-journey/step")',
            '@app.post("/api/v1/wellness-journey/shop")',
            '@app.post("/api/v1/pausa-ego/complete")',
            "admin_cron_ego_de_bolso_care",
            '@app.post("/api/v1/admin/cron/store-versions")',
            '@app.get("/go")',
        ],
    ),
    (
        "ego_api/store_versions.py",
        [
            "parse_ios_lookup_payload",
            "parse_play_html_version",
            "get_store_versions",
            "refresh_store_versions",
            "max_version",
        ],
    ),
    (
        "ego_api/config.py",
        [
            "app_update_payload",
            "store_version_auto_enabled",
            "latest_version_ios",
            "latest_version_android",
        ],
    ),
    (
        "app/src/context/AppUpdateContext.tsx",
        [
            "latest_version_ios",
            "latest_version_android",
            "AppUpdateProvider",
        ],
    ),
    (
        "ego_api/progression.py",
        ["get_cap", "maybe_expand_cap", "daily_ladder_window"],
    ),
    (
        "ego_api/daily_care.py",
        ["get_daily_care", "record_checkin", "record_journal_note", "record_goal", "record_calm_mark", "purchase_shop_item", "award_quiz_seeds", "CARE_MILESTONES", "shop_week_label", "mood_journal"],
    ),
    (
        "ego_api/gentleness.py",
        ["gentle_mode_active", "mirror_line", "gentleness_payload", "crisis_bridge", "mark_calm_day", "compute_calm_streak", "note_signals_lonely", "compute_survival_streak", "survival_streak_line"],
    ),
    (
        "ego_api/daily_care_missions.py",
        ["validate_mission_pool_size", "MISSION_POOL", "SURPRISE_POOL", "build_daily_goals"],
    ),
    (
        "ego_api/daily_care_shop.py",
        ["validate_shop_catalog_size", "SHOP_BASE_ITEMS", "SHOP_ROTATING_POOL", "shop_catalog_payload"],
    ),
    (
        "ego_api/wellness_journey.py",
        ["get_journey", "record_step", "JOURNEY_LEVELS", "validate_journey_levels", "validate_journey_expansion_caps", "_format_today_task", "_daily_care_fraction", "_label_with_how", "companion_name", "egg_color_shop", "weekly_challenge"],
    ),
    (
        "ego_api/companion_shop.py",
        ["purchase_egg_color", "award_mission_stars", "EGG_COLOR_ITEMS", "STARS_PER_MISSION"],
    ),
    (
        "ego_api/companion_weekly.py",
        ["build_weekly_payload", "touch_weekly_day_complete", "try_award_weekly_bonus", "STARS_WEEKLY_BONUS", "WEEK_DAYS_GOAL"],
    ),
    (
        "ego_api/pausa_ego.py",
        ["get_pausa", "complete_session", "default_payload", "MOMENTS", "bolso_replaced_by_pausa", "pausa_chat_prompt_block", "breath_duration_seconds", "BREATH_DURATIONS"],
    ),
    (
        "ego_api/pausa_exercises.py",
        [
            "pick_daily_exercise",
            "pick_tomorrow_teaser",
            "plan_benefits_payload",
            "exercises_for_tier",
            "exercise_catalog_size",
            "is_valid_session_kind",
            "ANYWHERE_LINE",
        ],
    ),
    (
        "ego_api/pausa_push.py",
        [
            "process_pausa_morning_pushes",
            "process_pausa_evening_pushes",
            "process_pausa_pushes",
            "morning_notification_copy",
            "evening_notification_copy",
            "pausa_push_enabled",
            "MORNING_HOUR",
            "EVENING_HOUR",
        ],
    ),
    (
        "ego_api/seasonal_events.py",
        ["get_active_event"],
    ),
    (
        "ego_api/mood_quiz.py",
        ["get_quiz", "submit_answer", "QUIZ_SEED_REWARD"],
    ),
    (
        "ego_api/mood_social.py",
        ["invite_payload"],
    ),
    (
        "ego_api/ego_de_bolso_push.py",
        [
            "process_ego_de_bolso_care_pushes",
            "process_ego_de_bolso_morning_pushes",
            "maybe_send_mission_complete_push",
            "mission_complete_notification_copy",
            "morning_notification_copy",
            "send_expo_push",
            "companion_needs_care",
            "MORNING_HOUR",
            "CARE_HOUR",
            "_bolso_push_suppressed",
        ],
    ),
    (
        "ego_api/plan_retention.py",
        [
            "process_plan_retention_cron",
            "on_trial_access_denied",
            "on_daily_limit_hit",
            "deliver_plan_retention",
            "plans_checkout_url",
        ],
    ),
    (
        "ego_api/bolso_chat.py",
        ["bolso_mission_prompt_block", "try_mission_complete_push"],
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
            "def request_password_reset(",
            "def complete_password_reset(",
            "Este e-mail já está cadastrado",
            "def process_chat_message",
            "check_token_allowance",
        ],
    ),
    (
        "ego_api/auth_signup.py",
        [
            "Este telefone já está cadastrado",
            "check_signup_eligibility",
            "delete_auth_user",
            "MSG_NO_ACCOUNT",
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
    (
        "ego_api/account_delete.py",
        ["delete_user_account", "MSG_DELETE_OK"],
    ),
    (
        "app/app/(main)/account.tsx",
        ["Excluir minha conta", "deleteMyAccount"],
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
        mon = body.get("monitoring") or {}
        if mon.get("sentry_dsn_set") and not mon.get("sentry"):
            print("  AVISO  Sentry DSN definido mas sentry=false (falta sentry-sdk no deploy?)")
        pi = body.get("play_integrity") or {}
        if not pi.get("enabled"):
            print("  AVISO  EGO_PLAY_INTEGRITY=0 em produção")
        print(f"  OK    ok=true api_build={body.get('api_build', '?')}")
        return 0
    except urllib.error.HTTPError as e:
        print(f"  ERRO  HTTP {e.code}")
        return 1
    except Exception as exc:
        print(f"  AVISO  não foi possível contactar API ({exc}) — verifique rede")
        return 0


def check_journey_missions() -> int:
    print("\n=== Missões EGO de Bolso (texto vs regras) ===")
    try:
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from ego_api.wellness_journey import (
            HANDCRAFTED_MAX,
            validate_journey_expansion_caps,
            validate_journey_levels,
        )

        cap = 500
        errors = validate_journey_levels(cap=cap)
        if not errors:
            errors = validate_journey_expansion_caps(caps=(500, 1000))
        if errors:
            for err in errors:
                print(f"  ERRO  {err}")
            return len(errors)
        print(
            f"  OK    {cap} níveis + expansão até 1000 validados "
            f"({HANDCRAFTED_MAX} guiados + procedurais automáticos)"
        )
        return 0
    except Exception as exc:
        print(f"  ERRO  validação jornada: {exc}")
        return 1


def check_shop_catalog() -> int:
    print("\n=== Loja Monstrinhos (30+ itens + rotação) ===")
    try:
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from ego_api.daily_care_shop import (
            SHOP_BASE_ITEMS,
            SHOP_ROTATING_POOL,
            SHOP_ROTATION_COUNT,
            validate_shop_catalog_size,
            shop_catalog_payload,
        )

        validate_shop_catalog_size()
        sample = shop_catalog_payload({}, 100)
        items = sample.get("shop_items") or []
        rotating = [i for i in items if i.get("rotating")]
        if len(rotating) != SHOP_ROTATION_COUNT:
            print(f"  ERRO  rotação semanal: esperado {SHOP_ROTATION_COUNT}, veio {len(rotating)}")
            return 1
        print(
            f"  OK    {len(SHOP_BASE_ITEMS)} base + {len(SHOP_ROTATING_POOL)} pool "
            f"= {len(SHOP_BASE_ITEMS) + len(SHOP_ROTATING_POOL)} itens · {len(rotating)}/semana"
        )
        return 0
    except Exception as exc:
        print(f"  ERRO  loja Monstrinhos: {exc}")
        return 1


def check_mission_pool() -> int:
    print("\n=== Missões Monstrinhos (pool 20+ + surpresa/dia) ===")
    try:
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        import datetime

        from ego_api.daily_care_missions import (
            MISSION_POOL,
            SURPRISE_POOL,
            build_daily_goals,
            daily_mission_keys,
            missions_differ_within_days,
            validate_mission_pool_size,
        )

        validate_mission_pool_size()
        today = datetime.date.today().isoformat()
        tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
        day3 = (datetime.date.today() + datetime.timedelta(days=2)).isoformat()
        goals = build_daily_goals({}, today, False, checkin_seeds=5)
        surprise = [g for g in goals if g.get("surprise")]
        if len(surprise) != 1:
            print(f"  ERRO  esperado 1 surpresa/dia, veio {len(surprise)}")
            return 1
        if len(goals) != 5:
            print(f"  ERRO  esperado 5 missões (check-in + 4), veio {len(goals)}")
            return 1
        if not missions_differ_within_days(today, tomorrow):
            print("  ERRO  missões iguais hoje e amanhã")
            return 1
        if daily_mission_keys(today) == daily_mission_keys(day3):
            print("  AVISO  missões dia+2 iguais — raro mas aceitável")
        print(
            f"  OK    {len(MISSION_POOL)} regulares + {len(SURPRISE_POOL)} surpresa "
            f"= {len(MISSION_POOL) + len(SURPRISE_POOL)} · 1 surpresa/dia"
        )
        return 0
    except Exception as exc:
        print(f"  ERRO  missões Monstrinhos: {exc}")
        return 1


def check_gentleness() -> int:
    print("\n=== Jardim da Gentileza (modo suave + PAUSA bridge) ===")
    try:
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        import datetime

        from ego_api.daily_care_missions import build_daily_goals, daily_mission_defs
        from ego_api.gentleness import (
            crisis_bridge,
            gentle_mode_active,
            gentleness_payload,
            note_signals_lonely,
        )

        if not note_signals_lonely("domingo sozinha"):
            print("  ERRO  note_signals_lonely deveria detectar solidão")
            return 1

        today = datetime.date.today().isoformat()
        journal = [{"date": today, "mood": "heavy", "note": ""}]
        if not gentle_mode_active("heavy", journal):
            print("  ERRO  gentle_mode deveria ligar em Nublina")
            return 1
        bridge = crisis_bridge("heavy", True)
        if not bridge.get("show"):
            print("  ERRO  crisis_bridge deveria aparecer em heavy")
            return 1
        gentle_goals = build_daily_goals({}, today, True, checkin_seeds=5, gentle_mode=True)
        gentle_keys = {g["key"] for g in gentle_goals if g["key"] != "checkin"}
        if "surprise_gentle_day" not in gentle_keys:
            print("  ERRO  missão surpresa gentil ausente")
            return 1
        if "adventure" in gentle_keys or "tidy" in gentle_keys:
            print("  ERRO  missões pesadas no modo gentil")
            return 1
        defs = daily_mission_defs(today, gentle=True)
        if len(defs) != 4:
            print(f"  ERRO  modo gentil espera 4 missões, veio {len(defs)}")
            return 1
        payload = gentleness_payload(
            {},
            today=today,
            checked_today=True,
            last_mood="heavy",
            journal=journal,
            local_hour=21,
        )
        if not payload.get("gentle_mode") or not payload.get("night_garden"):
            print("  ERRO  gentleness_payload incompleto")
            return 1
        if not payload.get("survival_streak_line") and payload.get("survival_streak_current", 0) == 0:
            pass
        lonely_bridge = crisis_bridge("ok", True, lonely_note=True, local_hour=23)
        if not lonely_bridge.get("show"):
            print("  ERRO  crisis_bridge deveria aparecer com carta solidão")
            return 1
        print("  OK    modo gentil · PAUSA bridge · missões leves · noite · solidão")
        return 0
    except Exception as exc:
        print(f"  ERRO  gentleness: {exc}")
        return 1


def check_pausa_exercise_pool() -> int:
    print("\n=== PAUSA — EXERCISE_POOL (key obrigatório) ===")
    try:
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from ego_api.pausa_exercises import EXERCISE_POOL, exercises_for_tier

        missing = [i for i, e in enumerate(EXERCISE_POOL) if not str(e.get("key") or "").strip()]
        if missing:
            print(f"  ERRO  exercícios sem key nos índices: {missing}")
            return len(missing)
        from ego_api.plans import PLAN_ESSENTIAL

        if len(exercises_for_tier(PLAN_ESSENTIAL)) != len(EXERCISE_POOL):
            print("  ERRO  PAUSA ainda bloqueada por plano no Essencial")
            return 1
        print(f"  OK    {len(EXERCISE_POOL)} técnicas com key · todas liberadas")
        return 0
    except Exception as exc:
        print(f"  ERRO  pausa_exercises: {exc}")
        return 1


def check_bootstrap_fallback_daily_care() -> int:
    print("\n=== Bootstrap fallback — Monstrinhos (daily_care) ===")
    try:
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from ego_api.services import bootstrap_payload_fallback

        payload = bootstrap_payload_fallback(None, "test-user")
        care = payload.get("daily_care")
        if not isinstance(care, dict):
            print("  ERRO  bootstrap_payload_fallback sem daily_care dict")
            return 1
        question = care.get("question")
        if not isinstance(question, dict) or not str(question.get("text") or "").strip():
            print("  ERRO  daily_care.question.text ausente no fallback")
            return 1
        moods = care.get("moods")
        if not isinstance(moods, list) or len(moods) < 5:
            print("  ERRO  daily_care.moods incompleto no fallback")
            return 1
        print("  OK    fallback inclui jardim + pergunta do dia")
        return 0
    except Exception as exc:
        print(f"  ERRO  bootstrap fallback: {exc}")
        return 1


def check_store_versions_parse() -> int:
    print("\n=== Store versions parse (banner automático) ===")
    try:
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from ego_api.store_versions import (
            max_version,
            parse_ios_lookup_payload,
            parse_play_html_version,
        )

        ios_json = b'{"resultCount":1,"results":[{"version":"1.0.112","trackId":6780595396}]}'
        ios_ver = parse_ios_lookup_payload(ios_json)
        if ios_ver != "1.0.112":
            print(f"  ERRO  iOS parse esperado 1.0.112, got {ios_ver!r}")
            return 1

        play_html = (
            'noise [["1.0.99"]] more '
            '[[["1.0.112"]]] '
            '"softwareVersion":"1.0.110"'
        )
        play_ver = parse_play_html_version(play_html)
        if play_ver != "1.0.112":
            print(f"  ERRO  Play parse esperado 1.0.112, got {play_ver!r}")
            return 1

        if max_version("1.0.111", "1.0.112", "") != "1.0.112":
            print("  ERRO  max_version falhou")
            return 1

        from ego_api.store_versions import normalize_ios_store_version

        if normalize_ios_store_version("1.0.118", "1.0.111") != "1.0.112":
            print("  ERRO  alias iOS 1.0.118 -> 1.0.112 falhou")
            return 1

        print("  OK    parse iOS + Play + max_version")
        return 0
    except Exception as exc:
        print(f"  ERRO  store_versions: {exc}")
        return 1


def check_apply_user_auth_no_set_session() -> int:
    """RLS no servidor não pode chamar GoTrue set_session (queima refresh do app)."""
    print("\n=== Auth persistente — apply_user_auth sem set_session ===")
    path = ROOT / "ego_api" / "supabase_client.py"
    text = path.read_text(encoding="utf-8")
    start = text.find("def apply_user_auth")
    if start < 0:
        print("  ERRO  apply_user_auth ausente")
        return 1
    nxt = text.find("\ndef ", start + 1)
    body = text[start : nxt if nxt > 0 else None]
    if ".set_session(" in body:
        print("  ERRO  apply_user_auth chama set_session (invalida refresh no telemóvel)")
        return 1
    if "postgrest.auth" not in body:
        print("  ERRO  apply_user_auth deve usar postgrest.auth(access)")
        return 1
    print("  OK    JWT no PostgREST; refresh só em /auth/refresh")

    print("\n=== Auth persistente — sem auto_refresh no servidor ===")
    lite = (ROOT / "ego_supabase.py").read_text(encoding="utf-8")
    if "auto_refresh_token: bool = True" in lite:
        print("  ERRO  ego_supabase auto_refresh_token=True (queima refresh do telemóvel)")
        return 1
    if "auto_refresh_token: bool = False" not in lite:
        print("  ERRO  ego_supabase deve default auto_refresh_token=False")
        return 1
    if "auto_refresh_token=False" not in text and "_server_client_options" not in text:
        print("  ERRO  supabase_client deve forçar auto_refresh off")
        return 1
    print("  OK    auto_refresh_token desligado no worker")
    return 0


def main() -> int:
    failed = check_symbols()
    failed += check_journey_missions()
    failed += check_shop_catalog()
    failed += check_mission_pool()
    failed += check_gentleness()
    failed += check_pausa_exercise_pool()
    failed += check_bootstrap_fallback_daily_care()
    failed += check_store_versions_parse()
    failed += check_apply_user_auth_no_set_session()
    try:
        import importlib.util

        og_path = ROOT / "scripts" / "onboarding_guard.py"
        spec = importlib.util.spec_from_file_location("onboarding_guard", og_path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if mod.main() != 0:
                failed += 1
        else:
            print("\n  ERRO  não foi possível carregar onboarding_guard.py")
            failed += 1
    except Exception as exc:
        print(f"\n  ERRO  onboarding_guard: {exc}")
        failed += 1
    failed += check_health()
    print()
    if failed:
        print(f"REGRESSION GUARD: {failed} falha(s). NÃO faça deploy/build até corrigir.")
        return 1
    print("REGRESSION GUARD: tudo OK — pode deploy/build (teste manual ainda recomendado).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
