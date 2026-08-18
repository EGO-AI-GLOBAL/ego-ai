"""Lembrete WhatsApp — só contas GRÁTIS do Ego (teste até 30/09/2026).

- 1.º envio: 13/08/2026 ~17h BRT; depois seg/qua/sex 17h.
- Só Essential (grátis) com telefone no cadastro.
- Quem já pagou: sem automático; se escrever PLANOS → «olha no app».
- Sem preço, sem link Stripe. Instância WhatsApp do Ego (não ShapeScan).
- Teto ~25/dia, pausa 90–180s. 100% na nuvem (thread no Railway).
"""
from __future__ import annotations

import logging
import os
import random
import re
import threading
import time
from datetime import date, datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from ego_api.plans import PLAN_ESSENTIAL, is_paid_plan, resolve_plan_tier
from ego_api.supabase_client import create_service_client
from ego_api.whatsapp_send import (
    WhatsAppSendError,
    resolve_whatsapp_provider_name,
    send_whatsapp_text,
)

logger = logging.getLogger(__name__)

BRT = ZoneInfo("America/Sao_Paulo")
TEST_START = date(2026, 8, 13)
TEST_END = date(2026, 9, 30)
NUDGE_WEEKDAYS = {0, 2, 4}  # seg qua sex (+ dia de arranque)
KIND_REMINDER = "reminder"
KIND_PLANOS = "planos_reply"
LOG_TABLE = "ego_free_nudge_log"
# Número oficial do Ego nesta campanha (BR). Instância Z-API/Evolution tem de ser DESTE número.
EGO_WHATSAPP_NUMBER = "5532999811376"

_cron_started = False
_job_lock = threading.Lock()
_job_running = False
_last: dict[str, Any] | None = None

REMINDER_MSG = (
    "Ego — lembrete de hoje\n\n"
    "Abre o app e usa o que já tens na conta grátis.\n\n"
    "Funções Pro são no app.\n"
    "Se quiser saber, responde PLANOS."
)

PLANOS_REPLY = (
    "Os planos estão no app.\n"
    "Abre o Ego e vê os planos.\n"
    "Assina só dentro do app."
)


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key) or default).strip()


def _enabled() -> bool:
    return _env("FREE_NUDGE_ENABLED", "1").lower() not in ("0", "false", "no")


def _ops_ok(hdr: str) -> bool:
    token = _env("FREE_NUDGE_OPS_TOKEN") or _env("EGO_OPS_TOKEN")
    if not token:
        return False
    return (hdr or "").strip() == token


def _max_per_day() -> int:
    try:
        return max(1, min(80, int(_env("FREE_NUDGE_MAX_PER_DAY", "25") or "25")))
    except ValueError:
        return 25


def _delay_sec() -> float:
    try:
        lo = float(_env("FREE_NUDGE_DELAY_MIN_SEC", "90") or "90")
        hi = float(_env("FREE_NUDGE_DELAY_MAX_SEC", "180") or "180")
    except ValueError:
        lo, hi = 90.0, 180.0
    if hi < lo:
        lo, hi = hi, lo
    return random.uniform(lo, hi)


def _cron_hour() -> int:
    try:
        return max(0, min(23, int(_env("FREE_NUDGE_HOUR_BRT", "17") or "17")))
    except ValueError:
        return 17


def now_brt() -> datetime:
    return datetime.now(BRT)


def campaign_open(today: date | None = None) -> bool:
    d = today or now_brt().date()
    return TEST_START <= d <= TEST_END


def is_nudge_weekday(d: date | None = None) -> bool:
    day = d or now_brt().date()
    if day == TEST_START:
        return True
    return day.weekday() in NUDGE_WEEKDAYS


def normalize_wa_phone(raw: str) -> str | None:
    digits = re.sub(r"\D+", "", raw or "")
    if len(digits) < 10:
        return None
    if digits.startswith("55") and len(digits) >= 12:
        return digits
    return "55" + digits


