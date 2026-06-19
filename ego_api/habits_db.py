"""Rascunhos de agenda (Descarrego) e lista de compras."""

from __future__ import annotations

import datetime
import uuid
from typing import Any

from ego_api.config import (
    SUPABASE_AGENDA_DRAFTS_TABLE,
    SUPABASE_SHOPPING_LIST_TABLE,
)
from ego_api.supabase_client import apply_user_auth, insert_returning_rows


def _now_utc() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def list_pending_drafts(supabase, user_id: str) -> list[dict]:
    if not supabase or not user_id:
        return []
    apply_user_auth(supabase)
    try:
        res = (
            supabase.table(SUPABASE_AGENDA_DRAFTS_TABLE)
            .select("*")
            .eq("user_id", user_id)
            .eq("status", "pending")
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )
        rows = list(res.data or [])
        out: list[dict] = []
        for row in rows:
            items = row.get("items")
            if not isinstance(items, list) or len(items) == 0:
                did = str(row.get("id") or "")
                if did:
                    dismiss_draft(supabase, user_id, did)
                continue
            out.append(row)
        return out
    except Exception:
        return []


def insert_draft(
    supabase,
    user_id: str,
    *,
    comfort_reply: str,
    items: list[dict],
    source: str = "night_dump",
) -> dict | None:
    if not supabase or not user_id:
        return None
    apply_user_auth(supabase)
    expires = _now_utc() + datetime.timedelta(hours=48)
    row = {
        "user_id": user_id,
        "source": source,
        "comfort_reply": (comfort_reply or "")[:4000],
        "items": items,
        "status": "pending",
        "expires_at": expires.isoformat(),
    }
    try:
        inserted = insert_returning_rows(supabase, SUPABASE_AGENDA_DRAFTS_TABLE, row)
        return inserted[0] if inserted else None
    except Exception:
        return None


def get_draft(supabase, user_id: str, draft_id: str) -> dict | None:
    if not supabase or not user_id or not draft_id:
        return None
    apply_user_auth(supabase)
    try:
        res = (
            supabase.table(SUPABASE_AGENDA_DRAFTS_TABLE)
            .select("*")
            .eq("user_id", user_id)
            .eq("id", draft_id)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        return rows[0] if rows else None
    except Exception:
        return None


def update_draft_items(supabase, user_id: str, draft_id: str, items: list[dict]) -> bool:
    if not supabase or not user_id:
        return False
    apply_user_auth(supabase)
    try:
        supabase.table(SUPABASE_AGENDA_DRAFTS_TABLE).update({"items": items}).eq(
            "user_id", user_id
        ).eq("id", draft_id).execute()
        return True
    except Exception:
        return False


def dismiss_draft(supabase, user_id: str, draft_id: str) -> bool:
    if not supabase or not user_id:
        return False
    apply_user_auth(supabase)
    try:
        supabase.table(SUPABASE_AGENDA_DRAFTS_TABLE).update({"status": "dismissed"}).eq(
            "user_id", user_id
        ).eq("id", draft_id).execute()
        return True
    except Exception:
        return False


def delete_draft(supabase, user_id: str, draft_id: str) -> bool:
    if not supabase or not user_id:
        return False
    apply_user_auth(supabase)
    try:
        supabase.table(SUPABASE_AGENDA_DRAFTS_TABLE).delete().eq(
            "user_id", user_id
        ).eq("id", draft_id).execute()
        return True
    except Exception:
        return False


def list_shopping_items(
    supabase, user_id: str, *, reminder_id: str | None = None, orphans_only: bool = False
) -> list[dict]:
    if not supabase or not user_id:
        return []
    apply_user_auth(supabase)
    try:
        q = (
            supabase.table(SUPABASE_SHOPPING_LIST_TABLE)
            .select("*")
            .eq("user_id", user_id)
            .eq("done", False)
        )
        if reminder_id:
            q = q.eq("reminder_id", reminder_id)
        elif orphans_only:
            q = q.is_("reminder_id", "null")
        res = q.order("created_at").execute()
        return list(res.data or [])
    except Exception:
        return []


def shopping_by_reminder_ids(supabase, user_id: str, reminder_ids: list[str]) -> dict[str, list[dict]]:
    if not supabase or not user_id or not reminder_ids:
        return {}
    apply_user_auth(supabase)
    out: dict[str, list[dict]] = {}
    try:
        res = (
            supabase.table(SUPABASE_SHOPPING_LIST_TABLE)
            .select("*")
            .eq("user_id", user_id)
            .eq("done", False)
            .in_("reminder_id", reminder_ids)
            .order("created_at")
            .execute()
        )
        for row in res.data or []:
            rid = str(row.get("reminder_id") or "")
            if rid:
                out.setdefault(rid, []).append(row)
    except Exception:
        pass
    return out


def insert_shopping_item(
    supabase,
    user_id: str,
    *,
    title: str,
    category: str = "mercado",
    reminder_id: str | None = None,
) -> dict | None:
    if not supabase or not user_id or not (title or "").strip():
        return None
    apply_user_auth(supabase)
    row = {
        "user_id": user_id,
        "reminder_id": reminder_id,
        "title": title.strip()[:300],
        "category": (category or "mercado")[:32],
        "done": False,
    }
    try:
        inserted = insert_returning_rows(supabase, SUPABASE_SHOPPING_LIST_TABLE, row)
        return inserted[0] if inserted else None
    except Exception:
        return None


def patch_shopping_item(
    supabase, user_id: str, item_id: str, *, done: bool | None = None, title: str | None = None
) -> bool:
    if not supabase or not user_id or not item_id:
        return False
    apply_user_auth(supabase)
    patch: dict[str, Any] = {}
    if done is not None:
        patch["done"] = done
    if title is not None:
        patch["title"] = title.strip()[:300]
    if not patch:
        return False
    try:
        supabase.table(SUPABASE_SHOPPING_LIST_TABLE).update(patch).eq(
            "user_id", user_id
        ).eq("id", item_id).execute()
        return True
    except Exception:
        return False


def delete_shopping_item(supabase, user_id: str, item_id: str) -> bool:
    if not supabase or not user_id:
        return False
    apply_user_auth(supabase)
    try:
        supabase.table(SUPABASE_SHOPPING_LIST_TABLE).delete().eq(
            "user_id", user_id
        ).eq("id", item_id).execute()
        return True
    except Exception:
        return False


def clear_done_shopping(supabase, user_id: str) -> int:
    if not supabase or not user_id:
        return 0
    apply_user_auth(supabase)
    try:
        res = (
            supabase.table(SUPABASE_SHOPPING_LIST_TABLE)
            .delete()
            .eq("user_id", user_id)
            .eq("done", True)
            .execute()
        )
        return len(res.data or [])
    except Exception:
        return 0
