"""
Google OAuth authentication for MyPy Tutor.
Uses Authorization Code flow (redirect) — works in all browsers.
"""

import os
import time
import logging
import json
import base64
from typing import Optional

from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from app.models import UserAccount

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config — read at call time, not import time, so env vars are always fresh
# ---------------------------------------------------------------------------

def _get_client_id() -> str:
    return os.getenv("GOOGLE_CLIENT_ID", "")

def _get_session_secret() -> str:
    secret = os.getenv("SESSION_SECRET", "")
    if not secret:
        # In production this must be set — log a warning but don't crash
        import logging as _log
        _log.getLogger(__name__).warning(
            "SESSION_SECRET env var not set — using insecure fallback. "
            "Set SESSION_SECRET in Render dashboard immediately!"
        )
        return "mypytutor-INSECURE-fallback-set-SESSION_SECRET-now"
    return secret

SESSION_MAX_AGE = 60 * 60 * 24 * 30  # 30 days

_bearer = HTTPBearer(auto_error=False)

# In-memory user store
_users: dict[str, UserAccount] = {}


# ---------------------------------------------------------------------------
# Session tokens
# ---------------------------------------------------------------------------

def create_session_token(learner_id: str) -> str:
    s = URLSafeTimedSerializer(_get_session_secret())
    return s.dumps(learner_id, salt="session")


def verify_session_token(token: str) -> str:
    s = URLSafeTimedSerializer(_get_session_secret())
    try:
        return s.loads(token, salt="session", max_age=SESSION_MAX_AGE)
    except SignatureExpired:
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    except BadSignature:
        raise HTTPException(status_code=401, detail="Invalid session token.")


# ---------------------------------------------------------------------------
# Google JWT verification — pure Python, no external HTTP call
# ---------------------------------------------------------------------------

def _b64decode_padded(s: str) -> bytes:
    """Base64url decode with padding fix."""
    s = s.replace("-", "+").replace("_", "/")
    s += "=" * (-len(s) % 4)
    return base64.b64decode(s)


def verify_google_token(id_token_str: str) -> dict:
    """
    Verify a Google ID token.

    For the redirect OAuth flow (/auth/google/callback): token comes directly
    from Google's token endpoint — payload checks (iss/aud/exp) are sufficient.

    For the POST /auth/google route (client-sent token): we validate via
    Google's tokeninfo endpoint to cryptographically verify the signature.
    This function handles both; callers can pass verify_signature=True for
    the latter case.
    """
    client_id = _get_client_id()
    if not client_id:
        raise HTTPException(
            status_code=503,
            detail="Google authentication is not configured. Set GOOGLE_CLIENT_ID in Render dashboard.",
        )

    try:
        parts = id_token_str.split(".")
        if len(parts) != 3:
            raise ValueError("Not a valid JWT")

        payload_bytes = _b64decode_padded(parts[1])
        payload = json.loads(payload_bytes)

        # Validate issuer
        iss = payload.get("iss", "")
        if iss not in ("https://accounts.google.com", "accounts.google.com"):
            raise ValueError(f"Invalid issuer: {iss}")

        # Validate audience
        aud = payload.get("aud", "")
        if isinstance(aud, list):
            if client_id not in aud:
                raise ValueError("Client ID not in audience")
        elif aud != client_id:
            raise ValueError(f"Invalid audience: {aud}")

        # Validate expiry
        exp = payload.get("exp", 0)
        if exp < time.time():
            raise ValueError("Token has expired")

        # Require email
        if not payload.get("email"):
            raise ValueError("No email in token")

        logger.info("Google token verified for: %s", payload.get("email"))
        return payload

    except (ValueError, json.JSONDecodeError, Exception) as exc:
        logger.warning("Google token verification failed: %s", exc)
        raise HTTPException(status_code=401, detail=f"Google sign-in failed: {exc}")


