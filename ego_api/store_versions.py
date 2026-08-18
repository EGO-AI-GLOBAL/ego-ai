"""Versões publicadas nas lojas (App Store + Play) — banner de atualização automático.

iOS: iTunes Lookup (oficial).
Android: página pública da Play (versionName).

Cache em memória (TTL) para não bater nas lojas em cada /health.
"""
from __future__ import annotations

import json
import logging
import re
import ssl
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

IOS_APP_ID = "6780595396"
ANDROID_PACKAGE = "com.egoai.app"
CACHE_TTL_SEC = 15 * 60
HTTP_TIMEOUT_SEC = 8

# App Store Connect da 1.0.112 ficou com o NOME da versão = build iOS (118).
# Sem isto o banner compara 1.0.112 instalado vs 1.0.118 na loja e nunca some.
IOS_STORE_VERSION_ALIASES = {
    "1.0.117": "1.0.112",
    "1.0.118": "1.0.112",
}

_lock = threading.Lock()
_cache: "_StoreCache | None" = None
_refreshing = False


@dataclass
class StoreVersions:
    ios: str = ""
    android: str = ""
    fetched_at: float = 0.0
    ios_ok: bool = False
    android_ok: bool = False


@dataclass
class _StoreCache:
    versions: StoreVersions
    expires_at: float


def _ssl_ctx(*, insecure: bool = False) -> ssl.SSLContext:
    if insecure:
        return ssl._create_unverified_context()
    ctx = ssl.create_default_context()
    try:
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
    except Exception:
        pass
    return ctx


def _http_get(url: str, *, headers: dict[str, str] | None = None) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (compatible; EGO-AI-StoreVersions/1.0; +https://egoai.com.br)"
            ),
            "Accept": "*/*",
            **(headers or {}),
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(
            req, timeout=HTTP_TIMEOUT_SEC, context=_ssl_ctx()
        ) as resp:
            return resp.read()
    except urllib.error.URLError as exc:
        # Alguns ambientes Windows/Python falham no verify CA; Railway Linux OK.
        msg = str(exc).lower()
        if "certificate" not in msg and "ssl" not in msg:
            raise
        with urllib.request.urlopen(
            req, timeout=HTTP_TIMEOUT_SEC, context=_ssl_ctx(insecure=True)
        ) as resp:
            return resp.read()


def parse_ios_lookup_payload(raw: bytes | str) -> str:
    """Extrai `version` do JSON do iTunes Lookup."""
    if isinstance(raw, bytes):
        text = raw.decode("utf-8", "replace")
    else:
        text = raw
    data = json.loads(text)
    results = data.get("results") or []
    if not results:
        return ""
    ver = str(results[0].get("version") or "").strip()
    return ver if _looks_like_version(ver) else ""


def parse_play_html_version(html: str) -> str:
    """Extrai versionName do HTML público da Play Store."""
    if not html:
        return ""

    # Padrões comuns no HTML embutido (AF_initData / ds: datasets).
    patterns = (
        r'\[\[\["(\d+\.\d+\.\d+(?:\.\d+)?)"\]\]',
        r'"softwareVersion"\s*:\s*"(\d+\.\d+\.\d+(?:\.\d+)?)"',
        r"\[\[\[[\"'](\d+\.\d+\.\d+(?:\.\d+)?)[\"']\]\]",
        r">Versão</[^>]*>[\s\S]*?>(\d+\.\d+\.\d+(?:\.\d+)?)<",
        r">Current Version</[^>]*>[\s\S]*?>(\d+\.\d+\.\d+(?:\.\d+)?)<",
    )
    candidates: list[str] = []
    for pat in patterns:
        for m in re.finditer(pat, html, flags=re.IGNORECASE):
            ver = (m.group(1) or "").strip()
            if _looks_like_version(ver):
                candidates.append(ver)

    if not candidates:
        return ""

    # Preferir a maior versão semântica encontrada (ruído no HTML).
    best = candidates[0]
    for ver in candidates[1:]:
        if _version_gt(ver, best):
            best = ver
    return best


def _looks_like_version(raw: str) -> bool:
    return bool(re.fullmatch(r"\d+(?:\.\d+){1,3}", (raw or "").strip()))


def _parse_parts(raw: str) -> list[int]:
    parts: list[int] = []
    for p in (raw or "").strip().split("."):
        try:
            parts.append(int(re.sub(r"\D", "", p) or "0"))
        except ValueError:
            parts.append(0)
    return parts


def _version_gt(a: str, b: str) -> bool:
    """True se a > b (semver simples)."""
    left = _parse_parts(a)
    right = _parse_parts(b)
    n = max(len(left), len(right))
    for i in range(n):
        x = left[i] if i < len(left) else 0
        y = right[i] if i < len(right) else 0
        if x > y:
            return True
        if x < y:
            return False
    return False


