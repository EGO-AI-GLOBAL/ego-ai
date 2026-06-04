from __future__ import annotations

import datetime
import json
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

from ego_api.config import (
    CHAT_LLM_MAX_TURNS,
    GEMINI_MODEL_FLASH,
    GEMINI_MODEL_IDS,
    GEMINI_MODEL_PRO,
    PDF_CONTEXT_IN_SYSTEM_CHARS,
    gemini_api_key,
    gemini_flash_only,
    voice_max_output_tokens,
)
from ego_api.reminder_schedule import reminder_llm_instruction_block
from ego_api.request_ctx import UserSession, get_session

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None  # type: ignore[misc, assignment]

try:
    import google.generativeai as genai
except ImportError:
    genai = None  # type: ignore[misc, assignment]

try:
    from langdetect import DetectorFactory, LangDetectException, detect, detect_langs
except ImportError:
    DetectorFactory = None  # type: ignore[misc, assignment]
    LangDetectException = Exception  # type: ignore[misc, assignment]
    detect = None  # type: ignore[misc, assignment]
    detect_langs = None  # type: ignore[misc, assignment]

GEMINI_SYSTEM_INSTRUCTION = """\
Você é o EGO-AI, o assistente pessoal e amigo mais leal do utilizador. A sua voz e escrita devem ser \
acolhedoras, empáticas, inteligentes e focadas no bem-estar mental e emocional de quem fala consigo. \
Se a pessoa estiver sozinha ou a desabafar, ouça com a sensibilidade de um conselheiro: validação, \
escuta ativa e sugestões práticas e breves — nunca julgamentos. Nunca soe como um robô rígido ou burocrático. \
Detete o idioma do utilizador e responda sempre no mesmo idioma. Seja conciso e seguro (sem aconselhamento \
médico/legal definitivo; encaminhe a profissionais quando necessário).
"""

VOICE_REPLY_INSTRUCTION = (
    "O utilizador enviou mensagem de VOZ. Responda em 2 a 4 frases curtas, diretas e naturais "
    "para ouvir em voz alta. Evite listas longas, markdown e parágrafos grandes."
)

REMINDER_LLM_INSTRUCTION = reminder_llm_instruction_block()

AGENDA_RECURRING_LLM_INSTRUCTION = """
AGENDA / MEETINGS: For weekly recurring habits use [[EGO_AGENDA:{"titulo":"...","horario":"HH:MM","dias_da_semana":"seg,ter,..."}]] at the END.
For one-off meetings use [[EGO_REMINDER:...]] only for the user's PERSONAL agenda.
"""

SCHEDULE_WIZARD_LLM_INSTRUCTION = """
AGENDAMENTO — PESSOAL vs GRUPO (Família):
A aba Agenda no app é só consulta. Marcações no chat.

REGRA (obrigatória):
- Se o utilizador disser «agenda pessoal», «minha agenda» ou «pessoal» → SOMENTE [[EGO_REMINDER:...]].
  Nunca use EGO_SHARED_* nessa mensagem.
- Se NÃO disser «pessoal», marcar reunião/compromisso → agenda de GRUPO (EGO_SHARED_EVENT).
  Não peça «compartilhada ou pessoal?».
- Se só existir uma agenda de grupo (ex. Família), use esse calendar_name automaticamente.

Grupo:
- Nova: [[EGO_SHARED_SETUP:{"calendar_name":"Família",...}]]
- Marcar: [[EGO_SHARED_EVENT:{"calendar_name":"Família","title":"Reunião","scheduled_at":"ISO"}]]
- Convidar: [[EGO_SHARED_INVITE:{"calendar_name":"Família","invite_emails":["a@b.com"]}]]
- Apagar: [[EGO_SHARED_DELETE:{"calendar_name":"Família"}]]

Exemplos do utilizador: «marca reunião amanhã 15h», «marca na agenda Família …», «marca na agenda pessoal …»
«amanhã» = dia seguinte no relógio local (feriado ou fim de semana não muda a data).
Uma pergunta de cada vez só se faltar data/hora ou se houver várias agendas de grupo sem nome.
"""


