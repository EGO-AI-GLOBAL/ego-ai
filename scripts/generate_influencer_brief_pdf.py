#!/usr/bin/env python3
"""Gera PDF do brief para influencers (requer fpdf2)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRAND_PATH = ROOT / "marketing" / "brand" / "config.json"
PDF_PATH = ROOT / "marketing" / "influencers" / "BRIEF_CREATORS_EGO-AI.pdf"


def _sanitize(text: str) -> str:
    replacements = {
        "\u2014": "-",
        "\u2013": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2022": "*",
        "\u2192": "->",
        "\u00e7": "c",
        "\u00e3": "a",
        "\u00f5": "o",
        "\u00e1": "a",
        "\u00e9": "e",
        "\u00ed": "i",
        "\u00f3": "o",
        "\u00fa": "u",
        "\u00c1": "A",
        "\u00c3": "A",
        "\u00c7": "C",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode("ascii", "replace").decode("ascii")


def _load_brand() -> dict:
    if BRAND_PATH.is_file():
        return json.loads(BRAND_PATH.read_text(encoding="utf-8"))
    return {"brandName": "EGO-AI", "domain": "egoai.app", "instagram": "@egoai.br"}


def main() -> int:
    try:
        from fpdf import FPDF
    except ImportError:
        print("Instale: pip install fpdf2")
        return 1

    brand = _load_brand()
    name = brand.get("brandName", "EGO-AI")
    domain = brand.get("domain", "egoai.app")
    site = brand.get("siteUrl", f"https://{domain}")
    ig = brand.get("instagram", "@egoai.br")
    utm = brand.get("utm", {}).get("influencer", "utm_source=influencer")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()
    content_w = pdf.w - pdf.l_margin - pdf.r_margin

    def _write(fn, h: float, t: str) -> None:
        pdf.set_x(pdf.l_margin)
        fn(content_w, h, _sanitize(t))

    def title(t: str) -> None:
        pdf.set_font("Helvetica", style="B", size=16)
        _write(pdf.multi_cell, 8, t)
        pdf.ln(2)

    def h2(t: str) -> None:
        pdf.set_font("Helvetica", style="B", size=12)
        _write(pdf.multi_cell, 6, t)
        pdf.ln(1)

    def body(t: str) -> None:
        pdf.set_font("Helvetica", size=10)
        _write(pdf.multi_cell, 5, t)
        pdf.ln(2)

    def bullet(t: str) -> None:
        pdf.set_font("Helvetica", size=10)
        _write(pdf.multi_cell, 5, f"  - {t}")
        pdf.ln(1)

    title(f"{name} - Campanha #MeuNovoAmigo")
    body(f"Brief para creators | {site} | {ig}")
    body(f"Link rastreavel sugerido: {site}?{utm}&ref=NOME_DO_CREATOR")
    pdf.ln(2)

    h2("Objetivo")
    body(
        "Gerar instalacoes organicas mostrando o EGO-AI como companheiro do dia a dia "
        "- nao como app de IA tecnico."
    )

    h2("Perfil ideal")
    bullet("Nicho: rotina, lifestyle, autocuidado, produtividade leve")
    bullet("Tamanho: 10k a 150k seguidores (micro/medio)")
    bullet("Evitar: reviewers de gadget e canais so de prompt ChatGPT")
    pdf.ln(2)

    h2("Entregaveis (por creator)")
    bullet("Reels/TikTok 45-90s: vlog + conversa no viva-voz com Luna ou Leo")
    bullet("Mostrar resposta acolhedora + 1 lembrete ou habito criado no app")
    bullet("Stories 3 frames: hook / tela do app / link na bio")
    bullet(f"Legenda: {ig} #MeuNovoAmigo + link na bio, comeco gratis")
    pdf.ln(2)

    h2("Roteiro Reels (sugestao)")
    bullet('Hook 3s: "Precisava de alguem pra ouvir meu domingo a noite..."')
    bullet("Contexto 10s: dia corrido")
    bullet("Demo 25s: audio desabafo + pedido de lembrete")
    bullet("Reacao 10s: resposta humana da IA na tela")
    bullet(f'CTA 5s: "{name}, gratis. Luna ou Leo. Link na bio."')
    pdf.ln(2)

    h2('Corte viral "Desabafo" (opcional)')
    bullet("Tela chat fullscreen")
    bullet('Legenda: "Como lidar com ansiedade de domingo a noite?"')
    bullet("Audio real da resposta 10-20s")
    bullet(f'Final: "Que app e esse? -> {name}"')
    pdf.ln(2)

    h2("Tom e compliance")
    bullet("Autentico, vulneravel, leve")
    bullet("NAO dizer que substitui terapia ou medico")
    bullet("NAO inventar funcionalidades")
    bullet(
        'Frase segura: "Me ajuda a organizar e desabafar; nao e consulta medica."'
    )
    pdf.ln(2)

    h2("Remuneracao sugerida (BR)")
    bullet("10k-30k: R$ 300-800 + link rastreavel")
    bullet("30k-100k: R$ 800-2.500")
    bullet("100k+: pacote 2 videos (negociar)")
    pdf.ln(2)

    h2("Kit anexo")
    bullet(f"Landing: {site}")
    bullet("PNG Luna e Leo (avatar-f1 / avatar-m1)")
    bullet("3 screenshots: chat, agenda, planos")
    bullet("Scripts de voz 15s em marketing/anuncios/SCRIPTS_15S_FALAS.md")
    pdf.ln(2)

    h2("KPIs")
    bullet('Comentarios "que app e esse?"')
    bullet(f"Cliques UTM: {utm}")
    bullet("Instalacoes (Play Console quando publicado)")

    pdf.ln(4)
    body(f"(c) {name} - Nao substitui acompanhamento medico ou psicologico.")

    PDF_PATH.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(PDF_PATH))
    print(f"PDF gerado: {PDF_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
