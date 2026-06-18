"""Descarrego da noite — áudio/texto → rascunhos de agenda + compras."""

from __future__ import annotations

import json
import re
from typing import Any

from ego_api import gemini, habits_db
from ego_api.request_ctx import get_session
from ego_api.schedule_tz import local_now_from_session


NIGHT_DUMP_EXTRACT_PROMPT = """
Analise o texto do utilizador (descarrego noturno) e devolva APENAS JSON válido, sem markdown:
{
  "comfort_reply": "2-3 frases acolhedoras em português do Brasil, tom de amigo/psicólogo leve",
  "items": [
    {
      "type": "reminder",
      "title": "título curto do compromisso",
      "scheduled_at": "ISO-8601 com offset do fuso do utilizador",
      "shopping_items": [{"title": "nome", "category": "mercado|remedio|outros"}]
    },
    {
      "type": "shopping_orphan",
      "title": "item avulso",
      "category": "mercado|remedio|outros"
    }
  ]
}

Regras:
- Extraia compromissos com data/hora relativas (amanhã, segunda, 9h, meio-dia, fim da tarde).
- Se disser «passar no mercado» ou «ir ao mercado», crie reminder «Ir ao mercado» com shopping_items dos produtos mencionados.
- Itens só de compra sem hora → shopping_orphan.
- Se não houver compromissos nem compras, items pode ser [].
- comfort_reply sempre presente e humano.
"""


def _parse_json_blob(text: str) -> dict | None:
    raw = (text or "").strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def _normalize_items(items: Any) -> list[dict]:
    if not isinstance(items, list):
        return []
    out: list[dict] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        t = str(it.get("type") or "").strip().lower()
        if t == "reminder":
            shopping = []
            for s in it.get("shopping_items") or []:
                if isinstance(s, str) and s.strip():
                    shopping.append({"title": s.strip(), "category": "mercado"})
                elif isinstance(s, dict) and (s.get("title") or "").strip():
                    shopping.append(
                        {
                            "title": str(s.get("title")).strip()[:300],
                            "category": str(s.get("category") or "mercado")[:32],
                        }
                    )
            out.append(
                {
                    "type": "reminder",
                    "title": str(it.get("title") or "Compromisso").strip()[:500],
                    "scheduled_at": str(it.get("scheduled_at") or "").strip(),
                    "shopping_items": shopping,
                }
            )
        elif t == "shopping_orphan":
            out.append(
                {
                    "type": "shopping_orphan",
                    "title": str(it.get("title") or "Item").strip()[:300],
                    "category": str(it.get("category") or "mercado")[:32],
                }
            )
    return out


def extract_from_transcript(transcript: str, lang: str = "pt-BR") -> tuple[str, list[dict]]:
    sess = get_session()
    loc = local_now_from_session(sess) if sess else None
    clock = ""
    if loc:
        clock = f"\nAgora local: {loc.isoformat(timespec='seconds')}\n"
    prompt = (
        NIGHT_DUMP_EXTRACT_PROMPT
        + clock
        + "\nTexto do utilizador:\n"
        + (transcript or "")[:12000]
    )
    reply = gemini.generate_reply(
        prompt,
        conversation_messages=[],
        lang_code=lang,
        agenda_context="",
    )
    if gemini.is_gemini_error_reply(reply):
        return (
            "Recebi o que você compartilhou. Amanhã confira os rascunhos na Agenda e ajuste o que precisar.",
            [],
        )
    parsed = _parse_json_blob(reply)
    if not parsed:
        return (
            "Obrigado por desabafar. Descanse — amanhã organizamos juntos na Agenda.",
            [],
        )
    comfort = str(parsed.get("comfort_reply") or "").strip()
    items = _normalize_items(parsed.get("items"))
    if not comfort:
        comfort = "Entendi. Deixe comigo — amanhã você só confirma na Agenda. Boa noite."
    return comfort, items