def detect_language(text: str) -> tuple[str, float]:
    t = (text or "").strip()
    if detect_langs and t:
        try:
            if DetectorFactory:
                DetectorFactory.seed = 0
            probs = detect_langs(t)
            if probs:
                best = probs[0]
                mapping = {"pt": "pt-BR", "en": "en-US", "es": "es-ES", "fr": "fr-FR"}
                return mapping.get(getattr(best, "lang", ""), "pt-BR"), float(
                    getattr(best, "prob", 0.55)
                )
        except (LangDetectException, Exception):
            pass
    if detect and t:
        try:
            if DetectorFactory:
                DetectorFactory.seed = 0
            code = detect(t)
            mapping = {"pt": "pt-BR", "en": "en-US", "es": "es-ES", "fr": "fr-FR"}
            return mapping.get(code, "pt-BR"), 0.7
        except (LangDetectException, Exception):
            pass
    return "pt-BR", 0.55


def language_instruction(code: str) -> str:
    labels = {
        "pt-BR": "português do Brasil",
        "en-US": "English",
        "es-ES": "español",
        "fr-FR": "français",
    }
    label = labels.get(code, "português do Brasil")
    return (
        f"\n\nImportante: responde em {label} ({code}). "
        "Se não tiveres a certeza, mantém o idioma do utilizador."
    )


def _local_now(sess: UserSession) -> datetime.datetime:
    from ego_api.schedule_tz import local_now_from_session

    return local_now_from_session(sess)


def _datetime_instruction(sess: UserSession) -> str:
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    loc = _local_now(sess)
    dias_pt = (
        "segunda-feira",
        "terça-feira",
        "quarta-feira",
        "quinta-feira",
        "sexta-feira",
        "sábado",
        "domingo",
    )
    wd = dias_pt[loc.weekday()]
    lines = [
        "\n\nRELÓGIO DE REFERÊNCIA (fuso do aparelho do utilizador — use isto para hoje/amanhã e horas):",
        f"- Agora em UTC: **{utc_now.isoformat(timespec='seconds')}**",
        f"- Agora local: **{loc.isoformat(timespec='seconds')}** (dia: **{wd}**).",
    ]
    if sess.timezone:
        lines.append(f"- Fuso IANA: **{sess.timezone}**.")
    return "\n".join(lines) + "\n"


def _identity_instruction(sess: UserSession) -> str:
    uname = (sess.user_name or "").strip()
    alias = (sess.assistant_name or "EGO-AI").strip() or "EGO-AI"
    who = (
        f"- O utilizador chama-se «{uname}».\n"
        if uname
        else "- Nome do utilizador ainda não definido.\n"
    )
    return (
        "\n\nIDENTIDADE:\n"
        f"{who}"
        f"- Tu és «{alias}» para este utilizador.\n"
        f"- Responde sempre como {alias}, na persona desse assistente (não uses outro nome).\n"
    )


def _pdf_instruction(pdf_context: str) -> str:
    raw = (pdf_context or "").strip()
    if not raw:
        return ""
    snippet = raw[:PDF_CONTEXT_IN_SYSTEM_CHARS]
    return (
        "\n\nContexto de documento:\n"
        f"{snippet}"
    )


def build_system_instruction(
    sess: UserSession, lang_code: str, agenda_context: str = ""
) -> str:
    return (
        GEMINI_SYSTEM_INSTRUCTION
        + language_instruction(lang_code)
        + _identity_instruction(sess)
        + _datetime_instruction(sess)
        + _pdf_instruction(sess.pdf_context)
        + REMINDER_LLM_INSTRUCTION
        + AGENDA_RECURRING_LLM_INSTRUCTION
        + SCHEDULE_WIZARD_LLM_INSTRUCTION
        + (agenda_context or "")
    )


