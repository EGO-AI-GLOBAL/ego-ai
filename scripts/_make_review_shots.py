from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "store" / "plans"
OUT.mkdir(parents=True, exist_ok=True)
ICON = ROOT / "app" / "assets" / "icon.png"

W, H = 1242, 2208  # spec de captura iPhone 5.5" aceite pela Apple
BG_TOP = (17, 16, 22)
BG_BOTTOM = (46, 26, 74)
PRIMARY = (167, 139, 250)
TEXT = (245, 244, 250)
MUTED = (170, 168, 185)
CARD = (28, 26, 36)

# Preço iOS = In-App Purchase (+30% do site)
PLANS = {
    "connection": ("EGO Conexão", "R$ 39,90", [
        "Chat de texto ilimitado com o seu avatar",
        "Conversa por voz com resposta em áudio",
        "Agenda e lembretes pessoais",
    ]),
    "premium": ("EGO Premium", "R$ 69,90", [
        "Tudo do plano Conexão",
        "Mais mensagens e voz por dia",
        "Agenda partilhada",
    ]),
    "total": ("EGO Total", "R$ 129,90", [
        "Tudo do plano Premium",
        "Limites máximos de uso",
        "Prioridade e recursos completos",
    ]),
}


def _font(size, bold=False):
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for c in candidates:
        try:
            return ImageFont.truetype(c, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _gradient(w, h, top, bottom):
    base = Image.new("RGB", (w, h), top)
    draw = ImageDraw.Draw(base)
    for y in range(h):
        t = y / h
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    return base


def make(tier, name, price, features):
    img = _gradient(W, H, BG_TOP, BG_BOTTOM)
    d = ImageDraw.Draw(img)

    # Ícone do app
    try:
        icon = Image.open(ICON).convert("RGBA").resize((220, 220))
        img.paste(icon, ((W - 220) // 2, 180), icon)
    except OSError:
        pass

    d.text((W // 2, 470), "EGO-AI", font=_font(56, bold=True), fill=TEXT, anchor="mm")
    d.text((W // 2, 545), "Assinatura mensal", font=_font(34), fill=MUTED, anchor="mm")

    # Cartão do plano
    cx0, cy0, cx1, cy1 = 110, 720, W - 110, 1560
    d.rounded_rectangle([cx0, cy0, cx1, cy1], radius=48, fill=CARD)

    d.text((W // 2, cy0 + 110), name, font=_font(72, bold=True), fill=TEXT, anchor="mm")
    d.text((W // 2, cy0 + 220), f"{price}/mês", font=_font(88, bold=True), fill=PRIMARY, anchor="mm")

    y = cy0 + 360
    fbody = _font(40)
    for feat in features:
        d.ellipse([cx0 + 70, y + 8, cx0 + 94, y + 32], fill=PRIMARY)
        d.text((cx0 + 130, y), feat, font=fbody, fill=TEXT)
        y += 100

    d.text((W // 2, cy1 + 90), "Compra dentro do app (In-App Purchase)",
           font=_font(34), fill=MUTED, anchor="mm")
    d.text((W // 2, cy1 + 150), "Renova automaticamente · cancele quando quiser",
           font=_font(30), fill=MUTED, anchor="mm")

    out = OUT / f"REVIEWSHOT-{tier}-1242x2208.png"
    img.convert("RGB").save(out)
    print(out.name, img.size)


def make_promo(tier, name, price):
    """Imagem promocional quadrada 1024x1024 exigida pela Apple."""
    S = 1024
    img = _gradient(S, S, BG_TOP, BG_BOTTOM)
    d = ImageDraw.Draw(img)
    try:
        icon = Image.open(ICON).convert("RGBA").resize((200, 200))
        img.paste(icon, ((S - 200) // 2, 130), icon)
    except OSError:
        pass
    d.text((S // 2, 400), "EGO-AI", font=_font(56, bold=True), fill=TEXT, anchor="mm")
    d.text((S // 2, 520), name, font=_font(70, bold=True), fill=TEXT, anchor="mm")
    d.text((S // 2, 640), f"{price}/mês", font=_font(80, bold=True), fill=PRIMARY, anchor="mm")
    d.text((S // 2, 760), "Assinatura mensal", font=_font(34), fill=MUTED, anchor="mm")
    d.text((S // 2, 900), "Compra dentro do app", font=_font(30), fill=MUTED, anchor="mm")
    out = OUT / f"PROMO-{tier}-1024.png"
    img.convert("RGB").save(out)
    print(out.name, img.size)


TARGET = ("total",)  # gerar só este; adicionar tier quando o preço for confirmado

for tier, (name, price, feats) in PLANS.items():
    if tier not in TARGET:
        continue
    make(tier, name, price, feats)
    make_promo(tier, name, price)

print("done")
