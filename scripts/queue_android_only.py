#!/usr/bin/env python3
"""Enfileira só Android e atualiza builds-VERSION.ids.json (mantém iOS id)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from wait_and_submit_eas import (  # noqa: E402
    app_version,
    ids_file_for_version,
    load_ids,
    queue_build,
    save_ids,
    sync_check,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids-file", help="Ficheiro de IDs (default: builds-VERSION.ids.json)")
    parser.add_argument("--skip-sync", action="store_true")
    args = parser.parse_args()

    if not args.skip_sync:
        sync_check()

    version = app_version()
    path = Path(args.ids_file) if args.ids_file else ids_file_for_version(version)
    ios_id = load_ids_android_queue(path) if path.is_file() else ""
    android_id = queue_build("android")
    save_ids(path, ios_id, android_id, version=version)
    print(f"Android {android_id} — iOS {'mantido ' + ios_id if ios_id else 'sem build (aguardar loja)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
