#!/usr/bin/env python3
"""
Converte export Vidnoz/HeyGen/D-ID em loop de fala (~8 s) para o app.

Coloque o MP4 bruto em:
  app/assets/incoming/{id}-speaking-original.mp4
  ex.: f1-speaking-original.mp4, m1-speaking-original.mp4

Frase sugerida (~8 s, boca sempre em movimento, terminar ainda "falando"):
  «Oi, estou aqui com você — pode falar comigo quando quiser, estou te ouvindo.»

Gravação:
  - 9:16 vertical (1080×1920 ou 720×1280) — único formato
  - 4 a 8 segundos (usa o vídeo inteiro se for ≤8 s)
  - SEM legenda, SEM logo, SEM áudio no export final
  - Rosto/ombros centrados; boca sempre em movimento no loop

Uso:
  python scripts/make_avatar_speaking_loop.py --id f1
  python scripts/make_avatar_speaking_loop.py --id f1 --skip-still-sync
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "app" / "assets"
INCOMING = ASSETS / "incoming"

# id → ficheiro final no bundle
AVATAR_OUTPUT = {
    "f1": "avatar-f1-speaking.mp4",
    "m1": "avatar-m1-speaking.mp4",
    "f2": "avatar-f2-speaking.mp4",
    "f3": "avatar-f3-speaking.mp4",
    "f4": "avatar-f4-speaking.mp4",
    "f5": "avatar-f5-speaking.mp4",
    "m2": "avatar-m2-speaking.mp4",
    "m3": "avatar-m3-speaking.mp4",
    "m4": "avatar-m4-speaking.mp4",
    "m5": "avatar-m5-speaking.mp4",
    "g1": "avatar-g1-speaking.mp4",
    "g2": "avatar-g2-speaking.mp4",
}

DEFAULT_PHRASE = (
    "Oi, estou aqui com você — pode falar comigo quando quiser, estou te ouvindo."
)

# Saída 9:16 para o frame vertical do chat (COVER no app)
OUT_W = 720
OUT_H = 1280
MIN_CLIP = 4.0
MAX_CLIP = 8.0
# Enquadramento: ligeiro bias para cima (rosto/ombros, corta um pouco em baixo)
FACE_CROP_Y_BIAS = 0.10


def _clip_duration(total: float, requested: float | None) -> float:
    """Usa o vídeo inteiro se ≤8 s; senão corta até 8 s (mín. 4 s quando possível)."""
    if total <= MAX_CLIP:
        return total
    want = requested if requested and requested > 0 else MAX_CLIP
    return max(MIN_CLIP, min(want, MAX_CLIP))


def _video_filter(crop_bottom: int) -> str:
    """9:16 — escala, centra horizontal, enquadra rosto (bias vertical)."""
    bottom = max(0, int(crop_bottom))
    h_crop = max(640, OUT_H - bottom)
    # scale up to cover 720×h_crop, center X, bias Y up for talking head
    return (
        f"scale={OUT_W}:{h_crop}:force_original_aspect_ratio=increase,"
        f"crop={OUT_W}:{h_crop}:(iw-{OUT_W})/2:(ih-{h_crop})*{FACE_CROP_Y_BIAS},"
        f"scale={OUT_W}:{OUT_H}:flags=lanczos,fps=30"
    )


def _ffmpeg_ok() -> bool:
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def _probe_duration(path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    out = subprocess.check_output(cmd, text=True).strip()
    return float(out)


def process_one(
    avatar_id: str,
    *,
    duration: float,
    start: float | None,
    crop_bottom: int,
    crossfade_ms: int,
) -> bool:
    aid = avatar_id.lower()
    out_name = AVATAR_OUTPUT.get(aid)
    if not out_name:
        print(f"  [{aid}] ID desconhecido — use: {', '.join(sorted(AVATAR_OUTPUT))}")
        return False

    src = INCOMING / f"{aid}-speaking-original.mp4"
    if not src.is_file():
        alt = INCOMING / f"avatar-{aid}-speaking-original.mp4"
        src = alt if alt.is_file() else src
    if not src.is_file():
        print(f"  [{aid}] Falta: {INCOMING / (aid + '-speaking-original.mp4')}")
        return False

    total = _probe_duration(src)
    clip = _clip_duration(total, duration if duration > 0 else None)
    if start is None:
        start = max(0.0, (total - clip) / 2.0) if total > clip else 0.0
    start = max(0.0, min(start, max(0.0, total - clip - 0.05)))

    dest = ASSETS / out_name
    tmp = ASSETS / f"_loop_{aid}.mp4"

    vf = _video_filter(crop_bottom)

    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{start:.3f}",
        "-i",
        str(src),
        "-t",
        f"{clip:.3f}",
        "-vf",
        vf,
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(tmp),
    ]
    print(f"  [{aid}] {src.name} -> {out_name} | {clip}s desde {start:.2f}s (fonte {total:.1f}s)")
    subprocess.run(cmd, check=True)

    if crossfade_ms > 0:
        # Segundo passo: funde final com início (loop seamless)
        ms = crossfade_ms / 1000.0
        loop_tmp = ASSETS / f"_loop_xfade_{aid}.mp4"
        xfade = [
            "ffmpeg",
            "-y",
            "-i",
            str(tmp),
            "-i",
            str(tmp),
            "-filter_complex",
            (
                f"[0:v]trim=0:{clip - ms:.3f},setpts=PTS-STARTPTS[head];"
                f"[1:v]trim=0:{ms:.3f},setpts=PTS-STARTPTS[tail];"
                f"[head][tail]xfade=transition=fade:duration={ms:.3f}:offset={clip - 2 * ms:.3f},format=yuv420p[v]"
            ),
            "-map",
            "[v]",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-movflags",
            "+faststart",
            str(loop_tmp),
        ]
        try:
            subprocess.run(xfade, check=True)
            loop_tmp.replace(tmp)
            print(f"  [{aid}] crossfade loop {crossfade_ms}ms aplicado")
        except subprocess.CalledProcessError:
            print(f"  [{aid}] crossfade falhou — usando corte seco")

    tmp.replace(dest)
    print(f"  [{aid}] OK → {dest}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera MP4 loop de fala para avatares EGO-AI")
    parser.add_argument("--id", help="Só este avatar (ex.: f1, m1)")
    parser.add_argument("--duration", type=float, default=0, help="Max segundos do loop (0=auto 4-8)")
    parser.add_argument("--start", type=float, default=None, help="Segundo inicial no vídeo fonte")
    parser.add_argument(
        "--crop-bottom",
        type=int,
        default=0,
        help="Pixels a cortar em baixo (legendas/logo Vidnoz)",
    )
    parser.add_argument(
        "--crossfade-ms",
        type=int,
        default=200,
        help="Dissolve fim→início para loop (0 = desligado)",
    )
    parser.add_argument(
        "--skip-still-sync",
        action="store_true",
        help="Nao sobrescrever avatar-*.png (use em testes com video curto)",
    )
    args = parser.parse_args()

    if not _ffmpeg_ok():
        print("Instale ffmpeg: winget install ffmpeg")
        return 1

    INCOMING.mkdir(parents=True, exist_ok=True)

    print("Frase recomendada (~8 s):")
    print(f"  «{DEFAULT_PHRASE}»")
    print()

    ids = [args.id.lower()] if args.id else sorted(AVATAR_OUTPUT)
    ok = 0
    for aid in ids:
        if process_one(
            aid,
            duration=args.duration,
            start=args.start,
            crop_bottom=args.crop_bottom,
            crossfade_ms=args.crossfade_ms,
        ):
            ok += 1

    if ok == 0:
        print("\nNenhum vídeo processado. Coloque MP4 em app/assets/incoming/")
        print("Ex.: app/assets/incoming/f1-speaking-original.mp4")
        return 1

    sync = ROOT / "scripts" / "sync_avatar_still_frames.py"
    if sync.is_file() and not args.skip_still_sync:
        print("\nAtualizando PNG still dos avatares...")
        subprocess.run([sys.executable, str(sync)], check=True)

    print(f"\n{ok} vídeo(s) prontos. Próximo: build 1.0.24 ou teste Expo (npx expo start -c)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
