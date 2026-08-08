"""Monstrinhos — loja de sementes (catálogo base + rotação semanal)."""

from __future__ import annotations

import datetime
import hashlib

from ego_api.schedule_tz import local_now_from_session
from ego_api.request_ctx import get_session

# Catálogo permanente — sempre visível até comprar.
SHOP_BASE_ITEMS: list[dict[str, str | int]] = [
    {"id": "mushroom", "emoji": "🍄", "label": "Cogumelo", "price": 6},
    {"id": "lantern", "emoji": "🏮", "label": "Lanterna", "price": 8},
    {"id": "bench", "emoji": "🪑", "label": "Banco", "price": 10},
    {"id": "birdhouse", "emoji": "🪺", "label": "Ninho", "price": 12},
    {"id": "windmill", "emoji": "🎡", "label": "Moinho", "price": 15},
    {"id": "stone_path", "emoji": "🪨", "label": "Trilha de pedras", "price": 9},
    {"id": "pond", "emoji": "🐸", "label": "Lagoa", "price": 11},
    {"id": "swing", "emoji": "🛝", "label": "Balanço", "price": 13},
    {"id": "totem", "emoji": "🗿", "label": "Totem calmo", "price": 14},
    {"id": "scarecrow", "emoji": "🎃", "label": "Espantalho", "price": 16},
]

# Pool de rotação — 8 itens/semana; renova às segundas (fuso do utilizador).
SHOP_ROTATING_POOL: list[dict[str, str | int]] = [
    {"id": "crystal", "emoji": "💎", "label": "Cristal", "price": 12},
    {"id": "campfire", "emoji": "🔥", "label": "Fogueira", "price": 10},
    {"id": "hammock", "emoji": "🏕️", "label": "Rede", "price": 14},
    {"id": "telescope", "emoji": "🔭", "label": "Luneta", "price": 16},
    {"id": "kite", "emoji": "🪁", "label": "Pipa", "price": 11},
    {"id": "sundial", "emoji": "⏳", "label": "Relógio solar", "price": 13},
    {"id": "beehive", "emoji": "🐝", "label": "Colmeia", "price": 12},
    {"id": "snail", "emoji": "🐌", "label": "Caracol", "price": 8},
    {"id": "ladybug", "emoji": "🐞", "label": "Joaninha", "price": 7},
    {"id": "owl", "emoji": "🦉", "label": "Coruja", "price": 15},
    {"id": "hedgehog", "emoji": "🦔", "label": "Ouriço", "price": 14},
    {"id": "fox", "emoji": "🦊", "label": "Raposa", "price": 17},
    {"id": "leaf_circle", "emoji": "🍃", "label": "Círculo de folhas", "price": 9},
    {"id": "star_jar", "emoji": "⭐", "label": "Pote de estrelas", "price": 18},
    {"id": "moon_lamp", "emoji": "🌙", "label": "Lamparina", "price": 13},
    {"id": "sunflower", "emoji": "🌻", "label": "Girassol", "price": 10},
    {"id": "cactus", "emoji": "🌵", "label": "Cacto", "price": 9},
    {"id": "bamboo", "emoji": "🎋", "label": "Bambu", "price": 11},
    {"id": "bridge", "emoji": "🌉", "label": "Ponte", "price": 16},
    {"id": "waterfall", "emoji": "💦", "label": "Cascata", "price": 19},
    {"id": "golden_nest", "emoji": "🪹", "label": "Ninho dourado", "price": 15},
    {"id": "shell", "emoji": "🐚", "label": "Concha", "price": 8},
    {"id": "gem_tree", "emoji": "🌴", "label": "Árvore de gemas", "price": 20},
    {"id": "happy_cloud", "emoji": "☁️", "label": "Nuvem feliz", "price": 12},
]

SHOP_ROTATION_COUNT = 8
SHOP_ITEMS = SHOP_BASE_ITEMS + SHOP_ROTATING_POOL  # retrocompat regression_guard

_CATALOG = {str(i["id"]): i for i in SHOP_ITEMS}

# Consumíveis — compra REPETÍVEL (nunca "acaba"): dá sempre o que gastar amêndoas
# e mais interação com o monstrinho (estilo Finch: alimentar + caixa surpresa).
SHOP_CONSUMABLES: list[dict[str, str | int]] = [
    {
        "id": "treat",
        "emoji": "🍪",
        "label": "Petisco",
        "price": 3,
        "kind": "treat",
        "xp": 6,
        "desc": "Alimenta o monstrinho — ele fica feliz e ganha experiência.",
    },
    {
        "id": "big_treat",
        "emoji": "🍰",
        "label": "Bolo especial",
        "price": 8,
        "kind": "treat",
        "xp": 18,
        "desc": "Petisco caprichado — o dobro de carinho e experiência.",
    },
    {
        "id": "surprise_box",
        "emoji": "🎁",
        "label": "Caixa surpresa",
        "price": 12,
        "kind": "box",
        "xp": 10,
        "desc": "Recompensa aleatória: decoração nova, amêndoas bônus ou surpresa.",
    },
]

_CONSUMABLES = {str(i["id"]): i for i in SHOP_CONSUMABLES}


