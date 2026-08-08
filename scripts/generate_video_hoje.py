#!/usr/bin/env python3
"""
Vídeo marketing 9:16 — fotos reais + voz Luna + legendas queimadas.
Você só coloca música de fundo no CapCut (volume baixo) e posta.

Entrada: marketing/CAPCUT-FOTOS-1.0.34/*.png
Saída:   marketing/videos/app-real/ego-ai-hoje-reels.mp4
"""
from __future__ import annotations

import asyncio
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOTOS = ROOT / "marketing" / "CAPCUT-FOTOS-1.0.34"
OUT_DIR = ROOT / "marketing" / "videos" / "app-real"
WORK = OUT_DIR / "_work-hoje"
FINAL = OUT_DIR / "ego-ai-android-31-07-reels.mp4"
FINAL_ALIAS = OUT_DIR / "ego-ai-hoje-reels.mp4"

W, H = 1080, 1920
FPS = 30
VOICE = "pt-BR-FranciscaNeural"
PURPLE = (56, 96, 140)
PURPLE_DARK = (8, 16, 36)
FONT_BOLD = Path(r"C:\Windows\Fonts\segoeuib.ttf")
FONT_REG = Path(r"C:\Windows\Fonts\segoeui.ttf")

USER_PHOTO_SOURCES: dict[str, str] = {}
ASSETS_PREFIX = ""

SCENES: list[dict] = [
    {
        "photo": "01-capa-luna.png",
        "lines": [
            ("Mente barulhenta?", 50, True),
            ("Agora também no Android.", 42, False),
        ],
        "darken": 0.42,
        "center": True,
        "voice": (
            "Mente barulhenta? O EGO-AI chegou no Android — e continua no iPhone."
        ),
    },
    {
        "photo": "04-desabafo-gravando.png",
        "lines": [
            ("Desabafo por voz", 50, True),
            ("Luna organiza a cabeça", 36, False),
        ],
        "voice": (
            "Desabafo por voz: a Luna escuta e organiza o que está na sua cabeça."
        ),
    },
    {
        "photo": "06-agenda-pessoal.png",
        "lines": [
            ("Agenda · compras · família", 44, True),
            ("Tudo no bolso", 36, False),
        ],
        "voice": (
            "Agenda, lista de compras e família — tudo no bolso, sem atrito."
        ),
    },
    {
        "photo": "11-monstrinhos-humor.png",
        "lines": [
            ("Luna, Leo e Monstrinhos", 44, True),
            ("Rosto, voz e cuidado", 34, False),
        ],
        "voice": (
            "Luna, Leo e o Jardim dos Monstrinhos: rosto, voz e cuidado de verdade."
        ),
    },
]

CTA = {
    "voice": (
        "Baixa no Android ou no iPhone. "
        "Três dias grátis. Link na bio."
    ),
}


def _cursor_assets_dir() -> Path | None:
    if not ASSETS_PREFIX or not USER_PHOTO_SOURCES:
        return None
    base = Path.home() / ".cursor" / "projects"
    for folder in base.glob("*/assets"):
        if any(folder.glob(f"{ASSETS_PREFIX}*")):
            return folder
    return None


def _sync_user_photos() -> None:
    if not USER_PHOTO_SOURCES:
        return
    assets = _cursor_assets_dir()
    if assets is None:
        return
    FOTOS.mkdir(parents=True, exist_ok=True)
    for dest_name, tail in USER_PHOTO_SOURCES.items():
        matches = list(assets.glob(f"{ASSETS_PREFIX}{tail}"))
        if matches:
            shutil.copy2(matches[0], FOTOS / dest_name)


def _has_ffmpeg() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True, timeout=10)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return False


async def _tts(text: str, out: Path) -> None:
    import os
    import ssl

    try:
        import certifi

        ca = certifi.where()
        os.environ["SSL_CERT_FILE"] = ca
        os.environ["REQUESTS_CA_BUNDLE"] = ca
    except ImportError:
        ca = None

    import edge_tts
    import edge_tts.communicate as edge_comm

    ctx = ssl.create_default_context(cafile=ca) if ca else ssl.create_default_context()
    try:
        edge_comm._SSL_CTX = ctx  # type: ignore[attr-defined]
    except Exception:
        pass

    try:
        await edge_tts.Communicate(text, VOICE).save(str(out))
    except Exception:
        edge_comm._SSL_CTX = ssl._create_unverified_context()  # type: ignore[attr-defined]
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


def _voice_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


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


def _draw_text_outlined(draw, xy, text: str, font, fill, outline=(0, 0, 0), width: int = 3) -> None:
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


