#!/usr/bin/env python3
"""
Reel pronto para postar — lê fotos + marketing/REEL-ENTREGA.json
Gera: MP4 (voz Luna + legendas + texto na tela) + POST-REEL-ENTREGA.txt

Uso:
  python scripts/generate_reel_entrega.py
  python scripts/generate_reel_entrega.py --config marketing/REEL-ENTREGA.json

Requisitos: pip install pillow edge-tts | ffmpeg no PATH
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "marketing" / "REEL-ENTREGA.json"

W, H = 1080, 1920
FPS = 30
VOICE = "pt-BR-FranciscaNeural"
PURPLE = (107, 33, 168)
PURPLE_DARK = (10, 18, 42)
FONT_BOLD = Path(r"C:\Windows\Fonts\segoeuib.ttf")
FONT_REG = Path(r"C:\Windows\Fonts\segoeui.ttf")

VOICE_RATE = "+22%"
AUDIO_PAD = 0.06
USE_ZOOM = False
CLEAR_MODE = True
CAPTION_FONT_SIZE = 56
TITLE_FONT_BOOST = 1.15
PHOTO_WIDTH_RATIO = 0.84
TOP_BAR_H = 300
BOTTOM_RESERVE = 220
BADGE_TEXT = "NOVO 1.0.42"

FOTOS: Path = ROOT / "marketing" / "CAPCUT-FOTOS-ENTREGA"
OUT_DIR = ROOT / "marketing" / "videos" / "app-real"
WORK = OUT_DIR / "_work-reel-entrega"
FINAL = OUT_DIR / "ego-ai-1.0.42-retencao-reels.mp4"
POST_FILE = ROOT / "marketing" / "POST-REEL-ENTREGA.txt"
SCENES: list[dict] = []


def _has_ffmpeg() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True, timeout=10)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return False


def _load_config(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    global FOTOS, FINAL, POST_FILE, SCENES, VOICE_RATE, AUDIO_PAD, USE_ZOOM, CLEAR_MODE, BADGE_TEXT
    global CAPTION_FONT_SIZE, TITLE_FONT_BOOST, PHOTO_WIDTH_RATIO, TOP_BAR_H, BOTTOM_RESERVE
    FOTOS = ROOT / data.get("fotos_dir", "marketing/CAPCUT-FOTOS-ENTREGA")
    FINAL = ROOT / data["output"]
    POST_FILE = ROOT / data.get("post_file", "marketing/POST-REEL-ENTREGA.txt")
    VOICE_RATE = data.get("voice_rate", "+22%")
    AUDIO_PAD = float(data.get("audio_pad", 0.06))
    USE_ZOOM = bool(data.get("use_zoom", False))
    CLEAR_MODE = bool(data.get("clear_mode", True))
    CAPTION_FONT_SIZE = int(data.get("caption_font_size", 56))
    TITLE_FONT_BOOST = float(data.get("title_font_boost", 1.15))
    PHOTO_WIDTH_RATIO = float(data.get("photo_width_ratio", 0.84))
    TOP_BAR_H = int(data.get("top_bar_h", 300))
    BOTTOM_RESERVE = int(data.get("bottom_reserve", 220))
    BADGE_TEXT = data.get("badge_text", "NOVO")
    SCENES = [_normalize_scene(s) for s in data["scenes"]]
    return data


def _normalize_scene(raw: dict) -> dict:
    lines = [tuple(line) for line in raw["lines"]]
    scene = {
        "photo": raw["photo"],
        "lines": lines,
        "voice": raw["voice"],
    }
    for key in ("darken", "center", "badge", "accent"):
        if key in raw:
            scene[key] = raw[key]
    return scene


def _resolve_photo(name: str) -> Path:
    return FOTOS / name


async def _tts(text: str, out: Path) -> None:
    import ssl

    import edge_tts
    import edge_tts.communicate as ec

    try:
        import certifi

        ec._SSL_CTX = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        pass

    try:
        await edge_tts.Communicate(text, VOICE, rate=VOICE_RATE).save(str(out))
    except Exception as exc:
        err = str(exc)
        if "SSL" not in err and "CERTIFICATE" not in err:
            raise
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ec._SSL_CTX = ctx
        await edge_tts.Communicate(text, VOICE, rate=VOICE_RATE).save(str(out))


def _audio_duration(path: Path) -> float:
    r = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True, text=True, check=True,
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


def _caption_bar_height(text: str | None) -> int:
    if not text:
        return BOTTOM_RESERVE
    font = _load_font(FONT_BOLD, CAPTION_FONT_SIZE)
    lines = _wrap_caption(text, font, W - 80, max_lines=3)
    line_h = CAPTION_FONT_SIZE + 12
    pad_y = 24
    bar_h = pad_y * 2 + line_h * len(lines)
    return max(BOTTOM_RESERVE, bar_h + 40)


def _title_bar_height(scene: dict) -> int:
    lines: list[tuple[str, int, bool]] = scene["lines"]
    y = 36
    if scene.get("badge"):
        y = 92
    for _, size, _ in lines:
        y += _title_size(size) + 10
    return max(TOP_BAR_H, y + 24)


def _fit_phone(img_path: Path, scene: dict | None = None, caption: str | None = None):
    from PIL import Image

    im = Image.open(img_path).convert("RGB")
    iw, ih = im.size
    canvas = Image.new("RGB", (W, H), PURPLE_DARK)

    if CLEAR_MODE:
        top = _title_bar_height(scene) if scene else TOP_BAR_H
        bottom = _caption_bar_height(caption)
        max_w = int(W * PHOTO_WIDTH_RATIO)
        avail_h = H - top - bottom
        scale = min(max_w / iw, avail_h / ih)
        nw, nh = max(1, int(iw * scale)), max(1, int(ih * scale))
        im = im.resize((nw, nh), Image.Resampling.LANCZOS)
        x = (W - nw) // 2
        y = top + max(0, (avail_h - nh) // 2)
        canvas.paste(im, (x, y))
        return canvas

    scale = W / iw
    nh = int(ih * scale)
    im = im.resize((W, nh), Image.Resampling.LANCZOS)
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
    return lines


def _draw_text_outlined(draw, xy, text: str, font, fill, outline=(0, 0, 0), width: int = 3) -> None:
    x, y = xy
    for dx in range(-width, width + 1):
        for dy in range(-width, width + 1):
            if dx or dy:
                draw.text((x + dx, y + dy), text, font=font, fill=outline, anchor="mm")
    draw.text((x, y), text, font=font, fill=fill, anchor="mm")


def _draw_caption(draw, text: str) -> None:
    font = _load_font(FONT_BOLD, CAPTION_FONT_SIZE)
    lines = _wrap_caption(text, font, W - 80, max_lines=3)
    line_h = CAPTION_FONT_SIZE + 12
    pad_y = 24
    bar_h = pad_y * 2 + line_h * len(lines)
    y0 = H - bar_h - 16
    draw.rectangle([0, y0, W, H - 8], fill=(8, 4, 22))
    draw.rectangle([0, y0, W, y0 + 6], fill=PURPLE)
    y = y0 + pad_y + line_h // 2
    for line in lines:
        _draw_text_outlined(draw, (W // 2, y), line, font, fill=(255, 255, 255), outline=(0, 0, 0), width=4)
        y += line_h


def _title_size(size: int) -> int:
    return max(28, int(size * TITLE_FONT_BOOST))


def _draw_novo_badge(draw, y_base: int = 72) -> None:
    font = _load_font(FONT_BOLD, 34)
    text = BADGE_TEXT
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pad_x, pad_y = 28, 14
    x0 = (W - tw) // 2 - pad_x
    y0 = y_base
    x1 = (W + tw) // 2 + pad_x
    y1 = y0 + th + pad_y * 2
    draw.rounded_rectangle([x0, y0, x1, y1], radius=24, fill=(255, 230, 80))
    draw.text((W // 2, y0 + pad_y + th // 2), text, fill=(30, 10, 60), font=font, anchor="mm")


def _draw_title_bar(draw, lines: list[tuple[str, int, bool]], scene: dict) -> int:
    """Barra roxa em cima — título grande, print fica livre abaixo."""
    bar_h = _title_bar_height(scene)
    draw.rectangle([0, 0, W, bar_h], fill=(*PURPLE, 250))
    y = 36
    if scene.get("badge"):
        _draw_novo_badge(draw, y_base=28)
        y = 92
    for i, (text, size, bold) in enumerate(lines):
        font = _load_font(FONT_BOLD if bold else FONT_REG, _title_size(size))
        if scene.get("accent") == i:
            color = (255, 230, 80)
        elif bold:
            color = (255, 255, 255)
        else:
            color = (220, 210, 255)
        _draw_text_outlined(
            draw, (W // 2, y + _title_size(size) // 2), text, font,
            fill=color, outline=(0, 0, 0), width=3,
        )
        y += _title_size(size) + 10
    return bar_h


def _render_scene(photo: Path, scene: dict, out: Path, caption: str | None = None) -> None:
    from PIL import Image, ImageDraw

    canvas = _fit_phone(photo, scene=scene, caption=caption)
    draw = ImageDraw.Draw(canvas)

    if scene.get("darken") and not CLEAR_MODE:
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, int(255 * scene["darken"])))
        canvas = canvas.convert("RGBA")
        canvas = Image.alpha_composite(canvas, overlay).convert("RGB")
        draw = ImageDraw.Draw(canvas)

    lines: list[tuple[str, int, bool]] = scene["lines"]
    if CLEAR_MODE or not scene.get("center"):
        _draw_title_bar(draw, lines, scene)
    else:
        total_h = sum(sz + 18 for _, sz, _ in lines)
        y = H // 2 - total_h // 2
        for i, (text, size, bold) in enumerate(lines):
            font = _load_font(FONT_BOLD if bold else FONT_REG, _title_size(size))
            if scene.get("accent") == i:
                color = (255, 230, 80)
            elif bold:
                color = (255, 255, 255)
            else:
                color = (230, 220, 255)
            _draw_text_outlined(draw, (W // 2, y + _title_size(size) // 2), text, font, fill=color)
            y += _title_size(size) + 18
        if scene.get("badge"):
            _draw_novo_badge(draw)
    if caption:
        _draw_caption(draw, caption)
    draw.rectangle([0, H - 8, W, H], fill=PURPLE)
    canvas.save(out, quality=95)


def _segment_from_image(img: Path, duration: float, out: Path) -> None:
    frames = max(int(duration * FPS), 1)
    if USE_ZOOM:
        # Ken Burns leve no frame 1080x1920 já composto — não recorta título nem legenda.
        vf = (
            f"scale={W}:{H},"
            f"zoompan=z='min(1.0+0.00035*on,1.035)'"
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={frames}:s={W}x{H}:fps={FPS}"
        )
    else:
        vf = (
            f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
            f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x0A122A"
        )
    subprocess.run(
        [
            "ffmpeg", "-y", "-loop", "1", "-i", str(img),
            "-vf", vf, "-t", f"{duration:.3f}", "-r", str(FPS),
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-an", str(out),
        ],
        check=True, capture_output=True,
    )


def _mux_video_audio(video: Path, audio: Path, out: Path) -> None:
    dur = _audio_duration(audio) + AUDIO_PAD
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(video), "-i", str(audio),
            "-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k", "-shortest", "-pix_fmt", "yuv420p", str(out),
        ],
        check=True, capture_output=True,
    )


def _concat_clips(clips: list[Path], out: Path) -> None:
    lst = WORK / "concat.txt"
    lines = [f"file '{c.resolve().as_posix()}'" for c in clips]
    lst.write_text("\n".join(lines), encoding="utf-8")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out)],
        check=True, capture_output=True,
    )


def _clip_with_captions(scene: dict, voice: str, audio: Path, out: Path, tag: str, photo: Path) -> None:
    sentences = _voice_sentences(voice) or [voice]
    dur = _audio_duration(audio) + AUDIO_PAD
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


def _write_post_file(cfg: dict) -> None:
    post = cfg["post"]
    tags = " ".join(post.get("hashtags", [])[:5])
    body = f"""POST — Reels/TikTok · EGO-AI {cfg.get('version', '')}
{'=' * 55}

