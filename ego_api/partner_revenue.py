"""Auditoria do split parceiro 30/70 (Connect destination — sem Transfer manual)."""

from __future__ import annotations

import logging
from typing import Any

_LOG = logging.getLogger("ego.partner_revenue")


def record_partner_split_from_invoice(
    invoice: dict[str, Any],
    *,
    stripe_event_id: str = "",
) -> dict[str, Any]:
    """
    Regista em partner_revenue_ledger o split esperado.
    O dinheiro já foi dividido pelo Stripe (application_fee + transfer_data).
    """
    from ego_api.gym_partners import (
        PREMIUM_PRICE_CENTS,
        get_admin_client,
        lookup_gym_partner,
        normalize_partner_code,
        resolve_connect_account_id,
        split_amounts_cents,
    )

    meta = invoice.get("metadata") if isinstance(invoice.get("metadata"), dict) else {}
    # metadata pode estar na subscription — invoice.subscription_details
    sub_details = invoice.get("subscription_details")
    if isinstance(sub_details, dict) and isinstance(sub_details.get("metadata"), dict):
        meta = {**sub_details["metadata"], **meta}

    channel = str(meta.get("channel") or "").strip().lower()
    partner_code = normalize_partner_code(
        str(meta.get("partner_coupon_code") or meta.get("partner_code") or "")
    )
    if channel not in ("partner", "gym") and not partner_code:
        return {"recorded": False, "reason": "not_partner_channel"}

    if not partner_code:
        return {"recorded": False, "reason": "no_partner_code"}

    total = int(invoice.get("amount_paid") or invoice.get("total") or PREMIUM_PRICE_CENTS)
    try:
        commission = int(meta.get("commission_pct") or 30)
    except (TypeError, ValueError):
        commission = 30
    amounts = split_amounts_cents(total, commission)

    sb = get_admin_client()
    if not sb:
        return {"recorded": False, "reason": "no_supabase"}

    acct = None
    try:
        row = lookup_gym_partner(sb, partner_code)
        acct = resolve_connect_account_id(row) if row else None
    except Exception as exc:
        _LOG.warning("lookup partner for ledger: %s", exc)

    inv_id = str(invoice.get("id") or "") or None
    row_payload = {
        "partner_code": partner_code,
        "stripe_account_id": acct,
        "stripe_invoice_id": inv_id,
        "stripe_event_id": (stripe_event_id or None),
        "amount_total_cents": amounts["amount_total_cents"],
        "partner_share_cents": amounts["partner_share_cents"],
        "platform_share_cents": amounts["platform_share_cents"],
        "commission_pct": amounts["commission_pct"],
        "note": "connect_destination_auto_split",
    }
    try:
        sb.table("partner_revenue_ledger").upsert(
            row_payload, on_conflict="stripe_invoice_id"
        ).execute()
    except Exception:
        # unique index parcial — tenta insert simples
        try:
            sb.table("partner_revenue_ledger").insert(row_payload).execute()
        except Exception as exc:
            _LOG.warning("partner_revenue_ledger: %s", exc)
            return {"recorded": False, "error": str(exc)[:200]}

    return {
        "recorded": True,
        "partner_code": partner_code,
        "partner_share_cents": amounts["partner_share_cents"],
        "platform_share_cents": amounts["platform_share_cents"],
        "split_mode": "connect_destination_auto_split",
    }
