#!/usr/bin/env python3
"""Gera site-publico.zip para upload rápido na UOL."""

from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site-publico"
ZIP_PATH = ROOT / "site-uol.zip"


def main() -> None:
    build = ROOT / "scripts" / "build_site_publico.py"
    subprocess.run([sys.executable, str(build), "--modo", "testadores"], check=True)
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(SITE.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(SITE).as_posix())
    print(f"OK {ZIP_PATH} ({ZIP_PATH.stat().st_size // 1024} KB) — 1 arquivo para a UOL")


if __name__ == "__main__":
    main()
