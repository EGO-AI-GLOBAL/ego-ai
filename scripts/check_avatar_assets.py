#!/usr/bin/env python3
"""Lista avatares fase 1 e ficheiros em falta em app/assets/."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "app" / "assets"

CATALOG = [
    ("f1", "Luna", "Grátis"),
    ("m1", "Leo", "Grátis"),
    ("f2", "Aisha", "Conexão"),
    ("f3", "Hana", "Conexão"),
    ("m2", "Kai", "Conexão"),
    ("m3", "Omar", "Conexão"),
    ("f4", "Amara", "Premium"),
    ("m4", "Ravi", "Premium"),
    ("g1", "Alex", "Premium"),
    ("f5", "Sara", "Total"),
    ("m5", "Malik", "Total"),
    ("g2", "Jordan", "Total"),
]


def is_png(path: Path) -> bool:
    if not path.is_file():
        return False
    return path.read_bytes()[:4] == b"\x89PNG"


def main() -> int:
    missing_png: list[str] = []
    missing_mp4: list[str] = []
    bad_png: list[str] = []
    ok = 0
    backup = ROOT / "app_local_backup" / "assets"
    repair = "--repair" in sys.argv

    print("EGO-AI — avatares fase 1\n")
    print(f"{'ID':<4} {'Nome':<8} {'Plano':<10} {'PNG':<8} {'MP4'}")
    print("-" * 44)

    for aid, name, plan in CATALOG:
        png = ASSETS / f"avatar-{aid}.png"
        mp4 = ASSETS / f"avatar-{aid}-speaking.mp4"
        bak_png = backup / png.name
        bak_mp4 = backup / mp4.name
        if repair and not is_png(png) and is_png(bak_png):
            png.write_bytes(bak_png.read_bytes())
        if repair and not mp4.is_file() and bak_mp4.is_file():
            mp4.write_bytes(bak_mp4.read_bytes())
        has_png = is_png(png)
        has_mp4 = mp4.is_file()
        if has_png and has_mp4:
            ok += 1
        if not has_png:
            if png.is_file():
                bad_png.append(aid)
            else:
                missing_png.append(aid)
        if not has_mp4:
            missing_mp4.append(aid)
        png_st = "OK" if has_png else ("JPEG?" if png.is_file() else "FALTA")
        print(
            f"{aid:<4} {name:<8} {plan:<10} "
            f"{png_st:<8} {'OK' if has_mp4 else 'FALTA'}"
        )

    print(f"\nCompletos: {ok}/12")
    if bad_png:
        print(f"PNG invalido (use PNG real, nao JPEG): {', '.join(bad_png)}")
    if missing_png:
        print(f"PNG em falta: {', '.join(missing_png)}")
    if missing_mp4:
        print(f"MP4 em falta: {', '.join(missing_mp4)}")
    print("\nGuia: app/assets/AVATARES_FASE1.md")
    return 0 if ok == 12 and not bad_png else 1


if __name__ == "__main__":
    sys.exit(main())
