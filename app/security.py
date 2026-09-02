"""
Security middleware and utilities for MyPy Tutor.

Covers:
- Rate limiting (per-IP, sliding window, in-memory)
- Input sanitisation and size guards
- Security response headers
- learner_id / param validation
"""

import re
import time
import logging
from collections import defaultdict, deque

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Rate limit: max requests per window per IP
RATE_LIMIT_REQUESTS = 30          # max calls
RATE_LIMIT_WINDOW   = 60          # per 60 seconds

# Strict limits for expensive LLM endpoints
LLM_RATE_LIMIT_REQUESTS = 10      # max LLM calls
LLM_RATE_LIMIT_WINDOW   = 60      # per 60 seconds

LLM_ENDPOINTS = {"/chat", "/quiz/generate", "/quiz/answer",
                 "/course/start", "/course/next", "/exercise/generate"}

# Auth endpoints — strict brute-force protection
AUTH_ENDPOINTS           = {"/auth/signin", "/auth/signup", "/admin/login"}
AUTH_RATE_LIMIT_REQUESTS = 10     # max 10 attempts
AUTH_RATE_LIMIT_WINDOW   = 300    # per 5 minutes per IP

# Enquiry endpoint — strict throttle to prevent inbox spam
ENQUIRY_ENDPOINTS            = {"/enquiry"}
ENQUIRY_RATE_LIMIT_REQUESTS  = 3      # max 3 enquiries
ENQUIRY_RATE_LIMIT_WINDOW    = 3600   # per hour per IP

# Input size limits
MAX_MESSAGE_LEN     = 8_000       # characters in a single user message — matches ChatRequest.message max_length
MAX_CODE_LEN        = 8_000       # characters of pasted code (embedded in message)
MAX_HISTORY_ITEMS   = 20          # max conversation turns sent per request
MAX_HISTORY_MSG_LEN = 2_000       # characters per history message — trimmed to prevent token bloat

# Allowed field values
ALLOWED_LEVELS  = {"beginner", "intermediate", "advanced"}
LEARNER_ID_RE   = re.compile(r"^[a-zA-Z0-9_\-]{1,64}$")
COURSE_NAME_RE  = re.compile(r"^[a-zA-Z0-9_\-]{1,80}$")
TOPIC_RE        = re.compile(r"^[a-zA-Z0-9 _\-&/]{1,100}$")

# Free tier daily prompt limit — resets at 5am WAT (UTC+1)
FREE_DAILY_LIMIT = 20

# ---------------------------------------------------------------------------
# In-memory rate limit stores
# { ip: deque of timestamps } — capped at 10k unique IPs to prevent memory growth
# ---------------------------------------------------------------------------

_general_store: dict[str, deque] = defaultdict(deque)
_llm_store:     dict[str, deque] = defaultdict(deque)
_auth_store:    dict[str, deque] = defaultdict(deque)   # brute-force protection
_enquiry_store: dict[str, deque] = defaultdict(deque)   # enquiry spam protection
_RATE_STORE_MAX = 10_000

# Per-store locks — _check_rate is called from async handlers running on threads;
# without a lock, two concurrent requests can both pass the len(dq) < limit check
# simultaneously, defeating brute-force protection on auth endpoints.
_general_lock: threading.Lock = threading.Lock()
_llm_lock:     threading.Lock = threading.Lock()
_auth_lock:    threading.Lock = threading.Lock()
_enquiry_lock: threading.Lock = threading.Lock()

# Map each store to its lock (populated at module load time)
_STORE_LOCKS: dict[int, threading.Lock] = {}

# Register all four stores immediately after creation
def _register_stores() -> None:
    _STORE_LOCKS[id(_general_store)] = _general_lock
    _STORE_LOCKS[id(_llm_store)]     = _llm_lock
    _STORE_LOCKS[id(_auth_store)]    = _auth_lock
    _STORE_LOCKS[id(_enquiry_store)] = _enquiry_lock

