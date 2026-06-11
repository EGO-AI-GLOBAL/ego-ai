"""OpenAI Realtime API — client secrets e instruções de sessão (chave só no servidor)."""

from __future__ import annotations

import hashlib
from typing import Any

import httpx

from ego_api.config import (
    openai_api_key,
    openai_realtime_enabled,
    openai_realtime_max_output_tokens_phone,
    openai_realtime_model,
    openai_realtime_phone_fast,
    openai_realtime_vad_eagerness,
    openai_realtime_vad_silence_ms,
    openai_realtime_voice_female,
    openai_realtime_voice_male,
)
from ego_api.gemini import GEMINI_SYSTEM_INSTRUCTION, _identity_instruction
from ego_api.wellness_coach import WELLNESS_COACH_INSTRUCTION
from ego_api.persona import apply_assistant_name_from_avatar, is_male_avatar
from ego_api.request_ctx import UserSession, get_session

_OPENAI_REALTIME_SECRETS_URL = "https://api.openai.com/v1/realtime/client_secrets"
_OPENAI_REALTIME_CALLS_URL = "https://api.openai.com/v1/realtime/calls"
_REALTIME_WS_BASE = "wss://api.openai.com/v1/realtime"


def is_available() -> bool:
    return openai_realtime_enabled()


def resolve_openai_voice(avatar_id: str | None) -> str:
    if is_male_avatar(avatar_id):
        return openai_realtime_voice_male()
    return openai_realtime_voice_female()


def _history_snippet(
    messages: list[dict],
    max_turns: int = 8,
    *,
    max_chars: int = 500,
) -> str:
    lines: list[str] = []
    for m in messages[-max_turns:]:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if not content or role not in ("user", "assistant"):
            continue
        label = "Utilizador" if role == "user" else "Assistente"
        lines.append(f"{label}: {content[:max_chars]}")
    if not lines:
        return ""
    return "\n\nHistórico recente da conversa:\n" + "\n".join(lines)


def _phone_core_turbo(sess: UserSession) -> str:
    alias = (sess.assistant_name or "EGO-AI").strip() or "EGO-AI"
    uname = (sess.user_name or "").strip()
    who = f"Utilizador: {uname}. " if uname else ""
    return (
        f"Você é «{alias}» (EGO-AI), assistente pessoal em ligação de voz. {who}"
        "Acolhedor, direto e confiante — como um amigo inteligente ao telefone.\n"
    )


_REALTIME_PHONE_PERSONA_TURBO = """
MODO TURBO — VOZ EM TEMPO REAL (latência mínima):
- Responda assim que o utilizador fizer uma pausa curta; priorize velocidade.
- Máximo 1 frase por turno (2 só se for indispensável). Nunca explique demais.
- Português do Brasil natural, tom energético e humano — como ligação real.
- Seja direto; corte enrolação. Não repita o que o utilizador disse.
- Sem listas, markdown, emojis ou frases tipo "como assistente de IA".
- Se interromperem, pare imediatamente e adapte-se.
- Não faça introduções longas; vá ao ponto.
- Exemplos de ritmo: "4." / "Começa pelo gancho nos primeiros 3 segundos." / "Depende do orçamento — iPhone Pro ou Galaxy Ultra no topo."
"""

_REALTIME_PHONE_PERSONA_FAST = _REALTIME_PHONE_PERSONA_TURBO

_REALTIME_PHONE_PERSONA = """
MODO CHAMADA AO VIVO (parecer uma pessoa real):
- Estás numa ligação telefónica contínua, não num chatbot. Soa presente, caloroso e espontâneo.
- Reage com naturalidade: valida emoções ("imagino", "faz sentido"), pequenas pausas na fala, tom humano.
- Por turno: 2 a 3 frases fluidas para ouvir em voz alta — nem monólogo longo, nem resposta seca de uma linha.
- Varia o estilo: às vezes pergunta curta, às vezes conselho prático; evita repetir a mesma abertura.
- Se o utilizador interromper, cala-te de imediato e adapta-te ao que disse.
- Português do Brasil. Sem listas, markdown, emojis ou frases tipo "como assistente de IA".
"""


