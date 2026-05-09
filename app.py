"""
Ego-AI — painel Streamlit: Gemini ou OpenAI, PDFs, dashboard e chat.
"""

from __future__ import annotations

import datetime
import html
import json
import math
import os
import secrets
from collections import Counter
from io import BytesIO
from urllib.parse import parse_qsl, quote, urlencode, urlparse, urlunparse

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
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore[misc, assignment]

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
You are EGO-AI, a global assistant.
Detect the user's language automatically and always reply in the same language.
Be concise, helpful, and safe.
"""

REMINDER_LLM_INSTRUCTION = """
REMINDERS / ALARMS: If the user asks for a reminder, alarm, meeting, or important call at a specific time,
you may register it by adding EXACTLY ONE line at the very END of your reply (after your normal answer), with this format:
[[EGO_REMINDER:{"title":"short title","scheduled_at":"ISO-8601 datetime WITH timezone offset","announce":"what to say at the first alarm (10 min before)"}]]
- scheduled_at is the moment the event happens (e.g. time of the call), NOT the first alarm time.
- The app notifies starting 10 minutes before, then every 5 minutes until that moment.
- If date/time is ambiguous, do NOT add the line; ask one clarifying question instead.
"""


def reminder_instruction_block() -> str:
    return REMINDER_LLM_INSTRUCTION
MODEL_CANDIDATES = [
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
]

# Trecho dos PDFs na instrução de sistema (Gemini).
PDF_CONTEXT_IN_SYSTEM_CHARS = 4000
# Trecho dos PDFs na mensagem system (OpenAI), como no seu exemplo.
OPENAI_PDF_CONTEXT_CHARS = 5000
OPENAI_DEFAULT_MODEL = "gpt-4o"
SUPABASE_STORAGE_BUCKET = "usuarios"
SUPABASE_HISTORY_TABLE = "chat_history"
SUPABASE_PROFILES_TABLE = "profiles"
SUPABASE_FEEDBACK_TABLE = "message_feedback"
SUPABASE_PERSONA_TABLE = "user_personas"
SUPABASE_FOOD_TABLE = "food_history"
SUPABASE_DRINK_TABLE = "drink_history"
SUPABASE_SHOP_TABLE = "shopping_history"
SUPABASE_TRAVEL_TABLE = "travel_history"
SUPABASE_NIGHTLIFE_TABLE = "nightlife_history"
SUPABASE_REMINDERS_TABLE = "reminders"
SUPABASE_GOOGLE_CALENDAR_TOKENS_TABLE = "google_calendar_tokens"
SUPABASE_GOOGLE_OAUTH_PENDING_TABLE = "google_oauth_pending"
GOOGLE_CALENDAR_READONLY_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"
GOOGLE_OAUTH_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CALENDAR_EVENTS_URL = (
    "https://www.googleapis.com/calendar/v3/calendars/primary/events"
)
REMINDER_MINUTES_BEFORE = 10
REMINDER_NUDGE_MINUTES = 5
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


def ego_operator_legal_name() -> str:
    return (
        _ego_read_secret("EGO_OPERATOR_LEGAL_NAME")
        or _ego_read_secret("EGO_COMPANY_LEGAL_NAME")
        or "Configure EGO_OPERATOR_LEGAL_NAME nos secrets"
    )


def ego_support_email() -> str:
    return _ego_read_secret("EGO_SUPPORT_EMAIL") or "suporte@egoai.com.br"


def ego_whatsapp_business_url() -> str:
    u = _ego_read_secret("EGO_WHATSAPP_URL")
    if u.startswith("http"):
        return u
    phone = _ego_read_secret("EGO_SUPPORT_WHATSAPP").replace(" ", "").replace("-", "")
    if phone.startswith("+"):
        phone = phone[1:]
    if not phone:
        return ""
    msg = _ego_read_secret("EGO_WHATSAPP_PREFILL") or "Olá, preciso de suporte com o EGO-AI."
    return f"https://wa.me/{phone}?text={urlencode({'text': msg})}"


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


def inject_styles() -> None:
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
    st.session_state.setdefault("pdf_context", "")
    st.session_state.setdefault("ego_ai_provider", "Gemini")
    st.session_state.setdefault("openai_model_input", OPENAI_DEFAULT_MODEL)
    st.session_state.setdefault("user_logged", False)
    st.session_state.setdefault("global_user_name", "")
    st.session_state.setdefault("auth_user_id", "")
    st.session_state.setdefault("history_loaded", False)
    st.session_state.setdefault("user", None)
    st.session_state.setdefault("ego_nav", "Chat")
    if st.session_state.get("ego_nav") == "Jurídico":
        st.session_state["ego_nav"] = "Políticas"
    st.session_state.setdefault("supabase_url_input", "")
    st.session_state.setdefault("supabase_key_input", "")
    st.session_state.setdefault("local_mode", False)
    st.session_state.setdefault("last_detected_language", "pt-BR")
    st.session_state.setdefault("last_detected_confidence", 0.0)
    st.session_state.setdefault("food_history", [])
    st.session_state.setdefault("drink_history", [])
    st.session_state.setdefault("shopping_history", [])
    st.session_state.setdefault("shop_market", "Brasil")
    st.session_state.setdefault("travel_history", [])
    st.session_state.setdefault("nightlife_history", [])
    st.session_state.setdefault("travel_market", "Brasil")
    st.session_state.setdefault("_ego_rem_fired", {})
    st.session_state.setdefault("ego_legal_tab", 0)
    st.session_state.setdefault("_legal_render_id", 0)
    st.session_state.setdefault("ego_login_policies", False)
    st.session_state.setdefault("food_city", "")
    st.session_state.setdefault("food_country", "")
    st.session_state.setdefault("persona_loaded", False)
    st.session_state.setdefault("assistant_avatar_id", "f1")
    st.session_state.setdefault("assistant_voice_id", "vf1")


def get_supabase_client() -> Client | None:
    """Cria cliente Supabase a partir de session state, environment ou secrets."""
    if not create_client:
        return None
    url = (st.session_state.get("supabase_url_input") or "").strip()
    key = (st.session_state.get("supabase_key_input") or "").strip()
    if not url:
        url = os.getenv("SUPABASE_URL", "").strip()
    if not key:
        key = os.getenv("SUPABASE_KEY", "").strip()
    if not url:
        url = (st.secrets.get("SUPABASE_URL", "") if hasattr(st, "secrets") else "").strip()
    if not key:
        key = (st.secrets.get("SUPABASE_KEY", "") if hasattr(st, "secrets") else "").strip()
    if not url or not key:
        return None
    try:
        return create_client(url, key)
    except Exception:
        return None


def render_supabase_setup() -> None:
    """Tela rápida para configurar credenciais Supabase quando ausentes."""
    st.error("Supabase não configurado.")
    render_public_trust_landing()
    st.markdown("### Configure as credenciais para entrar no app")
    with st.form("supabase_setup_form", border=True):
        st.text_input(
            "SUPABASE_URL",
            value=st.session_state.get("supabase_url_input", ""),
            placeholder="https://seu-projeto.supabase.co",
            key="supabase_url_input",
        )
        st.text_input(
            "SUPABASE_KEY (anon key)",
            value=st.session_state.get("supabase_key_input", ""),
            type="password",
            placeholder="eyJhbGciOi...",
            key="supabase_key_input",
        )
        submitted = st.form_submit_button("Salvar e testar conexão", use_container_width=True)
        if submitted:
            if get_supabase_client():
                st.success("Conexão Supabase configurada com sucesso.")
                st.rerun()
            else:
                st.warning("Não consegui conectar. Verifique URL e KEY.")
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
    row = {"user_id": user_id, "role": role, "content": content}
    try:
        res = (
            supabase.table(SUPABASE_HISTORY_TABLE)
            .insert(row)
            .select("ego_msg_id")
            .execute()
        )
        if res.data and res.data[0].get("ego_msg_id"):
            return str(res.data[0]["ego_msg_id"])
    except Exception:
        pass
    try:
        res = (
            supabase.table(SUPABASE_HISTORY_TABLE)
            .insert(row)
            .select("id")
            .execute()
        )
        if res.data and res.data[0].get("id") is not None:
            return str(res.data[0]["id"])
    except Exception:
        pass
    try:
        supabase.table(SUPABASE_HISTORY_TABLE).insert(row).execute()
    except Exception:
        pass
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
    """Contagem de tokens (OpenAI cl100k); aproximação útil também para Gemini."""
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


def build_chat_export_pdf_bytes(messages: list) -> bytes:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas as pdfcanvas
    except ImportError:
        return b""

    buf = BytesIO()
    c = pdfcanvas.Canvas(buf, pagesize=A4)
    _, h = A4
    x_margin, y_top = 40, h - 48
    y = y_top
    c.setFont("Helvetica", 9)
    for m in messages:
        role = str(m.get("role", "?"))
        content = str(m.get("content") or "")
        block = f"{role.upper()}: {content}"
        for raw_line in block.split("\n"):
            line = raw_line[:120]
            safe = line.encode("latin-1", "replace").decode("latin-1")
            if y < 48:
                c.showPage()
                y = y_top
                c.setFont("Helvetica", 9)
            c.drawString(x_margin, y, safe)
            y -= 12
    c.save()
    return buf.getvalue()


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
    wa = ego_whatsapp_business_url()
    mensal = html.escape(PAYWALL_PRECO_MENSAL)
    anual = html.escape(PAYWALL_PRECO_ANUAL)
    wa_btn = (
        f'<a class="ego-glass-cta" href="{html.escape(wa)}" target="_blank" rel="noopener noreferrer">'
        "WhatsApp Business</a>"
        if wa
        else '<span class="ego-glass-cta" style="opacity:0.5;">WhatsApp (configure EGO_SUPPORT_WHATSAPP)</span>'
    )
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
    &nbsp;&nbsp;{wa_btn}
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


def render_chat_messages_with_feedback(supabase: Client | None, user_id: str) -> None:
    msgs = st.session_state.get("messages") or []
    if not msgs:
        st.caption("Nenhuma mensagem ainda. Envie algo abaixo para começar.")
        return
    provider = st.session_state.get("ego_ai_provider", "Gemini")
    for i, msg in enumerate(msgs):
        role = msg.get("role", "user")
        with st.chat_message(role):
            st.markdown(msg.get("content") or "")
            mid = msg.get("msg_id")
            if role == "assistant" and mid and user_id and supabase:
                u1, u2 = st.columns(2)
                with u1:
                    if st.button("👍 Útil", key=f"fb_up_{mid}_{i}", use_container_width=True):
                        save_message_feedback(supabase, user_id, str(mid), 1, provider)
                        st.toast("Obrigado pelo feedback.")
                with u2:
                    if st.button("👎 Não útil", key=f"fb_dn_{mid}_{i}", use_container_width=True):
                        save_message_feedback(supabase, user_id, str(mid), -1, provider)
                        st.toast("Obrigado pelo feedback.")


def salvar_perfil_seguro(
    supabase: Client | None,
    *,
    user_id: str,
    full_name: str,
    email: str,
    country: str,
    document_type: str,
) -> None:
    """Cria/atualiza perfil completo do usuário logado."""
    if not supabase:
        return
    try:
        supabase.table(SUPABASE_PROFILES_TABLE).upsert(
            {
                "id": user_id,
                "full_name": full_name,
                "email": email,
                "country": country,
                "document_type": document_type,
            }
        ).execute()
    except Exception:
        pass


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


def save_food_event(
    supabase: Client | None,
    user_id: str,
    query: str,
    city: str,
    country: str,
    options: list[dict],
    price_tier: str = "",
) -> None:
    """Persiste busca/comida sugerida quando tabela existir."""
    if not supabase or not user_id:
        return
    row: dict = {
        "user_id": user_id,
        "query": query,
        "city": city,
        "country": country,
        "options": options,
    }
    if price_tier:
        row["price_tier"] = price_tier
    try:
        supabase.table(SUPABASE_FOOD_TABLE).insert(row).execute()
    except Exception:
        try:
            row.pop("price_tier", None)
            supabase.table(SUPABASE_FOOD_TABLE).insert(row).execute()
        except Exception:
            pass


def save_drink_event(
    supabase: Client | None,
    user_id: str,
    query: str,
    city: str,
    country: str,
    options: list[dict],
    price_tier: str = "",
    drink_category: str = "",
) -> None:
    """Persiste busca de bebidas quando a tabela existir."""
    if not supabase or not user_id:
        return
    row: dict = {
        "user_id": user_id,
        "query": query,
        "city": city,
        "country": country,
        "options": options,
    }
    if price_tier:
        row["price_tier"] = price_tier
    if drink_category:
        row["drink_category"] = drink_category
    while True:
        try:
            supabase.table(SUPABASE_DRINK_TABLE).insert(row).execute()
            return
        except Exception:
            if "drink_category" in row:
                row.pop("drink_category", None)
                continue
            if "price_tier" in row:
                row.pop("price_tier", None)
                continue
            break


def save_nightlife_event(
    supabase: Client | None,
    user_id: str,
    query: str,
    city: str,
    country: str,
    options: list[dict],
    price_tier: str = "",
    venue_category: str = "",
) -> None:
    """Persiste busca de bares, pubs e restaurantes quando a tabela existir."""
    if not supabase or not user_id:
        return
    row: dict = {
        "user_id": user_id,
        "query": query,
        "city": city,
        "country": country,
        "options": options,
    }
    if price_tier:
        row["price_tier"] = price_tier
    if venue_category:
        row["venue_category"] = venue_category
    while True:
        try:
            supabase.table(SUPABASE_NIGHTLIFE_TABLE).insert(row).execute()
            return
        except Exception:
            if "venue_category" in row:
                row.pop("venue_category", None)
                continue
            if "price_tier" in row:
                row.pop("price_tier", None)
                continue
            break


def save_shopping_event(
    supabase: Client | None,
    user_id: str,
    query: str,
    options: list[dict],
    price_tier: str = "",
    shop_category: str = "",
    market_region: str = "",
) -> None:
    """Persiste busca de produtos online quando a tabela existir."""
    if not supabase or not user_id:
        return
    row: dict = {
        "user_id": user_id,
        "query": query,
        "options": options,
    }
    if price_tier:
        row["price_tier"] = price_tier
    if shop_category:
        row["shop_category"] = shop_category
    if market_region:
        row["market_region"] = market_region
    while True:
        try:
            supabase.table(SUPABASE_SHOP_TABLE).insert(row).execute()
            return
        except Exception:
            if "market_region" in row:
                row.pop("market_region", None)
                continue
            if "shop_category" in row:
                row.pop("shop_category", None)
                continue
            if "price_tier" in row:
                row.pop("price_tier", None)
                continue
            break


def save_travel_event(
    supabase: Client | None,
    user_id: str,
    destination: str,
    query: str,
    options: list[dict],
    price_tier: str = "",
    travel_mode: str = "",
    travel_subcategory: str = "",
    market_region: str = "",
    origin_hint: str = "",
) -> None:
    """Persiste busca de hospedagem / pacotes quando a tabela existir."""
    if not supabase or not user_id:
        return
    row: dict = {
        "user_id": user_id,
        "destination": destination,
        "query": query,
        "options": options,
    }
    if price_tier:
        row["price_tier"] = price_tier
    if travel_mode:
        row["travel_mode"] = travel_mode
    if travel_subcategory:
        row["travel_subcategory"] = travel_subcategory
    if market_region:
        row["market_region"] = market_region
    if origin_hint:
        row["origin_hint"] = origin_hint
    while True:
        try:
            supabase.table(SUPABASE_TRAVEL_TABLE).insert(row).execute()
            return
        except Exception:
            if "origin_hint" in row:
                row.pop("origin_hint", None)
                continue
            if "market_region" in row:
                row.pop("market_region", None)
                continue
            if "travel_subcategory" in row:
                row.pop("travel_subcategory", None)
                continue
            if "travel_mode" in row:
                row.pop("travel_mode", None)
                continue
            if "price_tier" in row:
                row.pop("price_tier", None)
                continue
            break


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distância em linha reta entre dois pontos (km)."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def _nominatim_search(q: str, limit: int = 8) -> list[dict]:
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": q, "format": "jsonv2", "limit": limit},
            headers={"User-Agent": "EGO-AI/1.0"},
            timeout=12,
        )
        resp.raise_for_status()
        return resp.json() or []
    except Exception:
        return []


def _geocode_reference(city: str, country: str) -> tuple[float, float] | None:
    """Centro aproximado da região (cidade + país) para calcular distâncias."""
    parts = [p.strip() for p in [city, country] if p and p.strip()]
    if not parts:
        return None
    data = _nominatim_search(" ".join(parts), limit=1)
    if not data:
        return None
    row = data[0]
    try:
        lat = float(row.get("lat"))
        lon = float(row.get("lon"))
        return lat, lon
    except (TypeError, ValueError):
        return None


FOOD_PRICE_TIERS = ("Economia", "Padrão", "Premium")
FOOD_PRICE_QUERY_HINT: dict[str, str] = {
    "Economia": "cheap affordable budget casual",
    "Padrão": "restaurant",
    "Premium": "fine dining upscale gourmet",
}

DRINK_PRICE_QUERY_HINT: dict[str, str] = {
    "Economia": "cheap affordable budget local",
    "Padrão": "cafe bar drinks beverage",
    "Premium": "wine cocktail lounge speakeasy upscale craft",
}

DRINK_CATEGORIES = (
    "Café e espresso",
    "Chá, bubble tea e casas de chá",
    "Suco, smoothie, açaí e vitamina",
    "Refrigerante, energético e conveniência",
    "Cerveja, pub e brewpub",
    "Vinho, bar de vinhos e adega",
    "Coquetéis, destilados e rooftop",
    "Outro",
)
DRINK_TYPE_HINTS: dict[str, str] = {
    "Café e espresso": "coffee espresso cafe roastery",
    "Chá, bubble tea e casas de chá": "tea bubble tea teahouse",
    "Suco, smoothie, açaí e vitamina": "juice smoothie acai açaí frutaria",
    "Refrigerante, energético e conveniência": "convenience store beverages soft drink",
    "Cerveja, pub e brewpub": "beer pub brewpub cervejaria",
    "Vinho, bar de vinhos e adega": "wine bar enoteca adega",
    "Coquetéis, destilados e rooftop": "cocktail bar distillery rooftop lounge",
    "Outro": "",
}


def _search_venues_nearby(
    user_terms: str,
    city: str,
    country: str,
    price_tier: str,
    tier_hints: dict[str, str],
) -> list[dict]:
    """
    Busca via Nominatim com dica de faixa de preço + local; ordena por distância ao centro cidade+país.
    """
    q_base = (user_terms or "").strip()
    if not q_base:
        return []
    tier = price_tier if price_tier in tier_hints else "Padrão"
    hint = tier_hints[tier]
    loc_bits = " ".join(x for x in [city.strip(), country.strip()] if x)
    search_q = f"{q_base} {hint} {loc_bits}".strip()
    ref = _geocode_reference(city, country)
    data = _nominatim_search(search_q, limit=12)
    out: list[dict] = []
    for row in data:
        name = row.get("name") or row.get("display_name", "Opção")
        address = row.get("display_name", "")
        map_query = requests.utils.quote(f"{name} {address}")
        link = f"https://www.google.com/maps/search/?api=1&query={map_query}"
        item: dict = {
            "name": name,
            "address": address,
            "link": link,
            "price_band": tier,
        }
        try:
            plat = float(row.get("lat"))
            plon = float(row.get("lon"))
        except (TypeError, ValueError):
            plat = plon = None  # type: ignore[assignment]
        if ref and plat is not None and plon is not None:
            item["distance_km"] = round(_haversine_km(ref[0], ref[1], plat, plon), 1)
        else:
            item["distance_km"] = None
        out.append(item)

    def sort_key(d: dict) -> tuple[int, float]:
        dist = d.get("distance_km")
        if dist is None:
            return (1, 9999.0)
        return (0, float(dist))

    out.sort(key=sort_key)
    return out[:8]


def search_food_nearby(
    query: str,
    city: str,
    country: str,
    price_tier: str = "Padrão",
) -> list[dict]:
    """Comida: query livre + refinamento por faixa de preço."""
    q_base = (query or "").strip()
    if not q_base:
        return []
    return _search_venues_nearby(q_base, city, country, price_tier, FOOD_PRICE_QUERY_HINT)


def search_drink_nearby(
    query: str,
    city: str,
    country: str,
    price_tier: str = "Padrão",
    drink_category: str = "Outro",
) -> list[dict]:
    """Bebidas: categoria (café, chá, cerveja, etc.) + texto opcional + faixa de preço."""
    extra = (DRINK_TYPE_HINTS.get(drink_category) or "").strip()
    q_user = (query or "").strip()
    if drink_category == "Outro" and not q_user:
        return []
    if q_user:
        combined = f"{q_user} {extra}".strip()
    else:
        combined = extra
    if not combined:
        return []
    return _search_venues_nearby(combined, city, country, price_tier, DRINK_PRICE_QUERY_HINT)


NIGHTLIFE_PRICE_QUERY_HINT: dict[str, str] = {
    "Economia": "cheap happy hour dive local casual affordable",
    "Padrão": "restaurant bar pub dining drinks",
    "Premium": "rooftop cocktail upscale wine tasting chef fine dining",
}

_NIGHTLIFE_VENUE_PAIRS: tuple[tuple[str, str], ...] = (
    ("Restaurante (refeição)", "restaurant dining lunch dinner"),
    ("Bar e balada", "bar nightclub dance lounge live music"),
    ("Pub e sports bar", "pub sports bar draft beer tv"),
    ("Cervejaria e brewpub", "brewpub craft beer taproom cervejaria"),
    ("Wine bar e harmonização", "wine bar tasting charcuterie cheese pairing"),
    ("Rodízio e churrascaria", "churrascaria rodizio steakhouse brazilian bbq"),
    ("Boteco e petiscos", "boteco petiscos tapas casual bar food"),
    ("Hamburgueria e lanchonete", "burger diner hamburger sandwich fast casual"),
    ("Café, bistrô e brunch", "cafe bistro brunch breakfast"),
    ("Outro", ""),
)
NIGHTLIFE_VENUE_LABELS = tuple(p[0] for p in _NIGHTLIFE_VENUE_PAIRS)
NIGHTLIFE_VENUE_HINTS: dict[str, str] = dict(_NIGHTLIFE_VENUE_PAIRS)


def search_nightlife_nearby(
    query: str,
    city: str,
    country: str,
    price_tier: str = "Padrão",
    venue_category: str = "Outro",
) -> list[dict]:
    """Bares, pubs, restaurantes: tipo de estabelecimento + texto opcional + mapa (Nominatim)."""
    extra = (NIGHTLIFE_VENUE_HINTS.get(venue_category) or "").strip()
    q_user = (query or "").strip()
    if venue_category == "Outro" and not q_user:
        return []
    if q_user:
        combined = f"{q_user} {extra}".strip()
    else:
        combined = extra
    if not combined:
        return []
    return _search_venues_nearby(combined, city, country, price_tier, NIGHTLIFE_PRICE_QUERY_HINT)


_SHOP_PAIRS: tuple[tuple[str, str], ...] = (
    ("Eletrodomésticos e cozinha", "geladeira fogão microondas air fryer liquidificador eletrodomésticos cozinha"),
    ("TV, áudio e home theater", "smart tv soundbar home theater projetor caixa de som"),
    ("Informática e periféricos", "notebook monitor teclado mouse impressora SSD memória periféricos"),
    ("Games e consoles", "console videogame controle headset gamer placa de vídeo"),
    ("Celulares, tablets e smartwatches", "smartphone celular tablet smartwatch fone bluetooth capa"),
    ("Moda: camisetas, blusas e casacos", "camiseta blusa casaco moletom jaqueta moda masculina feminina"),
    ("Moda: calças, bermudas e shorts", "calça jeans bermuda shorts legging moda"),
    ("Moda: vestidos, saias e conjuntos", "vestido saia conjunto macacão moda feminina"),
    ("Moda: calçados", "tênis sapato sandália bota chinelo calçados"),
    ("Óculos, relógios e joias", "óculos relógio pulseira colar anel joias acessórios"),
    ("Beleza, perfumaria e cuidados", "perfume skincare maquiagem shampoo barbeador beleza"),
    ("Casa, móveis, cama e decoração", "sofá mesa cama roupa de cama decoração luminária tapete organizador"),
    ("Ferramentas, construção e jardim", "furadeira parafusadeira ferramenta tinta jardim vaso"),
    ("Automotivo e peças", "pneu acessório carro moto peça automotiva capa banco"),
    ("Esporte, academia e outdoor", "bicicleta esteira halter bola tênis corrida camping mochila"),
    ("Brinquedos, bebê e infantil", "brinquedo boneca lego bebê fralda carrinho infantil"),
    ("Livros, papelaria e hobbies", "livro caderno caneta kindle papelaria hobbie"),
    ("Pet shop", "ração pet brinquedo cachorro gato coleira comedouro"),
    ("Supermercado e alimentos online", "mercado alimento despensa bebida não alcoólica snack"),
    ("Farmácia, saúde e suplementos", "vitamina medicamento termômetro máscara suplemento saúde"),
    ("Maletas, mochilas e viagem", "mala mochila necessaire organizador viagem"),
    ("Outro", ""),
)
SHOP_CATEGORY_LABELS = tuple(p[0] for p in _SHOP_PAIRS)
SHOP_CATEGORY_HINTS: dict[str, str] = dict(_SHOP_PAIRS)

SHOP_MARKETS = ("Brasil", "Estados Unidos", "Global")

SHOP_PRICE_QUERY_HINT: dict[str, str] = {
    "Economia": "barato promoção oferta custo benefício",
    "Padrão": "comprar online entrega",
    "Premium": "premium lançamento importado luxo edição especial",
}


def search_online_products(
    query: str,
    shop_category: str,
    price_tier: str = "Padrão",
    market: str = "Brasil",
) -> list[dict]:
    """
    Monta atalhos para comparar preços online (Google Shopping, marketplaces).
    Não faz scraping: só URLs de busca seguras para o usuário abrir no navegador.
    """
    q_user = (query or "").strip()
    if shop_category == "Outro" and not q_user:
        return []
    cat_hint = (SHOP_CATEGORY_HINTS.get(shop_category) or "").strip() if shop_category != "Outro" else ""
    tier = price_tier if price_tier in SHOP_PRICE_QUERY_HINT else "Padrão"
    ph = SHOP_PRICE_QUERY_HINT[tier].strip()
    core = " ".join(x for x in [q_user, cat_hint, ph] if x).strip()
    if not core:
        return []
    enc = requests.utils.quote(core)
    buy_q = requests.utils.quote(f"comprar {core}")
    out: list[dict] = []
    out.append(
        {
            "name": "Google Shopping",
            "link": f"https://www.google.com/search?tbm=shop&q={enc}",
            "price_band": tier,
        }
    )
    out.append(
        {
            "name": "Busca web (comprar)",
            "link": f"https://www.google.com/search?q={buy_q}",
            "price_band": tier,
        }
    )
    if market in ("Brasil", "Global"):
        out.append(
            {
                "name": "Mercado Livre",
                "link": f"https://www.mercadolivre.com.br/jm/search?as_word={enc}",
                "price_band": tier,
            }
        )
        out.append(
            {
                "name": "Amazon.com.br",
                "link": f"https://www.amazon.com.br/s?k={enc}",
                "price_band": tier,
            }
        )
        out.append(
            {
                "name": "Shopee Brasil",
                "link": f"https://shopee.com.br/search?keyword={enc}",
                "price_band": tier,
            }
        )
    if market in ("Estados Unidos", "Global"):
        out.append(
            {
                "name": "Amazon.com",
                "link": f"https://www.amazon.com/s?k={enc}",
                "price_band": tier,
            }
        )
    seen: set[str] = set()
    deduped: list[dict] = []
    for item in out:
        u = item.get("link", "")
        if not u or u in seen:
            continue
        seen.add(u)
        deduped.append(item)
    return deduped


TRAVEL_MODES = ("Hospedagem", "Pacote de viagem")

_HOTEL_SUB: tuple[tuple[str, str], ...] = (
    ("Hotel urbano", "hotel cidade centro"),
    ("Resort ou all inclusive", "resort all inclusive praia spa"),
    ("Pousada ou chalé", "pousada chalé sítio café da manhã"),
    ("Hostel ou albergue", "hostel albergue dormitório mochilão"),
    ("Apartamento por temporada", "apartamento temporada airbnb booking"),
    ("Casa ou temporada em condomínio", "casa temporada condomínio piscina"),
    ("Outro", ""),
)
HOTEL_SUB_LABELS = tuple(p[0] for p in _HOTEL_SUB)
HOTEL_SUB_HINTS: dict[str, str] = dict(_HOTEL_SUB)

_PKG_SUB: tuple[tuple[str, str], ...] = (
    ("Praia no Brasil", "praia litoral resort nordeste sul"),
    ("Serra, frio e natureza (BR)", "serra gramado campos jordão montanha frio"),
    ("Grande cidade (BR)", "são paulo rio curitiba belo horizonte city tour"),
    ("Internacional — Américas", "miami cancun buenos aires santiago caribe"),
    ("Internacional — Europa ou Ásia", "europa paris lisboa toquio bangkok"),
    ("Cruzeiro marítimo", "cruzeiro navio marítimo all inclusive"),
    ("Lua de mel", "lua de mel honeymoon romântico resort"),
    ("Viagem a negócios", "negócios corporativo hotel aeroporto"),
    ("Feriado prolongado", "feriado prolongado fim de semana estendido"),
    ("Outro", ""),
)
PKG_SUB_LABELS = tuple(p[0] for p in _PKG_SUB)
PKG_SUB_HINTS: dict[str, str] = dict(_PKG_SUB)

TRAVEL_PRICE_QUERY_HINT: dict[str, str] = {
    "Economia": "econômico barato promoção",
    "Padrão": "bem avaliado",
    "Premium": "luxo 5 estrelas boutique resort exclusivo",
}


def search_travel_links(
    travel_mode: str,
    subcategory: str,
    destination: str,
    origin_hint: str,
    extra_query: str,
    price_tier: str = "Padrão",
    market: str = "Brasil",
) -> list[dict]:
    """
    Atalhos para pesquisar hospedagem e pacotes (Google Travel, Booking, buscas agregadoras).
    Não reserva nem mostra preços: só abre buscas no navegador.
    """
    dest = (destination or "").strip()
    if not dest:
        return []
    tier = price_tier if price_tier in TRAVEL_PRICE_QUERY_HINT else "Padrão"
    ph = (TRAVEL_PRICE_QUERY_HINT.get(tier) or "").strip()
    extra = (extra_query or "").strip()
    origin = (origin_hint or "").strip()

    if travel_mode == "Hospedagem":
        hint = (HOTEL_SUB_HINTS.get(subcategory) or "").strip() if subcategory != "Outro" else ""
        hotel_terms = " ".join(x for x in [dest, "hotel hospedagem", hint, ph, extra] if x)
        pkg_terms = ""
    else:
        hint = (PKG_SUB_HINTS.get(subcategory) or "").strip() if subcategory != "Outro" else ""
        hotel_terms = " ".join(x for x in [dest, "hotel", ph, extra] if x)
        pkg_parts = ["pacote viagem", dest, hint, ph, extra]
        if origin:
            pkg_parts.insert(0, f"saindo de {origin}")
        pkg_terms = " ".join(x for x in pkg_parts if x)

    dest_enc = requests.utils.quote(dest)
    out: list[dict] = []

    out.append(
        {
            "name": "Google Travel — Hotéis",
            "link": f"https://www.google.com/travel/hotels?q={requests.utils.quote(hotel_terms)}",
            "price_band": tier,
        }
    )
    out.append(
        {
            "name": "Booking.com",
            "link": f"https://www.booking.com/searchresults.html?ss={dest_enc}",
            "price_band": tier,
        }
    )
    out.append(
        {
            "name": "Airbnb (busca web)",
            "link": f"https://www.google.com/search?q={requests.utils.quote('airbnb ' + dest + ' ' + extra)}",
            "price_band": tier,
        }
    )

    if travel_mode == "Pacote de viagem" and pkg_terms:
        out.append(
            {
                "name": "Busca — pacotes (voo + hotel)",
                "link": f"https://www.google.com/search?q={requests.utils.quote(pkg_terms)}",
                "price_band": tier,
            }
        )
        flight_q = " ".join(x for x in [origin, dest, extra] if x) if origin else " ".join(x for x in [dest, extra, "passagens"] if x)
        out.append(
            {
                "name": "Google Flights",
                "link": f"https://www.google.com/travel/flights?q={requests.utils.quote(flight_q)}",
                "price_band": tier,
            }
        )

    if market in ("Brasil", "Global"):
        br_q = (
            pkg_terms
            if travel_mode == "Pacote de viagem" and pkg_terms
            else " ".join(x for x in [dest, "hotel", "decolar", "cvc", extra] if x)
        )
        out.append(
            {
                "name": "Agências BR (referência na busca)",
                "link": f"https://www.google.com/search?q={requests.utils.quote(br_q)}",
                "price_band": tier,
            }
        )

    seen: set[str] = set()
    deduped: list[dict] = []
    for item in out:
        u = item.get("link", "")
        if not u or u in seen:
            continue
        seen.add(u)
        deduped.append(item)
    return deduped


def _travel_entry_label(h: dict) -> str:
    """Rótulo estável para histórico / dashboard / prompt."""
    mode = str(h.get("travel_mode", "")).strip()
    sub = str(h.get("travel_subcategory", "")).strip()
    dest = str(h.get("destination", "")).strip()
    q = str(h.get("query", "")).strip()
    if mode and sub and dest:
        base = f"{mode} — {sub}: {dest}"
    elif dest and mode:
        base = f"{mode}: {dest}"
    elif dest:
        base = dest
    else:
        base = mode or "viagem"
    if q:
        return f"{base} ({q[:48]}{'…' if len(q) > 48 else ''})"
    return base


def build_food_hint() -> str:
    """Resumo curto do histórico de comida e bebidas para recomendação contextual da IA."""
    parts: list[str] = []
    food_hist = st.session_state.get("food_history") or []
    fq = [str(h.get("query", "")).strip() for h in food_hist if str(h.get("query", "")).strip()]
    if fq:
        top = Counter(fq).most_common(3)
        top_text = ", ".join([f"{q} ({n}x)" for q, n in top])
        parts.append(
            "\n\nContexto de preferências de comida do usuário: "
            f"itens mais buscados recentemente: {top_text}. "
            "Ao responder sobre o que comer hoje, use esse histórico para sugerir opções."
        )
    drink_hist = st.session_state.get("drink_history") or []
    dq: list[str] = []
    for h in drink_hist:
        cat = str(h.get("drink_category", "")).strip()
        q = str(h.get("query", "")).strip()
        if q and cat:
            dq.append(f"{cat}: {q}")
        elif cat:
            dq.append(cat)
        elif q:
            dq.append(q)
    if dq:
        top_d = Counter(dq).most_common(3)
        d_text = ", ".join([f"{q} ({n}x)" for q, n in top_d])
        parts.append(
            "\n\nContexto de bebidas (café, chá, suco, álcool, etc.): "
            f"buscas recentes mais frequentes: {d_text}. "
            "Ao sugerir bebidas ou lugares para beber, considere esse histórico."
        )
    nl_hist = st.session_state.get("nightlife_history") or []
    nlq: list[str] = []
    for h in nl_hist:
        cat = str(h.get("venue_category", "")).strip()
        q = str(h.get("query", "")).strip()
        if q and cat:
            nlq.append(f"{cat}: {q}")
        elif cat:
            nlq.append(cat)
        elif q:
            nlq.append(q)
    if nlq:
        top_n = Counter(nlq).most_common(3)
        n_text = ", ".join([f"{q} ({n}x)" for q, n in top_n])
        parts.append(
            "\n\nContexto de bares, pubs e restaurantes (saída à noite): "
            f"buscas recentes mais frequentes: {n_text}. "
            "Ao sugerir onde comer fora ou sair à noite, use esse histórico (estilo e orçamento)."
        )
    shop_hist = st.session_state.get("shopping_history") or []
    sq: list[str] = []
    for h in shop_hist:
        cat = str(h.get("shop_category", "")).strip()
        q = str(h.get("query", "")).strip()
        if q and cat:
            sq.append(f"{cat}: {q}")
        elif cat:
            sq.append(cat)
        elif q:
            sq.append(q)
    if sq:
        top_s = Counter(sq).most_common(3)
        s_text = ", ".join([f"{q} ({n}x)" for q, n in top_s])
        parts.append(
            "\n\nContexto de compras online (eletrodomésticos, moda, eletrônicos, etc.): "
            f"buscas recentes mais frequentes: {s_text}. "
            "Ao recomendar produtos ou lojas, considere esse histórico (preço e categoria)."
        )
    trav_hist = st.session_state.get("travel_history") or []
    tlabels = [_travel_entry_label(h) for h in trav_hist]
    tlabels = [x for x in tlabels if x and x != "viagem"]
    if tlabels:
        top_t = Counter(tlabels).most_common(3)
        t_text = ", ".join([f"{q} ({n}x)" for q, n in top_t])
        parts.append(
            "\n\nContexto de viagens e hospedagem do usuário: "
            f"destinos e tipos mais buscados: {t_text}. "
            "Ao sugerir hotéis, pacotes ou roteiros, considere esse histórico (orçamento e estilo)."
        )
    return "".join(parts)


def format_food_option_label(opt: dict) -> str:
    """Rótulo curto para botão de mapa: nome, distância aproximada e faixa de preço."""
    name = str(opt.get("name") or "Opção")
    bits = [name]
    dist = opt.get("distance_km")
    if dist is not None:
        bits.append(f"~{dist} km")
    band = opt.get("price_band")
    if band:
        bits.append(str(band))
    return " · ".join(bits)


def food_history_top_queries(limit: int = 3) -> list[tuple[str, int]]:
    """Tipos de comida mais buscados na sessão (para o dashboard)."""
    history = st.session_state.get("food_history") or []
    queries = [str(h.get("query", "")).strip() for h in history if str(h.get("query", "")).strip()]
    if not queries:
        return []
    return Counter(queries).most_common(limit)


def drink_history_top_queries(limit: int = 3) -> list[tuple[str, int]]:
    """Combinações categoria + bebida mais buscadas na sessão (para o dashboard)."""
    history = st.session_state.get("drink_history") or []
    labels: list[str] = []
    for h in history:
        cat = str(h.get("drink_category", "")).strip()
        q = str(h.get("query", "")).strip()
        if q and cat:
            labels.append(f"{cat}: {q}")
        elif cat:
            labels.append(cat)
        elif q:
            labels.append(q)
    if not labels:
        return []
    return Counter(labels).most_common(limit)


def shopping_history_top_queries(limit: int = 3) -> list[tuple[str, int]]:
    """Categoria + produto mais buscados na sessão (compras online)."""
    history = st.session_state.get("shopping_history") or []
    labels: list[str] = []
    for h in history:
        cat = str(h.get("shop_category", "")).strip()
        q = str(h.get("query", "")).strip()
        if q and cat:
            labels.append(f"{cat}: {q}")
        elif cat:
            labels.append(cat)
        elif q:
            labels.append(q)
    if not labels:
        return []
    return Counter(labels).most_common(limit)


def shopping_dashboard_search_url(text: str) -> str:
    """Reabre comparação no Google Shopping a partir do rótulo do histórico."""
    return f"https://www.google.com/search?tbm=shop&q={requests.utils.quote(text.strip())}"


def nightlife_history_top_queries(limit: int = 3) -> list[tuple[str, int]]:
    """Categoria de estabelecimento + busca mais frequentes (bares / restaurantes)."""
    history = st.session_state.get("nightlife_history") or []
    labels: list[str] = []
    for h in history:
        cat = str(h.get("venue_category", "")).strip()
        q = str(h.get("query", "")).strip()
        if q and cat:
            labels.append(f"{cat}: {q}")
        elif cat:
            labels.append(cat)
        elif q:
            labels.append(q)
    if not labels:
        return []
    return Counter(labels).most_common(limit)


def travel_history_top_queries(limit: int = 3) -> list[tuple[str, int]]:
    """Hospedagem / pacotes mais buscados na sessão (rótulo composto)."""
    history = st.session_state.get("travel_history") or []
    labels = [_travel_entry_label(h) for h in history]
    labels = [x for x in labels if x and x != "viagem"]
    if not labels:
        return []
    return Counter(labels).most_common(limit)


def travel_dashboard_open_url(text: str) -> str:
    """Reabre busca agregada (hotéis / pacotes) a partir do rótulo do histórico."""
    return f"https://www.google.com/search?q={requests.utils.quote(text.strip())}"


def food_dashboard_maps_url(query: str) -> str:
    """Link Google Maps para reabrir a busca com cidade/país da sessão."""
    city = (st.session_state.get("food_city") or "").strip()
    country = (st.session_state.get("food_country") or "").strip()
    tail = " ".join(x for x in [city, country] if x)
    full = f"{query.strip()} {tail}".strip()
    return f"https://www.google.com/maps/search/?api=1&query={requests.utils.quote(full)}"


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
        f"\n\nCRITICAL: Reply strictly in {label} ({code}). "
        "If uncertain, keep exactly the user's language."
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


def verificar_acesso(supabase: Client | None, user_id: str) -> tuple[bool, str]:
    """Retorna (acesso_liberado, status): Pro, beta (EGO_BETA_DEADLINE), trial (EGO_TRIAL_DAYS) ou expirado."""
    if not supabase:
        return True, "Modo Local"
    agora = datetime.datetime.now(datetime.timezone.utc)
    beta_fim = _ego_beta_deadline()
    try:
        perfil = (
            supabase.table(SUPABASE_PROFILES_TABLE)
            .select("created_at,is_pro")
            .eq("id", user_id)
            .single()
            .execute()
        )
        data = perfil.data or {}
        is_pro = bool(data.get("is_pro", False))
        if is_pro:
            return True, "Pro"
        if _ego_beta_sem_limite():
            return True, "Beta (sem limite)"
        if beta_fim and agora < beta_fim:
            return True, "Beta grátis"
        created_at = data.get("created_at")
        if not created_at:
            # Perfil sem data: não bloquear (evita "expirado" falso no primeiro acesso).
            return True, f"Trial ({EGO_TRIAL_DAYS} dias restantes)"
        data_criacao = datetime.datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        dias_de_uso = (agora - data_criacao).days
        if dias_de_uso <= EGO_TRIAL_DAYS:
            return True, f"Trial ({EGO_TRIAL_DAYS - dias_de_uso} dias restantes)"
        return False, "Expirado"
    except Exception:
        if _ego_beta_sem_limite():
            return True, "Beta (sem limite)"
        if beta_fim and agora < beta_fim:
            return True, "Beta grátis"
        return False, "Expirado"


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
    clean = (text[:idx].rstrip() + "\n" + text[end + 2 :].lstrip()).strip()
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict) and obj.get("scheduled_at"):
            return clean, [obj]
    except json.JSONDecodeError:
        pass
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
    supabase: Client | None, user_id: str, *, hours_back: int = 1, hours_ahead: int = 48
) -> list[dict]:
    if not supabase or not user_id:
        return []
    now = datetime.datetime.now(datetime.timezone.utc)
    start = (now - datetime.timedelta(hours=hours_back)).isoformat()
    end = (now + datetime.timedelta(hours=hours_ahead)).isoformat()
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
    scheduled_at: datetime.datetime,
    announce: str = "",
    google_event_id: str | None = None,
) -> bool:
    if not supabase or not user_id:
        return False
    row: dict = {
        "user_id": user_id,
        "title": (title or "Lembrete")[:500],
        "scheduled_at": scheduled_at.astimezone(datetime.timezone.utc).isoformat(),
        "announce": (announce or title or "")[:2000],
    }
    if google_event_id:
        row["google_event_id"] = str(google_event_id)[:300]
    try:
        supabase.table(SUPABASE_REMINDERS_TABLE).insert(row).execute()
        return True
    except Exception:
        if google_event_id and "google_event_id" in row:
            row.pop("google_event_id", None)
            try:
                supabase.table(SUPABASE_REMINDERS_TABLE).insert(row).execute()
                return True
            except Exception:
                return False
        return False


def process_assistant_reminders(
    supabase: Client | None, user_id: str, reply: str
) -> str:
    clean, items = extract_ego_reminders_from_reply(reply)
    if not user_id or not supabase or not items:
        return clean
    for it in items:
        st_iso = it.get("scheduled_at")
        dt = _parse_ts_iso(st_iso if isinstance(st_iso, str) else None)
        if not dt:
            continue
        title = str(it.get("title") or "Lembrete")[:500]
        announce = str(it.get("announce") or title)[:2000]
        insert_reminder_row(supabase, user_id, title=title, scheduled_at=dt, announce=announce)
    return clean


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


def try_speech_reminder(text: str, html_key: str) -> None:
    """Tenta falar no navegador (Web Speech). Pode ser bloqueado sem gesto do usuário."""
    try:
        import streamlit.components.v1 as components
    except ImportError:
        return
    safe = json.dumps((text or "")[:2000])
    components.html(
        f"""