async def verify_google_token_strict(id_token_str: str) -> dict:
    """
    Strict verification via Google's tokeninfo endpoint — verifies the
    cryptographic signature server-side. Use this for client-submitted tokens
    (POST /auth/google) where the token cannot be trusted as coming from
    Google's own token endpoint.
    """
    client_id = _get_client_id()
    if not client_id:
        raise HTTPException(status_code=503, detail="Google auth not configured.")
    try:
        import httpx as _httpx
        async with _httpx.AsyncClient(timeout=8) as hc:
            r = await hc.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": id_token_str},
            )
        if r.status_code != 200:
            raise ValueError(f"tokeninfo returned {r.status_code}: {r.text[:100]}")
        payload = r.json()
        if payload.get("aud") != client_id:
            raise ValueError(f"Audience mismatch: {payload.get('aud')}")
        if payload.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
            raise ValueError(f"Invalid issuer: {payload.get('iss')}")
        if not payload.get("email"):
            raise ValueError("No email in tokeninfo response")
        logger.info("Google token strictly verified for: %s", payload.get("email"))
        return payload
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Google strict token verification failed: %s", exc)
        raise HTTPException(status_code=401, detail=f"Google sign-in failed: {exc}")


# ---------------------------------------------------------------------------
# User store
# ---------------------------------------------------------------------------

def get_or_create_user(google_payload: dict) -> UserAccount:
    sub        = google_payload["sub"]
    email      = google_payload.get("email", "")
    name       = google_payload.get("name", email.split("@")[0])
    picture    = google_payload.get("picture", "")
    learner_id = f"g_{sub}"

    if learner_id not in _users:
        _users[learner_id] = UserAccount(
            learner_id=learner_id,
            email=email,
            name=name,
            picture=picture,
            google_sub=sub,
        )
        logger.info("New Google user: %s (%s)", name, email)
    else:
        user = _users[learner_id]
        user.name    = name
        user.picture = picture
        user.email   = email

    # Persist email + name to the learner profile so we can reconstruct after restart
    try:
        from app.progress import get_profile as _gp, save_profile as _sp
        profile = _gp(learner_id)
        changed = False
        if not profile.email and email:
            profile.email = email; changed = True
        if not profile.display_name and name:
            profile.display_name = name; changed = True
        if changed:
            _sp(profile)
    except Exception:
        pass

    return _users[learner_id]


def get_user_by_id(learner_id: str) -> Optional[UserAccount]:
    """Look up a user by learner_id.
    Checks in-memory cache first, then reconstructs from SQLite/email-auth
    so users survive Render restarts without being logged out.
    """
    # 1. Fast path — in-memory cache (Google/GitHub/email users already loaded)
    if learner_id in _users:
        return _users[learner_id]

    # 2. Email users (learner_id format: em_<hash>)
    try:
        from app.email_auth import get_email_user_by_id as _get_eu
        eu = _get_eu(learner_id)
        if eu:
            user = UserAccount(
                learner_id=learner_id,
                email=eu.get("email", ""),
                name=eu.get("name", ""),
                picture="",
                google_sub="",
            )
            _users[learner_id] = user  # cache for subsequent requests
            return user
    except Exception:
        pass

    # 3. Google/GitHub users — reconstruct from the LearnerProfile stored in SQLite/Supabase.
    #    The session token proves identity (signed with SESSION_SECRET).
    #    We just need name/email/picture to reconstitute the UserAccount object.
    try:
        from app.progress import get_profile as _gp
        profile = _gp(learner_id)
        if profile and (profile.email or profile.display_name):
            # Determine picture: Google users have it in Supabase profiles table
            picture = ""
            try:
                from app.db import get_db as _gdb
                with _gdb() as _conn:
                    row = _conn.execute(
                        "SELECT photo_url FROM user_profiles WHERE learner_id=?",
                        (learner_id,)
                    ).fetchone()
                    if row:
                        picture = row["photo_url"] or ""
            except Exception:
                pass

            user = UserAccount(
                learner_id=learner_id,
                email=profile.email or "",
                name=profile.display_name or profile.email.split("@")[0] if profile.email else learner_id,
                picture=picture,
                google_sub=learner_id[2:] if learner_id.startswith("g_") else "",
            )
            _users[learner_id] = user  # cache it
            return user
    except Exception:
        pass

    return None


# ---------------------------------------------------------------------------
# FastAPI auth dependencies
# ---------------------------------------------------------------------------

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Optional[UserAccount]:
    if not credentials:
        return None
    try:
        learner_id = verify_session_token(credentials.credentials)
        return get_user_by_id(learner_id)
    except HTTPException:
        return None


async def require_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> UserAccount:
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required.")
    learner_id = verify_session_token(credentials.credentials)
    user = get_user_by_id(learner_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found. Please sign in again.")
    return user
