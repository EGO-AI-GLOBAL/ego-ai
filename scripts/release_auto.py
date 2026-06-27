#!/usr/bin/env python3
"""Release 1.0.50 automática: push + verificações + EAS + submit + ficheiros Railway."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_CONFIG = ROOT / "app" / "app.config.ts"

# Ficheiros obrigatórios na build 1.0.50 (100% do pacote)
REQUIRED_1_0_50: list[str] = [
    "app/app.config.ts",
    "app/app/reset-password.tsx",
    "app/app/forgot-password.tsx",
    "app/src/storage/passwordRecovery.ts",
    "app/src/storage/sessionRefresh.ts",
    "app/src/utils/authLinkParams.ts",
    "ego_api/auth_reset.py",
    "ego_api/services.py",
    "flask_api.py",
    "marketing/NOTAS-1.0.50-PLAY.txt",
]

REQUIRED_SNIPPETS: list[tuple[str, str]] = [
    ("app/src/api/client.ts", "completePasswordReset"),
    ("ego_api/services.py", "def complete_password_reset("),
    ("flask_api.py", '/auth/reset-password'),
    ("ego_api/gemini.py", "melhor psicólogo"),
    ("app/app.config.ts", 'version: "1.0.50"'),
    ("app/src/context/AuthContext.tsx", "saveLocalProfilePhone"),
]


def _run(cmd: list[str], *, cwd: Path = ROOT, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)
    if check and proc.returncode != 0:
        if proc.stdout:
            print(proc.stdout)
        if proc.stderr:
            print(proc.stderr, file=sys.stderr)
        raise SystemExit(proc.returncode)
    return proc


def verify_bundle(version: str = "1.0.50") -> None:
    print("=== Verificar pacote 1.0.50 (100%) ===")
    missing = [p for p in REQUIRED_1_0_50 if not (ROOT / p).is_file()]
    if missing:
        for p in missing:
            print(f"  FALTA  {p}")
        raise SystemExit("Pacote 1.0.50 incompleto — faltam ficheiros.")
    for path, needle in REQUIRED_SNIPPETS:
        text = (ROOT / path).read_text(encoding="utf-8")
        if needle not in text:
            raise SystemExit(f"Pacote incompleto: {path} sem «{needle}»")
        print(f"  OK    {path}")
    cfg = APP_CONFIG.read_text(encoding="utf-8")
    m_ver = re.search(r'version:\s*"([^"]+)"', cfg)
    m_ios = re.search(r'buildNumber:\s*"(\d+)"', cfg)
    m_and = re.search(r"versionCode:\s*(\d+)", cfg)
    if not m_ver or m_ver.group(1) != version:
        raise SystemExit(f"app.config.ts version deve ser {version}")
    print(f"  OK    versão {m_ver.group(1)} · iOS {m_ios.group(1) if m_ios else '?'} · Android {m_and.group(1) if m_and else '?'}")
    print("Pacote 1.0.50 completo.\n")


def git_push_if_needed() -> None:
    print("=== Git push ===")
    ahead = subprocess.run(
        ["git", "rev-list", "--count", "origin/main..HEAD"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    n = int((ahead.stdout or "0").strip() or "0")
    if n <= 0:
        print("OK — nada por enviar.\n")
        return
    print(f"A enviar {n} commit(s) para origin/main...")
    _run(["git", "push", "-u", "origin", "HEAD"])
    print("Push concluído.\n")


def write_railway_snippet(version: str, android_code: str) -> Path:
    msg = (
        f"{version}: Recuperar senha + ficar logado ao reabrir. Avatares só escuta. "
        "Toque em Atualizar agora."
    )
    body = f"""# Colar no Railway após loja aprovar 1.0.50
EGO_LATEST_APP_VERSION={version}
EGO_LATEST_ANDROID_VERSION_CODE={android_code}
EGO_APP_UPDATE_MESSAGE={msg}
EGO_MAINTENANCE=0

# Confirmar também (já devem existir):
# EGO_CHAT_AGENDA_ACTIONS=0
"""
    path = ROOT / f"RAILWAY-VARS-{version}.txt"
    path.write_text(body, encoding="utf-8")
    print(f"Railway vars gravadas em {path.name}")
    return path


def write_done_log(version: str, ids_path: Path) -> None:
    log = ROOT / f"RELEASE-{version}-DONE.txt"
    ids = {}
    if ids_path.is_file():
        ids = json.loads(ids_path.read_text(encoding="utf-8"))
    log.write_text(
        f"""EGO-AI {version} — release automática concluída
========================================
iOS build: {ids.get('ios', '?')}
Android build: {ids.get('android', '?')}
Enfileirado: {ids.get('queued_at', '?')}

Incluído 100%:
• Recuperar senha (web + app + API)
• Avatares só escuta (sem agendar no chat)
• Sessão persistente ao reabrir app
• Cadastro: telefone não repete para contas novas
• Rituais 8h/14h/21h alinhados

Próximo: Railway vars em RAILWAY-VARS-{version}.txt (após loja)
Supabase Redirect URLs: supabase/SUPABASE-REDIRECT-RESET-SENHA.txt
""",
        encoding="utf-8",
    )
    print(f"Log gravado em {log.name}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Release automática EGO-AI")
    parser.add_argument("--version", default="1.0.50")
    parser.add_argument("--skip-push", action="store_true")
    parser.add_argument("--skip-eas", action="store_true", help="Só verificações + push")
    args = parser.parse_args()
    version = args.version.strip()

    sys.path.insert(0, str(ROOT))
    from scripts import smoke_test_api  # noqa: WPS433
    from scripts import regression_guard  # noqa: WPS433
    from scripts.wait_and_submit_eas import (  # noqa: WPS433
        app_version,
        ids_file_for_version,
        queue_build,
        save_ids,
        submit_pair,
        sync_check,
        wait_both,
    )

    verify_bundle(version)

    if not args.skip_push:
        git_push_if_needed()

    if regression_guard.main() != 0:
        raise SystemExit("regression_guard falhou")

    if smoke_test_api.main() != 0:
        raise SystemExit("smoke_test_api falhou")

    sync_check()

    if args.skip_eas:
        print("EAS ignorado (--skip-eas).")
        return 0

    ids_path = ids_file_for_version(version)
    print(f"\n=== EAS {version} ===")
    ios_id = queue_build("ios")
    android_id = queue_build("android")
    save_ids(ids_path, ios_id, android_id, version=version)

    wait_both(ios_id, android_id)
    submit_pair(ios_id, android_id)

    cfg = APP_CONFIG.read_text(encoding="utf-8")
    m_and = re.search(r"versionCode:\s*(\d+)", cfg)
    android_code = m_and.group(1) if m_and else "89"
    write_railway_snippet(version, android_code)
    write_done_log(version, ids_path)

    print()
    print("=" * 60)
    print(f"  {version} 100% — builds submetidos iOS + Android")
    print("=" * 60)
    print("Supabase (1x manual): supabase/SUPABASE-REDIRECT-RESET-SENHA.txt")
    print(f"Railway após loja: RAILWAY-VARS-{version}.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