def build_phone_instructions(
    sess: UserSession,
    *,
    avatar_id: str | None = None,
    client_history: list[dict] | None = None,
) -> str:
    """Persona para chamada — turbo por defeito (EGO_REALTIME_PHONE_FAST=1)."""
    apply_assistant_name_from_avatar(avatar_id)
    turbo = openai_realtime_phone_fast()
    if turbo:
        hist = _history_snippet(client_history or [], max_turns=2, max_chars=120)
        core = _phone_core_turbo(sess) + _REALTIME_PHONE_PERSONA_TURBO
    else:
        hist = _history_snippet(client_history or [], max_turns=6, max_chars=500)
        core = (
            GEMINI_SYSTEM_INSTRUCTION
            + WELLNESS_COACH_INSTRUCTION
            + _identity_instruction(sess)
            + _REALTIME_PHONE_PERSONA
        )
    if hist:
        return core + hist
    return core


def build_session_config(
    *,
    instructions: str,
    voice: str,
    model_id: str,
    phone_call: bool,
) -> dict[str, Any]:
    audio_input: dict[str, Any] = {
        "format": {"type": "audio/pcm", "rate": 24000},
        "turn_detection": _turn_detection_for_mode(phone_call),
    }
    if phone_call:
        if not openai_realtime_phone_fast():
            audio_input["transcription"] = {
                "model": "gpt-4o-mini-transcribe",
                "language": "pt",
            }
    else:
        audio_input["transcription"] = {
            "model": "gpt-4o-mini-transcribe",
            "language": "pt",
        }

    session: dict[str, Any] = {
        "type": "realtime",
        "model": model_id,
        "instructions": instructions,
        "output_modalities": ["audio"],
        "audio": {
            "input": audio_input,
            "output": {
                "format": {"type": "audio/pcm", "rate": 24000},
                "voice": voice,
            },
        },
    }
    if phone_call:
        session["max_output_tokens"] = openai_realtime_max_output_tokens_phone()
    return session


def build_realtime_instructions(
    sess: UserSession,
    *,
    avatar_id: str | None = None,
    lang_code: str = "pt-BR",
    client_history: list[dict] | None = None,
    phone_call: bool = False,
) -> str:
    from ego_api.gemini import VOICE_REPLY_INSTRUCTION, build_system_instruction

    if phone_call:
        return build_phone_instructions(
            sess, avatar_id=avatar_id, client_history=client_history
        )
    apply_assistant_name_from_avatar(avatar_id)
    base = build_system_instruction(sess, lang_code, agenda_context="")
    hist = _history_snippet(client_history or [], max_turns=10)
    return (
        base
        + "\n\n"
        + VOICE_REPLY_INSTRUCTION
        + "\nFale em português do Brasil de forma natural e calorosa."
        + hist
    )


def _turn_detection_for_mode(phone_call: bool) -> dict[str, Any] | None:
    if not phone_call:
        return None
    from ego_api.config import read_env

    mode = read_env("EGO_REALTIME_VAD_MODE", "semantic").lower()
    if mode == "server":
        return {
            "type": "server_vad",
            "threshold": 0.5,
            "prefix_padding_ms": 200,
            "silence_duration_ms": openai_realtime_vad_silence_ms(),
            "create_response": True,
            "interrupt_response": True,
        }
    return {
        "type": "semantic_vad",
        "eagerness": openai_realtime_vad_eagerness(),
        "create_response": True,
        "interrupt_response": True,
    }


