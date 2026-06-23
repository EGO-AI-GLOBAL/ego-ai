#!/usr/bin/env python3
"""
Remove legenda e marca Vidnoz do vídeo do Leo.

Sempre processa a partir de incoming/leo-speaking-vidnoz-original.mp4
(exporte do Vidnoz SEM legenda se possível).

Uso: python scripts/clean_leo_avatar_video.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / "app" / "assets" / "avatar-m1-speaking.mp4"
SOURCE = ROOT / "app" / "assets" / "incoming" / "leo-speaking-vidnoz-original.mp4"
TMP = ROOT / "app" / "assets" / "_avatar-m1-speaking-clean.mp4"

# Corte generoso: legendas + logo Vidnoz na base
CROP_BOTTOM_PX = 175


def main() -> int:
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("Instale ffmpeg: winget install ffmpeg")
        return 1

    src = SOURCE if SOURCE.is_file() else VIDEO
    if not src.is_file():
        print(f"Coloque o MP4 em: {SOURCE}")
        return 1

    h_out = 720 - CROP_BOTTOM_PX
    # Primeiro tira logo Vidnoz (canto inferior esq.), depois corta legendas
    vf = (
        "delogo=x=4:y=600:w=200:h=115,"
        f"crop=720:{h_out}:0:0,"
        "scale=720:720:flags=lanczos"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(src),
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "19",
        "-an",
        "-movflags",
        "+faststart",
        str(TMP),
    ]
    print(f"Fonte: {src.name} | cortando {CROP_BOTTOM_PX}px da base...")
    subprocess.run(cmd, check=True)
    TMP.replace(VIDEO)
    print(f"OK: {VIDEO}")

    for script in ("sync_avatar_still_frames.py",):
        p = ROOT / "scripts" / script
        if p.is_file():
            subprocess.run([sys.executable, str(p)], check=True)

    mkt = ROOT / "scripts" / "generate_marketing_videos.py"
    if mkt.is_file():
        subprocess.run([sys.executable, str(mkt), "--persona=leo"], check=True)

    print("\nNo telefone: cd app && npx expo start -c")
    print("Se ainda vir marca, exporte de novo no Vidnoz sem legenda/watermark.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
