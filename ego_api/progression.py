"""Cap global de níveis/tiers — 500 inicial, +500 ao chegar em cap-50 (450, 950…)."""

from __future__ import annotations

import datetime

from ego_api.config import read_env

try:
    from ego_supabase import Client
except ImportError:
    from supabase import Client  # type: ignore[assignment]

TABLE = "ego_progression_caps"
BASE_CAP = 500
EXPAND_BUFFER = 50
EXPAND_STEP = 500

_KIND_ENV: dict[str, str] = {
    "daily_care": "EGO_DAILY_CARE_MAX_TIERS",
    "wellness_journey": "EGO_JOURNEY_MAX_LEVELS",
}

_KIND_ROW: dict[str, str] = {
    "daily_care": "daily_care_tiers",
    "wellness_journey": "wellness_journey_levels",
}

# Cache por processo (Railway) — evita round-trip em cada request.
_cache: dict[str, int] = {}


def _default_cap(kind: str) -> int:
    env_name = _KIND_ENV.get(kind, "")
    raw = read_env(env_name, str(BASE_CAP)) if env_name else str(BASE_CAP)
    try:
        return max(BASE_CAP, int(raw))
    except ValueError:
        return BASE_CAP


def _admin_client() -> Client | None:
    try:
        from ego_api.supabase_client import create_service_client

        return create_service_client()
    except Exception:
        return None


def get_cap(supabase: Client | None, kind: str) -> int:
    if kind in _cache:
        return _cache[kind]
    row_key = _KIND_ROW.get(kind, kind)
    client = _admin_client() or supabase
    if client:
        try:
            res = (
                client.table(TABLE)
                .select("cap")
                .eq("key", row_key)
                .limit(1)
                .execute()
            )
            rows = res.data or []
            if rows:
                cap = max(BASE_CAP, int(rows[0].get("cap") or BASE_CAP))
                _cache[kind] = cap
                return cap
        except Exception as exc:
            print(f"[EGO] progression get_cap({kind}) fallback: {exc}", flush=True)
    cap = _default_cap(kind)
    _cache[kind] = cap
    return cap


def _persist_cap(kind: str, cap: int) -> None:
    row_key = _KIND_ROW.get(kind, kind)
    client = _admin_client()
    if not client:
        return
    try:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        client.table(TABLE).upsert(
            {"key": row_key, "cap": cap, "updated_at": now},
            on_conflict="key",
        ).execute()
    except Exception as exc:
        print(f"[EGO] progression persist_cap({kind}) error: {exc}", flush=True)


def maybe_expand_cap(supabase: Client | None, kind: str, user_value: int) -> int:
    """Se user_value >= cap-50, acrescenta 500 ao teto global."""
    val = max(0, int(user_value or 0))
    cap = get_cap(supabase, kind)
    threshold = cap - EXPAND_BUFFER
    if val < threshold:
        return cap
    new_cap = cap + EXPAND_STEP
    while val >= new_cap - EXPAND_BUFFER:
        new_cap += EXPAND_STEP
    if new_cap > cap:
        _cache[kind] = new_cap
        _persist_cap(kind, new_cap)
        print(
            f"[EGO] progression expanded {kind}: {cap} -> {new_cap} (user={val})",
            flush=True,
        )
    return _cache.get(kind, new_cap)


# Emojis/nomes para tiers do Desafio Diário (1..N).
_TIER_EMOJIS = ("🌱", "💪", "🔥", "⭐", "👑", "💜", "✨", "🏆", "🎯", "🌟")
_TIER_NAMES = (
    "Iniciante",
    "Firme",
    "Forte",
    "Mestre",
    "Lenda",
    "Guardião",
    "Campeão",
    "Ícone",
    "Luz",
    "Eterno",
)


def daily_tier_from_days(days: int, cap: int) -> int:
    """1 tier por dia de streak, até ao teto global."""
    d = max(0, int(days or 0))
    if d <= 0:
        return 0
    return min(d, cap)


def daily_tier_meta(tier: int) -> tuple[str, str]:
    if tier <= 0:
        return "🌱", "Comece hoje"
    i = (tier - 1) % len(_TIER_EMOJIS)
    name = _TIER_NAMES[i] if tier <= 30 else f"Nível {tier}"
    return _TIER_EMOJIS[i], name


def daily_ladder_window(current_tier: int, cap: int, window: int = 5) -> list[dict]:
    """Janela de tiers para UI (não envia os 500 de uma vez)."""
    if current_tier <= 0:
        milestones = [1, 2, 3, 4, 5]
    else:
        start = max(1, current_tier - 2)
        end = min(cap, start + window - 1)
        if end - start < window - 1:
            start = max(1, end - window + 1)
        milestones = list(range(start, end + 1))
    out: list[dict] = []
    for t in milestones:
        emoji, label = daily_tier_meta(t)
        out.append(
            {
                "min_days": t,
                "tier": t,
                "emoji": emoji,
                "label": label,
                "reached": current_tier >= t,
            }
        )
    return out
