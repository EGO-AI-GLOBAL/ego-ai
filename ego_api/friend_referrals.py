"""Indicação amigo→amigo: link Stripe Premium + 1 mês grátis para quem indica."""

from __future__ import annotations

import datetime as dt
import os
import secrets
from typing import Any
from urllib.parse import quote

try:
    from ego_supabase import Client
except ImportError:
    from supabase import Client  # type: ignore[assignment]

from ego_api.auth_signup import check_signup_eligibility
from ego_api.phone_utils import normalize_phone_br
from ego_api.referrals import normalize_referral_code, validate_referral_code as validate_partner_code


MSG_ALREADY_REGISTERED = (
    "Esta pessoa já tem conta no EGO-AI (e-mail ou telefone cadastrado). "
    "Só podes indicar quem ainda não se registou."
)
MSG_SELF = "Não podes indicar a ti próprio."
MSG_NEED_EMAIL_PHONE = "Informe o e-mail e o telefone do amigo (com DDD)."


def _signup_base_url() -> str:
    return (
        os.getenv("EGO_APP_SIGNUP_URL", "").strip()
        or os.getenv("EGO_PUBLIC_WEBSITE_URL", "").strip().rstrip("/") + "/signup"
        or "https://egoai.com.br/signup"
    ).rstrip("/")


def _go_base_url() -> str:
    api = (os.getenv("EGO_PUBLIC_API_URL", "") or "").strip().rstrip("/")
    if api:
        return f"{api}/go"
    return "https://ego-ai-production-a2c2.up.railway.app/go"


def friend_stripe_checkout_url() -> str:
    """Payment Link Stripe com preço de indicação (mais barato que loja)."""
    return (
        os.getenv("STRIPE_CHECKOUT_FRIEND_REFERRAL_URL", "").strip()
        or os.getenv("STRIPE_CHECKOUT_PREMIUM_URL", "").strip()
        or ""
    )


def friend_stripe_promo_code() -> str:
    return (os.getenv("STRIPE_FRIEND_REFERRAL_PROMO_CODE", "") or "").strip()


def append_friend_promo(url: str) -> str:
    base = (url or "").strip()
    promo = friend_stripe_promo_code()
    if not base or not promo:
        return base
    if "prefilled_promo_code=" in base:
        return base
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}prefilled_promo_code={quote(promo, safe='')}"


def _gen_code() -> str:
    return f"AMIGO{secrets.token_hex(3).upper()}"


