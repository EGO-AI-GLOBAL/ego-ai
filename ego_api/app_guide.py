"""Guia do app para os 12 avatares — escuta no chat; nenhuma agenda pelo chat; só explica."""

from __future__ import annotations

import re

APP_FEATURES_HELP = """
GUIA DO APP (use SÓ quando o utilizador perguntar como usar algo — todos os 12 avatares sabem isto):

CHAT (texto):
- Menu ☰ → Chat. Escreva na caixa e toque na seta ↑ para enviar.
- Toque no nome/avatar no topo para trocar de assistente.

VOZ:
- Toque no microfone → fale 2–3 segundos → o microfone vira seta ↑ no mesmo sítio → toque na seta para enviar.
- A resposta aparece em texto e o avatar fala (foto parada, vídeo enquanto fala).

MONSTRINHOS DO HUMOR 💜:
- Menu ☰ → Monstrinhos do Humor.
- 1 toque por dia no emoji do humor; missões diárias, sementes, ranking e partilha em Stories.
- Não marca agenda — é check-in emocional e gamificação leve.

EGO DE BOLSO 🥚:
- Menu ☰ → EGO de Bolso.
- Pet/ovo com níveis (estilo anos 90); missões diárias ligam chat, voz, Monstrinhos e Agenda.
- Progresso é pelo uso do app nas abas certas — o avatar não «dá nível» pelo chat.

AGENDA PESSOAL (só na aba Agenda — NUNCA pelo chat):
- Menu ☰ → Agenda → + Novo compromisso → título, data, hora → Marcar compromisso.
- Lembretes, hábitos, concluir e apagar na própria aba.

AGENDA COMPARTILHADA / FAMÍLIA / EQUIPE (só na aba Agenda — NUNCA pelo chat):
- Menu ☰ → Agenda → Gerir agendas → Criar agenda (nome) → Convidar membro (e-mail de quem já tem conta).
- Marcar evento: abrir essa agenda → + Novo compromisso → título, data, hora.
- Convidar, apagar agenda ou evento: sempre na aba Agenda — o avatar no chat não executa nada disto.

PDF / DOCUMENTOS:
- No Chat, ícone de documento ao lado da mensagem → escolher PDF ou foto.
- Depois: «Enviar resumo» ou pedir perguntas sobre o conteúdo.

PLANOS E USO:
- Menu ☰ → Planos (assinatura) e Uso (percentagem do limite diário do plano).

CONTA:
- Menu ☰ → Conta → perfil, trocar avatar, apagar conta.

DESABAFO NOTURNO (~21h):
- Modo de escuta; de manhã o utilizador confirma o que quiser na aba Agenda — avatar não cria itens.

REGRAS AO EXPLICAR:
- Máximo 3 passos curtos; tom do seu avatar; depois volte à escuta («Quer experimentar agora?»).
- Não invente botões que não existem (ex.: «Ouvir ao responder» já não existe).
- Se não perguntaram como usar, NÃO dê tutorial — escute e acolha.
"""

APP_GUIDE_LLM_INSTRUCTION = f"""
CHAT = ESCUTA CLÍNICA (obrigatório — os 12 avatares):
- Você NÃO usa agenda pelo chat — nem pessoal, nem compartilhada/família/equipe.
- Proibido: marcar, apagar, cancelar, criar agenda, convidar membros, lembretes ou compromissos pelo chat.
- Nunca use marcadores [[EGO_*:...]] nem diga que já gravou, convidou ou criou algo.
- NUNCA pergunte «quer que eu agende?», «qual horário?» para marcar, nem conduza wizard de agenda.
- Se pedirem AÇÃO na agenda (marcar, convidar, criar agenda família, etc. — não tutorial):
  diga em 1–2 frases que isso é na aba Agenda (pessoal ou Gerir agendas) e volte à escuta emocional.
- Se perguntarem «o que tenho hoje?»: resuma só se a lista vier no contexto; não sugira marcar.

AJUDA SOBRE O APP (quando pedirem explicitamente):
- «Como usar…», «como funciona…», «onde fica…» → explique com o GUIA abaixo (máx. 3 passos).
- Vale para agenda pessoal E compartilhada, Monstrinhos, Bolso, voz, PDF, planos, conta.
- Pergunta de tutorial NÃO é pedido para executar — só explique os passos na aba certa.

DESABAFO NOTURNO (21h):
- Só acolhimento e escuta. Itens ficam para o utilizador confirmar de manhã na aba Agenda — você não cria nada.

TOM:
- Melhor psicólogo e melhor psiquiatra do mundo em escuta: caloroso, presente, sem julgar.
- Tutorial só quando pedirem; conversa normal o resto do tempo.

{APP_FEATURES_HELP}
"""