def _render_scene(photo: Path, scene: dict, out: Path, caption: str | None = None) -> None:
    from PIL import Image, ImageDraw

    canvas = _fit_phone(photo)
    draw = ImageDraw.Draw(canvas)

    if scene.get("darken"):
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, int(255 * scene["darken"])))
        canvas = canvas.convert("RGBA")
        canvas = Image.alpha_composite(canvas, overlay).convert("RGB")
        draw = ImageDraw.Draw(canvas)

    lines: list[tuple[str, int, bool]] = scene["lines"]
    if scene.get("center"):
        total_h = sum(sz + 18 for _, sz, _ in lines)
        y = H // 2 - total_h // 2
        for text, size, bold in lines:
            font = _load_font(FONT_BOLD if bold else FONT_REG, size)
            color = (255, 255, 255) if bold else (230, 220, 255)
            _draw_text_outlined(draw, (W // 2, y + size // 2), text, font, fill=color)
            y += size + 18
    else:
        draw.rectangle([0, 0, W, 220], fill=(*PURPLE, 235))
        y = 52
        for i, (text, size, bold) in enumerate(lines):
            font = _load_font(FONT_BOLD if bold else FONT_REG, size)
            color = (255, 255, 255) if bold or i == 0 else (196, 181, 253)
            draw.text((48, y), text, fill=color, font=font)
            y += size + 12

    if caption:
        _draw_caption(draw, caption)

    draw.rectangle([0, H - 8, W, H], fill=PURPLE)
    canvas.save(out, quality=95)


def _render_cta(out: Path, caption: str | None = None) -> None:
    from PIL import Image, ImageDraw

    canvas = Image.new("RGB", (W, H), PURPLE)
    draw = ImageDraw.Draw(canvas)
    fb_big = _load_font(FONT_BOLD, 78)
    fb = _load_font(FONT_BOLD, 56)
    fr = _load_font(FONT_REG, 36)
    logo = _load_font(FONT_BOLD, 88)

    draw.text((W // 2, H // 2 - 280), "EGO-AI", fill=(255, 255, 255), font=logo, anchor="mm")
    draw.text((W // 2, H // 2 - 140), "TESTE GRÁTIS", fill=(255, 230, 80), font=fb_big, anchor="mm")
    draw.text((W // 2, H // 2 - 40), "Toque no perfil", fill=(255, 255, 255), font=fb, anchor="mm")
    draw.text((W // 2, H // 2 + 50), "Android + iPhone na bio", fill=(196, 181, 253), font=fr, anchor="mm")
    draw.text((W // 2, H // 2 + 130), "Versão 1.0.34", fill=(196, 181, 253), font=fr, anchor="mm")
    if caption:
        _draw_caption(draw, caption)
    canvas.save(out, quality=95)


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


def _clip_with_captions(
    photo: Path,
    scene: dict,
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
        _render_scene(photo, scene, img, caption=sentence)
        seg = WORK / f"{tag}-seg-{i:02d}.mp4"
        _segment_from_image(img, seg_dur, seg)
        segments.append(seg)
    if len(segments) == 1:
        _mux_video_audio(segments[0], audio, out)
        return
    silent = WORK / f"{tag}-silent.mp4"
    _concat_clips(segments, silent)
    _mux_video_audio(silent, audio, out)


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


async def main() -> int:
    if not _has_ffmpeg():
        print("Instale ffmpeg: winget install ffmpeg")
        return 1
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        print("pip install pillow edge-tts")
        return 1

    FOTOS.mkdir(parents=True, exist_ok=True)
    try:
        _sync_user_photos()
    except Exception as e:
        print(f"AVISO sync fotos: {e}")

    WORK.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    clips: list[Path] = []

    print("Gerando voz Luna (Edge TTS) + legendas + video de hoje...")
    for i, scene in enumerate(SCENES):
        photo = FOTOS / scene["photo"]
        if not photo.exists():
            print(f"FALTA foto: {photo}")
            return 1
        audio = WORK / f"audio-{i:02d}.mp3"
        await _tts(scene["voice"], audio)
        clip = WORK / f"clip-{i:02d}.mp4"
        print(f"  Cena {i + 1}/{len(SCENES)}: {scene['lines'][0][0]} (+ voz)")
        _clip_with_captions(photo, scene, scene["voice"], audio, clip, f"scene{i:02d}")
        clips.append(clip)

    cta_audio = WORK / "audio-cta.mp3"
    await _tts(CTA["voice"], cta_audio)
    cta_clip = WORK / "clip-cta.mp4"
    print("  Cena CTA (+ voz)")
    _clip_cta_with_captions(CTA["voice"], cta_audio, cta_clip, "cta")
    clips.append(cta_clip)

    print("Unindo clips...")
    _concat_clips(clips, FINAL)
    try:
        shutil.copy2(FINAL, FINAL_ALIAS)
    except OSError:
        pass
    mb = FINAL.stat().st_size / 1024 / 1024
    print(f"\nPRONTO: {FINAL}")
    print(f"Tamanho: {mb:.1f} MB · 9:16 · voz Luna + legendas")
    print("Opcional: CapCut -> musica de fundo 12-20% -> exportar -> postar")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
