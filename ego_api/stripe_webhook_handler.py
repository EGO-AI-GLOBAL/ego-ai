"""
Webhook Stripe → Supabase (ativação de plano + comissão indicação).
Sem dependência de FastAPI — usado pelo Flask (Railway ego-ai) e stripe_webhook.py.
"""

from __future__ import annotations

import json
import os

import stripe

try:
    from ego_supabase import Client
except ImportError:
    from supabase import Client  # type: ignore[assignment]

from ego_api.plans import (
    PLAN_CONNECTION,
    PLAN_ESSENTIAL,
    normalize_plan_tier,
    stripe_object_to_tier,
)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "").strip() or None


class StripeWebhookError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def get_supabase_admin() -> Client:
    from ego_api.supabase_client import create_service_client

    client = create_service_client()
    if not client:
        raise RuntimeError("Defina SUPABASE_SERVICE_ROLE_KEY para o webhook.")
    return client


def _resolve_team_seats_from_session(session: dict) -> int | None:
    from ego_api.team_stripe_checkout import parse_team_seats

    meta = session.get("metadata") or {}
    for key in ("team_seats", "seats", "seat_count"):
        if meta.get(key) is not None:
            return parse_team_seats(meta.get(key))
    return None


def _resolve_tier_from_session(session: dict) -> str:
    meta = session.get("metadata") or {}
    for key in ("plan_tier", "plan", "tier"):
        if meta.get(key):
            return normalize_plan_tier(str(meta[key]))

    line_items = session.get("line_items") or {}
    if isinstance(line_items, dict):
        data = line_items.get("data") or []
        for item in data:
            price = (item or {}).get("price") or {}
            pid = str(price.get("id") or "")
            prod = str(price.get("product") or (item or {}).get("product") or "")
            tier = stripe_object_to_tier(price_id=pid, product_id=prod)
            if tier:
                return tier

    mode = str(session.get("mode") or "")
    if mode == "subscription":
        return PLAN_CONNECTION

    return PLAN_CONNECTION


def _apply_plan(
    supabase: Client, user_id: str, tier: str, *, team_seats: int | None = None
) -> dict:
    tier = normalize_plan_tier(tier)
    paid = tier != PLAN_ESSENTIAL
    payload: dict = {"plan_tier": tier, "is_pro": paid}
    if team_seats:
        row = (
            supabase.table("profiles")
            .select("ui_state")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        ui = {}
        if row.data:
            raw = row.data[0].get("ui_state")
            if isinstance(raw, dict):
                ui = dict(raw)
            elif isinstance(raw, str) and raw.strip():
                try:
                    ui = json.loads(raw)
                except json.JSONDecodeError:
                    ui = {}
        ui["team_seats"] = int(team_seats)
        ui["plan_type"] = "team"
        payload["ui_state"] = ui
    (
        supabase.table("profiles")
        .update(payload)
        .eq("id", user_id)
        .execute()
    )
    return {"plan_tier": tier, "is_pro": paid, "team_seats": team_seats}


def handle_stripe_webhook_payload(
    payload: bytes, stripe_signature: str | None
) -> tuple[dict, int]:
    """Processa evento Stripe. Retorna (corpo JSON, HTTP status)."""
    if not stripe_signature:
        return {"ok": False, "error": "Header Stripe-Signature ausente."}, 400

    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
    if not webhook_secret:
        return {"ok": False, "error": "STRIPE_WEBHOOK_SECRET não configurado."}, 500

    try:
        event = stripe.Webhook.construct_event(payload, stripe_signature, webhook_secret)
    except stripe.error.SignatureVerificationError:
        return {"ok": False, "error": "Assinatura inválida."}, 400
    except ValueError:
        return {"ok": False, "error": "Payload inválido."}, 400

    try:
        body = _process_stripe_event(event)
    except StripeWebhookError as exc:
        return {"ok": False, "error": exc.detail}, exc.status_code
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:200]}, 500
    return body, 200


