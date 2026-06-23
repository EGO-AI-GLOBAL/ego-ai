#!/usr/bin/env python3
"""Adiciona faixa AAC silenciosa aos MP4 (formato que o Android ExoPlayer aceita melhor)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "app" / "assets"
IDS = ("f1", "m1", "f2", "f3", "f4", "f5", "m2", "m3", "m4", "m5", "g1", "g2")


def main() -> int:
    for aid in IDS:
        src = ASSETS / f"avatar-{aid}-speaking.mp4"
        if not src.is_file():
            print(f"  SKIP {src.name} (em falta)")
            continue
        tmp = ASSETS / f"_android_fix_{aid}.mp4"
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(src),
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=mono:sample_rate=44100",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "48k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(tmp),
        ]
        print(f"  [{aid}] {src.name} …")
        subprocess.run(cmd, check=True)
        tmp.replace(src)
        print(f"  [{aid}] OK")
    print("\n12 vídeos prontos para build Android.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
