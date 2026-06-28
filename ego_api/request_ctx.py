from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

_local = threading.local()


@dataclass
class UserSession:
    user_id: str
    email: str = ""
    access_token: str = ""
    refresh_token: str = ""
    user_name: str = ""
    assistant_name: str = "EGO-AI"
    avatar_id: str = "f1"
    timezone: str = ""
    tz_offset_min: int | None = None
    pdf_context: str = ""
    gemini_model_preference: str = ""
    gemini_model_ok: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


def set_session(sess: UserSession | None) -> None:
    _local.session = sess


def get_session() -> UserSession | None:
    return getattr(_local, "session", None)