def _phone_from_profile(row: dict[str, Any]) -> str | None:
    return normalize_wa_phone(str(row.get("phone") or ""))


def _is_free_profile(row: dict[str, Any]) -> bool:
    """Só Essential efectivo — pago / bónus indicação / is_pro fora do automático."""
    if bool(row.get("is_pro")):
        return False
    tier = resolve_plan_tier(row)
    return not is_paid_plan(tier) and tier == PLAN_ESSENTIAL


def list_free_candidates() -> list[dict[str, Any]]:
    svc = create_service_client()
    if not svc:
        return []
    rows: list[dict[str, Any]] = []
    start = 0
    page = 1000
    while True:
        try:
            res = (
                svc.table("profiles")
                .select(
                    "id,email,phone,full_name,is_pro,plan_tier,referral_bonus_until"
                )
                .range(start, start + page - 1)
                .execute()
            )
        except Exception as exc:
            logger.warning("free_nudge profiles: %s", exc)
            break
        chunk = list(res.data or [])
        if not chunk:
            break
        rows.extend(chunk)
        if len(chunk) < page:
            break
        start += page

    out: list[dict[str, Any]] = []
    seen_phone: set[str] = set()
    for row in rows:
        uid = str(row.get("id") or "").strip()
        if not uid or not _is_free_profile(row):
            continue
        phone = _phone_from_profile(row)
        if not phone or phone in seen_phone:
            continue
        seen_phone.add(phone)
        out.append(
            {
                "user_id": uid,
                "phone": phone,
                "email": row.get("email"),
                "name": row.get("full_name"),
            }
        )
    return out


def _sent_today_phones(svc, kind: str, today: date) -> set[str]:
    start = datetime(today.year, today.month, today.day, tzinfo=BRT).isoformat()
    try:
        res = (
            svc.table(LOG_TABLE)
            .select("phone")
            .eq("kind", kind)
            .gte("sent_at", start)
            .eq("ok", True)
            .execute()
        )
        return {
            normalize_wa_phone(str(r.get("phone") or "")) or ""
            for r in list(res.data or [])
        } - {""}
    except Exception as exc:
        logger.warning("free_nudge log read: %s", exc)
        return set()


def _log_send(
    svc,
    *,
    user_id: str | None,
    phone: str,
    kind: str,
    ok: bool,
    error: str | None,
) -> None:
    if not svc:
        return
    try:
        svc.table(LOG_TABLE).insert(
            {
                "user_id": user_id,
                "phone": phone,
                "kind": kind,
                "ok": ok,
                "error": (error or "")[:400] or None,
                "provider": resolve_whatsapp_provider_name(),
                "sent_at": datetime.now(timezone.utc).isoformat(),
            }
        ).execute()
    except Exception as exc:
        logger.warning("free_nudge log write: %s", exc)


def preview() -> dict[str, Any]:
    today = now_brt().date()
    cands = list_free_candidates()
    return {
        "ok": True,
        "enabled": _enabled(),
        "campaign_open": campaign_open(today),
        "test_start": TEST_START.isoformat(),
        "test_end": TEST_END.isoformat(),
        "nudge_weekday": is_nudge_weekday(today),
        "today": today.isoformat(),
        "provider": resolve_whatsapp_provider_name(),
        "ego_whatsapp_number": _env("EGO_WHATSAPP_NUMBER") or EGO_WHATSAPP_NUMBER,
        "candidates": len(cands),
        "max_per_day": _max_per_day(),
        "hour_brt": _cron_hour(),
        "job_running": _job_running,
        "last": _last,
        "reminder_msg": REMINDER_MSG,
        "planos_reply": PLANOS_REPLY,
    }


