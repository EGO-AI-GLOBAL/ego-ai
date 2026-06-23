"""
Gera 6 imagens PNG por plano pago (Stripe / loja / anúncios).

Uso:
  pip install pillow
  python scripts/generate_plan_product_images.py
  python scripts/generate_plan_product_images.py --locale int
  python scripts/generate_plan_product_images.py --locale br --locale int

Saída: assets/store/plans/<locale>/<tier>/01-capa.png ... 06-resumo.png
Tamanho: 1080x1080 (quadrado, ideal para Stripe Product image)
"""

from __future__ import annotations

import argparse
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT_BASE = ROOT / "assets" / "store" / "plans"
OUT_TEAM_BASE = ROOT / "assets" / "store" / "plans-team"

TEAM_SEATS = (10, 20, 30, 40, 50, 100)
TEAM_DISCOUNT = 0.80

TEAM_UNIT_BRL = {"connection": 29.90, "premium": 49.90, "total": 99.90}
TEAM_UNIT_USD = {"connection": 7.99, "premium": 14.99, "total": 29.99}
ICON_PATH = ROOT / "app" / "assets" / "icon.png"

W, H = 1080, 1080

COLORS = {
    "bg_top": (15, 15, 18),
    "bg_bottom": (40, 22, 62),
    "card": (24, 24, 28),
    "primary": (124, 58, 237),
    "primary_soft": (167, 139, 250),
    "text": (250, 250, 250),
    "muted": (161, 161, 170),
    "accent_connection": (99, 102, 241),
    "accent_premium": (124, 58, 237),
    "accent_total": (217, 119, 6),
}

