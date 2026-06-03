"""
Receitas automáticas a partir do Stripe.

- Webhook grava em Supabase (`stripe_revenue_ledger`) — fonte na produção (Railway).
- Se `FINANCE_DIR` apontar para `custo/financeiro`, espelha em `registro-diario.csv`
  e recalcula `resumo-mensal.csv` + `receitas-assinantes.csv`.

Idempotência: cada pagamento usa `stripe_id` único (ex.: invoice:in_xxx).
"""

from __future__ import annotations

import csv
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ego_api.plans import (
    PLAN_CONNECTION,
    PLAN_ENTERPRISE,
    PLAN_ESSENTIAL,
    PLAN_PREMIUM,
    PLAN_PRICES_BRL,
    PLAN_TOTAL,
    normalize_plan_tier,
    stripe_object_to_tier,
)

TABLE_LEDGER = "stripe_revenue_ledger"

TIER_TO_PLANO_CSV: dict[str, str] = {
    PLAN_CONNECTION: "Conexão",
    PLAN_PREMIUM: "Premium",
    PLAN_TOTAL: "Total",
    PLAN_ENTERPRISE: "Empresa",
    PLAN_ESSENTIAL: "Essencial",
}


def resolve_finance_dir() -> Path | None:
    raw = (os.getenv("FINANCE_DIR") or "").strip()
    if raw:
        p = Path(raw).expanduser()
        if not p.is_absolute():
            p = Path.cwd() / p
        if p.is_dir():
            return p.resolve()
    for base in (Path.cwd(), Path(__file__).resolve().parents[1]):
        candidate = base / "custo" / "financeiro"
        if (candidate / "registro-diario.csv").exists():
            return candidate.resolve()
    return None


def _plano_label(tier: str) -> str:
    return TIER_TO_PLANO_CSV.get(normalize_plan_tier(tier), "Conexão")


def _format_br(value: float) -> str:
    return f"{abs(value):.2f}".replace(".", ",")


def _parse_br_decimal(s: str) -> float:
    s = (s or "").strip().replace("R$", "").replace(" ", "")
    if not s:
        return 0.0
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    return float(s)


