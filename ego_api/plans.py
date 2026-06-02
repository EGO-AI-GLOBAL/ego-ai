"""Planos EGO-AI: limites por tier (Essencial, Conexão, Premium, Total, Empresa)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

PLAN_ESSENTIAL = "essential"
PLAN_CONNECTION = "connection"
PLAN_PREMIUM = "premium"
PLAN_TOTAL = "total"
PLAN_ENTERPRISE = "enterprise"

PLAN_TIERS: tuple[str, ...] = (
    PLAN_ESSENTIAL,
    PLAN_CONNECTION,
    PLAN_PREMIUM,
    PLAN_TOTAL,
    PLAN_ENTERPRISE,
)

PLAN_LABELS: dict[str, str] = {
    PLAN_ESSENTIAL: "EGO Essencial",
    PLAN_CONNECTION: "EGO Conexão",
    PLAN_PREMIUM: "EGO Premium",
    PLAN_TOTAL: "EGO Total",
    PLAN_ENTERPRISE: "EGO Empresa",
}

PLAN_PRICES_BRL: dict[str, float] = {
    PLAN_ESSENTIAL: 0.0,
    PLAN_CONNECTION: 29.90,
    PLAN_PREMIUM: 49.90,
    PLAN_TOTAL: 99.90,
    PLAN_ENTERPRISE: 199.90,
}


@dataclass(frozen=True)
class PlanLimits:
    monthly_tokens: int
    daily_text_messages: int
    daily_voice_messages: int
    daily_tts_replies: int
    max_agenda_items: int
    max_reminders: int
    audio_speed_multipliers: tuple[float, ...]
    chat_llm_max_turns: int

    def unlimited_daily_text(self) -> bool:
        return self.daily_text_messages <= 0

    def unlimited_daily_voice(self) -> bool:
        return self.daily_voice_messages <= 0

    def unlimited_daily_tts(self) -> bool:
        return self.daily_tts_replies <= 0

    def unlimited_agenda(self) -> bool:
        return self.max_agenda_items <= 0

    def unlimited_reminders(self) -> bool:
        return self.max_reminders <= 0


def _int_env(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _float_tuple_env(name: str, default: tuple[float, ...]) -> tuple[float, ...]:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    parts: list[float] = []
    for piece in raw.split(","):
        piece = piece.strip()
        if not piece:
            continue
        try:
            parts.append(float(piece))
        except ValueError:
            continue
    return tuple(parts) if parts else default


def _limits_for_tier(tier: str) -> PlanLimits:
    t = normalize_plan_tier(tier)
    defaults: dict[str, PlanLimits] = {
        PLAN_ESSENTIAL: PlanLimits(
            monthly_tokens=200_000,
            daily_text_messages=10,
            daily_voice_messages=3,
            daily_tts_replies=5,
            max_agenda_items=3,
            max_reminders=3,
            audio_speed_multipliers=(1.0,),
            chat_llm_max_turns=24,
        ),
        PLAN_CONNECTION: PlanLimits(
            monthly_tokens=800_000,
            daily_text_messages=50,
            daily_voice_messages=15,
            daily_tts_replies=0,
            max_agenda_items=20,
            max_reminders=20,
            audio_speed_multipliers=(1.0, 1.5, 2.0),
            chat_llm_max_turns=24,
        ),
        PLAN_PREMIUM: PlanLimits(
            monthly_tokens=2_500_000,
            daily_text_messages=0,
            daily_voice_messages=0,
            daily_tts_replies=0,
            max_agenda_items=0,
            max_reminders=0,
            audio_speed_multipliers=(1.0, 1.5, 2.0),
            chat_llm_max_turns=40,
        ),
        PLAN_TOTAL: PlanLimits(
            monthly_tokens=5_000_000,
            daily_text_messages=0,
            daily_voice_messages=0,
            daily_tts_replies=0,
            max_agenda_items=0,
            max_reminders=0,
            audio_speed_multipliers=(1.0, 1.5, 2.0),
            chat_llm_max_turns=40,
        ),
        PLAN_ENTERPRISE: PlanLimits(
            monthly_tokens=10_000_000,
            daily_text_messages=0,
            daily_voice_messages=0,
            daily_tts_replies=0,
            max_agenda_items=0,
            max_reminders=0,
            audio_speed_multipliers=(1.0, 1.5, 2.0, 2.5),
            chat_llm_max_turns=48,
        ),
    }
    base = defaults[t]
    prefix = t.upper()
    return PlanLimits(
        monthly_tokens=_int_env(f"EGO_{prefix}_MONTHLY_TOKENS", base.monthly_tokens),
        daily_text_messages=_int_env(
            f"EGO_{prefix}_DAILY_TEXT_MESSAGES", base.daily_text_messages
        ),
        daily_voice_messages=_int_env(
            f"EGO_{prefix}_DAILY_VOICE_MESSAGES", base.daily_voice_messages
        ),
        daily_tts_replies=_int_env(
            f"EGO_{prefix}_DAILY_TTS_REPLIES", base.daily_tts_replies
        ),
        max_agenda_items=_int_env(f"EGO_{prefix}_MAX_AGENDA", base.max_agenda_items),
        max_reminders=_int_env(f"EGO_{prefix}_MAX_REMINDERS", base.max_reminders),
        audio_speed_multipliers=_float_tuple_env(
            f"EGO_{prefix}_AUDIO_SPEEDS", base.audio_speed_multipliers
        ),
        chat_llm_max_turns=_int_env(
            f"EGO_{prefix}_CHAT_MAX_TURNS", base.chat_llm_max_turns
        ),
    )


def normalize_plan_tier(raw: str | None) -> str:
    tier = (raw or "").strip().lower()
    aliases = {
        "free": PLAN_ESSENTIAL,
        "gratis": PLAN_ESSENTIAL,
        "grátis": PLAN_ESSENTIAL,
        "essencial": PLAN_ESSENTIAL,
        "conexao": PLAN_CONNECTION,
        "conexão": PLAN_CONNECTION,
        "plus": PLAN_CONNECTION,
        "pro": PLAN_CONNECTION,
        "vip": PLAN_TOTAL,
        "total": PLAN_TOTAL,
        "empresa": PLAN_ENTERPRISE,
        "business": PLAN_ENTERPRISE,
        "enterprise": PLAN_ENTERPRISE,
        "corporate": PLAN_ENTERPRISE,
    }
    tier = aliases.get(tier, tier)
    if tier in PLAN_TIERS:
        return tier
    return PLAN_ESSENTIAL


def _test_total_emails() -> frozenset[str]:
    """E-mails com plano Total forçado (dev/teste). Env: EGO_TEST_TOTAL_EMAILS=a@x.com,b@y.com"""
    raw = (os.getenv("EGO_TEST_TOTAL_EMAILS") or "").strip()
    if not raw:
        return frozenset()
    return frozenset(
        part.strip().lower()
        for part in raw.split(",")
        if part.strip()
    )


def _profile_email(profile: dict[str, Any] | None) -> str:
    if not profile:
        return ""
    email = str(profile.get("email") or "").strip().lower()
    if email:
        return email
    try:
        from ego_api.request_ctx import get_session

        sess = get_session()
        if sess and str(sess.email or "").strip():
            return str(sess.email).strip().lower()
    except Exception:
        pass
    return ""


def is_test_total_email(email: str | None) -> bool:
    em = (email or "").strip().lower()
    return bool(em) and em in _test_total_emails()


def resolve_plan_tier(profile: dict[str, Any] | None) -> str:
    """Plano efetivo: override de teste, plan_tier no perfil, ou is_pro legado."""
    if is_test_total_email(_profile_email(profile)):
        return PLAN_TOTAL
    if not profile:
        return PLAN_ESSENTIAL
    raw = profile.get("plan_tier")
    if raw and str(raw).strip():
        return normalize_plan_tier(str(raw))
    if bool(profile.get("is_pro")):
        legacy = (os.getenv("EGO_LEGACY_IS_PRO_TIER") or PLAN_CONNECTION).strip().lower()
        return normalize_plan_tier(legacy)
    return PLAN_ESSENTIAL


def is_paid_plan(tier: str) -> bool:
    return normalize_plan_tier(tier) != PLAN_ESSENTIAL


def plan_limits(tier: str) -> PlanLimits:
    return _limits_for_tier(tier)


def plan_label(tier: str) -> str:
    return PLAN_LABELS.get(normalize_plan_tier(tier), PLAN_LABELS[PLAN_ESSENTIAL])


def stripe_price_to_tier(price_id: str) -> str | None:
    """Mapeia price_id Stripe → plan_tier via env STRIPE_PRICE_<TIER>."""
    pid = (price_id or "").strip()
    if not pid:
        return None
    for tier in (PLAN_CONNECTION, PLAN_PREMIUM, PLAN_TOTAL, PLAN_ENTERPRISE):
        env_name = f"STRIPE_PRICE_{tier.upper()}"
        if (os.getenv(env_name) or "").strip() == pid:
            return tier
    return None


def stripe_product_to_tier(product_id: str) -> str | None:
    """Mapeia product_id Stripe (prod_...) → plan_tier via STRIPE_PRODUCT_<TIER>."""
    prod = (product_id or "").strip()
    if not prod:
        return None
    for tier in (PLAN_CONNECTION, PLAN_PREMIUM, PLAN_TOTAL, PLAN_ENTERPRISE):
        env_name = f"STRIPE_PRODUCT_{tier.upper()}"
        if (os.getenv(env_name) or "").strip() == prod:
            return tier
    return None


def stripe_object_to_tier(*, price_id: str = "", product_id: str = "") -> str | None:
    return stripe_price_to_tier(price_id) or stripe_product_to_tier(product_id)


def stripe_checkout_urls() -> dict[str, str | None]:
    return {
        PLAN_CONNECTION: _clean_url(os.getenv("STRIPE_CHECKOUT_CONNECTION_URL", "")),
        PLAN_PREMIUM: _clean_url(os.getenv("STRIPE_CHECKOUT_PREMIUM_URL", "")),
        PLAN_TOTAL: _clean_url(os.getenv("STRIPE_CHECKOUT_TOTAL_URL", "")),
        PLAN_ENTERPRISE: _clean_url(os.getenv("STRIPE_CHECKOUT_ENTERPRISE_URL", "")),
        "monthly_legacy": _clean_url(os.getenv("STRIPE_CHECKOUT_MENSAL_URL", "")),
        "annual_legacy": _clean_url(os.getenv("STRIPE_CHECKOUT_ANUAL_URL", "")),
        "int_connection": _clean_url(os.getenv("STRIPE_CHECKOUT_INT_CONNECTION_URL", "")),
        "int_premium": _clean_url(os.getenv("STRIPE_CHECKOUT_INT_PREMIUM_URL", "")),
        "int_premium_annual": _clean_url(
            os.getenv("STRIPE_CHECKOUT_INT_PREMIUM_ANNUAL_URL", "")
        ),
        "int_total": _clean_url(os.getenv("STRIPE_CHECKOUT_INT_TOTAL_URL", "")),
        "int_total_annual": _clean_url(
            os.getenv("STRIPE_CHECKOUT_INT_TOTAL_ANNUAL_URL", "")
        ),
        "int_enterprise": _clean_url(os.getenv("STRIPE_CHECKOUT_INT_ENTERPRISE_URL", "")),
    }


def _clean_url(raw: str) -> str | None:
    url = (raw or "").strip()
    if not url or "COLOQUE" in url.upper() or "URL_DO" in url.upper():
        return None
    return url
