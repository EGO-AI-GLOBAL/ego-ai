#!/usr/bin/env python3
"""
Checklist automatizado: API Railway + Supabase + assets + preflight Expo.
Uso: python scripts/checklist_launch.py [--repair] [--skip-bundle]
"""
from __future__ import annotations

import json
import os
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

if os.getenv("NODE_TLS_REJECT_UNAUTHORIZED", "").strip() == "0":
    ssl._create_default_https_context = ssl._create_unverified_context  # noqa: SLF001

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
BACKUP_ASSETS = ROOT / "app_local_backup" / "assets"
APP_ASSETS = APP / "assets"

API_BASE = "https://ego-ai-production-a2c2.up.railway.app/api/v1"

AVATAR_IDS = ("f1", "m1", "f2", "f3", "f4", "f5", "m2", "m3", "m4", "m5", "g1", "g2")

REPAIR = "--repair" in sys.argv
SKIP_BUNDLE = "--skip-bundle" in sys.argv

errors = 0
warnings = 0


def ok(msg: str) -> None:
    print(f"  OK  {msg}")


def warn(msg: str) -> None:
    global warnings
    warnings += 1
    print(f"  AVISO  {msg}")


def fail(msg: str) -> None:
    global errors
    errors += 1
    print(f"  ERRO  {msg}")


def load_env_files() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    for p in (ROOT / ".env", APP / ".env"):
        if p.is_file():
            load_dotenv(p, override=False)


def api_get(path: str) -> tuple[int, dict]:
    req = urllib.request.Request(f"{API_BASE}{path}", method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode() if e.fp else "{}"
        try:
            body = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            body = {"raw": raw[:200]}
        return e.code, body
    except Exception as exc:
        return 0, {"error": str(exc)}


def check_api_powershell() -> bool:
    """Fallback quando Python SSL falha no Windows do utilizador."""
    ps = (
        f"$h=Invoke-RestMethod -Uri '{API_BASE}/health' -TimeoutSec 25; "
        f"if(-not $h.ok){{exit 1}}; "
        f"$p=Invoke-RestMethod -Uri '{API_BASE}/plans' -TimeoutSec 25; "
        f"if(-not $p.launch_offer){{exit 2}}; exit 0"
    )
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    return r.returncode == 0


def check_api() -> None:
    print("\n[API] Railway producao")
    code, health = api_get("/health")
    if code == 0 and health.get("error"):
        if "CERTIFICATE_VERIFY_FAILED" in str(health.get("error", "")):
            if check_api_powershell():
                ok("health + R$ 9,90 (via PowerShell)")
                return
            fail("API inacessivel (SSL)")
            return
    if code != 200 or health.get("ok") is not True:
        fail(f"GET /health -> {code} {health}")
        return
    ok(f"health OK (build {health.get('api_build', '?')})")
    if not health.get("service_role_set"):
        warn("SUPABASE_SERVICE_ROLE_KEY ausente no Railway — agenda/convites podem falhar")

    code, plans = api_get("/plans")
    if code != 200:
        fail(f"GET /plans -> {code}")
        return
    if plans.get("launch_offer"):
        ok("oferta R$ 9,90 (launch_offer) na API")
    else:
        fail("falta STRIPE_CHECKOUT_LAUNCH_URL no Railway (sem launch_offer)")


def is_png(path: Path) -> bool:
    if not path.is_file():
        return False
    head = path.read_bytes()[:4]
    return head == b"\x89PNG"


def repair_and_check_avatars() -> None:
    print("\n[APP] Avatares em app/assets")
    if not BACKUP_ASSETS.is_dir():
        warn("app_local_backup/assets ausente — reparo limitado")

    for aid in AVATAR_IDS:
        png = APP_ASSETS / f"avatar-{aid}.png"
        mp4 = APP_ASSETS / f"avatar-{aid}-speaking.mp4"
        bak_png = BACKUP_ASSETS / png.name
        bak_mp4 = BACKUP_ASSETS / mp4.name

        if not is_png(png) and REPAIR and is_png(bak_png):
            APP_ASSETS.mkdir(parents=True, exist_ok=True)
            png.write_bytes(bak_png.read_bytes())
            ok(f"reparado PNG real: {png.name}")

        if not png.is_file():
            fail(f"em falta: {png.name}")
        elif not is_png(png):
            fail(f"{png.name} nao e PNG (JPEG renomeado quebra Gradle)")
        else:
            ok(png.name)

        if not mp4.is_file():
            if REPAIR and bak_mp4.is_file():
                mp4.write_bytes(bak_mp4.read_bytes())
                ok(f"copiado {mp4.name}")
            else:
                fail(f"em falta: {mp4.name}")
        else:
            ok(mp4.name)

    for base in ("icon.png", "splash-icon.png", "adaptive-icon.png"):
        p = APP_ASSETS / base
        if not p.is_file():
            fail(f"em falta: {base}")
        else:
            ok(base)


def check_node_modules() -> None:
    print("\n[APP] Dependencias")
    er = APP / "node_modules" / "expo-router" / "package.json"
    if er.is_file():
        ok("node_modules / expo-router")
    else:
        fail("node_modules incompleto — rode RESTAURAR-NODE-MODULES.bat")


def run_preflight() -> None:
    print("\n[APP] Preflight Expo (bundle JS)")
    script = APP / "scripts" / "preflight-build.mjs"
    if not script.is_file():
        fail("app/scripts/preflight-build.mjs ausente")
        return
    args = ["node", str(script)]
    if SKIP_BUNDLE:
        args.append("--skip-bundle")
    env = os.environ.copy()
    env.setdefault("NODE_TLS_REJECT_UNAUTHORIZED", "0")
    r = subprocess.run(args, cwd=str(APP), env=env)
    if r.returncode != 0:
        fail("preflight-build.mjs falhou")


def check_supabase() -> None:
    print("\n[SUPABASE] Schema e telefone")
    load_env_files()
    url = (os.getenv("SUPABASE_URL") or "").strip()
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_PUBLISHABLE_KEY")
        or ""
    ).strip()
    if not url or not key:
        warn("SUPABASE_URL/KEY nao no .env — pulando (execute SQL manualmente)")
        print("       SQL: supabase/VERIFICAR-E-CORRIGIR.sql")
        print("       SQL: supabase/migrations/20260604120000_profiles_phone_invites.sql")
        return

    try:
        from supabase import create_client
    except ImportError:
        warn("pip install supabase — pulando teste Supabase")
        return

    try:
        client = create_client(url, key)
    except Exception as exc:
        fail(f"Supabase create_client: {exc}")
        return

    tables = (
        "profiles",
        "chat_history",
        "user_personas",
        "agenda",
        "reminders",
        "shared_calendars",
        "shared_calendar_members",
    )
    def _ssl_skip(exc: Exception) -> bool:
        return "CERTIFICATE_VERIFY_FAILED" in str(exc)

    for table in tables:
        try:
            client.table(table).select("*").limit(1).execute()
            ok(f"tabela {table}")
        except Exception as exc:
            if _ssl_skip(exc):
                warn("Supabase: SSL no PC — use SQL manual no checklist .md")
                return
            fail(f"tabela {table}: {str(exc)[:120]}")

    for table, col in (
        ("profiles", "phone"),
        ("shared_calendar_members", "invited_phone"),
    ):
        try:
            client.table(table).select(col).limit(1).execute()
            ok(f"coluna {table}.{col}")
        except Exception as exc:
            if _ssl_skip(exc):
                return
            msg = str(exc).lower()
            if "column" in msg or col in msg:
                fail(
                    f"coluna {table}.{col} ausente — rode "
                    "supabase/migrations/20260604120000_profiles_phone_invites.sql"
                )
            else:
                fail(f"{table}.{col}: {exc}")