<div id="ego-tts-{html_key}"></div>
<script>
(function() {{
  const msg = {safe};
  if (!msg || !('speechSynthesis' in window)) return;
  const u = new SpeechSynthesisUtterance(msg);
  const lang = navigator.language || 'pt-BR';
  u.lang = lang.startsWith('pt') ? 'pt-BR' : lang;
  try {{ speechSynthesis.cancel(); speechSynthesis.speak(u); }} catch (e) {{}}
}})();
</script>
""",
        height=0,
        width=0,
    )


def render_reminder_alarm_fragment(supabase: Client | None, user_id: str) -> None:
    """Reexecuta em intervalo fixo para avisos T-10 / a cada 5 min até T."""
    if not supabase or not user_id:
        return

    @st.fragment(run_every=datetime.timedelta(seconds=40))
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
                body = f"**Primeiro aviso (10 min antes):** {announce}\n\nHora do compromisso: **{when_local}**."
                try_speech_reminder(announce, f"{rid}-first")
            elif tag == "final":
                body = f"**Hora marcada:** {title}\n\n({when_local})"
                try_speech_reminder(f"Hora do compromisso: {title}", f"{rid}-final")
            else:
                body = f"**Lembrete:** {title}\n\nFaltam poucos minutos para **{when_local}**."
                try_speech_reminder(f"Lembrete: {title}. Em breve às {when_local}.", f"{rid}-mid")
            st.warning(body)
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("Desligar lembrete", key=f"dr_{rid}_{safe_a}"):
                    dismiss_reminder(supabase, user_id, rid)
                    st.rerun()
            with c2:
                if st.button("Adiar 5 min", key=f"sn_{rid}_{safe_a}"):
                    snooze_reminder_minutes(supabase, user_id, rid, 5)
                    st.rerun()
            with c3:
                if st.button("Ouvir de novo", key=f"rp_{rid}_{safe_a}"):
                    try_speech_reminder(announce if tag == "first" else title, f"{rid}-replay")

    _tick()


def render_agenda_reminders_page(supabase: Client | None, user_id: str) -> None:
    st.title("Agenda e lembretes")
    st.caption(
        "O avatar pode criar lembretes pelo **chat** (ele adiciona um código no fim da resposta) "
        "ou você cadastra aqui. Avisos: **10 minutos antes** (falado, se o navegador permitir) e **a cada 5 minutos** até a hora."
    )
    if not user_id:
        st.error("Sessão inválida.")
        return
    upcoming = list_upcoming_reminders(supabase, user_id, hours_back=0, hours_ahead=168)
    with st.form("nova_meta", clear_on_submit=True):
        st.subheader("Novo lembrete")
        tit = st.text_input("Título", placeholder="Ligar para …")
        d_col, h_col = st.columns(2)
        with d_col:
            d_val = st.date_input("Data do compromisso", value=datetime.date.today())
        with h_col:
            t_val = st.time_input("Hora do compromisso", value=datetime.time(9, 0))
        ann = st.text_input(
            "O que falar no primeiro aviso (10 min antes)",
            placeholder="Ligar para minha esposa às 15 horas",
        )
        sub = st.form_submit_button("Salvar lembrete")
        if sub:
            if not tit.strip():
                st.error("Preencha o título.")
            else:
                local_tz = datetime.datetime.now().astimezone().tzinfo or datetime.timezone.utc
                dt = datetime.datetime.combine(d_val, t_val).replace(tzinfo=local_tz)
                dt = dt.astimezone(datetime.timezone.utc)
                if insert_reminder_row(
                    supabase,
                    user_id,
                    title=tit.strip(),
                    scheduled_at=dt,
                    announce=ann.strip() or tit.strip(),
                ):
                    st.success("Lembrete salvo.")
                    st.rerun()
                st.error(
                    "Não foi possível salvar. Crie a tabela `reminders` no Supabase "
                    "(arquivo reminders.sql na pasta do projeto)."
                )
    st.subheader("Próximos lembretes")
    if not upcoming:
        st.info("Nenhum lembrete futuro. Peça no chat: “me lembre de … às …”.")
        return
    for r in upcoming[:40]:
        sid = str(r.get("id"))
        st.write(
            f"**{r.get('title', '')}** — {r.get('scheduled_at', '')} "
            f"{'(adiado até ' + str(r.get('snooze_until')) + ')' if r.get('snooze_until') else ''}"
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Desligar", key=f"agd_d_{sid}"):
                dismiss_reminder(supabase, user_id, sid)
                st.rerun()
        with c2:
            if st.button("Adiar 5 min", key=f"agd_s_{sid}"):
                snooze_reminder_minutes(supabase, user_id, sid, 5)
                st.rerun()


def _secret_any(name: str) -> str:
    raw = (os.getenv(name) or "").strip()
    if raw:
        return raw
    if hasattr(st, "secrets"):
        try:
            return str(st.secrets.get(name, "") or "").strip()
        except Exception:
            return ""
    return ""


def google_calendar_oauth_credentials() -> tuple[str, str, str] | None:
    """(client_id, client_secret, redirect_uri) ou None se incompleto."""
    cid = _secret_any("GOOGLE_OAUTH_CLIENT_ID")
    csec = _secret_any("GOOGLE_OAUTH_CLIENT_SECRET")
    redir = _secret_any("GOOGLE_OAUTH_REDIRECT_URI")
    if not cid or not csec or not redir:
        return None
    return cid, csec, redir


def build_google_calendar_authorize_url(client_id: str, redirect_uri: str, state: str) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": GOOGLE_CALENDAR_READONLY_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }
    return f"{GOOGLE_OAUTH_AUTH_URL}?{urlencode(params)}"


def register_google_oauth_pending(supabase: Client | None, user_id: str, state: str) -> bool:
    if not supabase or not user_id or not state:
        return False
    try:
        supabase.table(SUPABASE_GOOGLE_OAUTH_PENDING_TABLE).delete().eq(
            "user_id", user_id
        ).execute()
    except Exception:
        pass
    try:
        supabase.table(SUPABASE_GOOGLE_OAUTH_PENDING_TABLE).insert(
            {"state": state, "user_id": user_id}
        ).execute()
        return True
    except Exception:
        return False


def google_oauth_pending_exists(
    supabase: Client | None, user_id: str, state: str
) -> bool:
    if not supabase or not user_id or not state:
        return False
    try:
        res = (
            supabase.table(SUPABASE_GOOGLE_OAUTH_PENDING_TABLE)
            .select("state")
            .eq("user_id", user_id)
            .eq("state", state)
            .execute()
        )
        return bool(res.data)
    except Exception:
        return False


def delete_google_oauth_pending(supabase: Client | None, user_id: str, state: str) -> None:
    if not supabase or not user_id or not state:
        return
    try:
        supabase.table(SUPABASE_GOOGLE_OAUTH_PENDING_TABLE).delete().eq(
            "user_id", user_id
        ).eq("state", state).execute()
    except Exception:
        pass


def exchange_google_oauth_code(
    code: str, client_id: str, client_secret: str, redirect_uri: str
) -> dict:
    r = requests.post(
        GOOGLE_OAUTH_TOKEN_URL,
        data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def google_refresh_access_token(
    refresh_token: str, client_id: str, client_secret: str
) -> str | None:
    try:
        r = requests.post(
            GOOGLE_OAUTH_TOKEN_URL,
            data={
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "refresh_token",
            },
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        tok = data.get("access_token")
        return str(tok) if tok else None
    except Exception:
        return None


def save_google_calendar_refresh_token(
    supabase: Client | None, user_id: str, refresh_token: str
) -> bool:
    if not supabase or not user_id or not refresh_token:
        return False
    try:
        supabase.table(SUPABASE_GOOGLE_CALENDAR_TOKENS_TABLE).upsert(
            {
                "user_id": user_id,
                "refresh_token": refresh_token,
                "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
        ).execute()
        return True
    except Exception:
        return False


def load_google_calendar_refresh_token(supabase: Client | None, user_id: str) -> str | None:
    if not supabase or not user_id:
        return None
    try:
        res = (
            supabase.table(SUPABASE_GOOGLE_CALENDAR_TOKENS_TABLE)
            .select("refresh_token")
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        tok = (res.data or {}).get("refresh_token")
        return str(tok).strip() if tok else None
    except Exception:
        return None


def disconnect_google_calendar(supabase: Client | None, user_id: str) -> None:
    if not supabase or not user_id:
        return
    try:
        supabase.table(SUPABASE_GOOGLE_CALENDAR_TOKENS_TABLE).delete().eq(
            "user_id", user_id
        ).execute()
    except Exception:
        pass


def parse_google_calendar_event_start(ev: dict) -> datetime.datetime | None:
    start = ev.get("start") or {}
    if start.get("dateTime"):
        return _parse_ts_iso(start["dateTime"])
    if start.get("date"):
        try:
            d = datetime.date.fromisoformat(str(start["date"]))
            return datetime.datetime.combine(
                d, datetime.time(9, 0), tzinfo=datetime.timezone.utc
            )
        except ValueError:
            return None
    return None


def fetch_google_calendar_events(
    access_token: str,
    *,
    time_min: datetime.datetime,
    time_max: datetime.datetime,
    max_results: int = 25,
) -> list[dict]:
    params = {
        "singleEvents": "true",
        "orderBy": "startTime",
        "maxResults": str(max_results),
        "timeMin": time_min.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "timeMax": time_max.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    url = f"{GOOGLE_CALENDAR_EVENTS_URL}?{urlencode(params)}"
    try:
        r = requests.get(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        return list(data.get("items") or [])
    except Exception:
        return []


def _query_param_first(key: str) -> str | None:
    try:
        qp = st.query_params
        if key not in qp:
            return None
        v = qp[key]
        if isinstance(v, (list, tuple)):
            return str(v[0]) if v else None
        return str(v) if v is not None else None
    except Exception:
        return None


def maybe_finish_google_oauth_callback(supabase: Client | None, user_id: str) -> None:
    """Se a URL tiver ?code=&state= do Google, troca o código e grava refresh_token."""
    if not supabase or not user_id:
        return
    code = _query_param_first("code")
    state = _query_param_first("state")
    if not code or not state:
        return
    cred = google_calendar_oauth_credentials()
    if not cred:
        return
    client_id, client_secret, redirect_uri = cred
    if not google_oauth_pending_exists(supabase, user_id, str(state)):
        st.error("Estado OAuth inválido ou expirado. Gere o link de novo em Conexões.")
        try:
            st.query_params.clear()
        except Exception:
            pass
        return
    try:
        tokens = exchange_google_oauth_code(
            str(code), client_id, client_secret, redirect_uri
        )
        refresh = tokens.get("refresh_token")
        if not refresh:
            st.warning(
                "Google não devolveu refresh_token (pode acontecer se a conta já autorizou antes). "
                "Revogue o acesso em myaccount.google.com/permissions e conecte de novo."
            )
        else:
            save_google_calendar_refresh_token(supabase, user_id, str(refresh))
            st.success("Google Calendar conectado. Os avisos sonoros seguem os lembretes do EGO.")
    except Exception as e:  # noqa: BLE001
        st.error(f"Falha ao conectar Google: {e}")
    finally:
        delete_google_oauth_pending(supabase, user_id, str(state))
    try:
        st.query_params.clear()
    except Exception:
        pass


def import_google_events_as_reminders(
    supabase: Client | None, user_id: str, days: int = 7
) -> tuple[int, str]:
    """Importa eventos do calendário principal para a tabela reminders (avisos T-10 / 5 em 5)."""
    if not supabase or not user_id:
        return 0, "Sessão inválida."
    cred = google_calendar_oauth_credentials()
    if not cred:
        return 0, "Configure GOOGLE_OAUTH_* nos secrets."
    client_id, client_secret, _redirect_uri = cred
    refresh = load_google_calendar_refresh_token(supabase, user_id)
    if not refresh:
        return 0, "Conecte o Google Calendar antes."
    access = google_refresh_access_token(refresh, client_id, client_secret)
    if not access:
        return 0, "Não foi possível renovar o token. Conecte de novo."
    now = datetime.datetime.now(datetime.timezone.utc)
    tmax = now + datetime.timedelta(days=days)
    events = fetch_google_calendar_events(access, time_min=now, time_max=tmax, max_results=40)
    n = 0
    for ev in events:
        eid = str(ev.get("id") or "")
        title = (ev.get("summary") or "Evento no calendário").strip()[:500]
        st_dt = parse_google_calendar_event_start(ev)
        if not st_dt or st_dt < now:
            continue
        ann = f"Lembrete do calendário: {title}"
        if insert_reminder_row(
            supabase,
            user_id,
            title=title,
            scheduled_at=st_dt,
            announce=ann,
            google_event_id=eid or None,
        ):
            n += 1
    return n, ""


def render_google_calendar_section(supabase: Client | None, user_id: str) -> None:
    st.subheader("Google Calendar (OAuth)")
    cred = google_calendar_oauth_credentials()
    if not cred:
        st.warning(
            "Para conectar, crie credenciais **OAuth 2.0 (Web)** no Google Cloud Console, "
            "ative a API **Google Calendar**, e adicione ao `secrets.toml`:\n\n"
            "`GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI` "
            "(a URI de redirecionamento deve ser **igual** à URL pública do app, ex.: `https://seu-app.streamlit.app/`)."
        )
        return
    client_id, _client_secret, redirect_uri = cred
    connected = bool(load_google_calendar_refresh_token(supabase, user_id))
    if connected:
        st.success("Calendário conectado. Use **Importar** para gerar lembretes com avisos sonoros.")
        if st.button("Desconectar Google Calendar", key="gcal_disc"):
            disconnect_google_calendar(supabase, user_id)
            st.rerun()
        if st.button("Importar próximos 7 dias para lembretes do EGO", key="gcal_imp"):
            n, err = import_google_events_as_reminders(supabase, user_id, days=7)
            if err:
                st.error(err)
            elif n == 0:
                st.info("Nenhum evento futuro encontrado (ou já importados).")
            else:
                st.success(f"{n} evento(s) viraram lembretes com alarme.")
        return

    st.caption(
        "Escopo: **somente leitura** do calendário (`calendar.readonly`). "
        "O EGO não altera eventos no Google; só lê e cria lembretes locais com aviso."
    )
    if st.button("Gerar link seguro para autorizar o Google", key="gcal_start"):
        st_val = secrets.token_urlsafe(32)
        if register_google_oauth_pending(supabase, user_id, st_val):
            st.session_state["_gcal_oauth_state_ready"] = st_val
        else:
            st.error(
                "Não foi possível registrar o fluxo OAuth. Rode o SQL `google_calendar_oauth.sql` no Supabase."
            )
    st_val = st.session_state.get("_gcal_oauth_state_ready")
    if st_val:
        auth_url = build_google_calendar_authorize_url(client_id, redirect_uri, st_val)
        st.link_button("Abrir Google e autorizar calendário", auth_url, use_container_width=True)


def render_connections_page(supabase: Client | None, user_id: str) -> None:
    st.title("Conexões — calendário, música e outros apps")
    st.markdown(
        """
