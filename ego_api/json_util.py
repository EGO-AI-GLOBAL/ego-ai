"""Valores seguros para respostas JSON (Flask jsonify)."""

from __future__ import annotations

import datetime
import uuid
from decimal import Decimal
from typing import Any


def sanitize_for_json(value: Any) -> Any:
    """Converte UUID, datetime, Decimal, etc. em tipos JSON-serializáveis."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {str(k): sanitize_for_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize_for_json(v) for v in value]
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)