ARQUIVO DO VÍDEO
----------------
{FINAL.relative_to(ROOT)}

TÍTULO DO REEL
--------------
{post['title']}

LEGENDA (copiar no post)
------------------------
{post['description']}

{tags}

COMENTÁRIO FIXADO
-----------------
{post.get('pinned_comment', '')}

CAPCUT (opcional)
-----------------
Importar o MP4 → Áudio → música motivacional 12–15% → exportar 1080p → postar

MÉTRICA ALVO
------------
{post.get('metric_target', 'Retenção 3s > 45% · visita perfil · clique bio')}
"""
    POST_FILE.write_text(body, encoding="utf-8")
    print(f"Post pronto: {POST_FILE}")


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="JSON com cenas e legenda")
    args = parser.parse_args()
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = ROOT / config_path
    if not config_path.exists():
        print(f"FALTA config: {config_path}")
        return 1

    cfg = _load_config(config_path)
    FOTOS.mkdir(parents=True, exist_ok=True)

    if not _has_ffmpeg():
        print("Instale ffmpeg: winget install ffmpeg")
        return 1
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        print("pip install pillow edge-tts")
        return 1

    missing = [s["photo"] for s in SCENES if not _resolve_photo(s["photo"]).exists()]
    if missing:
        unique = sorted(set(missing))
        print("FALTAM fotos em marketing/CAPCUT-FOTOS-ENTREGA/:")
        for name in unique:
            print(f"  - {name}")
        print("\nVeja LEIA-ME.txt na mesma pasta.")
        return 1

    WORK.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    clips: list[Path] = []

    print(f"Gerando reel ({len(SCENES)} cenas, voz Luna, zoom={USE_ZOOM})...")
    for i, scene in enumerate(SCENES):
        audio = WORK / f"audio-{i:02d}.mp3"
        await _tts(scene["voice"], audio)
        clip = WORK / f"clip-{i:02d}.mp4"
        title = scene["lines"][0][0]
        print(f"  Cena {i + 1}/{len(SCENES)}: {title}")
        photo = _resolve_photo(scene["photo"])
        _clip_with_captions(scene, scene["voice"], audio, clip, f"scene{i:02d}", photo)
        clips.append(clip)

    print("Unindo clips...")
    _concat_clips(clips, FINAL)
    _write_post_file(cfg)
    mb = FINAL.stat().st_size / 1024 / 1024
    print(f"\nPRONTO: {FINAL}")
    print(f"Tamanho: {mb:.1f} MB · 9:16 · voz + legendas")
    print("Voce so coloca musica 15% no CapCut e posta.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
