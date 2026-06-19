"""Pedidos de delegação familiar (piloto automático)."""

from __future__ import annotations

import datetime
from typing import Any

from ego_api.config import SUPABASE_DELEGATION_REQUESTS_TABLE
from ego_api.supabase_client import apply_user_auth, insert_returning_rows

try:
    from ego_supabase import Client
except ImportError:
    from supabase import Client  # type: ignore[assignment]


def list_pending_incoming(supabase: Client | None, user_id: str) -> list[dict]:
    if not supabase or not user_id:
        return []
    apply_user_auth(supabase)
    try:
        res = (
            supabase.table(SUPABASE_DELEGATION_REQUESTS_TABLE)
            .select("*")
            .eq("to_user_id", user_id)
            .eq("status", "pending")
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )
        return list(res.data or [])
    except Exception:
        return []


def insert_request(
    supabase: Client | None,
    *,
    from_user_id: str,
    to_user_id: str,
    title: str,
    scheduled_at: str | None = None,
    task_description: str = "",
    assignee_label: str = "",
    assistant_name: str = "Luna",
    requester_name: str = "",
    draft_id: str | None = None,
    calendar_id: str | None = None,
) -> dict | None:
    if not supabase or not from_user_id or not to_user_id or not (title or "").strip():
        return None
    apply_user_auth(supabase)
    row: dict[str, Any] = {
        "from_user_id": from_user_id,
        "to_user_id": to_user_id,
        "title": title.strip()[:500],
        "task_description": (task_description or "")[:2000],
        "assignee_label": (assignee_label or "")[:120],
        "assistant_name": (assistant_name or "Luna")[:64],
        "requester_name": (requester_name or "")[:200],
        "status": "pending",
    }
    if scheduled_at:
        row["scheduled_at"] = scheduled_at
    if draft_id:
        row["draft_id"] = draft_id
    if calendar_id:
        row["calendar_id"] = calendar_id
    try:
        inserted = insert_returning_rows(supabase, SUPABASE_DELEGATION_REQUESTS_TABLE, row)
        return inserted[0] if inserted else None
    except Exception:
        return None


def get_request(supabase: Client | None, user_id: str, request_id: str) -> dict | None:
    if not supabase or not user_id or not request_id:
        return None
    apply_user_auth(supabase)
    try:
        res = (
            supabase.table(SUPABASE_DELEGATION_REQUESTS_TABLE)
            .select("*")
            .eq("id", request_id)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            return None
        row = rows[0]
        if str(row.get("to_user_id")) != user_id and str(row.get("from_user_id")) != user_id:
            return None
        return row
    except Exception:
        return None


def mark_confirmed(supabase: Client | None, user_id: str, request_id: str) -> bool:
    if not supabase or not user_id:
        return False
    apply_user_auth(supabase)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        supabase.table(SUPABASE_DELEGATION_REQUESTS_TABLE).update(
            {"status": "confirmed", "confirmed_at": now}
        ).eq("id", request_id).eq("to_user_id", user_id).eq("status", "pending").execute()
        return True
    except Exception:
        return False


def mark_dismissed(supabase: Client | None, user_id: str, request_id: str) -> bool:
    if not supabase or not user_id:
        return False
    apply_user_auth(supabase)
    try:
        supabase.table(SUPABASE_DELEGATION_REQUESTS_TABLE).update({"status": "dismissed"}).eq(
            "id", request_id
        ).eq("to_user_id", user_id).eq("status", "pending").execute()
        return True
    except Exception:
        return False
