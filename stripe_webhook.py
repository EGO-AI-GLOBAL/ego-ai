"""
Webhook Stripe -> Supabase (ativação de plano Pro).

Como funciona:
1) Stripe envia evento para POST /stripe/webhook
2) Assinatura Stripe é validada com STRIPE_WEBHOOK_SECRET
3) Em checkout.session.completed, lê client_reference_id (user_id do Supabase)
4) Atualiza profiles.is_pro = true para esse user_id
"""

from __future__ import annotations

import os

import stripe
from fastapi import FastAPI, Header, HTTPException, Request
from supabase import Client, create_client

app = FastAPI(title="EGO-AI Stripe Webhook")


def get_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Variável obrigatória ausente: {name}")
    return value


def get_supabase_admin() -> Client:
    # Use de preferência SUPABASE_SERVICE_ROLE_KEY para update server-side.
    url = get_env("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    anon_key = os.getenv("SUPABASE_KEY", "").strip()
    key = service_key or anon_key
    if not key:
        raise RuntimeError("Defina SUPABASE_SERVICE_ROLE_KEY (recomendado) ou SUPABASE_KEY.")
    return create_client(url, key)


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/stripe/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> dict:
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Header Stripe-Signature ausente.")

    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
    if not webhook_secret:
        raise HTTPException(status_code=500, detail="STRIPE_WEBHOOK_SECRET não configurado.")

    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(payload, stripe_signature, webhook_secret)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Assinatura inválida.")
    except ValueError:
        raise HTTPException(status_code=400, detail="Payload inválido.")

    # Idempotência simplificada: ignorar eventos já processados poderia usar tabela local.
    if event.get("type") != "checkout.session.completed":
        return {"ok": True, "ignored": event.get("type")}

    session = event["data"]["object"]
    user_id = session.get("client_reference_id")
    if not user_id:
        raise HTTPException(
            status_code=400,
            detail="client_reference_id ausente no checkout session.",
        )

    try:
        supabase = get_supabase_admin()
        (
            supabase.table("profiles")
            .update({"is_pro": True})
            .eq("id", user_id)
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Falha ao atualizar perfil: {exc}")

    return {"ok": True, "user_id": user_id, "is_pro": True}

