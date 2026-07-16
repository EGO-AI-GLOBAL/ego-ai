"""
Validação de compra Google Play Billing (assinaturas) e ativação de plano.

Espelha ego_api/apple_iap.py. Usa a Google Play Developer API
(androidpublisher v3) com uma conta de serviço para verificar o
purchase_token enviado pelo app Android.

Credenciais (Railway env, uma das duas):
  GOOGLE_PLAY_SERVICE_ACCOUNT_JSON  -> conteúdo JSON da service account
  GOOGLE_PLAY_SERVICE_ACCOUNT_FILE  -> caminho para o ficheiro .json
Pacote (opcional, default com.egoai.app):
  GOOGLE_PLAY_PACKAGE_NAME
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

try:
    from ego_supabase import Client
except ImportError:
    from supabase import Client  # type: ignore[assignment]

from ego_api.plan_grant import apply_plan_to_profile
from ego_api.plans import normalize_plan_tier

DEFAULT_PACKAGE_NAME = "com.egoai.app"

# Mesmos product IDs do iOS (App Store == Play Console).
IAP_PRODUCT_TIERS: dict[str, str] = {
    "com.egoai.app.sub.connection.monthly": "connection",
    "com.egoai.app.sub.premium.monthly": "premium",
    "com.egoai.app.sub.total.monthly": "total",
}

_ANDROID_SCOPE = "https://www.googleapis.com/auth/androidpublisher"


class GooglePlayBillingError(Exception):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        self.status_code = status_code
        super().__init__(message)


def _package_name() -> str:
    return (os.getenv("GOOGLE_PLAY_PACKAGE_NAME") or DEFAULT_PACKAGE_NAME).strip()


def _load_service_account_info() -> dict[str, Any]:
    # Prefer vars dedicadas ao Play Billing; fallback = mesma conta do Play Integrity.
    for env_name in (
        "GOOGLE_PLAY_SERVICE_ACCOUNT_JSON",
        "GOOGLE_SERVICE_ACCOUNT_JSON",
    ):
        raw = (os.getenv(env_name) or "").strip()
        if raw:
            try:
                info = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise GooglePlayBillingError(
                    f"{env_name} inválido (não é JSON).",
                    status_code=503,
                ) from exc
            if isinstance(info, dict):
                return info

    for env_name in (
        "GOOGLE_PLAY_SERVICE_ACCOUNT_FILE",
        "GOOGLE_SERVICE_ACCOUNT_FILE",
    ):
        path = (os.getenv(env_name) or "").strip()
        if path and os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                info = json.load(fh)
            if isinstance(info, dict):
                return info

    raise GooglePlayBillingError(
        "Credenciais Google Play não configuradas no servidor "
        "(GOOGLE_PLAY_SERVICE_ACCOUNT_JSON ou GOOGLE_SERVICE_ACCOUNT_JSON).",
        status_code=503,
    )


def _build_android_publisher():
    try:
        from google.oauth2 import service_account  # type: ignore
        from googleapiclient.discovery import build  # type: ignore
    except ImportError as exc:
        raise GooglePlayBillingError(
            "Dependência google-api-python-client ausente no servidor.",
            status_code=503,
        ) from exc

    info = _load_service_account_info()
    credentials = service_account.Credentials.from_service_account_info(
        info, scopes=[_ANDROID_SCOPE]
    )
    return build("androidpublisher", "v3", credentials=credentials, cache_discovery=False)


def _fetch_subscription_v2(purchase_token: str) -> dict[str, Any]:
    service = _build_android_publisher()
    try:
        resp = (
            service.purchases()
            .subscriptionsv2()
            .get(packageName=_package_name(), token=purchase_token)
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        raise GooglePlayBillingError(
            f"Google Play rejeitou o token: {str(exc)[:180]}",
            status_code=400,
        ) from exc
    if not isinstance(resp, dict):
        raise GooglePlayBillingError("Resposta inválida da Google Play.", status_code=502)
    return resp


def _pick_product_id(
    payload: dict[str, Any], preferred_product_id: str | None
) -> str:
    product_ids: list[str] = []
    line_items = payload.get("lineItems")
    if isinstance(line_items, list):
        for item in line_items:
            if isinstance(item, dict):
                pid = str(item.get("productId") or "").strip()
                if pid:
                    product_ids.append(pid)

    ours = [p for p in product_ids if p in IAP_PRODUCT_TIERS]
    if preferred_product_id:
        pref = str(preferred_product_id).strip()
        if pref in ours:
            return pref
    if ours:
        return ours[0]
    if preferred_product_id and str(preferred_product_id).strip() in IAP_PRODUCT_TIERS:
        return str(preferred_product_id).strip()
    raise GooglePlayBillingError("Nenhuma assinatura EGO-AI válida neste token.")


def _is_active(payload: dict[str, Any]) -> bool:
    state = str(payload.get("subscriptionState") or "").strip()
    active_states = {
        "SUBSCRIPTION_STATE_ACTIVE",
        "SUBSCRIPTION_STATE_IN_GRACE_PERIOD",
        "SUBSCRIPTION_STATE_CANCELED",  # cancelado mas ainda dentro do período pago
    }
    if state:
        if state in active_states:
            # se cancelado, confirmar que ainda não expirou
            if state == "SUBSCRIPTION_STATE_CANCELED":
                return not _is_expired(payload)
            return True
        return False
    # sem estado explícito: cair para verificação por data
    return not _is_expired(payload)


def _is_expired(payload: dict[str, Any]) -> bool:
    line_items = payload.get("lineItems")
    if not isinstance(line_items, list):
        return False
    latest_ms = 0
    for item in line_items:
        if not isinstance(item, dict):
            continue
        expiry = str(item.get("expiryTime") or "").strip()
        ms = _iso_to_ms(expiry)
        if ms > latest_ms:
            latest_ms = ms
    if latest_ms <= 0:
        return False
    return latest_ms < int(time.time() * 1000)


def _iso_to_ms(value: str) -> int:
    if not value:
        return 0
    try:
        from datetime import datetime

        cleaned = value.replace("Z", "+00:00")
        return int(datetime.fromisoformat(cleaned).timestamp() * 1000)
    except (ValueError, OverflowError):
        return 0


def _acknowledge(purchase_token: str, product_id: str) -> None:
    """Confirma a compra (evita reembolso automático em 3 dias)."""
    try:
        service = _build_android_publisher()
        service.purchases().subscriptions().acknowledge(
            packageName=_package_name(),
            subscriptionId=product_id,
            token=purchase_token,
            body={},
        ).execute()
    except Exception:  # noqa: BLE001
        # Já reconhecido ou API v2 sem subscriptions() clássico — não bloquear activação.
        pass


def verify_and_grant_plan(
    supabase: Client,
    user_id: str,
    *,
    purchase_token: str,
    product_id: str | None = None,
    order_id: str | None = None,
) -> dict[str, Any]:
    token = (purchase_token or "").strip()
    if not token:
        raise GooglePlayBillingError("purchase_token ausente.")

    payload = _fetch_subscription_v2(token)
    resolved_product_id = _pick_product_id(payload, product_id)
    tier = IAP_PRODUCT_TIERS.get(resolved_product_id)
    if not tier:
        raise GooglePlayBillingError("Produto Play desconhecido.")

    if not _is_active(payload):
        raise GooglePlayBillingError("Assinatura Google Play inativa ou expirada.")

    tier = normalize_plan_tier(tier)

    linked = str(payload.get("linkedPurchaseToken") or token).strip()
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
    ui["google_play_purchase_token"] = linked or token
    ui["google_play_product_id"] = resolved_product_id
    if order_id:
        ui["google_play_order_id"] = str(order_id).strip()
    supabase.table("profiles").update({"ui_state": ui}).eq("id", user_id).execute()

    _acknowledge(token, resolved_product_id)

    granted = apply_plan_to_profile(supabase, user_id, tier)
    return {
        "ok": True,
        "plan_tier": granted["plan_tier"],
        "product_id": resolved_product_id,
        "purchase_token": linked or token,
    }
