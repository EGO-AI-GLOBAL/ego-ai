"""Envio de notificações push via Expo Push API."""

from __future__ import annotations

import logging

try:
    import requests
except ImportError:
    requests = None  # type: ignore[assignment]

_LOG = logging.getLogger(__name__)
_EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
_BATCH = 100


def _valid_expo_token(token: str) -> bool:
    t = (token or "").strip()
    return t.startswith("ExponentPushToken[") or t.startswith("ExpoPushToken[")


def send_expo_push(
    tokens: list[str],
    *,
    title: str,
    body: str,
    data: dict | None = None,
) -> int:
    """Devolve quantos tokens foram enviados (0 se falhar ou sem tokens)."""
    if not requests:
        return 0
    uniq = list(dict.fromkeys(t for t in tokens if _valid_expo_token(t)))
    if not uniq:
        return 0
    sent = 0
    payload_data = data or {}
    for i in range(0, len(uniq), _BATCH):
        batch = uniq[i : i + _BATCH]
        messages = [
            {
                "to": tok,
                "title": (title or "EGO-AI")[:200],
                "body": (body or "")[:500],
                "sound": "default",
                "data": payload_data,
            }
            for tok in batch
        ]
        try:
            res = requests.post(
                _EXPO_PUSH_URL,
                json=messages,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                timeout=15,
            )
            if res.status_code >= 400:
                _LOG.warning("Expo push HTTP %s: %s", res.status_code, res.text[:300])
            else:
                sent += len(batch)
        except Exception as exc:  # noqa: BLE001
            _LOG.warning("Expo push falhou: %s", exc)
    return sent
