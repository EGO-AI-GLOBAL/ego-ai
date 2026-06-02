from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ego_api.config import read_env, supabase_anon_key, supabase_url
from ego_api.request_ctx import get_session

if TYPE_CHECKING:
    from ego_supabase import Client

try:
    from ego_supabase import create_client
except ImportError:
    from supabase import create_client  # type: ignore[assignment]


def supabase_env_status() -> dict[str, bool | int | str]:
    """Diagnóstico seguro (sem expor URL/chave) para health e logs."""
    url = supabase_url()
    key = supabase_anon_key()
    status: dict[str, bool | int | str] = {
        "url_set": bool(url),
        "key_set": bool(key),
        "key_len": len(key) if key else 0,
        "client_ok": False,
    }
    if not url or not key:
        return status
    try:
        create_client(url, key)
        status["client_ok"] = True
    except Exception as exc:
        status["client_error"] = type(exc).__name__
    return status


def create_anon_client() -> Client | None:
    url, key = supabase_url(), supabase_anon_key()
    if not url or not key:
        return None
    try:
        return create_client(url, key)
    except Exception:
        return None


def create_service_client() -> Client | None:
    """Cliente admin (convites por e-mail). Requer SUPABASE_SERVICE_ROLE_KEY no servidor."""
    url = supabase_url()
    key = read_env("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        return None
    try:
        return create_client(url, key)
    except Exception:
        return None


def insert_returning_rows(
    client: Client | None,
    table: str,
    row: dict | list,
    *,
    raise_errors: bool = False,
) -> list[dict[str, Any]]:
    """INSERT com linhas devolvidas (PostgREST 2.x: não usar .insert().select())."""
    if not client or not table:
        if raise_errors:
            raise RuntimeError("Cliente Supabase indisponível.")
        return []
    try:
        res = client.table(table).insert(row).execute()
        return list(res.data or [])
    except Exception as exc:
        if raise_errors:
            raise
        return []


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
