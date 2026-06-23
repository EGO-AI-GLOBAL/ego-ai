#!/usr/bin/env python3
"""
Gera vídeos de marketing: avatar falando + voz Edge TTS (mesmas do app).

Requisitos:
  pip install edge-tts
  ffmpeg no PATH (https://ffmpeg.org)

Saída: marketing/videos/luna/ e marketing/videos/leo/
"""
from __future__ import annotations

import asyncio
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "app" / "assets"
OUT = ROOT / "marketing" / "videos"
AUDIO_TMP = OUT / "_audio"

# Mesmas vozes que ego_api/tts.py (Luna = Francisca, Leo = Antonio)
VOICES = {
    "luna": ("vf1", "pt-BR-FranciscaNeural", ASSETS / "avatar-f1-speaking.mp4"),
    "leo": ("vm1", "pt-BR-AntonioNeural", ASSETS / "avatar-m1-speaking.mp4"),
}

CLIPS: dict[str, dict[str, str]] = {
    "luna": {
        "01-criativo-a-solidao": (
            "Oi… Vi que você ainda tá acordado. "
            "Quer conversar sobre como foi seu dia? "
            "Ou prefere que eu te ajude a planejar a manhã?"
        ),
        "02-criativo-b-produtividade": (
            "Feito! Organizei seus hábitos de hoje: "
            "água a cada duas horas, "
            "e sua reunião das quatorze horas já tá marcada."
        ),
        "03-desabafo-domingo": (
            "Domingo à noite costuma pesar, né? "
            "Respira comigo: o que tá na sua cabeça agora é temporário. "
            "Amanhã a gente reorganiza um passo de cada vez."
        ),
        "04-stories-10s": (
            "Chega de tela fria. Sou a Luna — baixa o EGO-AI e me diz oi."
        ),
        "05-descarrego-completo": (
            "Você já deitou exausto… e a mente continua listando tudo que falta amanhã? "
            "Ir ao mercado, marcar a consulta, lembrar da reunião, comprar remédio… "
            "No EGO-AI você não precisa carregar esse peso sozinho. "
            "Toque em Descarrego agora, segure o microfone e fale tudo o que está na sua cabeça. "
            "Eu te escuto com calma — e transformo em sugestões na sua Agenda na hora. "
            "Depois é só revisar: Agendar o que quiser guardar, ou Excluir o que não faz sentido. "
            "Lista de compras inclusa — leite, sabão, o que você falou no áudio. "
            "Esvazie a mente pra dormir em paz. "
            "Baixe o EGO-AI gratuitamente na fase de testes. Link na descrição."
        ),
    },
    "leo": {
        "01-criativo-a-solidao": (
            "E aí… Ainda por aqui acordado? "
            "Me conta como foi o dia — ou bora montar um plano leve pra amanhã? "
            "Tô contigo."
        ),
        "02-criativo-b-produtividade": (
            "Pronto — tá no jeito. "
            "Hidratação a cada duas horas "
            "e reunião das quatorze confirmadas. "
            "Qualquer coisa, é só chamar."
        ),
        "03-desabafo-domingo": (
            "Ansiedade de domingo é mais comum do que parece. "
            "Você não precisa resolver a semana inteira hoje. "
            "Quer que eu te ajude a priorizar só a segunda-feira?"
        ),
        "04-stories-10s": (
            "Sou o Leo. Um áudio e eu organizo seu dia. Grátis pra começar."
        ),
    },
}


async def _tts_mp3(text: str, edge_voice: str, out_path: Path) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text, edge_voice)
    await communicate.save(str(out_path))


def _has_ffmpeg() -> bool:
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            check=True,
            timeout=10,
        )
        return True
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


def _mux_video(
    loop_video: Path,
    audio_mp3: Path,
    out_mp4: Path,
    *,
    vertical_916: bool = True,
) -> None:
    """Loop do avatar + áudio TTS; opcional crop 9:16 para Reels."""
    vf = "format=yuv420p"
    if vertical_916:
        vf = (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,format=yuv420p"
        )
    cmd = [
        "ffmpeg",
        "-y",
        "-stream_loop",
        "-1",
        "-i",
        str(loop_video),
        "-i",
        str(audio_mp3),
        "-shortest",
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        str(out_mp4),
    ]
    subprocess.run(cmd, check=True, capture_output=True, timeout=300)


