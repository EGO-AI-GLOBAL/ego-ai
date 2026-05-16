"""
Ego-AI — painel Streamlit: Google Gemini (Google AI Studio), chat com PDFs e lembretes.
"""

from __future__ import annotations

import base64
import datetime
import hashlib
import html
import json
import os
import re
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlparse, urlunparse

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None  # type: ignore[misc, assignment]

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

import requests
import streamlit as st

try:
    import tiktoken
except ImportError:
    tiktoken = None  # type: ignore[misc, assignment]

try:
    from legal_copy import (
        privacy_policy_markdown,
        refund_policy_markdown,
        terms_of_use_markdown,
    )
except ImportError:

    def terms_of_use_markdown() -> str:
        return "Termos: adicione `legal_copy.py` ao projeto."

    def privacy_policy_markdown() -> str:
        return "Privacidade: adicione `legal_copy.py` ao projeto."

    def refund_policy_markdown() -> str:
        return "Reembolso: adicione `legal_copy.py` ao projeto."


try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None  # type: ignore[misc, assignment]

try:
    from ego_supabase import Client, create_client
except ImportError:
    try:
        from supabase import Client, create_client
    except ImportError:
        Client = None  # type: ignore[misc, assignment]
        create_client = None  # type: ignore[misc, assignment]

try:
    from langdetect import DetectorFactory, LangDetectException, detect, detect_langs
except ImportError:
    DetectorFactory = None  # type: ignore[misc, assignment]
    LangDetectException = Exception  # type: ignore[misc, assignment]
    detect = None  # type: ignore[misc, assignment]
    detect_langs = None  # type: ignore[misc, assignment]

GEMINI_SYSTEM_INSTRUCTION = """\
Você é o EGO-AI, o assistente pessoal e amigo mais leal do utilizador. A sua voz e escrita devem ser \
acolhedoras, empáticas, inteligentes e focadas no bem-estar mental e emocional de quem fala consigo. \
Se a pessoa estiver sozinha ou a desabafar, ouça com a sensibilidade de um conselheiro: validação, \
escuta ativa e sugestões práticas e breves — nunca julgamentos. Nunca soe como um robô rígido ou burocrático. \
Detete o idioma do utilizador e responda sempre no mesmo idioma. Seja conciso e seguro (sem aconselhamento \
médico/legal definitivo; encaminhe a profissionais quando necessário).
"""

AGENDA_HORIZON_DAYS = int(os.getenv("EGO_AGENDA_HORIZON_DAYS", "90"))
AGENDA_HORIZON_HOURS = AGENDA_HORIZON_DAYS * 24

REMINDER_LLM_INSTRUCTION = f"""
REMINDERS / ALARMS: If the user asks for a reminder, alarm, meeting, or important call at a specific time,
you may register it by adding EXACTLY ONE line at the very END of your reply (after your normal answer), with this format:
[[EGO_REMINDER:{{"title":"short title","scheduled_at":"ISO-8601 datetime WITH timezone offset","announce":"what to say at the first alarm (10 min before)"}}]]
- scheduled_at is the moment the event happens (e.g. time of the call), NOT the first alarm time.
- The app notifies starting 10 minutes before, then every 5 minutes until that moment.
- Agenda window: only schedule between now and the next {AGENDA_HORIZON_DAYS} days (reject beyond that).
- If the user omits the year, use the current calendar year; if that date/time already passed, use the next year.
- If the user omits the month, use the current month.
- Always output scheduled_at as full ISO-8601 with timezone offset after resolving year/month/day/time.
- If date/time is still ambiguous, do NOT add the line; ask one short clarifying question instead.
- When the user clearly wants a reminder/alarm at a known time, you MUST output the [[EGO_REMINDER:...]] line automatically.
  Do NOT ask whether to turn on the alarm, wait for confirmation, or offer to "activate" it — the app registers the line as soon as you send it.
"""

AGENDA_RECURRING_LLM_INSTRUCTION = """
AGENDA / MEETINGS (Supabase — each user only sees their own rows via user_id):

A) ONE-OFF meetings / reuniões / calls with a specific calendar date and time
   (e.g. "reunião amanhã às 15h", "meeting on June 5 at 3pm"):
   → use [[EGO_REMINDER:{"title":"...","scheduled_at":"ISO-8601 with timezone offset","announce":"..."}]]
   at the END of your reply. This saves to table `reminders` for THAT user only.

B) WEEKLY recurring habits (same weekdays every week, no single calendar date):
   (e.g. "academia segunda a sexta às 8h"):
   → use [[EGO_AGENDA:{"titulo":"short title","horario":"HH:MM","dias_da_semana":"seg,ter,qua,qui,sex"}]]
   at the END of your reply. This saves to table `agenda` for THAT user only.

Rules for [[EGO_AGENDA:...]]:
- dias_da_semana: lowercase Portuguese 3-letter codes: seg, ter, qua, qui, sex, sab, dom (comma-separated).
- horario: 24h HH:MM (e.g. 08:00, 15:30).
- When date+time are clear for a single meeting → use EGO_REMINDER, NOT EGO_AGENDA.
- When weekdays+time are clear for recurrence → use EGO_AGENDA automatically; do NOT ask to confirm saving.

READING THE USER'S CALENDAR:
- Below you receive a block "CURRENT USER AGENDA" loaded live from Supabase for THIS user only.
- ALWAYS use that block when the user asks what they have scheduled, conflicts, free time, or "my agenda".
- Do NOT invent meetings not listed there. If the block says (none), say the calendar is empty.
- Before adding [[EGO_REMINDER:...]] or [[EGO_AGENDA:...]], check the snapshot to avoid duplicate entries unless the user wants to replace one.
"""


def reminder_instruction_block() -> str:
    return REMINDER_LLM_INSTRUCTION


def agenda_instruction_block() -> str:
    return AGENDA_RECURRING_LLM_INSTRUCTION


# Motor principal pedido: gemini-1.5-flash (rápido). Se a API devolver 404, o código faz fallback para 2.5.
GEMINI_MODEL_FLASH = os.getenv("EGO_GEMINI_MODEL_FLASH", "gemini-1.5-flash")
GEMINI_MODEL_PRO = os.getenv("EGO_GEMINI_MODEL_PRO", "gemini-2.5-pro")
GEMINI_MODEL_IDS = (GEMINI_MODEL_FLASH, GEMINI_MODEL_PRO)

# Trecho dos PDFs na instrução de sistema (Gemini).
PDF_CONTEXT_IN_SYSTEM_CHARS = int(os.getenv("EGO_PDF_CONTEXT_CHARS", "3000"))
PDF_EXTRACT_MAX_CHARS = int(os.getenv("EGO_PDF_EXTRACT_MAX_CHARS", "120000"))
PDF_EXTRACT_MAX_PAGES = int(os.getenv("EGO_PDF_EXTRACT_MAX_PAGES", "24"))
SUPABASE_STORAGE_BUCKET = "usuarios"
SUPABASE_HISTORY_TABLE = "chat_history"
SUPABASE_PROFILES_TABLE = "profiles"
SUPABASE_FEEDBACK_TABLE = "message_feedback"
SUPABASE_PERSONA_TABLE = "user_personas"
SUPABASE_REMINDERS_TABLE = "reminders"
SUPABASE_AGENDA_TABLE = "agenda"
EGO_SCHEMA_TABLE_SPECS: tuple[tuple[str, str], ...] = (
    ("Perfil e preferências", SUPABASE_PROFILES_TABLE),
    ("Histórico do chat", SUPABASE_HISTORY_TABLE),
    ("Lembretes", SUPABASE_REMINDERS_TABLE),
    ("Agenda recorrente", SUPABASE_AGENDA_TABLE),
    ("Avatar e voz", SUPABASE_PERSONA_TABLE),
)
VALID_AGENDA_DOW = frozenset({"seg", "ter", "qua", "qui", "sex", "sab", "dom"})
DOW_PT_ORDER = ("seg", "ter", "qua", "qui", "sex", "sab", "dom")
REMINDER_MINUTES_BEFORE = 10
REMINDER_NUDGE_MINUTES = 5
REMINDER_PAST_GRACE = datetime.timedelta(minutes=5)
STRIPE_MENSAL_URL = os.getenv("STRIPE_CHECKOUT_MENSAL_URL", "URL_DO_STRIPE_MENSAL")
STRIPE_ANUAL_URL = os.getenv("STRIPE_CHECKOUT_ANUAL_URL", "URL_DO_STRIPE_ANUAL")
# Trial: dias após created_at em profiles (ajuste com EGO_TRIAL_DAYS). Beta: EGO_BETA_DEADLINE ISO libera todos não-Pro até a data.
EGO_TRIAL_DAYS = int(os.getenv("EGO_TRIAL_DAYS", "20"))
PAYWALL_PRECO_MENSAL = os.getenv("EGO_PAYWALL_MENSAL_LABEL", "R$ 29,90")
PAYWALL_PRECO_ANUAL = os.getenv("EGO_PAYWALL_ANUAL_LABEL", "R$ 299,00")
# Tokens mensais (tiktoken, aprox.): 0 = ilimitado. Contagem por turno (pergunta + resposta).
EGO_MONTHLY_TOKEN_LIMIT_FREE = int(os.getenv("EGO_MONTHLY_TOKEN_LIMIT_FREE", "500000"))
EGO_MONTHLY_TOKEN_LIMIT_PRO = int(os.getenv("EGO_MONTHLY_TOKEN_LIMIT_PRO", "10000000"))
EGO_APP_VERSION = os.getenv("EGO_APP_VERSION", "v1.5.0 — Global Stable")
CHAT_LLM_MAX_TURNS = int(os.getenv("EGO_CHAT_LLM_MAX_TURNS", "24"))
LOCAL_AUTH_VERSION = 1
EGO_BROWSER_AUTH_STORAGE_KEY = "ego_auth_v1"
EGO_AUTOSAVE_MIN_INTERVAL_SEC = int(os.getenv("EGO_AUTOSAVE_MIN_INTERVAL_SEC", "45"))

# Persistência de UI + PDF em profiles.ui_state (jsonb). Ver profiles_ui_state.sql no Supabase.
UI_STATE_VERSION = 1
UI_STATE_PDF_MAX_CHARS = int(os.getenv("EGO_UI_STATE_PDF_MAX_CHARS", "800000"))
ALLOWED_EGO_NAV_VALUES = frozenset(
    {
        "Chat",
        "Políticas",
        "Agenda e lembretes",
        "Meu Perfil",
        "Meu Avatar",
    }
)


def _ego_read_secret(name: str) -> str:
    raw = (os.getenv(name) or "").strip()
    if raw:
        return raw
    if hasattr(st, "secrets"):
        try:
            return str(st.secrets.get(name, "") or "").strip()
        except Exception:
            return ""
    return ""


def effective_gemini_api_key() -> str:
    """Chave do campo da barra lateral ou variável/secrets (Google AI Studio)."""
    k = (st.session_state.get("_ego_gemini_key") or "").strip()
    if k:
        return k
    return _ego_read_secret("GOOGLE_API_KEY") or _ego_read_secret("GEMINI_API_KEY")


def ego_operator_legal_name() -> str:
    return (
        _ego_read_secret("EGO_OPERATOR_LEGAL_NAME")
        or _ego_read_secret("EGO_COMPANY_LEGAL_NAME")
        or "Configure EGO_OPERATOR_LEGAL_NAME nos secrets"
    )


def ego_support_email() -> str:
    return _ego_read_secret("EGO_SUPPORT_EMAIL") or "suporte@egoai.com.br"


def _ego_beta_deadline() -> datetime.datetime | None:
    """Se definido (ISO 8601), não-Pro tem acesso até essa data/hora (ex.: teste 48h com 100 pessoas)."""
    raw = (os.getenv("EGO_BETA_DEADLINE") or "").strip()
    if not raw and hasattr(st, "secrets"):
        try:
            raw = str(st.secrets.get("EGO_BETA_DEADLINE", "") or "").strip()
        except Exception:
            raw = ""
    if not raw:
        return None
    try:
        dt = datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt
    except ValueError:
        return None


def _ego_beta_sem_limite() -> bool:
    """
    Se EGO_BETA_SEM_LIMITE=1 (env ou secrets): não-Pro usa app sem limite diário de mensagens
    e sem expirar trial (até você desligar — ex.: enquanto a Stripe não libera).
    """
    raw = (os.getenv("EGO_BETA_SEM_LIMITE") or "").strip().lower()
    if raw in ("1", "true", "yes", "sim"):
        return True
    if hasattr(st, "secrets"):
        try:
            s = str(st.secrets.get("EGO_BETA_SEM_LIMITE", "") or "").strip().lower()
            return s in ("1", "true", "yes", "sim")
        except Exception:
            pass
    return False

# Grátis: 1 avatar homem + 1 mulher (m1, f1). Demais só com Pro (catálogo mantém estilos para o futuro).
AVATAR_OPTIONS = [
    {"id": "m1", "name": "Leo", "group": "Homem", "premium": False},
    {"id": "m2", "name": "Caio", "group": "Homem", "premium": True},
    {"id": "m3", "name": "Noah", "group": "Homem", "premium": True},
    {"id": "m4", "name": "Enzo", "group": "Homem", "premium": True},
    {"id": "m5", "name": "Theo", "group": "Homem", "premium": True},
    {"id": "m6", "name": "Ravi", "group": "Homem", "premium": True},
    {"id": "m7", "name": "Davi", "group": "Homem", "premium": True},
    {"id": "m8", "name": "Alex", "group": "Homem", "premium": True},
    {"id": "m9", "name": "Bruno", "group": "Homem", "premium": True},
    {"id": "m10", "name": "Mateo", "group": "Homem", "premium": True},
    {"id": "f1", "name": "Luna", "group": "Mulher", "premium": False},
    {"id": "f2", "name": "Aurora", "group": "Mulher", "premium": True},
    {"id": "f3", "name": "Sofia", "group": "Mulher", "premium": True},
    {"id": "f4", "name": "Valentina", "group": "Mulher", "premium": True},
    {"id": "f5", "name": "Isis", "group": "Mulher", "premium": True},
    {"id": "f6", "name": "Helena", "group": "Mulher", "premium": True},
    {"id": "f7", "name": "Nina", "group": "Mulher", "premium": True},
    {"id": "f8", "name": "Maya", "group": "Mulher", "premium": True},
    {"id": "f9", "name": "Bianca", "group": "Mulher", "premium": True},
    {"id": "f10", "name": "Clara", "group": "Mulher", "premium": True},
    {"id": "pm1", "name": "Atlas Premium", "group": "Homem", "premium": True},
    {"id": "pf1", "name": "Ayla Premium", "group": "Mulher", "premium": True},
]
FREE_AVATAR_IDS = frozenset({"m1", "f1"})
FREE_VOICE_IDS = frozenset({"vm1", "vf1"})

# Grátis: 1 voz masculina + 1 feminina; demais Pro.
VOICE_OPTIONS = [
    {"id": "vm1", "name": "Bruno PT-BR", "group": "Masculina", "premium": False},
    {"id": "vm2", "name": "Rafael PT-BR", "group": "Masculina", "premium": True},
    {"id": "vm3", "name": "Gustavo PT-BR", "group": "Masculina", "premium": True},
    {"id": "vm4", "name": "Caio PT-BR", "group": "Masculina", "premium": True},
    {"id": "vm5", "name": "Daniel PT-BR", "group": "Masculina", "premium": True},
    {"id": "vm6", "name": "Henrique PT-BR", "group": "Masculina", "premium": True},
    {"id": "vm7", "name": "Levi EN-US", "group": "Masculina", "premium": True},
    {"id": "vm8", "name": "Noah EN-US", "group": "Masculina", "premium": True},
    {"id": "vm9", "name": "Liam EN-US", "group": "Masculina", "premium": True},
    {"id": "vm10", "name": "Mason EN-US", "group": "Masculina", "premium": True},
    {"id": "vf1", "name": "Ana PT-BR", "group": "Feminina", "premium": False},
    {"id": "vf2", "name": "Beatriz PT-BR", "group": "Feminina", "premium": True},
    {"id": "vf3", "name": "Livia PT-BR", "group": "Feminina", "premium": True},
    {"id": "vf4", "name": "Helena PT-BR", "group": "Feminina", "premium": True},
    {"id": "vf5", "name": "Maya PT-BR", "group": "Feminina", "premium": True},
    {"id": "vf6", "name": "Cecilia PT-BR", "group": "Feminina", "premium": True},
    {"id": "vf7", "name": "Aria EN-US", "group": "Feminina", "premium": True},
    {"id": "vf8", "name": "Ava EN-US", "group": "Feminina", "premium": True},
    {"id": "vf9", "name": "Emma EN-US", "group": "Feminina", "premium": True},
    {"id": "vf10", "name": "Zoe EN-US", "group": "Feminina", "premium": True},
    {"id": "pvm1", "name": "Titan Studio", "group": "Masculina", "premium": True},
    {"id": "pvf1", "name": "Nova Studio", "group": "Feminina", "premium": True},
]

# Vozes Microsoft Edge TTS (servidor → st.audio, fiável no Streamlit).
EDGE_TTS_VOICE_MAP: dict[str, str] = {
    "vm1": "pt-BR-AntonioNeural",
    "vm2": "pt-BR-DonatoNeural",
    "vm3": "pt-BR-FabioNeural",
    "vm4": "pt-BR-HumbertoNeural",
    "vm5": "pt-BR-JulioNeural",
    "vm6": "pt-BR-NicolauNeural",
    "vm7": "en-US-GuyNeural",
    "vm8": "en-US-ChristopherNeural",
    "vm9": "en-US-EricNeural",
    "vm10": "en-US-RogerNeural",
    "vf1": "pt-BR-FranciscaNeural",
    "vf2": "pt-BR-BrendaNeural",
    "vf3": "pt-BR-ThalitaNeural",
    "vf4": "pt-BR-YaraNeural",
    "vf5": "pt-BR-LeilaNeural",
    "vf6": "pt-BR-GiovannaNeural",
    "vf7": "en-US-JennyNeural",
    "vf8": "en-US-AriaNeural",
    "vf9": "en-US-EmmaNeural",
    "vf10": "en-US-MichelleNeural",
    "pvm1": "en-US-DavisNeural",
    "pvf1": "en-US-AmberNeural",
}
DEFAULT_EDGE_TTS_VOICE = "pt-BR-FranciscaNeural"


