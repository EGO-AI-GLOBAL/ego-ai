"""Relógio e formatação no fuso do aparelho (sessão com timezone / tz_offset_min)."""

from __future__ import annotations

import datetime
import re

from ego_api.request_ctx import UserSession, get_session

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None  # type: ignore[misc, assignment]


def tzinfo_from_session(sess: UserSession | None) -> datetime.tzinfo | None:
    if not sess:
        return None
    tz_name = (sess.timezone or "").strip()
    if tz_name and ZoneInfo is not None:
        try:
            return ZoneInfo(tz_name)
        except Exception:
            pass
    if isinstance(sess.tz_offset_min, int):
        try:
            return datetime.timezone(datetime.timedelta(minutes=int(sess.tz_offset_min)))
        except Exception:
            pass
    return None


def local_now_from_session(sess: UserSession | None = None) -> datetime.datetime:
    """Agora no fuso do utilizador (aparelho); fallback: fuso do processo."""
    sess = sess or get_session()
    tz = tzinfo_from_session(sess)
    if tz is not None:
        return datetime.datetime.now(tz)
    return datetime.datetime.now().astimezone()


def utc_to_session_local(
    dt: datetime.datetime, sess: UserSession | None = None
) -> datetime.datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    else:
        dt = dt.astimezone(datetime.timezone.utc)
    tz = tzinfo_from_session(sess or get_session())
    if tz is not None:
        return dt.astimezone(tz)
    return dt.astimezone()


def format_scheduled_for_user(
    iso_val: object, sess: UserSession | None = None
) -> str:
    if not iso_val:
        return ""
    try:
        s = str(iso_val).strip().replace("Z", "+00:00")
        if re.match(r"^\d{4}-\d{2}-\d{2}T", s) and not re.search(
            r"[zZ]|[+-]\d{2}", s[10:]
        ):
            s = f"{s}+00:00"
        dt = datetime.datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        local = utc_to_session_local(dt, sess)
        return f" para {local.strftime('%d/%m às %H:%M')}"
    except Exception:
        return ""
