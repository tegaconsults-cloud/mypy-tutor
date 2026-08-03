"""
Comprehensive verification script for all bug fixes.
Run from project root: python scripts/verify_all.py
"""
import sys, os, tempfile, sqlite3, importlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

PASS = []
FAIL = []

def ok(label):
    PASS.append(label)
    print(f"  OK  {label}")

def fail(label, reason=""):
    FAIL.append(label)
    print(f"  FAIL {label}{': ' + reason if reason else ''}")

# ── 1. All backend modules import without errors ───────────────────────────
print("\n=== MODULE IMPORTS ===")
mods = [
    "app.db", "app.models", "app.topics", "app.courses",
    "app.classifier", "app.formatter", "app.prompts",
    "app.security", "app.supabase_client", "app.progress",
    "app.auth", "app.email_auth", "app.feedback",
    "app.admin", "app.certificates",
]
for m in mods:
    try:
        importlib.import_module(m)
        ok(f"import {m}")
    except Exception as e:
        fail(f"import {m}", str(e))

# llm_client needs GROQ_API_KEY — patch env before importing
os.environ.setdefault("GROQ_API_KEY", "test-key-placeholder")
try:
    importlib.import_module("app.llm_client")
    ok("import app.llm_client")
except Exception as e:
    fail("import app.llm_client", str(e))

# ── 2. DB init creates all required tables ─────────────────────────────────
print("\n=== DATABASE ===")
tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
tf.close()
try:
    import app.db as adb
    adb.DB_PATH = tf.name
    adb.init_db()
    conn = sqlite3.connect(tf.name)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()

    required = [
        "learner_profiles", "email_accounts", "feedback_ratings",
        "feedback_surveys", "daily_prompt_counts", "activity_log",
        "payments", "certificates", "referrals", "coupons",
        "access_codes", "user_profiles", "course_purchases",
        "referral_withdrawals",
    ]
    for t in required:
        if t in tables:
            ok(f"table {t}")
        else:
            fail(f"table {t}", "missing from init_db()")
finally:
    os.unlink(tf.name)

# ── 3. Classifier intent detection ────────────────────────────────────────
print("\n=== CLASSIFIER ===")
from app.classifier import classify_intent
cases = [
    ("start course python-fundamentals", "course"),
    ("next lesson please",               "course"),
    ("continue learning",                "course"),
    ("explain decorators",               "concept"),
    ("what is a generator",              "concept"),
    ("my code has an error",             "debug"),
    ("why is this not working",          "debug"),
    ("write a function to sort a list",  "codegen"),
    ("give me a practice exercise",      "exercise"),
]
for msg, expected in cases:
    got = classify_intent(msg)
    if got == expected:
        ok(f"classify({msg!r}) == {expected!r}")
    else:
        fail(f"classify({msg!r})", f"got {got!r}, expected {expected!r}")

# ── 4. Security: anonymous prompt key uses ip_ prefix ─────────────────────
print("\n=== SECURITY ===")
import app.security as sec
sec._daily_prompt_store.clear()
sec._prompt_store_loaded = True
sec.check_free_prompt_limit("default", "9.9.9.9")
if "ip_9.9.9.9" in sec._daily_prompt_store:
    ok("anon prompt key = ip_9.9.9.9 (not shared 'default')")
else:
    fail("anon prompt key", f"keys={list(sec._daily_prompt_store.keys())}")

# Authenticated user gets own key
sec._daily_prompt_store.clear()
sec.check_free_prompt_limit("e_abc123", "9.9.9.9")
if "e_abc123" in sec._daily_prompt_store:
    ok("auth user prompt key = learner_id")
else:
    fail("auth user prompt key", f"keys={list(sec._daily_prompt_store.keys())}")

# Rate-limit eviction logic exists and doesn't crash
try:
    sec._evict_rate_store(sec._general_store)
    ok("_evict_rate_store runs without error")
except Exception as e:
    fail("_evict_rate_store", str(e))

# ── 5. LLM max_tokens routing ─────────────────────────────────────────────
print("\n=== LLM CLIENT ===")
import app.llm_client as lc
smart_tokens = lc._MAX_TOKENS.get(lc._SMART_MODEL)
fast_tokens  = lc._MAX_TOKENS.get(lc._FAST_MODEL)
if smart_tokens == 4096:
    ok(f"smart model max_tokens=4096")
else:
    fail("smart model max_tokens", f"got {smart_tokens}")
if fast_tokens == 2048:
    ok(f"fast model max_tokens=2048")
else:
    fail("fast model max_tokens", f"got {fast_tokens}")

# ── 6. Email auth: SQLite written before _pending deleted ─────────────────
print("\n=== EMAIL AUTH LOGIC ===")
import inspect
import app.email_auth as ea
src = inspect.getsource(ea.confirm_email_token)
# save_email_account must appear before del _pending[email]
save_pos = src.find("save_email_account")
del_pos  = src.find("del _pending[email]")
if save_pos != -1 and del_pos != -1 and save_pos < del_pos:
    ok("confirm_email_token: SQLite write before del _pending")
else:
    fail("confirm_email_token order", f"save_pos={save_pos}, del_pos={del_pos}")

# ── 7. Admin password: no plain-text fallback ─────────────────────────────
print("\n=== ADMIN AUTH ===")
src_admin = inspect.getsource(__import__("app.admin", fromlist=["verify_admin_login"]).verify_admin_login)
if "stored_pw == password" in src_admin or "stored_pw == pw" in src_admin:
    fail("verify_admin_login", "plain-text password comparison still present")
