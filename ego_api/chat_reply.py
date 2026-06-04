"""Garante texto visível no chat quando o LLM só devolve marcadores EGO_*."""

from __future__ import annotations

import re

from ego_api.request_ctx import get_session
from ego_api.schedule_tz import format_scheduled_for_user as _format_scheduled_pt


def _looks_like_false_schedule_success(text: str) -> bool:
    return bool(re.search(r"(?i)\b(pronto|marquei|agendei|confirmado|registrei)\b", text))


def ensure_visible_chat_reply(
    reply_clean: str,
    *,
    reminders_saved: list[dict],
    agenda_saved: list[dict],
    rem_items: list[dict] | None = None,
    ag_items: list[dict] | None = None,
    warnings: list[str] | None = None,
    shared_calendars_saved: list[dict] | None = None,
    shared_events_saved: list[dict] | None = None,
    shared_members_saved: list[dict] | None = None,
    shared_setup: dict | None = None,
    shared_invite: dict | None = None,
    shared_event: dict | None = None,
    shared_delete: dict | None = None,
    shared_calendars_deleted: list[str] | None = None,
    shared_calendars_created: list[dict] | None = None,
) -> str:
    warns = warnings or []
    shared_members = shared_members_saved or []
    shared_ev_saved = shared_events_saved or []
    deleted_cals = shared_calendars_deleted or []
    created_cals = shared_calendars_created or []
    shared_cals = shared_calendars_saved or []
    text = (reply_clean or "").strip()
    pending_rem = rem_items or []
    pending_ag = ag_items or []

    # Servidor gravou — resposta certa (ignora texto enganoso do LLM).
    if deleted_cals:
        cal_name = deleted_cals[0].strip() or "Agenda"
        extra = f" Avisos: {'; '.join(warns[:3])}" if warns else ""
        return f"Pronto! Apaguei a agenda «{cal_name}».{extra}"

    if created_cals:
        cal_name = str(created_cals[0].get("name") or "Agenda").strip()
        extra = f" Avisos: {'; '.join(warns[:3])}" if warns else ""
        return (
            f"Pronto! Criei a agenda «{cal_name}». "
            f"Vê-la na aba Agenda → Família e grupos.{extra}"
        )

    if shared_ev_saved:
        ev = shared_ev_saved[0]
        title = (ev.get("title") or "Compromisso").strip()
        when = _format_scheduled_pt(ev.get("scheduled_at"))
        cal_name = ""
        if shared_cals:
            cal_name = (shared_cals[0].get("name") or "").strip()
        if not cal_name and shared_setup:
            cal_name = str(
                shared_setup.get("calendar_name") or shared_setup.get("name") or ""
            ).strip()
        if not cal_name and shared_event:
            cal_name = str(
                shared_event.get("calendar_name") or shared_event.get("name") or ""
            ).strip()
        cal_part = f" na agenda «{cal_name}»" if cal_name else " na agenda"
        extra = f" Avisos: {'; '.join(warns[:3])}" if warns else ""
        return (
            f"Pronto! Marquei «{title}»{when}{cal_part}. "
            f"Os membros recebem aviso no telemóvel.{extra}"
        )

    if shared_members:
        cal_name = "Agenda"
        if shared_invite:
            cal_name = str(
                shared_invite.get("calendar_name") or shared_invite.get("name") or cal_name
            ).strip()
        elif shared_cals:
            cal_name = (shared_cals[0].get("name") or cal_name).strip()
        extra = f" Avisos: {'; '.join(warns[:3])}" if warns else ""
        pending_n = sum(
            1 for m in shared_members if str(m.get("status") or "") == "pending"
        )
        if pending_n == len(shared_members):
            return (
                f"Convite registado na agenda «{cal_name}». "
                "A pessoa verá a agenda ao entrar no EGO com o mesmo e-mail."
                f"{extra}"
            )
        if pending_n:
            return (
                f"Adicionei na agenda «{cal_name}»: alguns já têm acesso, "
                "outros verão quando criarem conta com o e-mail convidado."
                f"{extra}"
            )
        return (
            f"Pronto! Adicionei {len(shared_members)} pessoa(s) na agenda «{cal_name}». "
            f"Já têm acesso no app.{extra}"
        )

    if reminders_saved:
        row = reminders_saved[0]
        title = (row.get("title") or row.get("announce") or "seu lembrete").strip()
        when = _format_scheduled_pt(row.get("scheduled_at"))
        return f"Pronto! Agendei «{title}»{when} na agenda pessoal."

    if agenda_saved:
        row = agenda_saved[0]
        tit = (row.get("titulo") or row.get("title") or "compromisso").strip()
        return f"Pronto! Registrei na agenda pessoal: «{tit}»."

    if text and shared_setup and not created_cals and not shared_ev_saved:
        cal_name = str(
            shared_setup.get("calendar_name") or shared_setup.get("name") or "Agenda"
        ).strip()
        if warns:
            return (
                f"Não consegui criar a agenda «{cal_name}»: {warns[0]} "
                "Tente: Cria agenda Família"
            )
        return (
            f"Não consegui confirmar a criação da agenda «{cal_name}». "
            "Repita: Cria agenda Família"
        )

    if text and shared_invite and not shared_members:
        cal_name = str(
            shared_invite.get("calendar_name") or shared_invite.get("name") or "Agenda"
        ).strip()
        if warns:
            return (
                f"Não consegui adicionar na agenda «{cal_name}»: {warns[0]} "
                "Crie a agenda primeiro ou confirme o e-mail da conta."
            )
        return (
            f"Não consegui confirmar o convite na agenda «{cal_name}». "
            "Primeiro: Cria agenda Família. Depois convide o e-mail."
        )

    if text and shared_event and not shared_ev_saved:
        cal_name = str(
            shared_event.get("calendar_name") or shared_event.get("name") or "Agenda"
        ).strip()
        if warns:
            return (
                f"Não consegui marcar na agenda «{cal_name}»: {warns[0]} "
                "Confirme o nome da agenda e a data/hora."
            )
        return (
            f"Não consegui confirmar na agenda «{cal_name}». "
            "Repita: «marca na agenda familia» ou «marca na agenda pessoal»."
        )

    if text and shared_delete and not deleted_cals:
        cal_name = str(
            shared_delete.get("calendar_name") or shared_delete.get("name") or "Agenda"
        ).strip()
        if warns:
            return (
                f"Não consegui apagar a agenda «{cal_name}»: {warns[0]} "
                "Só quem criou a agenda pode apagá-la."
            )
        return (
            f"Não consegui confirmar a remoção da agenda «{cal_name}». "
            "Repita: Apaga a agenda Família"
        )

    if shared_invite and not shared_members:
        cal_name = str(
            shared_invite.get("calendar_name") or shared_invite.get("name") or "Agenda"
        ).strip()
        if warns:
            return (
                f"Não consegui adicionar na agenda «{cal_name}»: {warns[0]} "
                "Use o e-mail exacto da Conta no app."
            )
        return (
            f"Não consegui confirmar o convite na agenda «{cal_name}». "
            "Repita: Convida email@exemplo.com para a agenda Família"
        )

    if pending_rem and not reminders_saved:
        if warns:
            return f"Entendi o lembrete, mas não consegui agendar: {warns[0]}"
        item = pending_rem[0]
        title = (item.get("title") or "lembrete").strip()
        when = _format_scheduled_pt(item.get("scheduled_at"))
        return (
            f"Quase lá: confirme data e hora do lembrete «{title}»{when}. "
            "Ex.: «hoje às 13h» ou «sexta às 15h»."
        )

    if pending_ag and not agenda_saved:
        if warns:
            return f"Não consegui guardar na agenda: {warns[0]}"
        return "Entendi o hábito; informe dias da semana e horário (ex.: seg, qua, sex às 7h)."

    if (
        text
        and _looks_like_false_schedule_success(text)
        and not reminders_saved
        and not agenda_saved
        and not shared_ev_saved
    ):
        if warns:
            return f"Não consegui gravar na agenda: {warns[0]}"
        return (
            "Não consegui confirmar na agenda. "
            "Repita: Marca na agenda pessoal consulta amanhã às 9h"
        )

    if text:
        return text

    if warns:
        return warns[0]

    return "Recebi sua mensagem. Pode repetir ou detalhar um pouco mais?"