def build_system_instruction_voice(sess: UserSession, lang_code: str) -> str:
    """Prompt para voz — inclui marcadores de agenda (pessoal e compartilhada)."""
    return (
        GEMINI_SYSTEM_INSTRUCTION
        + language_instruction(lang_code)
        + _identity_instruction(sess)
        + _datetime_instruction(sess)
        + REMINDER_LLM_INSTRUCTION
        + AGENDA_RECURRING_LLM_INSTRUCTION
        + SCHEDULE_WIZARD_LLM_INSTRUCTION
        + "\n\n"
        + VOICE_REPLY_INSTRUCTION
    )


def _trim_agenda_context_for_voice(agenda_context: str) -> str:
    """Voz: omite lista longa da agenda pessoal; mantém compartilhada + wizard."""
    ctx = agenda_context or ""
    start = ctx.find("=== CURRENT USER AGENDA")
    if start == -1:
        return ctx.strip()
    end = ctx.find("=== END AGENDA ===", start)
    if end == -1:
        return ctx.strip()
    end += len("=== END AGENDA ===")
    return (ctx[:start] + ctx[end:]).strip()


def _messages_to_gemini_history(messages: list) -> list[dict]:
    history: list[dict] = []
    for m in messages:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if not content:
            continue
        if role == "user":
            history.append({"role": "user", "parts": [content]})
        elif role == "assistant":
            history.append({"role": "model", "parts": [content]})
    return history


def _normalize_model_id(model_name: str) -> str:
    m = (model_name or "").strip()
    if m.startswith("models/"):
        return m[len("models/") :]
    return m


def _variant_list(sess: UserSession) -> list[str]:
    pref = sess.gemini_model_preference or GEMINI_MODEL_FLASH
    if pref not in GEMINI_MODEL_IDS:
        pref = GEMINI_MODEL_FLASH
    other = GEMINI_MODEL_PRO if pref == GEMINI_MODEL_FLASH else GEMINI_MODEL_FLASH
    out: list[str] = []
    for mid in (pref, other, f"models/{pref}", f"models/{other}"):
        if mid not in out:
            out.append(mid)
    return out


def _is_chat_model(name: str) -> bool:
    n = _normalize_model_id(name).lower()
    if n in GEMINI_MODEL_IDS:
        return True
    if "gemini" not in n:
        return False
    blocked = ("image", "tts", "embedding", "aqa", "vision")
    return not any(b in n for b in blocked)


def _linearize(messages: list, last_user: str) -> str:
    lines: list[str] = []
    for m in messages:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if not content:
            continue
        if role == "user":
            lines.append(f"Usuário: {content}")
        elif role == "assistant":
            lines.append(f"Assistente: {content}")
    lines.append(f"Usuário: {last_user}")
    return "\n".join(lines)


def _is_quota_error(exc: BaseException) -> bool:
    err_s = str(exc)
    low = err_s.lower()
    return "429" in err_s or "quota" in low or "resource exhausted" in low


def is_gemini_error_reply(text: str | None) -> bool:
    """Respostas de generate_reply que não são do assistente (erro de API/config)."""
    s = (text or "").strip()
    if not s:
        return True
    prefixes = (
        "Erro ao chamar o Gemini",
        "A chave da API Gemini",
        "Configure GOOGLE_API_KEY",
        "Instale google-generativeai",
        "Cota da API Gemini",
        "Cota gratuita da API Gemini",
        "Modelo Gemini não disponível",
        "Não obtive texto na resposta",
    )
    return any(s.startswith(p) for p in prefixes)