def inject_styles() -> None:
    if st.session_state.get("_ego_styles_injected"):
        return
    st.session_state["_ego_styles_injected"] = True
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,600;0,9..40,700&display=swap');
            .stApp { background-color: #0E1117; color: #FFFFFF; }
            html, body, [class*="css"] {
                font-family: 'DM Sans', 'Segoe UI', system-ui, sans-serif;
            }
            .block-container {
                padding-top: 1.25rem;
                padding-bottom: 4.5rem;
                max-width: 1200px;
            }
            .ego-hero {
                background: linear-gradient(135deg, #1a1025 0%, #0f0f12 50%, #0d1520 100%);
                border: 1px solid rgba(124, 58, 237, 0.25);
                border-radius: 16px;
                padding: 1.5rem 1.75rem;
                margin-bottom: 1.5rem;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);
            }
            .ego-hero h1 {
                margin: 0 0 0.35rem 0;
                font-size: 1.65rem;
                font-weight: 700;
                letter-spacing: -0.02em;
                background: linear-gradient(90deg, #e8e8ed, #c4b5fd);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            .ego-hero p {
                margin: 0;
                color: #9ca3af;
                font-size: 0.95rem;
            }
            .ego-card {
                background: linear-gradient(165deg, #1e1e28 0%, #16161d 100%);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 14px;
                padding: 1.15rem 1.25rem;
                min-height: 140px;
                box-shadow: 0 4px 24px rgba(0, 0, 0, 0.25);
                transition: border-color 0.2s ease, box-shadow 0.2s ease;
            }
            .ego-card:hover {
                border-color: rgba(124, 58, 237, 0.35);
                box-shadow: 0 8px 28px rgba(124, 58, 237, 0.12);
            }
            .ego-card-title {
                font-size: 0.72rem;
                text-transform: uppercase;
                letter-spacing: 0.12em;
                color: #a78bfa;
                font-weight: 600;
                margin-bottom: 0.65rem;
            }
            .ego-card ul {
                margin: 0;
                padding-left: 1.1rem;
                color: #d1d5db;
                font-size: 0.88rem;
                line-height: 1.55;
            }
            .ego-card li { margin-bottom: 0.35rem; }
            .ego-chat-wrap {
                margin-top: 2rem;
                padding-top: 1.25rem;
                border-top: 1px solid rgba(255, 255, 255, 0.08);
            }
            .ego-chat-wrap h3 {
                font-size: 1rem;
                font-weight: 600;
                color: #e8e8ed;
                margin-bottom: 0.75rem;
            }
            .ego-brand-min {
                font-size: 0.68rem;
                letter-spacing: 0.2em;
                text-transform: uppercase;
                color: #94a3b8;
                margin: 0 0 0.5rem 0;
            }
            div[data-testid="stChatMessage"] { margin-bottom: 0.45rem !important; }
            div[data-testid="stSidebar"] {
                border-right: 1px solid rgba(255, 255, 255, 0.06);
                background: linear-gradient(
                    180deg,
                    rgba(22, 24, 32, 0.95) 0%,
                    rgba(14, 17, 23, 0.98) 100%
                ) !important;
            }
            .ego-chat-scroll {
                border: 1px solid rgba(255, 255, 255, 0.07);
                border-radius: 16px;
                background: rgba(10, 10, 14, 0.55);
                padding: 0.85rem 0.75rem 1rem;
                margin-bottom: 0.75rem;
            }
            .ego-chat-row {
                display: flex;
                width: 100%;
                margin-bottom: 0.65rem;
            }
            .ego-chat-row.user { justify-content: flex-end; }
            .ego-chat-row.assistant { justify-content: flex-start; }
            .ego-bubble {
                max-width: min(82%, 640px);
                border-radius: 16px;
                padding: 0.65rem 0.85rem;
                line-height: 1.45;
                font-size: 0.92rem;
                box-shadow: 0 6px 22px rgba(0, 0, 0, 0.28);
                border: 1px solid rgba(255, 255, 255, 0.08);
                word-wrap: break-word;
            }
            .ego-bubble.user {
                background: #2D5AFE;
                border-color: #1E40AF;
                color: #f3f4f6;
            }
            .ego-bubble.assistant {
                background: #1E2633;
                border-color: #384455;
                color: #e5e7eb;
            }
            .ego-bubble .ego-meta {
                font-size: 0.68rem;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                opacity: 0.65;
                margin-bottom: 0.35rem;
            }
            .ego-bubble .ego-body { white-space: pre-wrap; }
            .stChatMessage {
                border-radius: 15px;
                padding: 10px;
                margin-bottom: 10px;
            }
            [data-testid="stChatMessageAssistant"] {
                background-color: #1E2633;
                border: 1px solid #384455;
            }
            [data-testid="stChatMessageUser"] {
                background-color: #2D5AFE;
                border: 1px solid #1E40AF;
            }
            .stButton>button {
                width: 100%;
                border-radius: 20px;
                background-color: #2D5AFE;
                color: #FFFFFF;
                transition: 0.3s;
                border: none;
            }
            .stButton>button:hover {
                background-color: #1E40AF;
                transform: scale(1.02);
            }
            .ego-glass-panel {
                background: rgba(28, 28, 38, 0.42);
                backdrop-filter: blur(16px);
                -webkit-backdrop-filter: blur(16px);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 20px;
                padding: 1.35rem 1.5rem;
                margin-bottom: 1.35rem;
                box-shadow: 0 12px 40px rgba(0, 0, 0, 0.35),
                    inset 0 1px 0 rgba(255, 255, 255, 0.06);
            }
            .ego-glass-panel h3 {
                margin: 0 0 0.5rem 0;
                font-size: 1.35rem;
                font-weight: 700;
                background: linear-gradient(90deg, #f5f3ff, #c4b5fd);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            .ego-glass-panel p, .ego-glass-panel li {
                color: #c4c9d4;
                font-size: 0.92rem;
                line-height: 1.55;
            }
            .ego-glass-cta {
                display: inline-block;
                margin-top: 0.5rem;
                padding: 0.45rem 0.9rem;
                border-radius: 999px;
                background: rgba(124, 58, 237, 0.35);
                border: 1px solid rgba(167, 139, 250, 0.45);
                color: #ede9fe;
                font-size: 0.82rem;
                font-weight: 600;
            }
            .ego-trust-footer-glass {
                margin-top: 2rem;
                padding: 1rem 1.2rem 1.15rem;
                border-radius: 18px;
                background: rgba(18, 20, 28, 0.55);
                backdrop-filter: blur(14px);
                -webkit-backdrop-filter: blur(14px);
                border: 1px solid rgba(255, 255, 255, 0.08);
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.28);
            }
            .ego-footer-copy {
                margin: 0;
                font-size: 0.84rem;
                color: #cbd5e1;
                line-height: 1.45;
            }
            .ego-footer-links { font-size: 0.78rem; color: #94a3b8; }
            .ego-version-badge {
                display: inline-block;
                font-size: 0.68rem;
                font-weight: 600;
                letter-spacing: 0.04em;
                padding: 0.28rem 0.65rem;
                border-radius: 999px;
                background: rgba(124, 58, 237, 0.22);
                border: 1px solid rgba(167, 139, 250, 0.4);
                color: #e9d5ff;
                margin-bottom: 0.65rem;
            }
            .ego-page-hero {
                background: linear-gradient(135deg, #1a1025 0%, #12121a 55%, #0d1520 100%);
                border: 1px solid rgba(124, 58, 237, 0.28);
                border-radius: 18px;
                padding: 1.35rem 1.5rem;
                margin-bottom: 1.25rem;
                box-shadow: 0 10px 36px rgba(0, 0, 0, 0.32);
            }
            .ego-page-hero h1 {
                margin: 0 0 0.35rem 0;
                font-size: 1.55rem;
                font-weight: 700;
                color: #f3f4f6;
                letter-spacing: -0.02em;
            }
            .ego-page-hero p {
                margin: 0;
                color: #94a3b8;
                font-size: 0.9rem;
                line-height: 1.5;
            }
            .ego-section-head {
                font-size: 0.72rem;
                text-transform: uppercase;
                letter-spacing: 0.14em;
                color: #a78bfa;
                font-weight: 700;
                margin: 1.25rem 0 0.65rem 0;
            }
            .ego-form-shell {
                background: linear-gradient(165deg, rgba(30, 30, 40, 0.9) 0%, rgba(18, 18, 26, 0.95) 100%);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 16px;
                padding: 1rem 1.15rem 0.35rem;
                margin-bottom: 1.1rem;
            }
            .ego-reminder-list {
                display: flex;
                flex-direction: column;
                gap: 0.75rem;
                margin: 0.5rem 0 1rem 0;
            }
            .ego-reminder-card {
                display: grid;
                grid-template-columns: auto 1fr;
                gap: 0.85rem 1rem;
                align-items: start;
                background: linear-gradient(145deg, #1e2433 0%, #161b26 100%);
                border: 1px solid rgba(255, 255, 255, 0.07);
                border-left: 3px solid #7c3aed;
                border-radius: 14px;
                padding: 0.95rem 1.1rem;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.22);
            }
            .ego-reminder-card.is-today {
                border-left-color: #38bdf8;
                background: linear-gradient(145deg, #1a2438 0%, #141c2a 100%);
            }
            .ego-reminder-card.is-soon {
                border-left-color: #fbbf24;
            }
            .ego-reminder-when {
                text-align: center;
                min-width: 3.6rem;
                padding: 0.35rem 0.5rem;
                border-radius: 12px;
                background: rgba(124, 58, 237, 0.18);
                border: 1px solid rgba(167, 139, 250, 0.25);
            }
            .ego-reminder-when .ego-r-time {
                display: block;
                font-size: 1.15rem;
                font-weight: 700;
                color: #f5f3ff;
                line-height: 1.1;
            }
            .ego-reminder-when .ego-r-date {
                display: block;
                font-size: 0.68rem;
                color: #c4b5fd;
                margin-top: 0.2rem;
                text-transform: uppercase;
                letter-spacing: 0.06em;
            }
            .ego-reminder-body .ego-r-title {
                font-size: 1.02rem;
                font-weight: 600;
                color: #f3f4f6;
                margin: 0 0 0.35rem 0;
                line-height: 1.3;
            }
            .ego-reminder-body .ego-r-announce {
                font-size: 0.86rem;
                color: #9ca3af;
                margin: 0 0 0.45rem 0;
                line-height: 1.45;
            }
            .ego-reminder-meta {
                display: flex;
                flex-wrap: wrap;
                gap: 0.35rem;
                align-items: center;
            }
            .ego-pill {
                display: inline-block;
                font-size: 0.68rem;
                font-weight: 600;
                letter-spacing: 0.04em;
                padding: 0.22rem 0.55rem;
                border-radius: 999px;
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.1);
                color: #d1d5db;
            }
            .ego-pill.rel { background: rgba(56, 189, 248, 0.15); border-color: rgba(56, 189, 248, 0.35); color: #bae6fd; }
            .ego-pill.snooze { background: rgba(251, 191, 36, 0.12); border-color: rgba(251, 191, 36, 0.35); color: #fde68a; }
            .ego-pill.recurring { background: rgba(52, 211, 153, 0.12); border-color: rgba(52, 211, 153, 0.3); color: #a7f3d0; }
            .ego-agenda-card {
                background: linear-gradient(145deg, #1a2228 0%, #141a20 100%);
                border: 1px solid rgba(255, 255, 255, 0.07);
                border-left: 3px solid #34d399;
                border-radius: 14px;
                padding: 0.85rem 1rem;
                margin-bottom: 0.65rem;
            }
            .ego-agenda-card .ego-a-title {
                font-size: 0.98rem;
                font-weight: 600;
                color: #ecfdf5;
                margin: 0 0 0.4rem 0;
            }
            .ego-agenda-card .ego-a-row {
                display: flex;
                flex-wrap: wrap;
                gap: 0.35rem;
                align-items: center;
            }
            .ego-dow-chip {
                display: inline-block;
                font-size: 0.65rem;
                font-weight: 600;
                padding: 0.18rem 0.45rem;
                border-radius: 6px;
                background: rgba(52, 211, 153, 0.15);
                border: 1px solid rgba(52, 211, 153, 0.28);
                color: #a7f3d0;
            }
            .ego-alarm-banner {
                background: linear-gradient(135deg, rgba(124, 58, 237, 0.35) 0%, rgba(45, 90, 254, 0.25) 100%);
                border: 1px solid rgba(167, 139, 250, 0.45);
                border-radius: 16px;
                padding: 1rem 1.15rem;
                margin-bottom: 0.85rem;
                box-shadow: 0 8px 28px rgba(124, 58, 237, 0.2);
            }
            .ego-alarm-banner .ego-alarm-tag {
                font-size: 0.65rem;
                text-transform: uppercase;
                letter-spacing: 0.12em;
                color: #e9d5ff;
                font-weight: 700;
                margin-bottom: 0.35rem;
            }
            .ego-alarm-banner .ego-alarm-title {
                font-size: 1.05rem;
                font-weight: 700;
                color: #fff;
                margin: 0 0 0.35rem 0;
            }
            .ego-alarm-banner .ego-alarm-sub {
                font-size: 0.88rem;
                color: #e0e7ff;
                margin: 0;
                line-height: 1.45;
            }
            .ego-empty-state {
                text-align: center;
                padding: 1.5rem 1rem;
                border-radius: 14px;
                border: 1px dashed rgba(255, 255, 255, 0.12);
                background: rgba(255, 255, 255, 0.02);
                color: #94a3b8;
                font-size: 0.9rem;
                line-height: 1.5;
                margin: 0.5rem 0 1rem 0;
            }
            div[data-testid="stVerticalBlock"] > div:has(.ego-reminder-card) + div[data-testid="stHorizontalBlock"] {
                margin-top: -0.35rem;
                margin-bottom: 0.65rem;
            }
            .ego-tts-controls-hint {
                font-size: 0.78rem;
                color: #94a3b8;
                margin: 0.15rem 0 0.35rem 0;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_session() -> None:
    """Garante chaves estáveis no session_state (persistem entre reruns e widgets da sidebar)."""
    st.session_state.setdefault("messages", [])
    if not isinstance(st.session_state.messages, list):
        st.session_state.messages = []
    st.session_state.setdefault("user_name", "")
    st.session_state.setdefault("gemini_model_ok", None)
    st.session_state.setdefault("gemini_model_preference", GEMINI_MODEL_FLASH)
    _gm_ok = (st.session_state.get("gemini_model_ok") or "") if isinstance(st.session_state.get("gemini_model_ok"), str) else ""
    _gm_pref = st.session_state.get("gemini_model_preference") or ""
    if _gm_ok and ("gemini-1.5" in _gm_ok or "gemini-2" in _gm_ok and _gm_ok not in GEMINI_MODEL_IDS):
        st.session_state["gemini_model_ok"] = None
    if _gm_pref not in GEMINI_MODEL_IDS:
        st.session_state["gemini_model_preference"] = GEMINI_MODEL_FLASH
    st.session_state.setdefault("pdf_context", "")
    st.session_state["ego_ai_provider"] = "Gemini"
    st.session_state.setdefault("user_logged", False)
    st.session_state.setdefault("global_user_name", "")
    st.session_state.setdefault("auth_user_id", "")
    st.session_state.setdefault("history_loaded", False)
    st.session_state.setdefault("user", None)
    st.session_state.setdefault("ego_nav", "Chat")
    if st.session_state.get("ego_nav") == "Jurídico":
        st.session_state["ego_nav"] = "Políticas"
    _legacy_nav = {
        "Comida Perto",
        "Bares e restaurantes",
        "Bebidas Perto",
        "Compras online",
        "Viagens e hospedagem",
        "Conexões (e-mail, redes, CRM)",
    }
    if st.session_state.get("ego_nav") in _legacy_nav:
        st.session_state["ego_nav"] = "Chat"
    st.session_state.setdefault("supabase_url_input", "")
    st.session_state.setdefault("supabase_key_input", "")
    st.session_state.setdefault("local_mode", False)
    st.session_state.setdefault("last_detected_language", "pt-BR")
    st.session_state.setdefault("last_detected_confidence", 0.0)
    st.session_state.setdefault("_ego_rem_fired", {})
    st.session_state.setdefault("ego_legal_tab", 0)
    st.session_state.setdefault("_legal_render_id", 0)
    st.session_state.setdefault("ego_login_policies", False)
    st.session_state.setdefault("persona_loaded", False)
    st.session_state.setdefault("assistant_avatar_id", "f1")
    st.session_state.setdefault("assistant_voice_id", "vf1")
    st.session_state.setdefault("ego_ui_state_loaded", False)
    st.session_state.setdefault("_ego_ui_state_saved_sig", "")
    st.session_state.setdefault("_ego_session_boot_done", False)
    st.session_state.setdefault("_ego_voice_done_sig", None)
    st.session_state.setdefault("_ego_last_autosave_ts", 0.0)
    st.session_state.setdefault("ego_voice_replies", True)
    st.session_state.setdefault("ego_tts_volume", 80)
    st.session_state.setdefault("ego_tts_muted", False)
    st.session_state.setdefault("ego_tts_rate", 1.0)
    st.session_state.setdefault("ego_client_timezone", "")
    st.session_state.setdefault("ego_client_tz_offset_min", None)
    st.session_state.setdefault("_ego_tz_injected", False)
    st.session_state.setdefault("ego_assistant_display_name", "EGO-AI")
    st.session_state.setdefault("ego_name_setup_done", False)
    st.session_state.setdefault(
        "ego_assistant_display_name_input",
        st.session_state.get("ego_assistant_display_name") or "EGO-AI",
    )
    st.session_state.setdefault("ego_remember_device", True)
    st.session_state.setdefault("_ego_sb_access", "")
    st.session_state.setdefault("_ego_sb_refresh", "")
    if "login_email" not in st.session_state:
        last_em = _read_last_login_email_local()
        if last_em:
            st.session_state["login_email"] = last_em


def _supabase_project_url_ok(url: str) -> bool:
    """
    URL real do projeto: https://<ref>.supabase.co
    Rejeita o erro comum https://supabase.co (sem subdomínio do projeto).
    """
    u = (url or "").strip().rstrip("/")
    if not u.startswith("https://"):
        return False
    try:
        host = (urlparse(u).hostname or "").lower()
    except Exception:
        return False
    if host in ("", "supabase.co", "www.supabase.co"):
        return False
    if not host.endswith(".supabase.co"):
        return False
    # ex.: abcdefghijk.supabase.co
    ref = host[: -len(".supabase.co")]
    return bool(ref) and "." not in ref


def _supabase_ref_from_url(url: str) -> str | None:
    u = (url or "").strip().rstrip("/")
    if not _supabase_project_url_ok(u):
        return None
    host = (urlparse(u).hostname or "").lower()
    return host[: -len(".supabase.co")]


def _supabase_is_publishable_key(key: str) -> bool:
    return (key or "").strip().startswith("sb_publishable_")


def _supabase_ref_from_jwt_key(key: str) -> str | None:
    """Extrai o project ref embutido na chave legada anon (JWT eyJ...)."""
    try:
        parts = (key or "").strip().split(".")
        if len(parts) < 2:
            return None
        payload = parts[1]
        pad = "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload + pad))
        ref = data.get("ref")
        return str(ref).strip() if ref else None
    except Exception:
        return None


def _resolve_supabase_url() -> str:
    """Project URL: .env (SUPABASE_URL) → secrets.toml → formulário da app."""
    url = os.getenv("SUPABASE_URL", "").strip()
    if not url:
        url = _safe_streamlit_secret("SUPABASE_URL")
    if not url:
        url = (st.session_state.get("supabase_url_input") or "").strip()
    return url


def _resolve_supabase_api_key() -> str:
    """Chave publishable/anon: .env (SUPABASE_KEY) → secrets.toml → formulário."""
    key = os.getenv("SUPABASE_KEY", "").strip() or os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()
    if not key:
        key = _safe_streamlit_secret("SUPABASE_KEY") or _safe_streamlit_secret("SUPABASE_PUBLISHABLE_KEY")
    if not key:
        key = (st.session_state.get("supabase_key_input") or "").strip()
    return key


def _supabase_api_key_looks_valid(key: str) -> bool:
    k = (key or "").strip()
    if _supabase_is_publishable_key(k) and len(k) > 24:
        return True
    if k.startswith("eyJ") and len(k) > 40:
        return True
    return False


def _safe_streamlit_secret(name: str, default: str = "") -> str:
    """Lê st.secrets sem derrubar a app se secrets.toml estiver mal formatado."""
    if not hasattr(st, "secrets"):
        return default
    try:
        return str(st.secrets.get(name, default) or default).strip()
    except Exception:
        return default


def _peek_supabase_secrets() -> tuple[str, str]:
    return _resolve_supabase_url(), _resolve_supabase_api_key()


def get_supabase_client() -> Client | None:
    """Cliente Supabase: create_client(SUPABASE_URL, SUPABASE_KEY) como no guia oficial."""
    if not create_client:
        return None
    url = _resolve_supabase_url()
    key = _resolve_supabase_api_key()
    if not url or not key or not _supabase_api_key_looks_valid(key):
        return None
    if not _supabase_project_url_ok(url):
        return None
    url_ref = _supabase_ref_from_url(url)
    key_ref = _supabase_ref_from_jwt_key(key)
    if url_ref and key_ref and url_ref != key_ref:
        return None
    try:
        return create_client(url, key)
    except Exception as exc:
        msg = str(exc).lower()
        if _supabase_is_publishable_key(key) and "invalid api key" in msg:
            st.session_state["_ego_supabase_connect_hint"] = (
                "Chave publishable detectada, mas o pacote `supabase` está antigo. "
                "No terminal: `pip install -U \"supabase>=2.28.0\"` e reinicie o Streamlit."
            )
        return None


def _supabase_table_missing_error(exc: BaseException) -> bool:
    err = str(exc).lower()
    return (
        "pgrst205" in err
        or "schema cache" in err
        or "does not exist" in err
        or "42p01" in err
    )


def probe_ego_supabase_schema(supabase: Client | None) -> dict[str, bool]:
    """Verifica se as tabelas existem (uma query leve por tabela)."""
    if not supabase:
        return {label: False for label, _ in EGO_SCHEMA_TABLE_SPECS}
    out: dict[str, bool] = {}
    for label, table in EGO_SCHEMA_TABLE_SPECS:
        try:
            supabase.table(table).select("*").limit(1).execute()
            out[label] = True
        except Exception as e:  # noqa: BLE001
            out[label] = not _supabase_table_missing_error(e)
    return out


def render_ego_schema_banner() -> None:
    """Aviso quando faltam tabelas — dados do utilizador não gravam sem isto."""
    status = st.session_state.get("_ego_schema_status")
    if not isinstance(status, dict):
        return
    missing = [name for name, ok in status.items() if not ok]
    if not missing:
        return
    st.error(
        "**Base de dados incompleta no Supabase.** "
        f"Falta(m): {', '.join(missing)}. "
        "Enquanto isso, lembretes, agenda e histórico podem não ser guardados."
    )
    with st.expander("Como corrigir (uma vez no projeto Supabase)", expanded=True):
        st.markdown(
            "1. Abra [Supabase](https://supabase.com) → o seu projeto → **SQL Editor** → **New query**.\n"
            "2. Copie **todo** o ficheiro `supabase/bootstrap_ego_schema.sql` do repositório e execute **Run**.\n"
            "3. Volte à app, faça **Sair** e **Entrar** de novo.\n\n"
            "Cada utilizador fica ligado pelo `user_id` (o mesmo id do login):\n"
            "- **profiles** — preferências (`ui_state`), trial/pro\n"
            "- **chat_history** — mensagens do chat\n"
            "- **agenda** — compromissos recorrentes\n"
            "- **reminders** — lembretes com alarme\n"
            "- **user_personas** — avatar e voz"
        )
        if st.button("Verificar tabelas outra vez", key="ego_schema_recheck"):
            st.session_state.pop("_ego_schema_probed", None)
            st.rerun()


def _supabase_setup_hint(url: str, key: str) -> str:
    """Mensagem curta para o utilizador corrigir URL/chave."""
    u = (url or "").strip()
    k = (key or "").strip()
    if not u and not k:
        return (
            "Crie um ficheiro `.env` na raiz (copie de `.env.example`) com SUPABASE_URL e SUPABASE_KEY, "
            "ou use `.streamlit/secrets.toml` / Secrets no Streamlit Cloud."
        )
    if not u:
        return "Falta SUPABASE_URL."
    if not k:
        return (
            "Falta SUPABASE_KEY (ou SUPABASE_PUBLISHABLE_KEY): chave **publishable** "
            "(`sb_publishable_...`) em Settings → API Keys."
        )
    if not u.startswith("https://"):
        return "SUPABASE_URL deve começar por https://"
    if not _supabase_project_url_ok(u):
        return (
            "SUPABASE_URL inválido. No Supabase vá em Settings → API e copie o **Project URL**: "
            "deve ser como `https://abcdefgh.supabase.co` — **não** use só `https://supabase.co`."
        )
    if not _supabase_api_key_looks_valid(k):
        return (
            "SUPABASE_KEY inválida. Use a **publishable** (`sb_publishable_...`) "
            "ou, se preferir, a legada **anon** (`eyJ...`) — Settings → API Keys."
        )
    url_ref = _supabase_ref_from_url(u)
    key_ref = _supabase_ref_from_jwt_key(k)
    if url_ref and key_ref and url_ref != key_ref:
        return (
            f"A URL e a chave JWT **não são do mesmo projeto**. "
            f"Na URL: `{url_ref}` · Na chave: `{key_ref}`. "
            f"Corrija para: `https://{key_ref}.supabase.co` "
            f"(copie **Project URL** e a chave no mesmo ecrã Supabase → API)."
        )
    return (
        "Não consegui conectar. Confirme **Project URL** + **publishable** do mesmo projeto. "
        "**Não** use a chave `service_role` no Streamlit."
    )


def render_supabase_setup() -> None:
    """Tela rápida para configurar credenciais Supabase quando ausentes."""
    st.error("Supabase não configurado ou URL/chave inválidos.")
    if not create_client:
        st.warning(
            "O pacote Python `supabase` não está instalado. "
            "No terminal: `pip install -r requirements.txt` e reinicie o Streamlit."
        )
    hint_sess = st.session_state.pop("_ego_supabase_connect_hint", None)
    if hint_sess:
        st.error(hint_sess)
    su, sk = _peek_supabase_secrets()
    if su or sk:
        st.warning(f"**Diagnóstico (secrets.toml / variáveis):** {_supabase_setup_hint(su, sk)}")
        if create_client and su and sk and _supabase_api_key_looks_valid(sk):
            try:
                probe = create_client(su, sk)
                probe.table(SUPABASE_PROFILES_TABLE).select("id").limit(1).execute()
            except Exception as exc:
                err = str(exc)
                if "profiles" in err and ("PGRST205" in err or "does not exist" in err.lower()):
                    st.error(
                        "Ligação OK, mas falta a tabela **profiles**. "
                        "No Supabase → SQL Editor execute o ficheiro "
                        "`supabase/bootstrap_ego_schema.sql` do projeto."
                    )
                elif "Invalid API key" in err:
                    st.error(
                        "Chave recusada pelo cliente Python. Atualize: "
                        "`pip install -U \"supabase>=2.28.0\"` (publishable exige versão recente)."
                    )
    elif hasattr(st, "secrets"):
        try:
            _ = st.secrets.keys()
        except Exception as exc:
            st.error(
                f"**secrets.toml inválido:** {exc} "
                "Use aspas nas URLs (`SUPABASE_URL = \"https://...\"`) e não comece o ficheiro com a palavra `toml`."
            )
    st.info(
        "**Dica (igual ao guia Supabase):** crie `.env` na pasta do projeto com "
        "`SUPABASE_URL` e `SUPABASE_KEY` (publishable `sb_publishable_...`). "
        "Reinicie o Streamlit após guardar. No Cloud: Manage app → **Secrets**."
    )
    render_public_trust_landing()
    st.markdown("### Configure as credenciais para entrar no app")
    url_prefill = (st.session_state.get("supabase_url_input") or su or "").strip()
    key_prefill = (st.session_state.get("supabase_key_input") or sk or "").strip()
    with st.form("supabase_setup_form", border=True):
        st.text_input(
            "SUPABASE_URL",
            value=url_prefill,
            placeholder="https://seu-projeto.supabase.co",
            key="supabase_url_input",
        )
        st.text_input(
            "SUPABASE_KEY (publishable sb_publishable_...)",
            value=key_prefill,
            type="password",
            placeholder="sb_publishable_...",
            key="supabase_key_input",
        )
        submitted = st.form_submit_button("Salvar e testar conexão", use_container_width=True)
        if submitted:
            u_try = (st.session_state.get("supabase_url_input") or "").strip()
            k_try = (st.session_state.get("supabase_key_input") or "").strip()
            if get_supabase_client():
                st.success("Conexão Supabase configurada com sucesso.")
                st.rerun()
            else:
                st.warning(_supabase_setup_hint(u_try, k_try))
    render_trust_footer(authenticated=False)


def carregar_historico_seguro(supabase: Client | None, user_id: str) -> list[dict]:
    """Carrega mensagens do usuário atual; com RLS a query já vem filtrada."""
    if not supabase:
        return []
    try:
        res = (
            supabase.table(SUPABASE_HISTORY_TABLE)
            .select("ego_msg_id,role,content,created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=False)
            .execute()
        )
        rows = res.data or []
        out: list[dict] = []
        for r in rows:
            if r.get("role") not in ("user", "assistant"):
                continue
            mid = r.get("ego_msg_id")
            out.append(
                {
                    "role": r.get("role", "assistant"),
                    "content": r.get("content", ""),
                    "msg_id": str(mid) if mid else None,
                }
            )
        return out
    except Exception:
        try:
            res = (
                supabase.table(SUPABASE_HISTORY_TABLE)
                .select("role,content,created_at")
                .eq("user_id", user_id)
                .order("created_at", desc=False)
                .execute()
            )
            rows = res.data or []
            return [
                {
                    "role": r.get("role", "assistant"),
                    "content": r.get("content", ""),
                    "msg_id": None,
                }
                for r in rows
                if r.get("role") in ("user", "assistant")
            ]
        except Exception:
            return []


def salvar_mensagem_segura(
    supabase: Client | None, user_id: str, role: str, content: str
) -> str | None:
    """Persiste mensagem e devolve ego_msg_id (ou id) quando o Supabase devolver."""
    if not supabase:
        return None
    if not ensure_supabase_auth_client(supabase):
        st.session_state["_ego_chat_save_warn"] = (
            "Histórico não gravado: sessão Supabase expirada. Faça **Sair** e **Entrar** de novo."
        )
        return None
    row = {"user_id": user_id, "role": role, "content": content}
    last_err: Exception | None = None
    try:
        res = (
            supabase.table(SUPABASE_HISTORY_TABLE)
            .insert(row)
            .select("ego_msg_id")
            .execute()
        )
        if res.data and res.data[0].get("ego_msg_id"):
            return str(res.data[0]["ego_msg_id"])
    except Exception as e:  # noqa: BLE001
        last_err = e
    try:
        res = (
            supabase.table(SUPABASE_HISTORY_TABLE)
            .insert(row)
            .select("id")
            .execute()
        )
        if res.data and res.data[0].get("id") is not None:
            return str(res.data[0]["id"])
    except Exception as e:  # noqa: BLE001
        last_err = e
    try:
        supabase.table(SUPABASE_HISTORY_TABLE).insert(row).execute()
        return None
    except Exception as e:  # noqa: BLE001
        last_err = e
    if last_err and _supabase_table_missing_error(last_err):
        st.session_state["_ego_chat_save_warn"] = (
            "Histórico do chat não foi gravado: tabela `chat_history` em falta no Supabase. "
            "Execute `supabase/bootstrap_ego_schema.sql` no SQL Editor."
        )
    return None


# --- FUNCOES DE BANCO DE DADOS PARA O CHAT ---
def salvar_mensagem_no_banco(user_id: str, role: str, content: str) -> str | None:
    """Wrapper com assinatura simples (como no snippet), usando cliente Supabase ativo."""
    supabase = get_supabase_client()
    if not supabase:
        return None
    return salvar_mensagem_segura(supabase, user_id, role, content)


def carregar_historico_do_banco(user_id: str) -> list[dict]:
    """Carrega historico do usuario no formato usado pelo Streamlit chat."""
    supabase = get_supabase_client()
    if not supabase:
        return []
    return carregar_historico_seguro(supabase, user_id)


def count_tokens_text(text: str, encoding_name: str = "cl100k_base") -> int:
    """Contagem aproximada de tokens (encoding cl100k); útil para limites mensais com Gemini."""
    if not text:
        return 0
    if tiktoken is None:
        return max(1, len(text) // 4)
    try:
        enc = tiktoken.get_encoding(encoding_name)
        return len(enc.encode(text))
    except Exception:
        return max(1, len(text) // 4)


def count_turn_tokens(user_text: str, assistant_text: str) -> int:
    return count_tokens_text(user_text) + count_tokens_text(assistant_text)


def monthly_token_limit_for_user(is_pro: bool) -> int:
    lim = EGO_MONTHLY_TOKEN_LIMIT_PRO if is_pro else EGO_MONTHLY_TOKEN_LIMIT_FREE
    return int(lim)


def _current_token_period_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m")


def ensure_profile_token_period_reset(supabase: Client | None, user_id: str, prof: dict) -> dict:
    """Garante monthly_tokens_period = mês UTC atual; zera contador se mudou o mês."""
    if not supabase or not user_id:
        return prof
    period = _current_token_period_utc()
    cur = (prof.get("monthly_tokens_period") or "").strip()
    if cur == period:
        return prof
    try:
        supabase.table(SUPABASE_PROFILES_TABLE).update(
            {"monthly_tokens_used": 0, "monthly_tokens_period": period}
        ).eq("id", user_id).execute()
    except Exception:
        return prof
    prof = dict(prof)
    prof["monthly_tokens_used"] = 0
    prof["monthly_tokens_period"] = period
    return prof


def check_monthly_token_allowance(
    supabase: Client | None, user_id: str, is_pro: bool
) -> tuple[bool, str, int, int]:
    """(ok, mensagem, usado_no_mês, limite). limite 0 = ilimitado."""
    lim = monthly_token_limit_for_user(is_pro)
    if lim <= 0:
        return True, "", 0, 0
    if not supabase or not user_id:
        return True, "", 0, lim
    prof = carregar_perfil_usuario(supabase, user_id) or {}
    prof = ensure_profile_token_period_reset(supabase, user_id, prof)
    used = int(prof.get("monthly_tokens_used") or 0)
    if used >= lim:
        return (
            False,
            "Limite mensal de tokens atingido. Faça upgrade para Pro ou aguarde o próximo período.",
            used,
            lim,
        )
    return True, "", used, lim


def add_monthly_tokens_to_profile(
    supabase: Client | None, user_id: str, delta: int, is_pro: bool
) -> None:
    if not supabase or not user_id or delta <= 0:
        return
    lim = monthly_token_limit_for_user(is_pro)
    if lim <= 0:
        return
    prof = carregar_perfil_usuario(supabase, user_id) or {}
    prof = ensure_profile_token_period_reset(supabase, user_id, prof)
    used = int(prof.get("monthly_tokens_used") or 0)
    new_used = used + int(delta)
    try:
        supabase.table(SUPABASE_PROFILES_TABLE).update(
            {"monthly_tokens_used": new_used}
        ).eq("id", user_id).execute()
    except Exception:
        pass


def save_message_feedback(
    supabase: Client | None,
    user_id: str,
    message_id: str,
    vote: int,
    model_provider: str,
) -> None:
    if not supabase or not user_id or not message_id or vote not in (1, -1):
        return
    try:
        supabase.table(SUPABASE_FEEDBACK_TABLE).insert(
            {
                "user_id": user_id,
                "chat_message_id": message_id[:500],
                "vote": vote,
                "model_provider": (model_provider or "")[:80],
            }
        ).execute()
    except Exception:
        pass


def build_chat_export_txt(messages: list) -> bytes:
    lines: list[str] = []
    for m in messages:
        role = m.get("role", "?")
        content = (m.get("content") or "").strip()
        lines.append(f"[{role}]\n{content}\n")
    return ("\n".join(lines)).encode("utf-8")


LEGAL_DOC_OPTIONS = [
    "Termos de Uso",
    "Política de Privacidade",
    "Política de Reembolso",
]


def render_legal_documents_selector() -> None:
    """Termos, privacidade e reembolso com navegação estável (Stripe / LGPD)."""
    st.caption("Textos padrão para transparência e conformidade (revise com advogado antes do go-live).")
    rid = int(st.session_state.get("_legal_render_id", 0))
    default_ix = int(st.session_state.get("ego_legal_tab", 0))
    default_ix = min(max(default_ix, 0), len(LEGAL_DOC_OPTIONS) - 1)
    choice = st.radio(
        "Documentos",
        LEGAL_DOC_OPTIONS,
        horizontal=True,
        index=default_ix,
        key=f"legal_doc_radio_{rid}",
    )
    st.session_state["ego_legal_tab"] = LEGAL_DOC_OPTIONS.index(choice)
    if choice == LEGAL_DOC_OPTIONS[0]:
        st.markdown(terms_of_use_markdown())
    elif choice == LEGAL_DOC_OPTIONS[1]:
        st.markdown(privacy_policy_markdown())
    else:
        st.markdown(refund_policy_markdown())


def render_policies_page(*, for_public_login: bool = False) -> None:
    """Página Políticas: textos exigidos para Stripe (Termos, Privacidade, Reembolso)."""
    st.title("Políticas")
    if for_public_login:
        if st.button("← Voltar ao login", use_container_width=True, key="policies_back_login"):
            st.session_state["ego_login_policies"] = False
            st.rerun()
    st.caption(
        "Termos de Uso, Política de Privacidade e Política de Reembolso — transparência para utilizadores "
        "e para processadores de pagamento (ex.: Stripe)."
    )
    render_legal_documents_selector()


def render_public_trust_landing() -> None:
    """Antes do login: CTA Pro + contactos visíveis (exigência típica Stripe)."""
    em_addr = ego_support_email()
    em = html.escape(em_addr)
    op = html.escape(ego_operator_legal_name())
    mensal = html.escape(PAYWALL_PRECO_MENSAL)
    anual = html.escape(PAYWALL_PRECO_ANUAL)
    mail_href = f"mailto:{quote(em_addr, safe='@')}?subject={quote('Suporte EGO-AI')}"
    mail_href_attr = html.escape(mail_href)
    st.markdown(
        f"""
<div class="ego-glass-panel">
  <h3>EGO-AI — assistente global com IA</h3>
  <p style="margin:0 0 0.75rem 0;">
    Organize o seu dia, lembretes e integrações com privacidade em mente. <strong>LGPD / RGPD</strong> na base
    do desenho do produto; pagamentos seguros via <strong>Stripe</strong>.
  </p>
  <p style="margin:0 0 0.5rem 0;"><strong>Plano Pro</strong> — desbloqueie avatares e vozes premium, exportações e limites alargados.</p>
  <ul style="margin:0.35rem 0 0.75rem 1rem;">
    <li>Mensal: <strong>{mensal}</strong></li>
    <li>Anual: <strong>{anual}</strong> <em>(após entrar na conta, use os botões de checkout na app)</em></li>
  </ul>
  <p style="margin:0 0 0.35rem 0;"><strong>Contacto antes de criar conta</strong></p>
    <p style="margin:0;">
    <a class="ego-glass-cta" href="{mail_href_attr}">Enviar e-mail para suporte</a>
  </p>
  <p style="margin:0.85rem 0 0 0;font-size:0.8rem;color:#94a3b8;">
    Operador: <strong>{op}</strong> · Suporte: {em}
  </p>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_trust_footer(*, authenticated: bool) -> None:
    """Rodapé de confiança + atalhos jurídicos (todas as áreas)."""
    st.markdown('<div class="ego-trust-footer-glass">', unsafe_allow_html=True)
    y = datetime.datetime.now().year
    op = html.escape(ego_operator_legal_name())
    em = html.escape(ego_support_email())
    st.markdown(
        f'<p class="ego-footer-copy">© {y} EGO-AI — Operado por <strong>{op}</strong>. '
        f"Todos os direitos reservados.</p>"
        f'<p class="ego-footer-copy" style="margin-top:0.35rem;">Suporte: {em}</p>',
        unsafe_allow_html=True,
    )
    if not authenticated:
        if st.button(
            "Políticas — Termos, Privacidade e Reembolso (leitura antes do login · Stripe)",
            key="footer_policies_full_page",
            use_container_width=True,
        ):
            st.session_state["_legal_render_id"] = int(
                st.session_state.get("_legal_render_id", 0)
            ) + 1
            st.session_state["ego_login_policies"] = True
            st.rerun()
    fc1, fc2, fc3, fc4 = st.columns([1.1, 1, 1, 1])
    em_raw = ego_support_email()
    for col, label, tab_ix in (
        (fc1, "Termos", 0),
        (fc2, "Privacidade", 1),
        (fc3, "Reembolso", 2),
    ):
        with col:
            key = f"ft_{label}_{authenticated}"
            if st.button(label, key=key, use_container_width=True):
                st.session_state["_legal_render_id"] = int(
                    st.session_state.get("_legal_render_id", 0)
                ) + 1
                st.session_state["ego_legal_tab"] = tab_ix
                if authenticated:
                    st.session_state["ego_nav"] = "Políticas"
                else:
                    st.session_state["ego_login_policies"] = True
                st.rerun()
    with fc4:
        mh = f"mailto:{quote(em_raw, safe='@')}?subject={quote('Suporte EGO-AI')}"
        st.markdown(
            f'<a class="ego-footer-links" href="{html.escape(mh)}">E-mail</a>',
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


def _plain_text_for_speech(md: str) -> str:
    """Remove markdown ruidoso para TTS (não precisa ser perfeito)."""
    t = (md or "").strip()
    if not t:
        return ""
    t = re.sub(r"\[\[EGO_[^\]]+\]\]", "", t)
    t = re.sub(r"```[\s\S]*?```", " ", t)
    t = re.sub(r"`([^`]+)`", r"\1", t)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    t = re.sub(r"[*_#>|]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:4000]


def render_chat_messages_with_feedback(supabase: Client | None, user_id: str) -> None:
    msgs = st.session_state.get("messages") or []
    play_idx = st.session_state.pop("_ego_tts_play_index", None)
    if not msgs:
        st.caption("Escreva abaixo para começar a conversar com a IA.")
        return
    provider = "Gemini"
    show_fb = st.session_state.get("ego_show_msg_feedback", False)
    voice_on = bool(st.session_state.get("ego_voice_replies", True))
    last_i = len(msgs) - 1
    for i, msg in enumerate(msgs):
        role = msg.get("role", "user")
        with st.chat_message(role):
            st.markdown(msg.get("content") or "")
            mid = msg.get("msg_id")
            if (
                voice_on
                and role == "assistant"
                and play_idx is not None
                and i == play_idx
            ):
                spoken = _plain_text_for_speech(str(msg.get("content") or ""))
                if spoken:
                    st.session_state["_ego_tts_pending"] = {
                        "text": spoken,
                        "key": f"asst_{i}_{mid or i}",
                        "lang": st.session_state.get("last_detected_language"),
                    }
            if (
                voice_on
                and role == "assistant"
                and i == last_i
                and (msg.get("content") or "").strip()
            ):
                if st.button(
                    "Ouvir resposta",
                    key=f"ego_tts_replay_{i}_{mid or i}",
                    use_container_width=True,
                ):
                    spoken = _plain_text_for_speech(str(msg.get("content") or ""))
                    if spoken:
                        queue_assistant_speech(
                            spoken,
                            f"replay_{i}_{mid or i}",
                            lang_hint=st.session_state.get("last_detected_language"),
                        )
                        st.rerun()
            if (
                show_fb
                and role == "assistant"
                and mid
                and user_id
                and supabase
                and i == last_i
            ):
                u1, u2 = st.columns(2)
                with u1:
                    if st.button("👍", key=f"fb_up_{mid}_{i}", use_container_width=True):
                        save_message_feedback(supabase, user_id, str(mid), 1, provider)
                        st.toast("Obrigado!")
                with u2:
                    if st.button("👎", key=f"fb_dn_{mid}_{i}", use_container_width=True):
                        save_message_feedback(supabase, user_id, str(mid), -1, provider)
                        st.toast("Obrigado!")


def _normalize_auth_email(raw: str) -> tuple[str, str | None]:
    """E-mail para Auth/DB (RFC: até 254 caracteres)."""
    email = (raw or "").strip()
    if not email or "@" not in email or email.startswith("@") or email.endswith("@"):
        return "", "Informe um e-mail válido (ex.: nome@dominio.com)."
    if len(email) > 254:
        return "", "E-mail demasiado longo. Use no máximo 254 caracteres."
    return email, None


def _format_auth_error(exc: BaseException) -> str:
    """Mensagem amigável para erros comuns do Supabase Auth."""
    msg = str(exc).strip()
    low = msg.lower()
    if "rate limit" in low or "too many requests" in low:
        return (
            "**Limite de e-mails do Supabase** (muitas tentativas de cadastro/confirmação). "
            "Aguarde **15–60 minutos** e tente de novo, ou use a aba **Entrar** se a conta já existir. "
            "Para testes: Supabase → **Authentication** → **Providers** → **Email** → desative "
            "**Confirm email** e evite criar várias contas seguidas com o mesmo domínio."
        )
    if "already registered" in low or "already been registered" in low or "user already exists" in low:
        return "Este e-mail **já está cadastrado**. Use a aba **Entrar** com a mesma senha."
    if "invalid login" in low or "invalid credentials" in low:
        return "E-mail ou senha incorretos."
    return msg or "Erro de autenticação."


def _sync_supabase_auth_from_response(supabase: Client | None, res: object) -> None:
    """Garante JWT na sessão do cliente (RLS em profiles exige auth.uid())."""
    if not supabase or not res:
        return
    session = getattr(res, "session", None)
    if not session:
        return
    access = getattr(session, "access_token", None)
    refresh = getattr(session, "refresh_token", None)
    if access and refresh:
        try:
            supabase.auth.set_session(access, refresh)
            _ego_persist_auth_tokens(str(access), str(refresh))
        except Exception:
            pass


def _ego_persist_auth_tokens(access: str | None, refresh: str | None) -> None:
    if access and refresh:
        st.session_state["_ego_sb_access"] = access
        st.session_state["_ego_sb_refresh"] = refresh


def ensure_supabase_auth_client(supabase: Client | None) -> bool:
    """Reaplica JWT do utilizador no cliente Supabase (RLS exige auth.uid() = user_id)."""
    if not supabase:
        return False
    try:
        cur = supabase.auth.get_session()
        sess = getattr(cur, "session", None) if cur else None
        if sess and getattr(sess, "access_token", None):
            _ego_persist_auth_tokens(
                str(getattr(sess, "access_token", "") or ""),
                str(getattr(sess, "refresh_token", "") or ""),
            )
            return True
        user_resp = supabase.auth.get_user()
        if getattr(user_resp, "user", None):
            return True
    except Exception:
        pass
    access = st.session_state.get("_ego_sb_access")
    refresh = st.session_state.get("_ego_sb_refresh")
    if access and refresh:
        try:
            supabase.auth.set_session(str(access), str(refresh))
            return True
        except Exception:
            pass
    return False


def _ego_local_auth_root() -> Path:
    return Path.home() / ".ego-ai"


def _ego_local_auth_project_ref() -> str:
    return _supabase_ref_from_url(_resolve_supabase_url()) or "default"


def _ego_local_auth_session_path(email: str) -> Path:
    em = (email or "").strip().lower()
    digest = hashlib.sha256(f"{_ego_local_auth_project_ref()}:{em}".encode()).hexdigest()[:28]
    return _ego_local_auth_root() / "sessions" / f"{digest}.json"


def _ego_local_auth_last_email_path() -> Path:
    return _ego_local_auth_root() / "last_login.json"


def _read_last_login_email_local() -> str:
    p = _ego_local_auth_last_email_path()
    if not p.is_file():
        return ""
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            em = data.get("email")
            return str(em).strip() if em else ""
    except Exception:
        pass
    return ""


def _auth_tokens_from_session(session: object | None) -> tuple[str, str, int | None]:
    if not session:
        return "", "", None
    access = str(getattr(session, "access_token", None) or "")
    refresh = str(getattr(session, "refresh_token", None) or "")
    exp = getattr(session, "expires_at", None)
    exp_i: int | None
    try:
        exp_i = int(exp) if exp is not None else None
    except (TypeError, ValueError):
        exp_i = None
    return access, refresh, exp_i


def _build_local_auth_snapshot(
    supabase: Client | None,
    email: str,
    user: object,
    res: object | None,
) -> dict | None:
    session = getattr(res, "session", None) if res else None
    access, refresh, exp_i = _auth_tokens_from_session(session)
    if (not access or not refresh) and supabase:
        try:
            live = supabase.auth.get_session()
            sess = getattr(live, "session", None) if live else None
            access, refresh, exp_i = _auth_tokens_from_session(sess)
        except Exception:
            pass
    if not access or not refresh:
        return None
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return {
        "v": LOCAL_AUTH_VERSION,
        "project_ref": _ego_local_auth_project_ref(),
        "email": (email or "").strip().lower(),
        "user_id": str(getattr(user, "id", "") or ""),
        "access_token": access,
        "refresh_token": refresh,
        "expires_at": exp_i,
        "saved_at": now,
        "last_login_at": now,
    }


def save_local_login_snapshot(
    supabase: Client | None,
    email: str,
    user: object,
    res: object | None,
) -> None:
    """Guarda sessão Supabase no disco (utilizador) e no localStorage do browser."""
    if not st.session_state.get("ego_remember_device", True):
        return
    snap = _build_local_auth_snapshot(supabase, email, user, res)
    if not snap or not snap.get("email"):
        return
    try:
        root = _ego_local_auth_root()
        root.mkdir(parents=True, exist_ok=True)
        sess_path = _ego_local_auth_session_path(snap["email"])
        sess_path.parent.mkdir(parents=True, exist_ok=True)
        sess_path.write_text(json.dumps(snap, ensure_ascii=False), encoding="utf-8")
        try:
            os.chmod(sess_path, 0o600)
        except OSError:
            pass
        last_path = _ego_local_auth_last_email_path()
        last_path.write_text(
            json.dumps(
                {
                    "email": snap["email"],
                    "last_login_at": snap.get("last_login_at"),
                    "project_ref": snap.get("project_ref"),
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        try:
            os.chmod(last_path, 0o600)
        except OSError:
            pass
    except OSError:
        pass
    _ego_auth_browser_write(snap)


def clear_local_login_snapshot(email: str | None = None) -> None:
    """Remove sessão guardada localmente (logout)."""
    try:
        if email and (email or "").strip():
            p = _ego_local_auth_session_path(email)
            if p.is_file():
                p.unlink()
        else:
            sess_dir = _ego_local_auth_root() / "sessions"
            ref = _ego_local_auth_project_ref()
            if sess_dir.is_dir():
                for fp in sess_dir.glob("*.json"):
                    try:
                        data = json.loads(fp.read_text(encoding="utf-8"))
                        if data.get("project_ref") == ref:
                            fp.unlink()
                    except Exception:
                        pass
        last_p = _ego_local_auth_last_email_path()
        if last_p.is_file():
            try:
                data = json.loads(last_p.read_text(encoding="utf-8"))
                if not email or data.get("email") == (email or "").strip().lower():
                    last_p.unlink()
            except Exception:
                last_p.unlink()
    except OSError:
        pass
    _ego_auth_browser_clear()
    for k in (
        "_ego_browser_auth_raw",
        "_ego_browser_auth_read_done",
        "_ego_auth_restore_pass2",
    ):
        st.session_state.pop(k, None)


def _ego_auth_browser_write(snap: dict) -> None:
    try:
        import streamlit.components.v1 as components
    except ImportError:
        return
    blob = json.dumps(snap, ensure_ascii=False)
    components.html(
        f"""
<script>
(function() {{
  try {{
    localStorage.setItem({json.dumps(EGO_BROWSER_AUTH_STORAGE_KEY)}, {json.dumps(blob)});
  }} catch (e) {{}}
}})();
</script>
""",
        height=0,
        width=0,
    )


def _ego_auth_browser_clear() -> None:
    try:
        import streamlit.components.v1 as components
    except ImportError:
        return
    key = json.dumps(EGO_BROWSER_AUTH_STORAGE_KEY)
    components.html(
        f"""
<script>
(function() {{
  try {{ localStorage.removeItem({key}); }} catch (e) {{}}
}})();
</script>
""",
        height=0,
        width=0,
    )


def _ego_auth_browser_read() -> str:
    try:
        import streamlit.components.v1 as components
    except ImportError:
        return ""
    key = json.dumps(EGO_BROWSER_AUTH_STORAGE_KEY)
    val = components.html(
        f"""
<script>
(function() {{
  var payload = "";
  try {{
    payload = localStorage.getItem({key}) || "";
  }} catch (e) {{}}
  window.parent.postMessage({{
    type: "streamlit:setComponentValue",
    value: payload
  }}, "*");
}})();
</script>
""",
        height=0,
        width=0,
    )
    if isinstance(val, str):
        return val.strip()
    return ""


def _parse_local_auth_snapshot(raw: object) -> dict | None:
    if raw is None:
        return None
    if isinstance(raw, dict):
        data = raw
    elif isinstance(raw, str) and raw.strip():
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None
    else:
        return None
    if not isinstance(data, dict):
        return None
    if int(data.get("v") or 0) != LOCAL_AUTH_VERSION:
        return None
    if data.get("project_ref") and data.get("project_ref") != _ego_local_auth_project_ref():
        return None
    if not data.get("access_token") or not data.get("refresh_token"):
        return None
    return data


def _load_local_auth_snapshots() -> list[dict]:
    snaps: list[dict] = []
    raw_browser = str(st.session_state.get("_ego_browser_auth_raw") or "")
    parsed = _parse_local_auth_snapshot(raw_browser)
    if parsed:
        snaps.append(parsed)
    last_em = _read_last_login_email_local()
    if last_em:
        p = _ego_local_auth_session_path(last_em)
        if p.is_file():
            try:
                disk = _parse_local_auth_snapshot(json.loads(p.read_text(encoding="utf-8")))
                if disk and disk not in snaps:
                    snaps.append(disk)
            except Exception:
                pass
    sess_dir = _ego_local_auth_root() / "sessions"
    if sess_dir.is_dir():
        ref = _ego_local_auth_project_ref()
        files = sorted(sess_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
        for fp in files[:3]:
            try:
                disk = _parse_local_auth_snapshot(json.loads(fp.read_text(encoding="utf-8")))
                if disk and disk.get("project_ref") == ref and disk not in snaps:
                    snaps.append(disk)
            except Exception:
                continue
    return snaps


def try_restore_local_auth(supabase: Client | None) -> bool:
    """Reabre sessão Supabase a partir de credenciais guardadas neste dispositivo."""
    if not supabase or st.session_state.get("user_logged"):
        return False
    for snap in _load_local_auth_snapshots():
        email = str(snap.get("email") or "").strip()
        access = str(snap.get("access_token") or "")
        refresh = str(snap.get("refresh_token") or "")
        if not access or not refresh:
            continue
        try:
            supabase.auth.set_session(access, refresh)
            _ego_persist_auth_tokens(access, refresh)
            user_resp = supabase.auth.get_user()
            user = getattr(user_resp, "user", None) if user_resp else None
            if not user:
                continue
            em = email or str(getattr(user, "email", "") or "")
            _ego_apply_auth_session(user, em)
            touch_last_login(supabase, str(user.id))
            save_local_login_snapshot(supabase, em, user, None)
            return True
        except Exception:
            continue
    return False


def ensure_user_profile(
    supabase: Client | None,
    user_id: str,
    *,
    email: str = "",
    full_name: str = "",
    country: str = "Brasil",
    document_type: str = "",
) -> tuple[bool, str]:
    """Cria ou atualiza linha em public.profiles para o utilizador autenticado."""
    if not supabase or not user_id:
        return False, "Cliente Supabase ou user_id em falta."
    display = (full_name or "").strip() or (email.split("@")[0] if email else "Usuário")
    em = (email or "").strip()
    if len(em) > 254:
        em = em[:254]
    row = {
        "id": user_id,
        "full_name": display[:200],
        "email": em or None,
        "country": (country or "Brasil")[:80],
        "document_type": (document_type or "")[:500],
    }
    try:
        found = (
            supabase.table(SUPABASE_PROFILES_TABLE)
            .select("id")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        if found.data:
            supabase.table(SUPABASE_PROFILES_TABLE).update(
                {
                    "full_name": row["full_name"],
                    "email": row["email"],
                    "country": row["country"],
                    "document_type": row["document_type"],
                }
            ).eq("id", user_id).execute()
        else:
            supabase.table(SUPABASE_PROFILES_TABLE).insert(
                {**row, "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
            ).execute()
        return True, ""
    except Exception as exc:
        err = str(exc)
        if "too long" in err.lower() or "muito longo" in err.lower() or "varchar" in err.lower():
            return (
                False,
                f"{err} — No Supabase SQL Editor execute `supabase/fix_profiles_text_columns.sql`.",
            )
        return False, err


def touch_last_login(supabase: Client | None, user_id: str) -> None:
    """Grava profiles.last_login_at uma vez por sessão Streamlit (evita reruns)."""
    if not supabase or not user_id:
        return
    if st.session_state.get("_ego_last_login_at_unsupported"):
        return
    if st.session_state.get("_ego_last_login_persisted_for") == user_id:
        return
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        supabase.table(SUPABASE_PROFILES_TABLE).update({"last_login_at": ts}).eq("id", user_id).execute()
    except Exception as exc:  # noqa: BLE001
        err = str(exc).lower()
        if (
            "last_login_at" in err
            or "could not find" in err
            or ("column" in err and "does not exist" in err)
            or "schema cache" in err
        ):
            st.session_state["_ego_last_login_at_unsupported"] = True
        return
    st.session_state["_ego_last_login_persisted_for"] = user_id


def salvar_perfil_seguro(
    supabase: Client | None,
    *,
    user_id: str,
    full_name: str,
    email: str,
    country: str,
    document_type: str,
) -> tuple[bool, str]:
    """Cria/atualiza perfil completo do usuário logado."""
    return ensure_user_profile(
        supabase,
        user_id,
        email=email,
        full_name=full_name,
        country=country,
        document_type=document_type,
    )


def load_user_persona(supabase: Client | None, user_id: str) -> tuple[str, str]:
    if not supabase or not user_id:
        return st.session_state.get("assistant_avatar_id", "f1"), st.session_state.get(
            "assistant_voice_id", "vf1"
        )
    try:
        res = (
            supabase.table(SUPABASE_PERSONA_TABLE)
            .select("avatar_id,voice_id")
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        data = res.data or {}
        return data.get("avatar_id", "f1"), data.get("voice_id", "vf1")
    except Exception:
        return st.session_state.get("assistant_avatar_id", "f1"), st.session_state.get(
            "assistant_voice_id", "vf1"
        )


def save_user_persona(supabase: Client | None, user_id: str, avatar_id: str, voice_id: str) -> None:
    if not supabase or not user_id:
        return
    try:
        supabase.table(SUPABASE_PERSONA_TABLE).upsert(
            {"user_id": user_id, "avatar_id": avatar_id, "voice_id": voice_id}
        ).execute()
    except Exception:
        pass


def clamp_persona_para_plano_nao_pro(
    supabase: Client | None, user_id: str, *, is_pro: bool
) -> None:
    """Se não for Pro, força avatar/voz do tier grátis (m1 ou f1 + vm1 ou vf1)."""
    if is_pro or not supabase or not user_id:
        return
    aid = st.session_state.get("assistant_avatar_id", "f1")
    vid = st.session_state.get("assistant_voice_id", "vf1")
    changed = False
    if aid not in FREE_AVATAR_IDS:
        al = str(aid).lower()
        st.session_state.assistant_avatar_id = "m1" if al.startswith("m") or al.startswith("pm") else "f1"
        changed = True
    if vid not in FREE_VOICE_IDS:
        vl = str(vid).lower()
        if vl.startswith("vm") or vl.startswith("pvm"):
            st.session_state.assistant_voice_id = "vm1"
        else:
            st.session_state.assistant_voice_id = "vf1"
        changed = True
    if changed:
        save_user_persona(
            supabase,
            user_id,
            st.session_state.assistant_avatar_id,
            st.session_state.assistant_voice_id,
        )


def obter_user_id_logado() -> str:
    """Obtém o user_id da sessão atual."""
    user_obj = st.session_state.get("user")
    user_id = getattr(user_obj, "id", "") if user_obj else ""
    if not user_id:
        user_id = st.session_state.get("auth_user_id", "")
    return user_id or ""


def build_stripe_checkout_link(base_url: str, user_id: str) -> str:
    """
    Adiciona client_reference_id na URL de checkout Stripe.
    Espera uma URL de Checkout real (não use domínio genérico stripe.com).
    """
    raw = (base_url or "").strip()
    if not raw.startswith("http"):
        return raw
    parsed = urlparse(raw)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    params["client_reference_id"] = user_id
    new_query = urlencode(params, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def detect_user_language(text: str) -> str:
    """Detector leve de idioma para reforçar resposta no mesmo idioma do cliente."""
    t = (text or "").strip()
    if detect and t:
        try:
            if DetectorFactory:
                DetectorFactory.seed = 0
            code = detect(t)
            mapping = {
                "pt": "pt-BR",
                "en": "en-US",
                "es": "es-ES",
                "fr": "fr-FR",
            }
            if code in mapping:
                return mapping[code]
        except LangDetectException:
            pass
        except Exception:
            pass

    t = t.lower()
    if any(k in t for k in [" você ", " nao ", " não ", " qual ", " quero ", " por favor ", " obrigado "]):
        return "pt-BR"
    if any(k in t for k in [" the ", " and ", " please ", " i need ", " can you ", "thank you"]):
        return "en-US"
    if any(k in t for k in [" hola ", " gracias ", " por favor", " necesito ", " usted ", " que "]):
        return "es-ES"
    if any(k in t for k in [" bonjour ", " merci ", " s'il", " je ", " vous ", " quoi "]):
        return "fr-FR"
    # padrão seguro para sua base atual
    return "pt-BR"


def detect_user_language_with_confidence(text: str) -> tuple[str, float]:
    """Retorna idioma detectado e confiança aproximada (0.0 a 1.0)."""
    t = (text or "").strip()
    if detect_langs and t:
        try:
            if DetectorFactory:
                DetectorFactory.seed = 0
            probs = detect_langs(t)
            if probs:
                best = probs[0]
                code = getattr(best, "lang", "")
                confidence = float(getattr(best, "prob", 0.0))
                mapping = {
                    "pt": "pt-BR",
                    "en": "en-US",
                    "es": "es-ES",
                    "fr": "fr-FR",
                }
                return mapping.get(code, "pt-BR"), confidence
        except LangDetectException:
            pass
        except Exception:
            pass
    # Fallback sem probabilidade robusta
    return detect_user_language(t), 0.55


def language_instruction(code: str) -> str:
    labels = {
        "pt-BR": "português do Brasil",
        "en-US": "English",
        "es-ES": "español",
        "fr-FR": "français",
    }
    label = labels.get(code, "português do Brasil")
    return (
        f"\n\nImportante: responde em {label} ({code}). "
        "Se não tiveres a certeza, mantém o idioma do utilizador."
    )


def verificar_limite_diario(supabase: Client | None, user_id: str, limite: int = 20) -> tuple[bool, int]:
    """Conta mensagens de usuário enviadas hoje e informa se ainda pode enviar."""
    if _ego_beta_sem_limite():
        return True, 0
    if not supabase:
        return True, 0
    try:
        hoje = datetime.date.today().isoformat()
        res = (
            supabase.table(SUPABASE_HISTORY_TABLE)
            .select("*", count="exact")
            .eq("user_id", user_id)
            .eq("role", "user")
            .gte("created_at", hoje)
            .execute()
        )
        uso_atual = res.count or 0
        return uso_atual < limite, uso_atual
    except Exception:
        # Em caso de falha no contador, não bloqueia o uso.
        return True, 0


def carregar_perfil_usuario(supabase: Client | None, user_id: str) -> dict | None:
    """Busca perfil único do usuário na tabela profiles."""
    if not supabase:
        return None
    try:
        perfil = (
            supabase.table(SUPABASE_PROFILES_TABLE)
            .select("*")
            .eq("id", user_id)
            .single()
            .execute()
        )
        return perfil.data
    except Exception:
        return None


def get_profile_cached(supabase: Client | None, user_id: str) -> dict | None:
    """Perfil em memória na sessão (evita várias idas ao Supabase por rerun)."""
    if not user_id:
        return None
    cached = st.session_state.get("_ego_profile_cache")
    if isinstance(cached, dict) and cached.get("id") == user_id:
        return cached
    prof = carregar_perfil_usuario(supabase, user_id)
    if prof:
        st.session_state["_ego_profile_cache"] = prof
    return prof


def get_access_cached(supabase: Client | None, user_id: str) -> tuple[bool, str]:
    """Trial/Pro com cache curto para não consultar profiles em cada rerun."""
    if not user_id:
        return False, "Expirado"
    key = st.session_state.get("_ego_access_cache_key")
    if key == user_id:
        ts = float(st.session_state.get("_ego_access_cache_ts") or 0)
        if (datetime.datetime.now().timestamp() - ts) < 45:
            return (
                bool(st.session_state.get("_ego_access_cache_ok")),
                str(st.session_state.get("_ego_access_cache_status") or ""),
            )
    ok, status = verificar_acesso(supabase, user_id)
    st.session_state["_ego_access_cache_key"] = user_id
    st.session_state["_ego_access_cache_ok"] = ok
    st.session_state["_ego_access_cache_status"] = status
    st.session_state["_ego_access_cache_ts"] = datetime.datetime.now().timestamp()
    return ok, status


def limite_diario_cached(supabase: Client | None, user_id: str) -> tuple[bool, int]:
    if not user_id:
        return True, 0
    if st.session_state.get("_ego_daily_limit_key") == user_id:
        ts = float(st.session_state.get("_ego_daily_limit_ts") or 0)
        if (datetime.datetime.now().timestamp() - ts) < 30:
            return (
                bool(st.session_state.get("_ego_daily_limit_ok")),
                int(st.session_state.get("_ego_daily_limit_n") or 0),
            )
    ok, n = verificar_limite_diario(supabase, user_id)
    st.session_state["_ego_daily_limit_key"] = user_id
    st.session_state["_ego_daily_limit_ok"] = ok
    st.session_state["_ego_daily_limit_n"] = n
    st.session_state["_ego_daily_limit_ts"] = datetime.datetime.now().timestamp()
    return ok, n


def _cached_gemini_models_list() -> list[str]:
    ts = float(st.session_state.get("_ego_gemini_models_ts") or 0)
    if st.session_state.get("_ego_gemini_models") and (datetime.datetime.now().timestamp() - ts) < 600:
        return list(st.session_state["_ego_gemini_models"])
    if not genai:
        return []
    try:
        genai.configure(api_key=effective_gemini_api_key().strip())
        names = [
            m.name
            for m in genai.list_models()
            if hasattr(m, "supported_generation_methods")
            and "generateContent" in m.supported_generation_methods
        ]
        st.session_state["_ego_gemini_models"] = names
        st.session_state["_ego_gemini_models_ts"] = datetime.datetime.now().timestamp()
        return names
    except Exception:
        return []


def bootstrap_logged_in_session(supabase: Client | None, user_id: str) -> None:
    """Carrega histórico, UI e persona uma vez por sessão de login."""
    if not user_id or not supabase or st.session_state.get("_ego_session_boot_done"):
        return
    u_obj = st.session_state.get("user")
    boot_email = (
        st.session_state.get("ego_profile_email")
        or (getattr(u_obj, "email", None) if u_obj else None)
        or ""
    )
    ok_prof, _ = ensure_user_profile(
        supabase,
        user_id,
        email=str(boot_email or ""),
        full_name=st.session_state.get("global_user_name", ""),
    )
    if ok_prof:
        touch_last_login(supabase, user_id)
    if not st.session_state.get("history_loaded"):
        st.session_state.messages = carregar_historico_do_banco(user_id)
        st.session_state.history_loaded = True
    if not st.session_state.get("ego_ui_state_loaded"):
        merge_ui_state_from_profile(supabase, user_id)
        st.session_state["ego_ui_state_loaded"] = True
    if not st.session_state.get("persona_loaded"):
        avatar_id, voice_id = load_user_persona(supabase, user_id)
        st.session_state.assistant_avatar_id = avatar_id
        st.session_state.assistant_voice_id = voice_id
        st.session_state.persona_loaded = True
    get_profile_cached(supabase, user_id)
    get_access_cached(supabase, user_id)
    if not st.session_state.get("_ego_schema_probed"):
        st.session_state["_ego_schema_status"] = probe_ego_supabase_schema(supabase)
        st.session_state["_ego_schema_probed"] = True
    st.session_state["_ego_session_boot_done"] = True


def _normalize_profile_ui_state(raw: object) -> dict | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return None
        raw = parsed
    if not isinstance(raw, dict):
        return None
    return raw


def _sanitize_display_name(raw: str, *, max_len: int = 80) -> str:
    s = re.sub(r"\s+", " ", (raw or "").strip())
    if not s:
        return ""
    s = re.sub(r"[<>\x00-\x08\x0b\x0c\x0e-\x1f*]", "", s)
    return s[:max_len].strip()


def _resolved_user_display_name() -> str:
    dk = st.session_state.get("display_name_input")
    if isinstance(dk, str) and dk.strip():
        return _sanitize_display_name(dk.strip(), max_len=200)
    un = (st.session_state.get("user_name") or "").strip()
    if un:
        return _sanitize_display_name(un, max_len=200)
    g = (st.session_state.get("global_user_name") or "").strip()
    return _sanitize_display_name(g, max_len=200) if g else ""


def _resolved_assistant_display_name() -> str:
    a = (st.session_state.get("ego_assistant_display_name") or "").strip()
    if a:
        return _sanitize_display_name(a, max_len=48) or "EGO-AI"
    return "EGO-AI"


def build_ui_state_payload() -> dict:
    """Snapshot do estado persistível (sem chaves API)."""
    pdf = str(st.session_state.get("pdf_context") or "")
    truncated = False
    if len(pdf) > UI_STATE_PDF_MAX_CHARS:
        pdf = pdf[:UI_STATE_PDF_MAX_CHARS]
        truncated = True
    nav = str(st.session_state.get("ego_nav") or "Chat").strip()
    if nav not in ALLOWED_EGO_NAV_VALUES:
        nav = "Chat"
    pref = st.session_state.get("gemini_model_preference") or GEMINI_MODEL_FLASH
    if pref not in GEMINI_MODEL_IDS:
        pref = GEMINI_MODEL_FLASH
    uname = _resolved_user_display_name()
    return {
        "v": UI_STATE_VERSION,
        "ego_nav": nav,
        "pdf_context": pdf,
        "pdf_truncated": truncated,
        "gemini_model_preference": pref,
        "user_name": uname[:200],
        "ego_voice_replies": bool(st.session_state.get("ego_voice_replies", True)),
        "ego_tts_volume": max(0, min(100, int(st.session_state.get("ego_tts_volume", 80)))),
        "ego_tts_muted": bool(st.session_state.get("ego_tts_muted", False)),
        "ego_tts_rate": float(st.session_state.get("ego_tts_rate", 1.0)),
        "ego_client_timezone": str(st.session_state.get("ego_client_timezone") or "")[
            :120
        ],
        "ego_client_tz_offset_min": st.session_state.get("ego_client_tz_offset_min"),
        "ego_assistant_display_name": _resolved_assistant_display_name()[:48],
        "ego_name_setup_done": bool(st.session_state.get("ego_name_setup_done")),
    }


def merge_ui_state_from_profile(supabase: Client | None, user_id: str) -> None:
    """Aplica profiles.ui_state ao session_state (não altera auth nem mensagens)."""
    if not supabase or not user_id:
        return
    try:
        res = (
            supabase.table(SUPABASE_PROFILES_TABLE)
            .select("ui_state")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            return
        state = _normalize_profile_ui_state(rows[0].get("ui_state"))
        if state is None:
            return
        if int(state.get("v") or 0) > UI_STATE_VERSION:
            return
        nav = str(state.get("ego_nav") or "").strip()
        if nav in ALLOWED_EGO_NAV_VALUES:
            st.session_state["ego_nav"] = nav
        if "pdf_context" in state and isinstance(state["pdf_context"], str):
            st.session_state["pdf_context"] = state["pdf_context"]
        pref = state.get("gemini_model_preference")
        if isinstance(pref, str) and pref in GEMINI_MODEL_IDS:
            st.session_state["gemini_model_preference"] = pref
        uname = state.get("user_name")
        if isinstance(uname, str) and uname.strip():
            st.session_state["user_name"] = uname.strip()[:200]
        if "ego_voice_replies" in state:
            st.session_state["ego_voice_replies"] = bool(state["ego_voice_replies"])
        tv = state.get("ego_tts_volume")
        if isinstance(tv, bool):
            pass
        elif isinstance(tv, (int, float)):
            st.session_state["ego_tts_volume"] = max(0, min(100, int(tv)))
        if "ego_tts_muted" in state:
            st.session_state["ego_tts_muted"] = bool(state["ego_tts_muted"])
        tr = state.get("ego_tts_rate")
        if isinstance(tr, (int, float)) and tr in (1.0, 1.5, 2.0):
            st.session_state["ego_tts_rate"] = float(tr)
        tz_saved = state.get("ego_client_timezone")
        if isinstance(tz_saved, str):
            tz_ok = _sanitize_client_timezone(tz_saved)
            if tz_ok:
                st.session_state["ego_client_timezone"] = tz_ok
        om = state.get("ego_client_tz_offset_min")
        if isinstance(om, bool):
            pass
        elif isinstance(om, int):
            st.session_state["ego_client_tz_offset_min"] = om
        elif isinstance(om, float) and om.is_integer():
            st.session_state["ego_client_tz_offset_min"] = int(om)
        elif om is not None:
            try:
                st.session_state["ego_client_tz_offset_min"] = int(om)
            except (TypeError, ValueError):
                pass
        asst = state.get("ego_assistant_display_name")
        if isinstance(asst, str) and asst.strip():
            st.session_state["ego_assistant_display_name"] = _sanitize_display_name(
                asst.strip(), max_len=48
            ) or "EGO-AI"
        st.session_state["ego_assistant_display_name_input"] = st.session_state.get(
            "ego_assistant_display_name", "EGO-AI"
        )
        done = state.get("ego_name_setup_done")
        has_uname = bool((st.session_state.get("user_name") or "").strip())
        if done is True:
            st.session_state["ego_name_setup_done"] = True
        elif has_uname:
            st.session_state["ego_name_setup_done"] = True
        elif isinstance(done, bool) and not done:
            st.session_state["ego_name_setup_done"] = False
        else:
            st.session_state["ego_name_setup_done"] = False
    except Exception:
        pass
    finally:
        pl = build_ui_state_payload()
        st.session_state["_ego_ui_state_saved_sig"] = json.dumps(
            pl, ensure_ascii=False, sort_keys=True
        )


def save_ui_state_to_profile(supabase: Client | None, user_id: str, payload: dict) -> bool:
    if not supabase or not user_id:
        return False
    try:
        supabase.table(SUPABASE_PROFILES_TABLE).update({"ui_state": payload}).eq(
            "id", user_id
        ).execute()
        return True
    except Exception:
        return False


def maybe_autosave_ui_state(supabase: Client | None, user_id: str) -> None:
    if not supabase or not user_id or not st.session_state.get("user_logged"):
        return
    now = datetime.datetime.now().timestamp()
    payload = build_ui_state_payload()
    sig = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    if st.session_state.get("_ego_ui_state_saved_sig") == sig:
        return
    if (now - float(st.session_state.get("_ego_last_autosave_ts") or 0)) < EGO_AUTOSAVE_MIN_INTERVAL_SEC:
        return
    if save_ui_state_to_profile(supabase, user_id, payload):
        st.session_state["_ego_ui_state_saved_sig"] = sig
        st.session_state["_ego_last_autosave_ts"] = now


def verificar_acesso(supabase: Client | None, user_id: str) -> tuple[bool, str]:
    """Retorna (acesso_liberado, status): Pro, beta, trial (EGO_TRIAL_DAYS desde profiles.created_at) ou expirado."""
    if not supabase:
        return True, "Modo Local"
    agora = datetime.datetime.now(datetime.timezone.utc)
    beta_fim = _ego_beta_deadline()
    if _ego_beta_sem_limite():
        return True, "Beta (sem limite)"
    if beta_fim and agora < beta_fim:
        return True, "Beta grátis"
    try:
        res = (
            supabase.table(SUPABASE_PROFILES_TABLE)
            .select("created_at,is_pro")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            return True, f"Trial ({EGO_TRIAL_DAYS} dias restantes)"
        data = rows[0]
        is_pro = bool(data.get("is_pro", False))
        if is_pro:
            return True, "Pro"
        created_at = data.get("created_at")
        if not created_at:
            return True, f"Trial ({EGO_TRIAL_DAYS} dias restantes)"
        data_criacao = _parse_ts_iso(str(created_at))
        if not data_criacao:
            return True, f"Trial ({EGO_TRIAL_DAYS} dias restantes)"
        dias_de_uso = max(0, (agora.date() - data_criacao.date()).days)
        restantes = EGO_TRIAL_DAYS - dias_de_uso
        if restantes >= 0:
            return True, f"Trial ({restantes} dias restantes)"
        return False, "Expirado"
    except Exception:
        return True, f"Trial ({EGO_TRIAL_DAYS} dias restantes)"


def _query_param_first(key: str) -> str:
    try:
        qp = st.query_params
        v = qp.get(key)
        if v is None:
            return ""
        if isinstance(v, (list, tuple)):
            return str(v[0] or "").strip()
        return str(v).strip()
    except Exception:
        return ""


def _sanitize_client_timezone(raw: str) -> str:
    s = unquote((raw or "").strip())[:120]
    if not s or ".." in s or len(s) > 80:
        return ""
    if not re.match(r"^[A-Za-z0-9_/+-]+$", s):
        return ""
    return s


def ensure_user_timezone_from_browser() -> None:
    """Após login: lê ?ego_tz= da URL (definido por JS) ou injeta redirect único para capturar IANA."""
    if not st.session_state.get("user_logged"):
        return
    raw_tz = _query_param_first("ego_tz")
    if raw_tz:
        tz_clean = _sanitize_client_timezone(raw_tz)
        raw_off = _query_param_first("ego_tzoff")
        off_min: int | None = None
        if raw_off.strip():
            try:
                off_min = int(raw_off.strip())
            except ValueError:
                off_min = None
        if tz_clean:
            st.session_state["ego_client_timezone"] = tz_clean
            st.session_state["ego_client_tz_offset_min"] = off_min
        elif off_min is not None:
            st.session_state["ego_client_tz_offset_min"] = off_min
        st.session_state.pop("_ego_tz_injected", None)
        for qp_key in ("ego_tz", "ego_tzoff"):
            try:
                if qp_key in st.query_params:
                    del st.query_params[qp_key]
            except Exception:
                pass
        st.rerun()
        return
    if (st.session_state.get("ego_client_timezone") or "").strip():
        return
    if st.session_state.get("_ego_tz_injected"):
        return
    st.session_state["_ego_tz_injected"] = True
    try:
        import streamlit.components.v1 as components
    except ImportError:
        return
    components.html(
        """
<script>
(function() {
  try {
    var root = window.top || window.parent || window;
    if (!root || !root.location) return;
    var u = new URL(root.location.href);
    if (u.searchParams.get('ego_tz')) return;
    var tz = (Intl.DateTimeFormat().resolvedOptions().timeZone || '').trim();
    if (!tz) return;
    var off = String(-new Date().getTimezoneOffset());
    u.searchParams.set('ego_tz', tz);
    u.searchParams.set('ego_tzoff', off);
    root.location.replace(u.toString());
  } catch (e) {}
})();
</script>
""",
        height=0,
        width=0,
    )


def _browser_offset_tzinfo() -> datetime.timezone | None:
    """ego_client_tz_offset_min = `-getTimezoneOffset()` em minutos (ex.: -180 para UTC−3)."""
    off = st.session_state.get("ego_client_tz_offset_min")
    if not isinstance(off, int):
        return None
    try:
        return datetime.timezone(datetime.timedelta(minutes=int(off)))
    except Exception:
        return None


def _effective_local_now() -> datetime.datetime:
    tz_name = (st.session_state.get("ego_client_timezone") or "").strip()
    if tz_name and ZoneInfo is not None:
        try:
            return datetime.datetime.now(ZoneInfo(tz_name))
        except Exception:
            pass
    tz_off = _browser_offset_tzinfo()
    if tz_off is not None:
        return datetime.datetime.now(tz_off)
    return datetime.datetime.now().astimezone()


def _local_now() -> datetime.datetime:
    return _effective_local_now()


def client_datetime_context_instruction() -> str:
    """Relógio sempre derivado em Python (evita o modelo a «adivinhar» data/hora)."""
    tz = (st.session_state.get("ego_client_timezone") or "").strip()
    off_min = st.session_state.get("ego_client_tz_offset_min")
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    loc = _effective_local_now()
    dias_pt = (
        "segunda-feira",
        "terça-feira",
        "quarta-feira",
        "quinta-feira",
        "sexta-feira",
        "sábado",
        "domingo",
    )
    wd = dias_pt[loc.weekday()]
    utc_iso = utc_now.isoformat(timespec="seconds")
    loc_iso = loc.isoformat(timespec="seconds")
    lines: list[str] = [
        "\n\nRELÓGIO DE REFERÊNCIA (calculado pela app — para «que dia/hora é», usa **apenas** isto, nunca estimes):",
        f"- Agora em UTC: **{utc_iso}**",
        f"- Agora no fuso local do utilizador: **{loc_iso}** (dia da semana: **{wd}**).",
    ]
    if tz:
        lines.append(f"- Fuso IANA sincronizado do dispositivo: **{tz}**.")
    if isinstance(off_min, int):
        lines.append(
            f"- Offset guardado a partir do browser (minutos, convencão interna da app): **{off_min}**."
        )
    if not tz and not isinstance(off_min, int):
        lines.append(
            "- **Aviso:** o fuso do dispositivo ainda não sincronizou; o «local» acima pode ser o do servidor."
        )
    lines.extend(
        [
            "- Usa este instante local para lembretes, recorrências e qualquer pergunta sobre data/hora.",
            "- **Não perguntes** em que país, cidade ou fuso a pessoa está para perguntas simples de relógio.",
        ]
    )
    return "\n".join(lines) + "\n"


def names_and_identity_instruction() -> str:
    uname = _resolved_user_display_name()
    alias = _resolved_assistant_display_name()
    if uname:
        who_line = (
            f"- O utilizador chama-se «{uname}». Trata-o por esse nome de forma natural, "
            "sobretudo em cumprimentos e mensagens acolhedoras.\n"
        )
    else:
        who_line = (
            "- Ainda não indicou o nome preferido; cumprimenta de forma calorosa sem insistir "
            "em perguntas repetidas sobre o nome, salvo se for essencial ao pedido.\n"
        )
    return (
        "\n\nIDENTIDADE E TRATAMENTO:\n"
        f"{who_line}"
        f"- Tu apresentas-te e falas na primeira pessoa como «{alias}» — é o nome que o utilizador "
        "escolheu para ti; usa-o com consistência na conversa.\n"
        "- O produto/serviço chama-se EGO-AI; podes mencionar essa marca quando falares da aplicação ou da empresa, "
        f"mas na relação direta contigo és «{alias}» para este utilizador.\n"
        "- Não voltes a perguntar como te chamar ou como chamar o utilizador se já estiver definido acima.\n"
    )


def _default_time_for_agenda_date(d_val: datetime.date) -> datetime.time:
    """Evita horário padrão no passado quando a data é hoje."""
    ref = _local_now()
    if d_val != ref.date():
        return datetime.time(9, 0)
    slot = ref + datetime.timedelta(minutes=30)
    slot = slot.replace(second=0, microsecond=0)
    if slot.date() != d_val:
        return datetime.time(23, 55)
    return slot.time()


def _agenda_horizon_utc(ref: datetime.datetime | None = None) -> datetime.datetime:
    base = ref or datetime.datetime.now(datetime.timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=datetime.timezone.utc)
    return base + datetime.timedelta(days=AGENDA_HORIZON_DAYS)


def _infer_year_for_month_day(month: int, day: int, ref: datetime.datetime) -> int | None:
    year = ref.year
    for candidate_year in (year, year + 1):
        try:
            d = datetime.date(candidate_year, month, day)
        except ValueError:
            continue
        if d >= ref.date():
            return candidate_year
    return year + 1


def _parse_partial_reminder_datetime(
    raw: str, ref: datetime.datetime | None = None
) -> datetime.datetime | None:
    """Interpreta datas incompletas: mês atual se faltar mês; ano atual (ou próximo) se faltar ano."""
    ref = ref or _local_now()
    tz = ref.tzinfo or datetime.timezone.utc
    s = (raw or "").strip()
    if not s:
        return None

    def _combine(
        year: int, month: int, day: int, hour: int = 9, minute: int = 0
    ) -> datetime.datetime | None:
        try:
            return datetime.datetime(year, month, day, hour, minute, tzinfo=tz)
        except ValueError:
            return None

    m = re.match(
        r"^(\d{4})-(\d{1,2})-(\d{1,2})(?:[T\s](\d{1,2}):(\d{2}))?",
        s,
    )
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        h = int(m.group(4) or 9)
        mi = int(m.group(5) or 0)
        return _combine(y, mo, d, h, mi)

    m = re.match(
        r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})(?:\s+(\d{1,2}):(\d{2}))?",
        s,
    )
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        h = int(m.group(4) or 9)
        mi = int(m.group(5) or 0)
        return _combine(y, mo, d, h, mi)

    m = re.match(
        r"^(\d{1,2})[/.-](\d{1,2})(?:\s+(\d{1,2}):(\d{2}))?$",
        s,
    )
    if m:
        d, mo = int(m.group(1)), int(m.group(2))
        h = int(m.group(3) or 9)
        mi = int(m.group(4) or 0)
        y = _infer_year_for_month_day(mo, d, ref)
        if y is None:
            return None
        return _combine(y, mo, d, h, mi)

    m = re.match(
        r"^(\d{1,2})(?:\s+(?:às|as|at)\s+)?(\d{1,2}):(\d{2})$",
        s,
        re.IGNORECASE,
    )
    if m:
        d = int(m.group(1))
        h, mi = int(m.group(2)), int(m.group(3))
        mo = ref.month
        y = _infer_year_for_month_day(mo, d, ref)
        if y is None:
            return None
        return _combine(y, mo, d, h, mi)

    return None


def _parse_ts_iso(value: str | None) -> datetime.datetime | None:
    if not value or not str(value).strip():
        return None
    try:
        dt = datetime.datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.astimezone(datetime.timezone.utc)
    except ValueError:
        return None


def _coerce_reminder_to_utc(
    value: str | datetime.datetime | int | float | None,
    *,
    ref: datetime.datetime | None = None,
) -> datetime.datetime | None:
    """Converte valor do lembrete para instante em UTC (sem validar passado/horizonte)."""
    ref = ref or _local_now()
    if value is None:
        return None
    if type(value) is bool:
        return None
    if isinstance(value, (dict, list)):
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.datetime.fromtimestamp(
                float(value), tz=datetime.timezone.utc
            )
        except (OSError, OverflowError, ValueError):
            return None
    if isinstance(value, datetime.datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ref.tzinfo or datetime.timezone.utc)
        return dt.astimezone(datetime.timezone.utc)
    raw = str(value).strip()
    if not raw:
        return None
    parsed = _parse_ts_iso(raw)
    if parsed:
        return parsed
    partial = _parse_partial_reminder_datetime(raw, ref)
    if not partial:
        return None
    return partial.astimezone(datetime.timezone.utc)


def normalize_scheduled_at(
    value: str | datetime.datetime | int | float | None,
    *,
    ref: datetime.datetime | None = None,
) -> datetime.datetime | None:
    """
    Normaliza data/hora do lembrete (UTC): ano/mês implícitos, só aceita até AGENDA_HORIZON_DAYS.
    Aceita ISO (str), datetime, timestamp Unix (int/float).
    """
    dt_utc = _coerce_reminder_to_utc(value, ref=ref)
    if not dt_utc:
        return None
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    horizon = _agenda_horizon_utc(now_utc)
    if dt_utc < now_utc - REMINDER_PAST_GRACE:
        return None
    if dt_utc > horizon:
        return None
    return dt_utc


def extract_ego_reminders_from_reply(text: str) -> tuple[str, list[dict]]:
    """Remove [[EGO_REMINDER:{json}]] do texto e devolve lembretes válidos."""
    marker = "[[EGO_REMINDER:"
    if marker not in text:
        return text, []
    idx = text.find(marker)
    end = text.find("]]", idx)
    if end == -1:
        return text, []
    raw = text[idx + len(marker) : end].strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z0-9]*\s*", "", raw)
        raw = re.sub(r"\s*```\s*$", "", raw).strip()
    clean = (text[:idx].rstrip() + "\n" + text[end + 2 :].lstrip()).strip()
    obj: object = None
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        j0, j1 = raw.find("{"), raw.rfind("}")
        if j0 != -1 and j1 > j0:
            try:
                obj = json.loads(raw[j0 : j1 + 1])
            except json.JSONDecodeError:
                return text, []
        else:
            return text, []
    if isinstance(obj, dict) and obj.get("scheduled_at") not in (None, ""):
        return clean, [obj]
    return text, []


def reminder_slot_windows(
    scheduled_at: datetime.datetime,
) -> list[tuple[datetime.datetime, datetime.datetime, str]]:
    """Janelas [início, fim) para T-10, T-5 e hora T (última com margem curta)."""
    if scheduled_at.tzinfo is None:
        scheduled_at = scheduled_at.replace(tzinfo=datetime.timezone.utc)
    t0 = scheduled_at - datetime.timedelta(minutes=REMINDER_MINUTES_BEFORE)
    return [
        (t0, t0 + datetime.timedelta(minutes=REMINDER_NUDGE_MINUTES), "first"),
        (
            t0 + datetime.timedelta(minutes=REMINDER_NUDGE_MINUTES),
            scheduled_at,
            "mid",
        ),
        (
            scheduled_at,
            scheduled_at + datetime.timedelta(minutes=3),
            "final",
        ),
    ]


def reminder_current_window(
    now: datetime.datetime, scheduled_at: datetime.datetime
) -> tuple[datetime.datetime, datetime.datetime, str] | None:
    if now.tzinfo is None:
        now = now.replace(tzinfo=datetime.timezone.utc)
    for a, b, tag in reminder_slot_windows(scheduled_at):
        if a <= now < b:
            return (a, b, tag)
    return None


def list_upcoming_reminders(
    supabase: Client | None,
    user_id: str,
    *,
    hours_back: int = 0,
    days_ahead: int = AGENDA_HORIZON_DAYS,
) -> list[dict]:
    if not supabase or not user_id:
        return []
    if not ensure_supabase_auth_client(supabase):
        return []
    now = datetime.datetime.now(datetime.timezone.utc)
    start = (now - datetime.timedelta(hours=hours_back)).isoformat()
    end = (now + datetime.timedelta(days=days_ahead)).isoformat()
    try:
        res = (
            supabase.table(SUPABASE_REMINDERS_TABLE)
            .select("*")
            .eq("user_id", user_id)
            .eq("dismissed", False)
            .gte("scheduled_at", start)
            .lte("scheduled_at", end)
            .order("scheduled_at")
            .execute()
        )
        return list(res.data or [])
    except Exception:
        return []


def list_reminders_for_alarm_tick(
    supabase: Client | None, user_id: str
) -> list[dict]:
    """Lembretes ativos num intervalo largo; a janela exata (T-10 … T) filtra em Python."""
    if not supabase or not user_id:
        return []
    now = datetime.datetime.now(datetime.timezone.utc)
    look_from = (now - datetime.timedelta(hours=2)).isoformat()
    look_to = (now + datetime.timedelta(hours=72)).isoformat()
    try:
        res = (
            supabase.table(SUPABASE_REMINDERS_TABLE)
            .select("*")
            .eq("user_id", user_id)
            .eq("dismissed", False)
            .gte("scheduled_at", look_from)
            .lte("scheduled_at", look_to)
            .execute()
        )
        return list(res.data or [])
    except Exception:
        return []


def insert_reminder_row(
    supabase: Client | None,
    user_id: str,
    *,
    title: str,
    scheduled_at: object,
    announce: str = "",
) -> tuple[bool, str]:
    if not supabase or not user_id:
        return False, "Sessão ou Supabase indisponível."
    if scheduled_at is None or scheduled_at == "":
        return False, "Data/hora do lembrete em falta."
    if isinstance(scheduled_at, (dict, list)):
        return False, "scheduled_at inválido (objeto em vez de data/hora)."
    if not isinstance(scheduled_at, (str, datetime.datetime, int, float)):
        return False, "Tipo de data/hora não suportado no lembrete."
    norm = normalize_scheduled_at(scheduled_at)
    if not norm:
        coerced = _coerce_reminder_to_utc(scheduled_at)
        if not coerced:
            return (
                False,
                "Data/hora do lembrete inválida. Use ISO com fuso "
                "(ex.: 2026-06-01T15:30:00-03:00).",
            )
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        if coerced < now_utc - REMINDER_PAST_GRACE:
            return False, "A data/hora já passou. Escolha um horário no futuro."
        return (
            False,
            f"Só é possível agendar nos próximos {AGENDA_HORIZON_DAYS} dias.",
        )
    row: dict = {
        "user_id": user_id,
        "title": (title or "Lembrete")[:500],
        "scheduled_at": norm.astimezone(datetime.timezone.utc).isoformat(),
        "announce": (announce or title or "")[:2000],
    }
    if not ensure_supabase_auth_client(supabase):
        return False, "Sessão expirada. Saia e entre de novo para gravar lembretes/reuniões."
    try:
        res = supabase.table(SUPABASE_REMINDERS_TABLE).insert(row).select("id").execute()
        if not (res.data or []):
            return False, "O lembrete não foi confirmado pelo Supabase (resposta vazia)."
        return True, ""
    except Exception as e:  # noqa: BLE001
        err = str(e).lower()
        if _supabase_table_missing_error(e):
            return (
                False,
                "Tabela `reminders` em falta. No Supabase → SQL Editor, execute "
                "`supabase/bootstrap_ego_schema.sql` (ou `reminders.sql`).",
            )
        if "row-level security" in err or "rls" in err or "42501" in err:
            return (
                False,
                "Permissão negada ao salvar (RLS). Confirme se está logado e se as policies de "
                "`reminders` existem.",
            )
        return False, f"Erro ao salvar no banco: {e}"


def process_assistant_reminders(
    supabase: Client | None, user_id: str, reply: str
) -> str:
    clean, items = extract_ego_reminders_from_reply(reply)
    if not user_id or not supabase or not items:
        return clean
    msgs: list[str] = []
    for it in items:
        raw_sched = it.get("scheduled_at")
        if raw_sched is None or raw_sched == "":
            msgs.append("Lembrete sem data/hora no marcador.")
            continue
        if isinstance(raw_sched, (dict, list)):
            msgs.append("Marcador de lembrete com scheduled_at inválido.")
            continue
        title = str(it.get("title") or "Lembrete")[:500]
        announce = str(it.get("announce") or title)[:2000]
        ok, err = insert_reminder_row(
            supabase,
            user_id,
            title=title,
            scheduled_at=raw_sched,
            announce=announce,
        )
        if not ok and err:
            msgs.append(err)
    if msgs:
        st.session_state["_ego_reminder_warn"] = " ".join(msgs)[:1500]
    return clean


def _parse_horario_br(v: object) -> datetime.time | None:
    """Aceita '8:00', '08:00', '08:00:00' ou objeto vindo do PostgREST."""
    if v is None:
        return None
    raw = str(v).strip()
    if not raw:
        return None
    raw = raw.replace("T", " ").split()[0] if " " in raw.replace("T", " ") else raw
    parts = raw.replace(".", ":").split(":")
    try:
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        s = int(parts[2]) if len(parts) > 2 else 0
        if not (0 <= h <= 23 and 0 <= m <= 59 and 0 <= s <= 59):
            return None
        return datetime.time(h, m, s)
    except (ValueError, IndexError):
        return None


def _horario_to_pg(t: datetime.time) -> str:
    return t.strftime("%H:%M:%S")


def _normalize_agenda_dias_csv(raw: str) -> tuple[str | None, str | None]:
    """Devolve (csv canónico seg,ter,... ou None, erro)."""
    if not raw or not str(raw).strip():
        return None, "dias_da_semana vazio"
    low = str(raw).lower()
    if any(
        x in low
        for x in (
            "segunda a sexta",
            "seg a sex",
            "seg–sex",
            "mon-fri",
            "monday to friday",
            "dias úteis",
            "dias uteis",
        )
    ):
        return "seg,ter,qua,qui,sex", None
    if "todos os dias" in low or "todo dia" in low or "diário" in low or "diario" in low:
        return "seg,ter,qua,qui,sex,sab,dom", None
    aliases = {
        "segunda": "seg",
        "segunda-feira": "seg",
        "terça": "ter",
        "terca": "ter",
        "terça-feira": "ter",
        "quarta": "qua",
        "quarta-feira": "qua",
        "quinta": "qui",
        "quinta-feira": "qui",
        "sexta": "sex",
        "sexta-feira": "sex",
        "sábado": "sab",
        "sabado": "sab",
        "domingo": "dom",
    }
    seen: list[str] = []
    seen_set: set[str] = set()
    for part in str(raw).lower().replace(";", ",").split(","):
        tok = part.strip()
        if not tok:
            continue
        tok = aliases.get(tok, tok)
        if tok not in VALID_AGENDA_DOW:
            return None, f"dia inválido: {tok}"
        if tok not in seen_set:
            seen_set.add(tok)
            seen.append(tok)
    if not seen:
        return None, "nenhum dia válido"
    seen.sort(key=lambda d: DOW_PT_ORDER.index(d))
    return ",".join(seen), None


def refresh_user_agenda_snapshot(supabase: Client | None, user_id: str) -> list[dict]:
    rows = fetch_user_agenda_rows(supabase, user_id)
    st.session_state["_ego_agenda_rows_snapshot"] = rows
    return rows


def fetch_user_agenda_rows(supabase: Client | None, user_id: str) -> list[dict]:
    if not supabase or not user_id:
        return []
    if not ensure_supabase_auth_client(supabase):
        st.session_state["_ego_agenda_fetch_warn"] = (
            "Sessão Supabase expirada. Faça **Sair** e **Entrar** de novo para carregar a agenda."
        )
        return []
    try:
        res = (
            supabase.table(SUPABASE_AGENDA_TABLE)
            .select("id,titulo,horario,dias_da_semana,data_criacao")
            .eq("user_id", user_id)
            .order("data_criacao", desc=True)
            .execute()
        )
        return list(res.data or [])
    except Exception as e:  # noqa: BLE001
        if _supabase_table_missing_error(e):
            st.session_state["_ego_agenda_fetch_warn"] = (
                "Tabela `agenda` em falta. Execute `supabase/bootstrap_ego_schema.sql` no Supabase."
            )
        return []


def insert_agenda_row(
    supabase: Client | None,
    user_id: str,
    *,
    titulo: str,
    horario: object,
    dias_da_semana: str,
) -> tuple[bool, str]:
    if not supabase or not user_id:
        return False, "Sessão indisponível."
    t = _parse_horario_br(horario)
    if not t:
        return False, "Horário inválido (use HH:MM, ex.: 08:00)."
    dias_ok, err = _normalize_agenda_dias_csv(dias_da_semana)
    if not dias_ok:
        return False, err or "Dias da semana inválidos."
    tit = (titulo or "").strip()[:500] or "Compromisso"
    row = {
        "user_id": user_id,
        "titulo": tit,
        "horario": _horario_to_pg(t),
        "dias_da_semana": dias_ok[:500],
    }
    if not ensure_supabase_auth_client(supabase):
        return False, "Sessão expirada. Saia e entre de novo para gravar na agenda."
    try:
        res = supabase.table(SUPABASE_AGENDA_TABLE).insert(row).select("id").execute()
        if not (res.data or []):
            return False, "A agenda não confirmou a gravação (resposta vazia do Supabase)."
        return True, ""
    except Exception as e:  # noqa: BLE001
        es = str(e).lower()
        if _supabase_table_missing_error(e):
            return (
                False,
                "Tabela `agenda` em falta. No Supabase → SQL Editor, execute "
                "`supabase/bootstrap_ego_schema.sql` (ou `agenda.sql`).",
            )
        if "row-level security" in es or "rls" in es or "42501" in es:
            return False, "Sem permissão para gravar na agenda (RLS)."
        return False, f"Erro ao salvar agenda: {e}"


def delete_agenda_row(supabase: Client | None, user_id: str, agenda_id: str) -> bool:
    if not supabase or not user_id or not agenda_id:
        return False
    try:
        supabase.table(SUPABASE_AGENDA_TABLE).delete().eq("id", agenda_id).eq(
            "user_id", user_id
        ).execute()
        return True
    except Exception:
        return False


def extract_ego_agenda_from_reply(text: str) -> tuple[str, list[dict]]:
    marker = "[[EGO_AGENDA:"
    if marker not in text:
        return text, []
    idx = text.find(marker)
    end = text.find("]]", idx)
    if end == -1:
        return text, []
    raw = text[idx + len(marker) : end].strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z0-9]*\s*", "", raw)
        raw = re.sub(r"\s*```\s*$", "", raw).strip()
    clean = (text[:idx].rstrip() + "\n" + text[end + 2 :].lstrip()).strip()
    obj: object = None
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        j0, j1 = raw.find("{"), raw.rfind("}")
        if j0 != -1 and j1 > j0:
            try:
                obj = json.loads(raw[j0 : j1 + 1])
            except json.JSONDecodeError:
                return text, []
        else:
            return text, []
    if not isinstance(obj, dict):
        return text, []
    tit = obj.get("titulo") or obj.get("title")
    hor = obj.get("horario") or obj.get("time")
    dias = obj.get("dias_da_semana") or obj.get("dias") or obj.get("weekdays")
    if tit and hor is not None and dias:
        return clean, [obj]
    return text, []


def process_assistant_agenda(supabase: Client | None, user_id: str, reply: str) -> str:
    clean, items = extract_ego_agenda_from_reply(reply)
    if not user_id or not supabase or not items:
        return clean
    msgs: list[str] = []
    for it in items:
        tit = str(it.get("titulo") or it.get("title") or "").strip()
        hor = it.get("horario") if it.get("horario") is not None else it.get("time")
        dias = it.get("dias_da_semana") or it.get("dias") or it.get("weekdays")
        ok, err = insert_agenda_row(
            supabase,
            user_id,
            titulo=tit,
            horario=hor,
            dias_da_semana=str(dias),
        )
        if ok:
            refresh_user_agenda_snapshot(supabase, user_id)
            try:
                st.toast("Compromisso recorrente guardado na agenda.", icon="📅")
            except Exception:
                pass
        elif err:
            msgs.append(f"Agenda: {err}")
    if msgs:
        prev = st.session_state.get("_ego_reminder_warn")
        add = " ".join(msgs)[:800]
        st.session_state["_ego_reminder_warn"] = (
            f"{prev} {add}".strip() if prev else add
        )[:1500]
    return clean


def next_recurring_agenda_message_today(rows: list[dict]) -> str | None:
    """Próximo compromisso recorrente ainda hoje (fuso local), ou None."""
    now = datetime.datetime.now().astimezone()
    today = now.date()
    wk = today.weekday()
    abbr = DOW_PT_ORDER[wk]
    tz = now.tzinfo or datetime.timezone.utc
    candidates: list[tuple[datetime.datetime, str]] = []
    for row in rows:
        dias_raw = (row.get("dias_da_semana") or "").lower()
        days_set = {d.strip() for d in dias_raw.split(",") if d.strip()}
        if abbr not in days_set:
            continue
        titulo = (row.get("titulo") or "Compromisso").strip()
        hor = _parse_horario_br(row.get("horario"))
        if not hor:
            continue
        try:
            dt_local = datetime.datetime.combine(today, hor, tzinfo=tz)
        except (TypeError, ValueError):
            continue
        if dt_local > now:
            candidates.append((dt_local, titulo))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    t0, title = candidates[0]
    hm = t0.strftime("%H:%M")
    return f"🔔 Lembrete: o seu **{title}** é hoje às **{hm}**."


_DOW_LABEL_PT = {
    "seg": "Seg",
    "ter": "Ter",
    "qua": "Qua",
    "qui": "Qui",
    "sex": "Sex",
    "sab": "Sáb",
    "dom": "Dom",
}


def _format_reminder_display(scheduled_raw: object) -> tuple[str, str, str, str]:
    """Data legível, hora, etiqueta relativa (Hoje/Amanhã) e classe CSS extra."""
    sch = _parse_ts_iso(scheduled_raw)
    if not sch:
        return "—", "—", "", ""
    loc = sch.astimezone()
    now = _local_now()
    date_line = loc.strftime("%d/%m")
    time_line = loc.strftime("%H:%M")
    day_delta = (loc.date() - now.date()).days
    if day_delta == 0:
        rel, extra = "Hoje", "is-today"
    elif day_delta == 1:
        rel, extra = "Amanhã", "is-soon"
    elif day_delta < 0:
        rel, extra = "Passado", ""
    elif day_delta <= 7:
        rel, extra = f"Em {day_delta} dias", "is-soon"
    else:
        rel, extra = loc.strftime("%d %b"), ""
    return date_line, time_line, rel, extra


def _format_snooze_label(snooze_raw: object) -> str:
    sn = _parse_ts_iso(snooze_raw)
    if not sn:
        return ""
    return f"Adiado até {sn.astimezone().strftime('%d/%m %H:%M')}"


def _reminder_card_html(row: dict) -> str:
    title = html.escape(str(row.get("title") or "Lembrete"))
    announce = (row.get("announce") or row.get("title") or "").strip()
    announce_html = (
        f'<p class="ego-r-announce">{html.escape(announce)}</p>' if announce else ""
    )
    date_line, time_line, rel, extra_cls = _format_reminder_display(row.get("scheduled_at"))
    snooze = _format_snooze_label(row.get("snooze_until"))
    pills = f'<span class="ego-pill rel">{html.escape(rel)}</span>' if rel else ""
    if snooze:
        pills += f'<span class="ego-pill snooze">{html.escape(snooze)}</span>'
    cls = f"ego-reminder-card {extra_cls}".strip()
    return (
        f'<div class="{cls}">'
        f'<div class="ego-reminder-when">'
        f'<span class="ego-r-time">{html.escape(time_line)}</span>'
        f'<span class="ego-r-date">{html.escape(date_line)}</span>'
        f"</div>"
        f'<div class="ego-reminder-body">'
        f'<p class="ego-r-title">{title}</p>'
        f"{announce_html}"
        f'<div class="ego-reminder-meta">{pills}</div>'
        f"</div></div>"
    )


def _agenda_card_html(row: dict) -> str:
    tit = html.escape(str(row.get("titulo") or "Compromisso"))
    hor = html.escape(str(row.get("horario") or "")[:5])
    dias_raw = str(row.get("dias_da_semana") or "")
    chips = "".join(
        f'<span class="ego-dow-chip">{html.escape(_DOW_LABEL_PT.get(d.strip(), d.strip()))}</span>'
        for d in dias_raw.split(",")
        if d.strip()
    )
    return (
        f'<div class="ego-agenda-card">'
        f'<p class="ego-a-title">{tit}</p>'
        f'<div class="ego-a-row">'
        f'<span class="ego-pill recurring">{hor}</span>{chips}'
        f"</div></div>"
    )


def _reminder_alarm_html(tag: str, title: str, announce: str, when_local: str) -> str:
    title_e = html.escape(title or "Lembrete")
    when_e = html.escape(when_local)
    if tag == "first":
        tag_label = "10 min antes"
        sub = html.escape((announce or title or "").strip())
        detail = f"Compromisso às <strong>{when_e}</strong>"
    elif tag == "final":
        tag_label = "Agora"
        sub = title_e
        detail = f"<strong>{when_e}</strong>"
    else:
        tag_label = "Em breve"
        sub = title_e
        detail = f"Faltam poucos minutos para <strong>{when_e}</strong>"
    return (
        f'<div class="ego-alarm-banner">'
        f'<div class="ego-alarm-tag">{html.escape(tag_label)}</div>'
        f'<p class="ego-alarm-title">{sub}</p>'
        f'<p class="ego-alarm-sub">{detail}</p>'
        f"</div>"
    )


def render_recurring_agenda_banner(supabase: Client | None, user_id: str) -> None:
    if not user_id:
        return
    rows = st.session_state.get("_ego_agenda_rows_snapshot")
    if not isinstance(rows, list):
        rows = fetch_user_agenda_rows(supabase, user_id)
    if not rows:
        return
    msg = next_recurring_agenda_message_today(rows)
    if msg:
        st.info(msg)


def render_sidebar_agenda_panel(supabase: Client | None, user_id: str) -> None:
    if not user_id:
        return
    rows = st.session_state.get("_ego_agenda_rows_snapshot")
    if not isinstance(rows, list):
        rows = fetch_user_agenda_rows(supabase, user_id)
    with st.sidebar.expander("📅 Minha Agenda", expanded=False):
        if not rows:
            st.caption("Nenhum hábito recorrente. Diga no chat: *marque academia de segunda a sexta às 8h*.")
            return
        st.caption("Recorrente · horário local")
        for row in rows[:20]:
            aid = str(row.get("id") or "")
            st.caption(f"{row.get('titulo') or '—'} · {row.get('dias_da_semana') or ''} · {row.get('horario') or ''}")
            if aid and st.button("Remover", key=f"agdel_{aid}", use_container_width=True):
                if delete_agenda_row(supabase, user_id, aid):
                    st.rerun()


def dismiss_reminder(supabase: Client | None, user_id: str, reminder_id: str) -> None:
    if not supabase or not user_id or not reminder_id:
        return
    try:
        supabase.table(SUPABASE_REMINDERS_TABLE).update({"dismissed": True}).eq(
            "id", reminder_id
        ).eq("user_id", user_id).execute()
    except Exception:
        pass


def snooze_reminder_minutes(
    supabase: Client | None, user_id: str, reminder_id: str, minutes: int = 5
) -> None:
    if not supabase or not user_id or not reminder_id:
        return
    until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        minutes=minutes
    )
    try:
        supabase.table(SUPABASE_REMINDERS_TABLE).update(
            {"snooze_until": until.isoformat()}
        ).eq("id", reminder_id).eq("user_id", user_id).execute()
    except Exception:
        pass


def _edge_voice_for_assistant(voice_id: str) -> str:
    return EDGE_TTS_VOICE_MAP.get(str(voice_id or "").strip(), DEFAULT_EDGE_TTS_VOICE)


def _tts_cache_key(text: str, voice_id: str) -> str:
    payload = f"{voice_id}:{text[:2400]}".encode("utf-8", errors="ignore")
    return hashlib.sha256(payload).hexdigest()[:20]


def synthesize_speech_mp3(text: str, voice_id: str) -> bytes | None:
    """Gera MP3 no servidor (edge-tts). Funciona onde o Web Speech do iframe falha."""
    plain = (text or "").strip()[:3000]
    if not plain:
        return None
    ck = _tts_cache_key(plain, voice_id)
    cache: dict[str, bytes] = st.session_state.setdefault("_ego_mp3_cache", {})
    if ck in cache:
        return cache[ck]
    edge_voice = _edge_voice_for_assistant(voice_id)
    try:
        import asyncio

        import edge_tts

        async def _run() -> bytes:
            communicate = edge_tts.Communicate(plain, edge_voice)
            data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    data += chunk["data"]
            return data

        data = asyncio.run(_run())
    except Exception:
        return None
    if not data:
        return None
    if len(cache) > 40:
        cache.clear()
    cache[ck] = data
    return data


def _ego_pause_all_audio_elements() -> None:
    try:
        import streamlit.components.v1 as components
    except ImportError:
        return
    components.html(
        """
<script>
(function() {
  function pauseAll(doc) {
    if (!doc) return;
    try {
      doc.querySelectorAll("audio").forEach(function(a) {
        try { a.pause(); a.currentTime = 0; } catch (e) {}
      });
    } catch (e) {}
  }
  pauseAll(document);
  try { pauseAll(window.parent.document); } catch (e) {}
  try {
    var s = window.speechSynthesis || (window.parent && window.parent.speechSynthesis);
    if (s) s.cancel();
  } catch (e) {}
})();
</script>
        """,
        height=0,
        width=0,
    )


def _ego_tts_playback_volume() -> float:
    return max(0.0, min(1.0, float(st.session_state.get("ego_tts_volume", 80)) / 100.0))


def _ego_tts_playback_rate() -> float:
    rate = float(st.session_state.get("ego_tts_rate", 1.0))
    if rate not in (1.0, 1.5, 2.0):
        return 1.0
    return rate


_EGO_TTS_RATE_LABELS = ("1x", "1.5x", "2x")
_EGO_TTS_RATE_VALUES = (1.0, 1.5, 2.0)


def _ego_apply_audio_playback_rate(rate: float) -> None:
    try:
        import streamlit.components.v1 as components
    except ImportError:
        return
    r = max(0.5, min(3.0, float(rate)))
    components.html(
        f"""
<script>
(function() {{
  var rate = {r};
  function apply(doc) {{
    if (!doc) return;
    try {{
      doc.querySelectorAll("audio").forEach(function(a) {{
        try {{ a.playbackRate = rate; }} catch (e) {{}}
      }});
    }} catch (e) {{}}
  }}
  apply(document);
  try {{ apply(window.parent.document); }} catch (e) {{}}
}})();
</script>
        """,
        height=0,
        width=0,
    )


def _ego_tts_try_autoplay_audio(vol: float, rate: float) -> None:
    """Tenta dar play no último <audio> (autoplay do st.audio falha em alguns browsers)."""
    try:
        import streamlit.components.v1 as components
    except ImportError:
        return
    v = max(0.0, min(1.0, float(vol)))
    r = max(0.5, min(3.0, float(rate)))
    components.html(
        f"""
<script>
(function() {{
  var vol = {v};
  var rate = {r};
  function run(doc) {{
    if (!doc) return;
    var list = [];
    try {{ list = doc.querySelectorAll("audio"); }} catch (e) {{ return; }}
    if (!list.length) return;
    var a = list[list.length - 1];
    try {{
      a.volume = vol;
      a.playbackRate = rate;
      if (vol > 0) a.play().catch(function() {{}});
    }} catch (e) {{}}
  }}
  run(document);
  try {{ run(window.parent.document); }} catch (e) {{}}
}})();
</script>
        """,
        height=0,
        width=0,
    )


def queue_assistant_speech(
    text: str, html_key: str, *, lang_hint: str | None = None, max_chars: int = 3500
) -> None:
    """Prepara áudio MP3 para reproduzir no leitor Streamlit."""
    if st.session_state.get("ego_tts_muted"):
        return
    plain = _plain_text_for_speech((text or "")[:max_chars])
    if not plain:
        return
    vid = str(st.session_state.get("assistant_voice_id", "vf1"))
    mp3 = synthesize_speech_mp3(plain, vid)
    if not mp3:
        st.session_state["_ego_tts_error"] = (
            "Não foi possível gerar áudio. Instale: pip install edge-tts"
        )
        return
    st.session_state.pop("_ego_tts_error", None)
    st.session_state["_ego_tts_playback"] = {
        "mp3": mp3,
        "key": html_key,
        "vol": int(st.session_state.get("ego_tts_volume", 80)),
        "rate": _ego_tts_playback_rate(),
        "lang": lang_hint,
    }


def render_tts_playback_player() -> None:
    """Leitor de áudio visível (st.audio) — o utilizador pode dar play se o autoplay falhar."""
    pb = st.session_state.get("_ego_tts_playback")
    if not pb or not pb.get("mp3"):
        return
    mp3 = pb["mp3"]
    vol = _ego_tts_playback_volume()
    rate = _ego_tts_playback_rate()
    st.markdown("**Voz da assistente**")
    st.caption(
        f"Velocidade {rate}x · se não ouvir, prima ▶ no leitor."
    )
    st.audio(mp3, format="audio/mp3", autoplay=vol > 0)
    _ego_apply_audio_playback_rate(rate)
    if vol > 0:
        _ego_tts_try_autoplay_audio(vol, rate)


def inject_ego_tts_controller() -> None:
    """Compatibilidade: controlo de áudio via st.audio (sem motor no iframe)."""
    return


def render_tts_controls() -> None:
    """Barra de controlo: velocidade, volume e mudo."""
    st.markdown(
        '<p class="ego-tts-controls-hint">Controlo da voz da IA (áudio gerado no servidor)</p>',
        unsafe_allow_html=True,
    )
    err = st.session_state.pop("_ego_tts_error", None)
    if err:
        st.warning(str(err))
    vol_now = int(st.session_state.get("ego_tts_volume", 80))
    if vol_now <= 0:
        st.caption("Volume em 0 — sobe o slider para ouvir.")
    if st.session_state.get("ego_tts_muted"):
        st.caption("Mudo ligado — desliga «Mudo» para ouvir.")
    cur_rate = _ego_tts_playback_rate()
    try:
        rate_idx = _EGO_TTS_RATE_VALUES.index(cur_rate)
    except ValueError:
        rate_idx = 0
    c_spd, c_vol, c_mut, c_test = st.columns([2.2, 2.2, 1, 1])
    with c_spd:
        picked = st.radio(
            "Velocidade",
            list(_EGO_TTS_RATE_LABELS),
            index=rate_idx,
            horizontal=True,
            key="ego_tts_rate_radio",
            label_visibility="collapsed",
        )
        st.session_state["ego_tts_rate"] = _EGO_TTS_RATE_VALUES[
            _EGO_TTS_RATE_LABELS.index(picked)
        ]
    with c_vol:
        st.slider(
            "Volume",
            min_value=0,
            max_value=100,
            step=5,
            key="ego_tts_volume",
            help="Controla o leitor HTML. Use também o volume do sistema.",
        )
    with c_mut:
        st.toggle("Mudo", key="ego_tts_muted", help="Não gera nem reproduz áudio.")
    with c_test:
        if st.button("Testar", key="ego_tts_btn_test", use_container_width=True):
            queue_assistant_speech(
                "Olá. O áudio da assistente está a funcionar.",
                "ego_tts_test",
                lang_hint="pt-BR",
            )
            st.rerun()
    _ego_apply_audio_playback_rate(_ego_tts_playback_rate())


def try_browser_tts(
    text: str, html_key: str, *, lang_hint: str | None = None, max_chars: int = 3500
) -> None:
    """Gera MP3 no servidor e mostra leitor de áudio."""
    queue_assistant_speech(text, html_key, lang_hint=lang_hint, max_chars=max_chars)


def try_speech_reminder(text: str, html_key: str) -> None:
    """Lembretes: mesma pipeline de áudio MP3."""
    queue_assistant_speech(
        text,
        html_key,
        lang_hint=st.session_state.get("last_detected_language"),
        max_chars=2000,
    )
    render_tts_playback_player()


def render_reminder_alarm_fragment(supabase: Client | None, user_id: str) -> None:
    """Reexecuta em intervalo fixo para avisos T-10 / a cada 5 min até T."""
    if not supabase or not user_id:
        return

    @st.fragment(run_every=datetime.timedelta(seconds=120))
    def _tick() -> None:
        st.session_state.setdefault("_ego_rem_fired", {})
        fired: dict[str, bool] = st.session_state["_ego_rem_fired"]
        now = datetime.datetime.now(datetime.timezone.utc)
        rows = list_reminders_for_alarm_tick(supabase, user_id)
        for row in rows:
            rid = str(row.get("id") or "")
            if not rid:
                continue
            sch = _parse_ts_iso(row.get("scheduled_at"))
            if not sch:
                continue
            snooze = _parse_ts_iso(row.get("snooze_until"))
            if snooze and now < snooze:
                continue
            win = reminder_current_window(now, sch)
            if not win:
                continue
            a, _b, tag = win
            safe_a = a.isoformat().replace(":", "-")
            fire_key = f"{rid}|{safe_a}"
            if fired.get(fire_key):
                continue
            fired[fire_key] = True
            title = row.get("title") or "Lembrete"
            announce = (row.get("announce") or title or "").strip()
            when_local = sch.astimezone().strftime("%H:%M")
            if tag == "first":
                try_speech_reminder(announce, f"{rid}-first")
            elif tag == "final":
                try_speech_reminder(f"Hora do compromisso: {title}", f"{rid}-final")
            else:
                try_speech_reminder(f"Lembrete: {title}. Em breve às {when_local}.", f"{rid}-mid")
            st.markdown(
                _reminder_alarm_html(tag, str(title), announce, when_local),
                unsafe_allow_html=True,
            )
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button(
                    "Desligar lembrete", key=f"dr_{rid}_{safe_a}", use_container_width=True
                ):
                    dismiss_reminder(supabase, user_id, rid)
                    st.rerun()
            with c2:
                if st.button(
                    "Adiar 5 min", key=f"sn_{rid}_{safe_a}", use_container_width=True
                ):
                    snooze_reminder_minutes(supabase, user_id, rid, 5)
                    st.rerun()
            with c3:
                if st.button(
                    "Ouvir de novo", key=f"rp_{rid}_{safe_a}", use_container_width=True
                ):
                    try_speech_reminder(announce if tag == "first" else title, f"{rid}-replay")

    _tick()


def render_agenda_reminders_page(supabase: Client | None, user_id: str) -> None:
    st.markdown(
        """
        <div class="ego-page-hero">
            <span class="ego-version-badge">Agenda</span>
            <h1>Agenda e lembretes</h1>
            <p>Reuniões com data ficam nos lembretes; hábitos da semana na agenda recorrente.
            Avisos automáticos 10 min antes e a cada 5 min até a hora marcada.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if not user_id:
        st.error("Sessão inválida.")
        return
    ag_warn = st.session_state.pop("_ego_agenda_fetch_warn", None)
    if ag_warn:
        st.warning(str(ag_warn))

    agenda_rows = refresh_user_agenda_snapshot(supabase, user_id)

    st.markdown(
        '<p class="ego-section-head">Hábitos recorrentes (semana)</p>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="ego-form-shell">', unsafe_allow_html=True)
    with st.form("nova_agenda_recorrente", clear_on_submit=True):
        ar_tit = st.text_input("Título", placeholder="Academia, reunião de equipa…")
        ar_hor = st.text_input("Horário (24h)", placeholder="08:00")
        ar_dias = st.text_input(
            "Dias da semana",
            placeholder="seg,ter,qua,qui,sex ou segunda a sexta",
        )
        if st.form_submit_button("Salvar na agenda", use_container_width=True):
            ok_a, err_a = insert_agenda_row(
                supabase,
                user_id,
                titulo=ar_tit,
                horario=ar_hor,
                dias_da_semana=ar_dias,
            )
            if ok_a:
                refresh_user_agenda_snapshot(supabase, user_id)
                st.success("Guardado na sua agenda (só você vê).")
                st.rerun()
            else:
                st.error(err_a or "Não foi possível salvar.")
    st.markdown("</div>", unsafe_allow_html=True)
    if agenda_rows:
        for row in agenda_rows[:30]:
            aid = str(row.get("id") or "")
            st.markdown(_agenda_card_html(row), unsafe_allow_html=True)
            if aid and st.button("Remover", key=f"ag_rm_{aid}", use_container_width=True):
                if delete_agenda_row(supabase, user_id, aid):
                    refresh_user_agenda_snapshot(supabase, user_id)
                    st.rerun()
    else:
        st.markdown(
            '<div class="ego-empty-state">Nenhum hábito recorrente.<br>'
            "Ex.: no chat: <em>marca academia de segunda a sexta às 8h</em>.</div>",
            unsafe_allow_html=True,
        )

    st.divider()
    st.markdown(
        '<p class="ego-section-head">Reuniões e lembretes (data específica)</p>',
        unsafe_allow_html=True,
    )
    today = _local_now().date()
    max_day = today + datetime.timedelta(days=AGENDA_HORIZON_DAYS)
    upcoming = list_upcoming_reminders(supabase, user_id)
    st.markdown('<div class="ego-form-shell">', unsafe_allow_html=True)
    with st.form("nova_meta", clear_on_submit=True):
        tit = st.text_input("Título da reunião / lembrete", placeholder="Reunião com cliente…")
        d_col, h_col = st.columns(2)
        with d_col:
            d_val = st.date_input(
                "Data",
                value=today,
                min_value=today,
                max_value=max_day,
            )
        with h_col:
            t_val = st.time_input(
                "Hora",
                value=_default_time_for_agenda_date(d_val),
            )
        ann = st.text_input(
            "O que falar no primeiro aviso (10 min antes)",
            placeholder="Sua reunião começa em dez minutos",
        )
        if st.form_submit_button("Salvar reunião / lembrete", use_container_width=True):
            if not tit.strip():
                st.error("Preencha o título.")
            else:
                local_tz = _local_now().tzinfo or datetime.timezone.utc
                dt = datetime.datetime.combine(d_val, t_val).replace(tzinfo=local_tz)
                if d_val > max_day:
                    st.error(f"Escolha uma data até {max_day.strftime('%d/%m/%Y')}.")
                else:
                    ok_ins, err_ins = insert_reminder_row(
                        supabase,
                        user_id,
                        title=tit.strip(),
                        scheduled_at=dt,
                        announce=ann.strip() or tit.strip(),
                    )
                    if ok_ins:
                        st.success("Reunião/lembrete guardado (só você vê).")
                        st.rerun()
                    else:
                        st.error(err_ins or "Não foi possível salvar.")
    st.markdown("</div>", unsafe_allow_html=True)
    if upcoming:
        st.markdown('<div class="ego-reminder-list">', unsafe_allow_html=True)
        for r in upcoming[:40]:
            sid = str(r.get("id"))
            st.markdown(_reminder_card_html(r), unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Desligar", key=f"agd_d_{sid}", use_container_width=True):
                    dismiss_reminder(supabase, user_id, sid)
                    st.rerun()
            with c2:
                if st.button("Adiar 5 min", key=f"agd_s_{sid}", use_container_width=True):
                    snooze_reminder_minutes(supabase, user_id, sid, 5)
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div class="ego-empty-state">Nenhuma reunião nos próximos {AGENDA_HORIZON_DAYS} dias.<br>'
            "No chat: <em>marca reunião amanhã às 15h</em>.</div>",
            unsafe_allow_html=True,
        )


def _ego_apply_auth_session(user: object, email: str) -> None:
    """Marca sessão Streamlit após login ou cadastro bem-sucedido."""
    st.session_state.user_logged = True
    st.session_state.user = user
    st.session_state.auth_user_id = user.id
    st.session_state.global_user_name = (email.split("@")[0] or "Usuário Global")
    st.session_state["ego_profile_email"] = email
    st.session_state.history_loaded = False
    st.session_state["ego_ui_state_loaded"] = False
    st.session_state.pop("_ego_ui_state_saved_sig", None)
    _ego_invalidate_caches()


def _ego_invalidate_caches(*, full: bool = False) -> None:
    for key in (
        "_ego_profile_cache",
        "_ego_access_cache_key",
        "_ego_access_cache_ok",
        "_ego_access_cache_status",
        "_ego_access_cache_ts",
        "_ego_daily_limit_key",
        "_ego_daily_limit_ok",
        "_ego_daily_limit_n",
        "_ego_daily_limit_ts",
        "_ego_session_boot_done",
        "_ego_last_login_persisted_for",
        "_ego_last_login_at_unsupported",
        "_ego_voice_done_sig",
    ):
        st.session_state.pop(key, None)
    if full:
        st.session_state.pop("_ego_gemini_models", None)
        st.session_state.pop("_ego_gemini_models_ts", None)
        st.session_state.pop("gemini_model_ok", None)
        for _tzk in ("ego_client_timezone", "ego_client_tz_offset_min", "_ego_tz_injected"):
            st.session_state.pop(_tzk, None)
        for _nk in ("ego_onb_user_name", "ego_onb_asst_name"):
            st.session_state.pop(_nk, None)
        st.session_state.pop("_ego_sb_access", None)
        st.session_state.pop("_ego_sb_refresh", None)


def _ego_finish_auth(
    supabase: Client,
    res: object,
    user: object,
    email: str,
    *,
    full_name: str = "",
) -> tuple[bool, str]:
    """Sessão JWT no cliente + linha em profiles."""
    _sync_supabase_auth_from_response(supabase, res)
    _ego_apply_auth_session(user, email)
    ok_prof, err_prof = ensure_user_profile(
        supabase,
        user.id,
        email=email,
        full_name=full_name or st.session_state.get("global_user_name", ""),
    )
    if ok_prof:
        touch_last_login(supabase, user.id)
    save_local_login_snapshot(supabase, email, user, res)
    return ok_prof, err_prof


def login_usuario(supabase: Client) -> None:
    """Tela de entrada/cadastro com Supabase Auth (sem upload de documento no cadastro)."""
    if st.session_state.get("ego_login_policies"):
        render_sidebar_support_and_version()
        render_policies_page(for_public_login=True)
        render_trust_footer(authenticated=False)
        return
    render_sidebar_support_and_version()
    render_public_trust_landing()
    st.markdown("## Acesso à sua conta")
    st.caption("Entre ou cadastre-se — autenticação segura via Supabase.")
    st.checkbox(
        "Manter sessão neste dispositivo (último login)",
        key="ego_remember_device",
        help="Guarda o e-mail e a sessão no browser e em ficheiros locais deste aparelho. "
        "Use «Sair» para remover.",
    )
    with st.expander("Políticas — resumo (documentos completos no rodapé)", expanded=False):
        lt1, lt2, lt3 = st.tabs(
            ["Termos de Uso", "Política de Privacidade", "Política de Reembolso"]
        )
        with lt1:
            st.markdown(terms_of_use_markdown())
        with lt2:
            st.markdown(privacy_policy_markdown())
        with lt3:
            st.markdown(refund_policy_markdown())
    aba1, aba2 = st.tabs(["Entrar", "Cadastrar Novo Usuario"])

    with aba2:
        with st.form("cadastro_supabase", border=True):
            email = st.text_input("E-mail", placeholder="nome@exemplo.com")
            senha = st.text_input("Senha", type="password")
            st.caption("E-mail: até 254 caracteres (formato nome@dominio.com).")
            nome = st.text_input("Nome (opcional)", placeholder="Pode deixar em branco para testar")
            st.caption("Sem upload de documento — só e-mail e senha.")

            if st.form_submit_button("Criar conta e entrar", use_container_width=True):
                email_norm, email_err = _normalize_auth_email(email)
                if email_err:
                    st.error(email_err)
                elif not senha.strip():
                    st.error("Preencha a senha.")
                else:
                    try:
                        display = nome.strip() or email_norm.split("@")[0] or "Usuário"
                        res = supabase.auth.sign_up(
                            {
                                "email": email_norm,
                                "password": senha,
                                "options": {
                                    "data": {
                                        "full_name": display,
                                        "country": "Brasil",
                                    }
                                },
                            }
                        )
                        user = getattr(res, "user", None)
                        if not user:
                            st.warning(
                                "Conta criada no Auth. Confirme o e-mail (se estiver ativo) e use **Entrar**. "
                                "Se o perfil não aparecer em `profiles`, execute "
                                "`supabase/trigger_profile_on_signup.sql` no SQL Editor."
                            )
                        else:
                            ok_prof, err_prof = _ego_finish_auth(
                                supabase,
                                res,
                                user,
                                email_norm,
                                full_name=display,
                            )
                            if ok_prof:
                                st.success("Conta criada! A entrar…")
                                st.rerun()
                            else:
                                st.warning(
                                    f"Entrou no Auth, mas o perfil não gravou: {err_prof} "
                                    "Execute `supabase/trigger_profile_on_signup.sql` no Supabase."
                                )
                    except Exception as e:  # noqa: BLE001
                        st.error(_format_auth_error(e))

    with aba1:
        with st.form("login_supabase", border=True):
            email_login = st.text_input("E-mail", key="login_email")
            senha_login = st.text_input("Senha", type="password", key="login_senha")
            if st.form_submit_button("Entrar", use_container_width=True):
                email_norm, email_err = _normalize_auth_email(email_login)
                if email_err:
                    st.error(email_err)
                elif not senha_login.strip():
                    st.error("Informe a senha.")
                else:
                    try:
                        res = supabase.auth.sign_in_with_password(
                            {"email": email_norm, "password": senha_login}
                        )
                        user = getattr(res, "user", None)
                        if not user:
                            st.error("Não foi possível autenticar. Verifique suas credenciais.")
                        else:
                            ok_prof, err_prof = _ego_finish_auth(
                                supabase,
                                res,
                                user,
                                email_norm,
                            )
                            if not ok_prof:
                                st.warning(f"Login OK, mas perfil: {err_prof}")
                            st.success("Login realizado com sucesso.")
                            st.rerun()
                    except Exception as e:  # noqa: BLE001
                        st.error(_format_auth_error(e))
    render_trust_footer(authenticated=False)


def get_pdf_text(pdf_files: list) -> str:
    """Extrai texto dos PDFs em blocos (páginas), com limites para não travar em ficheiros grandes."""
    if not PdfReader:
        return ""
    text_parts: list[str] = []
    total_chars = 0
    for pdf in pdf_files:
        try:
            raw = pdf.getvalue() if hasattr(pdf, "getvalue") else pdf.read()
            reader = PdfReader(BytesIO(raw))
            for i, page in enumerate(reader.pages):
                if i >= PDF_EXTRACT_MAX_PAGES:
                    text_parts.append("\n[… páginas extra omitidas para velocidade]\n")
                    break
                page_text = page.extract_text() or ""
                if not page_text.strip():
                    continue
                text_parts.append(page_text)
                total_chars += len(page_text)
                if total_chars >= PDF_EXTRACT_MAX_CHARS:
                    text_parts.append("\n[… limite de caracteres atingido neste PDF]\n")
                    break
        except Exception as exc:  # noqa: BLE001
            text_parts.append(f"\n[Erro ao ler um PDF: {exc}]\n")
    return "\n".join(text_parts)


def render_sidebar_support_and_version() -> None:
    """Badge de versão + canais de suporte (login e sessão autenticada)."""
    st.sidebar.markdown(
        f'<p class="ego-version-badge">{html.escape(EGO_APP_VERSION)}</p>',
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("### AJUDA E SUPORTE")
    em_raw = ego_support_email()
    st.sidebar.link_button(
        "Enviar e-mail",
        f"mailto:{quote(em_raw, safe='@')}?subject={quote('Suporte EGO-AI')}",
        use_container_width=True,
    )
    st.sidebar.divider()


def sidebar_settings() -> None:
    render_sidebar_support_and_version()
    if st.session_state.get("user_logged"):
        who = st.session_state.get("global_user_name") or "Utilizador"
        st.sidebar.caption(f"**{who}**")
        user_obj = st.session_state.get("user")
        if user_obj and getattr(user_obj, "email", None):
            st.sidebar.caption(user_obj.email)
        st.sidebar.radio(
            "Ir para",
            [
                "Chat",
                "Políticas",
                "Agenda e lembretes",
                "Meu Perfil",
                "Meu Avatar",
            ],
            key="ego_nav",
        )
        render_sidebar_agenda_panel(get_supabase_client(), obter_user_id_logado())
        if st.sidebar.button("Sair", use_container_width=True):
            supabase = get_supabase_client()
            logout_email = (
                st.session_state.get("ego_profile_email")
                or (getattr(st.session_state.get("user"), "email", None) if st.session_state.get("user") else None)
                or ""
            )
            if supabase:
                try:
                    supabase.auth.sign_out()
                except Exception:
                    pass
            clear_local_login_snapshot(str(logout_email or ""))
            st.session_state.user_logged = False
            st.session_state.user = None
            st.session_state.auth_user_id = ""
            st.session_state.messages = []
            st.session_state.history_loaded = False
            st.session_state["ego_ui_state_loaded"] = False
            _ego_invalidate_caches(full=True)
            st.session_state.pop("_ego_ui_state_saved_sig", None)
            st.rerun()
        st.sidebar.divider()
        with st.sidebar.expander("👤 Perfil e ficheiros", expanded=False):
            name = st.text_input(
                "Nome",
                placeholder="Como te chamar",
                key="display_name_input",
                label_visibility="collapsed",
            )
            if name:
                st.session_state.user_name = name.strip()
            st.text_input(
                "Nome do assistente",
                placeholder="Como ele se apresenta no chat (ex.: EGO-AI, Alex…)",
                key="ego_assistant_display_name_input",
                label_visibility="collapsed",
            )
            raw_asst = st.session_state.get("ego_assistant_display_name_input")
            st.session_state["ego_assistant_display_name"] = _sanitize_display_name(
                str(raw_asst or "").strip(), max_len=48
            ) or "EGO-AI"
            st.caption(
                "Podes mudar **o teu nome** e **o nome do assistente** aqui a qualquer momento."
            )
            st.caption("Chaves: Streamlit Secrets (`GOOGLE_API_KEY`, etc.) ou `.env`.")
            st.caption(
                "Som do assistente: interruptor no **Chat** + velocidade (1x / 1.5x / 2x) e volume."
            )
            st.selectbox(
                "Modelo",
                options=list(GEMINI_MODEL_IDS),
                format_func=lambda m: (
                    "Gemini 1.5 Flash"
                    if m == GEMINI_MODEL_FLASH
                    else ("Gemini 2.5 Pro" if m == GEMINI_MODEL_PRO else m)
                ),
                key="gemini_model_preference",
            )
            st.text_input(
                "Chave Gemini (opcional)",
                type="password",
                placeholder="Só se não estiver nos secrets",
                key="gemini_api_key_input",
                label_visibility="collapsed",
            )
            uploaded_files = st.file_uploader(
                "PDF",
                type=["pdf"],
                accept_multiple_files=True,
                key="ego_pdf_uploader",
                label_visibility="collapsed",
            )
            if st.button("Carregar PDFs", use_container_width=True):
                if not PdfReader:
                    st.error("PyPDF2 em falta.")
                elif uploaded_files:
                    with st.spinner("A ler…"):
                        raw_text = get_pdf_text(list(uploaded_files))
                        st.session_state.pdf_context = raw_text[
                            : min(len(raw_text), 200_000)
                        ]
                    st.success(f"{len(st.session_state.pdf_context):,} caracteres.")
                else:
                    st.warning("Escolhe um PDF.")
            if st.button("Limpar PDFs", use_container_width=True):
                st.session_state.pdf_context = ""
                st.rerun()
        st.sidebar.divider()
        if st.sidebar.button("Limpar chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.history_loaded = True
            st.rerun()
    else:
        st.sidebar.caption("Inicia sessão para ver o menu.")
    st.session_state._ego_gemini_key = st.session_state.get("gemini_api_key_input") or ""


def render_profile(supabase: Client | None, user_id: str) -> None:
    st.title("Meu Perfil EGO-AI")
    perfil = get_profile_cached(supabase, user_id)
    if not perfil:
        st.warning("Não foi possível carregar seu perfil no momento.")
        return

    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**Nome:** {perfil.get('full_name', '-')}")
        st.info(f"**E-mail:** {perfil.get('email', '-')}")
    with col2:
        st.info(f"**País:** {perfil.get('country', '-')}")
        doc_tipo = (perfil.get("document_type") or "").strip()
        if doc_tipo:
            st.info(f"**Documento:** {doc_tipo}")

    pode, total = verificar_limite_diario(supabase, user_id)
    if _ego_beta_sem_limite():
        st.metric("Mensagens hoje (beta)", "ilimitado")
    else:
        st.metric("Mensagens enviadas hoje", f"{total} / 20")
        if not pode:
            st.error("Você atingiu o limite diário gratuito.")
    is_pro_pf = bool(perfil.get("is_pro"))
    prof_tok = ensure_profile_token_period_reset(supabase, user_id, dict(perfil))
    used_t = int(prof_tok.get("monthly_tokens_used") or 0)
    lim_t = monthly_token_limit_for_user(is_pro_pf)
    if lim_t <= 0:
        st.metric("Tokens IA (mês UTC)", f"{used_t:,} · sem limite configurado")
    else:
        st.metric(
            "Tokens IA (mês UTC, aprox.)",
            f"{used_t:,} / {lim_t:,}",
            help="Contagem tiktoken (cl100k) por pergunta+resposta. Limite: EGO_MONTHLY_TOKEN_LIMIT_FREE / _PRO.",
        )
    if st.button("Solicitar Exclusão de Dados"):
        st.warning("Entre em contato com o suporte para conformidade LGPD/GDPR.")


def render_avatar_page(supabase: Client | None, user_id: str) -> None:
    st.title("Meu Avatar e Voz")
    st.caption("Escolha um avatar humano e uma voz para o EGO-AI.")
    _, status = get_access_cached(supabase, user_id)
    is_pro = status == "Pro"
    if not is_pro:
        st.info("Itens Premium exigem plano Pro.")

    avatar_labels = [
        f"{a['name']} ({a['group']}){' [Premium]' if a['premium'] else ''}" for a in AVATAR_OPTIONS
    ]
    voice_labels = [
        f"{v['name']} ({v['group']}){' [Premium]' if v['premium'] else ''}" for v in VOICE_OPTIONS
    ]

    curr_avatar = st.session_state.get("assistant_avatar_id", "f1")
    curr_voice = st.session_state.get("assistant_voice_id", "vf1")
    idx_avatar = next((i for i, a in enumerate(AVATAR_OPTIONS) if a["id"] == curr_avatar), 0)
    idx_voice = next((i for i, v in enumerate(VOICE_OPTIONS) if v["id"] == curr_voice), 0)

    selected_avatar_label = st.selectbox("Avatar", avatar_labels, index=idx_avatar)
    selected_voice_label = st.selectbox("Voz", voice_labels, index=idx_voice)
    selected_avatar = AVATAR_OPTIONS[avatar_labels.index(selected_avatar_label)]
    selected_voice = VOICE_OPTIONS[voice_labels.index(selected_voice_label)]

    if st.button("Salvar avatar e voz", use_container_width=True):
        if (selected_avatar["premium"] or selected_voice["premium"]) and not is_pro:
            st.warning("Essa combinação é Premium. Assine o plano Pro para desbloquear.")
            mensal = build_stripe_checkout_link(STRIPE_MENSAL_URL, user_id)
            anual = build_stripe_checkout_link(STRIPE_ANUAL_URL, user_id)
            c1, c2 = st.columns(2)
            with c1:
                st.link_button(f"Assinar Mensal ({PAYWALL_PRECO_MENSAL})", mensal, use_container_width=True)
            with c2:
                st.link_button(f"Assinar Anual ({PAYWALL_PRECO_ANUAL})", anual, use_container_width=True)
            return
        st.session_state.assistant_avatar_id = selected_avatar["id"]
        st.session_state.assistant_voice_id = selected_voice["id"]
        save_user_persona(
            supabase,
            user_id,
            st.session_state.assistant_avatar_id,
            st.session_state.assistant_voice_id,
        )
        st.success("Avatar e voz salvos.")

    st.caption(
        "Próximo passo: ativar comando de voz (STT) e resposta falada (TTS) com o pacote de voz escolhido."
    )


def _api_ready() -> bool:
    return bool(effective_gemini_api_key())


def _bubble_html(role: str, content: str) -> str:
    avatar_name = next(
        (a["name"] for a in AVATAR_OPTIONS if a["id"] == st.session_state.get("assistant_avatar_id")),
        "Ego-AI",
    )
    alias = (st.session_state.get("ego_assistant_display_name") or "").strip()
    assistant_label = _sanitize_display_name(alias, max_len=48) or avatar_name
    label = "Você" if role == "user" else html.escape(str(assistant_label))
    safe = html.escape(content or "").replace("\n", "<br/>")
    cls = "user" if role == "user" else "assistant"
    return (
        f'<div class="ego-chat-row {cls}">'
        f'<div class="ego-bubble {cls}">'
        f'<div class="ego-meta">{html.escape(label)}</div>'
        f'<div class="ego-body">{safe}</div>'
        f"</div></div>"
    )


def render_chat_history_html() -> str:
    """HTML do histórico vindo de st.session_state.messages (uma única marcação = layout estável)."""
    if not st.session_state.messages:
        return (
            '<div class="ego-chat-scroll">'
            '<p style="color:#9ca3af;font-size:0.88rem;margin:0.35rem 0.25rem;">'
            "Nenhuma mensagem ainda. Envie algo abaixo para começar."
            "</p></div>"
        )
    parts = ['<div class="ego-chat-scroll">']
    for msg in st.session_state.messages:
        role = msg.get("role", "assistant")
        text = msg.get("content", "")
        parts.append(_bubble_html(role, text))
    parts.append("</div>")
    return "".join(parts)


def render_dashboard(supabase: Client | None, user_id: str) -> None:
    name = _resolved_user_display_name() or "você"
    st.markdown(
        f"""
        <div class="ego-hero">
            <h1>Olá, {name} 👋</h1>
            <p>Bem-vindo ao <strong>Ego-AI</strong> — seu painel com inteligência artificial.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(
            """
            <div class="ego-card">
                <div class="ego-card-title">Ações Sugeridas</div>
                <ul>
                    <li>Revisar prioridades da manhã</li>
                    <li>Responder mensagens pendentes</li>
                    <li>Bloquear 25 minutos de foco profundo</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        agenda_items = list_upcoming_reminders(supabase, user_id)[:5]
        if agenda_items:
            lis = "".join(
                f"<li>{html.escape(str(r.get('title', 'Lembrete')))} — "
                f"{html.escape(str(r.get('scheduled_at', ''))[:16].replace('T', ' '))}</li>"
                for r in agenda_items
            )
        else:
            lis = (
                "<li>Nenhum lembrete cadastrado.</li>"
                "<li>Use <strong>Agenda e lembretes</strong> ou peça no chat.</li>"
            )
        st.markdown(
            f"""
            <div class="ego-card">
                <div class="ego-card-title">Sua agenda</div>
                <ul>{lis}</ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c3:
        prov = "Google Gemini"
        tip_base = (
            f"Configure a chave da API ({prov}) na barra lateral ou em secrets/env para usar o chat."
            if not _api_ready()
            else "O assistente está pronto — use o campo de mensagem abaixo."
        )
        insight_tip = tip_base
        st.markdown(
            f"""
            <div class="ego-card">
                <div class="ego-card-title">Insights</div>
                <ul>
                    <li>Picos de energia costumam ser pela manhã</li>
                    <li>Menos abas abertas, mais foco numa tarefa</li>
                    <li>{insight_tip}</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <div class="ego-card" style="margin-top:1rem;">
            <div class="ego-card-title">Chat com PDF e lembretes</div>
            <p style="color:#9ca3af;font-size:0.88rem;margin:0;">
                Use a barra lateral para carregar PDFs e o chat para perguntas.
                Lembretes: peça no chat ou em <strong>Agenda e lembretes</strong>.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def build_user_agenda_context_for_llm(
    supabase: Client | None, user_id: str
) -> str:
    """Carrega agenda + lembretes do Supabase e injeta no system prompt do Gemini."""
    if not supabase or not user_id:
        return (
            "\n\n=== CURRENT USER AGENDA ===\n"
            "(not logged in — cannot read calendar)\n"
            "=== END AGENDA ===\n"
        )
    if not ensure_supabase_auth_client(supabase):
        return (
            "\n\n=== CURRENT USER AGENDA ===\n"
            "(session expired — ask the user to log out and log in again to sync calendar)\n"
            "=== END AGENDA ===\n"
        )
    recurring = fetch_user_agenda_rows(supabase, user_id)
    reminders = list_upcoming_reminders(supabase, user_id)
    now_local = _local_now()
    today_lbl = now_local.strftime("%d/%m/%Y %H:%M")
    wk = DOW_PT_ORDER[now_local.weekday()]
    lines = [
        "",
        "=== CURRENT USER AGENDA (Supabase — authoritative for this user) ===",
        f"Loaded at local time: {today_lbl} (weekday code today: {wk})",
        "Recurring rows are in table `agenda`; one-off meetings/alarms in `reminders`.",
        "",
    ]
    if recurring:
        lines.append("Recurring weekly habits:")
        for row in recurring[:35]:
            tit = (row.get("titulo") or "—").strip()
            hor = str(row.get("horario") or "")[:5]
            dias = row.get("dias_da_semana") or ""
            today_mark = " [TODAY]" if wk in {d.strip() for d in str(dias).lower().split(",")} else ""
            lines.append(f"  - {tit} | {hor} | days: {dias}{today_mark}")
    else:
        lines.append("Recurring weekly habits: (none)")
    lines.append("")
    if reminders:
        lines.append(f"One-off meetings / reminders (next {AGENDA_HORIZON_DAYS} days):")
        for row in reminders[:45]:
            tit = (row.get("title") or "—").strip()
            sch = _parse_ts_iso(row.get("scheduled_at"))
            if sch:
                when = sch.astimezone().strftime("%d/%m/%Y %H:%M %Z")
            else:
                when = str(row.get("scheduled_at") or "—")
            extra = ""
            sn = _parse_ts_iso(row.get("snooze_until"))
            if sn:
                extra = f" | snoozed until {sn.astimezone().strftime('%d/%m %H:%M')}"
            lines.append(f"  - {tit} | {when}{extra}")
    else:
        lines.append(f"One-off meetings / reminders: (none in the next {AGENDA_HORIZON_DAYS} days)")
    lines.append("=== END AGENDA ===")
    return "\n".join(lines)


def _build_contexto_instrucao_pdf(pdf_context: str) -> str:
    """Trecho curto no system prompt (até PDF_CONTEXT_IN_SYSTEM_CHARS) — RAG leve."""
    raw = (pdf_context or "").strip()
    if not raw:
        return ""
    snippet = raw[:PDF_CONTEXT_IN_SYSTEM_CHARS]
    suffix = (
        f"\n\n(O documento completo é maior; aqui há só os primeiros "
        f"{PDF_CONTEXT_IN_SYSTEM_CHARS} caracteres. Resuma o essencial e diga se faltar contexto.)"
        if len(raw) > PDF_CONTEXT_IN_SYSTEM_CHARS
        else ""
    )
    return (
        "\n\nContexto opcional de documento (início do ficheiro):\n"
        f"{snippet}{suffix}"
    )


def _build_full_system_instruction(
    pdf_context: str,
    lang_code: str = "pt-BR",
    *,
    agenda_context: str = "",
) -> str:
    return (
        GEMINI_SYSTEM_INSTRUCTION
        + language_instruction(lang_code)
        + names_and_identity_instruction()
        + client_datetime_context_instruction()
        + _build_contexto_instrucao_pdf(pdf_context)
        + reminder_instruction_block()
        + agenda_instruction_block()
        + (agenda_context or "")
    )


def _messages_to_gemini_history(messages: list) -> list[dict]:
    """Converte st.session_state.messages (exceto a última) para o formato de histórico do Gemini."""
    history: list[dict] = []
    for m in messages:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if not content:
            continue
        if role == "user":
            history.append({"role": "user", "parts": [content]})
        elif role == "assistant":
            history.append({"role": "model", "parts": [content]})
    return history


def _normalize_gemini_model_id(model_name: str) -> str:
    """API `GenerativeModel` usa o id sem prefixo `models/`."""
    m = (model_name or "").strip()
    if m.startswith("models/"):
        return m[len("models/") :]
    return m


def _gemini_variant_list() -> list[str]:
    """Variações de nome (com e sem prefixo models/) na ordem preferida."""
    pref = st.session_state.get("gemini_model_preference") or GEMINI_MODEL_FLASH
    if pref not in GEMINI_MODEL_IDS:
        pref = GEMINI_MODEL_FLASH
    other = GEMINI_MODEL_PRO if pref == GEMINI_MODEL_FLASH else GEMINI_MODEL_FLASH
    out: list[str] = []
    for mid in (pref, other, f"models/{pref}", f"models/{other}"):
        if mid not in out:
            out.append(mid)
    return out


def _is_gemini_chat_model_name(name: str) -> bool:
    n = _normalize_gemini_model_id(name).lower()
    if n in GEMINI_MODEL_IDS:
        return True
    if "gemini" not in n:
        return False
    blocked = ("image", "tts", "embedding", "aqa", "vision")
    return not any(b in n for b in blocked)


def _linearize_messages_for_fallback(messages: list, last_user: str) -> str:
    """Única string com o diálogo (fallback se start_chat falhar)."""
    lines: list[str] = []
    for m in messages:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if not content:
            continue
        if role == "user":
            lines.append(f"Usuário: {content}")
        elif role == "assistant":
            lines.append(f"Assistente: {content}")
    lines.append(f"Usuário: {last_user}")
    return "\n".join(lines)


def _generate_with_model(
    model_name: str,
    full_system: str,
    prior_messages: list,
    user_text: str,
    *,
    audio_bytes: bytes | None = None,
    audio_mime: str | None = None,
) -> str:
    """Uma chamada: system + histórico (chat) ou prompt único (fallback). Opcional: áudio multimodal."""
    mid = _normalize_gemini_model_id(model_name)
    try:
        model = genai.GenerativeModel(
            model_name=mid,
            system_instruction=full_system,
        )
        legacy_prompt_merge = False
    except TypeError:
        model = genai.GenerativeModel(model_name=mid)
        legacy_prompt_merge = True

    history = _messages_to_gemini_history(prior_messages)
    asst_nm = _resolved_assistant_display_name()
    voice_intro = (
        "Em anexo: mensagem de voz do utilizador. Escuta com atenção, responde no mesmo idioma "
        f"da fala e mantém o tom acolhedor de {asst_nm}."
    )

    if legacy_prompt_merge:
        blob = _linearize_messages_for_fallback(prior_messages, user_text or "(voz)")
        if audio_bytes:
            prompt = f"{full_system}\n\n{voice_intro}\n\n{blob}"
            resp = model.generate_content(
                [prompt, {"mime_type": audio_mime or "audio/wav", "data": audio_bytes}]
            )
        else:
            prompt = f"{full_system}\n\n{blob}"
            resp = model.generate_content(prompt)
        st.session_state["gemini_model_ok"] = mid
        return resp.text or ""

    if history:
        try:
            chat = model.start_chat(history=history)
            if audio_bytes:
                parts: list[object] = []
                if (user_text or "").strip():
                    parts.append((user_text or "").strip())
                parts.append(voice_intro)
                parts.append({"mime_type": audio_mime or "audio/wav", "data": audio_bytes})
                resp = chat.send_message(parts)
            else:
                resp = chat.send_message(user_text)
        except Exception:  # noqa: BLE001
            blob = _linearize_messages_for_fallback(
                prior_messages, user_text or "(mensagem de voz)"
            )
            if audio_bytes:
                resp = model.generate_content(
                    [
                        f"{full_system}\n\n{blob}\n\n{voice_intro}",
                        {"mime_type": audio_mime or "audio/wav", "data": audio_bytes},
                    ]
                )
            else:
                resp = model.generate_content(blob)
    else:
        if audio_bytes:
            parts2: list[object] = []
            if (user_text or "").strip():
                parts2.append((user_text or "").strip())
            parts2.append(voice_intro)
            parts2.append({"mime_type": audio_mime or "audio/wav", "data": audio_bytes})
            resp = model.generate_content(parts2)
        else:
            resp = model.generate_content(user_text)

    st.session_state["gemini_model_ok"] = mid
    return resp.text or ""


def run_gemini_reply(
    api_key: str,
    user_text: str,
    pdf_context: str = "",
    *,
    conversation_messages: list | None = None,
    lang_code: str = "pt-BR",
    audio_bytes: bytes | None = None,
    audio_mime: str | None = None,
    agenda_context: str = "",
) -> str:
    """Gemini: system (PDF até N chars) + histórico; opcionalmente áudio multimodal."""
    if not genai:
        return "Instale o pacote `google-generativeai` (veja requirements.txt)."
    if not api_key.strip():
        return (
            "Adicione a **chave da API do Gemini** na barra lateral ou defina "
            "`GOOGLE_API_KEY` / `GEMINI_API_KEY` em variáveis de ambiente ou em `.streamlit/secrets.toml`."
        )

    msgs = conversation_messages if conversation_messages is not None else []
    prior = msgs[:-1] if msgs else []
    if len(prior) > CHAT_LLM_MAX_TURNS:
        prior = prior[-CHAT_LLM_MAX_TURNS:]

    full_system = _build_full_system_instruction(
        pdf_context, lang_code, agenda_context=agenda_context
    )

    try:
        genai.configure(api_key=api_key.strip())
        listed_supported = _cached_gemini_models_list()

        preferred_variants = _gemini_variant_list()
        listed_chat = [n for n in listed_supported if _is_gemini_chat_model_name(n)]

        chosen_model = st.session_state.get("gemini_model_ok")
        if chosen_model:
            cm = _normalize_gemini_model_id(str(chosen_model))
            if not _is_gemini_chat_model_name(cm):
                chosen_model = None
            elif listed_supported and chosen_model not in listed_supported:
                alt = f"models/{cm}" if not str(chosen_model).startswith("models/") else cm
                chosen_model = alt if alt in listed_supported else None

        if not chosen_model:
            for preferred in preferred_variants:
                if preferred in listed_supported:
                    chosen_model = preferred
                    break
            if not chosen_model and listed_chat:
                chosen_model = listed_chat[0]
            if not chosen_model:
                chosen_model = (
                    st.session_state.get("gemini_model_preference") or GEMINI_MODEL_FLASH
                )
            st.session_state["gemini_model_ok"] = _normalize_gemini_model_id(str(chosen_model))

        model_try_order: list[str] = []
        for name in [chosen_model, *preferred_variants, *listed_chat, "models/gemini-flash-latest"]:
            if name and name not in model_try_order and _is_gemini_chat_model_name(name):
                model_try_order.append(name)

        last_error = None
        for model_name in model_try_order:
            try:
                text = _generate_with_model(
                    model_name,
                    full_system,
                    prior,
                    user_text,
                    audio_bytes=audio_bytes,
                    audio_mime=audio_mime,
                )
                if text:
                    return text
                return "Não obtive texto na resposta. Tente novamente."
            except Exception as model_err:  # noqa: BLE001
                last_error = model_err
                continue

        err_s = str(last_error)
        if "404" in err_s and "gemini-1.5" in err_s:
            return (
                "Os modelos Gemini 1.5 já não estão disponíveis na API. "
                "Atualize a app e escolha **Gemini 2.5 Flash** na barra lateral."
            )
        if "429" in err_s or "quota" in err_s.lower():
            return (
                "Cota da API Gemini esgotada (429). Crie outra chave em "
                "https://aistudio.google.com/apikey ou ative faturação no Google AI."
            )
        return f"Erro ao chamar o Gemini: {last_error}"
    except Exception as e:  # noqa: BLE001
        err_s = str(e)
        if "429" in err_s or "quota" in err_s.lower():
            return (
                "Cota da API Gemini esgotada. Verifique limites em "
                "https://ai.google.dev/gemini-api/docs/rate-limits"
            )
        return f"Erro ao chamar o Gemini: {e}"


def _ego_process_chat_turn(
    supabase: Client | None,
    user_id: str,
    user_display: str,
    *,
    audio_bytes: bytes | None = None,
    audio_mime: str | None = None,
    mark_voice_sig: int | None = None,
) -> None:
    """Texto ou voz: limites, Gemini, marcadores, Supabase, rerun."""
    is_pro_chat = bool((get_profile_cached(supabase, user_id) or {}).get("is_pro"))
    ok_tok, msg_tok, used_tok, lim_tok = check_monthly_token_allowance(
        supabase, user_id, is_pro_chat
    )
    if not ok_tok:
        st.error(msg_tok)
        st.caption(f"Uso aproximado no mês: {used_tok:,} / {lim_tok:,} tokens.")
        return
    if mark_voice_sig is not None:
        st.session_state["_ego_voice_done_sig"] = mark_voice_sig

    if audio_bytes:
        detected_lang = str(st.session_state.get("last_detected_language", "pt-BR"))
        confidence = float(st.session_state.get("last_detected_confidence", 0.0))
    else:
        detected_lang, confidence = detect_user_language_with_confidence(user_display)
    st.session_state.last_detected_language = detected_lang
    st.session_state.last_detected_confidence = confidence
    mid_u: str | None = None
    if user_id and supabase:
        mid_u = salvar_mensagem_segura(supabase, user_id, "user", user_display)
    st.session_state.messages.append({"role": "user", "content": user_display, "msg_id": mid_u})
    pdf_ctx = st.session_state.get("pdf_context") or ""
    if user_id and supabase:
        refresh_user_agenda_snapshot(supabase, user_id)
    agenda_ctx = build_user_agenda_context_for_llm(supabase, user_id)

    with st.spinner("A pensar…"):
        reply = run_gemini_reply(
            effective_gemini_api_key(),
            user_display if not audio_bytes else "",
            pdf_ctx,
            conversation_messages=st.session_state.messages,
            lang_code=detected_lang,
            audio_bytes=audio_bytes,
            audio_mime=audio_mime,
            agenda_context=agenda_ctx,
        )
    reply_clean = process_assistant_reminders(supabase, user_id, reply)
    reply_clean = process_assistant_agenda(supabase, user_id, reply_clean)
    st.session_state.pop("_ego_daily_limit_ts", None)
    st.session_state.pop("_ego_profile_cache", None)
    mid_a: str | None = None
    if user_id and supabase:
        mid_a = salvar_mensagem_segura(supabase, user_id, "assistant", reply_clean)
        tok_n = count_turn_tokens(user_display, reply_clean)
        add_monthly_tokens_to_profile(supabase, user_id, tok_n, is_pro_chat)
    st.session_state.messages.append(
        {"role": "assistant", "content": reply_clean, "msg_id": mid_a}
    )
    if st.session_state.get("ego_voice_replies", True):
        st.session_state["_ego_tts_play_index"] = len(st.session_state.messages) - 1
    st.rerun()


def _ego_apply_name_onboarding_submit(
    supabase: Client, user_id: str, *, use_suggestions: bool
) -> None:
    gname = (st.session_state.get("global_user_name") or "").strip()
    if use_suggestions:
        u_ok = _sanitize_display_name(gname, max_len=80) or "Amigo(a)"
        a_ok = "EGO-AI"
    else:
        u_ok = _sanitize_display_name(
            str(st.session_state.get("ego_onb_user_name") or ""), max_len=80
        )
        if not u_ok:
            u_ok = _sanitize_display_name(gname, max_len=80) or "Amigo(a)"
        a_ok = (
            _sanitize_display_name(
                str(st.session_state.get("ego_onb_asst_name") or ""), max_len=48
            )
            or "EGO-AI"
        )
    st.session_state["user_name"] = u_ok
    st.session_state["ego_assistant_display_name"] = a_ok
    st.session_state["display_name_input"] = u_ok
    st.session_state["ego_assistant_display_name_input"] = a_ok
    st.session_state["ego_name_setup_done"] = True
    save_ui_state_to_profile(supabase, user_id, build_ui_state_payload())
    pl = build_ui_state_payload()
    st.session_state["_ego_ui_state_saved_sig"] = json.dumps(
        pl, ensure_ascii=False, sort_keys=True
    )
    st.rerun()


@st.dialog("Como nos tratamos?")
def _ego_name_onboarding_dialog(supabase: Client, user_id: str) -> None:
    st.markdown(
        "Indica **o teu nome** e **como queres chamar o assistente**. "
        "Isto fica guardado no teu perfil — podes mudar a qualquer momento na barra lateral, "
        "em **👤 Perfil e ficheiros**."
    )
    gname = (st.session_state.get("global_user_name") or "").strip()
    du = (st.session_state.get("user_name") or "").strip() or gname
    da = (st.session_state.get("ego_assistant_display_name") or "").strip() or "EGO-AI"
    if "ego_onb_user_name" not in st.session_state:
        st.session_state["ego_onb_user_name"] = du
    if "ego_onb_asst_name" not in st.session_state:
        st.session_state["ego_onb_asst_name"] = da
    st.text_input("O teu nome (como te chamo)", max_chars=80, key="ego_onb_user_name")
    st.text_input(
        "Nome do assistente",
        max_chars=48,
        key="ego_onb_asst_name",
        help="Ex.: EGO-AI, Alex, Luna…",
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Guardar e continuar", type="primary", use_container_width=True):
            _ego_apply_name_onboarding_submit(supabase, user_id, use_suggestions=False)
    with c2:
        if st.button("Usar sugestões", use_container_width=True):
            _ego_apply_name_onboarding_submit(supabase, user_id, use_suggestions=True)


def maybe_ego_name_onboarding(supabase: Client | None, user_id: str | None) -> None:
    if not supabase or not user_id:
        return
    if not st.session_state.get("_ego_session_boot_done"):
        return
    if st.session_state.get("ego_name_setup_done"):
        return
    _ego_name_onboarding_dialog(supabase, user_id)


def render_chat(supabase: Client | None, user_id: str) -> None:
    asst = _resolved_assistant_display_name()
    st.markdown(
        f'<p class="ego-brand-min">{html.escape(asst)}</p>',
        unsafe_allow_html=True,
    )
    who = _resolved_user_display_name()
    if who:
        st.caption(f"Aqui por ti, «{who}» — estou aqui como «{asst}».")
    else:
        st.caption(f"Fala com «{asst}» quando quiseres.")
    reminder_warn = st.session_state.pop("_ego_reminder_warn", None)
    if reminder_warn:
        st.warning(str(reminder_warn))
    st.toggle(
        f"Ouvir {asst} (voz no browser)",
        key="ego_voice_replies",
        help="Desliga em sítios em silêncio: só vês a resposta escrita. Ligado = texto + leitura em voz.",
    )
    render_tts_controls()
    msgs = st.session_state.get("messages") or []
    with st.expander("Exportar conversa", expanded=False):
        if msgs:
            st.download_button(
                "TXT",
                data=build_chat_export_txt(msgs),
                file_name=f"ego_chat_{datetime.date.today().isoformat()}.txt",
                mime="text/plain; charset=utf-8",
                key="ego_export_txt",
            )
        else:
            st.caption("Sem mensagens ainda.")
        if not effective_gemini_api_key():
            st.caption("Configura `GOOGLE_API_KEY` nos secrets do Streamlit Cloud ou no `.env`.")

    try:
        with st.container(height=520, border=False):
            render_chat_messages_with_feedback(supabase, user_id)
    except TypeError:
        render_chat_messages_with_feedback(supabase, user_id)

    pending_tts = st.session_state.pop("_ego_tts_pending", None)
    if isinstance(pending_tts, dict) and pending_tts.get("text"):
        queue_assistant_speech(
            str(pending_tts["text"]),
            str(pending_tts.get("key") or "asst_pending"),
            lang_hint=pending_tts.get("lang"),
        )
    render_tts_playback_player()

    acesso_liberado, _status = get_access_cached(supabase, user_id)
    if not acesso_liberado:
        st.error(f"🚨 Seu período de teste de {EGO_TRIAL_DAYS} dias expirou!")
        st.markdown("### Assine o plano Pro para continuar usando o EGO-AI")
        link_mensal = build_stripe_checkout_link(STRIPE_MENSAL_URL, user_id)
        link_anual = build_stripe_checkout_link(STRIPE_ANUAL_URL, user_id)
        col1, col2 = st.columns(2)
        with col1:
            st.link_button(f"Plano Mensal ({PAYWALL_PRECO_MENSAL})", link_mensal, use_container_width=True)
        with col2:
            st.link_button(f"Plano Anual ({PAYWALL_PRECO_ANUAL})", link_anual, use_container_width=True)
        st.stop()

    pode_enviar, total_hoje = limite_diario_cached(supabase, user_id)
    if not pode_enviar:
        st.error("Limite diário atingido. Volte amanhã ou assine o Pro.")
        st.caption(f"Hoje: {total_hoje} / 20 mensagens.")
        return

    audio_rec = None
    if hasattr(st, "audio_input"):
        audio_rec = st.audio_input("Mensagem de voz", key="ego_voice_in")
    voice_buf: bytes | None = None
    voice_mime: str | None = None
    if audio_rec is not None:
        voice_buf = audio_rec.getvalue()
        voice_mime = getattr(audio_rec, "type", None) or "audio/wav"
    if audio_rec is not None and voice_buf and not effective_gemini_api_key():
        st.caption("Configura `GOOGLE_API_KEY` nos secrets para usar a mensagem de voz.")
    voice_sig = hash(voice_buf) if voice_buf else None
    voice_pending = bool(
        voice_buf
        and effective_gemini_api_key()
        and voice_sig is not None
        and st.session_state.get("_ego_voice_done_sig") != voice_sig
    )

    prompt = st.chat_input("Escreve ou grava no microfone…")

    if voice_pending:
        _ego_process_chat_turn(
            supabase,
            user_id,
            "(mensagem de voz)",
            audio_bytes=voice_buf,
            audio_mime=voice_mime,
            mark_voice_sig=voice_sig,
        )
        return

    if prompt and prompt.strip():
        _ego_process_chat_turn(supabase, user_id, prompt.strip())


def main() -> None:
    st.set_page_config(
        page_title="EGO-AI Global",
        page_icon="🤖",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    init_session()
    inject_styles()
    supabase = get_supabase_client()
    if not supabase:
        render_supabase_setup()
        st.caption(
            "Para modo produção, configure `SUPABASE_URL` e `SUPABASE_KEY` "
            "via environment variables ou `.streamlit/secrets.toml`."
        )
        return
    st.session_state.local_mode = False
    if not st.session_state.get("user_logged"):
        if not st.session_state.get("_ego_browser_auth_read_done"):
            raw_br = _ego_auth_browser_read()
            if raw_br:
                st.session_state["_ego_browser_auth_raw"] = raw_br
            st.session_state["_ego_browser_auth_read_done"] = True
            st.rerun()
        if try_restore_local_auth(supabase):
            st.rerun()
        login_usuario(supabase)
        return
    uid = obter_user_id_logado()
    if uid and supabase:
        ensure_supabase_auth_client(supabase)
        bootstrap_logged_in_session(supabase, uid)
        refresh_user_agenda_snapshot(supabase, uid)
    else:
        st.session_state.pop("_ego_agenda_rows_snapshot", None)
    ensure_user_timezone_from_browser()
    maybe_ego_name_onboarding(supabase, uid)
    render_ego_schema_banner()
    chat_db_warn = st.session_state.pop("_ego_chat_save_warn", None)
    if chat_db_warn:
        st.warning(str(chat_db_warn))
    perfil_nav = get_profile_cached(supabase, uid) if uid and supabase else None
    is_pro_nav = bool((perfil_nav or {}).get("is_pro", False))
    clamp_persona_para_plano_nao_pro(supabase, uid or "", is_pro=is_pro_nav)
    sidebar_settings()
    acesso_liberado, status = get_access_cached(supabase, uid) if uid else (False, "Expirado")
    if acesso_liberado:
        st.sidebar.success(f"Status da Conta: {status}")
    elif uid and supabase:
        st.sidebar.error(f"Status: {status}")
        st.sidebar.caption(
            f"Trial = {EGO_TRIAL_DAYS} dias desde `profiles.created_at`. "
            "Para reiniciar: execute `supabase/reset_trial_20_days.sql` no SQL Editor."
        )
    if uid and supabase:
        render_recurring_agenda_banner(supabase, uid)
    nav = st.session_state.get("ego_nav") or "Chat"
    if nav in ("Chat", "Agenda e lembretes") and uid and supabase:
        render_reminder_alarm_fragment(supabase, uid)
    if nav == "Políticas":
        render_policies_page(for_public_login=False)
    elif nav == "Agenda e lembretes":
        render_agenda_reminders_page(supabase, uid)
    elif nav == "Meu Perfil":
        render_profile(supabase, uid)
    elif nav == "Meu Avatar":
        render_avatar_page(supabase, uid)
    else:
        render_chat(supabase, uid)
    if uid and supabase:
        maybe_autosave_ui_state(supabase, uid)
    render_trust_footer(authenticated=True)


if __name__ == "__main__":
    main()
