"""Envio WhatsApp (Z-API / Evolution / dry_run) — instância do EGO, não ShapeScan.

Variáveis no Railway (serviço ego-ai):
  WHATSAPP_PROVIDER=zapi|evolution|dry_run
  ZAPI_INSTANCE_ID / ZAPI_TOKEN / ZAPI_CLIENT_TOKEN  (número do Ego)
  ou EVOLUTION_API_URL / EVOLUTION_API_KEY / EVOLUTION_INSTANCE
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any
from urllib.parse import quote

logger = logging.getLogger(__name__)


class WhatsAppSendError(Exception):
    pass


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key) or default).strip()


def resolve_whatsapp_provider_name() -> str:
    forced = _env("WHATSAPP_PROVIDER").lower()
    if forced in ("zapi", "evolution", "dry_run", "dry-run", "none"):
        return "dry_run" if forced in ("dry-run", "none") else forced
    if _env("ZAPI_INSTANCE_ID") and _env("ZAPI_TOKEN"):
        return "zapi"
    if _env("EVOLUTION_API_URL") and _env("EVOLUTION_API_KEY") and _env("EVOLUTION_INSTANCE"):
        return "evolution"
    return "dry_run"


def send_whatsapp_text(phone_digits: str, message: str) -> dict[str, Any]:
    provider = resolve_whatsapp_provider_name()
    phone = re.sub(r"\D+", "", phone_digits or "")
    if not phone:
        raise WhatsAppSendError("telefone vazio")
    if provider == "dry_run":
        logger.info("WA dry_run → …%s (%d chars)", phone[-4:], len(message or ""))
        return {
            "ok": True,
            "provider": "dry_run",
            "message_id": f"dry-{phone[-4:]}-{int(time.time())}",
        }
    if provider == "zapi":
        return _send_zapi(phone, message)
    if provider == "evolution":
        return _send_evolution(phone, message)
    raise WhatsAppSendError(f"provider desconhecido: {provider}")


def _send_zapi(phone: str, message: str) -> dict[str, Any]:
    import urllib.error
    import urllib.request

    instance = _env("ZAPI_INSTANCE_ID")
    token = _env("ZAPI_TOKEN")
    client_token = _env("ZAPI_CLIENT_TOKEN")
    base = (_env("ZAPI_BASE_URL") or "https://api.z-api.io").rstrip("/")
    url = f"{base}/instances/{instance}/token/{token}/send-text"
    payload = json.dumps({"phone": phone, "message": message}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            **({"Client-Token": client_token} if client_token else {}),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            data = json.loads(body) if body else {}
            mid = str(data.get("messageId") or data.get("id") or data.get("zaapId") or "")
            return {"ok": True, "provider": "zapi", "message_id": mid or None, "raw": data}
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")[:400]
        raise WhatsAppSendError(f"Z-API HTTP {exc.code}: {err_body}") from exc
    except Exception as exc:
        raise WhatsAppSendError(f"Z-API: {exc}") from exc


def _send_evolution(phone: str, message: str) -> dict[str, Any]:
    import urllib.error
    import urllib.request

    base = _env("EVOLUTION_API_URL").rstrip("/")
    key = _env("EVOLUTION_API_KEY")
    instance = _env("EVOLUTION_INSTANCE")
    url = f"{base}/message/sendText/{quote(instance)}"
    number = phone if "@" in phone else phone
    payload = json.dumps({"number": number, "text": message}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "apikey": key,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            data = json.loads(body) if body else {}
            key_obj = data.get("key") if isinstance(data.get("key"), dict) else {}
            mid = str((key_obj or {}).get("id") or data.get("messageId") or data.get("id") or "")
            return {"ok": True, "provider": "evolution", "message_id": mid or None, "raw": data}
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")[:400]
        raise WhatsAppSendError(f"Evolution HTTP {exc.code}: {err_body}") from exc
    except Exception as exc:
        raise WhatsAppSendError(f"Evolution: {exc}") from exc
