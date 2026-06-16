#!/usr/bin/env python3
"""Gera icon.png / adaptive-icon.png / splash-icon.png — logo grande, sem moldura cinza."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow", "-q"])
    from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "app" / "assets"
BRAND = ROOT / "marketing" / "brand"
# Igual app.config.ts splash + adaptiveIcon backgroundColor
BG = (10, 18, 42, 255)  # #0A122A
SIZE = 1024
ICON_FILL = 0.94  # iOS — ocupa quase o quadrado inteiro
ADAPTIVE_FILL = 0.72  # Android — zona segura ~66–72%


def find_logo() -> Path:
    for name in ("logo-master.png", "logo-site.png"):
        p = BRAND / name
        if p.is_file() and p.stat().st_size > 1000:
            return p
    for p in (ASSETS / "icon.png", ASSETS / "adaptive-icon.png"):
        if p.is_file():
            return p
    raise FileNotFoundError(
        f"Logo não encontrado. Coloque logo-master.png em {BRAND}"
    )


def _is_mockup_gray(r: int, g: int, b: int) -> bool:
    """Remove fundo cinza/preto de mockups (cantos do logo-site)."""
    if max(r, g, b) > 72:
        return False
    return max(r, g, b) - min(r, g, b) < 22


def strip_mockup_frame(src: Image.Image) -> Image.Image:
    im = src.convert("RGBA")
    px = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            if _is_mockup_gray(r, g, b):
                px[x, y] = (0, 0, 0, 0)
    bbox = im.getbbox()
    return im.crop(bbox) if bbox else im


def scale_on_bg(src: Image.Image, side: int, bg: tuple[int, ...], fill_ratio: float) -> Image.Image:
    canvas = Image.new("RGBA", (side, side), bg)
    im = strip_mockup_frame(src)
    target = max(1, int(side * fill_ratio))
    w, h = im.size
    scale = min(target / w, target / h)
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    im = im.resize((nw, nh), Image.Resampling.LANCZOS)
    x = (side - nw) // 2
    y = (side - nh) // 2
    canvas.paste(im, (x, y), im)
    return canvas.convert("RGB")


def adaptive_foreground(src: Image.Image) -> Image.Image:
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    im = strip_mockup_frame(src)
    target = int(SIZE * ADAPTIVE_FILL)
    w, h = im.size
    scale = min(target / w, target / h)
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    im = im.resize((nw, nh), Image.Resampling.LANCZOS)
    x = (SIZE - nw) // 2
    y = (SIZE - nh) // 2
    canvas.paste(im, (x, y), im)
    return canvas


def main() -> None:
    logo_path = find_logo()
    logo = Image.open(logo_path)
    ASSETS.mkdir(parents=True, exist_ok=True)

    icon = scale_on_bg(logo, SIZE, BG, ICON_FILL)
    adaptive = adaptive_foreground(logo)

    for name, img in (
        ("icon.png", icon),
        ("splash-icon.png", icon),
        ("adaptive-icon.png", adaptive),
    ):
        out = ASSETS / name
        img.save(out, "PNG", optimize=True)
        print(f"OK {out.relative_to(ROOT)}  ({out.stat().st_size // 1024} KB)")

    print(f"Fonte: {logo_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
