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

    raw = session.get("metadata") if isinstance(session, dict) else None
    meta = raw if isinstance(raw, dict) else {}
    for key in ("team_seats", "seats", "seat_count"):
        if meta.get(key) is not None:
            return parse_team_seats(meta.get(key))
    return None


def _resolve_tier_from_session(session: dict) -> str:
    raw = session.get("metadata") if isinstance(session, dict) else None
    meta = raw if isinstance(raw, dict) else {}
    for key in ("plan_tier", "plan", "tier"):
        if meta.get(key):
            return normalize_plan_tier(str(meta[key]))

    line_items = session.get("line_items") or {}
    if isinstance(line_items, dict):
        data = line_items.get("data") or []
        for item in data:
            price = (item or {}).get("price") or {}
            if not isinstance(price, dict):
                price = {}
            pid = str(price.get("id") or "")
            prod = str(price.get("product") or (item or {}).get("product") or "")
            tier = stripe_object_to_tier(price_id=pid, product_id=prod)
            if tier:
                return tier

    mode = str(session.get("mode") or "")
    if mode == "subscription":
        return PLAN_CONNECTION

    return PLAN_CONNECTION


from ego_api.plan_grant import apply_plan_to_profile


def _as_plain_dict(value: object) -> dict:
    """Stripe API 2026+ pode devolver objetos sem .get() → AttributeError('get')."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        try:
            out = to_dict()
            if isinstance(out, dict):
                return out
        except Exception:  # noqa: BLE001
            pass
    try:
        return json.loads(json.dumps(value, default=lambda o: dict(o) if hasattr(o, "keys") else str(o)))
    except Exception:  # noqa: BLE001
        try:
            return dict(value)  # type: ignore[arg-type]
        except Exception:  # noqa: BLE001
            return {}


def _meta_dict(obj: dict) -> dict:
    meta = obj.get("metadata") if isinstance(obj, dict) else None
    return _as_plain_dict(meta) if meta is not None else {}


def _user_id_from_checkout_session(session: dict) -> str | None:
    meta = _meta_dict(session)
    uid = session.get("client_reference_id") or meta.get("user_id")
    if uid:
        return str(uid)
    email = str(session.get("customer_email") or "").strip().lower()
    if not email:
        details = _as_plain_dict(session.get("customer_details"))
        email = str(details.get("email") or "").strip().lower()
    if not email:
        return None
    try:
        from ego_api.shared_calendars import resolve_user_id_by_email

        return resolve_user_id_by_email(email)
    except Exception:
        return None


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
        body = _process_stripe_event(_as_plain_dict(event))
    except StripeWebhookError as exc:
        return {"ok": False, "error": exc.detail}, exc.status_code
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}"[:200],
        }, 500
    return body, 200


def _process_stripe_event(event: dict) -> dict:
    event = _as_plain_dict(event)
    event_type = event.get("type")
    data = _as_plain_dict(event.get("data"))

    if event_type in ("invoice.paid", "charge.refunded"):
        obj = _as_plain_dict(data.get("object"))
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
        friend_reward = None
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
                    try:
                        from ego_api.friend_referrals import grant_referrer_one_month

                        friend_reward = grant_referrer_one_month(
                            supabase,
                            str(uid),
                            stripe_session_id=str(obj.get("id") or ""),
                        )
                    except Exception as exc:  # noqa: BLE001
                        friend_reward = {"error": str(exc)[:200]}
            except Exception as exc:  # noqa: BLE001
                referral_result = {"error": str(exc)[:200]}

        out_fin = {
            "ok": True,
            "finance": finance_result,
            "referral": referral_result,
            "friend_referral_reward": friend_reward,
        }
        if event_type == "invoice.paid":
            try:
                from ego_api.partner_revenue import record_partner_split_from_invoice

                out_fin["partner_split"] = record_partner_split_from_invoice(
                    obj, stripe_event_id=str(event.get("id") or "")
                )
            except Exception as exc:  # noqa: BLE001
                out_fin["partner_split"] = {"recorded": False, "error": str(exc)[:200]}
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

    obj = _as_plain_dict(data.get("object"))
    meta = _meta_dict(obj)
    user_id = obj.get("client_reference_id") or meta.get("user_id")
    if not user_id and event_type != "checkout.session.completed":
        return {"ok": True, "ignored": "sem user_id"}

    if event_type == "customer.subscription.deleted":
        if not user_id:
            return {"ok": True, "ignored": "sem user_id"}
        try:
            supabase = get_supabase_admin()
            result = apply_plan_to_profile(supabase, str(user_id), PLAN_ESSENTIAL)
        except Exception:  # noqa: BLE001
            raise StripeWebhookError(500, "Falha ao rebaixar perfil.")
        return {"ok": True, "user_id": user_id, **result}

    if event_type == "customer.subscription.updated":
        status = str(obj.get("status") or "")
        # cancel_at_period_end ainda vem status=active — não rebaixar até deleted
        if obj.get("cancel_at_period_end") and status in ("active", "trialing"):
            return {"ok": True, "ignored": "cancel_at_period_end"}
        if status in ("active", "trialing") and user_id:
            tier = normalize_plan_tier(str(meta.get("plan_tier") or PLAN_CONNECTION))
        elif status in ("canceled", "unpaid", "past_due") and user_id:
            tier = PLAN_ESSENTIAL
        else:
            return {"ok": True, "ignored": status or "sem alteração"}
        try:
            supabase = get_supabase_admin()
            result = apply_plan_to_profile(supabase, str(user_id), tier)
        except Exception:  # noqa: BLE001
            raise StripeWebhookError(500, "Falha ao atualizar perfil.")
        return {"ok": True, "user_id": user_id, **result}

    session = obj
    user_id = _user_id_from_checkout_session(session)
    if not user_id:
        raise StripeWebhookError(
            400,
            "client_reference_id/e-mail ausente — não foi possível ligar o pagamento ao utilizador.",
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
                full_d = _as_plain_dict(full)
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
        result = apply_plan_to_profile(
            supabase, str(user_id), tier, team_seats=team_seats
        )
        commission = None
        friend_reward = None
        try:
            from ego_api.referrals import record_first_payment_commission

            commission = record_first_payment_commission(
                supabase,
                str(user_id),
                stripe_session_id=str(session.get("id") or ""),
            )
        except Exception:
            commission = {"error": "commission_skipped"}
        try:
            from ego_api.friend_referrals import grant_referrer_one_month

            friend_reward = grant_referrer_one_month(
                supabase,
                str(user_id),
                stripe_session_id=str(session.get("id") or ""),
            )
        except Exception:
            friend_reward = {"error": "friend_reward_skipped"}
    except StripeWebhookError:
        raise
    except Exception:  # noqa: BLE001
        raise StripeWebhookError(500, "Falha ao atualizar perfil.")

    out = {"ok": True, "user_id": user_id, **result}
    if commission:
        out["referral_commission"] = commission
    if friend_reward:
        out["friend_referral_reward"] = friend_reward
    try:
        from ego_api.finance_revenue import record_checkout_completed

        out["finance"] = record_checkout_completed(
            session, stripe_event_id=str(event.get("id") or "")
        )
    except Exception as exc:  # noqa: BLE001
        out["finance"] = {"recorded": False, "error": str(exc)[:200]}
    return out
