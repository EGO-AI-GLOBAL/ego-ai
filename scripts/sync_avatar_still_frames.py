#!/usr/bin/bin/env python3
"""Gera avatar-*-still.png a partir do frame do vídeo falando (mesmo rosto)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "app" / "assets"
LANDING_IMG = ROOT / "marketing" / "landing" / "img"

PAIRS = [
    ("avatar-f1-speaking.mp4", "avatar-f1.png", 0.45),
    ("avatar-m1-speaking.mp4", "avatar-m1.png", 0.8),
    ("avatar-f2-speaking.mp4", "avatar-f2.png", 0.35),
    ("avatar-f3-speaking.mp4", "avatar-f3.png", 0.4),
    ("avatar-m2-speaking.mp4", "avatar-m2.png", 0.45),
    ("avatar-m3-speaking.mp4", "avatar-m3.png", 0.5),
    ("avatar-f4-speaking.mp4", "avatar-f4.png", 0.5),
    ("avatar-m4-speaking.mp4", "avatar-m4.png", 0.5),
    ("avatar-g1-speaking.mp4", "avatar-g1.png", 0.5),
    ("avatar-f5-speaking.mp4", "avatar-f5.png", 0.5),
    ("avatar-m5-speaking.mp4", "avatar-m5.png", 0.5),
    ("avatar-g2-speaking.mp4", "avatar-g2.png", 0.5),
]


def _extract(video: Path, png: Path, at_sec: float = 0.5) -> None:
    tmp = png.with_suffix(".tmp.png")
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video),
        "-ss",
        str(at_sec),
        "-frames:v",
        "1",
        "-update",
        "1",
        str(tmp),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    tmp.replace(png)


def main() -> int:
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("Instale ffmpeg (winget install ffmpeg)")
        return 1

    LANDING_IMG.mkdir(parents=True, exist_ok=True)

    for video_name, png_name, at_sec in PAIRS:
        video = ASSETS / video_name
        png = ASSETS / png_name
        if not video.is_file():
            print(f"Pulando (sem video): {video}")
            continue
        print(f"{video_name} -> {png_name} @ {at_sec}s")
        _extract(video, png, at_sec=at_sec)
        shutil_copy = LANDING_IMG / png_name
        shutil_copy.write_bytes(png.read_bytes())
        print(f"  OK {png.stat().st_size // 1024} KB")

    print("Pronto. Reinicie o Expo: npx expo start -c")
    return 0


if __name__ == "__main__":
    sys.exit(main())
