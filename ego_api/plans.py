"""Planos EGO-AI: limites por tier (Essencial, Conexão, Premium, Total, Empresa)."""

from __future__ import annotations

import datetime
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
    if not tier:
        return PLAN_ESSENTIAL
    aliases = {
        "free": PLAN_ESSENTIAL,
        "gratis": PLAN_ESSENTIAL,
        "grátis": PLAN_ESSENTIAL,
        "essencial": PLAN_ESSENTIAL,
        "ego essencial": PLAN_ESSENTIAL,
        "conexao": PLAN_CONNECTION,
        "conexão": PLAN_CONNECTION,
        "ego conexao": PLAN_CONNECTION,
        "ego conexão": PLAN_CONNECTION,
        "plus": PLAN_CONNECTION,
        "pro": PLAN_CONNECTION,
        "premium": PLAN_PREMIUM,
        "ego premium": PLAN_PREMIUM,
        "vip": PLAN_TOTAL,
        "total": PLAN_TOTAL,
        "ego total": PLAN_TOTAL,
        "plano total": PLAN_TOTAL,
        "empresa": PLAN_ENTERPRISE,
        "business": PLAN_ENTERPRISE,
        "enterprise": PLAN_ENTERPRISE,
        "corporate": PLAN_ENTERPRISE,
        "ego empresa": PLAN_ENTERPRISE,
    }
    tier = aliases.get(tier, tier)
    if tier in PLAN_TIERS:
        return tier
    # Labels vindos do Supabase/UI ("EGO Total", etc.)
    if "enterprise" in tier or "empresa" in tier:
        return PLAN_ENTERPRISE
    if "total" in tier:
        return PLAN_TOTAL
    if "premium" in tier:
        return PLAN_PREMIUM
    if "conex" in tier or "connection" in tier:
        return PLAN_CONNECTION
    if "essencial" in tier or "essential" in tier or "gratis" in tier or "grátis" in tier:
        return PLAN_ESSENTIAL
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
        tier = normalize_plan_tier(str(raw))
        if tier != PLAN_ESSENTIAL:
            return tier
    ui = profile.get("ui_state")
    if isinstance(ui, str) and ui.strip():
        import json

        try:
            ui = json.loads(ui)
        except json.JSONDecodeError:
            ui = {}
    if isinstance(ui, dict):
        ui_tier = normalize_plan_tier(str(ui.get("plan_tier") or ""))
        if ui_tier != PLAN_ESSENTIAL:
            return ui_tier
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


def launch_offer_intro_months() -> int:
    """Meses com preço promocional por assinante (Stripe deve espelhar isto)."""
    return max(1, _int_env("EGO_LAUNCH_OFFER_MONTHS", 6))


def launch_offer_price_brl() -> float:
    return float(os.getenv("EGO_LAUNCH_OFFER_PRICE_BRL", "9.99") or "9.99")


def launch_offer_price_after_brl() -> float:
    return PLAN_PRICES_BRL[PLAN_CONNECTION]


def _parse_launch_start_date() -> datetime.date | None:
    raw = (os.getenv("EGO_LAUNCH_OFFER_START_DATE") or "2026-06-01").strip()
    if not raw:
        return None
    try:
        return datetime.date.fromisoformat(raw[:10])
    except ValueError:
        return None


def _add_months(d: datetime.date, months: int) -> datetime.date:
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    # Último dia do mês alvo
    if month == 12:
        next_first = datetime.date(year + 1, 1, 1)
    else:
        next_first = datetime.date(year, month + 1, 1)
    last_day = (next_first - datetime.timedelta(days=1)).day
    return datetime.date(year, month, min(d.day, last_day))


def launch_offer_campaign_active() -> bool:
    """Campanha visível no app (janela global, ex. 6 meses desde o lançamento na Play)."""
    start = _parse_launch_start_date()
    if not start:
        return True
    end = _add_months(start, launch_offer_intro_months())
    return datetime.date.today() < end


def launch_offer_campaign_ends_at() -> str | None:
    start = _parse_launch_start_date()
    if not start:
        return None
    return _add_months(start, launch_offer_intro_months()).isoformat()


def stripe_launch_checkout_url() -> str | None:
    """Oferta de lançamento BR (R$ 9,99 · 6 meses) — mesmos limites EGO Conexão."""
    if not launch_offer_campaign_active():
        return None
    return _clean_url(os.getenv("STRIPE_CHECKOUT_LAUNCH_URL", ""))


def build_launch_offer_payload() -> dict | None:
    """Payload para GET /api/v1/plans (None se campanha encerrada)."""
    url = stripe_launch_checkout_url()
    if not url:
        return None
    lim = plan_limits(PLAN_CONNECTION)
    price = launch_offer_price_brl()
    after = launch_offer_price_after_brl()
    months = launch_offer_intro_months()

    def _brl(v: float) -> str:
        return f"R$ {v:.2f}/mês".replace(".", ",")

    return {
        "tier": PLAN_CONNECTION,
        "label": "EGO Conexão — Oferta de lançamento",
        "price_brl": price,
        "price_label": _brl(price),
        "tagline": (
            f"Oferta de lançamento: {_brl(price)} por {months} meses. "
            f"Depois R$ 19,90/mês por {months} meses. "
            f"Depois {_brl(after)} (EGO Conexão). Cancele quando quiser. Sem cupons adicionais."
        ),
        "intro_months": months,
        "price_after_brl": after,
        "campaign_ends_at": launch_offer_campaign_ends_at(),
        "checkout_url": url,
        "limits": {
            "monthly_tokens": lim.monthly_tokens,
            "daily_text_messages": lim.daily_text_messages,
            "daily_voice_messages": lim.daily_voice_messages,
            "daily_tts_replies": lim.daily_tts_replies,
            "max_agenda_items": lim.max_agenda_items,
            "max_reminders": lim.max_reminders,
            "audio_speed_multipliers": list(lim.audio_speed_multipliers),
        },
    }


def stripe_checkout_urls() -> dict[str, str | None]:
    return {
        "launch": stripe_launch_checkout_url(),
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