def sync_backup() -> None:
    print("\n[SYNC] app -> app_local_backup")
    ps1 = ROOT / "scripts" / "sync-app-to-backup.ps1"
    if not ps1.is_file():
        warn("sync-app-to-backup.ps1 ausente")
        return
    r = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ps1),
        ],
        cwd=str(ROOT),
    )
    if r.returncode != 0:
        warn("sync backup retornou codigo != 0")


def main() -> int:
    print("=== EGO-AI checklist automatizado ===")
    if REPAIR:
        print("(modo --repair: corrige PNG/MP4 de avatares)")
    if os.getenv("NODE_TLS_REJECT_UNAUTHORIZED", "").strip() == "0":
        print("(SSL verify off — NODE_TLS_REJECT_UNAUTHORIZED=0)")
    check_api()
    check_supabase()
    check_node_modules()
    repair_and_check_avatars()
    run_preflight()
    sync_backup()

    print("\n" + "=" * 60)
    if errors:
        print(f"FALHOU: {errors} erro(s), {warnings} aviso(s)")
        print("Corrija antes de 6-eas-build.bat ou testadores.")
        return 1
    if warnings:
        print(f"OK com {warnings} aviso(s) — revise acima.")
    else:
        print("TUDO OK (automatico).")
    print("Manual: INSTALAR-NO-CELULAR-USB.bat depois 6-eas-build.bat")
    print("Marcar: CHECKLIST-LANCAMENTO.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
