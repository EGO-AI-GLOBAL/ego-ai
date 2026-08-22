# -*- coding: utf-8 -*-
"""Alinha site + copy freemium: 0 trial · Essential grátis · Premium pago."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site-publico"


def patch_file(path: Path, replacements: list[tuple[str, str]]) -> int:
    text = path.read_text(encoding="utf-8")
    n = 0
    for old, new in replacements:
        c = text.count(old)
        if c:
            text = text.replace(old, new)
            n += c
            print(f"  {path.name}: {c}x «{old[:50]}…»" if len(old) > 50 else f"  {path.name}: {c}x «{old}»")
    path.write_text(text, encoding="utf-8", newline="\n")
    return n


def main() -> None:
    home = SITE / "index.html"
    planos = SITE / "planos" / "index.html"

    print("=== site home ===")
    patch_file(
        home,
        [
            (
                '<span class="badge" id="site-badge">3 dias grátis · depois Premium</span>',
                '<span class="badge" id="site-badge">Grátis com texto · voz no Premium</span>',
            ),
            (
                "Converse com qualquer dos 12 avatares por texto ou microfone. Respostas com rosto e voz - comece com 3 dias grátis.",
                "Converse com Luna e Leo por texto no plano grátis (Essential). Voz e áudio do avatar no Premium.",
            ),
            (
                "Converse com qualquer dos 12 avatares por texto ou microfone. Respostas com rosto e voz — comece com 3 dias grátis.",
                "Converse com Luna e Leo por texto no plano grátis (Essential). Voz e áudio do avatar no Premium.",
            ),
            (
                '<p class="section-sub">3 dias grátis · depois trava · EGO Premium para continuar</p>',
                '<p class="section-sub">Essential grátis (texto + anúncios) · Premium com voz</p>',
            ),
            (
                "<p><strong>3 dias grátis</strong> para experimentar · depois o app trava</p>",
                "<p><strong>Essential grátis:</strong> chat por texto (até 5 msgs/dia) com anúncios. Sem trava — a voz fica no Premium.</p>",
            ),
            (
                "<p style=\"margin-top:12px\"><strong>EGO Premium - R$ 49,90</strong>/mês</p>",
                "<p style=\"margin-top:12px\"><strong>EGO Premium — R$ 49,90</strong>/mês · sem anúncios · voz liberada</p>",
            ),
            (
                "<li>Texto e voz no Premium</li>",
                "<li>Texto amplo + voz Luna/Leo</li>",
            ),
        ],
    )

    print("=== site planos ===")
    patch_file(
        planos,
        [
            (
                '<p class="sub">3 dias grátis. Depois trava - assine o EGO Premium. Se o amigo pagar, quem indicou ganha 1 mês.</p>',
                '<p class="sub">Essential grátis: texto (5 msgs/dia) com anúncios. Premium: voz sem anúncios. Indique: se o amigo pagar, você ganha 1 mês.</p>',
            ),
            (
                "<strong>3 dias grátis</strong> para experimentar o app.<br />\n"
                " Depois disso, o uso <strong>trava</strong> e é preciso <strong>pagar/assinar o EGO Premium</strong> para continuar.",
                "<strong>Essential</strong> é grátis: chat por texto (até 5 mensagens/dia) com anúncios.<br />\n"
                " A <strong>voz</strong> (gravar e ouvir Luna/Leo) fica no <strong>EGO Premium</strong>.",
            ),
            (
                '      <h3>Teste</h3>\n'
                '      <div class="price" style="color:var(--success)">3 dias</div>',
                '      <h3>Essential</h3>\n'
                '      <div class="price" style="color:var(--success)">Grátis</div>',
            ),
            (
                "<li>3 dias para experimentar</li>",
                "<li>Texto até 5 msgs/dia</li>",
            ),
            (
                '<span class="btn btn-muted">Baixe e teste 3 dias</span>',
                '<span class="btn btn-muted">Baixe grátis · Essential</span>',
            ),
            (
                "<li>Texto e voz no Premium</li>",
                "<li>Texto amplo + voz Luna/Leo</li>",
            ),
        ],
    )

    # Fallback: catch remaining "3 dias" / trava phrases if encoding variants remain
    for path in (home, planos):
        t = path.read_text(encoding="utf-8")
        leftovers = []
        for needle in ("3 dias", "três dias", "trava", "Trava"):
            if needle in t.lower() if needle.islower() else needle in t:
                # case-sensitive count for display
                if needle in t:
                    leftovers.append(f"{needle}={t.count(needle)}")
        if leftovers:
            print(f"  AVISO {path.name}: ainda {', '.join(leftovers)}")
        else:
            print(f"  OK {path.name}: sem 3 dias / trava óbvios")


if __name__ == "__main__":
    main()
