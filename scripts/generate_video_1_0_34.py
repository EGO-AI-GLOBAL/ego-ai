#!/usr/bin/env python3
"""
Vídeo marketing 9:16 — fotos reais 1.0.34 + voz Luna + legendas + CTA.

Requisitos: pip install edge-tts pillow
             ffmpeg no PATH

Entrada: marketing/CAPCUT-FOTOS-1.0.34/*.png
Saída:   marketing/videos/app-real/ego-ai-1.0.34-reels.mp4
"""
from __future__ import annotations

import asyncio
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOTOS = ROOT / "marketing" / "CAPCUT-FOTOS-1.0.34"

# Fotos originais enviadas pelo utilizador (Cursor assets)
USER_PHOTO_SOURCES: dict[str, str] = {
    "01-capa-luna.png": "5021598036920044875-2f035281-67bc-4ba7-b31f-7a07070e9dde.png",
    "02-chat-texto.png": "5021598036920044876-123e1172-9fb9-4946-b43e-25953fb234ed.png",
    "03-chat-voz.png": "5021598036920044848-549abeb8-f227-4848-a6f7-02500ff3cf04.png",
    "04-desabafo-gravando.png": "5021598036920044877-ae12ea83-c514-4e10-8580-fb0093153867.png",
    "05-desabafo-agenda-agendar.png": "5021598036920044879-03a250a5-944d-4d80-92d4-9b997184a6ce.png",
    "06-agenda-pessoal.png": "5021598036920044880-b41e8d03-0eff-4c82-b951-1326667d3754.png",
    "07-familia-compartilhada.png": "5021598036920044881-c4a10eab-7b1c-4e77-9934-acf3b8a93835.png",
    "08-entre-nos.png": "5021598036920044882-272c041b-2b4e-468e-bf98-a7b8772d99f2.png",
    "10-ofensiva.png": "5021598036920044878-cb6bdb02-e96d-4631-a3ba-f7ffa83e0cd1.png",
}
ASSETS_PREFIX = (
    "c__Users_Iury_AppData_Roaming_Cursor_User_workspaceStorage_"
    "06e651399a8ed00c18da821d96265836_images_"
)


def _cursor_assets_dir() -> Path | None:
    base = Path.home() / ".cursor" / "projects"
    for folder in base.glob("*/assets"):
        if any(folder.glob(f"{ASSETS_PREFIX}5021598036920044877*")):
            return folder
    return None


def _sync_user_photos() -> None:
    """Copia só as capturas reais do utilizador para FOTOS/."""
    assets = _cursor_assets_dir()
    if assets is None:
        return
    import shutil

    FOTOS.mkdir(parents=True, exist_ok=True)
    for dest_name, tail in USER_PHOTO_SOURCES.items():
        matches = list(assets.glob(f"{ASSETS_PREFIX}{tail}"))
        if not matches:
            raise FileNotFoundError(f"Foto utilizador em falta: {tail}")
        shutil.copy2(matches[0], FOTOS / dest_name)


OUT_DIR = ROOT / "marketing" / "videos" / "app-real"
WORK = OUT_DIR / "_work-1.0.34"
FINAL = OUT_DIR / "ego-ai-1.0.34-reels.mp4"

W, H = 1080, 1920
FPS = 30
VOICE = "pt-BR-FranciscaNeural"
FONT_BOLD = Path(r"C:\Windows\Fonts\segoeuib.ttf")
FONT_REG = Path(r"C:\Windows\Fonts\segoeui.ttf")
PURPLE = (107, 33, 168)
PURPLE_DARK = (10, 18, 42)