LOCALES = {
    "br": {
        "brand": "EGO-AI",
        "monthly": "/mês",
        "plans": {
            "connection": {
                "name": "EGO Conexão",
                "price": "R$ 29,90",
                "tagline": "Seu assistente no dia a dia",
                "accent": "accent_connection",
                "slides": [
                    ("01-capa", "Assinatura mensal", "Luna e Leo · chat, voz e agenda"),
                    ("02-chat", "Mensagens de texto", "Até 50 mensagens por dia"),
                    ("03-voz", "Mensagens de voz", "Até 15 áudios enviados por dia"),
                    ("04-audio-resposta", "Respostas em áudio", "Assistente fala com você (ilimitado no pacote)"),
                    ("05-agenda", "Agenda e lembretes", "Até 20 hábitos e 20 lembretes"),
                    ("06-resumo", "Pacote mensal inclui", "800 mil tokens · velocidade 1x, 1,5x e 2x"),
                ],
            },
            "premium": {
                "name": "EGO Premium",
                "price": "R$ 49,90",
                "tagline": "Mais conversa, voz e agenda",
                "accent": "accent_premium",
                "slides": [
                    ("01-capa", "Assinatura mensal", "Para quem usa o app todo dia"),
                    ("02-chat", "Chat sem limite diário", "Texto ilimitado (teto mensal de tokens)"),
                    ("03-voz", "Voz sem limite diário", "Microfone liberado no dia a dia"),
                    ("04-audio-resposta", "Áudio nas respostas", "TTS ilimitado dentro do pacote"),
                    ("05-agenda", "Agenda completa", "Hábitos e lembretes ilimitados"),
                    ("06-resumo", "Pacote mensal inclui", "2,5 milhões de tokens · histórico ampliado"),
                ],
            },
            "total": {
                "name": "EGO Total",
                "price": "R$ 99,90",
                "tagline": "Uso intenso, quase sem limites",
                "accent": "accent_total",
                "slides": [
                    ("01-capa", "Assinatura mensal", "Máximo desempenho para power users"),
                    ("02-chat", "Uso amplo", "Sem travas diárias de mensagens"),
                    ("03-voz", "Voz e áudio", "Conversa longa com assistente"),
                    ("04-audio-resposta", "Prioridade de produto", "Novidades e melhorias primeiro"),
                    ("05-agenda", "Organização total", "Agenda e lembretes sem teto"),
                    ("06-resumo", "Pacote mensal inclui", "5 milhões de tokens · uso generoso"),
                ],
            },
        },
    },
    "int": {
        "brand": "EGO-AI",
        "monthly": "/month",
        "plans": {
            "connection": {
                "name": "EGO AI Pro",
                "price": "US$ 7.99",
                "tagline": "Your daily AI companion",
                "accent": "accent_connection",
                "slides": [
                    ("01-capa", "Monthly subscription", "Luna & Leo · chat, voice & agenda"),
                    ("02-chat", "Text messages", "Up to 50 messages per day"),
                    ("03-voz", "Voice messages", "Up to 15 voice notes per day"),
                    ("04-audio-resposta", "Spoken replies", "Assistant talks back (within monthly pack)"),
                    ("05-agenda", "Agenda & reminders", "Up to 20 habits and 20 reminders"),
                    ("06-resumo", "Monthly pack includes", "800K tokens · 1x, 1.5x and 2x playback"),
                ],
            },
            "premium": {
                "name": "EGO AI Premium",
                "price": "US$ 14.99",
                "tagline": "More chat, voice & agenda",
                "accent": "accent_premium",
                "slides": [
                    ("01-capa", "Monthly subscription", "Built for daily use"),
                    ("02-chat", "No daily text cap", "Unlimited daily text (monthly token pool)"),
                    ("03-voz", "No daily voice cap", "Use the mic freely every day"),
                    ("04-audio-resposta", "Audio replies", "Unlimited TTS within your pack"),
                    ("05-agenda", "Full agenda", "Unlimited habits and reminders"),
                    ("06-resumo", "Monthly pack includes", "2.5M tokens · extended chat history"),
                ],
            },
            "total": {
                "name": "EGO AI Complete",
                "price": "US$ 29.99",
                "tagline": "Generous limits for power users",
                "accent": "accent_total",
                "slides": [
                    ("01-capa", "Monthly subscription", "Maximum headroom for heavy use"),
                    ("02-chat", "Ample usage", "No daily message friction"),
                    ("03-voz", "Voice & audio", "Long conversations with your assistant"),
                    ("04-audio-resposta", "Product priority", "Early access to new features"),
                    ("05-agenda", "Stay organized", "Unlimited agenda & reminders"),
                    ("06-resumo", "Monthly pack includes", "5M tokens · generous fair-use pool"),
                ],
            },
        },
    },
}


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = []
    if bold:
        candidates += [
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        ]
    else:
        candidates += [
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
        ]
    for path in candidates:
        p = Path(path)
        if p.exists():
            return ImageFont.truetype(str(p), size=size)
    return ImageFont.load_default()


