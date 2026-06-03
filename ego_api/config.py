from __future__ import annotations

import datetime
import os

try:
    from dotenv import load_dotenv

    load_dotenv(override=False)
except ImportError:
    pass

GEMINI_MODEL_FLASH = os.getenv("EGO_GEMINI_MODEL_FLASH", "gemini-1.5-flash")
GEMINI_MODEL_PRO = os.getenv("EGO_GEMINI_MODEL_PRO", "gemini-2.5-pro")
GEMINI_MODEL_IDS = (GEMINI_MODEL_FLASH, GEMINI_MODEL_PRO)

SUPABASE_HISTORY_TABLE = "chat_history"
SUPABASE_PROFILES_TABLE = "profiles"
SUPABASE_FEEDBACK_TABLE = "message_feedback"
SUPABASE_PERSONA_TABLE = "user_personas"
SUPABASE_REMINDERS_TABLE = "reminders"
SUPABASE_AGENDA_TABLE = "agenda"
SUPABASE_SHARED_CALENDARS_TABLE = "shared_calendars"
SUPABASE_SHARED_CALENDAR_MEMBERS_TABLE = "shared_calendar_members"
SUPABASE_SHARED_CALENDAR_EVENTS_TABLE = "shared_calendar_events"

AGENDA_HORIZON_DAYS = int(os.getenv("EGO_AGENDA_HORIZON_DAYS", "90"))
EGO_TRIAL_DAYS = int(os.getenv("EGO_TRIAL_DAYS", "20"))
CHAT_LLM_MAX_TURNS = int(os.getenv("EGO_CHAT_LLM_MAX_TURNS", "24"))
CHAT_HISTORY_FETCH_LIMIT = int(os.getenv("EGO_CHAT_HISTORY_FETCH_LIMIT", "40"))
PDF_CONTEXT_IN_SYSTEM_CHARS = int(os.getenv("EGO_PDF_CONTEXT_CHARS", "3000"))
# Legado (Streamlit / fallback); planos usam ego_api.plans
EGO_MONTHLY_TOKEN_LIMIT_FREE = int(os.getenv("EGO_MONTHLY_TOKEN_LIMIT_FREE", "200000"))
EGO_MONTHLY_TOKEN_LIMIT_PRO = int(os.getenv("EGO_MONTHLY_TOKEN_LIMIT_PRO", "2500000"))
DAILY_MESSAGE_LIMIT = int(os.getenv("EGO_DAILY_MESSAGE_LIMIT", "0"))

STRIPE_MENSAL_URL = os.getenv("STRIPE_CHECKOUT_MENSAL_URL", "")
STRIPE_ANUAL_URL = os.getenv("STRIPE_CHECKOUT_ANUAL_URL", "")


def read_env(name: str, default: str = "") -> str:
    raw = (os.getenv(name) or default).strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        raw = raw[1:-1].strip()
    return raw.rstrip(",").strip()


def gemini_api_key() -> str:
    return read_env("GOOGLE_API_KEY") or read_env("GEMINI_API_KEY")


def supabase_url() -> str:
    return read_env("SUPABASE_URL")


def supabase_anon_key() -> str:
    return (
        read_env("SUPABASE_KEY")
        or read_env("SUPABASE_PUBLISHABLE_KEY")
        or read_env("SUPABASE_ANON_KEY")
    )


def cors_origins() -> list[str]:
    """Origens permitidas no browser (Expo web usa :8081). Não use '*' com credentials."""
    raw = read_env("EGO_CORS_ORIGINS", "")
    if raw and raw != "*":
        return [o.strip() for o in raw.split(",") if o.strip()]
    local_defaults = [
        "http://localhost:8081",
        "http://127.0.0.1:8081",
        "http://localhost:8082",
        "http://127.0.0.1:8082",
        "http://localhost:19006",
        "http://127.0.0.1:19006",
        "http://localhost:5000",
        "http://127.0.0.1:5000",
        "http://localhost:8081",
        "http://127.0.0.1:8081",
        "http://localhost:8083",
        "http://127.0.0.1:8083",
        "http://localhost",
        "http://127.0.0.1",
        "capacitor://localhost",
        "https://localhost",
    ]
    # Permite adicionar origens locais sem editar código (ex.: IP LAN atual).
    extra_raw = read_env("EGO_CORS_EXTRA_ORIGINS", "")
    extra = [o.strip() for o in extra_raw.split(",") if o.strip()]
    merged = [*local_defaults, *extra]
    unique: list[str] = []
    seen: set[str] = set()
    for origin in merged:
        if origin in seen:
            continue
        unique.append(origin)
        seen.add(origin)
    return unique


def api_env() -> str:
    return read_env("EGO_API_ENV", "development").lower()


def is_production_env() -> bool:
    return api_env() in ("prod", "production")


def _ego_beta_deadline() -> datetime.datetime | None:
    raw = read_env("EGO_BETA_DEADLINE")
    if not raw:
        return None
    try:
        dt = datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt
    except ValueError:
        return None


def gemini_flash_only() -> bool:
    return read_env("EGO_GEMINI_FLASH_ONLY", "").lower() in ("1", "true", "yes", "sim")


def beta_unlimited() -> bool:
    if read_env("EGO_BETA_SEM_LIMITE", "").lower() in ("1", "true", "yes", "sim"):
        return True
    return False


def monthly_token_limit(is_pro: bool) -> int:
    """Legado — prefira ego_api.plans.plan_limits()."""
    return EGO_MONTHLY_TOKEN_LIMIT_PRO if is_pro else EGO_MONTHLY_TOKEN_LIMIT_FREE