_APP_HELP_INTENT = re.compile(
    r"(?i)("
    r"como\s+(usar|uso|funciona|faço|fazer|marco|marcar|acesso|abro|entro|ativo|começo|comeco|convidar|criar)|"
    r"onde\s+(fica|está|esta|acho|encontro)|"
    r"o\s+que\s+(é|e)\s+(o\s+)?(ego|monstrinho|bolso|agenda|app)|"
    r"me\s+(explica|ensina|mostra)|"
    r"\btutorial\b|"
    r"ajuda\s+(com|no|na|para)|"
    r"funcionalidades?\s+do\s+app|"
    r"como\s+é\s+que\s+(uso|funciona|marco)"
    r")"
)


def looks_like_app_help_intent(text: str) -> bool:
    """True quando o utilizador quer aprender a usar o app — não agir na agenda."""
    t = (text or "").strip()
    if not t:
        return False
    return bool(_APP_HELP_INTENT.search(t))


def looks_like_any_agenda_action_intent(text: str) -> bool:
    """Pedido para agir na agenda (pessoal ou compartilhada) — não confundir com tutorial."""
    t = (text or "").strip()
    if not t or looks_like_app_help_intent(t):
        return False
    from ego_api import chat_schedule as cs

    if cs.looks_like_schedule_intent(t):
        return True
    if cs.looks_like_dismiss_commitment_intent(t):
        return True
    if cs.parse_invite_from_plain_text(t):
        return True
    if cs.parse_create_shared_calendar_from_plain_text(t):
        return True
    if cs.parse_delete_shared_calendar_from_plain_text(t):
        return True
    return False


def app_guide_context_block() -> str:
    return (
        "\n\n=== MODO ESCUTA (sem agenda no chat) ===\n"
        "Não marque, convide, crie nem apague — agenda pessoal nem compartilhada.\n"
        "Tudo na aba Agenda, manual. Chat = escuta + explicar COMO USAR se perguntarem.\n"
        "=== FIM MODO ESCUTA ===\n"
    )


def manual_agenda_redirect_reply(
    user_text: str = "",
    *,
    supabase=None,
    user_id: str | None = None,
) -> str:
    """Resposta fixa quando pedem ação na agenda com chat_agenda desligado."""
    from ego_api import chat_schedule as cs

    t = (user_text or "").strip()

    if t and cs.parse_invite_from_plain_text(t):
        return (
            "Aqui no chat eu só te escuto — não convido ninguém por você. "
            "Para convidar: menu Agenda → Gerir agendas → escolha a agenda → Convidar membro "
            "(e-mail de quem já tem conta EGO-AI). Quer me contar o que precisas?"
        )

    if t and (
        cs.parse_create_shared_calendar_from_plain_text(t)
        or cs._user_requests_new_calendar(t)
    ):
        return (
            "Não crio agendas compartilhadas pelo chat. "
            "Menu Agenda → Gerir agendas → Criar agenda → nome e convites. "
            "Quer falar para que é essa agenda?"
        )

    if t and cs.parse_delete_shared_calendar_from_plain_text(t):
        return (
            "Não apago agendas pelo chat. "
            "Menu Agenda → Gerir agendas → escolha a agenda → apagar. "
            "Quer me contar o que está a incomodar?"
        )

    scope = None
    if t and supabase and user_id:
        scope = cs.detect_scope_from_user_text(t, supabase, user_id)
    elif t and (cs.user_named_shared_calendar(t) or cs._SCOPE_SHARED.search(t)):
        scope = "shared"

    if scope == "shared":
        return (
            "Aqui no chat eu te escuto — não marco na agenda da família/equipe por você. "
            "Para marcar: menu Agenda → Gerir agendas → escolha a agenda → + Novo compromisso → "
            "título, data e hora. Quer me contar o que está por trás desse compromisso?"
        )

    return (
        "Aqui no chat eu te escuto com calma — não marco compromissos por você. "
        "Agenda pessoal: menu Agenda → + Novo compromisso → data, hora → Marcar. "
        "Agenda família/equipe: Agenda → Gerir agendas. "
        "Quer me contar o que está por trás desse compromisso?"
    )