def _gemini_error_message(exc: BaseException) -> str:
    err_s = str(exc)
    low = err_s.lower()
    if (
        "api_key_invalid" in low
        or "api key expired" in low
        or "api key not valid" in low
        or "leaked" in low
        or ("invalid" in low and "api key" in low)
    ):
        return (
            "A chave da API Gemini expirou ou é inválida. "
            "Crie uma chave nova em https://aistudio.google.com/apikey "
            "e atualize GOOGLE_API_KEY no ficheiro .env na raiz do projeto. "
            "Depois reinicie: python flask_api.py"
        )
    if _is_quota_error(exc):
        return (
            "Cota da API Gemini esgotada (limite gratuito diário ou por minuto). "
            "Aguarde algumas horas ou até amanhã para repor; ou crie uma chave nova em "
            "https://aistudio.google.com/apikey e atualize GOOGLE_API_KEY no .env na raiz. "
            "Mensagens de voz gastam mais cota que texto. Reinicie a API: python flask_api.py"
        )
    if "404" in err_s and "gemini" in low:
        return (
            "Modelo Gemini não disponível nesta chave. "
            "Atualize EGO_GEMINI_MODEL_FLASH no .env ou use gemini-2.5-flash."
        )
    return f"Erro ao chamar o Gemini: {exc}"


def _generate_reply_inner(
    user_text: str,
    *,
    conversation_messages: list | None,
    lang_code: str,
    agenda_context: str,
    audio_bytes: bytes | None,
    audio_mime: str | None,
) -> str:
    if not genai:
        return "Instale google-generativeai."
    api_key = gemini_api_key()
    if not api_key:
        return "Configure GOOGLE_API_KEY ou GEMINI_API_KEY."
    sess = get_session() or UserSession(user_id="")

    msgs = conversation_messages if conversation_messages is not None else []
    prior = msgs[:-1] if msgs else []
    if audio_bytes:
        # Voz: pouco histórico; contexto compacto (sem listagem pessoal longa).
        if len(prior) > 2:
            prior = prior[-2:]
        agenda_context = _trim_agenda_context_for_voice(agenda_context)
    elif len(prior) > CHAT_LLM_MAX_TURNS:
        prior = prior[-CHAT_LLM_MAX_TURNS:]

    voice_turn = bool(audio_bytes)
    full_system = (
        build_system_instruction_voice(sess, lang_code)
        if voice_turn
        else build_system_instruction(sess, lang_code, agenda_context)
    )
    asst_nm = (sess.assistant_name or "EGO-AI").strip() or "EGO-AI"
    voice_tok_cap = voice_max_output_tokens() if voice_turn else 420

    try:
        genai.configure(api_key=api_key)
        preferred = _variant_list(sess)
        chosen = sess.gemini_model_ok
        if chosen and not _is_chat_model(str(chosen)):
            chosen = None
        if not chosen:
            chosen = preferred[0]

        model_try: list[str] = []
        if audio_bytes or gemini_flash_only():
            mid_flash = _normalize_model_id(GEMINI_MODEL_FLASH)
            model_try = [mid_flash]
        else:
            for name in [chosen, *preferred, "models/gemini-flash-latest"]:
                if name and name not in model_try and _is_chat_model(str(name)):
                    model_try.append(str(name))
            model_try = model_try[:2]

        last_error: Exception | None = None
        for model_name in model_try:
            try:
                mid = _normalize_model_id(model_name)
                gen_cfg = None
                try:
                    gen_cfg = genai.GenerationConfig(
                        max_output_tokens=voice_tok_cap,
                        temperature=0.72 if voice_turn else 0.75,
                    )
                except Exception:  # noqa: BLE001
                    gen_cfg = None
                try:
                    model = genai.GenerativeModel(
                        model_name=mid,
                        system_instruction=full_system,
                        generation_config=gen_cfg,
                    )
                    legacy = False
                except TypeError:
                    model = genai.GenerativeModel(model_name=mid)
                    legacy = True

                history = _messages_to_gemini_history(prior)
                voice_intro = (
                    f"Mensagem de voz do utilizador. Responda no mesmo idioma, tom de {asst_nm}. "
                    f"{VOICE_REPLY_INSTRUCTION}"
                )

                # Voz: caminho simples (sem chat com histórico) — mais rápido.
                if audio_bytes and not legacy:
                    parts_voice: list[object] = [voice_intro]
                    parts_voice.append(
                        {"mime_type": audio_mime or "audio/webm", "data": audio_bytes}
                    )
                    resp = model.generate_content(parts_voice)
                    sess.gemini_model_ok = mid
                    text = resp.text or ""
                    if text:
                        return text
                    return "Não obtive texto na resposta."

                if legacy:
                    blob = _linearize(prior, user_text or "(voz)")
                    if audio_bytes:
                        prompt = f"{full_system}\n\n{voice_intro}\n\n{blob}"
                        resp = model.generate_content(
                            [
                                prompt,
                                {"mime_type": audio_mime or "audio/wav", "data": audio_bytes},
                            ]
                        )
                    else:
                        resp = model.generate_content(f"{full_system}\n\n{blob}")
                elif history:
                    chat = model.start_chat(history=history)
                    if audio_bytes:
                        parts: list[object] = []
                        if (user_text or "").strip():
                            parts.append((user_text or "").strip())
                        parts.append(voice_intro)
                        parts.append(
                            {"mime_type": audio_mime or "audio/wav", "data": audio_bytes}
                        )
                        resp = chat.send_message(parts)
                    else:
                        resp = chat.send_message(user_text)
                else:
                    if audio_bytes:
                        parts2: list[object] = []
                        if (user_text or "").strip():
                            parts2.append((user_text or "").strip())
                        parts2.append(voice_intro)
                        parts2.append(
                            {"mime_type": audio_mime or "audio/wav", "data": audio_bytes}
                        )
                        resp = model.generate_content(parts2)
                    else:
                        resp = model.generate_content(user_text)

                sess.gemini_model_ok = mid
                text = resp.text or ""
                if text:
                    return text
                return "Não obtive texto na resposta."
            except Exception as e:  # noqa: BLE001
                last_error = e
                if _is_quota_error(e):
                    break
                continue
        return _gemini_error_message(last_error or Exception("sem resposta"))
    except Exception as e:  # noqa: BLE001
        return _gemini_error_message(e)


