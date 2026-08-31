"""Testes — anti-abuso free identity guard."""

from __future__ import annotations

from ego_api.free_identity_guard import (
    _oauth_keys_from_auth_user,
    _usage_snapshot,
    profile_has_trial_used,
)


class _Ident:
    def __init__(self, provider: str, id: str):
        self.provider = provider
        self.id = id


class _User:
    def __init__(self, identities):
        self.identities = identities


def test_oauth_keys_from_auth_user():
    user = _User([_Ident("apple", "abc-123"), _Ident("email", "x")])
    keys = _oauth_keys_from_auth_user(user)
    assert keys == [("apple", "abc-123")]


def test_usage_snapshot_resets_other_day():
    prof = {
        "daily_usage_date": "2020-01-01",
        "ui_state": {"daily_messages": {"date": "2020-01-01", "text": 5, "voice": 1}},
        "daily_tts_count": 1,
    }
    d, text, voice, tts = _usage_snapshot(prof)
    assert text == 0 and voice == 0 and tts == 0


def test_profile_has_trial_used():
    assert profile_has_trial_used({"ui_state": {"trial_used": True}})
    assert not profile_has_trial_used({"ui_state": {}})
