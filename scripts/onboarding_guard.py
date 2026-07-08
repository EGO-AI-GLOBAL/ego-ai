#!/usr/bin/env python3
"""
Bloqueia regressões no fluxo utilizador NOVO: cadastro → avatar → chat.

Corre dentro de regression_guard.py antes de qualquer EAS build.

  python scripts/onboarding_guard.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_SRC = ROOT / "app" / "src"
APP_APP = ROOT / "app" / "app"

# (ficheiro, marcador que DEVE existir antes do return null de guarda)
HOOKS_BEFORE_GUARD: list[tuple[str, str, str]] = [
    (
        "app/src/components/moodMonsters/MoodGardenWidgetCard.tsx",
        "const subtitle = useMemo",
        "if (!care?.question) return null",
    ),
    (
        "app/src/components/EgoDeBolsoChatCard.tsx",
        "useState(false)",
        "if (!journey) return null",
    ),
]

ONBOARDING_FILES = [
    "app/src/storage/freshInstallGuard.ts",
    "app/app/(main)/choose-avatar.tsx",
    "app/app/forgot-password.tsx",
    "app/app/reset-password.tsx",
    "app/src/components/PersonaPicker.tsx",
    "app/src/components/PersonaGate.tsx",
    "ego_api/auth_reset.py",
    "supabase/SUPABASE-REDIRECT-RESET-SENHA.txt",
    "supabase/SUPABASE-SMTP-RESET-SENHA.txt",
]

FORBIDDEN_IN_APP_SRC = [
    ("colors.card", "AppColors não tem .card — use colors.bgCard"),
]


def _read(rel: str) -> str:
    path = ROOT / rel.replace("/", "\\")
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _hooks_before_guard(rel: str, hook_marker: str, guard_marker: str) -> bool:
    text = _read(rel)
    if not text:
        return False
    hi = text.find(hook_marker)
    gi = text.find(guard_marker)
    if hi < 0 or gi < 0:
        return False
    return hi < gi


def check_hooks_order() -> int:
    failed = 0
    print("=== Onboarding - hooks antes de return null ===")
    for rel, hook_marker, guard_marker in HOOKS_BEFORE_GUARD:
        if not _read(rel):
            print(f"  ERRO  ficheiro em falta: {rel}")
            failed += 1
            continue
        if _hooks_before_guard(rel, hook_marker, guard_marker):
            print(f"  OK    {rel}")
        else:
            print(
                f"  ERRO  {rel}: '{guard_marker}' antes de hooks - crash em utilizador novo"
            )
            failed += 1
    return failed


def check_forbidden_tokens() -> int:
    failed = 0
    print("\n=== Onboarding - tokens proibidos em app/src ===")
    for path in APP_SRC.rglob("*.tsx"):
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(ROOT).as_posix()
        for token, why in FORBIDDEN_IN_APP_SRC:
            if token in text:
                print(f"  ERRO  {rel}: {why} ({token})")
                failed += 1
    if failed == 0:
        print("  OK    sem colors.card em app/src")
    return failed


def check_onboarding_files() -> int:
    failed = 0
    print("\n=== Onboarding - ficheiros do fluxo cadastro/senha ===")
    for rel in ONBOARDING_FILES:
        if _read(rel):
            print(f"  OK    {rel}")
        else:
            print(f"  ERRO  em falta: {rel}")
            failed += 1
    return failed


def check_avatar_engagement_card() -> int:
    rel = "app/src/components/AvatarEngagementCard.tsx"
    text = _read(rel)
    print("\n=== Onboarding - AvatarEngagementCard ===")
    if not text:
        print(f"  ERRO  {rel} em falta")
        return 1
    if "colors.bgCard" not in text:
        print("  ERRO  AvatarEngagementCard deve usar colors.bgCard")
        return 1
    if "colors.card" in text:
        print("  ERRO  AvatarEngagementCard ainda usa colors.card")
        return 1
    print(f"  OK    {rel}")
    return 0


def check_password_reset_api() -> int:
    failed = 0
    print("\n=== Onboarding - API recuperar senha ===")
    for rel, needle in [
        ("flask_api.py", '@app.post("/api/v1/auth/forgot-password")'),
        ("flask_api.py", '@app.get("/auth/reset-password")'),
        ("ego_api/auth_reset.py", "password_reset_redirect_url"),
        ("ego_api/auth_reset.py", "dispatch_password_reset_email"),
        ("app/src/api/client.ts", "requestPasswordReset"),
    ]:
        if needle in _read(rel):
            print(f"  OK    {rel} :: {needle[:40]}")
        else:
            print(f"  ERRO  {rel}: em falta {needle}")
            failed += 1
    return failed


def scan_early_return_before_hooks() -> int:
    """Scan só componentes do 1º ecrã pós-cadastro (chat + cartões)."""
    failed = 0
    hook_re = re.compile(r"\buse(Memo|State|Effect|Callback|Ref)\s*\(")
    print("\n=== Onboarding - scan componentes do chat (hooks apos return null) ===")
    scan_files = [
        APP_SRC / "components" / "moodMonsters" / "MoodGardenWidgetCard.tsx",
        APP_SRC / "components" / "AvatarEngagementCard.tsx",
        APP_SRC / "components" / "EgoDeBolsoChatCard.tsx",
        APP_SRC / "components" / "SpeakingAvatar.tsx",
        APP_SRC / "components" / "TrialExpiredBanner.tsx",
        APP_SRC / "components" / "ChatDayStrip.tsx",
        APP_SRC / "components" / "WellnessJourneyCard.tsx",
    ]
    for path in scan_files:
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        in_fn = False
        brace = 0
        saw_return_null = False
        for i, line in enumerate(lines, 1):
            if re.search(r"export (default )?function ", line):
                in_fn = True
                brace = 0
                saw_return_null = False
            if not in_fn:
                continue
            brace += line.count("{") - line.count("}")
            if re.search(r"return\s+null\s*;", line):
                saw_return_null = True
            if saw_return_null and hook_re.search(line):
                print(
                    f"  ERRO  {rel}:{i} - hook apos return null (utilizador novo pode crashar)"
                )
                failed += 1
                break
            if brace <= 0 and "function " in line:
                in_fn = False
    if failed == 0:
        print("  OK    componentes do chat sem hook após return null")
    return failed


def check_fresh_install_guard() -> int:
    print("\n=== Onboarding - sessão zombie após reinstall (iOS Keychain) ===")
    guard = _read("app/src/storage/freshInstallGuard.ts")
    auth = _read("app/src/context/AuthContext.tsx")
    persona = _read("app/src/storage/personaPrefs.ts")
    failed = 0
    if "clearSecureSessionIfFreshInstall" not in guard:
        print("  ERRO  freshInstallGuard.ts sem clearSecureSessionIfFreshInstall")
        failed += 1
    elif "ego_secure_install_marker_v1" not in guard:
        print("  ERRO  freshInstallGuard.ts sem marcador SecureStore (backup)")
        failed += 1
    elif "consumeSecureWipeIfNeeded" not in guard:
        print("  ERRO  freshInstallGuard.ts sem consumeSecureWipeIfNeeded (persona Keychain)")
        failed += 1
    elif "clearLocalProfilePhone" in guard.split("consumeSecureWipeIfNeeded", 1)[-1]:
        print("  ERRO  consumeSecureWipeIfNeeded não deve apagar telefone (pede 2x no cadastro)")
        failed += 1
    else:
        print("  OK    app/src/storage/freshInstallGuard.ts")
    if "clearLocalPersonaForUser" not in persona:
        print("  ERRO  personaPrefs.ts sem clearLocalPersonaForUser")
        failed += 1
    else:
        print("  OK    personaPrefs limpa escolha local")
    if "clearSecureSessionIfFreshInstall" not in auth:
        print("  ERRO  AuthContext não chama clearSecureSessionIfFreshInstall no arranque")
        failed += 1
    elif "consumeSecureWipeIfNeeded" not in auth:
        print("  ERRO  AuthContext não consome wipe de persona após login")
        failed += 1
    else:
        print("  OK    AuthContext limpa Keychain em reinstall + persona")
    return failed


def check_persona_gate() -> int:
    print("\n=== Onboarding - PersonaGate após escolher avatar ===")
    text = _read("app/src/components/PersonaGate.tsx")
    if not text:
        print("  ERRO  PersonaGate.tsx em falta")
        return 1
    failed = 0
    if "personaGateOk" not in text:
        print("  ERRO  PersonaGate deve usar personaGateOk (evita loop chat/avatar)")
        failed += 1
    if "personaReady" not in text:
        print("  ERRO  PersonaGate deve combinar local + personaGateOk")
        failed += 1
    if failed == 0:
        print("  OK    PersonaGate com personaGateOk")
    return failed


def check_chat_screen_imports() -> int:
    print("\n=== Onboarding - chat.tsx imports obrigatórios ===")
    text = _read("app/app/(main)/chat.tsx")
    if not text:
        print("  ERRO  chat.tsx em falta")
        return 1
    if "<AppGradientBackground" in text and "@/components/AppGradientBackground" not in text:
        print("  ERRO  chat.tsx usa AppGradientBackground sem import")
        return 1
    print("  OK    chat.tsx com AppGradientBackground importado")
    return 0


def main() -> int:
    failed = 0
    failed += check_hooks_order()
    failed += check_forbidden_tokens()
    failed += check_onboarding_files()
    failed += check_avatar_engagement_card()
    failed += check_password_reset_api()
    failed += check_fresh_install_guard()
    failed += check_persona_gate()
    failed += check_chat_screen_imports()
    failed += scan_early_return_before_hooks()
    print()
    if failed:
        print(f"ONBOARDING GUARD: {failed} falha(s). NÃO build até corrigir.")
        return 1
    print("ONBOARDING GUARD: OK - fluxo cadastro->avatar->chat protegido.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