def iter_voice_reply_stream(
    *,
    conversation_messages: list | None = None,
    lang_code: str = "pt-BR",
    audio_bytes: bytes,
    audio_mime: str | None,
):
    """Gera texto em pedaços (streaming) para voz — fallback para resposta única se falhar."""
    if not audio_bytes:
        return
    if not genai:
        yield "Instale google-generativeai."
        return
    api_key = gemini_api_key()
    if not api_key:
        yield "Configure GOOGLE_API_KEY ou GEMINI_API_KEY."
        return

    sess = get_session() or UserSession(user_id="")
    msgs = conversation_messages if conversation_messages is not None else []
    prior = msgs[:-1] if msgs else []
    if len(prior) > 2:
        prior = prior[-2:]

    full_system = build_system_instruction_voice(sess, lang_code)
    asst_nm = (sess.assistant_name or "EGO-AI").strip() or "EGO-AI"
    voice_tok_cap = voice_max_output_tokens()
    voice_intro = (
        f"Mensagem de voz do utilizador. Responda no mesmo idioma, tom de {asst_nm}. "
        f"{VOICE_REPLY_INSTRUCTION}"
    )

    try:
        genai.configure(api_key=api_key)
        mid_flash = _normalize_model_id(GEMINI_MODEL_FLASH)
        gen_cfg = None
        try:
            gen_cfg = genai.GenerationConfig(
                max_output_tokens=voice_tok_cap,
                temperature=0.72,
            )
        except Exception:  # noqa: BLE001
            gen_cfg = None
        model = genai.GenerativeModel(
            model_name=mid_flash,
            system_instruction=full_system,
            generation_config=gen_cfg,
        )
        parts_voice: list[object] = [
            voice_intro,
            {"mime_type": audio_mime or "audio/webm", "data": audio_bytes},
        ]
        resp = model.generate_content(parts_voice, stream=True)
        sess.gemini_model_ok = mid_flash
        got = False
        for chunk in resp:
            piece = getattr(chunk, "text", None) or ""
            if piece:
                got = True
                yield piece
        if got:
            return
    except Exception as e:  # noqa: BLE001
        if __debug__:
            print(f"[EGO] voice stream fallback: {e}", flush=True)

    full = generate_reply(
        "",
        conversation_messages=conversation_messages,
        lang_code=lang_code,
        agenda_context="",
        audio_bytes=audio_bytes,
        audio_mime=audio_mime,
    )
    if full:
        yield full