_register_stores()


def _evict_rate_store(store: dict) -> None:
    """Drop the 20% of entries whose most-recent timestamp is oldest."""
    if len(store) > _RATE_STORE_MAX:
        evict_count = _RATE_STORE_MAX // 5
        sorted_keys = sorted(
            store.keys(),
            key=lambda k: store[k][-1] if store[k] else 0,
        )
        for key in sorted_keys[:evict_count]:
            store.pop(key, None)


def _check_rate(store: dict, ip: str, limit: int, window: int) -> bool:
    """Return True if request is allowed, False if rate-limited.
    Thread-safe: each store has a dedicated lock so concurrent requests
    cannot both sneak through the len(dq) < limit check simultaneously."""
    # Resolve the lock for this store at call time
    lock = _STORE_LOCKS.get(id(store))
    if lock is None:
        # Fallback: create and register a lock for any unregistered store
        lock = threading.Lock()
        _STORE_LOCKS[id(store)] = lock
    with lock:
        now = time.monotonic()
        dq  = store[ip]
        while dq and dq[0] < now - window:
            dq.popleft()
        if len(dq) >= limit:
            return False
        dq.append(now)
        _evict_rate_store(store)
    return True


# ---------------------------------------------------------------------------
# Free-tier daily prompt counter
# Write-through cache: memory first for speed; every mutation also written to
# SQLite so counts survive Render restarts.
# ---------------------------------------------------------------------------

import datetime as _dt

# { key -> (date_str, count) }
_daily_prompt_store: dict[str, tuple[str, int]] = {}
_prompt_store_loaded: bool = False


def _ensure_prompt_store_loaded() -> None:
    """Load today's counts from SQLite once per process startup."""
    global _daily_prompt_store, _prompt_store_loaded
    if _prompt_store_loaded:
        return
    try:
        today = _wat_date_key()
        from app.db import load_todays_prompt_counts, purge_old_prompt_counts
        counts = load_todays_prompt_counts(today)
        for k, c in counts.items():
            _daily_prompt_store[k] = (today, c)
        import datetime as _dt2
        yesterday = (_dt2.date.today() - _dt2.timedelta(days=1)).isoformat()
        purge_old_prompt_counts(yesterday)
    except Exception:
        pass
    _prompt_store_loaded = True


def _wat_date_key() -> str:
    """
    Return today's date string in WAT (UTC+1), reset at 5am WAT.
    Prompts used between 00:00-04:59 WAT count toward the previous day's quota.
    """
    wat_now = _dt.datetime.utcnow() + _dt.timedelta(hours=1)
    if wat_now.hour < 5:
        wat_now = wat_now - _dt.timedelta(days=1)
    return wat_now.strftime("%Y-%m-%d")


def check_free_prompt_limit(learner_id: str, ip: str) -> tuple[bool, int]:
    """Check if a free-tier user has exceeded their daily limit.
    Returns (allowed: bool, used_count: int)."""
    _ensure_prompt_store_loaded()
    key   = learner_id if learner_id and learner_id != "default" else f"ip_{ip}"
    today = _wat_date_key()

    existing = _daily_prompt_store.get(key)
    if existing is None or existing[0] != today:
        try:
            from app.db import get_daily_prompt_count_db
            db_count = get_daily_prompt_count_db(key, today)
        except Exception:
            db_count = 0
        if db_count >= FREE_DAILY_LIMIT:
            _daily_prompt_store[key] = (today, db_count)
            return False, db_count
        _daily_prompt_store[key] = (today, db_count)
        return True, db_count

    _, count = existing
    if count >= FREE_DAILY_LIMIT:
        return False, count
    return True, count


