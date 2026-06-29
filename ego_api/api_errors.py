"""Mensagens de erro legíveis para o app (em vez de «Erro interno.»)."""

from __future__ import annotations


def friendly_api_error(exc: BaseException | str, *, context: str = "") -> str:
    raw = str(exc).strip() if exc is not None else ""
    if not raw and exc is not None:
        raw = type(exc).__name__
    low = raw.lower()

    if not raw:
        return _default(context)

    if "data/hora inválida" in low or "horizonte permitido" in low:
        return (
            "Data/hora inválida ou no passado. "
            "Toque na data e escolha um dia futuro no calendário."
        )
    if "horário inválido" in low:
        return "Horário inválido. Use HH:MM (ex.: 10:00)."

    if "row-level security" in low or "rls" in low or "42501" in low:
        return "Sem permissão para gravar. Saia da conta e entre de novo."

    if (
        "jwt" in low
        or "expired" in low
        or "invalid claim" in low
        or "sessão expirada" in low
        or "sessão inválida" in low
    ):
        return "Sessão expirada. Saia e entre de novo."

    if "42p01" in low or "does not exist" in low or "could not find" in low:
        if "reminders" in low:
            return (
                "Servidor sem tabela de compromissos. "
                "Contacte o suporte EGO-AI."
            )
        if "agenda" in low:
            return "Servidor sem tabela de hábitos. Contacte o suporte EGO-AI."
        return "Configuração do servidor incompleta. Tente mais tarde."

    if "timeout" in low or "timed out" in low or "connection" in low:
        return "Servidor demorou a responder. Tente em instantes."

    if any(
        x in low
        for x in (
            "gemini",
            "google",
            "openai",
            "quota",
            "429",
            "resource exhausted",
            "cota",
        )
    ):
        return raw[:500]

    if "limite" in low or "upgrade" in low:
        return raw[:500]

    if any(
        marker in raw
        for marker in (
            "Data/hora",
            "Horário",
            "Sessão",
            "Limite",
            "Não foi",
            "Não consegui",
            "obrigatório",
        )
    ):
        return raw[:500]

    default = _default(context)
    if context == "chat" and raw:
        return f"{default} ({raw[:200]})"
    return default


def _default(context: str) -> str:
    hints = {
        "reminder": (
            "Não foi possível marcar o compromisso. "
            "Saia e entre de novo, escolha uma data futura e tente outra vez."
        ),
        "agenda": (
            "Não foi possível criar o hábito. "
            "Saia e entre de novo e tente outra vez."
        ),
        "auth": "Não foi possível validar a sessão. Saia e entre de novo.",
        "chat": (
            "Não foi possível processar a mensagem. "
            "Tente de novo ou marque pela agenda manual (+ Novo compromisso)."
        ),
    }
    return hints.get(
        context,
        "Não foi possível concluir agora. Tente de novo ou saia e entre na conta.",
    )