def run_reminder_batch(*, force: bool = False, allow_dry: bool = False) -> dict[str, Any]:
    """Envia lembrete aos grátis com telefone (teto/dia)."""
    global _last
    today = now_brt().date()
    if not _enabled():
        return {"ok": False, "error": "FREE_NUDGE_ENABLED=0"}
    if not campaign_open(today):
        return {"ok": False, "error": f"Campanha fechou em {TEST_END.isoformat()}"}
    if not force and not is_nudge_weekday(today):
        return {"ok": False, "error": "Hoje não é seg/qua/sex. Usa force=1 só em teste."}

    provider = resolve_whatsapp_provider_name()
    if provider == "dry_run" and not allow_dry:
        return {
            "ok": False,
            "error": "WhatsApp do Ego não configurado no Railway "
            "(ZAPI_* ou EVOLUTION_* da instância Ego — não ShapeScan).",
            "provider": provider,
        }

    cands = list_free_candidates()
    svc = create_service_client()
    already = _sent_today_phones(svc, KIND_REMINDER, today) if svc else set()
    pending = [c for c in cands if c["phone"] not in already]
    cap = _max_per_day()
    batch = pending[:cap]
    sent = 0
    failed = 0
    errors: list[str] = []

    for i, c in enumerate(batch):
        try:
            send_whatsapp_text(c["phone"], REMINDER_MSG)
            _log_send(
                svc,
                user_id=c["user_id"],
                phone=c["phone"],
                kind=KIND_REMINDER,
                ok=True,
                error=None,
            )
            sent += 1
        except WhatsAppSendError as exc:
            failed += 1
            errors.append(str(exc)[:180])
            _log_send(
                svc,
                user_id=c["user_id"],
                phone=c["phone"],
                kind=KIND_REMINDER,
                ok=False,
                error=str(exc),
            )
        except Exception as exc:
            failed += 1
            errors.append(str(exc)[:180])
            _log_send(
                svc,
                user_id=c["user_id"],
                phone=c["phone"],
                kind=KIND_REMINDER,
                ok=False,
                error=str(exc),
            )
        if i + 1 < len(batch):
            time.sleep(_delay_sec())

    _last = {
        "at": now_brt().isoformat(),
        "kind": KIND_REMINDER,
        "provider": provider,
        "candidates": len(cands),
        "pending_before": len(pending),
        "attempted": len(batch),
        "sent": sent,
        "failed": failed,
        "remaining": max(0, len(pending) - len(batch)),
    }
    return {"ok": True, **_last, "errors": errors[:8]}


def handle_inbound_text(phone_raw: str, text: str) -> dict[str, Any]:
    """Resposta PLANOS (serviço). Ignora o resto. Pago também só recebe «olha no app»."""
    phone = normalize_wa_phone(phone_raw)
    body = (text or "").strip().lower()
    if not phone:
        return {"ok": False, "ignored": True, "reason": "phone"}
    if "plano" not in body:
        return {"ok": True, "ignored": True, "reason": "not_planos"}

    svc = create_service_client()
    today = now_brt().date()
    if svc:
        already = _sent_today_phones(svc, KIND_PLANOS, today)
        if phone in already:
            return {"ok": True, "ignored": True, "reason": "already_replied_today"}

    user_id = None
    if svc:
        try:
            res = (
                svc.table("profiles")
                .select("id,phone")
                .execute()
            )
            for row in list(res.data or []):
                p = normalize_wa_phone(str(row.get("phone") or ""))
                if p == phone:
                    user_id = str(row.get("id") or "") or None
                    break
        except Exception as exc:
            logger.warning("inbound profile: %s", exc)

    try:
        send_whatsapp_text(phone, PLANOS_REPLY)
        _log_send(svc, user_id=user_id, phone=phone, kind=KIND_PLANOS, ok=True, error=None)
        return {"ok": True, "replied": True}
    except Exception as exc:
        _log_send(svc, user_id=user_id, phone=phone, kind=KIND_PLANOS, ok=False, error=str(exc))
        return {"ok": False, "error": str(exc)[:200]}