def _gradient_bg() -> Image.Image:
    img = Image.new("RGB", (W, H), COLORS["bg_top"])
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / max(H - 1, 1)
        r = int(COLORS["bg_top"][0] * (1 - t) + COLORS["bg_bottom"][0] * t)
        g = int(COLORS["bg_top"][1] * (1 - t) + COLORS["bg_bottom"][1] * t)
        b = int(COLORS["bg_top"][2] * (1 - t) + COLORS["bg_bottom"][2] * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))
    return img


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    avg_char = max(font.getbbox("A")[2], 8)
    chars = max(12, max_width // avg_char)
    return textwrap.wrap(text, width=chars)


def _paste_icon(base: Image.Image, size: int = 120) -> None:
    if not ICON_PATH.exists():
        return
    icon = Image.open(ICON_PATH).convert("RGBA")
    icon = icon.resize((size, size), Image.Resampling.LANCZOS)
    x = W - size - 56
    y = 56
    base.paste(icon, (x, y), icon)


def render_slide(
    *,
    plan_name: str,
    price: str,
    monthly_suffix: str,
    tagline: str,
    accent_key: str,
    title: str,
    subtitle: str,
    brand: str,
    slide_id: str,
) -> Image.Image:
    img = _gradient_bg()
    draw = ImageDraw.Draw(img)
    accent = COLORS[accent_key]

    draw.rounded_rectangle((56, 56, W - 56, H - 56), radius=36, fill=COLORS["card"])
    draw.rounded_rectangle((56, 56, W - 56, 130), radius=36, fill=accent)

    font_brand = _font(28, bold=True)
    font_plan = _font(64, bold=True)
    font_price = _font(48, bold=True)
    font_title = _font(44, bold=True)
    font_sub = _font(32)
    font_small = _font(24)

    draw.text((88, 78), brand, font=font_brand, fill=COLORS["text"])
    _paste_icon(img)

    y = 170
    if slide_id == "01-capa":
        draw.text((88, y), plan_name, font=font_plan, fill=COLORS["text"])
        y += 88
        draw.text((88, y), f"{price}{monthly_suffix}", font=font_price, fill=COLORS["primary_soft"])
        y += 72
        draw.text((88, y), tagline, font=font_sub, fill=COLORS["muted"])
        y += 56
        draw.text((88, y), subtitle, font=font_sub, fill=COLORS["text"])
    else:
        draw.text((88, y), title, font=font_title, fill=COLORS["text"])
        y += 64
        for line in _wrap(draw, subtitle, font_sub, W - 176):
            draw.text((88, y), line, font=font_sub, fill=COLORS["muted"])
            y += 42
        y += 24
        draw.text((88, y), plan_name, font=font_small, fill=accent)
        draw.text((88, y + 36), f"{price}{monthly_suffix}", font=font_small, fill=COLORS["primary_soft"])

    # Rodapé decorativo
    draw.rounded_rectangle((88, H - 160, W - 88, H - 100), radius=20, fill=(36, 36, 42))
    draw.text((108, H - 142), f"{plan_name} · {price}{monthly_suffix}", font=font_small, fill=COLORS["text"])

    return img


def _fmt_brl(value: float) -> str:
    whole = int(value)
    cents = int(round((value - whole) * 100)) % 100
    int_str = f"{whole:,}".replace(",", ".")
    return f"R$ {int_str},{cents:02d}"


def _fmt_usd(value: float) -> str:
    return f"US$ {value:.2f}"


def _team_price(locale: str, tier: str, seats: int) -> str:
    unit = TEAM_UNIT_BRL if locale == "br" else TEAM_UNIT_USD
    total = seats * unit[tier] * TEAM_DISCOUNT
    return _fmt_brl(total) if locale == "br" else _fmt_usd(total)


TEAM_LOCALES = {
    "br": {
        "brand": "EGO-AI",
        "monthly": "/mês",
        "people": "pessoas",
        "shared": "Agendas compartilhadas · 20% de economia",
        "tiers": {
            "connection": {"name": "EGO Conexão Equipe", "accent": "accent_connection"},
            "premium": {"name": "EGO Premium Equipe", "accent": "accent_premium"},
            "total": {"name": "EGO Total Equipe", "accent": "accent_total"},
        },
    },
    "int": {
        "brand": "EGO-AI",
        "monthly": "/month",
        "people": "people",
        "shared": "Shared calendars · save 20%",
        "tiers": {
            "connection": {"name": "EGO AI Pro Team", "accent": "accent_connection"},
            "premium": {"name": "EGO AI Premium Team", "accent": "accent_premium"},
            "total": {"name": "EGO AI Complete Team", "accent": "accent_total"},
        },
    },
}


def render_team_capa(
    *,
    plan_line: str,
    seats: int,
    price: str,
    monthly_suffix: str,
    accent_key: str,
    shared_line: str,
    brand: str,
) -> Image.Image:
    img = _gradient_bg()
    draw = ImageDraw.Draw(img)
    accent = COLORS[accent_key]
    draw.rounded_rectangle((56, 56, W - 56, H - 56), radius=36, fill=COLORS["card"])
    draw.rounded_rectangle((56, 56, W - 56, 130), radius=36, fill=accent)
    font_brand = _font(28, bold=True)
    font_plan = _font(52, bold=True)
    font_seats = _font(72, bold=True)
    font_price = _font(46, bold=True)
    font_sub = _font(30)
    draw.text((88, 78), brand, font=font_brand, fill=COLORS["text"])
    _paste_icon(img)
    y = 168
    draw.text((88, y), plan_line, font=font_plan, fill=COLORS["text"])
    y += 76
    draw.text((88, y), str(seats), font=font_seats, fill=COLORS["primary_soft"])
    y += 88
    draw.text((88, y), shared_line.split(" · ")[0] if "·" in shared_line else shared_line, font=font_sub, fill=COLORS["muted"])
    y += 44
    draw.text((88, y), f"{price}{monthly_suffix}", font=font_price, fill=COLORS["text"])
    y += 64
    draw.text((88, y), shared_line, font=font_sub, fill=COLORS["muted"])
    draw.rounded_rectangle((88, H - 160, W - 88, H - 100), radius=20, fill=(36, 36, 42))
    draw.text((108, H - 142), f"{plan_line} · {seats} · {price}{monthly_suffix}", font=_font(22), fill=COLORS["text"])
    return img


def generate_team_locale(locale: str) -> list[Path]:
    cfg = TEAM_LOCALES[locale]
    written: list[Path] = []
    people = cfg["people"]
    for tier, tcfg in cfg["tiers"].items():
        for seats in TEAM_SEATS:
            out_dir = OUT_TEAM_BASE / locale / tier / str(seats)
            out_dir.mkdir(parents=True, exist_ok=True)
            price = _team_price(locale, tier, seats)
            subtitle = f"Até {seats} {people}"
            img = render_team_capa(
                plan_line=tcfg["name"],
                seats=seats,
                price=price,
                monthly_suffix=cfg["monthly"],
                accent_key=tcfg["accent"],
                shared_line=f"{subtitle} · {cfg['shared']}",
                brand=cfg["brand"],
            )
            path = out_dir / "01-capa.png"
            img.save(path, "PNG", optimize=True)
            written.append(path)
    return written


def generate_locale(locale: str) -> list[Path]:
    cfg = LOCALES[locale]
    written: list[Path] = []
    for tier, plan in cfg["plans"].items():
        out_dir = OUT_BASE / locale / tier
        out_dir.mkdir(parents=True, exist_ok=True)
        for slide_id, title, subtitle in plan["slides"]:
            img = render_slide(
                plan_name=plan["name"],
                price=plan["price"],
                monthly_suffix=cfg["monthly"],
                tagline=plan["tagline"],
                accent_key=plan["accent"],
                title=title,
                subtitle=subtitle,
                brand=cfg["brand"],
                slide_id=slide_id,
            )
            path = out_dir / f"{slide_id}.png"
            img.save(path, "PNG", optimize=True)
            written.append(path)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera imagens de produto por plano EGO-AI")
    parser.add_argument(
        "--locale",
        action="append",
        choices=sorted(LOCALES.keys()),
        help="br e/ou int (padrão: ambos)",
    )
    parser.add_argument(
        "--team",
        action="store_true",
        help="Gera capas dos planos Equipe (plans-team/)",
    )
    parser.add_argument(
        "--individual",
        action="store_true",
        help="Gera pacotes particulares (plans/) — padrão se nada for passado",
    )
    args = parser.parse_args()
    do_team = args.team
    do_individual = args.individual or not do_team
    locales = args.locale or ["br", "int"]
    all_paths: list[Path] = []
    if do_individual:
        for loc in locales:
            all_paths.extend(generate_locale(loc))
        print(f"Particulares: {len(all_paths)} imagens em {OUT_BASE}")
    if do_team:
        team_paths: list[Path] = []
        for loc in locales:
            team_paths.extend(generate_team_locale(loc))
        print(f"Equipes: {len(team_paths)} capas em {OUT_TEAM_BASE}")
        all_paths.extend(team_paths)
    if not all_paths:
        print("Nada gerado. Use --individual e/ou --team")
        return
    for p in all_paths[:6]:
        print(f"  {p.relative_to(ROOT)}")
    if len(all_paths) > 6:
        print(f"  ... e mais {len(all_paths) - 6}")


if __name__ == "__main__":
    main()
