"""
Webhook Stripe (serviço FastAPI opcional).
Lógica compartilhada em ego_api.stripe_webhook_handler (Flask Railway usa direto).
"""

from __future__ import annotations

from fastapi import FastAPI, Header, HTTPException, Request

from ego_api.stripe_webhook_handler import handle_stripe_webhook_payload

app = FastAPI(title="EGO-AI Stripe Webhook")


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/stripe/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> dict:
    payload = await request.body()
    body, status = handle_stripe_webhook_payload(payload, stripe_signature)
    if status >= 400:
        raise HTTPException(status_code=status, detail=body.get("error") or body)
    return body
