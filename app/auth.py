"""
Google OAuth authentication for MyPy Tutor.

Flow:
  1. Frontend loads Google Identity Services (GSI) script.
  2. User clicks "Sign in with Google" — Google returns a JWT id_token.
  3. Frontend POSTs the id_token to /auth/google.
  4. Backend verifies it with google-auth, extracts user info.
  5. Backend issues a signed session token (itsdangerous) and returns it.
  6. Frontend stores the session token in localStorage and sends it as
     Authorization: Bearer <token> on every request.
  7. Backend's get_current_user() dependency validates the token and
     returns the UserAccount.
"""

import os
import time
import logging
from typing import Optional

from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from app.models import UserAccount

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
SESSION_SECRET   = os.getenv("SESSION_SECRET", "change-me-in-production-32-chars-min")
SESSION_MAX_AGE  = 60 * 60 * 24 * 30   # 30 days in seconds

_serializer = URLSafeTimedSerializer(SESSION_SECRET)
_bearer     = HTTPBearer(auto_error=False)

# In-memory user store: { learner_id: UserAccount }
# Replace with a database in production.
_users: dict[str, UserAccount] = {}


# ---------------------------------------------------------------------------
# Session tokens
# ---------------------------------------------------------------------------

def create_session_token(learner_id: str) -> str:
    """Sign and return a session token encoding the learner_id."""
    return _serializer.dumps(learner_id, salt="session")


def verify_session_token(token: str) -> str:
    """
    Verify and decode a session token.
    Returns learner_id or raises HTTPException 401.
    """
    try:
        learner_id = _serializer.loads(token, salt="session", max_age=SESSION_MAX_AGE)
        return learner_id
    except SignatureExpired:
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    except BadSignature:
        raise HTTPException(status_code=401, detail="Invalid session token.")


# ---------------------------------------------------------------------------
# Google ID token verification
# ---------------------------------------------------------------------------

def verify_google_token(credential: str) -> dict:
    """
    Verify a Google JWT id_token from the GSI one-tap flow.
    Returns the decoded payload dict.
    Raises HTTPException 401 on failure.
    """
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=503,
            detail="Google authentication is not configured on this server.",
        )
    try:
        payload = google_id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )
        return payload
    except ValueError as exc:
        logger.warning("Google token verification failed: %s", exc)
        raise HTTPException(status_code=401, detail="Invalid Google credential.")


# ---------------------------------------------------------------------------
# User store helpers
# ---------------------------------------------------------------------------

def get_or_create_user(google_payload: dict) -> UserAccount:
    """
    Look up a user by Google sub (unique ID).
    Creates a new UserAccount on first login.
    """
    sub        = google_payload["sub"]              # Google's unique user ID
    email      = google_payload.get("email", "")
    name       = google_payload.get("name", email.split("@")[0])
    picture    = google_payload.get("picture", "")
    learner_id = f"g_{sub}"                         # prefix to avoid collision with anonymous ids

    if learner_id not in _users:
        _users[learner_id] = UserAccount(
            learner_id=learner_id,
            email=email,
            name=name,
            picture=picture,
            google_sub=sub,
        )
        logger.info("New user registered: %s (%s)", name, email)
    else:
        # Refresh mutable fields on each login
        user = _users[learner_id]
        user.name    = name
        user.picture = picture
        user.email   = email

    return _users[learner_id]


def get_user_by_id(learner_id: str) -> Optional[UserAccount]:
    return _users.get(learner_id)


# ---------------------------------------------------------------------------
# FastAPI dependency — optional auth
# ---------------------------------------------------------------------------

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Optional[UserAccount]:
    """
    Optional auth dependency. Returns UserAccount if a valid Bearer token is
    present, otherwise returns None (anonymous access allowed).
    """
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
    """
    Strict auth dependency. Raises 401 if not authenticated.
    Use this when a route must be protected.
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required.")
    learner_id = verify_session_token(credentials.credentials)
    user = get_user_by_id(learner_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found. Please sign in again.")
    return user
