from __future__ import annotations

import datetime
import os

try:
    from dotenv import load_dotenv

    load_dotenv(override=False)
except ImportError:
    pass

GEMINI_MODEL_FLASH = os.getenv("EGO_GEMINI_MODEL_FLASH", "gemini-2.0-flash")
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
SUPABASE_AGENDA_DRAFTS_TABLE = "agenda_drafts"
SUPABASE_SHOPPING_LIST_TABLE = "shopping_list_items"
SUPABASE_DELEGATION_REQUESTS_TABLE = "delegation_requests"

# Máximo de agendas de grupo que cada utilizador pode criar (ser dono).
MAX_SHARED_CALENDARS_PER_OWNER = int(os.getenv("EGO_MAX_SHARED_CALENDARS", "10"))
# Máximo de pessoas (membros + convites pendentes) por agenda compartilhada.
MAX_MEMBERS_PER_SHARED_CALENDAR = int(
    os.getenv("EGO_MAX_SHARED_CALENDAR_MEMBERS", "100")
)

AGENDA_HORIZON_DAYS = int(os.getenv("EGO_AGENDA_HORIZON_DAYS", "90"))
EGO_TRIAL_DAYS = int(os.getenv("EGO_TRIAL_DAYS", "0"))
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


def openai_api_key() -> str:
    return read_env("OPENAI_API_KEY")


def openai_realtime_enabled() -> bool:
    """Voz em tempo real (OpenAI Realtime) — requer OPENAI_API_KEY no servidor."""
    if read_env("EGO_OPENAI_REALTIME", "1").lower() in ("0", "false", "no", "nao", "não"):
        return False
    return bool(openai_api_key())


def openai_realtime_model() -> str:
    """Modelo Realtime — gpt-realtime-mini = atual e económico; override com OPENAI_REALTIME_MODEL."""
    return read_env(
        "OPENAI_REALTIME_MODEL",
        "gpt-realtime-mini",
    )


def openai_realtime_phone_fast() -> bool:
    """Respostas curtas + VAD agressivo — menor latência (Chamada ao vivo turbo)."""
    return read_env("EGO_REALTIME_PHONE_FAST", "1").lower() not in (
        "0",
        "false",
        "no",
        "nao",
        "não",
    )


def openai_realtime_max_output_tokens_phone() -> int:
    default = "96" if openai_realtime_phone_fast() else "220"
    raw = read_env("EGO_REALTIME_MAX_TOKENS_PHONE", default)
    try:
        return max(48, min(400, int(raw)))
    except ValueError:
        return 96 if openai_realtime_phone_fast() else 220


def openai_realtime_vad_eagerness() -> str:
    """semantic_vad: auto | low | medium | high — high = responde mais cedo."""
    if openai_realtime_phone_fast():
        return "high"
    raw = read_env("EGO_REALTIME_VAD_EAGERNESS", "auto").lower()
    if raw in ("low", "medium", "high", "auto"):
        return raw
    return "auto"


def openai_realtime_use_webrtc() -> bool:
    return read_env("EGO_REALTIME_WEBRTC", "1").lower() not in (
        "0",
        "false",
        "no",
        "nao",
        "não",
    )


def openai_realtime_voice_male() -> str:
    return read_env("OPENAI_REALTIME_VOICE_MALE", "echo")


def openai_realtime_voice_female() -> str:
    return read_env("OPENAI_REALTIME_VOICE_FEMALE", "coral")


def openai_realtime_vad_silence_ms() -> int:
    """Pausa (ms) após falar para a IA responder — menor = mais rápido, mais sensível."""
    default = "200" if openai_realtime_phone_fast() else "280"
    raw = read_env("EGO_REALTIME_VAD_SILENCE_MS", default)
    try:
        return max(160, min(800, int(raw)))
    except ValueError:
        return 200 if openai_realtime_phone_fast() else 280


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
    if is_production_env() and (not raw or raw == "*"):
        # App mobile não usa CORS; browser só com allowlist explícita.
        return []
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
        "http://localhost:8084",
        "http://127.0.0.1:8084",
        "http://localhost:8085",
        "http://127.0.0.1:8085",
        "http://localhost:8086",
        "http://127.0.0.1:8086",
        "http://localhost:8087",
        "http://127.0.0.1:8087",
        "http://localhost:8088",
        "http://127.0.0.1:8088",
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


def chat_agenda_actions_enabled() -> bool:
    """False (padrão) = avatares só escutam; agenda 100% manual na aba Agenda."""
    return read_env("EGO_CHAT_AGENDA_ACTIONS", "0").lower() in (
        "1",
        "true",
        "yes",
        "sim",
    )


def beta_unlimited() -> bool:
    if is_production_env():
        return False
    if read_env("EGO_BETA_SEM_LIMITE", "").lower() in ("1", "true", "yes", "sim"):
        return True
    return False


