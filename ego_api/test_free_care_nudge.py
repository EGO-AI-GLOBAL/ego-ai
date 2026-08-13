"""Testes leves do lembrete WhatsApp grátis (sem rede)."""
from datetime import date

from ego_api import free_care_nudge as n


def test_campaign_window():
    assert n.campaign_open(date(2026, 8, 13)) is True
    assert n.campaign_open(date(2026, 8, 12)) is False
    assert n.campaign_open(date(2026, 9, 30)) is True
    assert n.campaign_open(date(2026, 10, 1)) is False


def test_weekday_includes_start_thursday():
    # 13/08/2026 = quinta
    assert n.is_nudge_weekday(date(2026, 8, 13)) is True
    # 14/08 = sexta
    assert n.is_nudge_weekday(date(2026, 8, 14)) is True
    # 15/08 = sábado
    assert n.is_nudge_weekday(date(2026, 8, 15)) is False
    # 17/08 = segunda
    assert n.is_nudge_weekday(date(2026, 8, 17)) is True


def test_normalize_phone():
    assert n.normalize_wa_phone("11 99999-8888") == "5511999998888"
    assert n.normalize_wa_phone("+55 21 98888-7777") == "5521988887777"
    assert n.normalize_wa_phone("123") is None


def test_free_profile_filter():
    assert n._is_free_profile({"plan_tier": "essential", "is_pro": False}) is True
    assert n._is_free_profile({"plan_tier": "connection", "is_pro": False}) is False
    assert n._is_free_profile({"plan_tier": "essential", "is_pro": True}) is False


def test_messages_no_stripe_price():
    low = (n.REMINDER_MSG + n.PLANOS_REPLY).lower()
    assert "stripe" not in low
    assert "r$" not in low
    assert "29" not in low
    assert "assine um plano" not in low
    assert "planos" in n.REMINDER_MSG.lower()