def ensure_friend_invite_code(supabase: Client, user_id: str) -> str:
    row = (
        supabase.table("profiles")
        .select("friend_invite_code")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    existing = ""
    if row.data:
        existing = str(row.data[0].get("friend_invite_code") or "").strip()
    if existing:
        return existing.upper()
    for _ in range(8):
        code = _gen_code()
        try:
            supabase.table("profiles").update({"friend_invite_code": code}).eq(
                "id", user_id
            ).execute()
            return code
        except Exception:
            continue
    code = _gen_code()
    supabase.table("profiles").update({"friend_invite_code": code}).eq(
        "id", user_id
    ).execute()
    return code


def find_user_id_by_friend_code(supabase: Client, code: str) -> str | None:
    norm = normalize_referral_code(code)
    if not norm:
        return None
    res = (
        supabase.table("profiles")
        .select("id")
        .ilike("friend_invite_code", norm)
        .limit(1)
        .execute()
    )
    if not res.data:
        return None
    return str(res.data[0].get("id") or "") or None


def validate_friend_or_partner_code(code: str) -> tuple[dict | None, str | None]:
    """Parceiro B2B (canal Connect) → influenciador → código pessoal de amigo."""
    from ego_api.gym_partners import (
        get_admin_client as gym_admin_client,
        lookup_gym_partner,
        normalize_partner_code,
    )
    from ego_api.supabase_client import create_service_client

    # 1) Parceiro B2B (academia/clínica/empresa/…) → Stripe Connect
    gym_code = normalize_partner_code(code)
    if gym_code:
        try:
            gym_sb = gym_admin_client() or create_service_client()
            if gym_sb:
                gym = lookup_gym_partner(gym_sb, gym_code)
                if gym:
                    return {
                        "kind": "partner",
                        "code": gym.get("partner_code") or gym_code,
                        "display_name": gym.get("name") or gym_code,
                    }, None
        except Exception:
            pass

    # 2) Influenciador
    partner, err = validate_partner_code(code)
    if partner:
        return {
            "kind": "influencer",
            "code": partner["code"],
            "display_name": partner.get("display_name") or partner["code"],
        }, None

    # 3) Amigo
    admin = create_service_client()
    if not admin:
        return None, err or "Código inválido."
    uid = find_user_id_by_friend_code(admin, code)
    if not uid:
        return None, err or "Código inválido."
    norm = normalize_referral_code(code)
    return {
        "kind": "friend",
        "code": norm,
        "display_name": "Indicação de amigo",
        "referrer_user_id": uid,
    }, None


def assert_invitee_not_registered(email: str, phone: str) -> tuple[bool, str | None]:
    """Trava: não indicar quem já tem e-mail ou telefone no EGO."""
    pre = check_signup_eligibility(email, phone)
    if pre.get("ok"):
        return True, None
    reason = str(pre.get("reason") or "")
    if reason in ("email_taken", "phone_taken", "duplicate"):
        return False, MSG_ALREADY_REGISTERED
    msg = str(pre.get("message") or "").strip()
    if "já está cadastrado" in msg.lower() or "já cadastrado" in msg.lower():
        return False, MSG_ALREADY_REGISTERED
    return False, msg or MSG_NEED_EMAIL_PHONE


def create_friend_invite(
    supabase: Client,
    referrer_user_id: str,
    email: str,
    phone: str,
) -> tuple[dict | None, str | None]:
    from ego_api.services import normalize_email

    email_norm, email_err = normalize_email(email)
    if email_err:
        return None, email_err
    phone_norm, phone_err = normalize_phone_br(phone)
    if phone_err:
        return None, phone_err or MSG_NEED_EMAIL_PHONE

    # Auto-indicação
    me = (
        supabase.table("profiles")
        .select("email,phone")
        .eq("id", referrer_user_id)
        .limit(1)
        .execute()
    )
    if me.data:
        my_email = str(me.data[0].get("email") or "").strip().lower()
        my_phone = str(me.data[0].get("phone") or "").strip()
        if my_email and my_email == email_norm:
            return None, MSG_SELF
        if my_phone and phone_norm and my_phone == phone_norm:
            return None, MSG_SELF

    ok, err = assert_invitee_not_registered(email_norm, phone_norm)
    if not ok:
        return None, err

    code = ensure_friend_invite_code(supabase, referrer_user_id)
    try:
        supabase.table("friend_referral_invites").insert(
            {
                "referrer_user_id": referrer_user_id,
                "invited_email": email_norm,
                "invited_phone": phone_norm,
                "status": "pending",
            }
        ).execute()
    except Exception as exc:  # noqa: BLE001
        low = str(exc).lower()
        if "unique" in low or "duplicate" in low:
            return None, "Já existe um convite pendente para este e-mail."
        return None, "Não foi possível guardar o convite. Tente de novo."

    signup = _signup_base_url()
    if "signup" not in signup.lower():
        share = f"{_go_base_url()}?ref={quote(code)}&next=signup"
    else:
        sep = "&" if "?" in signup else "?"
        share = f"{signup}{sep}ref={quote(code)}"

    stripe = append_friend_promo(friend_stripe_checkout_url())
    return {
        "code": code,
        "share_url": share,
        "stripe_checkout_url": stripe or None,
        "invited_email": email_norm,
        "message": (
            "Convite ok. Partilha o link — o amigo cria conta e assina no Stripe "
            "(Premium). Se ele pagar, ganhas 1 mês grátis."
        ),
    }, None


def friend_referral_status(supabase: Client, user_id: str) -> dict[str, Any]:
    code = ensure_friend_invite_code(supabase, user_id)
    prof = (
        supabase.table("profiles")
        .select("referral_bonus_until")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    bonus_until = None
    if prof.data:
        bonus_until = prof.data[0].get("referral_bonus_until")

    invites = (
        supabase.table("friend_referral_invites")
        .select("id,invited_email,status,created_at")
        .eq("referrer_user_id", user_id)
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    paid = (
        supabase.table("profiles")
        .select("id")
        .eq("referred_by_user_id", user_id)
        .not_.is_("friend_referral_paid_at", "null")
        .execute()
    )
    rewards = len(paid.data or [])
    signup = _signup_base_url()
    sep = "&" if "?" in signup else "?"
    share = f"{signup}{sep}ref={quote(code)}"
    stripe = append_friend_promo(friend_stripe_checkout_url())
    return {
        "code": code,
        "share_url": share,
        "stripe_checkout_url": stripe or None,
        "rewards_earned": rewards,
        "referral_bonus_until": bonus_until,
        "invites": list(invites.data or []),
        "tagline": (
            "Coloca o e-mail e o telefone do amigo e envia o link Stripe pelo WhatsApp. "
            "Se ele assinar o Premium, você ganha 1 mês grátis. "
            "Só quem ainda não tem e-mail ou telefone no EGO."
        ),
    }


def attach_friend_referral_on_signup(
    supabase: Client, user_id: str, code: str, *, email: str = ""
) -> str | None:
    """Liga o novo utilizador ao amigo indicador (código pessoal)."""
    norm = normalize_referral_code(code)
    if not norm:
        return None
    referrer = find_user_id_by_friend_code(supabase, norm)
    if not referrer:
        return None
    if referrer == user_id:
        return MSG_SELF

    row = (
        supabase.table("profiles")
        .select("referred_by_user_id, referred_by_partner_id")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    if not row.data:
        return "Perfil não encontrado."
    if row.data[0].get("referred_by_user_id") or row.data[0].get("referred_by_partner_id"):
        return None

    supabase.table("profiles").update({"referred_by_user_id": referrer}).eq(
        "id", user_id
    ).execute()

    email_norm = (email or "").strip().lower()
    if email_norm:
        try:
            supabase.table("friend_referral_invites").update(
                {"status": "signed_up", "referred_user_id": user_id}
            ).eq("referrer_user_id", referrer).eq("invited_email", email_norm).eq(
                "status", "pending"
            ).execute()
        except Exception:
            pass
    return None


def grant_referrer_one_month(
    supabase: Client, referred_user_id: str, *, stripe_session_id: str = ""
) -> dict[str, Any]:
    """Após 1º pagamento Stripe do indicado → 1 mês Premium para quem indicou."""
    row = (
        supabase.table("profiles")
        .select("referred_by_user_id, friend_referral_paid_at, email")
        .eq("id", referred_user_id)
        .limit(1)
        .execute()
    )
    if not row.data:
        return {"skipped": "no_profile"}
    prof = row.data[0]
    if prof.get("friend_referral_paid_at"):
        return {"skipped": "already_paid"}
    referrer = str(prof.get("referred_by_user_id") or "").strip()
    if not referrer:
        return {"skipped": "no_referrer"}

    now = dt.datetime.now(dt.timezone.utc)
    ref_row = (
        supabase.table("profiles")
        .select("referral_bonus_until, plan_tier, is_pro")
        .eq("id", referrer)
        .limit(1)
        .execute()
    )
    base = now
    if ref_row.data and ref_row.data[0].get("referral_bonus_until"):
        try:
            raw = str(ref_row.data[0]["referral_bonus_until"])
            prev = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if prev > base:
                base = prev
        except Exception:
            pass
    until = base + dt.timedelta(days=30)

    supabase.table("profiles").update(
        {"friend_referral_paid_at": now.isoformat()}
    ).eq("id", referred_user_id).execute()

    supabase.table("profiles").update(
        {"referral_bonus_until": until.isoformat()}
    ).eq("id", referrer).execute()

    try:
        supabase.table("friend_referral_invites").update(
            {"status": "rewarded", "referred_user_id": referred_user_id}
        ).eq("referrer_user_id", referrer).eq(
            "invited_email", str(prof.get("email") or "").strip().lower()
        ).execute()
    except Exception:
        pass

    return {
        "referrer_user_id": referrer,
        "referral_bonus_until": until.isoformat(),
        "stripe_session_id": stripe_session_id or None,
        "months": 1,
    }