def _read_registro(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def _write_registro(path: Path, rows: list[dict[str, str]]) -> None:
    fields = ["data", "tipo", "subtipo", "categoria", "valor_rs", "pago", "nota"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter=";")
        w.writeheader()
        w.writerows(rows)


def _stripe_id_in_registro(rows: list[dict[str, str]], stripe_id: str) -> bool:
    needle = f"stripe_id:{stripe_id}"
    for row in rows:
        if needle in (row.get("nota") or ""):
            return True
    return False


def _get_supabase_admin():
    url = (os.getenv("SUPABASE_URL") or "").strip()
    key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not url or not key:
        return None
    from supabase import create_client

    return create_client(url, key)


def _ledger_exists_supabase(supabase, stripe_id: str) -> bool:
    try:
        r = (
            supabase.table(TABLE_LEDGER)
            .select("stripe_id")
            .eq("stripe_id", stripe_id)
            .limit(1)
            .execute()
        )
        return bool(r.data)
    except Exception:
        return False


def _insert_ledger_supabase(
    supabase,
    *,
    stripe_id: str,
    payment_date: str,
    mes_aaaa_mm: str,
    plan_tier: str,
    valor_rs: float,
    tipo: str,
    user_id: str | None,
    obs: str,
    stripe_event_id: str | None,
) -> bool:
    row = {
        "stripe_id": stripe_id,
        "payment_date": payment_date,
        "mes_aaaa_mm": mes_aaaa_mm,
        "plan_tier": normalize_plan_tier(plan_tier),
        "plano_label": _plano_label(plan_tier),
        "valor_rs": round(valor_rs, 2),
        "tipo": tipo,
        "user_id": user_id,
        "obs": obs[:500] if obs else None,
        "stripe_event_id": stripe_event_id,
    }
    try:
        supabase.table(TABLE_LEDGER).insert(row).execute()
        return True
    except Exception as exc:
        msg = str(exc).lower()
        if "duplicate" in msg or "unique" in msg or "23505" in msg:
            return False
        raise


def _append_registro_csv(
    finance_dir: Path,
    *,
    payment_date: str,
    valor_rs: float,
    plano_label: str,
    stripe_id: str,
    tipo: str,
    obs: str,
) -> bool:
    path = finance_dir / "registro-diario.csv"
    rows = _read_registro(path) if path.exists() else []
    if _stripe_id_in_registro(rows, stripe_id):
        return False

    is_refund = tipo == "reembolso"
    rows.append(
        {
            "data": payment_date,
            "tipo": "DESPESA" if is_refund else "RECEITA",
            "subtipo": "REEMBOLSO" if is_refund else "ASSINATURA",
            "categoria": plano_label,
            "valor_rs": _format_br(valor_rs),
            "pago": "Sim",
            "nota": f"stripe_id:{stripe_id}; {obs}".strip(),
        }
    )
    _write_registro(path, rows)
    return True


def rebuild_receitas_assinantes(finance_dir: Path) -> None:
    """Agrega RECEITA/ASSINATURA do registro-diario em receitas-assinantes.csv."""
    registro = finance_dir / "registro-diario.csv"
    if not registro.exists():
        return

    agg: dict[str, dict[str, dict[str, float | int]]] = defaultdict(
        lambda: defaultdict(lambda: {"qtd": 0, "total": 0.0})
    )
    for row in _read_registro(registro):
        if (row.get("tipo") or "").upper() != "RECEITA":
            continue
        if (row.get("subtipo") or "").upper() != "ASSINATURA":
            continue
        data = (row.get("data") or "").strip()
        try:
            mes = datetime.strptime(data, "%Y-%m-%d").strftime("%Y-%m")
        except ValueError:
            continue
        plano = (row.get("categoria") or "Conexão").strip() or "Conexão"
        try:
            val = _parse_br_decimal(row.get("valor_rs", "0"))
        except ValueError:
            continue
        if val <= 0:
            continue
        agg[mes][plano]["qtd"] = int(agg[mes][plano]["qtd"]) + 1
        agg[mes][plano]["total"] = float(agg[mes][plano]["total"]) + val

    out_path = finance_dir / "receitas-assinantes.csv"
    fields = [
        "mes_aaaa_mm",
        "plano",
        "qtd_assinantes",
        "mensalidade_unit_rs",
        "receita_mensalidades_rs",
        "obs",
    ]
    rows_out: list[dict[str, str]] = []
    for mes in sorted(agg.keys()):
        for plano in sorted(agg[mes].keys()):
            qtd = int(agg[mes][plano]["qtd"])
            total = float(agg[mes][plano]["total"])
            unit = total / qtd if qtd else 0.0
            rows_out.append(
                {
                    "mes_aaaa_mm": mes,
                    "plano": plano,
                    "qtd_assinantes": str(qtd),
                    "mensalidade_unit_rs": _format_br(unit),
                    "receita_mensalidades_rs": _format_br(total),
                    "obs": "auto Stripe",
                }
            )

    if not rows_out:
        return

    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter=";")
        w.writeheader()
        w.writerows(rows_out)


def refresh_finance_summary(finance_dir: Path | None) -> None:
    if not finance_dir:
        return
    rebuild_receitas_assinantes(finance_dir)
    if (os.getenv("FINANCE_AUTO_RESUMO") or "true").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        import importlib.util

        script = finance_dir / "atualizar_resumo.py"
        if script.is_file():
            spec = importlib.util.spec_from_file_location("atualizar_resumo", script)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                mod.main()


def record_stripe_revenue(
    *,
    stripe_id: str,
    payment_date: str,
    amount_brl: float,
    plan_tier: str,
    tipo: str,
    user_id: str | None = None,
    obs: str = "",
    stripe_event_id: str | None = None,
) -> dict[str, Any]:
    """
    Grava receita (ou reembolso como DESPESA/REEMBOLSO).
    Retorna {recorded, storage, stripe_id, ...}.
    """
    if amount_brl <= 0 and tipo != "reembolso":
        return {"recorded": False, "reason": "valor_zero"}

    try:
        mes = datetime.strptime(payment_date, "%Y-%m-%d").strftime("%Y-%m")
    except ValueError:
        mes = datetime.now(timezone.utc).strftime("%Y-%m")

    plan_tier = normalize_plan_tier(plan_tier)
    plano_label = _plano_label(plan_tier)
    stored: list[str] = []
    recorded = False

    supabase = _get_supabase_admin()
    if supabase:
        if not _ledger_exists_supabase(supabase, stripe_id):
            if _insert_ledger_supabase(
                supabase,
                stripe_id=stripe_id,
                payment_date=payment_date,
                mes_aaaa_mm=mes,
                plan_tier=plan_tier,
                valor_rs=amount_brl,
                tipo=tipo,
                user_id=user_id,
                obs=obs,
                stripe_event_id=stripe_event_id,
            ):
                stored.append("supabase")
                recorded = True

    finance_dir = resolve_finance_dir()
    if finance_dir:
        if _append_registro_csv(
            finance_dir,
            payment_date=payment_date,
            valor_rs=amount_brl,
            plano_label=plano_label,
            stripe_id=stripe_id,
            tipo=tipo,
            obs=obs,
        ):
            stored.append("csv")
            recorded = True
        try:
            refresh_finance_summary(finance_dir)
        except Exception:
            pass

    if not recorded and not stored:
        if supabase and _ledger_exists_supabase(supabase, stripe_id):
            return {"recorded": False, "reason": "duplicate", "stripe_id": stripe_id}
        finance_dir_s = str(finance_dir) if finance_dir else None
        return {
            "recorded": False,
            "reason": "no_storage",
            "stripe_id": stripe_id,
            "finance_dir": finance_dir_s,
        }

    return {
        "recorded": recorded,
        "storage": stored,
        "stripe_id": stripe_id,
        "mes": mes,
        "valor_rs": amount_brl,
        "plano": plano_label,
    }