def normalize_ios_store_version(ios: str, android: str = "") -> str:
    """Corrige versionName iOS quando o Connect usou o build number."""
    ios = (ios or "").strip()
    if not ios:
        return ""
    aliased = IOS_STORE_VERSION_ALIASES.get(ios)
    if aliased:
        return aliased
    andr = (android or "").strip()
    if (
        _looks_like_version(ios)
        and _looks_like_version(andr)
        and _version_gt(ios, andr)
    ):
        ios_parts = _parse_parts(ios)
        and_parts = _parse_parts(andr)
        # 1.0.118 vs 1.0.111: patch iOS parece CFBundleVersion, não marketing.
        if (
            len(ios_parts) >= 3
            and len(and_parts) >= 3
            and ios_parts[0] == and_parts[0]
            and ios_parts[1] == and_parts[1]
            and ios_parts[2] >= 115
            and ios_parts[2] - and_parts[2] >= 5
        ):
            return andr
    return ios


def max_version(*versions: str) -> str:
    best = ""
    for v in versions:
        v = (v or "").strip()
        if not _looks_like_version(v):
            continue
        if not best or _version_gt(v, best):
            best = v
    return best


def fetch_ios_version(*, app_id: str = IOS_APP_ID, country: str = "br") -> str:
    url = f"https://itunes.apple.com/lookup?id={app_id}&country={country}"
    raw = _http_get(url, headers={"Accept": "application/json"})
    return parse_ios_lookup_payload(raw)


def fetch_android_version(*, package: str = ANDROID_PACKAGE) -> str:
    url = (
        f"https://play.google.com/store/apps/details?id={package}&hl=pt&gl=BR"
    )
    raw = _http_get(url, headers={"Accept-Language": "pt-BR,pt;q=0.9"})
    html = raw.decode("utf-8", "replace")
    return parse_play_html_version(html)


def _fetch_both() -> StoreVersions:
    ios = ""
    android = ""
    ios_ok = False
    android_ok = False
    try:
        ios = fetch_ios_version()
        ios_ok = bool(ios)
    except Exception as exc:
        logger.warning("store_versions ios fetch failed: %s", exc)
    try:
        android = fetch_android_version()
        android_ok = bool(android)
    except Exception as exc:
        logger.warning("store_versions android fetch failed: %s", exc)
    if ios:
        ios = normalize_ios_store_version(ios, android)
    return StoreVersions(
        ios=ios,
        android=android,
        fetched_at=time.time(),
        ios_ok=ios_ok,
        android_ok=android_ok,
    )


def _merge_with_previous(fresh: StoreVersions, prev: StoreVersions | None) -> StoreVersions:
    if prev is None:
        return fresh
    return StoreVersions(
        ios=fresh.ios if fresh.ios_ok else prev.ios,
        android=fresh.android if fresh.android_ok else prev.android,
        fetched_at=fresh.fetched_at,
        ios_ok=fresh.ios_ok or (bool(prev.ios) and prev.ios_ok),
        android_ok=fresh.android_ok or (bool(prev.android) and prev.android_ok),
    )


def refresh_store_versions(*, force: bool = False) -> StoreVersions:
    """Actualiza o cache (síncrono)."""
    global _cache
    with _lock:
        prev = _cache.versions if _cache else None
        if (
            not force
            and _cache is not None
            and time.time() < _cache.expires_at
        ):
            return _cache.versions

    fresh = _fetch_both()
    merged = _merge_with_previous(fresh, prev)
    with _lock:
        _cache = _StoreCache(
            versions=merged,
            expires_at=time.time() + CACHE_TTL_SEC,
        )
    return merged


def _background_refresh() -> None:
    global _refreshing
    try:
        refresh_store_versions(force=True)
    finally:
        with _lock:
            _refreshing = False


def get_store_versions(*, allow_network: bool = True) -> StoreVersions:
    """Devolve versões em cache; se expirado, devolve stale e refresca em background.

    Sem cache: fetch síncrono (1.ª chamada /health após deploy).
    """
    global _refreshing
    now = time.time()
    with _lock:
        cached = _cache
        refreshing = _refreshing

    if cached is not None and now < cached.expires_at:
        return cached.versions

    if cached is not None:
        # Stale: servir já e refrescar em background.
        if allow_network and not refreshing:
            with _lock:
                if not _refreshing:
                    _refreshing = True
                    threading.Thread(
                        target=_background_refresh,
                        name="ego-store-versions",
                        daemon=True,
                    ).start()
        return cached.versions

    if not allow_network:
        return StoreVersions()

    return refresh_store_versions(force=True)


def store_versions_status() -> dict[str, Any]:
    with _lock:
        cached = _cache
    if not cached:
        return {"cached": False, "ttl_sec": CACHE_TTL_SEC}
    v = cached.versions
    return {
        "cached": True,
        "ttl_sec": CACHE_TTL_SEC,
        "expires_in_sec": max(0, int(cached.expires_at - time.time())),
        "ios": v.ios,
        "android": v.android,
        "ios_ok": v.ios_ok,
        "android_ok": v.android_ok,
        "fetched_at": v.fetched_at,
    }
