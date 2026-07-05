"""
Supabase client for MyPy Tutor.

Provides permanent cloud persistence for:
  - User profiles (profiles table)
  - Conversations & messages (conversations + messages tables)
  - Learning progress (learner_progress table)
  - Certificates (certificates table)
  - Payments (payments table)

Design: dual-write.
  - SQLite remains the fast local read/write cache.
  - Every write is also mirrored to Supabase asynchronously.
  - On startup, data is reconciled from Supabase if SQLite is empty
    (covers Render ephemeral filesystem restarts).
  - If SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY are not set, all
    Supabase calls silently no-op — the app continues with SQLite only.

Required Render environment variables:
    SUPABASE_URL              https://<project-ref>.supabase.co
    SUPABASE_ANON_KEY         your publishable anon key
    SUPABASE_SERVICE_ROLE_KEY your service role key (server-side only)

SQL to run once in Supabase SQL editor → see docs/supabase_schema.sql
"""

import os
import logging
from typing import Any

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "") or os.getenv("SUPABASE_ANON_KEY", "")

_client = None   # lazy-initialised


def get_supabase():
    """
    Return a Supabase client, or None if not configured.
    Lazy-initialises on first call to avoid import-time errors.
    """
    global _client
    if _client is not None:
        return _client
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.info("Supabase not configured — using SQLite only")
        return None
    try:
        from supabase import create_client
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Supabase client initialised: %s", SUPABASE_URL)
        return _client
    except Exception as exc:
        logger.warning("Supabase init failed: %s — falling back to SQLite", exc)
        return None


def sb_enabled() -> bool:
    """True if Supabase is configured and the client was created."""
    return get_supabase() is not None


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------

def sb_upsert_profile(learner_id: str, email: str, name: str,
                       tier: str = "free", level: str = "beginner",
                       xp: int = 0) -> None:
    """Create or update a learner profile in Supabase."""
    sb = get_supabase()
    if not sb:
        return
    try:
        sb.table("profiles").upsert({
            "id":           learner_id,
            "email":        email,
            "full_name":    name,
            "subscription": tier,
            "level":        level,
            "xp":           xp,
        }, on_conflict="id").execute()
    except Exception as exc:
        logger.warning("sb_upsert_profile failed: %s", exc)


def sb_get_profile(learner_id: str) -> dict | None:
    """Fetch a profile from Supabase. Returns None on failure."""
    sb = get_supabase()
    if not sb:
        return None
    try:
        res = sb.table("profiles").select("*").eq("id", learner_id).single().execute()
        return res.data
    except Exception as exc:
        logger.debug("sb_get_profile miss for %s: %s", learner_id, exc)
        return None


def sb_update_tier(learner_id: str, tier: str) -> None:
    sb = get_supabase()
    if not sb:
        return
    try:
        sb.table("profiles").update({"subscription": tier}).eq("id", learner_id).execute()
    except Exception as exc:
        logger.warning("sb_update_tier failed: %s", exc)


# ---------------------------------------------------------------------------
# Conversations & Messages  (persistent AI memory)
# ---------------------------------------------------------------------------