def process_night_dump(
    supabase,
    user_id: str,
    *,
    text: str = "",
    audio_bytes: bytes | None = None,
    audio_mime: str | None = None,
) -> tuple[dict | None, str | None]:
    transcript = (text or "").strip()
    if audio_bytes and len(audio_bytes) >= 128:
        transcript = (
            gemini.transcribe_voice_audio(audio_bytes, audio_mime) or transcript
        ).strip()
    if not transcript:
        return None, "Envie um áudio ou texto com o que está na sua cabeça."

    lang, _ = gemini.detect_language(transcript)
    comfort, items = extract_from_transcript(transcript, lang)
    row = habits_db.insert_draft(
        supabase,
        user_id,
        comfort_reply=comfort,
        items=items,
    )
    if not row:
        return None, "Não foi possível guardar o descarrego. Tente de novo."
    return {
        "draft": row,
        "comfort_reply": comfort,
        "items": items,
        "transcript": transcript[:2000],
    }, None


def confirm_draft_items(
    supabase,
    user_id: str,
    draft_id: str,
    item_indices: list[int] | None = None,
) -> tuple[list[dict], list[dict], list[str]]:
    """Confirma itens do rascunho → reminders + shopping. Retorna (reminders, shopping, errors)."""
    from ego_api import db

    draft = habits_db.get_draft(supabase, user_id, draft_id)
    if not draft or draft.get("status") != "pending":
        return [], [], ["Rascunho não encontrado ou já confirmado."]
    items = draft.get("items") or []
    if not isinstance(items, list):
        items = []

    indices = item_indices if item_indices is not None else list(range(len(items)))
    reminders_out: list[dict] = []
    shopping_out: list[dict] = []
    errors: list[str] = []
    remaining = list(items)

    for idx in sorted(indices, reverse=True):
        if idx < 0 or idx >= len(items):
            continue
        it = items[idx]
        itype = str(it.get("type") or "")
        if itype == "reminder":
            ok, err, rem = db.insert_reminder(
                supabase,
                user_id,
                title=str(it.get("title") or "Compromisso"),
                scheduled_at=it.get("scheduled_at"),
                announce=str(it.get("title") or ""),
            )
            if ok and rem:
                reminders_out.append(rem)
                rid = str(rem.get("id") or "")
                for s in it.get("shopping_items") or []:
                    title = s.get("title") if isinstance(s, dict) else str(s)
                    cat = s.get("category") if isinstance(s, dict) else "mercado"
                    row = habits_db.insert_shopping_item(
                        supabase,
                        user_id,
                        title=str(title or ""),
                        category=str(cat or "mercado"),
                        reminder_id=rid or None,
                    )
                    if row:
                        shopping_out.append(row)
                remaining.pop(idx)
            else:
                errors.append(err or f"Não gravou: {it.get('title')}")
        elif itype == "shopping_orphan":
            row = habits_db.insert_shopping_item(
                supabase,
                user_id,
                title=str(it.get("title") or "Item"),
                category=str(it.get("category") or "mercado"),
                reminder_id=None,
            )
            if row:
                shopping_out.append(row)
                remaining.pop(idx)
            else:
                errors.append(f"Não gravou item: {it.get('title')}")

    if not remaining:
        habits_db.delete_draft(supabase, user_id, draft_id)
    else:
        habits_db.update_draft_items(supabase, user_id, draft_id, remaining)

    return reminders_out, shopping_out, errors


def dismiss_draft_item(
    supabase,
    user_id: str,
    draft_id: str,
    item_index: int,
) -> tuple[bool, str | None]:
    """Remove um item do rascunho sem confirmar (Excluir na revisão matinal)."""
    draft = habits_db.get_draft(supabase, user_id, draft_id)
    if not draft or draft.get("status") != "pending":
        return False, "Rascunho não encontrado ou já confirmado."
    items = draft.get("items") or []
    if not isinstance(items, list):
        items = []
    if item_index < 0 or item_index >= len(items):
        return False, "Item não encontrado."
    remaining = list(items)
    remaining.pop(item_index)
    if not remaining:
        habits_db.delete_draft(supabase, user_id, draft_id)
    else:
        habits_db.update_draft_items(supabase, user_id, draft_id, remaining)
    return True, None