async def _generate_all(
    *,
    vertical: bool = True,
    audio_only: bool = False,
    only_persona: str | None = None,
    only_slug: str | None = None,
) -> int:
    try:
        import edge_tts  # noqa: F401
    except ImportError:
        print("Instale: pip install edge-tts")
        return 1

    use_ffmpeg = _has_ffmpeg() and not audio_only
    if not use_ffmpeg:
        print("AVISO: ffmpeg nao encontrado — gerando MP3 + loops + script mux.")
        print("  Depois: winget install ffmpeg && python scripts/generate_marketing_videos.py")

    for persona, (_vid, edge_voice, loop_path) in VOICES.items():
        if not loop_path.is_file():
            print(f"Falta video loop: {loop_path}")
            return 1

    loops_dir = OUT / "_loops"
    loops_dir.mkdir(parents=True, exist_ok=True)
    for persona, (_vid, _edge, loop_path) in VOICES.items():
        dest = loops_dir / f"{persona}-speaking-loop.mp4"
        if not dest.exists() or dest.stat().st_size != loop_path.stat().st_size:
            shutil.copy2(loop_path, dest)

    personas_list = list(CLIPS.keys())
    if only_persona:
        if only_persona not in CLIPS:
            print(f"Persona invalida: {only_persona}. Use: luna, leo")
            return 1
        personas_list = [only_persona]

    AUDIO_TMP.mkdir(parents=True, exist_ok=True)
    ok = 0
    total = 0
    for p in personas_list:
        clips_count = CLIPS[p]
        if only_slug:
            total += 1 if only_slug in clips_count else 0
        else:
            total += len(clips_count)

    for persona in personas_list:
        clips = CLIPS[persona]
        if only_slug:
            if only_slug not in clips:
                print(f"Slug invalido: {only_slug}. Disponiveis: {', '.join(clips)}")
                return 1
            clips = {only_slug: clips[only_slug]}
        _vid, edge_voice, loop_path = VOICES[persona]
        persona_dir = OUT / persona
        persona_dir.mkdir(parents=True, exist_ok=True)

        for slug, text in clips.items():
            audio_path = AUDIO_TMP / f"{persona}-{slug}.mp3"
            video_path = persona_dir / f"{slug}.mp4"

            print(f"[TTS] {persona}/{slug}...")
            await _tts_mp3(text, edge_voice, audio_path)

            if use_ffmpeg:
                print(f"[MUX] {persona}/{slug}.mp4...")
                try:
                    _mux_video(loop_path, audio_path, video_path, vertical_916=vertical)
                    ok += 1
                    print(f"  OK -> {video_path.relative_to(ROOT)}")
                except subprocess.CalledProcessError as e:
                    err = (e.stderr or b"").decode("utf-8", errors="replace")[-800:]
                    print(f"  ERRO ffmpeg: {err}")
            else:
                ok += 1

    if not use_ffmpeg:
        _write_mux_batch(vertical=vertical, personas_list=personas_list)
        print(f"\nAudios: {AUDIO_TMP}")
        print(f"Rode: {OUT / 'gerar-videos.bat'} (apos instalar ffmpeg)")

    print(f"\nConcluido: {ok}/{total} {'videos' if use_ffmpeg else 'faixas de audio'} em {OUT}")
    return 0 if ok == total else 1


def _write_mux_batch(*, vertical: bool, personas_list: list[str]) -> None:
    bat = OUT / "gerar-videos.bat"
    vf = (
        "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,format=yuv420p"
        if vertical
        else "format=yuv420p"
    )
    lines = ["@echo off", "setlocal", f"cd /d \"{OUT}\""]
    for persona in personas_list:
        clips = CLIPS[persona]
        _vid, _edge, loop_path = VOICES[persona]
        loop = OUT / "_loops" / f"{persona}-speaking-loop.mp4"
        for slug in clips:
            audio = AUDIO_TMP / f"{persona}-{slug}.mp3"
            out = OUT / persona / f"{slug}.mp4"
            lines.append(f"if not exist \"{persona}\" mkdir \"{persona}\"")
            lines.append(
                f"ffmpeg -y -stream_loop -1 -i \"{loop}\" -i \"{audio}\" "
                f"-shortest -map 0:v:0 -map 1:a:0 -vf \"{vf}\" "
                f"-c:v libx264 -preset fast -crf 23 -c:a aac -b:a 128k "
                f"-movflags +faststart \"{out}\""
            )
    lines.append("echo Pronto.")
    bat.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")


def main() -> int:
    vertical = "--square" not in sys.argv
    audio_only = "--audio-only" in sys.argv
    only = None
    only_slug = None
    for arg in sys.argv[1:]:
        if arg.startswith("--persona="):
            only = arg.split("=", 1)[1].strip().lower()
        elif arg.startswith("--slug="):
            only_slug = arg.split("=", 1)[1].strip()
        elif arg in ("--leo",):
            only = "leo"
        elif arg in ("--luna",):
            only = "luna"
    if "--help" in sys.argv:
        print(__doc__)
        print("  --square         mantem proporcao original (sem crop 9:16)")
        print("  --audio-only     so MP3 + bat (nao exige ffmpeg)")
        print("  --persona=leo    regenera so videos do Leo")
        print("  --persona=luna   regenera so videos da Luna")
        print("  --slug=NOME      gera so um clip (ex: 05-descarrego-completo)")
        return 0
    return asyncio.run(
        _generate_all(
            vertical=vertical,
            audio_only=audio_only,
            only_persona=only,
            only_slug=only_slug,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
