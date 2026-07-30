"""
Espelho ShapeScan → EGO: POST /internal/partner-mirror-from-shapescan

ShapeScan chama após /panel/partner-apply com sucesso.
Idempotente por partner_code (+ CNPJ se já existir outro code no mesmo CNPJ: actualiza).
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from ego_api.gym_partners import (
    DEFAULT_COMMISSION_PCT,
    GYM_PARTNERS_TABLE,
    PARTNER_APPLICATIONS_TABLE,
    get_admin_client,
    gym_commission_pct,
    is_valid_partner_code,
    normalize_cnpj,
    normalize_partner_code,
    partner_checkout_path,
)

_LOG = logging.getLogger("ego.partner_mirror")

PITCH_DEFAULT = (
    "Parceria única (ShapeScan + EGO) · apps e pagamentos separados · "
    "30% academia em cada Premium do código"
)


def partner_mirror_key() -> str:
    return (
        os.getenv("EGO_PARTNER_MIRROR_KEY", "").strip()
        or os.getenv("EGO_INTERNAL_KEY", "").strip()
    )


def _str(v: Any, default: str = "") -> str:
    if v is None:
        return default
    return str(v).strip() or default


def _notify_admin(partner_code: str, academia_nome: str, created: bool) -> None:
    to = (
        os.getenv("EGO_PARTNER_NOTIFY_EMAIL", "").strip()
        or os.getenv("EGO_OPS_EMAIL", "").strip()
        or "contato@egoai.com.br"
    )
    try:
        from ego_api.signup_emails import email_configured, send_ops_email

        if not email_configured():
            return
        verb = "criada" if created else "atualizada"
        send_ops_email(
            to_email=to,
            subject=f"[EGO] Academia {verb}: {partner_code}",
            text_body=(
                f"Parceria academia {verb} via mirror ShapeScan.\n"
                f"Código: {partner_code}\n"
                f"Nome: {academia_nome}\n"
                f"Comissão: {gym_commission_pct()}%\n"
                f"Checkout (fase B): {partner_checkout_path(partner_code)}\n"
            ),
            html_body=(
                f"<p>Parceria academia <b>{verb}</b> via mirror ShapeScan.</p>"
                f"<ul>"
                f"<li>Código: <b>{partner_code}</b></li>"
                f"<li>Nome: {academia_nome}</li>"
                f"<li>Comissão: {gym_commission_pct()}%</li>"
                f"</ul>"
            ),
        )
    except Exception as exc:
        _LOG.warning("partner mirror notify failed: %s", exc)


def upsert_from_shapescan_payload(body: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """
    Cria/atualiza gym_partners + regista partner_applications.
    Devolve (payload_ok, erro).
    """
    supabase = get_admin_client()
    if not supabase:
        return None, "Supabase service role não configurado."

    partner_code = normalize_partner_code(_str(body.get("partner_code")))
    if not is_valid_partner_code(partner_code):
        return None, "partner_code inválido."

    cnpj = normalize_cnpj(_str(body.get("cnpj")))
    if cnpj and len(cnpj) not in (11, 14):
        # aceita CPF representante errado no campo? exige CNPJ 14 se presente
        if len(cnpj) < 11:
            return None, "cnpj inválido."

    academia_nome = _str(body.get("academia_nome") or body.get("name"))
    if not academia_nome:
        return None, "academia_nome obrigatório."

    login_email = _str(body.get("login_email") or body.get("email_oficial")).lower()
    commission = body.get("commission_pct")
    try:
        commission_pct = int(commission) if commission is not None else gym_commission_pct()
    except (TypeError, ValueError):
        commission_pct = DEFAULT_COMMISSION_PCT
    commission_pct = max(1, min(90, commission_pct))

    products = body.get("products")
    if not isinstance(products, list) or not products:
        products = ["shapescan", "ego"]

    now_iso = datetime.now(timezone.utc).isoformat()
    pitch = _str(body.get("pitch"), PITCH_DEFAULT)

    row = {
        "name": academia_nome,
        "partner_code": partner_code,
        "active": True,
        "cnpj": cnpj or None,
        "razao_social": _str(body.get("razao_social")) or None,
        "endereco": _str(body.get("endereco")) or None,
        "cidade": _str(body.get("cidade")) or None,
        "uf": _str(body.get("uf")).upper()[:2] or None,
        "cep": _str(body.get("cep")) or None,
        "email_oficial": _str(body.get("email_oficial")).lower() or None,
        "whatsapp": _str(body.get("whatsapp")) or None,
        "representante_nome": _str(body.get("representante_nome")) or None,
        "representante_cpf": normalize_cnpj(_str(body.get("representante_cpf"))) or None,
        "representante_cargo": _str(body.get("representante_cargo")) or None,
        "instagram": _str(body.get("instagram")) or None,
        "login_email": login_email or None,
        "commission_pct": commission_pct,
        "source": _str(body.get("source"), "shapescan") or "shapescan",
        "products": products,
        "pitch": pitch,
        "updated_at": now_iso,
    }

    created = False
    existing = None
    try:
        by_code = (
            supabase.table(GYM_PARTNERS_TABLE)
            .select("id, partner_code, cnpj")
            .eq("partner_code", partner_code)
            .limit(1)
            .execute()
        )
        rows_code = by_code.data or []
        if rows_code:
            existing = rows_code[0]
        elif cnpj:
            by_cnpj = (
                supabase.table(GYM_PARTNERS_TABLE)
                .select("id, partner_code, cnpj")
                .eq("cnpj", cnpj)
                .limit(1)
                .execute()
            )
            rows_cnpj = by_cnpj.data or []
            if rows_cnpj:
                existing = rows_cnpj[0]
    except Exception as exc:
        _LOG.exception("gym_partners lookup: %s", exc)
        return None, (
            "Tabelas gym_partners em falta — corre "
            "supabase/COLE-GYM-PARTNERS-SHAPESCAN-MIRROR.sql no Supabase."
        )

    try:
        if existing:
            supabase.table(GYM_PARTNERS_TABLE).update(row).eq(
                "id", existing["id"]
            ).execute()
            partner_id = existing["id"]
        else:
            row["created_at"] = now_iso
            ins = supabase.table(GYM_PARTNERS_TABLE).insert(row).execute()
            inserted = (ins.data or [None])[0]
            if not inserted:
                # upsert fallback
                upsert = (
                    supabase.table(GYM_PARTNERS_TABLE)
                    .upsert(row, on_conflict="partner_code")
                    .execute()
                )
                inserted = (upsert.data or [None])[0]
            partner_id = (inserted or {}).get("id")
            created = True
    except Exception as exc:
        _LOG.exception("gym_partners write: %s", exc)
        return None, f"Falha ao gravar gym_partners: {exc}"

    auto_done = [
        "gym_partners upsert",
        f"commission_pct={commission_pct}",
        "source=shapescan mirror",
    ]
    manual_todo = [
        "Criar/ligar Stripe Connect account_id na academia (EGO)",
        "Confirmar checkout g.html?c=CODE (fase B)",
    ]

    try:
        supabase.table(PARTNER_APPLICATIONS_TABLE).insert(
            {
                "login_email": login_email or _str(body.get("email_oficial")).lower() or "unknown",
                "academia_nome": academia_nome,
                "razao_social": _str(body.get("razao_social")),
                "cnpj": cnpj or "",
                "endereco": _str(body.get("endereco")),
                "cidade": _str(body.get("cidade")),
                "uf": _str(body.get("uf")).upper()[:2],
                "cep": _str(body.get("cep")) or None,
                "email_oficial": _str(body.get("email_oficial")).lower(),
                "whatsapp": _str(body.get("whatsapp")),
                "representante_nome": _str(body.get("representante_nome")),
                "representante_cpf": normalize_cnpj(_str(body.get("representante_cpf"))),
                "representante_cargo": _str(body.get("representante_cargo")) or None,
                "instagram": _str(body.get("instagram")) or None,
                "partner_code": partner_code,
                "status": "activated",
                "auto_done": auto_done,
                "manual_todo": manual_todo,
                "source": "shapescan",
            }
        ).execute()
    except Exception as exc:
        _LOG.warning("partner_applications insert (non-fatal): %s", exc)

    _notify_admin(partner_code, academia_nome, created)

    return {
        "ok": True,
        "created": created,
        "partner_id": partner_id,
        "partner_code": partner_code,
        "academia_nome": academia_nome,
        "commission_pct": commission_pct,
        "checkout_url": partner_checkout_path(partner_code),
        "manual_todo": manual_todo,
        "message": (
            "Academia espelhada no EGO (corpo+mente · 30%)."
            if created
            else "Academia actualizada no EGO (idempotente)."
        ),
    }, None