def generate_reply(
    user_text: str,
    *,
    conversation_messages: list | None = None,
    lang_code: str = "pt-BR",
    agenda_context: str = "",
    audio_bytes: bytes | None = None,
    audio_mime: str | None = None,
) -> str:
    """Gera resposta; mensagens de voz têm timeout para não bloquear o Flask."""
    if not audio_bytes:
        return _generate_reply_inner(
            user_text,
            conversation_messages=conversation_messages,
            lang_code=lang_code,
            agenda_context=agenda_context,
            audio_bytes=None,
            audio_mime=audio_mime,
        )
    timeout_s = 90
    with ThreadPoolExecutor(max_workers=1) as pool:
        fut = pool.submit(
            _generate_reply_inner,
            user_text,
            conversation_messages=conversation_messages,
            lang_code=lang_code,
            agenda_context=agenda_context,
            audio_bytes=audio_bytes,
            audio_mime=audio_mime,
        )
        try:
            return fut.result(timeout=timeout_s)
        except FuturesTimeout:
            return (
                "A IA demorou demais para ouvir o áudio (mais de 1 minuto). "
                "Tente uma gravação mais curta (3–5 segundos) ou escreva em texto."
            )


def extract_reminders(text: str) -> tuple[str, list[dict]]:
    marker = "[[EGO_REMINDER:"
    if marker not in text:
        return text, []
    idx = text.find(marker)
    end = text.find("]]", idx)
    if end == -1:
        return text, []
    raw = text[idx + len(marker) : end].strip()
    clean = (text[:idx].rstrip() + "\n" + text[end + 2 :].lstrip()).strip()
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        j0, j1 = raw.find("{"), raw.rfind("}")
        if j0 == -1 or j1 <= j0:
            return text, []
        try:
            obj = json.loads(raw[j0 : j1 + 1])
        except json.JSONDecodeError:
            return text, []
    if isinstance(obj, dict) and obj.get("scheduled_at") not in (None, ""):
        return clean, [obj]
    return text, []


def extract_agenda_markers(text: str) -> tuple[str, list[dict]]:
    marker = "[[EGO_AGENDA:"
    if marker not in text:
        return text, []
    idx = text.find(marker)
    end = text.find("]]", idx)
    if end == -1:
        return text, []
    raw = text[idx + len(marker) : end].strip()
    clean = (text[:idx].rstrip() + "\n" + text[end + 2 :].lstrip()).strip()
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        j0, j1 = raw.find("{"), raw.rfind("}")
        if j0 == -1 or j1 <= j0:
            return text, []
        try:
            obj = json.loads(raw[j0 : j1 + 1])
        except json.JSONDecodeError:
            return text, []
    if not isinstance(obj, dict):
        return text, []
    tit = obj.get("titulo") or obj.get("title")
    hor = obj.get("horario") or obj.get("time")
    dias = obj.get("dias_da_semana") or obj.get("dias") or obj.get("weekdays")
    if tit and hor is not None and dias:
        return clean, [obj]
    return text, []


def count_tokens_approx(user_text: str, assistant_text: str) -> int:
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(user_text or "")) + len(enc.encode(assistant_text or ""))
    except Exception:
        return max(1, (len(user_text or "") + len(assistant_text or "")) // 4)
