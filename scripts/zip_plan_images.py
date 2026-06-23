"""Empacota todas as fotos de planos num ZIP na raiz do projeto."""

from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "assets" / "store" / "plans"
SRC_TEAM = ROOT / "assets" / "store" / "plans-team"
OUT = ROOT / "EGO-AI-fotos-planos.zip"
OUT_TEAM = ROOT / "EGO-AI-fotos-planos-equipe.zip"


def _zip_folder(src: Path, out_zip: Path, label: str) -> int:
    if not src.exists():
        print(f"Aviso: {label} — pasta não encontrada: {src}")
        return 0
    pngs = sorted(src.rglob("*.png"))
    if not pngs:
        print(f"Aviso: {label} — nenhum PNG em {src}")
        return 0
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in pngs:
            arc = path.relative_to(src).as_posix()
            zf.write(path, arc)
    print(f"ZIP {label}: {out_zip} ({len(pngs)} ficheiros)")
    return len(pngs)


def main() -> None:
    n1 = _zip_folder(SRC, OUT, "particulares")
    n2 = _zip_folder(SRC_TEAM, OUT_TEAM, "equipes")
    if n1 + n2 == 0:
        raise SystemExit(
            "Nenhuma imagem. Rode:\n"
            "  python scripts/generate_plan_product_images.py\n"
            "  python scripts/generate_plan_product_images.py --team"
        )


if __name__ == "__main__":
    main()