def sb_get_or_create_conversation(learner_id: str) -> str | None:
    """
    Returns the active conversation_id for a learner.
    Creates a new conversation row if none exists.
    Ensures the profile row exists first to prevent FK violations.
    Returns None if Supabase unavailable.
    """
    sb = get_supabase()
    if not sb:
        return None
    try:
        # Ensure a minimal profile row exists before inserting conversation.
        # Use upsert with on_conflict=id so we never overwrite real profile data.
        # Only inserts if the row doesn't exist yet.
        try:
            sb.table("profiles").upsert({
                "id":        learner_id,
                "email":     "",       # empty — real email added by sb_upsert_profile later
                "full_name": "",
            }, on_conflict="id").execute()
        except Exception:
            pass  # profile may already exist; ignore errors

        # Look for the most recent conversation
        res = (
            sb.table("conversations")
            .select("id")
            .eq("learner_id", learner_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if res.data:
            return res.data[0]["id"]
        # Create a new one
        import secrets
        conv_id = secrets.token_hex(16)
        sb.table("conversations").insert({
            "id":         conv_id,
            "learner_id": learner_id,
        }).execute()
        return conv_id
    except Exception as exc:
        logger.warning("sb_get_or_create_conversation failed: %s", exc)
        return None


def sb_save_message(conversation_id: str, learner_id: str,
                     role: str, content: str,
                     intent: str = "", topic: str = "") -> None:
    """Persist a single message to Supabase messages table."""
    sb = get_supabase()
    if not sb or not conversation_id:
        return
    try:
        sb.table("messages").insert({
            "conversation_id": conversation_id,
            "learner_id":      learner_id,
            "role":            role,
            "content":         content[:8000],
            "intent":          intent[:50],
            "topic":           topic[:100],
        }).execute()
    except Exception as exc:
        logger.warning("sb_save_message failed: %s", exc)


def sb_load_messages(conversation_id: str, limit: int = 20) -> list[dict]:
    """
    Load the last N messages for a conversation.
    Returns list of {role, content} dicts — ready to pass to LLM.
    """
    sb = get_supabase()
    if not sb or not conversation_id:
        return []
    try:
        res = (
            sb.table("messages")
            .select("role,content,intent,topic,created_at")
            .eq("conversation_id", conversation_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        # Return in chronological order
        return list(reversed(res.data or []))
    except Exception as exc:
        logger.warning("sb_load_messages failed: %s", exc)
        return []


def sb_load_all_conversations(learner_id: str) -> list[dict]:
    """
    Return all conversations for a learner (for history panel).
    Each item has: id, created_at, message_count (approx).
    """
    sb = get_supabase()
    if not sb:
        return []
    try:
        res = (
            sb.table("conversations")
            .select("id,created_at")
            .eq("learner_id", learner_id)
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )
        return res.data or []
    except Exception as exc:
        logger.warning("sb_load_all_conversations failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Progress sync
# ---------------------------------------------------------------------------

def sb_sync_progress(learner_id: str, profile_dict: dict) -> None:
    """Mirror learner progress to Supabase learner_progress table."""
    sb = get_supabase()
    if not sb:
        return
    try:
        import json
        # Serialize topic_progress — it's a dict of TopicProgress objects or dicts
        tp_raw = profile_dict.get("topic_progress", {})
        if isinstance(tp_raw, dict):
            tp_serialized = json.dumps({
                k: v if isinstance(v, dict) else v.model_dump() if hasattr(v, "model_dump") else {}
                for k, v in tp_raw.items()
            })
        else:
            tp_serialized = "{}"
        sb.table("learner_progress").upsert({
            "learner_id":          learner_id,
            "level":               profile_dict.get("level", "beginner"),
            "xp":                  profile_dict.get("xp", 0),
            "tier":                profile_dict.get("tier", "free"),
            "badges":              json.dumps(profile_dict.get("badges", [])),
            "topics_seen":         json.dumps(profile_dict.get("topics_seen", [])),
            "topic_progress":      tp_serialized,
            "current_course":      profile_dict.get("current_course"),
            "current_course_step": profile_dict.get("current_course_step", 0),
            "completed_projects":  json.dumps(profile_dict.get("completed_projects", [])),
            "email":               profile_dict.get("email", ""),
            "display_name":        profile_dict.get("display_name", ""),
        }, on_conflict="learner_id").execute()
    except Exception as exc:
        logger.debug("sb_sync_progress failed: %s", exc)


def sb_load_progress(learner_id: str) -> dict | None:
    """Load progress from Supabase on restart (SQLite recovery)."""
    sb = get_supabase()
    if not sb:
        return None
    try:
        res = (
            sb.table("learner_progress")
            .select("*")
            .eq("learner_id", learner_id)
            .single()
            .execute()
        )
        return res.data
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Certificates
# ---------------------------------------------------------------------------

def sb_save_certificate(cert_id: str, learner_id: str,
                          learner_name: str, level: str) -> None:
    sb = get_supabase()
    if not sb:
        return
    try:
        sb.table("certificates").upsert({
            "id":           cert_id,
            "learner_id":   learner_id,
            "learner_name": learner_name,
            "level":        level,
        }, on_conflict="id").execute()
    except Exception as exc:
        logger.warning("sb_save_certificate failed: %s", exc)


# ---------------------------------------------------------------------------
# Email accounts  (survives Render ephemeral restarts)
# ---------------------------------------------------------------------------

def sb_upsert_email_account(email: str, learner_id: str,
                              full_name: str, password_hash: str) -> None:
    """
    Store a confirmed email account in Supabase.
    Called every time an account is confirmed or password is updated.
    password_hash is SHA-256 — never plain text.
    """
    sb = get_supabase()
    if not sb:
        return
    try:
        sb.table("email_accounts").upsert({
            "email":         email.lower(),
            "learner_id":    learner_id,
            "full_name":     full_name,
            "password_hash": password_hash,
            "confirmed":     True,
        }, on_conflict="email").execute()
        logger.debug("sb_upsert_email_account: %s", email)
    except Exception as exc:
        logger.warning("sb_upsert_email_account failed for %s: %s", email, exc)


def sb_update_email_password(email: str, new_hash: str) -> None:
    """Update only the password_hash in Supabase after a reset."""
    sb = get_supabase()
    if not sb:
        return
    try:
        sb.table("email_accounts").update({
            "password_hash": new_hash,
        }).eq("email", email.lower()).execute()
    except Exception as exc:
        logger.warning("sb_update_email_password failed for %s: %s", email, exc)


def sb_load_all_email_accounts() -> list[dict]:
    """
    Fetch all confirmed email accounts from Supabase.
    Called on startup to repopulate SQLite + in-memory cache
    when the Render ephemeral filesystem has been wiped.
    Returns list of dicts with: email, learner_id, full_name, password_hash.
    """
    sb = get_supabase()
    if not sb:
        return []
    try:
        res = (
            sb.table("email_accounts")
            .select("email,learner_id,full_name,password_hash,confirmed")
            .eq("confirmed", True)
            .execute()
        )
        return res.data or []
    except Exception as exc:
        logger.warning("sb_load_all_email_accounts failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------

def sb_save_payment(payment_id: str, email: str, name: str,
                     amount: float, plan: str, method: str = "paystack") -> None:
    sb = get_supabase()
    if not sb:
        return
    try:
        sb.table("payments").upsert({
            "id":     payment_id,
            "email":  email,
            "name":   name,
            "amount": amount,
            "plan":   plan,
            "method": method,
        }, on_conflict="id").execute()
    except Exception as exc:
        logger.warning("sb_save_payment failed: %s", exc)


# ---------------------------------------------------------------------------
# Pending confirmations  (survives Render restarts so email links still work)
# ---------------------------------------------------------------------------

def sb_save_pending_confirmation(email: str, learner_id: str,
                                  full_name: str, password_hash: str,
                                  token: str) -> None:
    """
    Save an unconfirmed registration to Supabase pending_confirmations table.
    Allows confirmation links to work even after a Render restart wipes _pending.
    """
    sb = get_supabase()
    if not sb:
        return
    try:
        import time as _t
        sb.table("pending_confirmations").upsert({
            "email":         email.lower(),
            "learner_id":    learner_id,
            "full_name":     full_name,
            "password_hash": password_hash,
            "token":         token,
            "created_at":    _t.time(),
        }, on_conflict="email").execute()
    except Exception as exc:
        logger.debug("sb_save_pending_confirmation failed for %s: %s", email, exc)


def sb_delete_pending_confirmation(email: str) -> None:
    """Remove a confirmed user from the pending_confirmations table."""
    sb = get_supabase()
    if not sb:
        return
    try:
        sb.table("pending_confirmations").delete().eq("email", email.lower()).execute()
    except Exception as exc:
        logger.debug("sb_delete_pending_confirmation failed for %s: %s", email, exc)


def sb_load_pending_confirmations() -> list[dict]:
    """
    Load all pending (unconfirmed) registrations from Supabase.
    Called on startup to repopulate _pending so old confirmation links still work.
    Returns list of dicts with: email, learner_id, full_name, password_hash, token, created_at.
    """
    sb = get_supabase()
    if not sb:
        return []
    try:
        import time as _t
        cutoff = _t.time() - (60 * 60 * 24)  # 24 hours ago — ignore expired
        res = (
            sb.table("pending_confirmations")
            .select("email,learner_id,full_name,password_hash,token,created_at")
            .gt("created_at", cutoff)
            .execute()
        )
        rows = res.data or []
        # Add created_at_ts field (numeric) for age check in email_auth.py
        for r in rows:
            r["created_at_ts"] = float(r.get("created_at") or 0)
        return rows
    except Exception as exc:
        logger.debug("sb_load_pending_confirmations failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Password reset tokens  (survives Render restarts)
# ---------------------------------------------------------------------------

def sb_save_reset_token(token: str, email: str) -> None:
    """Persist a password reset token to Supabase."""
    sb = get_supabase()
    if not sb:
        return
    try:
        import time as _t
        sb.table("password_reset_tokens").upsert({
            "token":      token,
            "email":      email.lower(),
            "used":       False,
            "created_at": _t.time(),
        }, on_conflict="token").execute()
    except Exception as exc:
        logger.debug("sb_save_reset_token failed: %s", exc)


def sb_load_reset_token(token: str) -> dict | None:
    """Load a reset token from Supabase. Returns None if not found or already used."""
    sb = get_supabase()
    if not sb:
        return None
    try:
        res = (
            sb.table("password_reset_tokens")
            .select("token,email,used,created_at")
            .eq("token", token)
            .eq("used", False)
            .single()
            .execute()
        )
        return res.data
    except Exception:
        return None


def sb_mark_reset_token_used(token: str) -> None:
    """Mark a reset token as used in Supabase."""
    sb = get_supabase()
    if not sb:
        return
    try:
        sb.table("password_reset_tokens").update({"used": True}).eq("token", token).execute()
    except Exception as exc:
        logger.debug("sb_mark_reset_token_used failed: %s", exc)


# ---------------------------------------------------------------------------
# Referral codes  (mirror to Supabase for restart recovery)
# ---------------------------------------------------------------------------

def sb_mirror_referral_code(code: str, owner_id: str, owner_email: str,
                              max_uses: int = 50, reward_tier: str = "tier1") -> None:
    """
    Persist a user-generated referral code to Supabase referral_codes table.
    Called whenever a new code is created so it survives Render restarts.
    """
    sb = get_supabase()
    if not sb:
        return
    try:
        sb.table("referral_codes").upsert({
            "code":        code.upper(),
            "owner_id":    owner_id,
            "owner_email": owner_email.lower(),
            "max_uses":    max_uses,
            "reward_tier": reward_tier,
            "uses":        0,
            "bonus_balance": 0.0,
        }, on_conflict="code").execute()
        logger.debug("Mirrored referral code %s to Supabase", code)
    except Exception as exc:
        logger.debug("sb_mirror_referral_code failed for %s: %s", code, exc)


def sb_update_referral_stats(code: str, uses: int, bonus_balance: float) -> None:
    """Update the uses and bonus_balance for a referral code in Supabase."""
    sb = get_supabase()
    if not sb:
        return
    try:
        sb.table("referral_codes").update({
            "uses":          uses,
            "bonus_balance": bonus_balance,
        }).eq("code", code.upper()).execute()
    except Exception as exc:
        logger.debug("sb_update_referral_stats failed for %s: %s", code, exc)
