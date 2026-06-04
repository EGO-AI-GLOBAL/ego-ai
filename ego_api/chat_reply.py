"""Garante texto visível no chat quando o LLM só devolve marcadores EGO_*."""

from __future__ import annotations

from datetime import datetime


def _format_scheduled_pt(iso_val: object) -> str:
    if not iso_val:
        return ""
    try:
        s = str(iso_val).replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        return f" para {dt.strftime('%d/%m às %H:%M')}"
    except Exception:
        return ""


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
) -> str:
    warns = warnings or []
    shared_members = shared_members_saved or []
    text = (reply_clean or "").strip()
    if text and shared_invite and not shared_members:
        if warns:
            return (
                f"Não consegui adicionar na agenda compartilhada: {warns[0]} "
                "Confirme o e-mail da conta e o nome da agenda."
            )
    if text:
        return text

    pending_rem = rem_items or []
    pending_ag = ag_items or []
    shared_cals = shared_calendars_saved or []
    shared_ev = shared_events_saved or []

    if shared_ev:
        ev = shared_ev[0]
        title = (ev.get("title") or "Compromisso").strip()
        when = _format_scheduled_pt(ev.get("scheduled_at"))
        cal_name = ""
        if shared_cals:
            cal_name = (shared_cals[0].get("name") or "").strip()
        if not cal_name and shared_setup:
            cal_name = str(
                shared_setup.get("calendar_name") or shared_setup.get("name") or ""
            ).strip()
        cal_part = f" na agenda «{cal_name}»" if cal_name else " na agenda compartilhada"
        extra = ""
        if warns:
            extra = f" Avisos: {'; '.join(warns[:3])}"
        return (
            f"Pronto! Marquei «{title}»{when}{cal_part}. "
            f"Os membros recebem aviso no telemóvel.{extra}"
        )

    if shared_cals and shared_setup:
        cal_name = str(
            shared_setup.get("calendar_name") or shared_setup.get("name") or "Agenda"
        ).strip()
        extra = ""
        if warns:
            extra = f" Avisos: {'; '.join(warns[:3])}"
        return (
            f"Pronto! Criei a agenda compartilhada «{cal_name}». "
            f"Vê-la na aba Agenda → Compartilhada.{extra}"
        )

    if shared_invite:
        cal_name = str(
            shared_invite.get("calendar_name") or shared_invite.get("name") or "Agenda"
        ).strip()
        if shared_members:
            extra = ""
            if warns:
                extra = f" Avisos: {'; '.join(warns[:3])}"
            return (
                f"Pronto! Adicionei {len(shared_members)} pessoa(s) na agenda «{cal_name}». "
                f"Os convidados já veem a agenda no app.{extra}"
            )
        if warns:
            return (
                f"Não consegui adicionar na agenda «{cal_name}»: {warns[0]} "
                "Use o e-mail exacto da Conta no app."
            )
        return (
            f"Não consegui confirmar o convite na agenda «{cal_name}». "
            "Repita: Convida email@exemplo.com para a agenda compartilhada Família"
        )

    if reminders_saved:
        row = reminders_saved[0]
        title = (row.get("title") or row.get("announce") or "seu lembrete").strip()
        when = _format_scheduled_pt(row.get("scheduled_at"))
        return f"Pronto! Agendei o lembrete «{title}»{when} na sua agenda pessoal."

    if agenda_saved:
        row = agenda_saved[0]
        tit = (row.get("titulo") or row.get("title") or "compromisso").strip()
        return f"Pronto! Registrei na agenda: «{tit}»."

    if pending_rem:
        if warns:
            return f"Entendi o lembrete, mas não consegui agendar: {warns[0]}"
        item = pending_rem[0]
        title = (item.get("title") or "lembrete").strip()
        when = _format_scheduled_pt(item.get("scheduled_at"))
        return (
            f"Quase lá: confirme data e hora do lembrete «{title}»{when}. "
            "Ex.: «hoje às 13h» ou «sexta às 15h»."
        )

    if pending_ag:
        if warns:
            return f"Não consegui guardar na agenda: {warns[0]}"
        return "Entendi o hábito; informe dias da semana e horário (ex.: seg, qua, sex às 7h)."

    if warns:
        return warns[0]

    return "Recebi sua mensagem. Pode repetir ou detalhar um pouco mais?"
