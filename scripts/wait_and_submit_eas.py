#!/usr/bin/env python3
"""EAS: enfileirar iOS+Android juntos, esperar ambos, submeter uma vez só."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
APP_CONFIG = APP / "app.config.ts"
BUILD_ID_RE = re.compile(
    r"expo\.dev/accounts/[^/]+/projects/[^/]+/builds/([0-9a-f-]{36})", re.I
)
VERSION_RE = re.compile(r'version:\s*"([^"]+)"')


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("EAS_BUILD_NO_EXPO_GO_WARNING", "true")
    env.setdefault("NODE_TLS_REJECT_UNAUTHORIZED", "0")
    return env


def _eas_cmd() -> list[str]:
    for name in ("eas", "eas.cmd", "eas.bat"):
        found = shutil.which(name)
        if found:
            return [found]
    return ["eas"]


def _run(cmd: list[str], *, cwd: Path = APP) -> subprocess.CompletedProcess[str]:
    if cmd and cmd[0] == "eas":
        cmd = _eas_cmd() + cmd[1:]
    env = _env()
    npm_bin = os.path.join(os.environ.get("APPDATA", ""), "npm")
    if npm_bin and npm_bin not in env.get("PATH", ""):
        env["PATH"] = npm_bin + os.pathsep + env.get("PATH", "")
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )


def app_version() -> str:
    text = APP_CONFIG.read_text(encoding="utf-8")
    match = VERSION_RE.search(text)
    if not match:
        raise SystemExit("Não achei version em app/app.config.ts")
    return match.group(1).strip()


def ids_file_for_version(version: str | None = None) -> Path:
    ver = (version or app_version()).strip()
    return ROOT / f"builds-{ver}.ids.json"


def build_status(build_id: str) -> str:
    proc = _run(["eas", "build:view", build_id, "--json"])
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "eas build:view falhou")
    data = json.loads(proc.stdout)
    return str(data.get("status") or "UNKNOWN").upper()


def wait_both(
    ios_id: str, android_id: str, poll_sec: int = 60, *, ios_only: bool = False
) -> None:
    print(f"Aguardando iOS {ios_id} + Android {android_id}...")
    while True:
        ios = build_status(ios_id)
        android = build_status(android_id)
        print(f"  iOS={ios}  Android={android}")
        if ios == "FINISHED" and (android == "FINISHED" or (ios_only and android == "ERRORED")):
            if ios_only and android == "ERRORED":
                print("iOS FINISHED; Android ERRORED — segue só TestFlight.")
            else:
                print("Ambos FINISHED.")
            return
        if ios in {"ERRORED", "CANCELED"}:
            raise SystemExit(f"Build falhou: iOS={ios} Android={android}")
        if not ios_only and android in {"ERRORED", "CANCELED"}:
            raise SystemExit(f"Build falhou: iOS={ios} Android={android}")
        time.sleep(poll_sec)


def _safe_print(text: str) -> None:
    out = text or ""
    try:
        print(out)
    except UnicodeEncodeError:
        enc = getattr(sys.stdout, "encoding", None) or "utf-8"
        print(out.encode(enc, errors="replace").decode(enc, errors="replace"))


def submit_pair(ios_id: str, android_id: str) -> None:
    print("Submetendo iOS (TestFlight)...")
    proc_ios = _run(
        ["eas", "submit", "--platform", "ios", "--id", ios_id, "--non-interactive"]
    )
    if proc_ios.returncode != 0:
        _safe_print(proc_ios.stdout or "")
        print(proc_ios.stderr, file=sys.stderr)
        raise SystemExit(proc_ios.returncode)
    _safe_print(proc_ios.stdout or "")

    print("Submetendo Android (Play)...")
    proc_and = _run(
        ["eas", "submit", "--platform", "android", "--id", android_id, "--non-interactive"]
    )
    if proc_and.returncode != 0:
        _safe_print(proc_and.stdout or "")
        print(proc_and.stderr, file=sys.stderr)
        raise SystemExit(proc_and.returncode)
    _safe_print(proc_and.stdout or "")
    print("Submit iOS + Android concluído (uma vez só).")


def queue_build(platform: str) -> str:
    print(f"Enfileirando build {platform}...")
    proc = _run(
        [
            "eas",
            "build",
            "--platform",
            platform,
            "--profile",
            "production",
            "--non-interactive",
            "--no-wait",
        ]
    )
    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    if proc.returncode != 0:
        _safe_print(out)
        raise SystemExit(proc.returncode)
    match = BUILD_ID_RE.search(out)
    if not match:
        _safe_print(out)
        raise SystemExit(f"Não achei build id no output {platform}")
    build_id = match.group(1)
    print(f"  {platform} -> {build_id}")
    return build_id


def save_ids(path: Path, ios_id: str, android_id: str, *, version: str) -> None:
    payload = {
        "version": version,
        "ios": ios_id,
        "android": android_id,
        "queued_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"IDs gravados em {path}")


def load_ids(path: Path) -> tuple[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    ios = str(data.get("ios") or "").strip()
    android = str(data.get("android") or "").strip()
    if not ios or not android:
        raise SystemExit(f"IDs inválidos em {path}")
    return ios, android


def load_ids_android_queue(path: Path) -> str:
    """iOS opcional (vazio = sem build iOS nesta release)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return str(data.get("ios") or "").strip()