SLIDES: list[dict] = [
    {
        "photo": "01-capa-luna.png",
        "title": "EGO-AI",
        "subtitle": "Assistente com rosto e voz",
        "voice": (
            "Conheça o EGO-AI — assistente com rosto e voz, no seu bolso. "
            "Seu dia organizado, sem cobrança no WhatsApp."
        ),
    },
    {
        "photo": "02-chat-texto.png",
        "title": "FALE OU DIGITE",
        "subtitle": "Luna responde na hora",
        "voice": (
            "Conversa por texto com Luna ou Leo — como falar com alguém de verdade. "
            "Ela acolhe, organiza e te ajuda no dia a dia."
        ),
    },
    {
        "photo": "03-chat-voz.png",
        "title": "MENSAGEM DE VOZ",
        "subtitle": "Segure o microfone",
        "voice": (
            "Prefere falar? Grava a mensagem — a inteligência artificial entende "
            "e responde com voz, se você quiser ouvir."
        ),
    },
    {
        "photo": "04-desabafo-gravando.png",
        "title": "DESABAFO DA NOITE",
        "subtitle": "Fale ou escreva tudo",
        "voice": (
            "À noite, usa o Desabafo: fala ou escreve tudo que está na cabeça. "
            "A app transforma em organização para amanhã."
        ),
    },
    {
        "photo": "05-desabafo-agenda-agendar.png",
        "title": "DO DESABAFO À AGENDA",
        "subtitle": "Agendar ou Excluir",
        "voice": (
            "Ela separa compromissos e lista de compras — você só toca Agendar ou Excluir. "
            "Item a item, no seu ritmo."
        ),
    },
    {
        "photo": "06-agenda-pessoal.png",
        "title": "AGENDA PESSOAL",
        "subtitle": "Compromissos · hábitos · mercado",
        "voice": (
            "Tudo fica na sua agenda: consultas, churrasco, mercado com checklist. "
            "Hábitos semanais no mesmo lugar."
        ),
    },
    {
        "photo": "07-familia-compartilhada.png",
        "title": "AGENDA COMPARTILHADA",
        "subtitle": "Família · convites · todos veem",
        "voice": (
            "Para a família: agenda compartilhada — convida quem quiser, "
            "marca churrasco, reunião ou jogo. Todo mundo vê junto."
        ),
    },
    {
        "photo": "08-entre-nos.png",
        "title": "ENTRE NÓS",
        "subtitle": "Você + 1 pessoa",
        "voice": (
            "Entre Nós é diferente: só você e uma pessoa — casal, parceiro ou melhor amigo. "
            "Manda tarefa, convite ou compromisso."
        ),
    },
    {
        "photo": "08-entre-nos.png",
        "title": "CONFIRMAR OU RECUSAR",
        "subtitle": "Sem viu no WhatsApp",
        "voice": (
            "A pessoa confirma ou recusa na hora. Push nos dois lados — "
            "sem ficar cobrando no WhatsApp."
        ),
    },
    {
        "photo": "10-ofensiva.png",
        "title": "OFENSIVA DIÁRIA",
        "subtitle": "Mantenha o ritmo",
        "voice": (
            "Ofensiva: quantos dias seguidos você cuida da sua rotina. "
            "Chat, voz, desabafo, agenda pessoal, família e Entre Nós — tudo num app."
        ),
    },
]

CTA = {
    "title": "BAIXE GRÁTIS",
    "subtitle": "👆 Toque no perfil · Android + iPhone na bio",
    "voice": (
        "Versão um ponto zero trinta e quatro. "
        "Toque no perfil — links na bio. Android e iPhone. "
        "Entra no teste e me conta o que achou."
    ),
}


def _has_ffmpeg() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True, timeout=10)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return False


async def _tts(text: str, out: Path) -> None:
    import edge_tts

    await edge_tts.Communicate(text, VOICE).save(str(out))


def _audio_duration(path: Path) -> float:
    r = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return max(float(r.stdout.strip()), 0.5)


