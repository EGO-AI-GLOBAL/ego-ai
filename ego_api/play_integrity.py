"""Verificação Play Integrity (Android) no servidor."""

from __future__ import annotations

import json
import os
import time
from typing import Any

import httpx

from ego_api.config import read_env

_SCOPES = ("https://www.googleapis.com/auth/playintegrity",)


def play_integrity_enabled() -> bool:
    return read_env("EGO_PLAY_INTEGRITY", "0").lower() in ("1", "true", "yes", "sim")


def play_integrity_mode() -> str:
    """monitor = regista falhas; enforce = bloqueia pedido."""
    return read_env("EGO_PLAY_INTEGRITY_MODE", "monitor").lower()


def play_integrity_enforced() -> bool:
    return play_integrity_enabled() and play_integrity_mode() == "enforce"


def android_package_name() -> str:
    return read_env("ANDROID_PACKAGE_NAME", "com.egoai.app")


def google_cloud_project_number() -> str:
    return read_env("GOOGLE_CLOUD_PROJECT_NUMBER")


def server_configured() -> bool:
    return bool(google_cloud_project_number() and _service_account_info())


def status_payload() -> dict[str, Any]:
    return {
        "enabled": play_integrity_enabled(),
        "mode": play_integrity_mode(),
        "server_configured": server_configured(),
        "package_name": android_package_name(),
        "project_number": google_cloud_project_number() or None,
    }


def _service_account_info() -> dict[str, Any] | None:
    raw = read_env("GOOGLE_SERVICE_ACCOUNT_JSON")
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None
    path = read_env("GOOGLE_APPLICATION_CREDENTIALS")
    if path and os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, json.JSONDecodeError):
            return None
    return None


def _google_access_token() -> str:
    info = _service_account_info()
    if not info:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON ou GOOGLE_APPLICATION_CREDENTIALS em falta.")

    try:
        from google.auth.transport.requests import Request as GoogleAuthRequest
        from google.oauth2 import service_account
    except ImportError as exc:
        raise RuntimeError("Instale google-auth no servidor (requirements-api.txt).") from exc

    creds = service_account.Credentials.from_service_account_info(info, scopes=_SCOPES)
    creds.refresh(GoogleAuthRequest())
    token = creds.token
    if not token:
        raise RuntimeError("Falha ao obter token Google para Play Integrity.")
    return token


def decode_integrity_token(integrity_token: str) -> dict[str, Any]:
    package = android_package_name()
    access = _google_access_token()
    url = f"https://playintegrity.googleapis.com/v1/{package}:decodeIntegrityToken"
    with httpx.Client(timeout=25.0) as client:
        response = client.post(
            url,
            json={"integrityToken": integrity_token},
            headers={"Authorization": f"Bearer {access}"},
        )
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict):
            raise ValueError("Resposta Play Integrity inválida.")
        return body


def evaluate_verdict(payload: dict[str, Any]) -> tuple[bool, str]:
    external = payload.get("tokenPayloadExternal") or {}
    if not isinstance(external, dict):
        return False, "payload_invalid"

    request_details = external.get("requestDetails") or {}
    app_integrity = external.get("appIntegrity") or {}
    device_integrity = external.get("deviceIntegrity") or {}

    pkg = str(request_details.get("requestPackageName") or "").strip()
    if pkg and pkg != android_package_name():
        return False, "package_mismatch"

    ts_raw = request_details.get("timestampMillis")
    try:
        ts_ms = int(ts_raw)
    except (TypeError, ValueError):
        ts_ms = 0
    if ts_ms:
        age_ms = abs(int(time.time() * 1000) - ts_ms)
        if age_ms > 10 * 60 * 1000:
            return False, "token_stale"

    verdict = str(app_integrity.get("appRecognitionVerdict") or "").strip()
    strict_app = read_env("EGO_PLAY_INTEGRITY_STRICT_APP", "0").lower() in (
        "1",
        "true",
        "yes",
        "sim",
    )
    allowed_app = {"PLAY_RECOGNIZED"} if strict_app else {"PLAY_RECOGNIZED", "UNRECOGNIZED_VERSION"}
    if verdict not in allowed_app:
        return False, f"app_{verdict or 'unknown'}"

    device_verdicts = device_integrity.get("deviceRecognitionVerdict") or []
    if not isinstance(device_verdicts, list):
        device_verdicts = []
    if not device_verdicts:
        return False, "device_unknown"

    require_device = read_env("EGO_PLAY_INTEGRITY_REQUIRE_DEVICE", "0").lower() in (
        "1",
        "true",
        "yes",
        "sim",
    )
    if require_device:
        if "MEETS_DEVICE_INTEGRITY" not in device_verdicts:
            return False, "device_integrity_failed"

    return True, "ok"


def verify_integrity_token(integrity_token: str) -> tuple[bool, str]:
    token = (integrity_token or "").strip()
    if not token:
        return False, "token_missing"
    if not server_configured():
        return False, "server_not_configured"
    try:
        decoded = decode_integrity_token(token)
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code if exc.response is not None else 0
        return False, f"decode_http_{code}"
    except Exception as exc:  # noqa: BLE001
        return False, f"decode_failed:{type(exc).__name__}"
    return evaluate_verdict(decoded)