O avatar **não tem acesso genérico a “todos os aplicativos”** da pessoa. Cada serviço (Google, Spotify, WhatsApp, CRM…)
exige **login separado (OAuth)** e **permissões explícitas** que você aprova. Isso é o que torna o uso legal e seguro.

- **Google Calendar (abaixo):** já preparado para OAuth + importar eventos como **lembretes com avisos sonoros** (mesma lógica T−10 / 5 em 5 min).
- **Spotify / “tocar uma música”:** é possível numa **fase seguinte**, com **Spotify OAuth** e a API Web (ex.: colocar na fila / iniciar reprodução num **dispositivo já ativo**). Limitações típicas: conta **Premium** para alguns fluxos no web player, e o utilizador precisa de ter o Spotify aberto num aparelho.
- **E-mail, redes, CRM:** cada um com OAuth próprio e revisão de privacidade.
        """
    )
    render_google_calendar_section(supabase, user_id)
    st.divider()
    st.subheader("Spotify e outros (próximas fases)")
    st.info(
        "Pedir “põe esta música no Spotify” implica integrar a **Web API do Spotify** (pesquisa + fila + play). "
        "O avatar só consegue isso **depois** de o utilizador autorizar o Spotify e, em muitos casos, com o leitor "
        "ou telemóvel já ligado. Não substitui o acesso total ao telemóvel."
    )


PAIS_CADASTRO = [
    "Brasil",
    "Portugal",
    "Argentina",
    "México",
    "Colômbia",
    "Chile",
    "Peru",
    "Uruguai",
    "Paraguai",
    "Estados Unidos",
    "Canadá",
    "Reino Unido",
    "Alemanha",
    "França",
    "Espanha",
    "Itália",
    "Outros",
]

DOC_INSTRUCOES_PAIS: dict[str, str] = {
    "Brasil": "Envie documento **com foto** (CNH, RG físico ou e-RG com QR legível). Na segunda foto, **você ao lado do documento aberto** (rosto visível).",
    "Portugal": "Cartão de cidadão (CC) ou título/residência com **foto**. Segunda imagem: **selfie com o documento**.",
    "Argentina": "DNI com **foto** vigente. Segunda imagem: **selfie segurando o DNI**.",
    "México": "INE/IFE ou pasaporte con **foto**. Segunda imagen: **selfie con el documento**.",
    "Colômbia": "Cédula de ciudadanía con **foto**. Segunda imagen: **selfie con la cédula**.",
    "Chile": "Cédula de identidad con **foto**. Segunda imagen: **selfie con la cédula**.",
    "Peru": "DNI/electoral con **foto**. Segunda imagen: **selfie con el documento**.",
    "Uruguai": "Cédula de identidad con **foto**. Segunda imagen: **selfie con la cédula**.",
    "Paraguai": "Cédula con **foto**. Segunda imagen: **selfie con el documento**.",
    "Estados Unidos": "State ID ou passport com **foto**. Second image: **selfie holding the ID open**.",
    "Canadá": "Driver's license ou passport com **foto**. Second image: **selfie with document**.",
    "Reino Unido": "Passport ou driving licence com **foto**. Second image: **selfie with document**.",
    "Alemanha": "Personalausweis ou Reisepass mit **Foto**. Zweites Bild: **Selfie mit Dokument**.",
    "França": "Carte d’identité ou passeport avec **photo**. Deuxième image: **selfie avec le document**.",
    "Espanha": "DNI o pasaporte con **foto**. Segunda imagen: **selfie con el documento**.",
    "Itália": "Carta d’identità o passaporto con **foto**. Seconda immagine: **selfie con il documento**.",
    "Outros": "Documento nacional **com foto** válido. Segunda imagem: **selfie com o documento aberto**.",
}


def login_usuario(supabase: Client) -> None:
    """Tela de entrada/cadastro com Supabase Auth + upload de documento no Storage."""
    if st.session_state.get("ego_login_policies"):
        render_sidebar_support_and_version()
        render_policies_page(for_public_login=True)
        render_trust_footer(authenticated=False)
        return
    render_sidebar_support_and_version()
    render_public_trust_landing()
    st.markdown("## Acesso à sua conta")
    st.caption("Entre ou cadastre-se — autenticação segura via Supabase.")
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
            col1, col2 = st.columns(2)
            with col1:
                nome = st.text_input("Nome completo (como no documento)")
                email = st.text_input("E-mail")
                pais = st.selectbox("País / país de emissão do documento", PAIS_CADASTRO)
            with col2:
                senha = st.text_input("Senha", type="password")
                doc_tipo = st.text_input(
                    "Tipo e número do documento (ex.: RG 12.345.678-9, DNI, passport …)"
                )
            st.markdown(DOC_INSTRUCOES_PAIS.get(pais, DOC_INSTRUCOES_PAIS["Outros"]))
            doc_frente = st.file_uploader(
                "1) Documento com foto (frente legível)",
                type=["jpg", "jpeg", "png", "pdf"],
                key="cad_doc_frente",
            )
            doc_selfie = st.file_uploader(
                "2) Selfie sua segurando o mesmo documento aberto (rosto visível)",
                type=["jpg", "jpeg", "png", "pdf"],
                key="cad_doc_selfie",
            )

            if st.form_submit_button("Finalizar Cadastro Global", use_container_width=True):
                if not (
                    nome.strip()
                    and email.strip()
                    and senha.strip()
                    and doc_tipo.strip()
                    and doc_frente
                    and doc_selfie
                ):
                    st.error(
                        "Preencha nome, e-mail, senha, tipo/número do documento e as **duas** imagens obrigatórias."
                    )
                else:
                    try:
                        res = supabase.auth.sign_up({"email": email, "password": senha})
                        user = getattr(res, "user", None)
                        if not user:
                            st.warning("Conta criada. Verifique o e-mail para confirmar.")
                        else:
                            user_id = user.id
                            salvar_perfil_seguro(
                                supabase,
                                user_id=user_id,
                                full_name=nome.strip(),
                                email=email.strip(),
                                country=pais,
                                document_type=doc_tipo.strip(),
                            )
                            bucket = supabase.storage.from_(SUPABASE_STORAGE_BUCKET)
                            for label, up in (
                                ("documento_frente", doc_frente),
                                ("documento_selfie", doc_selfie),
                            ):
                                ext = (
                                    up.name.split(".")[-1].lower() if "." in up.name else "bin"
                                )
                                path = f"{user_id}/{label}.{ext}"
                                bucket.upload(path, up.getvalue(), {"upsert": "true"})
                            st.success("Conta criada! Verifique seu e-mail.")
                    except Exception as e:  # noqa: BLE001
                        st.error(f"Falha no cadastro: {e}")

    with aba1:
        with st.form("login_supabase", border=True):
            email_login = st.text_input("E-mail", key="login_email")
            senha_login = st.text_input("Senha", type="password", key="login_senha")
            if st.form_submit_button("Entrar", use_container_width=True):
                if not email_login.strip() or not senha_login.strip():
                    st.error("Informe e-mail e senha.")
                else:
                    try:
                        res = supabase.auth.sign_in_with_password(
                            {"email": email_login, "password": senha_login}
                        )
                        user = getattr(res, "user", None)
                        if not user:
                            st.error("Não foi possível autenticar. Verifique suas credenciais.")
                        else:
                            st.session_state.user_logged = True
                            st.session_state.user = user
                            st.session_state.auth_user_id = user.id
                            st.session_state.global_user_name = (
                                email_login.split("@")[0] or "Usuário Global"
                            )
                            st.session_state.history_loaded = False
                            st.success("Login realizado com sucesso.")
                            st.rerun()
                    except Exception as e:  # noqa: BLE001
                        st.error(f"Falha no login: {e}")
    render_trust_footer(authenticated=False)


def get_pdf_text(pdf_files: list) -> str:
    """Extrai texto de uma lista de arquivos PDF (objetos UploadedFile do Streamlit)."""
    if not PdfReader:
        return ""
    text_parts: list[str] = []
    for pdf in pdf_files:
        try:
            raw = pdf.getvalue() if hasattr(pdf, "getvalue") else pdf.read()
            reader = PdfReader(BytesIO(raw))
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
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
    wa_url = ego_whatsapp_business_url()
    if wa_url:
        st.sidebar.link_button(
            "WhatsApp Business",
            wa_url,
            use_container_width=True,
            help="Abre o chat oficial no WhatsApp.",
        )
    else:
        st.sidebar.caption("Configure `EGO_SUPPORT_WHATSAPP` ou `EGO_WHATSAPP_URL` nos secrets.")
    em_raw = ego_support_email()
    st.sidebar.link_button(
        "Enviar e-mail",
        f"mailto:{quote(em_raw, safe='@')}?subject={quote('Suporte EGO-AI')}",
        use_container_width=True,
    )
    st.sidebar.divider()


def sidebar_settings() -> None:
    render_sidebar_support_and_version()
    st.sidebar.markdown("### Configurações")
    st.sidebar.caption("As chaves ficam só nesta sessão do navegador; não são salvas em disco.")
    if st.session_state.get("user_logged"):
        who = st.session_state.get("global_user_name") or "Usuário Global"
        st.sidebar.success(f"Conectado como: {who}")
        user_obj = st.session_state.get("user")
        if user_obj and getattr(user_obj, "email", None):
            st.sidebar.caption(f"Conta: {user_obj.email}")
        st.sidebar.radio(
            "Navegação",
            [
                "Chat",
                "Políticas",
                "Agenda e lembretes",
                "Conexões (e-mail, redes, CRM)",
                "Meu Perfil",
                "Meu Avatar",
                "Comida Perto",
                "Bares e restaurantes",
                "Bebidas Perto",
                "Compras online",
                "Viagens e hospedagem",
            ],
            key="ego_nav",
        )
        if st.sidebar.button("Sair", use_container_width=True):
            supabase = get_supabase_client()
            if supabase:
                try:
                    supabase.auth.sign_out()
                except Exception:
                    pass
            st.session_state.user_logged = False
            st.session_state.user = None
            st.session_state.auth_user_id = ""
            st.session_state.messages = []
            st.session_state.history_loaded = False
            st.rerun()
        st.sidebar.divider()
    st.sidebar.radio(
        "Provedor de IA",
        ["Gemini", "OpenAI"],
        horizontal=True,
        key="ego_ai_provider",
    )
    provider = st.session_state.ego_ai_provider

    gemini_key = ""
    openai_key = ""
    if provider == "Gemini":
        gemini_key = st.sidebar.text_input(
            "Chave da API do Gemini",
            type="password",
            placeholder="Cole sua chave aqui",
            help="Gere a chave no Google AI Studio.",
            key="gemini_api_key_input",
        )
    else:
        openai_key = st.sidebar.text_input(
            "Chave da API da OpenAI",
            type="password",
            placeholder="sk-…",
            help="Ou use a variável de ambiente OPENAI_API_KEY nesta máquina.",
            key="openai_api_key_input",
        )
        st.sidebar.text_input(
            "Modelo OpenAI",
            help="Ex.: gpt-4o, gpt-4o-mini.",
            key="openai_model_input",
        )

    name = st.sidebar.text_input(
        "Como podemos te chamar?",
        placeholder="Seu nome",
        key="display_name_input",
    )
    if name:
        st.session_state.user_name = name.strip()
    st.sidebar.divider()
    st.sidebar.markdown("### Documentos do EGO")
    uploaded_files = st.sidebar.file_uploader(
        "Envie PDFs para análise no chat",
        type=["pdf"],
        accept_multiple_files=True,
        key="ego_pdf_uploader",
    )
    if st.sidebar.button("Processar documentos", use_container_width=True):
        if not PdfReader:
            st.sidebar.error("Instale o pacote PyPDF2 (veja requirements.txt).")
        elif uploaded_files:
            with st.spinner("O Ego-AI está lendo os PDFs…"):
                raw_text = get_pdf_text(list(uploaded_files))
                st.session_state.pdf_context = raw_text
            n_chars = len(st.session_state.pdf_context)
            st.sidebar.success(f"Conhecimento absorvido! ({n_chars:,} caracteres)")
        else:
            st.sidebar.warning("Selecione pelo menos um PDF.")

    if st.sidebar.button("Limpar documentos carregados", use_container_width=True):
        st.session_state.pdf_context = ""
        st.rerun()

    if st.sidebar.button("Limpar histórico do chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.session_state._ego_gemini_key = gemini_key or ""
    st.session_state._ego_openai_key = openai_key or ""


def render_profile(supabase: Client | None, user_id: str) -> None:
    st.title("Meu Perfil EGO-AI")
    perfil = carregar_perfil_usuario(supabase, user_id)
    if not perfil:
        st.warning("Não foi possível carregar seu perfil no momento.")
        return

    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**Nome:** {perfil.get('full_name', '-')}")
        st.info(f"**E-mail:** {perfil.get('email', '-')}")
    with col2:
        st.info(f"**País:** {perfil.get('country', '-')}")
        st.info(f"**Documento:** {perfil.get('document_type', '-')}")

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
    _, status = verificar_acesso(supabase, user_id)
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


def render_food_page(supabase: Client | None, user_id: str) -> None:
    st.title("Comida Perto de Você")
    st.caption("Busque opções de comida perto da sua região e guarde preferências para sugestões futuras.")
    perfil = carregar_perfil_usuario(supabase, user_id) or {}
    default_country = perfil.get("country", "")

    c1, c2 = st.columns(2)
    with c1:
        city = st.text_input("Cidade", value=st.session_state.get("food_city", ""))
    with c2:
        country = st.text_input(
            "País",
            value=st.session_state.get("food_country", "") or default_country,
        )
    query = st.text_input("O que você quer comer hoje?", placeholder="Ex.: sushi, pizza, hambúrguer")
    tier_default = st.session_state.get("food_price_tier", "Padrão")
    tier_index = FOOD_PRICE_TIERS.index(tier_default) if tier_default in FOOD_PRICE_TIERS else 1
    price_tier = st.selectbox(
        "Faixa de preço (refina a busca)",
        FOOD_PRICE_TIERS,
        index=tier_index,
        help="Economia prioriza opções casuais/baratas; Premium prioriza experiências mais sofisticadas.",
    )
    st.session_state.food_price_tier = price_tier

    if st.button("Buscar opções", use_container_width=True):
        st.session_state.food_city = city
        st.session_state.food_country = country
        options = search_food_nearby(query, city, country, price_tier)
        if not options:
            st.warning("Não encontrei opções agora. Tente refinar cidade/país/comida.")
        else:
            item = {
                "query": query.strip(),
                "city": city.strip(),
                "country": country.strip(),
                "price_tier": price_tier,
                "options": options,
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
            history = st.session_state.get("food_history") or []
            st.session_state.food_history = [item, *history][:20]
            save_food_event(
                supabase,
                user_id,
                item["query"],
                item["city"],
                item["country"],
                options,
                price_tier=price_tier,
            )
            st.success("Opções encontradas! Distância é aproximada (linha reta a partir do centro da cidade).")

    latest = (st.session_state.get("food_history") or [])
    if latest:
        st.markdown("### Opções recentes")
        for entry in latest[:3]:
            tier_lbl = entry.get("price_tier", "")
            extra = f" · {tier_lbl}" if tier_lbl else ""
            st.write(f"**Busca:** {entry.get('query', '-')}{extra}")
            for opt in entry.get("options", [])[:5]:
                st.link_button(format_food_option_label(opt), opt.get("link", "#"))


def render_nightlife_page(supabase: Client | None, user_id: str) -> None:
    st.title("Bares, pubs e restaurantes")
    st.caption(
        "Busque no mapa por tipo de lugar (bar, pub, restaurante, rodízio, etc.) — mesma lógica de "
        "distância e faixa de preço da Comida Perto e Bebidas Perto."
    )
    perfil = carregar_perfil_usuario(supabase, user_id) or {}
    default_country = perfil.get("country", "")

    c1, c2 = st.columns(2)
    with c1:
        city = st.text_input(
            "Cidade",
            value=st.session_state.get("food_city", ""),
            key="nightlife_input_city",
        )
    with c2:
        country = st.text_input(
            "País",
            value=st.session_state.get("food_country", "") or default_country,
            key="nightlife_input_country",
        )
    vc_default = st.session_state.get("nightlife_venue_choice", NIGHTLIFE_VENUE_LABELS[0])
    vc_index = (
        NIGHTLIFE_VENUE_LABELS.index(vc_default) if vc_default in NIGHTLIFE_VENUE_LABELS else 0
    )
    venue_category = st.selectbox(
        "Tipo de lugar",
        NIGHTLIFE_VENUE_LABELS,
        index=vc_index,
        help="Cada opção adiciona termos na busca (bar, pub, restaurante, rodízio…). Em «Outro», descreva.",
    )
    st.session_state.nightlife_venue_choice = venue_category
    query = st.text_input(
        "Refinar (opcional, exceto em «Outro»)",
        placeholder="Ex.: ao ar livre, música ao vivo, pet friendly, jantar romântico",
        key="nightlife_query_input",
    )
    tier_default = st.session_state.get("nightlife_price_tier", st.session_state.get("food_price_tier", "Padrão"))
    tier_index = FOOD_PRICE_TIERS.index(tier_default) if tier_default in FOOD_PRICE_TIERS else 1
    price_tier = st.selectbox(
        "Faixa de preço (refina a busca)",
        FOOD_PRICE_TIERS,
        index=tier_index,
        key="nightlife_price_tier_select",
        help="Economia: boteco, happy hour; Premium: carta de vinhos, rooftop, alta gastronomia.",
    )
    st.session_state.nightlife_price_tier = price_tier

    if st.button("Buscar no mapa", use_container_width=True, key="nightlife_search_btn"):
        st.session_state.food_city = city
        st.session_state.food_country = country
        options = search_nightlife_nearby(query, city, country, price_tier, venue_category)
        if not options:
            st.warning(
                "Não encontrei opções agora. Em «Outro» descreva o estilo de lugar; nos demais tipos refine ou use só a categoria."
            )
        else:
            item = {
                "query": query.strip(),
                "venue_category": venue_category,
                "city": city.strip(),
                "country": country.strip(),
                "price_tier": price_tier,
                "options": options,
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
            history = st.session_state.get("nightlife_history") or []
            st.session_state.nightlife_history = [item, *history][:25]
            save_nightlife_event(
                supabase,
                user_id,
                item["query"],
                item["city"],
                item["country"],
                options,
                price_tier=price_tier,
                venue_category=venue_category,
            )
            st.success("Opções encontradas! Distância é aproximada (linha reta a partir do centro da cidade).")

    latest = st.session_state.get("nightlife_history") or []
    if latest:
        st.markdown("### Opções recentes")
        for entry in latest[:3]:
            cat = entry.get("venue_category", "")
            qtxt = entry.get("query", "")
            head = f"{cat}" + (f" — {qtxt}" if qtxt else "")
            tier_lbl = entry.get("price_tier", "")
            extra = f" · {tier_lbl}" if tier_lbl else ""
            st.write(f"**Busca:** {head}{extra}")
            for opt in entry.get("options", [])[:5]:
                st.link_button(format_food_option_label(opt), opt.get("link", "#"))


def render_drink_page(supabase: Client | None, user_id: str) -> None:
    st.title("Bebidas Perto de Você")
    st.caption(
        "Café, chá, sucos, cerveja, vinho, coquetéis e mais — mesma faixa de preço, distância aproximada e histórico para o assistente."
    )
    perfil = carregar_perfil_usuario(supabase, user_id) or {}
    default_country = perfil.get("country", "")

    c1, c2 = st.columns(2)
    with c1:
        city = st.text_input(
            "Cidade",
            value=st.session_state.get("food_city", ""),
            key="drink_input_city",
        )
    with c2:
        country = st.text_input(
            "País",
            value=st.session_state.get("food_country", "") or default_country,
            key="drink_input_country",
        )
    dc_default = st.session_state.get("drink_category_choice", DRINK_CATEGORIES[0])
    dc_index = DRINK_CATEGORIES.index(dc_default) if dc_default in DRINK_CATEGORIES else 0
    drink_category = st.selectbox(
        "Tipo de bebida / estabelecimento",
        DRINK_CATEGORIES,
        index=dc_index,
        help="Cada opção adiciona termos de busca (café, chá, bar, etc.). Em «Outro», descreva livremente.",
    )
    st.session_state.drink_category_choice = drink_category
    query = st.text_input(
        "Refinar busca (opcional, exceto em «Outro»)",
        placeholder="Ex.: gelado, artesanal, happy hour, sem álcool",
        key="drink_query_input",
    )
    tier_default = st.session_state.get("drink_price_tier", st.session_state.get("food_price_tier", "Padrão"))
    tier_index = FOOD_PRICE_TIERS.index(tier_default) if tier_default in FOOD_PRICE_TIERS else 1
    price_tier = st.selectbox(
        "Faixa de preço (refina a busca)",
        FOOD_PRICE_TIERS,
        index=tier_index,
        key="drink_price_tier_select",
        help="Economia: locais simples; Premium: cartas elaboradas, wine bar, coquetelaria.",
    )
    st.session_state.drink_price_tier = price_tier

    if st.button("Buscar bebidas", use_container_width=True, key="drink_search_btn"):
        st.session_state.food_city = city
        st.session_state.food_country = country
        options = search_drink_nearby(query, city, country, price_tier, drink_category)
        if not options:
            st.warning(
                "Não encontrei opções agora. Em «Outro» digite o que procura; nos demais tipos você pode deixar só a categoria."
            )
        else:
            item = {
                "query": query.strip(),
                "drink_category": drink_category,
                "city": city.strip(),
                "country": country.strip(),
                "price_tier": price_tier,
                "options": options,
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
            history = st.session_state.get("drink_history") or []
            st.session_state.drink_history = [item, *history][:20]
            save_drink_event(
                supabase,
                user_id,
                item["query"],
                item["city"],
                item["country"],
                options,
                price_tier=price_tier,
                drink_category=drink_category,
            )
            st.success("Opções encontradas! Distância é aproximada (linha reta a partir do centro da cidade).")

    latest = st.session_state.get("drink_history") or []
    if latest:
        st.markdown("### Opções recentes")
        for entry in latest[:3]:
            cat = entry.get("drink_category", "")
            qtxt = entry.get("query", "")
            head = f"{cat}" + (f" — {qtxt}" if qtxt else "")
            tier_lbl = entry.get("price_tier", "")
            extra = f" · {tier_lbl}" if tier_lbl else ""
            st.write(f"**Busca:** {head}{extra}")
            for opt in entry.get("options", [])[:5]:
                st.link_button(format_food_option_label(opt), opt.get("link", "#"))


def render_shopping_page(supabase: Client | None, user_id: str) -> None:
    st.title("Compras online")
    st.caption(
        "Eletrodomésticos, roupas, calçados, eletrônicos e dezenas de categorias — atalhos para "
        "Google Shopping e marketplaces (sem login no app; você abre no navegador)."
    )
    m_default = st.session_state.get("shop_market", "Brasil")
    m_index = SHOP_MARKETS.index(m_default) if m_default in SHOP_MARKETS else 0
    market = st.selectbox(
        "Região dos links",
        SHOP_MARKETS,
        index=m_index,
        help="Ajusta quais lojas aparecem primeiro (Brasil, EUA ou misto).",
    )
    st.session_state.shop_market = market

    cat_default = st.session_state.get("shop_category_choice", SHOP_CATEGORY_LABELS[0])
    cat_index = SHOP_CATEGORY_LABELS.index(cat_default) if cat_default in SHOP_CATEGORY_LABELS else 0
    shop_category = st.selectbox(
        "Categoria do produto",
        SHOP_CATEGORY_LABELS,
        index=cat_index,
    )
    st.session_state.shop_category_choice = shop_category

    query = st.text_input(
        "O que você procura?",
        placeholder="Ex.: geladeira inverse 400L, camisa social slim, tênis corrida 42",
        key="shop_query_input",
    )
    tier_default = st.session_state.get("shop_price_tier", st.session_state.get("food_price_tier", "Padrão"))
    tier_index = FOOD_PRICE_TIERS.index(tier_default) if tier_default in FOOD_PRICE_TIERS else 1
    price_tier = st.selectbox(
        "Faixa de preço (refina os termos de busca)",
        FOOD_PRICE_TIERS,
        index=tier_index,
        key="shop_price_tier_select",
        help="Economia enfatiza ofertas; Premium enfatiza linhas mais caras ou importadas.",
    )
    st.session_state.shop_price_tier = price_tier

    if st.button("Gerar atalhos de compra", use_container_width=True, key="shop_search_btn"):
        options = search_online_products(query, shop_category, price_tier, market)
        if not options:
            st.warning('Em «Outro» descreva o produto. Nas demais categorias, refine ou deixe só a categoria.')
        else:
            item = {
                "query": query.strip(),
                "shop_category": shop_category,
                "price_tier": price_tier,
                "market": market,
                "options": options,
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
            history = st.session_state.get("shopping_history") or []
            st.session_state.shopping_history = [item, *history][:30]
            save_shopping_event(
                supabase,
                user_id,
                item["query"],
                options,
                price_tier=price_tier,
                shop_category=shop_category,
                market_region=market,
            )
            st.success("Atalhos prontos. Use os botões abaixo para comparar em cada loja.")

    latest = st.session_state.get("shopping_history") or []
    if latest:
        st.markdown("### Buscas recentes")
        for entry in latest[:3]:
            cat = entry.get("shop_category", "")
            qtxt = entry.get("query", "")
            head = f"{cat}" + (f" — {qtxt}" if qtxt else "")
            mk = entry.get("market", "")
            tier_lbl = entry.get("price_tier", "")
            extra = " · ".join(x for x in [mk, tier_lbl] if x)
            st.write(f"**{head}**" + (f" ({extra})" if extra else ""))
            for opt in entry.get("options", [])[:6]:
                st.link_button(format_food_option_label(opt), opt.get("link", "#"))


def render_travel_page(supabase: Client | None, user_id: str) -> None:
    st.title("Viagens e hospedagem")
    st.caption(
        "Hotéis, pousadas, apartamentos temporários e pacotes (voo + hotel): atalhos para Google Travel, "
        "Booking, voos e buscas em agências — você fecha a reserva no site da companhia ou agência."
    )
    m_default = st.session_state.get("travel_market", "Brasil")
    m_index = SHOP_MARKETS.index(m_default) if m_default in SHOP_MARKETS else 0
    market = st.selectbox(
        "Região dos links (agências / contexto)",
        SHOP_MARKETS,
        index=m_index,
        key="travel_market_select",
        help="Inclui sugestão de busca focada em operadoras brasileiras quando for Brasil ou Global.",
    )
    st.session_state.travel_market = market

    mode_default = st.session_state.get("travel_mode_choice", TRAVEL_MODES[0])
    mode_index = TRAVEL_MODES.index(mode_default) if mode_default in TRAVEL_MODES else 0
    travel_mode = st.radio(
        "O que buscar primeiro?",
        TRAVEL_MODES,
        index=mode_index,
        horizontal=True,
        key="travel_mode_radio",
    )
    st.session_state.travel_mode_choice = travel_mode

    sub_labels = HOTEL_SUB_LABELS if travel_mode == "Hospedagem" else PKG_SUB_LABELS
    cat_default = st.session_state.get("travel_subcategory_choice", sub_labels[0])
    if cat_default not in sub_labels:
        cat_default = sub_labels[0]
    sub_index = sub_labels.index(cat_default)
    subcategory = st.selectbox(
        "Tipo de hospedagem" if travel_mode == "Hospedagem" else "Tipo de pacote / viagem",
        sub_labels,
        index=sub_index,
        key="travel_subcategory_select",
    )
    st.session_state.travel_subcategory_choice = subcategory

    destination = st.text_input(
        "Destino",
        placeholder="Ex.: Porto de Galinhas, Paris, Tóquio, Cruzeiro pelo Caribe",
        key="travel_destination_input",
    )
    origin_hint = st.text_input(
        "Origem (opcional; ajuda em pacotes e voos)",
        placeholder="Ex.: São Paulo, Brasília",
        key="travel_origin_input",
    )
    extra = st.text_input(
        "Datas, duração ou preferências (opcional)",
        placeholder="Ex.: carnaval 2026, 5 noites, aceita pet, all inclusive",
        key="travel_extra_input",
    )

    tier_default = st.session_state.get("travel_price_tier", st.session_state.get("food_price_tier", "Padrão"))
    tier_index = FOOD_PRICE_TIERS.index(tier_default) if tier_default in FOOD_PRICE_TIERS else 1
    price_tier = st.selectbox(
        "Faixa de preço / estilo (refina a busca)",
        FOOD_PRICE_TIERS,
        index=tier_index,
        key="travel_price_tier_select",
        help="Economia: hospedagem econômica e ofertas; Premium: alto padrão, resorts e experiências.",
    )
    st.session_state.travel_price_tier = price_tier

    if st.button("Gerar atalhos de viagem", use_container_width=True, key="travel_search_btn"):
        if not destination.strip():
            st.warning("Informe pelo menos o destino (cidade, região ou país).")
        else:
            options = search_travel_links(
                travel_mode,
                subcategory,
                destination,
                origin_hint,
                extra,
                price_tier,
                market,
            )
            if not options:
                st.warning("Não foi possível montar links. Verifique o destino e tente de novo.")
            else:
                item = {
                    "destination": destination.strip(),
                    "origin_hint": origin_hint.strip(),
                    "query": extra.strip(),
                    "travel_mode": travel_mode,
                    "travel_subcategory": subcategory,
                    "price_tier": price_tier,
                    "market": market,
                    "options": options,
                    "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                }
                history = st.session_state.get("travel_history") or []
                st.session_state.travel_history = [item, *history][:30]
                save_travel_event(
                    supabase,
                    user_id,
                    item["destination"],
                    item["query"],
                    options,
                    price_tier=price_tier,
                    travel_mode=travel_mode,
                    travel_subcategory=subcategory,
                    market_region=market,
                    origin_hint=item["origin_hint"],
                )
                st.success("Atalhos prontos. Confira datas e políticas direto em cada site antes de pagar.")

    latest = st.session_state.get("travel_history") or []
    if latest:
        st.markdown("### Buscas recentes")
        for entry in latest[:3]:
            st.write(f"**{_travel_entry_label(entry)}**")
            for opt in entry.get("options", [])[:7]:
                st.link_button(format_food_option_label(opt), opt.get("link", "#"))


def _api_ready() -> bool:
    if st.session_state.get("ego_ai_provider") == "OpenAI":
        return bool(st.session_state.get("_ego_openai_key"))
    return bool(st.session_state.get("_ego_gemini_key"))


def _bubble_html(role: str, content: str) -> str:
    avatar_name = next(
        (a["name"] for a in AVATAR_OPTIONS if a["id"] == st.session_state.get("assistant_avatar_id")),
        "Ego-AI",
    )
    label = "Você" if role == "user" else avatar_name
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
    name = st.session_state.get("user_name") or "você"
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
        agenda_items = list_upcoming_reminders(
            supabase, user_id, hours_back=0, hours_ahead=168
        )[:5]
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
        prov = st.session_state.get("ego_ai_provider", "Gemini")
        tip_base = (
            f"Configure a chave da API ({prov}) na barra lateral para usar o chat."
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
            <div class="ego-card-title">Sugestões rápidas — comida, bebidas, bares, compras e viagens</div>
            <p style="color:#9ca3af;font-size:0.88rem;margin:0 0 0.5rem 0;">
                Top 3 por sessão: mapa (comida, bebidas, bares/restaurantes), shopping e viagens.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    dash_food, dash_drink, dash_shop = st.columns(3)
    top_food = food_history_top_queries(3)
    with dash_food:
        st.markdown("**Comida**")
        if not top_food:
            st.caption("Use **Comida Perto**.")
        else:
            cols = st.columns(min(3, len(top_food)))
            for i, (fq, n) in enumerate(top_food):
                with cols[i]:
                    st.metric(label=fq[:28] + ("…" if len(fq) > 28 else ""), value=f"{n}×" if n > 1 else "1×")
                    st.link_button("Mapa", food_dashboard_maps_url(fq), use_container_width=True)
    top_drink = drink_history_top_queries(3)
    with dash_drink:
        st.markdown("**Bebidas**")
        if not top_drink:
            st.caption("Use **Bebidas Perto**.")
        else:
            cols = st.columns(min(3, len(top_drink)))
            for i, (dq, n) in enumerate(top_drink):
                with cols[i]:
                    short = dq[:28] + ("…" if len(dq) > 28 else "")
                    st.metric(label=short, value=f"{n}×" if n > 1 else "1×")
                    st.link_button("Mapa", food_dashboard_maps_url(dq), use_container_width=True)
    top_shop = shopping_history_top_queries(3)
    with dash_shop:
        st.markdown("**Compras online**")
        if not top_shop:
            st.caption("Use **Compras online**.")
        else:
            cols = st.columns(min(3, len(top_shop)))
            for i, (sq, n) in enumerate(top_shop):
                with cols[i]:
                    short = sq[:28] + ("…" if len(sq) > 28 else "")
                    st.metric(label=short, value=f"{n}×" if n > 1 else "1×")
                    st.link_button("Shopping", shopping_dashboard_search_url(sq), use_container_width=True)

    st.markdown(
        """
        <div class="ego-card" style="margin-top:0.85rem;">
            <div class="ego-card-title">Bares, pubs e restaurantes — top 3 da sessão</div>
            <p style="color:#9ca3af;font-size:0.88rem;margin:0 0 0.5rem 0;">
                Mesmo mapa e cidade/país usados em Comida Perto.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    top_nl = nightlife_history_top_queries(3)
    if not top_nl:
        st.caption("Use **Bares e restaurantes** na barra lateral para ver aqui seus tipos de lugar mais buscados.")
    else:
        cols_nl = st.columns(min(3, len(top_nl)))
        for i, (nq, n) in enumerate(top_nl):
            with cols_nl[i]:
                short = nq[:32] + ("…" if len(nq) > 32 else "")
                st.metric(label=short, value=f"{n}×" if n > 1 else "1×")
                st.link_button("Mapa", food_dashboard_maps_url(nq), use_container_width=True)

    st.markdown(
        """
        <div class="ego-card" style="margin-top:0.85rem;">
            <div class="ego-card-title">Viagens e hospedagem — top 3 da sessão</div>
            <p style="color:#9ca3af;font-size:0.88rem;margin:0 0 0.5rem 0;">
                Reabre uma busca semelhante na web (hotéis / pacotes).
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    top_travel = travel_history_top_queries(3)
    if not top_travel:
        st.caption("Use **Viagens e hospedagem** na barra lateral para ver aqui seus destinos mais buscados.")
    else:
        cols_t = st.columns(min(3, len(top_travel)))
        for i, (tq, n) in enumerate(top_travel):
            with cols_t[i]:
                short = tq[:32] + ("…" if len(tq) > 32 else "")
                st.metric(label=short, value=f"{n}×" if n > 1 else "1×")
                st.link_button("Buscar de novo", travel_dashboard_open_url(tq), use_container_width=True)


def _build_contexto_instrucao_pdf(pdf_context: str) -> str:
    """Como no seu exemplo: instrução + trecho limitado dos PDFs (não vai no prompt do usuário)."""
    raw = (pdf_context or "").strip()
    if not raw:
        return ""
    snippet = raw[:PDF_CONTEXT_IN_SYSTEM_CHARS]
    suffix = (
        "\n\n(Conteúdo truncado aos primeiros "
        f"{PDF_CONTEXT_IN_SYSTEM_CHARS} caracteres para limitar tokens.)"
        if len(raw) > PDF_CONTEXT_IN_SYSTEM_CHARS
        else ""
    )
    return (
        "\n\nBaseie sua resposta no seguinte conteúdo extraído de documentos:\n"
        f"{snippet}{suffix}"
    )


def _build_full_system_instruction(pdf_context: str, lang_code: str = "pt-BR") -> str:
    return (
        GEMINI_SYSTEM_INSTRUCTION
        + language_instruction(lang_code)
        + _build_contexto_instrucao_pdf(pdf_context)
        + build_food_hint()
        + reminder_instruction_block()
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


def _generate_with_model(model_name: str, full_system: str, prior_messages: list, user_text: str) -> str:
    """Uma chamada: system + histórico (chat) ou prompt único (fallback)."""
    try:
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=full_system,
        )
        legacy_prompt_merge = False
    except TypeError:
        model = genai.GenerativeModel(model_name=model_name)
        legacy_prompt_merge = True

    history = _messages_to_gemini_history(prior_messages)
    if legacy_prompt_merge:
        blob = _linearize_messages_for_fallback(prior_messages, user_text)
        prompt = f"{full_system}\n\n{blob}"
        resp = model.generate_content(prompt)
        st.session_state["gemini_model_ok"] = model_name
        return resp.text or ""

    if history:
        try:
            chat = model.start_chat(history=history)
            resp = chat.send_message(user_text)
        except Exception:  # noqa: BLE001
            blob = _linearize_messages_for_fallback(prior_messages, user_text)
            resp = model.generate_content(blob)
    else:
        resp = model.generate_content(user_text)

    st.session_state["gemini_model_ok"] = model_name
    return resp.text or ""


def run_gemini_reply(
    api_key: str,
    user_text: str,
    pdf_context: str = "",
    *,
    conversation_messages: list | None = None,
    lang_code: str = "pt-BR",
) -> str:
    """Envia ao Gemini com system (PDF até 4000 chars) + histórico das mensagens anteriores."""
    if not genai:
        return "Instale o pacote `google-generativeai` (veja requirements.txt)."
    if not api_key.strip():
        return "Adicione a **chave da API do Gemini** em **Configurações** para receber respostas."

    msgs = conversation_messages if conversation_messages is not None else []
    prior = msgs[:-1] if msgs else []

    full_system = _build_full_system_instruction(pdf_context, lang_code)

    try:
        genai.configure(api_key=api_key.strip())
        listed_supported = []
        try:
            listed_supported = [
                m.name
                for m in genai.list_models()
                if hasattr(m, "supported_generation_methods")
                and "generateContent" in m.supported_generation_methods
            ]
        except Exception:
            listed_supported = []

        preferred_variants = []
        for candidate in MODEL_CANDIDATES:
            preferred_variants.extend([candidate, f"models/{candidate}"])

        chosen_model = st.session_state.get("gemini_model_ok")
        if chosen_model and listed_supported and chosen_model not in listed_supported:
            chosen_model = None

        if not chosen_model:
            # Prioriza candidatos conhecidos; se não houver, usa o primeiro retornado pela API.
            for preferred in preferred_variants:
                if preferred in listed_supported:
                    chosen_model = preferred
                    break
            if not chosen_model and listed_supported:
                chosen_model = listed_supported[0]
            if not chosen_model:
                chosen_model = MODEL_CANDIDATES[0]
            st.session_state["gemini_model_ok"] = chosen_model

        model_try_order = [chosen_model]
        for name in [*preferred_variants, *listed_supported]:
            if name not in model_try_order:
                model_try_order.append(name)

        last_error = None
        for model_name in model_try_order:
            try:
                text = _generate_with_model(
                    model_name, full_system, prior, user_text
                )
                if text:
                    return text
                return "Não obtive texto na resposta. Tente novamente."
            except Exception as model_err:  # noqa: BLE001
                last_error = model_err
                continue

        return f"Erro ao chamar o Gemini: {last_error}"
    except Exception as e:  # noqa: BLE001
        return f"Erro ao chamar o Gemini: {e}"


def run_openai_reply(
    api_key: str,
    pdf_context: str,
    conversation_messages: list,
    model_id: str,
    *,
    temperature: float = 0.7,
    lang_code: str = "pt-BR",
) -> str:
    """OpenAI Chat Completions: system + histórico (como no seu exemplo); PDF até 5000 chars no system."""
    if not OpenAI:
        return 'Instale o pacote `openai` (veja requirements.txt ou `pip install openai`).'
    key = (api_key or "").strip()
    if not key:
        key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        key = (st.secrets.get("OPENAI_API_KEY", "") if hasattr(st, "secrets") else "").strip()
    try:
        client = OpenAI(api_key=key) if key else OpenAI()
    except Exception as e:  # noqa: BLE001
        return f"Erro ao iniciar cliente OpenAI: {e}"

    system_message = (
        "You are EGO-AI, a global assistant. "
        "IMPORTANT: detect the language of the user's message automatically. "
        "If the user writes in Portuguese, reply in Portuguese. "
        "If the user writes in English, reply in English. "
        "Always match the user's language."
    )
    system_message += language_instruction(lang_code)
    system_message += build_food_hint()
    pdf_raw = (pdf_context or "").strip()
    if pdf_raw:
        snippet = pdf_raw[:OPENAI_PDF_CONTEXT_CHARS]
        system_message += f"\n\nContexto extraído dos PDFs:\n{snippet}"
        system_message += (
            "\n\nResponda com base no contexto acima quando a pergunta for relacionada aos documentos."
        )
    system_message += reminder_instruction_block()

    openai_msgs: list[dict] = [{"role": "system", "content": system_message}]
    for m in conversation_messages:
        role = m.get("role")
        if role not in ("user", "assistant"):
            continue
        openai_msgs.append({"role": role, "content": (m.get("content") or "")})

    mid = (model_id or "").strip() or OPENAI_DEFAULT_MODEL
    try:
        response = client.chat.completions.create(
            model=mid,
            messages=openai_msgs,
            temperature=temperature,
        )
        resposta_final = response.choices[0].message.content
        out = (resposta_final or "").strip()
        return out if out else "A API não retornou texto."
    except Exception as e:  # noqa: BLE001
        return f"Erro na API OpenAI: {e}"


def render_chat(supabase: Client | None, user_id: str) -> None:
    st.markdown('<div class="ego-chat-wrap"><h3>EGO-AI Global Agent</h3></div>', unsafe_allow_html=True)
    lang = st.session_state.get("last_detected_language", "pt-BR")
    conf = float(st.session_state.get("last_detected_confidence", 0.0))
    st.caption(f"Idioma detectado: {lang} · confiança: {conf:.0%}")
    msgs = st.session_state.get("messages") or []
    if msgs:
        ex1, ex2 = st.columns(2)
        fn = f"ego_chat_{datetime.date.today().isoformat()}"
        with ex1:
            st.download_button(
                "Exportar conversa (TXT)",
                data=build_chat_export_txt(msgs),
                file_name=f"{fn}.txt",
                mime="text/plain; charset=utf-8",
                use_container_width=True,
                key="ego_export_txt",
            )
        with ex2:
            pdf_bytes = build_chat_export_pdf_bytes(msgs)
            if pdf_bytes:
                st.download_button(
                    "Exportar conversa (PDF)",
                    data=pdf_bytes,
                    file_name=f"{fn}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key="ego_export_pdf",
                )
            else:
                st.caption("Instale `reportlab` para exportar PDF.")

    try:
        with st.container(height=420, border=False):
            render_chat_messages_with_feedback(supabase, user_id)
    except TypeError:
        with st.container():
            render_chat_messages_with_feedback(supabase, user_id)

    acesso_liberado, _status = verificar_acesso(supabase, user_id)
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

    pode_enviar, total_hoje = verificar_limite_diario(supabase, user_id)
    if not pode_enviar:
        st.error("Você atingiu seu limite diário gratuito. Volte amanhã ou mude para o plano Pro.")
        st.caption(f"Uso de hoje: {total_hoje} / 20 mensagens.")
        return

    if prompt := st.chat_input(
        "Pergunte em qualquer idioma...",
    ):
        is_pro_chat = bool((carregar_perfil_usuario(supabase, user_id) or {}).get("is_pro"))
        ok_tok, msg_tok, used_tok, lim_tok = check_monthly_token_allowance(
            supabase, user_id, is_pro_chat
        )
        if not ok_tok:
            st.error(msg_tok)
            st.caption(f"Uso aproximado no mês: {used_tok:,} / {lim_tok:,} tokens.")
            return

        detected_lang, confidence = detect_user_language_with_confidence(prompt)
        st.session_state.last_detected_language = detected_lang
        st.session_state.last_detected_confidence = confidence
        mid_u: str | None = None
        if user_id and supabase:
            mid_u = salvar_mensagem_segura(supabase, user_id, "user", prompt)
        st.session_state.messages.append(
            {"role": "user", "content": prompt, "msg_id": mid_u}
        )
        pdf_ctx = st.session_state.get("pdf_context") or ""

        if st.session_state.get("ego_ai_provider") == "OpenAI":
            reply = run_openai_reply(
                st.session_state.get("_ego_openai_key") or "",
                pdf_ctx,
                st.session_state.messages,
                st.session_state.get("openai_model_input") or OPENAI_DEFAULT_MODEL,
                lang_code=detected_lang,
            )
        else:
            reply = run_gemini_reply(
                st.session_state.get("_ego_gemini_key") or "",
                prompt,
                pdf_ctx,
                conversation_messages=st.session_state.messages,
                lang_code=detected_lang,
            )
        reply_clean = process_assistant_reminders(supabase, user_id, reply)
        mid_a: str | None = None
        if user_id and supabase:
            mid_a = salvar_mensagem_segura(supabase, user_id, "assistant", reply_clean)
            tok_n = count_turn_tokens(prompt, reply_clean)
            add_monthly_tokens_to_profile(supabase, user_id, tok_n, is_pro_chat)
        st.session_state.messages.append(
            {"role": "assistant", "content": reply_clean, "msg_id": mid_a}
        )
        st.rerun()


def main() -> None:
    st.set_page_config(
        page_title="EGO-AI Global",
        page_icon="🤖",
        layout="centered",
        initial_sidebar_state="expanded",
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
        login_usuario(supabase)
        return
    # No início do bloco de usuário logado:
    if not st.session_state.get("history_loaded"):
        uid = obter_user_id_logado()
        if uid and supabase:
            st.session_state.messages = carregar_historico_do_banco(uid)
        else:
            st.session_state.messages = []
        st.session_state.history_loaded = True
    if not st.session_state.get("persona_loaded"):
        uid = obter_user_id_logado()
        avatar_id, voice_id = load_user_persona(supabase, uid)
        st.session_state.assistant_avatar_id = avatar_id
        st.session_state.assistant_voice_id = voice_id
        st.session_state.persona_loaded = True
    uid = obter_user_id_logado()
    if uid and supabase:
        maybe_finish_google_oauth_callback(supabase, uid)
    perfil_nav = carregar_perfil_usuario(supabase, uid) if uid and supabase else None
    is_pro_nav = bool((perfil_nav or {}).get("is_pro", False))
    clamp_persona_para_plano_nao_pro(supabase, uid or "", is_pro=is_pro_nav)
    sidebar_settings()
    acesso_liberado, status = verificar_acesso(supabase, uid) if uid else (False, "Expirado")
    if acesso_liberado:
        st.sidebar.success(f"Status da Conta: {status}")
    if uid and supabase:
        render_reminder_alarm_fragment(supabase, uid)
    if st.session_state.get("ego_nav") == "Políticas":
        render_policies_page(for_public_login=False)
    elif st.session_state.get("ego_nav") == "Agenda e lembretes":
        render_agenda_reminders_page(supabase, uid)
    elif st.session_state.get("ego_nav") == "Conexões (e-mail, redes, CRM)":
        render_connections_page(supabase, uid)
    elif st.session_state.get("ego_nav") == "Meu Perfil":
        render_profile(supabase, uid)
    elif st.session_state.get("ego_nav") == "Meu Avatar":
        render_avatar_page(supabase, uid)
    elif st.session_state.get("ego_nav") == "Comida Perto":
        render_food_page(supabase, uid)
    elif st.session_state.get("ego_nav") == "Bares e restaurantes":
        render_nightlife_page(supabase, uid)
    elif st.session_state.get("ego_nav") == "Bebidas Perto":
        render_drink_page(supabase, uid)
    elif st.session_state.get("ego_nav") == "Compras online":
        render_shopping_page(supabase, uid)
    elif st.session_state.get("ego_nav") == "Viagens e hospedagem":
        render_travel_page(supabase, uid)
    else:
        render_dashboard(supabase, uid)
        render_chat(supabase, uid)
    render_trust_footer(authenticated=True)


if __name__ == "__main__":
    main()