def _process_stripe_event(event: dict) -> dict:
    event_type = event.get("type")

    if event_type in ("invoice.paid", "charge.refunded"):
        obj = event["data"]["object"]
        try:
            from ego_api.finance_revenue import (
                record_charge_refunded,
                record_invoice_paid,
            )

            if event_type == "invoice.paid":
                finance_result = record_invoice_paid(
                    obj, stripe_event_id=str(event.get("id") or "")
                )
            else:
                finance_result = record_charge_refunded(
                    obj, stripe_event_id=str(event.get("id") or "")
                )
        except Exception as exc:  # noqa: BLE001
            finance_result = {"recorded": False, "error": str(exc)[:200]}

        referral_result = None
        if event_type == "invoice.paid":
            try:
                from ego_api.finance_revenue import _user_id_from_invoice
                from ego_api.referrals import record_first_payment_commission

                uid = _user_id_from_invoice(obj)
                if uid:
                    supabase = get_supabase_admin()
                    referral_result = record_first_payment_commission(
                        supabase,
                        str(uid),
                        stripe_session_id=str(obj.get("id") or ""),
                    )
            except Exception as exc:  # noqa: BLE001
                referral_result = {"error": str(exc)[:200]}

        out_fin = {"ok": True, "finance": finance_result, "referral": referral_result}
        if event_type == "charge.refunded":
            return out_fin
        if event_type == "invoice.paid":
            return out_fin

    if event_type not in (
        "checkout.session.completed",
        "customer.subscription.deleted",
        "customer.subscription.updated",
    ):
        return {"ok": True, "ignored": event_type}

    obj = event["data"]["object"]
    user_id = obj.get("client_reference_id") or (obj.get("metadata") or {}).get("user_id")
    if not user_id and event_type != "checkout.session.completed":
        return {"ok": True, "ignored": "sem user_id"}

    if event_type == "customer.subscription.deleted":
        if not user_id:
            return {"ok": True, "ignored": "sem user_id"}
        try:
            supabase = get_supabase_admin()
            result = _apply_plan(supabase, str(user_id), PLAN_ESSENTIAL)
        except Exception:  # noqa: BLE001
            raise StripeWebhookError(500, "Falha ao rebaixar perfil.")
        return {"ok": True, "user_id": user_id, **result}

    if event_type == "customer.subscription.updated":
        status = str(obj.get("status") or "")
        if status in ("active", "trialing") and user_id:
            tier = normalize_plan_tier(
                str((obj.get("metadata") or {}).get("plan_tier") or PLAN_CONNECTION)
            )
        elif status in ("canceled", "unpaid", "past_due") and user_id:
            tier = PLAN_ESSENTIAL
        else:
            return {"ok": True, "ignored": status or "sem alteração"}
        try:
            supabase = get_supabase_admin()
            result = _apply_plan(supabase, str(user_id), tier)
        except Exception:  # noqa: BLE001
            raise StripeWebhookError(500, "Falha ao atualizar perfil.")
        return {"ok": True, "user_id": user_id, **result}

    session = obj
    user_id = session.get("client_reference_id")
    if not user_id:
        raise StripeWebhookError(
            400, "client_reference_id ausente no checkout session."
        )

    tier = _resolve_tier_from_session(session)
    team_seats = _resolve_team_seats_from_session(session)
    try:
        supabase = get_supabase_admin()
        sub_id = session.get("subscription")
        if session.get("mode") == "subscription" and stripe.api_key:
            try:
                full = stripe.checkout.Session.retrieve(
                    session["id"],
                    expand=["line_items.data.price.product"],
                )
                full_d = dict(full)
                tier = _resolve_tier_from_session(full_d)
                team_seats = _resolve_team_seats_from_session(full_d) or team_seats
                sub_id = sub_id or full_d.get("subscription")
            except Exception:
                pass
        if sub_id and stripe.api_key:
            try:
                stripe.Subscription.modify(
                    str(sub_id),
                    metadata={"user_id": str(user_id)},
                )
            except Exception:
                pass
        result = _apply_plan(supabase, str(user_id), tier, team_seats=team_seats)
        commission = None
        try:
            from ego_api.referrals import record_first_payment_commission

            commission = record_first_payment_commission(
                supabase,
                str(user_id),
                stripe_session_id=str(session.get("id") or ""),
            )
        except Exception:
            commission = {"error": "commission_skipped"}
    except StripeWebhookError:
        raise
    except Exception:  # noqa: BLE001
        raise StripeWebhookError(500, "Falha ao atualizar perfil.")

    out = {"ok": True, "user_id": user_id, **result}
    if commission:
        out["referral_commission"] = commission
    try:
        from ego_api.finance_revenue import record_checkout_completed

        out["finance"] = record_checkout_completed(
            session, stripe_event_id=str(event.get("id") or "")
        )
    except Exception as exc:  # noqa: BLE001
        out["finance"] = {"recorded": False, "error": str(exc)[:200]}
    return out