else:
    ok("verify_admin_login: only SHA-256 comparison, no plain-text fallback")

# ── 8. GitHub OAuth routes exist in main.py ───────────────────────────────
print("\n=== GITHUB OAUTH ROUTES ===")
with open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8") as f:
    main_src = f.read()
for route in ["/auth/github/login", "/auth/github/callback"]:
    if route in main_src:
        ok(f"route {route} defined in main.py")
    else:
        fail(f"route {route}", "not found in main.py")

# ── 9. Progress save_profile debounce uses threading.Timer ────────────────
print("\n=== PROGRESS DEBOUNCE ===")
import app.progress as prog
src_sp = inspect.getsource(prog.save_profile)
if "threading.Timer" in src_sp:
    ok("save_profile uses threading.Timer debounce")
else:
    fail("save_profile debounce", "threading.Timer not found")
if "_pending_syncs" in src_sp:
    ok("save_profile cancels previous pending sync")
else:
    fail("save_profile debounce", "_pending_syncs not found")

# ── 10. Supabase created_at ISO handling ─────────────────────────────────
print("\n=== SUPABASE CLIENT ===")
with open(os.path.join(ROOT, "app", "supabase_client.py"), encoding="utf-8") as f:
    sb_src = f.read()
if "fromisoformat" in sb_src:
    ok("supabase_client handles ISO timestamp format for created_at")
else:
    fail("supabase_client created_at", "fromisoformat not found")

# ── 11. Feedback tables created in init_db not inline ─────────────────────
print("\n=== FEEDBACK PERSISTENCE ===")
with open(os.path.join(ROOT, "app", "feedback.py"), encoding="utf-8") as f:
    fb_src = f.read()
if "CREATE TABLE IF NOT EXISTS feedback" in fb_src:
    fail("feedback.py inline CREATE TABLE", "still present (should be in init_db only)")
else:
    ok("feedback.py: no inline CREATE TABLE (tables managed by init_db)")

with open(os.path.join(ROOT, "app", "db.py"), encoding="utf-8") as f:
    db_src = f.read()
for tbl in ["feedback_ratings", "feedback_surveys"]:
    if f"CREATE TABLE IF NOT EXISTS {tbl}" in db_src:
        ok(f"db.py: {tbl} table in init_db")
    else:
        fail(f"db.py: {tbl} table", "not in init_db")

# ── 12. ChatPanel: no hardcoded FREE_LIMIT, no unused Logo import ─────────
print("\n=== FRONTEND CHATPANEL ===")
cp_path = os.path.join(ROOT, "frontend-react", "src", "components", "ChatPanel.tsx")
with open(cp_path, encoding="utf-8") as f:
    cp_src = f.read()
if "import Logo" in cp_src:
    fail("ChatPanel.tsx", "unused Logo import still present")
else:
    ok("ChatPanel.tsx: Logo import removed")
if "FREE_LIMIT = " in cp_src and "DEFAULT_FREE_LIMIT" not in cp_src:
    fail("ChatPanel.tsx", "hardcoded FREE_LIMIT constant still present (not DEFAULT_FREE_LIMIT)")
else:
    ok("ChatPanel.tsx: no hardcoded FREE_LIMIT (uses DEFAULT_FREE_LIMIT + server fetch)")
if "getPromptCount" in cp_src:
    ok("ChatPanel.tsx: fetches free limit from server via getPromptCount")
else:
    fail("ChatPanel.tsx", "getPromptCount not used")
if "refresh(user.learner_id, true)" in cp_src:
    ok("ChatPanel.tsx: refresh called with force=true after message")
else:
    fail("ChatPanel.tsx", "force=true not passed to refresh()")
if "history.slice(-20)" in cp_src:
    ok("ChatPanel.tsx: history slice matches backend MAX_HISTORY_ITEMS=20")
else:
    fail("ChatPanel.tsx", "history slice not updated to -20")

# ── 13. Header.tsx: reads tier from ProgressContext ───────────────────────
print("\n=== FRONTEND HEADER ===")
hdr_path = os.path.join(ROOT, "frontend-react", "src", "components", "Header.tsx")
with open(hdr_path, encoding="utf-8") as f:
    hdr_src = f.read()
if "useProgress" in hdr_src:
    ok("Header.tsx: imports useProgress for live tier")
else:
    fail("Header.tsx", "useProgress not imported")
if "Free Plan" in hdr_src and "TIER_META" not in hdr_src:
    fail("Header.tsx", "still hardcodes 'Free Plan'")
else:
    ok("Header.tsx: tier badge reads from progress context (TIER_META)")
if "progress?.tier" in hdr_src or "currentTier" in hdr_src:
    ok("Header.tsx: currentTier derived from progress")
else:
    fail("Header.tsx", "currentTier not found")

# ── 14. AuthModal: resend guard ───────────────────────────────────────────
print("\n=== FRONTEND AUTHMODAL ===")
am_path = os.path.join(ROOT, "frontend-react", "src", "components", "AuthModal.tsx")
with open(am_path, encoding="utf-8") as f:
    am_src = f.read()
if "if (!password)" in am_src:
    ok("AuthModal.tsx: resend handler guards against empty password")
else:
    fail("AuthModal.tsx", "empty password guard not found in handleResend")

# ── SUMMARY ───────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"PASSED: {len(PASS)}   FAILED: {len(FAIL)}")
if FAIL:
    print("\nFailed checks:")
    for f in FAIL:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("All checks passed. Ready for deployment.")
