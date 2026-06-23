#!/usr/bin/env python3
"""Gera imagens da Play Console em pastas nomeadas como cada campo do formulário."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow", "-q"])
    from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "app" / "assets"
BASE = ROOT / "app" / "store-assets"

# Pastas = nomes dos campos na Play Console (pt-BR)
DIR_ICON = BASE / "01-icone-do-aplicativo"
DIR_FEATURE = BASE / "02-recurso-grafico"
DIR_PHONE = BASE / "03-capturas-telefone"
DIR_TABLET_7 = BASE / "04-capturas-tablet-7-pol"
DIR_TABLET_10 = BASE / "05-capturas-tablet-10-pol"
DIR_VIDEO = BASE / "06-video-opcional-VAZIO"
DIR_CHROMEBOOK = BASE / "07-chromebook-opcional-VAZIO"
DIR_XR = BASE / "08-android-xr-opcional-VAZIO"

BG = (9, 9, 11)
PRIMARY = (167, 139, 250)
PRIMARY_DIM = (124, 58, 237)
TEXT = (250, 250, 250)
MUTED = (161, 161, 170)


def load_fonts(large: int = 52, small: int = 32):
    for name in ("arial.ttf", "segoeui.ttf", "calibri.ttf"):
        try:
            return (
                ImageFont.truetype(name, large),
                ImageFont.truetype(name, small),
            )
        except OSError:
            continue
    default = ImageFont.load_default()
    return default, default


def make_icon(path: Path) -> None:
    src = ASSETS / "adaptive-icon.png"
    if not src.is_file():
        src = ASSETS / "icon.png"
    icon = Image.open(src).convert("RGBA").resize((512, 512), Image.Resampling.LANCZOS)
    bg = Image.new("RGBA", (512, 512), (18, 28, 44, 255))
    bg.paste(icon, (0, 0), icon)
    out = path / "icone-512x512.png"
    bg.convert("RGB").save(out, "PNG", optimize=True)
    print(f"OK {out.relative_to(BASE)}")


def make_feature(path: Path) -> None:
    fg = Image.new("RGB", (1024, 500), BG)
    draw = ImageDraw.Draw(fg)
    for x in range(1024):
        t = x / 1024
        c = tuple(int(BG[i] * (1 - t) + PRIMARY_DIM[i] * t * 0.35) for i in range(3))
        draw.line([(x, 0), (x, 500)], fill=c)
    font_l, font_s = load_fonts(72, 36)
    draw.text((48, 160), "EGO-AI", fill=PRIMARY, font=font_l)
    draw.text((48, 260), "O amigo que não te abandona", fill=TEXT, font=font_s)
    draw.text((48, 320), "Chat com IA  |  Voz  |  Agenda", fill=MUTED, font=font_s)
    icon_src = ASSETS / "icon.png"
    if icon_src.is_file():
        tile = Image.new("RGBA", (280, 280), (18, 28, 44, 255))
        im = Image.open(icon_src).convert("RGBA").resize((248, 248), Image.Resampling.LANCZOS)
        tile.paste(im, (16, 16), im)
        fg.paste(tile, (700, 110), tile)
    out = path / "banner-1024x500.png"
    fg.save(out, "PNG", optimize=True)
    print(f"OK {out.relative_to(BASE)}")


def make_screenshot(title: str, sub: str) -> Image.Image:
    w, h = 1080, 1920
    img = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([40, 80, w - 40, 200], radius=24, fill=(20, 20, 22))
    ft, fs = load_fonts()
    d.text((72, 120), "EGO-AI", fill=PRIMARY, font=ft)
    d.rounded_rectangle([40, 240, w - 40, h - 280], radius=32, fill=(20, 20, 22))
    d.text((72, 320), title, fill=TEXT, font=ft)
    d.text((72, 400), sub, fill=MUTED, font=fs)
    icon_path = ASSETS / "icon.png"
    if icon_path.is_file():
        a = Image.open(icon_path).convert("RGBA").resize((420, 420), Image.Resampling.LANCZOS)
        img.paste(a, ((w - 420) // 2, 680), a)
    d.rounded_rectangle([80, h - 180, w - 80, h - 100], radius=40, fill=PRIMARY_DIM)
    d.text((w // 2 - 140, h - 155), "Continuar", fill=TEXT, font=fs)
    return img


def write_readme(folder: Path, lines: list[str]) -> None:
    (folder / "LEIA-ME.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    specs = [
        ("01-login.png", "Entrar na sua conta", "E-mail e senha seguros"),
        ("02-chat.png", "Chat com assistente IA", "Texto e mensagens de voz"),
        ("03-agenda.png", "Agenda pessoal", "Compromissos e lembretes"),
        ("04-home.png", "Tudo em um só lugar", "Assistente, chat e agenda"),
    ]

    for d in (
        DIR_ICON,
        DIR_FEATURE,
        DIR_PHONE,
        DIR_TABLET_7,
        DIR_TABLET_10,
        DIR_VIDEO,
        DIR_CHROMEBOOK,
        DIR_XR,
    ):
        d.mkdir(parents=True, exist_ok=True)

    make_icon(DIR_ICON)
    make_feature(DIR_FEATURE)

    images: list[Image.Image] = []
    for fname, title, sub in specs:
        im = make_screenshot(title, sub)
        images.append(im)
        out = DIR_PHONE / fname
        im.save(out, "PNG", optimize=True)
        print(f"OK {out.relative_to(BASE)}")

    for i, im in enumerate(images, 1):
        im.save(DIR_TABLET_7 / f"{i:02d}.png", "PNG", optimize=True)
        scaled = im.resize((1200, int(1200 * 16 / 9)), Image.Resampling.LANCZOS)
        scaled.save(DIR_TABLET_10 / f"{i:02d}.png", "PNG", optimize=True)
    print(f"OK {DIR_TABLET_7.name} (4 imagens)")
    print(f"OK {DIR_TABLET_10.name} (4 imagens)")

    write_readme(
        DIR_ICON,
        [
            "PLAY CONSOLE: Ícone do aplicativo *",
            "Envie: icone-512x512.png",
            "Tamanho: 512 x 512 px, PNG, max 1 MB",
        ],
    )
    write_readme(
        DIR_FEATURE,
        [
            "PLAY CONSOLE: Recurso gráfico *",
            "Envie: banner-1024x500.png",
            "Tamanho: 1024 x 500 px, PNG, max 15 MB",
        ],
    )
    write_readme(
        DIR_PHONE,
        [
            "PLAY CONSOLE: Capturas de tela do telefone *",
            "Envie as 4 imagens (minimo 2):",
            "  01-login.png",
            "  02-chat.png",
            "  03-agenda.png",
            "  04-home.png",
            "Proporcao 9:16 (vertical)",
        ],
    )
    write_readme(
        DIR_TABLET_7,
        [
            "PLAY CONSOLE: Capturas de tela do tablet de 7 pol. *",
            "Envie: 01.png, 02.png, 03.png, 04.png",
        ],
    )
    write_readme(
        DIR_TABLET_10,
        [
            "PLAY CONSOLE: Capturas de tela de tablet de 10 pol. *",
            "Envie: 01.png, 02.png, 03.png, 04.png",
        ],
    )
    for folder, title in (
        (DIR_VIDEO, "Video (YouTube) — NAO enviar nada"),
        (DIR_CHROMEBOOK, "Chromebook — NAO enviar (opcional)"),
        (DIR_XR, "Android XR — NAO enviar (opcional)"),
    ):
        write_readme(folder, [title, "Deixe vazio na Play Console."])

    # Limpar ficheiros antigos na raiz de store-assets
    for old in BASE.glob("*.png"):
        if old.is_file():
            old.unlink()
    for old in BASE.glob("*.jpg"):
        if old.is_file():
            old.unlink()

    print(f"\nPronto: {BASE}")


if __name__ == "__main__":
    main()
