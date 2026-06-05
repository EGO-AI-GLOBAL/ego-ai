"""Normalização de telefone BR (convites e cadastro)."""

from __future__ import annotations

import re


def normalize_phone_br(raw: str) -> tuple[str, str | None]:
    """Devolve E.164 (+55…) ou erro em português."""
    digits = re.sub(r"\D", "", (raw or "").strip())
    if not digits:
        return "", "Informe o telefone com DDD."
    if digits.startswith("55") and len(digits) >= 12:
        norm = "+" + digits
    elif len(digits) in (10, 11):
        norm = "+55" + digits
    else:
        return "", "Telefone inválido. Use DDD + número (ex.: 11 99999-9999)."
    if len(norm) < 12 or len(norm) > 16:
        return "", "Telefone inválido."
    return norm, None


def format_phone_display(e164: str) -> str:
    """+5511999887766 → (11) 99988-7766"""
    digits = re.sub(r"\D", "", e164 or "")
    if digits.startswith("55"):
        digits = digits[2:]
    if len(digits) == 11:
        return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
    if len(digits) == 10:
        return f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"
    return e164 or "Telefone"


def phone_invite_email_placeholder(phone_e164: str) -> str:
    """Chave única em invited_email quando o convite é só por telefone."""
    digits = re.sub(r"\D", "", phone_e164)
    return f"phone{digits}@invite.ego"


def is_phone_invite_email(email: str) -> bool:
    return (email or "").strip().lower().endswith("@invite.ego") and (
        email or ""
    ).lower().startswith("phone")