def production_bypass_warnings() -> list[str]:
    """Variáveis perigosas activas em produção (para logs de arranque)."""
    if not is_production_env():
        return []
    warnings: list[str] = []
    if read_env("EGO_TEST_TOTAL_EMAILS"):
        warnings.append("EGO_TEST_TOTAL_EMAILS definido (ignorado em produção)")
    if read_env("EGO_BETA_SEM_LIMITE", "").lower() in ("1", "true", "yes", "sim"):
        warnings.append("EGO_BETA_SEM_LIMITE definido (ignorado em produção)")
    if read_env("EGO_MAINTENANCE", "").lower() in ("1", "true", "yes", "sim"):
        warnings.append("EGO_MAINTENANCE=1 — app em manutenção")
    if read_env("EGO_ENFORCE_HTTPS", "").lower() not in ("1", "true", "yes", "sim"):
        warnings.append("EGO_ENFORCE_HTTPS desligado em produção")
    return warnings


def latest_app_version() -> str:
    """Versão mais recente na loja — app antigo mostra aviso de atualização."""
    return read_env("EGO_LATEST_APP_VERSION", "1.0.50")


def play_store_update_url() -> str:
    """Link Play (produção por defeito — parceiros / QR /go)."""
    url = read_env(
        "EGO_PLAY_STORE_URL",
        "https://play.google.com/store/apps/details?id=com.egoai.app",
    )
    if url:
        return url
    return "market://details?id=com.egoai.app"


def app_update_message() -> str:
    return read_env(
        "EGO_APP_UPDATE_MESSAGE",
        "1.0.50: Sessão persistente — app fica logado ao reabrir. Toque em Atualizar agora.",
    )


def testflight_update_url() -> str:
    """Link iOS — App Store produção (override EGO_TESTFLIGHT_URL se precisares Beta)."""
    return read_env(
        "EGO_TESTFLIGHT_URL",
        "https://apps.apple.com/app/id6780595396",
    ).strip()


def app_store_public_url() -> str:
    return read_env(
        "EGO_APP_STORE_URL",
        "https://apps.apple.com/app/id6780595396",
    ).strip()


def maintenance_mode() -> bool:
    return read_env("EGO_MAINTENANCE", "").lower() in ("1", "true", "yes", "sim")


def maintenance_message() -> str:
    return read_env(
        "EGO_MAINTENANCE_MESSAGE",
        "Estamos atualizando o servidor. Algumas funções podem falhar por instantes.",
    )


def latest_android_version_code() -> int:
    """Version code Play (EAS autoIncrement) — Android usa para aviso de atualização."""
    raw = read_env("EGO_LATEST_ANDROID_VERSION_CODE", "89").strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 68


def app_update_payload() -> dict[str, str | int]:
    from ego_api.download_go import public_go_url

    return {
        "latest_version": latest_app_version(),
        "play_store_url": play_store_update_url(),
        "ios_update_url": testflight_update_url(),
        "smart_download_url": public_go_url(),
        "message": app_update_message(),
        "android_version_code": latest_android_version_code(),
    }


def chat_defer_tts_on_voice() -> bool:
    """Voz: devolve texto primeiro; o app pede áudio em /tts (evita timeout)."""
    raw = read_env("EGO_CHAT_DEFER_TTS_ON_VOICE", "1").strip().lower()
    return raw not in ("0", "false", "no", "nao", "não")


def voice_fast_mode() -> bool:
    """Voz: prompt curto, sem lembretes/agenda no pós-processamento — menor latência."""
    raw = read_env("EGO_VOICE_FAST", "1").strip().lower()
    return raw not in ("0", "false", "no", "nao", "não")


def voice_max_output_tokens() -> int:
    """Respostas de voz curtas — Railway EGO_VOICE_MAX_TOKENS=64 para ~5–6 s."""
    raw = read_env("EGO_VOICE_MAX_TOKENS", "96")
    try:
        return max(64, min(420, int(raw)))
    except ValueError:
        return 96


def voice_stream_enabled() -> bool:
    """Streaming NDJSON em /chat/voice/stream (texto aparece enquanto o Gemini gera)."""
    raw = read_env("EGO_VOICE_STREAM", "1").strip().lower()
    return raw not in ("0", "false", "no", "nao", "não")


def chat_local_history_enabled() -> bool:
    """Conversas no aparelho; servidor não grava chat_history."""
    raw = read_env("EGO_CHAT_LOCAL_HISTORY", "1").strip().lower()
    return raw not in ("0", "false", "no", "nao", "não")


def monthly_token_limit(is_pro: bool) -> int:
    """Legado — prefira ego_api.plans.plan_limits()."""
    return EGO_MONTHLY_TOKEN_LIMIT_PRO if is_pro else EGO_MONTHLY_TOKEN_LIMIT_FREE