def wait_android(android_id: str, poll_sec: int = 60) -> None:
    print(f"Aguardando Android {android_id}...")
    while True:
        android = build_status(android_id)
        print(f"  Android={android}")
        if android == "FINISHED":
            return
        if android in {"ERRORED", "CANCELED"}:
            raise SystemExit(f"Build Android falhou: {android}")
        time.sleep(poll_sec)


def submit_android(android_id: str) -> None:
    print("Submetendo Android (Play)...")
    proc_and = _run(
        ["eas", "submit", "--platform", "android", "--id", android_id, "--non-interactive"]
    )
    if proc_and.returncode != 0:
        _safe_print(proc_and.stdout or "")
        print(proc_and.stderr, file=sys.stderr)
        raise SystemExit(proc_and.returncode)
    _safe_print(proc_and.stdout or "")
    print("Submit Android concluído.")


def sync_check() -> None:
    """Garante que todos os agentes já fundiram no main antes de build."""
    print("=== Sync check (todos os agentes) ===")
    fetch = subprocess.run(
        ["git", "fetch", "origin"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if fetch.returncode != 0:
        print("AVISO: git fetch falhou — confirme rede/login")
    else:
        behind = subprocess.run(
            ["git", "rev-list", "--count", "HEAD..origin/main"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        n_behind = int((behind.stdout or "0").strip() or "0")
        if n_behind > 0:
            raise SystemExit(
                f"main local está {n_behind} commit(s) atrás de origin/main. "
                "Espere o outro agente e rode: git pull origin main"
            )
        ahead = subprocess.run(
            ["git", "rev-list", "--count", "origin/main..HEAD"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        n_ahead = int((ahead.stdout or "0").strip() or "0")
        if n_ahead > 0:
            raise SystemExit(
                f"main tem {n_ahead} commit(s) nao enviados. "
                "Rode: python scripts/release_auto.py (faz push) ou git push origin main"
            )

    dirty = subprocess.run(
        ["git", "status", "--porcelain", "app/", "ego_api/", "flask_api.py", "scripts/"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    lines = [
        ln
        for ln in (dirty.stdout or "").splitlines()
        if ln.strip() and not ln.startswith("??")
    ]
    if lines:
        print("AVISO: alterações locais não commitadas em app/API:")
        for ln in lines[:12]:
            print(f"  {ln}")
        if len(lines) > 12:
            print(f"  ... +{len(lines) - 12} ficheiros")
        raise SystemExit("Commit + push de TODOS os agentes antes de GERAR builds.")
    print("OK — main alinhado, sem diff local em app/API.")


def main() -> int:
    parser = argparse.ArgumentParser(description="EAS: esperar par iOS+Android e submeter uma vez")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sc = sub.add_parser("sync-check", help="Verifica git antes de build (dois agentes)")

    q = sub.add_parser("queue", help="Enfileira iOS + Android (--no-wait) e grava IDs")
    q.add_argument("--ids-file", help="Onde gravar os build IDs (default: builds-VERSION.ids.json)")
    q.add_argument("--skip-sync", action="store_true", help="Não rodar sync-check")

    w = sub.add_parser("wait-submit", help="Espera ambos FINISHED e submete uma vez")
    w.add_argument("--ios", help="Build ID iOS")
    w.add_argument("--android", help="Build ID Android")
    w.add_argument("--ids-file", help="Ficheiro com ios/android ids")
    w.add_argument("--poll", type=int, default=60)
    w.add_argument(
        "--ios-only",
        action="store_true",
        help="Espera ambos builds mas submete só iOS (TestFlight)",
    )
    w.add_argument(
        "--android-only",
        action="store_true",
        help="Espera e submete só Android (Play) — iOS fica para depois",
    )

    qa = sub.add_parser("queue-android", help="Enfileira só Android e grava IDs")
    qa.add_argument("--ids-file", help="Onde gravar os build IDs (default: builds-VERSION.ids.json)")
    qa.add_argument("--skip-sync", action="store_true", help="Não rodar sync-check")

    args = parser.parse_args()

    if args.cmd == "sync-check":
        sync_check()
        return 0

    version = app_version()
    ids_path = Path(args.ids_file) if getattr(args, "ids_file", None) else ids_file_for_version(version)

    if args.cmd == "queue":
        if not args.skip_sync:
            sync_check()
        ios_id = queue_build("ios")
        android_id = queue_build("android")
        save_ids(ids_path, ios_id, android_id, version=version)
        print()
        print(f"Versão {version} — builds enfileirados.")
        print("Próximo passo (UMA vez, os dois):")
        print("  AGUARDAR-E-SUBMETER.bat")
        print(f"  ou: python scripts/wait_and_submit_eas.py wait-submit --ids-file {ids_path}")
        return 0

    if args.cmd == "queue-android":
        if not args.skip_sync:
            sync_check()
        ios_id = ""
        if ids_path.is_file():
            ios_id = load_ids_android_queue(ids_path)
        android_id = queue_build("android")
        save_ids(ids_path, ios_id, android_id, version=version)
        print()
        print(f"Versão {version} — só Android enfileirado.")
        print("Próximo passo:")
        print(f"  AGUARDAR-ANDROID-{version}.bat")
        print(f"  ou: python scripts/wait_and_submit_eas.py wait-submit --android-only --ids-file {ids_path}")
        return 0

    ios_id = args.ios
    android_id = args.android
    if getattr(args, "android_only", False):
        if not android_id:
            if not ids_path.is_file():
                raise SystemExit(f"Ficheiro não existe: {ids_path}")
            data = json.loads(ids_path.read_text(encoding="utf-8"))
            android_id = str(data.get("android") or "").strip()
        if not android_id:
            raise SystemExit("Android build ID em falta — rode GERAR-ANDROID primeiro")
        wait_android(android_id, poll_sec=args.poll)
        submit_android(android_id)
        return 0

    if not ios_id or not android_id:
        if not ids_path.is_file():
            raise SystemExit(f"Ficheiro não existe: {ids_path} — rode GERAR-E-SUBMETER-JUNTO.bat primeiro")
        ios_id, android_id = load_ids(ids_path)

    wait_both(ios_id, android_id, poll_sec=args.poll, ios_only=getattr(args, "ios_only", False))
    if getattr(args, "ios_only", False):
        print("Submetendo só iOS (TestFlight) — Android fica para depois do teste no iPhone.")
        proc_ios = _run(
            ["eas", "submit", "--platform", "ios", "--id", ios_id, "--non-interactive"]
        )
        if proc_ios.returncode != 0:
            _safe_print(proc_ios.stdout or "")
            print(proc_ios.stderr, file=sys.stderr)
            raise SystemExit(proc_ios.returncode)
        _safe_print(proc_ios.stdout or "")
        print("Submit iOS concluído. Android: rode submit manual quando iPhone OK.")
        return 0
    submit_pair(ios_id, android_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