def extract_inbound(payload: dict[str, Any]) -> tuple[str, str] | None:
    if not isinstance(payload, dict):
        return None
    if payload.get("fromMe") is True:
        return None
    phone = str(
        payload.get("phone")
        or payload.get("from")
        or (payload.get("key") or {}).get("remoteJid")
        or ""
    )
    text = ""
    t = payload.get("text")
    if isinstance(t, dict):
        text = str(t.get("message") or t.get("text") or "")
    elif isinstance(t, str):
        text = t
    text = text or str(payload.get("message") or payload.get("body") or "")
    if isinstance(payload.get("data"), dict):
        inner = extract_inbound(payload["data"])
        if inner:
            return inner
    phone_n = normalize_wa_phone(phone.split("@")[0] if "@" in phone else phone)
    if not phone_n or not (text or "").strip():
        return None
    return phone_n, text


def _cron_loop() -> None:
    global _job_running
    last_key = ""
    while True:
        try:
            time.sleep(45)
            if not _enabled():
                continue
            now = now_brt()
            if not campaign_open(now.date()):
                continue
            if not is_nudge_weekday(now.date()):
                continue
            if now.hour != _cron_hour():
                continue
            key = now.date().isoformat()
            if key == last_key:
                continue
            if resolve_whatsapp_provider_name() == "dry_run":
                logger.warning("free_nudge cron skip: WhatsApp Ego não configurado")
                last_key = key
                continue
            if not _job_lock.acquire(blocking=False):
                continue
            try:
                _job_running = True
                logger.info("free_nudge cron start %s", key)
                run_reminder_batch(force=False)
                last_key = key
            finally:
                _job_running = False
                _job_lock.release()
        except Exception as exc:
            logger.warning("free_nudge cron: %s", exc)


def start_free_nudge_cron() -> None:
    global _cron_started
    if _cron_started:
        return
    if not _enabled():
        logger.info("free_nudge cron off")
        return
    _cron_started = True
    t = threading.Thread(target=_cron_loop, name="ego-free-nudge", daemon=True)
    t.start()
    logger.info(
        "free_nudge cron on · %s · %dh BRT · %s→%s",
        resolve_whatsapp_provider_name(),
        _cron_hour(),
        TEST_START.isoformat(),
        TEST_END.isoformat(),
    )


def register_free_nudge_routes(app) -> None:
    from flask import jsonify, request

    def _token() -> str:
        return (
            request.headers.get("X-Ops-Token")
            or request.args.get("token")
            or request.headers.get("Authorization", "").replace("Bearer ", "")
            or ""
        )

    @app.get("/ops/free-nudge/preview")
    def free_nudge_preview():
        if not _ops_ok(_token()):
            return jsonify({"error": "token"}), 401
        return jsonify(preview())

    @app.post("/ops/free-nudge/run")
    def free_nudge_run():
        global _job_running
        if not _ops_ok(_token()):
            return jsonify({"error": "token"}), 401
        force = str(request.args.get("force") or "").strip() in ("1", "true", "yes")
        allow_dry = str(request.args.get("allow_dry") or "").strip() in ("1", "true", "yes")
        if _job_running:
            return jsonify({"error": "já está a enviar"}), 409
        if not _job_lock.acquire(blocking=False):
            return jsonify({"error": "já está a enviar"}), 409
        try:
            _job_running = True
            return jsonify(run_reminder_batch(force=force, allow_dry=allow_dry))
        finally:
            _job_running = False
            _job_lock.release()

    @app.post("/ops/free-nudge/inbound")
    def free_nudge_inbound():
        """Webhook Z-API / Evolution — mensagem recebida (instância Ego)."""
        if not _ops_ok(_token()):
            return jsonify({"error": "token"}), 401
        payload = request.get_json(silent=True) or {}
        parsed = extract_inbound(payload)
        if not parsed:
            return jsonify({"ok": True, "ignored": True})
        phone, text = parsed
        return jsonify(handle_inbound_text(phone, text))
