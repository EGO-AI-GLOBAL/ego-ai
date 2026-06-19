"""Agenda família no descarrego — só texto na agenda compartilhada (sem push/avatar)."""

from __future__ import annotations

import unicodedata

from ego_api import delegation_db
from ego_api.expo_push import send_expo_push
from ego_api.shared_calendar_notify import _format_when_pt, _ui_state_dict
from ego_api.supabase_client import create_service_client

try:
    from ego_supabase import Client
except ImportError:
    from supabase import Client  # type: ignore[assignment]

_RELATIONSHIP_WORDS = (
    "marido",
    "esposo",
    "esposa",
    "parceiro",
    "parceira",
    "namorado",
    "namorada",
    "mãe",
    "mae",
    "pai",
    "filho",
    "filha",
    "sogro",
    "sogra",
)


def _norm(s: str) -> str:
    raw = unicodedata.normalize("NFD", (s or "").strip().lower())
    return "".join(c for c in raw if unicodedata.category(c) != "Mn")


def _requester_label(admin: Client, user_id: str) -> str:
    try:
        res = (
            admin.table("profiles")
            .select("full_name,name,email")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        row = (res.data or [{}])[0]
        name = str(row.get("full_name") or row.get("name") or "").strip()
        if name:
            return name.split()[0]
        email = str(row.get("email") or "").strip()
        if email and "@" in email:
            return email.split("@")[0]
    except Exception:
        pass
    return "Alguém da família"


def _push_token(admin: Client, user_id: str) -> str:
    try:
        res = (
            admin.table("profiles")
            .select("ui_state")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        row = (res.data or [{}])[0]
        ui = _ui_state_dict(row if isinstance(row, dict) else None)
        return str(ui.get("expo_push_token") or "").strip()
    except Exception:
        return ""


def _collect_partner_candidates(
    supabase: Client | None, from_user_id: str
) -> list[dict]:
    from ego_api import shared_calendars as sc

    out: list[dict] = []
    seen: set[str] = set()
    for cal in sc.list_calendars_for_user(supabase, from_user_id):
        cid = str(cal.get("id") or "")
        for mem in cal.get("members") or []:
            uid = str(mem.get("user_id") or "").strip()
            if not uid or uid == from_user_id or uid in seen:
                continue
            if str(mem.get("status") or "active") != "active":
                continue
            seen.add(uid)
            label = str(mem.get("display_name") or mem.get("invited_email") or "").strip()
            out.append(
                {
                    "user_id": uid,
                    "calendar_id": cid,
                    "calendar_name": str(cal.get("name") or ""),
                    "display_name": label,
                }
            )
    return out


def _match_assignee(candidates: list[dict], assign_to: dict) -> dict | None:
    if not candidates:
        return None
    hint = _norm(str(assign_to.get("assignee_hint") or assign_to.get("relationship") or ""))
    task = _norm(str(assign_to.get("task") or ""))

    if hint:
        for c in candidates:
            dn = _norm(c.get("display_name") or "")
            if hint in dn or dn in hint:
                return c
        for word in _RELATIONSHIP_WORDS:
            if word in hint:
                for c in candidates:
                    dn = _norm(c.get("display_name") or "")
                    if word in dn:
                        return c
                break

    if len(candidates) == 1:
        return candidates[0]

    for c in candidates:
        dn = _norm(c.get("display_name") or "")
        for word in _RELATIONSHIP_WORDS:
            if word in dn and (not hint or word in hint or word in task):
                return c
    return None


def _preferred_family_calendar(
    supabase: Client | None, user_id: str
) -> tuple[str, str]:
    """(calendar_id, calendar_name) — prefere agenda «Entre Nós»."""
    from ego_api import shared_calendars as sc

    cals = sc.list_calendars_for_user(supabase, user_id)
    if not cals:
        return "", ""
    for cal in cals:
        name = str(cal.get("name") or "")
        if sc.is_entre_nos_calendar(name):
            return str(cal.get("id") or ""), name or "Entre Nós"
    for cal in cals:
        key = sc.calendar_name_key(str(cal.get("name") or ""))
        if key in ("familia", "family", "casa"):
            return str(cal.get("id") or ""), str(cal.get("name") or "Entre Nós")
    first = cals[0]
    return str(first.get("id") or ""), str(first.get("name") or "Entre Nós")


def enrich_family_items(
    supabase: Client | None, user_id: str, items: list[dict]
) -> list[dict]:
    """Itens com assign_to → marcar agenda Entre Nós (compartilhada)."""
    if not supabase or not user_id or not items:
        return items
    candidates = _collect_partner_candidates(supabase, user_id)
    fallback_id, fallback_name = _preferred_family_calendar(supabase, user_id)
    out: list[dict] = []
    for raw in items:
        it = dict(raw)
        assign = it.get("assign_to")
        if not isinstance(assign, dict):
            out.append(it)
            continue
        cal_id, cal_name = "", ""
        target = _match_assignee(candidates, assign)
        if target:
            cal_id = str(target.get("calendar_id") or "")
            cal_name = str(target.get("calendar_name") or "")
        if not cal_id:
            cal_id, cal_name = fallback_id, fallback_name
        if cal_id:
            it["shared_calendar_id"] = cal_id
            it["shared_calendar_name"] = cal_name
        out.append(it)
    return out


def family_event_title_from_item(it: dict) -> str:
    """Título do evento na agenda compartilhada — responsável por escrito."""
    title = str(it.get("title") or "Compromisso").strip()
    assign = it.get("assign_to")
    if not isinstance(assign, dict):
        return title[:500]
    task = str(assign.get("task") or "").strip()
    hint = str(
        assign.get("assignee_hint") or assign.get("relationship") or "parceiro"
    ).strip()
    if task:
        return f"{title} — {hint}: {task}"[:500]
    if hint and hint.lower() not in title.lower():
        return f"{title} — {hint}"[:500]
    return title[:500]


def _build_push_copy(
    *,
    assistant_name: str,
    title: str,
    scheduled_at: str,
    task_description: str,
    assignee_label: str,
) -> tuple[str, str]:
    when = _format_when_pt(scheduled_at) if scheduled_at else ""
    event_line = title.strip()
    if when:
        event_line += f" amanhã às {when.split()[-1] if when else when}"
    task = (task_description or assignee_label or "ajudar na tarefa").strip()
    body = (
        f"Olá! A {assistant_name} me avisou que {event_line} "
        f"e você ficou responsável por {task}. "
        f"Posso incluir isso na sua agenda também?"
    )
    return "Família · EGO-AI", body[:500]


def process_delegations_from_items(
    supabase: Client | None,
    from_user_id: str,
    *,
    draft_id: str,
    items: list[dict],
    assistant_name: str = "Luna",
) -> list[dict]:
    """Cria pedidos + push para itens com assign_to. Devolve pedidos criados."""
    if not supabase or not from_user_id or not items:
        return []
    admin = create_service_client()
    requester = _requester_label(admin, from_user_id) if admin else "Alguém"
    candidates = _collect_partner_candidates(supabase, from_user_id)
    created: list[dict] = []

    for it in items:
        assign = it.get("assign_to")
        if not isinstance(assign, dict):
            continue
        target = _match_assignee(candidates, assign)
        if not target:
            continue
        to_uid = str(target.get("user_id") or "")
        title = str(it.get("title") or "Compromisso").strip()
        scheduled = str(it.get("scheduled_at") or "").strip()
        task = str(assign.get("task") or title).strip()
        label = str(assign.get("assignee_hint") or assign.get("relationship") or "").strip()

        row = delegation_db.insert_request(
            supabase,
            from_user_id=from_user_id,
            to_user_id=to_uid,
            title=title,
            scheduled_at=scheduled or None,
            task_description=task,
            assignee_label=label,
            assistant_name=assistant_name,
            requester_name=requester,
            draft_id=draft_id,
            calendar_id=str(target.get("calendar_id") or "") or None,
        )
        if not row:
            continue
        created.append(row)

        if admin:
            tok = _push_token(admin, to_uid)
            if tok:
                push_title, push_body = _build_push_copy(
                    assistant_name=assistant_name,
                    title=title,
                    scheduled_at=scheduled,
                    task_description=task,
                    assignee_label=label,
                )
                send_expo_push(
                    [tok],
                    title=push_title,
                    body=push_body,
                    data={
                        "type": "delegation_request",
                        "request_id": str(row.get("id") or ""),
                        "screen": "agenda",
                    },
                )
    return created


def confirm_delegation(
    supabase: Client | None, user_id: str, request_id: str
) -> tuple[dict | None, str | None]:
    from ego_api import db

    req = delegation_db.get_request(supabase, user_id, request_id)
    if not req:
        return None, "Pedido não encontrado."
    if str(req.get("to_user_id")) != user_id:
        return None, "Sem permissão."
    if str(req.get("status") or "") != "pending":
        return None, "Este pedido já foi respondido."

    title = str(req.get("title") or "Compromisso")
    task = str(req.get("task_description") or "").strip()
    rem_title = title if not task else f"{title} — {task[:120]}"
    scheduled = req.get("scheduled_at")
    cal_id = str(req.get("calendar_id") or "").strip()

    if cal_id:
        from ego_api import shared_calendars as sc

        ok, err, ev = sc.insert_event(
            supabase,
            user_id,
            cal_id,
            title=rem_title[:500],
            scheduled_at=scheduled,
            announce=rem_title[:500],
            partner_invite=False,
        )
        if not ok or not ev:
            return None, err or "Não foi possível gravar na agenda da família."
        rem = ev
    else:
        ok, err, rem = db.insert_reminder(
            supabase,
            user_id,
            title=rem_title[:500],
            scheduled_at=scheduled,
            announce=rem_title[:500],
        )
        if not ok or not rem:
            return None, err or "Não foi possível gravar na agenda."

    delegation_db.mark_confirmed(supabase, user_id, request_id)
    from ego_api import streaks

    streaks.record_streak_activity(supabase, user_id, source="delegation_confirm")
    return rem, None