def lookup_consumable(item_id: str) -> dict[str, str | int] | None:
    return _CONSUMABLES.get((item_id or "").strip().lower()[:24])


def consumables_payload(seeds: int) -> list[dict]:
    out: list[dict] = []
    for item in SHOP_CONSUMABLES:
        price = int(item["price"])
        out.append(
            {
                "id": str(item["id"]),
                "emoji": str(item["emoji"]),
                "label": str(item["label"]),
                "price": price,
                "kind": str(item["kind"]),
                "desc": str(item["desc"]),
                "can_afford": seeds >= price,
            }
        )
    return out


def all_decor_ids() -> list[str]:
    return [str(i["id"]) for i in SHOP_ITEMS]


def validate_shop_catalog_size() -> None:
    total = len(SHOP_ITEMS)
    if total < 30:
        raise ValueError(f"daily_care shop precisa de 30+ itens, tem {total}")
    if len(SHOP_ROTATING_POOL) < 20:
        raise ValueError(f"pool rotação precisa de 20+ itens, tem {len(SHOP_ROTATING_POOL)}")
    ids = [str(i["id"]) for i in SHOP_ITEMS]
    if len(ids) != len(set(ids)):
        raise ValueError("ids duplicados no catálogo da loja")


def _local_date_str() -> str:
    sess = get_session()
    if sess:
        loc = local_now_from_session(sess)
        if loc:
            return loc.strftime("%Y-%m-%d")
    return datetime.datetime.now().strftime("%Y-%m-%d")


def _week_key(local_date: str | None = None) -> str:
    today = local_date or _local_date_str()
    try:
        dt = datetime.datetime.strptime(today, "%Y-%m-%d").date()
        iso = dt.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"
    except ValueError:
        return "0000-W00"


def _next_monday(local_date: str | None = None) -> str:
    today = local_date or _local_date_str()
    try:
        dt = datetime.datetime.strptime(today, "%Y-%m-%d").date()
        days_ahead = (7 - dt.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        return (dt + datetime.timedelta(days=days_ahead)).isoformat()
    except ValueError:
        return ""


def _weekly_rotating_ids(week_key: str, count: int = SHOP_ROTATION_COUNT) -> list[str]:
    pool_ids = [str(i["id"]) for i in SHOP_ROTATING_POOL]
    if not pool_ids:
        return []
    seed = int(hashlib.sha256(week_key.encode()).hexdigest()[:8], 16)
    ordered = sorted(pool_ids, key=lambda pid: int(hashlib.md5(f"{week_key}:{pid}".encode()).hexdigest(), 16))
    start = seed % len(ordered)
    out: list[str] = []
    for n in range(len(ordered)):
        out.append(ordered[(start + n) % len(ordered)])
        if len(out) >= min(count, len(ordered)):
            break
    return out


def _base_all_owned(owned: set[str]) -> bool:
    base_ids = {str(i["id"]) for i in SHOP_BASE_ITEMS}
    return bool(base_ids) and base_ids.issubset(owned)


def shop_catalog_payload(raw: dict, seeds: int) -> dict:
    """Catálogo visível + metadados de rotação."""
    owned_list = raw.get("shop_owned")
    owned: set[str] = set()
    if isinstance(owned_list, list):
        owned = {str(x).strip() for x in owned_list if str(x).strip()}

    week_key = _week_key()
    rotating_ids = set(_weekly_rotating_ids(week_key))
    base_complete = _base_all_owned(owned)

    items: list[dict] = []
    for item in SHOP_BASE_ITEMS:
        iid = str(item["id"])
        price = int(item["price"])
        is_owned = iid in owned
        items.append(
            {
                "id": iid,
                "emoji": str(item["emoji"]),
                "label": str(item["label"]),
                "price": price,
                "owned": is_owned,
                "can_afford": seeds >= price and not is_owned,
                "rotating": False,
            }
        )

    for iid in _weekly_rotating_ids(week_key):
        item = _CATALOG.get(iid)
        if not item:
            continue
        price = int(item["price"])
        is_owned = iid in owned
        items.append(
            {
                "id": iid,
                "emoji": str(item["emoji"]),
                "label": str(item["label"]),
                "price": price,
                "owned": is_owned,
                "can_afford": seeds >= price and not is_owned,
                "rotating": True,
            }
        )

    unowned_rotating = [i for i in items if i.get("rotating") and not i.get("owned")]
    return {
        "shop_items": items,
        "shop_week_label": week_key.replace("-W", " · semana "),
        "shop_rotation_reset": _next_monday(),
        "shop_base_complete": base_complete,
        "shop_rotating_available": len(unowned_rotating),
        "shop_rotating_ids": list(rotating_ids),
    }


def shop_owned_decor(raw: dict) -> list[dict[str, str]]:
    owned_list = raw.get("shop_owned")
    if not isinstance(owned_list, list):
        return []
    out: list[dict[str, str]] = []
    for iid in owned_list:
        sid = str(iid).strip()
        item = _CATALOG.get(sid)
        if not item:
            continue
        out.append(
            {
                "id": sid,
                "emoji": str(item["emoji"]),
                "label": str(item["label"]),
            }
        )
    return out


def lookup_shop_item(item_id: str) -> dict[str, str | int] | None:
    return _CATALOG.get((item_id or "").strip().lower()[:24])
