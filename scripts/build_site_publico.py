#!/usr/bin/env python3
"""Gera site-publico/ pronto para upload na UOL (FTP / gerenciador de arquivos)."""

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_LANDING = ROOT / "marketing" / "landing"
SRC_BRAND = ROOT / "marketing" / "brand"
OUT = ROOT / "site-publico"


def clean_output_dir(out: Path) -> None:
    """Limpa site-publico/ sem falhar se OneDrive bloquear uma pasta."""
    out.mkdir(parents=True, exist_ok=True)

    def _on_rm_error(func, path, exc_info):
        import stat

        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except OSError:
            pass

    for item in list(out.iterdir()):
        if item.is_file():
            try:
                item.unlink()
            except OSError:
                pass
        elif item.is_dir():
            try:
                shutil.rmtree(item, onerror=_on_rm_error)
            except OSError:
                pass


def copy_tree_files(src: Path, dst: Path) -> None:
    """Copia ficheiros (OneDrive reparse points quebram shutil.copytree)."""
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.rglob("*"):
        if not item.is_file():
            continue
        rel = item.relative_to(src)
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)

# Import legal texts from project
import sys

sys.path.insert(0, str(ROOT))
from legal_copy import (  # noqa: E402
    privacy_policy_markdown,
    refund_policy_markdown,
    terms_of_use_markdown,
)


def md_to_html(md: str) -> str:
    """Conversão mínima markdown → HTML (títulos, negrito, parágrafos)."""
    lines = md.strip().split("\n")
    parts: list[str] = []
    in_p = False
    for line in lines:
        line = line.rstrip()
        if not line:
            if in_p:
                parts.append("</p>")
                in_p = False
            continue
        if line.startswith("## "):
            if in_p:
                parts.append("</p>")
                in_p = False
            parts.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("### "):
            if in_p:
                parts.append("</p>")
                in_p = False
            parts.append(f"<h3>{line[4:]}</h3>")
        else:
            text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line)
            if not in_p:
                parts.append(f"<p>{text}")
                in_p = True
            else:
                parts.append(f" {text}")
    if in_p:
        parts.append("</p>")
    return "\n".join(parts)