def increment_free_prompt_count(learner_id: str, ip: str) -> int:
    """Increment daily prompt counter in memory and SQLite. Returns new count."""
    _ensure_prompt_store_loaded()
    key   = learner_id if learner_id and learner_id != "default" else f"ip_{ip}"
    today = _wat_date_key()

    try:
        from app.db import increment_daily_prompt_count_db
        new_count = increment_daily_prompt_count_db(key, today)
    except Exception:
        existing  = _daily_prompt_store.get(key)
        new_count = ((existing[1] + 1) if existing and existing[0] == today else 1)

    _daily_prompt_store[key] = (today, new_count)
    return new_count


def get_free_prompt_count(learner_id: str, ip: str) -> int:
    """Get current daily prompt count. Checks memory first, then SQLite."""
    _ensure_prompt_store_loaded()
    key   = learner_id if learner_id and learner_id != "default" else f"ip_{ip}"
    today = _wat_date_key()

    existing = _daily_prompt_store.get(key)
    if existing and existing[0] == today:
        return existing[1]

    try:
        from app.db import get_daily_prompt_count_db
        count = get_daily_prompt_count_db(key, today)
        _daily_prompt_store[key] = (today, count)
        return count
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Single middleware that applies:
    1. General rate limiting (all routes)
    2. Auth endpoint brute-force protection
    3. Stricter LLM rate limiting (AI endpoints)
    4. Enquiry spam protection
    5. Security response headers
    """

    async def dispatch(self, request: Request, call_next):
        ip = _get_ip(request)

        # Skip rate limiting for CORS preflight requests
        if request.method == "OPTIONS":
            response = await call_next(request)
            return response

        # 1. General rate limit
        if not _check_rate(_general_store, ip, RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW):
            logger.warning("General rate limit hit: %s", ip)
            return JSONResponse(
                status_code=429,
                content={"error": "Too many requests. Please slow down."},
                headers={"Retry-After": str(RATE_LIMIT_WINDOW)},
            )

        # 2. Auth endpoint brute-force protection
        if request.url.path in AUTH_ENDPOINTS:
            if not _check_rate(_auth_store, ip, AUTH_RATE_LIMIT_REQUESTS, AUTH_RATE_LIMIT_WINDOW):
                logger.warning("Auth brute-force blocked: %s %s", ip, request.url.path)
                return JSONResponse(
                    status_code=429,
                    content={"error": "Too many login attempts. Please wait 5 minutes."},
                    headers={"Retry-After": str(AUTH_RATE_LIMIT_WINDOW)},
                )

        # 3. LLM-endpoint rate limit
        if request.url.path in LLM_ENDPOINTS:
            if not _check_rate(_llm_store, ip, LLM_RATE_LIMIT_REQUESTS, LLM_RATE_LIMIT_WINDOW):
                logger.warning("LLM rate limit hit: %s %s", ip, request.url.path)
                return JSONResponse(
                    status_code=429,
                    content={"error": "Too many AI requests. Wait a moment before trying again."},
                    headers={"Retry-After": str(LLM_RATE_LIMIT_WINDOW)},
                )

        # 4. Enquiry spam protection
        if request.url.path in ENQUIRY_ENDPOINTS:
            if not _check_rate(_enquiry_store, ip, ENQUIRY_RATE_LIMIT_REQUESTS, ENQUIRY_RATE_LIMIT_WINDOW):
                logger.warning("Enquiry spam blocked: %s", ip)
                return JSONResponse(
                    status_code=429,
                    content={"error": "Too many enquiries. Please wait before sending another."},
                    headers={"Retry-After": str(ENQUIRY_RATE_LIMIT_WINDOW)},
                )

        response = await call_next(request)

        # 5. Security headers on every response
        response.headers["X-Content-Type-Options"]  = "nosniff"
        response.headers["X-Frame-Options"]         = "DENY"
        response.headers["X-XSS-Protection"]        = "1; mode=block"
        response.headers["Referrer-Policy"]         = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"]      = "geolocation=(), microphone=(), camera=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' "
            "https://cdn.jsdelivr.net "
            "https://cdnjs.cloudflare.com "
            "https://accounts.google.com "
            "https://www.googletagmanager.com "
            "https://www.google-analytics.com; "
            "style-src 'self' 'unsafe-inline' "
            "https://cdnjs.cloudflare.com "
            "https://accounts.google.com "
            "https://fonts.googleapis.com; "
            "font-src 'self' "
            "https://cdnjs.cloudflare.com "
            "https://fonts.gstatic.com; "
            "img-src 'self' data: "
            "https://mypytutor.onrender.com "
            "https://www.google-analytics.com "
            "https://www.googletagmanager.com "
            "https://lh3.googleusercontent.com "
            "https://avatars.githubusercontent.com; "
            "connect-src 'self' "
            "https://mypytutor.onrender.com "
            "https://mypytutor.com.ng "
            "https://www.mypytutor.com.ng "
            "https://cdn.jsdelivr.net "
            "https://cdnjs.cloudflare.com "
            "https://accounts.google.com "
            "https://www.google-analytics.com "
            "https://analytics.google.com "
            "https://region1.google-analytics.com "
            "https://www.googletagmanager.com "
            "https://oauth2.googleapis.com "
            "https://fonts.googleapis.com "
            "https://fonts.gstatic.com "
            "https://lh3.googleusercontent.com "
            "https://avatars.githubusercontent.com "
            "https://api.github.com; "
            "frame-src https://accounts.google.com; "
            "worker-src 'self';"
        )
        if "server" in response.headers:
            del response.headers["server"]
        if "x-powered-by" in response.headers:
            del response.headers["x-powered-by"]

        return response


def _get_ip(request: Request) -> str:
    """Extract real client IP, respecting Render's X-Forwarded-For header.
    Only trusts the first hop — prevents spoofing via crafted header values."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # Take only the first (leftmost) IP — that is the real client.
        # Subsequent entries are proxies we don't control.
        first_ip = forwarded.split(",")[0].strip()
        # Basic sanity check: reject obviously invalid values
        if first_ip and not first_ip.startswith("unknown"):
            return first_ip
    return request.client.host if request.client else "unknown"


