"""Smoke test: módulos de agenda compartilhada (sem Supabase)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    import datetime as dt

    from ego_api import chat_schedule as cs
    from ego_api import shared_calendars as sc

    ref = dt.datetime(2026, 5, 29, 10, 0, tzinfo=dt.timezone(dt.timedelta(hours=-3)))

    assert hasattr(sc, "create_calendar")
    assert hasattr(sc, "list_calendars_for_user")
    assert hasattr(sc, "find_calendar_id_by_name")
    assert sc.calendar_name_key("Família") == sc.calendar_name_key("familia")
    assert sc.calendar_name_key("  FAMILIA ") == sc.calendar_name_key("família")
    assert hasattr(cs, "extract_shared_setup")
    assert hasattr(cs, "extract_shared_event")
    assert hasattr(cs, "extract_shared_invite")
    assert hasattr(cs, "parse_shared_event_from_plain_text")
    assert hasattr(cs, "is_group_schedule_request")
    assert hasattr(cs, "fill_shared_calendar_name")
    assert hasattr(cs, "shared_event_from_schedule_draft")
    assert hasattr(cs, "build_today_commitments_reply")

    event_text = (
        "Marca na agenda compartilhada Família reunião amanhã às 15h"
    )
    ev = cs.parse_shared_event_from_plain_text(event_text)
    assert ev and ev.get("calendar_name") == "Família", ev

    short_event = "Marque na agenda Família reunião amanhã às 15h"
    ev2 = cs.parse_shared_event_from_plain_text(short_event)
    assert ev2 and ev2.get("calendar_name"), ev2

    bare = "Marca reunião amanhã às 15h"
    assert cs.is_group_schedule_request(bare)
    assert cs.detect_scope_from_user_text(bare) is None
    assert cs.user_named_shared_calendar(bare) is False
    assert cs.user_named_shared_calendar(short_event) is True
    assert cs.detect_scope_from_user_text(short_event) == "shared"
    assert cs.user_named_shared_calendar("marca na agenda familia") is True
    assert cs.detect_scope_from_user_text("marca na agenda pessoal") == "personal"

    sched: dict = {"step": "choose_scope", "draft": {}}
    sched = cs.stash_pending_schedule_from_text(
        sched, "Marca reunião amanhã às 15h", ref=ref
    )
    assert sched["draft"].get("scheduled_at"), sched
    done = cs.apply_scope_follow_up_if_pending(
        sched, "marca na agenda familia", None, ""
    )
    assert done and done["draft"].get("scope") == "shared", done
    assert (
        cs.resolve_effective_schedule_scope(done, "marca na agenda familia")
        == "shared"
    )
    assert (
        cs.resolve_effective_schedule_scope(
            {"draft": {"scope": "personal"}}, "ok"
        )
        == "personal"
    )
    assert cs.detect_scope_from_user_text("Marca na agenda pessoal amanhã 15h") == "personal"
    ev3 = cs.parse_shared_event_from_plain_text(bare)
    assert ev3 and ev3.get("scheduled_at") and not ev3.get("calendar_name")
    assert ev2.get("title") == "Reunião", ev2
    assert ev.get("scheduled_at"), ev
    assert ev2.get("scheduled_at"), ev2

    delete_text = "Apaga a agenda compartilhada Família"
    deleted = cs.parse_delete_shared_calendar_from_plain_text(delete_text)
    assert deleted and deleted.get("calendar_name") == "Família", deleted

    short_delete = "Apaga a agenda Família"
    deleted2 = cs.parse_delete_shared_calendar_from_plain_text(short_delete)
    assert deleted2 and deleted2.get("calendar_name") == "Família", deleted2

    create_text = "Cria agenda compartilhada Família"
    created = cs.parse_create_shared_calendar_from_plain_text(create_text)
    assert created and created.get("calendar_name") == "Família", created

    short_create = "Cria agenda Família"
    created2 = cs.parse_create_shared_calendar_from_plain_text(short_create)
    assert created2 and created2.get("calendar_name") == "Família", created2

    invite = cs.parse_invite_from_plain_text(
        "Convida teste@exemplo.com para a agenda Família"
    )
    assert invite and invite.get("calendar_name") == "Família", invite

    personal = "Marca na agenda pessoal consulta amanhã às 9h"
    assert cs.detect_scope_from_user_text(personal) == "personal"
    prem = cs.parse_reminder_from_plain_text(personal)
    assert prem and prem.get("title") == "Consulta" and prem.get("scheduled_at"), prem

    wrong_llm = [{"title": "Consulta", "scheduled_at": "2026-06-05T12:00:00-03:00"}]
    fixed = cs.override_scheduled_from_user_message(personal, wrong_llm, ref=ref)
    assert fixed and "2026-05-30" in str(fixed[0].get("scheduled_at")), fixed
    assert "T09:00" in str(fixed[0].get("scheduled_at")), fixed

    nine = cs.parse_reminder_from_plain_text(personal, ref=ref)
    assert nine and "T09:00" in str(nine.get("scheduled_at")), nine

    from ego_api.chat_reply import ensure_visible_chat_reply

    reply = ensure_visible_chat_reply(
        "Pronto, criei a agenda Família!",
        reminders_saved=[],
        agenda_saved=[],
        shared_calendars_created=[{"name": "Família", "id": "x"}],
        shared_setup={"calendar_name": "Família"},
    )
    assert "Criei a agenda «Família»" in reply, reply

    reply = ensure_visible_chat_reply(
        "Não encontrei a agenda Família.",
        reminders_saved=[],
        agenda_saved=[],
        shared_calendars_deleted=["Família"],
        shared_delete={"calendar_name": "Família"},
    )
    assert "Apaguei" in reply and "Família" in reply, reply

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