def _ts_to_date(ts: int | None) -> str:
    if not ts:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")


def _amount_brl_from_cents(cents: int | None) -> float:
    return round((int(cents or 0)) / 100.0, 2)


def _tier_from_invoice(invoice: dict) -> str:
    meta = invoice.get("metadata") or {}
    for key in ("plan_tier", "plan", "tier"):
        if meta.get(key):
            return normalize_plan_tier(str(meta[key]))

    lines = (invoice.get("lines") or {}).get("data") or []
    for line in lines:
        price = (line or {}).get("price") or {}
        pid = str(price.get("id") or "")
        prod = str(price.get("product") or "")
        tier = stripe_object_to_tier(price_id=pid, product_id=prod)
        if tier:
            return tier
        amount = _amount_brl_from_cents((line or {}).get("amount") or price.get("unit_amount"))
        for t, p in PLAN_PRICES_BRL.items():
            if t != PLAN_ESSENTIAL and abs(amount - p) < 0.02:
                return t

    sub_details = (invoice.get("subscription_details") or {}).get("metadata") or {}
    if sub_details.get("plan_tier"):
        return normalize_plan_tier(str(sub_details["plan_tier"]))

    return PLAN_CONNECTION


def _user_id_from_invoice(invoice: dict) -> str | None:
    meta = invoice.get("metadata") or {}
    for key in ("user_id", "supabase_user_id"):
        if meta.get(key):
            return str(meta[key])
    sub_meta = (invoice.get("subscription_details") or {}).get("metadata") or {}
    if sub_meta.get("user_id"):
        return str(sub_meta["user_id"])
    sub = invoice.get("subscription")
    if isinstance(sub, dict):
        sm = sub.get("metadata") or {}
        if sm.get("user_id"):
            return str(sm["user_id"])
    return None


def _maybe_expand_invoice(invoice: dict) -> dict:
    inv_id = str(invoice.get("id") or "")
    if not inv_id:
        return invoice
    lines = (invoice.get("lines") or {}).get("data") or []
    if lines:
        return invoice
    key = (os.getenv("STRIPE_SECRET_KEY") or "").strip()
    if not key:
        return invoice
    try:
        import stripe

        stripe.api_key = key
        full = stripe.Invoice.retrieve(
            inv_id,
            expand=["lines.data.price.product", "subscription"],
        )
        return dict(full)
    except Exception:
        return invoice


def record_invoice_paid(invoice: dict, *, stripe_event_id: str | None = None) -> dict[str, Any]:
    invoice = _maybe_expand_invoice(invoice)
    inv_id = str(invoice.get("id") or "")
    if not inv_id:
        return {"recorded": False, "reason": "sem_invoice_id"}

    currency = str(invoice.get("currency") or "brl").lower()
    amount = _amount_brl_from_cents(invoice.get("amount_paid"))
    if currency != "brl":
        amount = _amount_brl_from_cents(invoice.get("amount_paid"))

    paid_at = (invoice.get("status_transitions") or {}).get("paid_at")
    payment_date = _ts_to_date(paid_at or invoice.get("created"))

    billing = str(invoice.get("billing_reason") or "subscription_cycle")
    tipo_map = {
        "subscription_create": "nova_assinatura",
        "subscription_cycle": "renovacao",
        "subscription_update": "atualizacao",
    }
    tipo = tipo_map.get(billing, "pagamento")

    tier = _tier_from_invoice(invoice)
    user_id = _user_id_from_invoice(invoice)

    return record_stripe_revenue(
        stripe_id=f"invoice:{inv_id}",
        payment_date=payment_date,
        amount_brl=amount,
        plan_tier=tier,
        tipo=tipo,
        user_id=user_id,
        obs=f"Stripe invoice {inv_id} ({billing})",
        stripe_event_id=stripe_event_id,
    )


