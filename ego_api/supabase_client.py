from __future__ import annotations

from typing import TYPE_CHECKING

from ego_api.config import supabase_anon_key, supabase_url
from ego_api.request_ctx import get_session

if TYPE_CHECKING:
    from ego_supabase import Client

try:
    from ego_supabase import create_client
except ImportError:
    from supabase import create_client  # type: ignore[assignment]


def create_anon_client() -> Client | None:
    url, key = supabase_url(), supabase_anon_key()
    if not url or not key:
        return None
    try:
        return create_client(url, key)
    except Exception:
        return None


def apply_user_auth(client: Client | None) -> bool:
    """Aplica JWT do pedido atual ao cliente Supabase (RLS)."""
    if not client:
        return False
    sess = get_session()
    if not sess or not sess.access_token:
        return False
    try:
        if sess.refresh_token:
            client.auth.set_session(sess.access_token, sess.refresh_token)
        else:
            client.postgrest.auth(sess.access_token)
        return True
    except Exception:
        return False
