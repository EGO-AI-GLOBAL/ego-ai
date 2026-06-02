"""
Lançamentos automáticos de despesas já conhecidas (idempotente).

Novas despesas: você informa → linha em registro-diario.csv
ou adicione aqui com chave única em `lancamento_auto:...`.
"""

from __future__ import annotations

from typing import Any

from ego_api.finance_revenue import (
    _format_br,
    _read_registro,
    _write_registro,
    resolve_finance_dir,
)

# Só incluir o que já foi pago ou confirmado. Não estimar Railway/Play/contador/marketing.
KNOWN_EXPENSES: list[dict[str, Any]] = [
    {
        "key": "dominio-uol-2026",
        "data": "2026-05-09",
        "tipo": "DESPESA",
        "subtipo": "FIXA",
        "categoria": "Domínio egoai.com.br",
        "valor_rs": 99.80,
        "pago": "Sim",
        "nota": "egoai.com.br 2 anos UOL",
    },
    {
        "key": "hospedagem-uol-2026",
        "data": "2026-05-28",
        "tipo": "DESPESA",
        "subtipo": "FIXA",
        "categoria": "Hospedagem site UOL",
        "valor_rs": 238.80,
        "pago": "Sim",
        "nota": "Site estático egoai.com.br — 1 ano",
    },
    {
        "key": "aiprog-2026-06",
        "data": "2026-06-03",
        "tipo": "DESPESA",
        "subtipo": "FIXA",
        "categoria": "AI-Prog.org",
        "valor_rs": 49.00,
        "pago": "Sim",
        "nota": "Ferramenta dev — mensal R$ 49",
    },
    {
        "key": "cursor-2026-06",
        "data": "2026-06-03",
        "tipo": "DESPESA",
        "subtipo": "FIXA",
        "categoria": "Cursor Pro",
        "valor_rs": 120.00,
        "pago": "Sim",
        "nota": "IDE + agente — ~US$ 20/mês (ajuste na fatura)",
    },
    {
        "key": "google-play-2026-06",
        "data": "2026-06-02",
        "tipo": "DESPESA",
        "subtipo": "FIXA",
        "categoria": "Google Play taxa desenvolvedor",
        "valor_rs": 137.50,
        "pago": "Sim",
        "nota": "US$ 25 taxa única conta desenvolvedor — não há mensalidade",
    },
]


def _marker(key: str) -> str:
    return f"lancamento_auto:{key}"


def _parse_val(s: str) -> float:
    t = (s or "").strip().replace("R$", "").replace(" ", "")
    if "," in t:
        t = t.replace(".", "").replace(",", ".") if "," in t and "." in t else t.replace(",", ".")
    return float(t) if t else 0.0


def _is_duplicate_row(row: dict[str, str], item: dict[str, Any]) -> bool:
    if (row.get("data") or "") != item["data"]:
        return False
    try:
        if abs(_parse_val(row.get("valor_rs", "")) - float(item["valor_rs"])) > 0.02:
            return False
    except ValueError:
        return False
    cat_row = (row.get("categoria") or "").lower()
    cat_item = str(item["categoria"]).lower()
    if cat_row == cat_item or cat_row in cat_item or cat_item in cat_row:
        return True
    keys = ("domínio", "dominio", "hospedagem", "cursor", "ai-prog", "aiprog")
    for k in keys:
        if k in cat_row and k in cat_item:
            return True
    return False


def _already_logged(rows: list[dict[str, str]], key: str) -> bool:
    needle = _marker(key)
    for row in rows:
        if needle in (row.get("nota") or ""):
            return True
    return False


def sync_known_expenses() -> dict[str, Any]:
    finance_dir = resolve_finance_dir()
    if not finance_dir:
        return {"ok": False, "error": "finance_dir_ausente"}

    path = finance_dir / "registro-diario.csv"
    rows = _read_registro(path) if path.exists() else []
    added: list[str] = []

    for item in KNOWN_EXPENSES:
        key = str(item["key"])
        if _already_logged(rows, key):
            continue
        # evita duplicar se já existe linha manual equivalente
        if any(_is_duplicate_row(row, item) for row in rows):
            continue

        rows.append(
            {
                "data": item["data"],
                "tipo": item["tipo"],
                "subtipo": item["subtipo"],
                "categoria": item["categoria"],
                "valor_rs": _format_br(float(item["valor_rs"])),
                "pago": item.get("pago", "Sim"),
                "nota": f"{_marker(key)}; {item.get('nota', '')}".strip(),
            }
        )
        added.append(key)

    if added:
        _write_registro(path, rows)

    return {"ok": True, "added": added, "total_known": len(KNOWN_EXPENSES)}