# ---------------------------------------------------------------------------
# Input validators — called inside route handlers
# ---------------------------------------------------------------------------

def validate_learner_id(learner_id: str) -> str:
    """Sanitise and validate learner_id. Raises 400 on bad input."""
    if not LEARNER_ID_RE.match(learner_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid learner_id. Use only letters, numbers, hyphens, underscores (max 64 chars).",
        )
    return learner_id


def validate_level(level: str) -> str:
    """Validate level field. Raises 400 on unknown value."""
    if level not in ALLOWED_LEVELS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid level '{level}'. Must be one of: beginner, intermediate, advanced.",
        )
    return level


def validate_course_name(name: str) -> str:
    if not COURSE_NAME_RE.match(name):
        raise HTTPException(status_code=400, detail="Invalid course name.")
    return name


def validate_topic(topic: str) -> str:
    if not TOPIC_RE.match(topic):
        raise HTTPException(status_code=400, detail="Invalid topic.")
    return topic


def validate_chat_request(message: str, history: list, level: str, learner_id: str) -> None:
    """Full validation of a /chat request payload. Raises 400 on any violation."""
    if len(message) > MAX_MESSAGE_LEN:
        raise HTTPException(
            status_code=400,
            detail=f"Message too long. Maximum {MAX_MESSAGE_LEN} characters.",
        )
    if len(history) > MAX_HISTORY_ITEMS:
        raise HTTPException(
            status_code=400,
            detail=f"History too long. Maximum {MAX_HISTORY_ITEMS} messages.",
        )
    for i, msg in enumerate(history):
        if len(msg.content) > MAX_HISTORY_MSG_LEN:
            raise HTTPException(
                status_code=400,
                detail=f"History message {i} too long. Maximum {MAX_HISTORY_MSG_LEN} characters.",
            )
        if msg.role not in {"user", "assistant", "system"}:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid role '{msg.role}' in history.",
            )
    validate_level(level)
    validate_learner_id(learner_id)
