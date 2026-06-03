"""
Despesas automáticas — comissão de indicação (cupom / código parceiro).

Quando `record_first_payment_commission` cria R$ 10 para o parceiro,
registra DESPESA em `registro-diario.csv` (e espelho opcional no Supabase).
"""

from __future__ import annotations

import csv
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ego_api.finance_revenue import (
    _format_br,
    _read_registro,
    _stripe_id_in_registro,
    _write_registro,
    refresh_finance_summary,
    resolve_finance_dir,
)


def _commission_stripe_id(commission_id: str) -> str:
    return f"commission:{commission_id}"


def record_partner_commission_expense(
    *,
    commission_id: str,
    partner_code: str,
    partner_name: str,
    amount_brl: float,
    payment_date: str,
    payout_month: str,
    referred_user_id: str = "",
) -> dict[str, Any]:
    """Lança comissão de parceiro como DESPESA (idempotente)."""
    if not commission_id:
        return {"recorded": False, "reason": "sem_commission_id"}

    stripe_id = _commission_stripe_id(commission_id)
    finance_dir = resolve_finance_dir()
    if not finance_dir:
        return {
            "recorded": False,
            "reason": "finance_dir_ausente",
            "stripe_id": stripe_id,
        }

    path = finance_dir / "registro-diario.csv"
    rows = _read_registro(path) if path.exists() else []
    if _stripe_id_in_registro(rows, stripe_id):
        return {"recorded": False, "reason": "duplicate", "stripe_id": stripe_id}

    categoria = f"Parceiro {partner_code}"
    obs = (
        f"Comissão indicação 1º pagamento — {partner_name} "
        f"(mês repasse {payout_month})"
    )
    if referred_user_id:
        obs += f" user={referred_user_id[:8]}…"

    rows.append(
        {
            "data": payment_date[:10],
            "tipo": "DESPESA",
            "subtipo": "COMISSAO_INDICACAO",
            "categoria": categoria,
            "valor_rs": _format_br(amount_brl),
            "pago": "Não",
            "nota": f"stripe_id:{stripe_id}; {obs}",
        }
    )
    _write_registro(path, rows)

    try:
        refresh_finance_summary(finance_dir)
    except Exception:
        pass

    return {
        "recorded": True,
        "stripe_id": stripe_id,
        "valor_rs": amount_brl,
        "parceiro": partner_code,
    }


def sync_pending_commissions_to_finance() -> dict[str, Any]:
    """Espelha comissões `pending` do Supabase que ainda não estão no CSV."""
    from ego_api.referrals import get_admin_client

    client = get_admin_client()
    if not client:
        return {"ok": False, "error": "supabase_admin_ausente"}

    finance_dir = resolve_finance_dir()
    if not finance_dir:
        return {"ok": False, "error": "finance_dir_ausente"}

    comm = (
        client.table("referral_commissions")
        .select(
            "id, amount_cents, payout_month, created_at, referred_user_id, "
            "partner:referral_partners(code, display_name)"
        )
        .in_("status", ["pending", "paid"])
        .execute()
    )

    added = 0
    for row in comm.data or []:
        cid = str(row.get("id") or "")
        if not cid:
            continue
        partner = row.get("partner") or {}
        if isinstance(partner, list):
            partner = partner[0] if partner else {}
        code = partner.get("code") or "?"
        name = partner.get("display_name") or code
        cents = int(row.get("amount_cents") or 1000)
        created = (row.get("created_at") or "")[:10]
        if not created:
            created = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        month = row.get("payout_month") or created[:7]

        r = record_partner_commission_expense(
            commission_id=cid,
            partner_code=code,
            partner_name=name,
            amount_brl=cents / 100.0,
            payment_date=created,
            payout_month=str(month),
            referred_user_id=str(row.get("referred_user_id") or ""),
        )
        if r.get("recorded"):
            added += 1

    return {"ok": True, "added": added, "total": len(comm.data or [])}


def write_monthly_payout_files(month: str, finance_dir: Path | None = None) -> dict[str, Any]:
    """
    Gera em custo/financeiro/parceiros/:
    - repasses-YYYY-MM-detalhe.csv (cada indicação)
    - repasses-YYYY-MM-resumo.csv (total a repassar por parceiro)
    """
    from ego_api.referrals import commissions_report_csv, partner_payout_summary

    finance_dir = finance_dir or resolve_finance_dir()
    if not finance_dir:
        return {"ok": False, "error": "finance_dir_ausente"}

    detail_csv, err = commissions_report_csv(month)
    if err:
        return {"ok": False, "error": err}

    out_dir = finance_dir / "parceiros"
    out_dir.mkdir(parents=True, exist_ok=True)

    detail_path = out_dir / f"repasses-{month}-detalhe.csv"
    detail_path.write_text(detail_csv, encoding="utf-8-sig")

    summary, err2 = partner_payout_summary(month)
    if err2:
        return {"ok": False, "error": err2, "detail_path": str(detail_path)}

    resumo_path = out_dir / f"repasses-{month}-resumo.csv"
    fields = [
        "mes",
        "codigo_parceiro",
        "nome_parceiro",
        "email_parceiro",
        "pix_parceiro",
        "qtd_indicacoes",
        "total_repassar_brl",
        "status",
    ]
    with resumo_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter=";")
        w.writeheader()
        for row in summary:
            w.writerow(
                {
                    "mes": month,
                    "codigo_parceiro": row.get("code", ""),
                    "nome_parceiro": row.get("display_name", ""),
                    "email_parceiro": row.get("contact_email", ""),
                    "pix_parceiro": row.get("payout_pix", ""),
                    "qtd_indicacoes": str(row.get("count", 0)),
                    "total_repassar_brl": _format_br(float(row.get("total_brl", 0))),
                    "status": row.get("status", "pending"),
                }
            )

    total_geral = sum(float(r.get("total_brl", 0)) for r in summary)
    return {
        "ok": True,
        "month": month,
        "detail_path": str(detail_path),
        "resumo_path": str(resumo_path),
        "parceiros": len(summary),
        "total_repassar_brl": round(total_geral, 2),
    }
