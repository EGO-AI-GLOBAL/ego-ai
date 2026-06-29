"""Guard Play Integrity nas rotas caras (chat, voz, TTS)."""

from __future__ import annotations

import logging
from functools import wraps
from typing import Any, Callable

from flask import jsonify, request

_LOG = logging.getLogger("ego.integrity")


def _client_platform() -> str:
    return (request.headers.get("X-EGO-Platform") or "").strip().lower()


def play_integrity_applies() -> bool:
    """Só Android explícito (header X-EGO-Platform). Legacy sem header = não bloquear."""
    from ego_api.play_integrity import play_integrity_enabled

    if not play_integrity_enabled():
        return False
    platform = _client_platform()
    return platform == "android"


def evaluate_request_integrity() -> tuple[bool, str, bool]:
    """
    Retorna (permitir_pedido, motivo, bloqueou).
    monitor = regista falha mas permite; enforce = bloqueia.
    """
    from ego_api.play_integrity import (
        play_integrity_enforced,
        play_integrity_mode,
        verify_integrity_token,
    )

    if not play_integrity_applies():
        return True, "skipped", False

    token = (request.headers.get("X-Play-Integrity") or "").strip()

    # Modo monitor: não chamar Google em cada pedido (só Android). Evita atrasos
    # no chat enquanto iOS/web seguem sem este passo.
    if not play_integrity_enforced():
        if token:
            _LOG.info("play_integrity monitor token_present route=%s", request.path)
        else:
            _LOG.warning(
                "play_integrity monitor token_missing route=%s", request.path
            )
        return True, "monitor_skip", False

    ok, reason = verify_integrity_token(token)
    if ok:
        _LOG.info("play_integrity ok route=%s", request.path)
        return True, reason, False

    enforced = play_integrity_enforced()
    level = "error" if enforced else "warning"
    _LOG.log(
        level,
        "play_integrity fail mode=%s route=%s reason=%s",
        play_integrity_mode(),
        request.path,
        reason,
    )
    if enforced:
        return False, reason, True
    return True, reason, False


def require_play_integrity(f: Callable) -> Callable:
    @wraps(f)
    def wrapper(*args: Any, **kwargs: Any):
        allow, reason, blocked = evaluate_request_integrity()
        if blocked:
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": (
                            "App não verificado. Instale pela Play Store oficial "
                            "e actualize para a versão mais recente."
                        ),
                        "integrity_reason": reason,
                    }
                ),
                403,
            )
        if not allow:
            return jsonify({"ok": False, "error": "Integridade do app recusada."}), 403
        return f(*args, **kwargs)

    return wrapper
