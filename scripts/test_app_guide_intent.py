"""Smoke rápido — tutorial vs ação na agenda (pessoal e compartilhada)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ego_api.app_guide import (
    looks_like_any_agenda_action_intent,
    looks_like_app_help_intent,
)


def main() -> None:
    help_cases = [
        ("como usar monstrinhos", True),
        ("como usar a agenda", True),
        ("como marco na agenda da familia", True),
        ("marca reuniao amanha 15h", False),
        ("estou triste hoje", False),
    ]
    for text, expected in help_cases:
        got = looks_like_app_help_intent(text)
        assert got == expected, f"help {text!r}: expected {expected}, got {got}"

    action_cases = [
        ("marca reuniao amanha 15h", True),
        ("marca na agenda familia jantar sexta 20h", True),
        ("convida maria@email.com na agenda familia", True),
        ("cria agenda compartilhada familia", True),
        ("como usar agenda compartilhada", False),
    ]
    for text, expected in action_cases:
        got = looks_like_any_agenda_action_intent(text)
        assert got == expected, f"action {text!r}: expected {expected}, got {got}"

    # "como convidar na agenda" should be help not action
    assert looks_like_app_help_intent("como convidar na agenda")
    assert not looks_like_any_agenda_action_intent("como convidar na agenda")

    print("test_app_guide_intent: OK")


if __name__ == "__main__":
    main()
