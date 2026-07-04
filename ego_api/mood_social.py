"""Monstrinhos Fase 10 — convite social (partilhar app com amigos)."""

from __future__ import annotations

from typing import Any

try:
    from ego_supabase import Client
except ImportError:
    from supabase import Client  # type: ignore[assignment]


def invite_payload(supabase: Client | None, user_id: str) -> dict[str, Any]:
    del supabase, user_id
    try:
        from ego_api.download_go import public_go_url

        link = public_go_url()
    except Exception:
        link = "https://egoai.com.br"
    return {
        "title": "Convide um amigo",
        "emoji": "💬",
        "message": (
            "Estou cuidando do humor no EGO-AI — Monstrinhos + PAUSA de 2 min com avatar. "
            f"Teste grátis: {link}"
        ),
        "share_hook": "Quem doma o humor junto cresce mais rápido 🌱",
    }