def _load_font(path: Path, size: int):
    from PIL import ImageFont

    if path.exists():
        return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _fit_phone(img_path: Path):
    from PIL import Image

    im = Image.open(img_path).convert("RGB")
    iw, ih = im.size
    scale = W / iw
    nh = int(ih * scale)
    im = im.resize((W, nh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (W, H), PURPLE_DARK)
    y = max(0, (H - nh) // 2 - 40)
    if y + nh > H:
        y = H - nh
    canvas.paste(im, (0, y))
    return canvas


def _voice_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _wrap_caption(text: str, font, max_width: int, max_lines: int = 3) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        trial = " ".join(current + [word])
        bbox = font.getbbox(trial)
        if bbox[2] - bbox[0] <= max_width or not current:
            current.append(word)
        else:
            lines.append(" ".join(current))
            current = [word]
        if len(lines) >= max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(" ".join(current))
    if len(lines) == max_lines and len(words) > len(" ".join(lines).split()):
        lines[-1] = lines[-1].rstrip(".") + "…"
    return lines


def _draw_text_outlined(draw, xy, text: str, font, fill, outline=(0, 0, 0), width: int = 2) -> None:
    x, y = xy
    for dx in range(-width, width + 1):
        for dy in range(-width, width + 1):
            if dx or dy:
                draw.text((x + dx, y + dy), text, font=font, fill=outline, anchor="mm")
    draw.text((x, y), text, font=font, fill=fill, anchor="mm")


def _draw_caption(draw, text: str) -> None:
    font = _load_font(FONT_BOLD, 42)
    lines = _wrap_caption(text, font, W - 96, max_lines=3)
    line_h = 50
    pad_y = 22
    pad_x = 36
    bar_h = pad_y * 2 + line_h * len(lines)
    y0 = H - bar_h - 20
    draw.rectangle([pad_x, y0, W - pad_x, H - 20], fill=(12, 6, 28))
    draw.rectangle([pad_x, y0, W - pad_x, y0 + 5], fill=PURPLE)
    y = y0 + pad_y + line_h // 2
    for line in lines:
        _draw_text_outlined(draw, (W // 2, y), line, font, fill=(255, 255, 255))
        y += line_h


def _draw_header(draw, title: str, subtitle: str | None) -> None:
    fb = _load_font(FONT_BOLD, 52)
    fr = _load_font(FONT_REG, 34)
    draw.rectangle([0, 0, W, 200], fill=(*PURPLE, 230))
    draw.text((48, 48), title, fill=(255, 255, 255), font=fb)
    if subtitle:
        draw.text((48, 118), subtitle, fill=(196, 181, 253), font=fr)


def _render_slide(
    photo: Path,
    title: str,
    subtitle: str | None,
    out: Path,
    caption: str | None = None,
) -> None:
    from PIL import ImageDraw

    canvas = _fit_phone(photo)
    draw = ImageDraw.Draw(canvas)
    _draw_header(draw, title, subtitle)
    if caption:
        _draw_caption(draw, caption)
    draw.rectangle([0, H - 8, W, H], fill=PURPLE)
    canvas.save(out, quality=95)


def _render_cta(out: Path, caption: str | None = None) -> None:
    from PIL import Image, ImageDraw

    canvas = Image.new("RGB", (W, H), PURPLE)
    draw = ImageDraw.Draw(canvas)
    fb = _load_font(FONT_BOLD, 72)
    fr = _load_font(FONT_REG, 36)
    logo_fb = _load_font(FONT_BOLD, 96)
    draw.text((W // 2, H // 2 - 160), "EGO-AI", fill=(255, 255, 255), font=logo_fb, anchor="mm")
    draw.text((W // 2, H // 2 - 40), CTA["title"], fill=(255, 255, 255), font=fb, anchor="mm")
    draw.text((W // 2, H // 2 + 50), CTA["subtitle"], fill=(196, 181, 253), font=fr, anchor="mm")
    draw.text((W // 2, H // 2 + 150), "Toque no perfil", fill=(255, 255, 255), font=fb, anchor="mm")
    draw.text((W // 2, H // 2 + 230), "Android + iPhone na bio", fill=(196, 181, 253), font=fr, anchor="mm")
    if caption:
        _draw_caption(draw, caption)
    canvas.save(out, quality=95)


def _clip_cta_with_captions(voice: str, audio: Path, out: Path, tag: str) -> None:
    sentences = _voice_sentences(voice)
    if not sentences:
        sentences = [voice]
    dur = _audio_duration(audio) + 0.35
    weights = [max(len(s), 1) for s in sentences]
    total_w = sum(weights)
    segments: list[Path] = []
    for i, sentence in enumerate(sentences):
        seg_dur = dur * weights[i] / total_w
        img = WORK / f"{tag}-cap-{i:02d}.jpg"
        _render_cta(img, caption=sentence)
        seg = WORK / f"{tag}-seg-{i:02d}.mp4"
        _segment_from_image(img, seg_dur, seg)
        segments.append(seg)
    if len(segments) == 1:
        _mux_video_audio(segments[0], audio, out)
        return
    silent = WORK / f"{tag}-silent.mp4"
    _concat_clips(segments, silent)
    _mux_video_audio(silent, audio, out)


def _segment_from_image(img: Path, duration: float, out: Path) -> None:
    frames = max(int(duration * FPS), 1)
    vf = (
        f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
        f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x0A122A"
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(img),
            "-vf",
            vf,
            "-t",
            f"{duration:.3f}",
            "-r",
            str(FPS),
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-an",
            str(out),
        ],
        check=True,
        capture_output=True,
    )


def _mux_video_audio(video: Path, audio: Path, out: Path) -> None:
    dur = _audio_duration(audio) + 0.35
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video),
            "-i",
            str(audio),
            "-t",
            f"{dur:.3f}",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "-pix_fmt",
            "yuv420p",
            str(out),
        ],
        check=True,
        capture_output=True,
    )


def _clip_with_captions(
    photo: Path,
    title: str,
    subtitle: str | None,
    voice: str,
    audio: Path,
    out: Path,
    tag: str,
) -> None:
    sentences = _voice_sentences(voice)
    if not sentences:
        sentences = [voice]
    dur = _audio_duration(audio) + 0.35
    weights = [max(len(s), 1) for s in sentences]
    total_w = sum(weights)
    segments: list[Path] = []
    for i, sentence in enumerate(sentences):
        seg_dur = dur * weights[i] / total_w
        img = WORK / f"{tag}-cap-{i:02d}.jpg"
        _render_slide(photo, title, subtitle, img, caption=sentence)
        seg = WORK / f"{tag}-seg-{i:02d}.mp4"
        _segment_from_image(img, seg_dur, seg)
        segments.append(seg)
    if len(segments) == 1:
        _mux_video_audio(segments[0], audio, out)
        return
    silent = WORK / f"{tag}-silent.mp4"
    _concat_clips(segments, silent)
    _mux_video_audio(silent, audio, out)


def _concat_clips(clips: list[Path], out: Path) -> None:
    lst = WORK / "concat.txt"
    lines = [f"file '{c.resolve().as_posix()}'" for c in clips]
    lst.write_text("\n".join(lines), encoding="utf-8")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(lst),
            "-c",
            "copy",
            str(out),
        ],
        check=True,
        capture_output=True,
    )


async def main() -> int:
    if not _has_ffmpeg():
        print("Instale ffmpeg: winget install ffmpeg")
        return 1
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        print("pip install pillow edge-tts")
        return 1

    if not FOTOS.is_dir():
        print(f"FALTA pasta: {FOTOS}")
        return 1

    try:
        _sync_user_photos()
    except FileNotFoundError as e:
        print(f"AVISO: {e} — usando fotos já em {FOTOS}")

    WORK.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    clips: list[Path] = []

    print("Gerando voz Luna (Edge TTS) + video 1.0.34...")
    for i, slide in enumerate(SLIDES):
        photo = FOTOS / slide["photo"]
        if not photo.exists():
            print(f"FALTA foto: {photo}")
            return 1
        audio = WORK / f"audio-{i:02d}.mp3"
        await _tts(slide["voice"], audio)
        clip = WORK / f"clip-{i:02d}.mp4"
        print(f"  Clip {i + 1}/{len(SLIDES)}: {slide['title']} (+ legendas)")
        _clip_with_captions(
            photo,
            slide["title"],
            slide.get("subtitle"),
            slide["voice"],
            audio,
            clip,
            f"slide{i:02d}",
        )
        clips.append(clip)

    cta_audio = WORK / "audio-cta.mp3"
    await _tts(CTA["voice"], cta_audio)
    cta_clip = WORK / "clip-cta.mp4"
    print("  Clip CTA (+ legendas)")
    _clip_cta_with_captions(CTA["voice"], cta_audio, cta_clip, "cta")
    clips.append(cta_clip)

    print("Unindo clips...")
    _concat_clips(clips, FINAL)
    mb = FINAL.stat().st_size / 1024 / 1024
    print(f"\nPRONTO: {FINAL}")
    print(f"Tamanho: {mb:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
