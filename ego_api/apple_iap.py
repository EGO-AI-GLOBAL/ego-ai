"""
Validação de recibo Apple (In-App Purchase) e ativação de plano.

Usa verifyReceipt (shared secret). Sandbox é tentado automaticamente (status 21007).
"""

from __future__ import annotations

import os
from typing import Any

import requests

try:
    from ego_supabase import Client
except ImportError:
    from supabase import Client  # type: ignore[assignment]

from ego_api.plan_grant import apply_plan_to_profile
from ego_api.plans import normalize_plan_tier

APPLE_VERIFY_PROD = "https://buy.itunes.apple.com/verifyReceipt"
APPLE_VERIFY_SANDBOX = "https://sandbox.itunes.apple.com/verifyReceipt"

IAP_PRODUCT_TIERS: dict[str, str] = {
    "com.egoai.app.sub.connection.monthly": "connection",
    "com.egoai.app.sub.premium.monthly": "premium",
    "com.egoai.app.sub.total.monthly": "total",
}


class AppleIapError(Exception):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        self.status_code = status_code
        super().__init__(message)


def _post_verify(url: str, receipt_data: str, shared_secret: str) -> dict[str, Any]:
    body: dict[str, Any] = {
        "receipt-data": receipt_data,
        "exclude-old-transactions": True,
    }
    if shared_secret:
        body["password"] = shared_secret
    resp = requests.post(url, json=body, timeout=25)
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, dict):
        raise AppleIapError("Resposta inválida da Apple.", status_code=502)
    return data


def _verify_with_apple(receipt_data: str) -> dict[str, Any]:
    receipt = (receipt_data or "").strip()
    if not receipt:
        raise AppleIapError("Recibo ausente.")

    shared_secret = os.getenv("APPLE_IAP_SHARED_SECRET", "").strip()
    if not shared_secret:
        raise AppleIapError(
            "APPLE_IAP_SHARED_SECRET não configurado no servidor.",
            status_code=503,
        )

    result = _post_verify(APPLE_VERIFY_PROD, receipt, shared_secret)
    status = int(result.get("status") or 0)
    if status == 21007:
        result = _post_verify(APPLE_VERIFY_SANDBOX, receipt, shared_secret)
        status = int(result.get("status") or 0)
    if status != 0:
        raise AppleIapError(f"Recibo Apple rejeitado (status {status}).")
    return result


def _pick_subscription_product(
    apple_payload: dict[str, Any], preferred_product_id: str | None
) -> tuple[str, dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    latest = apple_payload.get("latest_receipt_info")
    if isinstance(latest, list):
        candidates.extend([x for x in latest if isinstance(x, dict)])

    receipt = apple_payload.get("receipt")
    if isinstance(receipt, dict):
        in_app = receipt.get("in_app")
        if isinstance(in_app, list):
            candidates.extend([x for x in in_app if isinstance(x, dict)])

    renewal = apple_payload.get("pending_renewal_info")
    if isinstance(renewal, list):
        for item in renewal:
            if isinstance(item, dict) and item.get("auto_renew_product_id"):
                candidates.append(
                    {
                        "product_id": item.get("auto_renew_product_id"),
                        "expires_date_ms": item.get("grace_period_expires_date_ms")
                        or item.get("expires_date_ms"),
                    }
                )

    our_ids = set(IAP_PRODUCT_TIERS)
    matches = [
        c
        for c in candidates
        if str(c.get("product_id") or c.get("productId") or "") in our_ids
    ]
    if preferred_product_id:
        pref = str(preferred_product_id).strip()
        preferred = [m for m in matches if str(m.get("product_id") or "") == pref]
        if preferred:
            matches = preferred

    if not matches:
        raise AppleIapError("Nenhuma assinatura EGO-AI válida no recibo.")

    def sort_key(item: dict[str, Any]) -> str:
        return str(
            item.get("expires_date_ms")
            or item.get("purchase_date_ms")
            or item.get("original_purchase_date_ms")
            or ""
        )

    best = max(matches, key=sort_key)
    product_id = str(best.get("product_id") or "")
    tier = IAP_PRODUCT_TIERS.get(product_id)
    if not tier:
        raise AppleIapError("Produto IAP desconhecido.")
    return tier, best


def verify_and_grant_plan(
    supabase: Client,
    user_id: str,
    *,
    receipt_data: str,
    product_id: str | None = None,
    transaction_id: str | None = None,
) -> dict[str, Any]:
    apple_payload = _verify_with_apple(receipt_data)
    tier, tx = _pick_subscription_product(apple_payload, product_id)
    tier = normalize_plan_tier(tier)

    expires_ms = str(tx.get("expires_date_ms") or "").strip()
    if expires_ms.isdigit() and int(expires_ms) > 0:
        import time

        if int(expires_ms) < int(time.time() * 1000):
            raise AppleIapError("Assinatura expirada.")

    original_tx = str(tx.get("original_transaction_id") or transaction_id or "").strip()
    if original_tx:
        row = (
            supabase.table("profiles")
            .select("ui_state")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        ui: dict[str, Any] = {}
        if row.data:
            raw = row.data[0].get("ui_state")
            if isinstance(raw, dict):
                ui = dict(raw)
        ui["apple_iap_original_transaction_id"] = original_tx
        ui["apple_iap_product_id"] = str(tx.get("product_id") or product_id or "")
        supabase.table("profiles").update({"ui_state": ui}).eq("id", user_id).execute()

    granted = apply_plan_to_profile(supabase, user_id, tier)
    return {
        "ok": True,
        "plan_tier": granted["plan_tier"],
        "product_id": str(tx.get("product_id") or product_id or ""),
        "original_transaction_id": original_tx or None,
    }
