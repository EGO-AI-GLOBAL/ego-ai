#!/usr/bin/env python3
"""Gera site-envio-UOL/ com pastas numeradas 01, 02, 03 + PREVIEW-COMPLETO para ver no PC."""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "site-publico"
OUT = ROOT / "site-envio-UOL"
PREVIEW = OUT / "PREVIEW-COMPLETO"

LEGAL_DIRS = ("privacidade", "termos", "exclusao-conta", "contato")
ROOT_FILES = (
    "index.html",
    "brand.js",
    "avatars-ui.js",
    "avatars-site.json",
    ".htaccess",
    "robots.txt",
)


def reset_output_dir(path: Path) -> None:
    """Remove pasta de saída (compatível com OneDrive / reparse points)."""
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        return
    if path.is_file():
        path.unlink(missing_ok=True)
    elif path.is_dir():
        for child in path.iterdir():
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
            else:
                try:
                    child.unlink(missing_ok=True)
                except OSError:
                    pass
        try:
            path.rmdir()
        except OSError:
            shutil.rmtree(path, ignore_errors=True)
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def copy_dir(src: Path, dst: Path) -> None:
    if not src.is_dir():
        return
    shutil.copytree(src, dst, dirs_exist_ok=True)


def main() -> None:
    if not (SRC / "index.html").is_file():
        raise SystemExit(
            "site-publico/index.html em falta. Corra:\n"
            "  python scripts/build_site_publico.py --modo completo"
        )

    reset_output_dir(OUT)

    p1 = OUT / "01-paginas-legais"
    p2 = OUT / "02-imagens-e-brand"
    p3 = OUT / "03-site-principal-raiz"

    for d in (p1, p2, p3, PREVIEW):
        d.mkdir(parents=True, exist_ok=True)

    # 1 — Legais (Play Console)
    for name in LEGAL_DIRS:
        copy_dir(SRC / name, p1 / name)
        copy_dir(SRC / name, PREVIEW / name)

    # 2 — Imagens + brand
    copy_dir(SRC / "img", p2 / "img")
    copy_dir(SRC / "img", PREVIEW / "img")
    if (SRC / "brand").is_dir():
        copy_dir(SRC / "brand", p2 / "brand")
        copy_dir(SRC / "brand", PREVIEW / "brand")

    # 3 — Raiz do site
    for name in ROOT_FILES:
        f = SRC / name
        if f.is_file():
            copy_file(f, p3 / name)
            copy_file(f, PREVIEW / name)

    # LEIA-ME + preview bat
    readme = OUT / "LEIA-ME-ORDEM-1-2-3.txt"
    readme.write_text(
        """EGO-AI — Envio UOL (ordem 1 → 2 → 3)
=====================================

Destino no servidor: public_html/

ANTES DE SUBIR: abra PREVIEW-LOCAL.bat e veja o site no PC.

ORDEM DE UPLOAD (não misture com site-publico na UOL de uma vez):

  PASSO 1 — pasta: 01-paginas-legais/
    Crie no public_html as pastas e envie o conteúdo:
      privacidade/index.html  → public_html/privacidade/
      termos/index.html       → public_html/termos/
      exclusao-conta/index.html → public_html/exclusao-conta/
      contato/index.html      → public_html/contato/

  PASSO 2 — pasta: 02-imagens-e-brand/
      img/*     → public_html/img/
      brand/*   → public_html/brand/

  PASSO 3 — pasta: 03-site-principal-raiz/
      index.html, brand.js, avatars-ui.js, avatars-site.json,
      .htaccess, robots.txt  → public_html/ (raiz)

TESTAR NO AR (depois do passo 3):
  https://egoai.com.br/
  https://egoai.com.br/privacidade/
  https://egoai.com.br/exclusao-conta/

PREVIEW no PC (pasta separada, não enviar):
  PREVIEW-COMPLETO/ = site montado como na UOL após os 3 passos.
""",
        encoding="utf-8",
    )

    bat = OUT / "PREVIEW-LOCAL.bat"
    bat.write_text(
        r"""@echo off
cd /d "%~dp0PREVIEW-COMPLETO"
echo Preview: http://127.0.0.1:8765/
echo Feche esta janela para parar o servidor.
start "" "http://127.0.0.1:8765/"
python -m http.server 8765
pause
""",
        encoding="utf-8",
    )

    print(f"OK {OUT}")
    print("  01-paginas-legais")
    print("  02-imagens-e-brand")
    print("  03-site-principal-raiz")
    print("  PREVIEW-COMPLETO + PREVIEW-LOCAL.bat")


if __name__ == "__main__":
    main()