def create_client_secret(
    *,
    instructions: str,
    voice: str,
    model: str | None = None,
    user_id: str = "",
    phone_call: bool = False,
) -> tuple[dict[str, Any] | None, str | None]:
    """Cria token efémero (ek_…) para o browser ligar ao Realtime via WebSocket."""
    key = openai_api_key()
    if not key:
        return None, "OpenAI Realtime não configurado (OPENAI_API_KEY em falta)."

    model_id = (model or openai_realtime_model()).strip()
    session = build_session_config(
        instructions=instructions,
        voice=voice,
        model_id=model_id,
        phone_call=phone_call,
    )
    body: dict[str, Any] = {
        "expires_after": {"anchor": "created_at", "seconds": 600},
        "session": session,
    }

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    if user_id:
        stable = hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:32]
        headers["OpenAI-Safety-Identifier"] = stable

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(_OPENAI_REALTIME_SECRETS_URL, json=body, headers=headers)
    except httpx.HTTPError as exc:
        return None, f"Falha ao contactar OpenAI: {exc}"

    if resp.status_code >= 400:
        detail = resp.text[:400] if resp.text else resp.reason_phrase
        return None, f"OpenAI Realtime ({resp.status_code}): {detail}"

    data = resp.json()
    secret = data.get("value") or data.get("client_secret", {}).get("value")
    if not secret:
        return None, "OpenAI não devolveu client secret."

    expires_at = data.get("expires_at") or data.get("client_secret", {}).get("expires_at")
    ws_url = f"{_REALTIME_WS_BASE}?model={model_id}"
    return (
        {
            "client_secret": str(secret),
            "expires_at": expires_at,
            "model": model_id,
            "ws_url": ws_url,
            "voice": voice,
        },
        None,
    )


def prepare_session_for_user(
    user_id: str,
    avatar_id: str,
    client_history: list[dict] | None = None,
    *,
    phone_call: bool = False,
) -> tuple[dict[str, Any] | None, str | None]:
    sess = get_session()
    if not sess or sess.user_id != user_id:
        return None, "Sessão inválida."
    if phone_call:
        instructions = build_phone_instructions(
            sess, avatar_id=avatar_id, client_history=client_history
        )
    else:
        instructions = build_realtime_instructions(
            sess,
            avatar_id=avatar_id,
            client_history=client_history,
            phone_call=False,
        )
    voice = resolve_openai_voice(avatar_id)
    return create_client_secret(
        instructions=instructions,
        voice=voice,
        user_id=user_id,
        phone_call=phone_call,
    )


def prepare_webrtc_for_user(
    user_id: str,
    avatar_id: str,
    sdp_offer: str,
    client_history: list[dict] | None = None,
) -> tuple[str | None, str | None]:
    return create_webrtc_call(
        sdp_offer,
        user_id,
        avatar_id,
        client_history=client_history,
        phone_call=True,
    )


def create_webrtc_call(
    sdp_offer: str,
    user_id: str,
    avatar_id: str,
    client_history: list[dict] | None = None,
    *,
    phone_call: bool = True,
) -> tuple[str | None, str | None]:
    """WebRTC unified interface — menor latência que WebSocket no browser."""
    key = openai_api_key()
    if not key:
        return None, "OpenAI Realtime não configurado."

    sdp = (sdp_offer or "").strip()
    if len(sdp) < 32:
        return None, "SDP inválido."

    sess = get_session()
    if not sess or sess.user_id != user_id:
        return None, "Sessão inválida."

    if phone_call:
        instructions = build_phone_instructions(
            sess, avatar_id=avatar_id, client_history=client_history
        )
    else:
        instructions = build_realtime_instructions(
            sess, avatar_id=avatar_id, client_history=client_history, phone_call=False
        )
    voice = resolve_openai_voice(avatar_id)
    model_id = openai_realtime_model().strip()
    session = build_session_config(
        instructions=instructions,
        voice=voice,
        model_id=model_id,
        phone_call=phone_call,
    )

    import json

    headers = {"Authorization": f"Bearer {key}"}
    if user_id:
        stable = hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:32]
        headers["OpenAI-Safety-Identifier"] = stable

    try:
        with httpx.Client(timeout=45.0) as client:
            resp = client.post(
                _OPENAI_REALTIME_CALLS_URL,
                data={
                    "sdp": sdp,
                    "session": json.dumps(session),
                },
                headers=headers,
            )
    except httpx.HTTPError as exc:
        return None, f"Falha WebRTC OpenAI: {exc}"

    if resp.status_code >= 400:
        detail = resp.text[:400] if resp.text else resp.reason_phrase
        return None, f"OpenAI WebRTC ({resp.status_code}): {detail}"

    answer = (resp.text or "").strip()
    if not answer:
        return None, "OpenAI não devolveu SDP de resposta."
    return answer, None