def _tier_from_checkout_session(session: dict) -> str:
    meta = session.get("metadata") or {}
    for key in ("plan_tier", "plan", "tier"):
        if meta.get(key):
            return normalize_plan_tier(str(meta[key]))

    line_items = session.get("line_items") or {}
    if isinstance(line_items, dict):
        for item in line_items.get("data") or []:
            price = (item or {}).get("price") or {}
            pid = str(price.get("id") or "")
            prod = str(price.get("product") or (item or {}).get("product") or "")
            tier = stripe_object_to_tier(price_id=pid, product_id=prod)
            if tier:
                return tier

    if str(session.get("mode") or "") == "subscription":
        return PLAN_CONNECTION
    return PLAN_CONNECTION


def record_checkout_completed(
    session: dict, *, stripe_event_id: str | None = None
) -> dict[str, Any]:
    """Pagamento único (mode=payment). Assinaturas usam invoice.paid."""
    mode = str(session.get("mode") or "")
    if mode == "subscription":
        return {"recorded": False, "reason": "subscription_use_invoice"}

    session_id = str(session.get("id") or "")
    if not session_id:
        return {"recorded": False, "reason": "sem_session_id"}

    amount = _amount_brl_from_cents(session.get("amount_total"))
    if amount <= 0:
        return {"recorded": False, "reason": "valor_zero"}

    tier = _tier_from_checkout_session(session)
    user_id = str(session.get("client_reference_id") or "") or None
    created = session.get("created")
    payment_date = _ts_to_date(created)

    return record_stripe_revenue(
        stripe_id=f"checkout:{session_id}",
        payment_date=payment_date,
        amount_brl=amount,
        plan_tier=tier,
        tipo="pagamento_unico",
        user_id=user_id,
        obs=f"Stripe checkout {session_id}",
        stripe_event_id=stripe_event_id,
    )


def record_charge_refunded(charge: dict, *, stripe_event_id: str | None = None) -> dict[str, Any]:
    charge_id = str(charge.get("id") or "")
    if not charge_id:
        return {"recorded": False, "reason": "sem_charge_id"}

    amount = _amount_brl_from_cents(charge.get("amount_refunded"))
    if amount <= 0:
        return {"recorded": False, "reason": "sem_reembolso"}

    created = charge.get("created")
    payment_date = _ts_to_date(created)

    meta = charge.get("metadata") or {}
    tier = normalize_plan_tier(str(meta.get("plan_tier") or PLAN_CONNECTION))

    return record_stripe_revenue(
        stripe_id=f"refund:{charge_id}",
        payment_date=payment_date,
        amount_brl=amount,
        plan_tier=tier,
        tipo="reembolso",
        user_id=meta.get("user_id"),
        obs=f"Reembolso Stripe charge {charge_id}",
        stripe_event_id=stripe_event_id,
    )


def sync_supabase_ledger_to_csv(finance_dir: Path | None = None) -> dict[str, Any]:
    """Baixa ledger Supabase → registro-diario (idempotente) e recalcula resumo."""
    finance_dir = finance_dir or resolve_finance_dir()
    if not finance_dir:
        return {"ok": False, "error": "FINANCE_DIR não encontrado"}

    supabase = _get_supabase_admin()
    if not supabase:
        return {"ok": False, "error": "SUPABASE_SERVICE_ROLE_KEY ausente"}

    try:
        r = (
            supabase.table(TABLE_LEDGER)
            .select("*")
            .order("payment_date")
            .execute()
        )
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

    added = 0
    for row in r.data or []:
        stripe_id = str(row.get("stripe_id") or "")
        if not stripe_id:
            continue
        tipo = str(row.get("tipo") or "pagamento")
        plano = str(row.get("plano_label") or _plano_label(str(row.get("plan_tier") or "")))
        payment_date = str(row.get("payment_date") or "")[:10]
        try:
            valor = float(row.get("valor_rs") or 0)
        except (TypeError, ValueError):
            valor = 0.0
        obs = str(row.get("obs") or "sync Supabase")
        if _append_registro_csv(
            finance_dir,
            payment_date=payment_date,
            valor_rs=valor,
            plano_label=plano,
            stripe_id=stripe_id,
            tipo=tipo if tipo == "reembolso" else "renovacao",
            obs=obs,
        ):
            added += 1

    refresh_finance_summary(finance_dir)
    return {"ok": True, "added": added, "total_ledger": len(r.data or [])}
