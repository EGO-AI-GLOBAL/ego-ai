#!/usr/bin/env python3
"""
Vídeo marketing 9:16 — 5 fotos reais do app + voz Luna + legendas + CTA.

Requisitos: pip install edge-tts pillow
             ffmpeg no PATH

Saída: marketing/videos/app-real/ego-ai-app-real-reels.mp4
"""
from __future__ import annotations

import asyncio
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOTOS = ROOT / "marketing" / "videos" / "app-real" / "fotos"
OUT_DIR = ROOT / "marketing" / "videos" / "app-real"
WORK = OUT_DIR / "_work"
FINAL = OUT_DIR / "ego-ai-app-real-reels.mp4"

W, H = 1080, 1920
FPS = 30
VOICE = "pt-BR-FranciscaNeural"
FONT_BOLD = Path(r"C:\Windows\Fonts\segoeuib.ttf")
FONT_REG = Path(r"C:\Windows\Fonts\segoeui.ttf")
PURPLE = (107, 33, 168)
PURPLE_DARK = (10, 18, 42)

# Ordem viral: gancho → emoção → diferencial → prático → social → CTA
SLIDES: list[dict] = [
    {
        "photo": "01-icone.png",
        "title": "APP REAL NO CELULAR",
        "subtitle": "Não é mockup — é o EGO-AI",
        "voice": (
            "Para de scrollar. Isso aqui não é propaganda bonita: "
            "é o EGO-AI rodando de verdade no celular."
        ),
    },
    {
        "photo": "03-chat-dia-a-dia.png",
        "title": "SEU AVATAR NO DIA A DIA",
        "subtitle": "Texto ou voz · 12 avatares",
        "voice": (
            "Conversa com a Hana — ou o avatar que você escolher. "
            "Ela ouve, acolhe e te ajuda sem julgamento."
        ),
    },
    {
        "photo": "04-descarrego.png",
        "title": "DESCARREGO DA NOITE",
        "subtitle": "Fale tudo · organize na Agenda",
        "voice": (
            "Dia pesado? Toque em Descarrego agora, fale o que está na cabeça "
            "e a IA transforma em compromissos na Agenda. Você confirma: Agendar ou Excluir."
        ),
    },
    {
        "photo": "05-agenda-mercado.png",
        "title": "AGENDA + COMPRAS",
        "subtitle": "Mercado, consulta, tudo junto",
        "voice": (
            "Mercado, consulta, churrasco… Compromissos e lista de compras "
            "no mesmo lugar. Marca o que comprou e segue a vida."
        ),
    },
    {
        "photo": "02-agenda-compartilhada.png",
        "title": "AGENDA COMPARTILHADA",
        "subtitle": "Família · amigos · trabalho",
        "voice": (
            "Agenda compartilhada com família, amigos ou trabalho. "
            "Crie o grupo e adicione quem você quiser — "
            "churrasco, reunião, jogo da seleção: todo mundo vê na mesma agenda."
        ),
    },
]

CTA = {
    "title": "TESTE GRÁTIS",
    "subtitle": "Link na descrição · Android e iPhone",
    "voice": "Baixe grátis na fase de testes. Link na descrição. Te vejo lá.",
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


def _fit_phone(img_path: Path) -> "Image.Image":
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


def _draw_header(draw, title: str, subtitle: str | None) -> None:
    from PIL import ImageDraw

    draw.rectangle([0, 0, W, 200], fill=(*PURPLE, 230))
    font_t = ImageDraw.ImageDraw  # type hint placate
    fb = _load_font(FONT_BOLD, 52)
    fr = _load_font(FONT_REG, 34)
    draw.text((48, 48), title, fill=(255, 255, 255), font=fb)
    if subtitle:
        draw.text((48, 118), subtitle, fill=(196, 181, 253), font=fr)


def _load_font(path: Path, size: int):
    from PIL import ImageFont

    if path.exists():
        return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _render_slide(photo: Path, title: str, subtitle: str | None, out: Path) -> None:
    from PIL import ImageDraw

    canvas = _fit_phone(photo)
    draw = ImageDraw.Draw(canvas)
    _draw_header(draw, title, subtitle)
    # barra inferior marca
    draw.rectangle([0, H - 8, W, H], fill=PURPLE)
    canvas.save(out, quality=95)


def _render_cta(out: Path) -> None:
    from PIL import Image, ImageDraw

    canvas = Image.new("RGB", (W, H), PURPLE)
    draw = ImageDraw.Draw(canvas)
    fb = _load_font(FONT_BOLD, 72)
    fr = _load_font(FONT_REG, 40)
    logo_fb = _load_font(FONT_BOLD, 96)
    draw.text((W // 2, H // 2 - 120), "EGO-AI", fill=(255, 255, 255), font=logo_fb, anchor="mm")
    draw.text((W // 2, H // 2), CTA["title"], fill=(255, 255, 255), font=fb, anchor="mm")
    draw.text((W // 2, H // 2 + 80), CTA["subtitle"], fill=(196, 181, 253), font=fr, anchor="mm")
    draw.text((W // 2, H // 2 + 200), "egoai.com.br", fill=(255, 255, 255), font=fr, anchor="mm")
    canvas.save(out, quality=95)


def _clip_from_image(img: Path, audio: Path, out: Path) -> None:
    dur = _audio_duration(audio) + 0.35
    frames = max(int(dur * FPS), 1)
    vf = (
        f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
        f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x0A122A,"
        f"zoompan=z='min(zoom+0.0008,1.06)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={frames}:s={W}x{H}:fps={FPS}"
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(img),
            "-i",
            str(audio),
            "-vf",
            vf,
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

    WORK.mkdir(parents=True, exist_ok=True)
    clips: list[Path] = []

    print("Gerando voz Luna (Edge TTS)...")
    for i, slide in enumerate(SLIDES):
        photo = FOTOS / slide["photo"]
        if not photo.exists():
            print(f"FALTA foto: {photo}")
            return 1
        audio = WORK / f"audio-{i:02d}.mp3"
        await _tts(slide["voice"], audio)
        comp = WORK / f"slide-{i:02d}.jpg"
        _render_slide(photo, slide["title"], slide.get("subtitle"), comp)
        clip = WORK / f"clip-{i:02d}.mp4"
        print(f"  Clip {i + 1}/{len(SLIDES)}: {slide['title']}")
        _clip_from_image(comp, audio, clip)
        clips.append(clip)

    cta_audio = WORK / "audio-cta.mp3"
    await _tts(CTA["voice"], cta_audio)
    cta_img = WORK / "slide-cta.jpg"
    _render_cta(cta_img)
    cta_clip = WORK / "clip-cta.mp4"
    _clip_from_image(cta_img, cta_audio, cta_clip)
    clips.append(cta_clip)

    print("Unindo clips...")
    _concat_clips(clips, FINAL)
    print(f"\nPRONTO: {FINAL}")
    print(f"Tamanho: {FINAL.stat().st_size / 1024 / 1024:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