def legal_page(title: str, body_html: str, back: str = "/") -> str:
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title} — EGO-AI</title>
  <style>
    :root {{ --bg:#09090b; --text:#fafafa; --muted:#a1a1aa; --primary:#a78bfa; }}
    body {{ font-family: system-ui, sans-serif; background: var(--bg); color: var(--text);
      max-width: 720px; margin: 0 auto; padding: 2rem 1.25rem 4rem; line-height: 1.65; }}
    a {{ color: var(--primary); }}
    h1 {{ font-size: 1.75rem; margin-bottom: 0.5rem; }}
  </style>
</head>
<body>
  <p><a href="{back}">← Voltar ao site</a></p>
  <h1>{title}</h1>
  <article>{body_html}</article>
  <p style="margin-top:2rem;color:var(--muted);font-size:0.9rem;">
    Dúvidas: <a href="mailto:contato@egoai.com.br">contato@egoai.com.br</a>
  </p>
</body>
</html>
"""


def legal_sections_html() -> str:
    blocks = [
        ("contato", "Contato", """
        <p>Suporte e dúvidas sobre o EGO-AI:</p>
        <p><strong><a href="mailto:contato@egoai.com.br">contato@egoai.com.br</a></strong></p>
        <p>Resposta em dias úteis.</p>
        """),
        ("termos", "Termos de Uso", md_to_html(terms_of_use_markdown())),
        ("privacidade", "Política de Privacidade", md_to_html(privacy_policy_markdown())),
        ("reembolso", "Política de Reembolso", md_to_html(refund_policy_markdown())),
    ]
    parts = []
    for sid, title, body in blocks:
        parts.append(
            f'<article class="legal-block" id="{sid}"><h2>{title}</h2>{body}</article>'
        )
    return "\n".join(parts)


def redirect_html(anchor: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head>
  <meta charset="utf-8" />
  <meta http-equiv="refresh" content="0;url=/{anchor}" />
  <link rel="canonical" href="https://egoai.com.br/{anchor}" />
  <script>location.replace("/{anchor}");</script>
  <title>EGO-AI</title>
</head><body><p><a href="/{anchor}">Continuar</a></p></body></html>
"""


def exclusao_conta_page() -> str:
    return """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Exclusão de conta — EGO-AI</title>
  <style>
    :root { --bg:#09090b; --text:#fafafa; --muted:#a1a1aa; --primary:#a78bfa; }
    body { font-family: system-ui, sans-serif; background: var(--bg); color: var(--text);
      max-width: 640px; margin: 0 auto; padding: 2rem 1.25rem; line-height: 1.65; }
    a { color: var(--primary); }
    ol { padding-left: 1.25rem; }
    li { margin-bottom: 0.5rem; }
  </style>
</head>
<body>
  <p><a href="/">← Voltar ao site</a></p>
  <h1>Exclusão de conta</h1>
  <p>Para apagar sua conta e dados do EGO-AI:</p>
  <ol>
    <li>Abra o app EGO-AI e faça login.</li>
    <li>Vá em <strong>Conta</strong> (menu).</li>
    <li>Toque em <strong>Excluir minha conta</strong> e confirme.</li>
  </ol>
  <p>Ou envie e-mail para
    <strong><a href="mailto:contato@egoai.com.br?subject=Exclus%C3%A3o%20de%20conta%20EGO-AI">contato@egoai.com.br</a></strong>
    com o mesmo e-mail ou telefone usado no cadastro.</p>
  <p style="color:var(--muted);font-size:0.9rem;">
    Processamos em dias úteis. Dados essenciais para faturação podem ser mantidos pelo prazo legal.
    Veja também a <a href="/privacidade/">Política de Privacidade</a>.
  </p>
</body>
</html>
"""


def contato_page() -> str:
    return """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Contato — EGO-AI</title>
  <style>
    :root { --bg:#09090b; --text:#fafafa; --muted:#a1a1aa; --primary:#a78bfa; }
    body { font-family: system-ui, sans-serif; background: var(--bg); color: var(--text);
      max-width: 560px; margin: 0 auto; padding: 2rem 1.25rem; line-height: 1.6; }
    a { color: var(--primary); }
  </style>
</head>
<body>
  <p><a href="/">← Voltar ao site</a></p>
  <h1>Contato</h1>
  <p>Suporte e dúvidas sobre o app EGO-AI:</p>
  <p><strong><a href="mailto:contato@egoai.com.br">contato@egoai.com.br</a></strong></p>
  <p style="color:var(--muted);font-size:0.9rem;">
    Resposta em dias úteis. Para privacidade e dados pessoais, veja a
    <a href="/privacidade/">Política de Privacidade</a>.
  </p>
</body>
</html>
"""


def build_full_index() -> str:
    index = (SRC_LANDING / "index.html").read_text(encoding="utf-8")
    short_legal = (
        ' <a href="privacidade/">Política completa</a> · '
        '<a href="termos/">Termos</a>.'
    )
    if "<!-- INJECT_LEGAL -->" in index:
        index = index.replace("<!-- INJECT_LEGAL -->", short_legal)
    if "favicon" not in index:
        index = index.replace(
            "</head>",
            '  <link rel="icon" href="img/icon.png" type="image/png" />\n</head>',
        )
    return index


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Gera site-publico/ para a UOL")
    parser.add_argument(
        "--modo",
        choices=("construcao", "completo", "testadores"),
        default="testadores",
        help="testadores = 2 botões Android+iPhone (padrão); construcao = em breve; completo = planos Stripe",
    )
    args = parser.parse_args()
    modo = args.modo

    clean_output_dir(OUT)

    if modo == "testadores":
        shutil.copy2(SRC_LANDING / "testadores.html", OUT / "index.html")
    elif modo == "construcao":
        shutil.copy2(SRC_LANDING / "construcao.html", OUT / "index.html")
        (OUT / "index-completo.html").write_text(build_full_index(), encoding="utf-8")
    else:
        (OUT / "index.html").write_text(build_full_index(), encoding="utf-8")

    if modo == "completo":
        shutil.copy2(SRC_LANDING / "brand.js", OUT / "brand.js")
        for extra in ("avatars-ui.js", "avatars-site.json"):
            src = SRC_LANDING / extra
            if src.is_file():
                shutil.copy2(src, OUT / extra)
    (OUT / "img").mkdir(parents=True, exist_ok=True)
    if modo == "testadores":
        # Landing testadores: só Luna + Leo + ícone (evita ZIP 8 MB na UOL)
        for name in ("avatar-f1.png", "avatar-m1.png"):
            src = SRC_LANDING / "img" / name
            if src.is_file():
                shutil.copy2(src, OUT / "img" / name)
    else:
        copy_tree_files(SRC_LANDING / "img", OUT / "img")
    assets_dir = ROOT / "app" / "assets"
    if not assets_dir.is_dir():
        sibling = ROOT.parent / "EGO-AI-APP" / "app" / "assets"
        if sibling.is_dir():
            assets_dir = sibling
    icon_candidates = [
        SRC_BRAND / "logo-site.png",
        SRC_BRAND / "logo-master.png",
        assets_dir / "icon.png" if assets_dir.is_dir() else None,
        ROOT / "app" / "assets" / "icon.png",
        ROOT.parent / "EGO-AI-APP" / "app" / "assets" / "icon.png",
    ]
    icon_src = next((p for p in icon_candidates if p and p.is_file()), None)
    if icon_src:
        shutil.copy2(icon_src, OUT / "img" / "icon.png")
    if modo != "testadores" and assets_dir.is_dir():
            for png in assets_dir.glob("avatar-*.png"):
                if "speaking" in png.name:
                    continue
                shutil.copy2(png, OUT / "img" / png.name)
    (OUT / "brand").mkdir(parents=True, exist_ok=True)
    cfg_src = SRC_BRAND / "config.json"
    if cfg_src.is_file():
        shutil.copy2(cfg_src, OUT / "brand" / "config.json")
    if modo == "completo":
        for extra in SRC_BRAND.glob("*"):
            if extra.is_file() and extra.name != "config.json":
                shutil.copy2(extra, OUT / "brand" / extra.name)

    if modo == "completo" and (OUT / "brand.js").is_file():
        brand_js = (OUT / "brand.js").read_text(encoding="utf-8")
        brand_js = brand_js.replace(
            'const CONFIG_PATH = "../brand/config.json";',
            'const CONFIG_PATH = "brand/config.json";',
        )
        (OUT / "brand.js").write_text(brand_js, encoding="utf-8")

    cfg_path = OUT / "brand" / "config.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    cfg.update(
        {
            "domain": "egoai.com.br",
            "siteUrl": "https://egoai.com.br",
            "supportEmail": "contato@egoai.com.br",
            "privacyUrl": "https://egoai.com.br/privacidade/",
            "termsUrl": "https://egoai.com.br/termos/",
            "accountDeletionUrl": "https://egoai.com.br/exclusao-conta/",
        }
    )
    cfg_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    (OUT / ".htaccess").write_text(
        """# UOL / Apache — site estático EGO-AI
DirectoryIndex index.html
Options -Indexes
<IfModule mod_rewrite.c>
  RewriteEngine On
  RewriteCond %{HTTPS} off
  RewriteRule ^ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]
</IfModule>
""",
        encoding="utf-8",
    )
    (OUT / "robots.txt").write_text(
        "User-agent: *\nAllow: /\nSitemap: https://egoai.com.br/\n",
        encoding="utf-8",
    )

    d = OUT / "contato"
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text(contato_page(), encoding="utf-8")

    d = OUT / "exclusao-conta"
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text(exclusao_conta_page(), encoding="utf-8")

    # Páginas legais completas (Play Store pode usar /privacidade/ mesmo em construção)
    for sub, content in (
        (
            "privacidade",
            legal_page("Política de Privacidade", md_to_html(privacy_policy_markdown())),
        ),
        (
            "termos",
            legal_page(
                "Termos de Uso",
                md_to_html(terms_of_use_markdown())
                + "<hr/><h2>Política de Reembolso</h2>"
                + md_to_html(refund_policy_markdown()),
            ),
        ),
    ):
        d = OUT / sub
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(content, encoding="utf-8")

    if modo == "testadores":
        print(f"OK {OUT} — modo TESTADORES (2 botões Android + iPhone)")
        print("  https://egoai.com.br - baixar gratis")
    elif modo == "construcao":
        print(f"OK {OUT} — modo EM CONSTRUÇÃO (index.html)")
        print("  Site completo guardado em index-completo.html (troque quando estiver pronto)")
        print("  /privacidade/, /termos/ e /exclusao-conta/ para a Play Store")
    else:
        print(f"OK {OUT} — modo COMPLETO (planos + Stripe)")
    print("  Envie TODO site-publico/ para public_html na UOL")


if __name__ == "__main__":
    main()
