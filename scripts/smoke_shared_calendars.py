"""Smoke test: módulos de agenda compartilhada (sem Supabase)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    from ego_api import chat_schedule as cs
    from ego_api import shared_calendars as sc

    assert hasattr(sc, "create_calendar")
    assert hasattr(sc, "list_calendars_for_user")
    assert hasattr(sc, "find_calendar_id_by_name")
    assert hasattr(cs, "extract_shared_setup")
    assert hasattr(cs, "extract_shared_event")
    assert hasattr(cs, "extract_shared_invite")
    assert hasattr(cs, "parse_shared_event_from_plain_text")
    assert hasattr(cs, "shared_event_from_schedule_draft")
    assert hasattr(cs, "build_today_commitments_reply")

    event_text = (
        "Marca na agenda compartilhada Família reunião amanhã às 15h"
    )
    ev = cs.parse_shared_event_from_plain_text(event_text)
    assert ev and ev.get("calendar_name") == "Família", ev
    assert ev.get("title") == "Reunião", ev
    assert ev.get("scheduled_at"), ev

    delete_text = "Apaga a agenda compartilhada Família"
    deleted = cs.parse_delete_shared_calendar_from_plain_text(delete_text)
    assert deleted and deleted.get("calendar_name") == "Família", deleted

    sample = (
        'Ok [[EGO_SHARED_SETUP:{"calendar_name":"Familia","title":"Call",'
        '"scheduled_at":"2026-06-15T14:00:00-03:00","invite_emails":["a@b.com"]}]]'
    )
    clean, obj = cs.extract_shared_setup(sample)
    assert obj and obj.get("calendar_name") == "Familia", obj

    invite = '[[EGO_SHARED_INVITE:{"calendar_name":"Familia","invite_emails":["x@y.com"]}]]'
    _, inv = cs.extract_shared_invite(invite)
    assert inv and inv.get("invite_emails") == ["x@y.com"]

    assert cs.looks_like_today_agenda_query("compromissos de hoje")
    assert not cs.looks_like_today_agenda_query("marcar compromisso hoje as 15h")

    import flask_api

    rules = {r.rule for r in flask_api.app.url_map.iter_rules()}
    for path in (
        "/api/v1/shared-calendars",
        "/api/v1/shared-calendars/<calendar_id>",
        "/api/v1/shared-calendars/<calendar_id>/members",
        "/api/v1/shared-calendars/<calendar_id>/events",
    ):
        assert path in rules, f"Rota em falta: {path}"

    print("OK smoke_shared_calendars")
    return 0


if __name__ == "__main__":
    sys.exit(main())
