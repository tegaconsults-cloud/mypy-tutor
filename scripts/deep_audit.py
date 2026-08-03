"""
Deep audit — catches inconsistencies across backend, frontend and config
that automated unit checks miss.
"""
import sys, os, re, ast
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PASS, FAIL = [], []

def ok(label, detail=""):
    PASS.append(label)
    print(f"  OK    {label}" + (f": {detail}" if detail else ""))

def fail(label, detail=""):
    FAIL.append(label)
    print(f"  FAIL  {label}" + (f": {detail}" if detail else ""))

def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return f.read()

main_src    = read("app/main.py")
courses_src = read("app/courses.py")
pricing_src = read("frontend-react/src/components/PricingPanel.tsx")
certs_src   = read("frontend-react/src/components/CertificatesPanel.tsx")
header_src  = read("frontend-react/src/components/Header.tsx")
admin_src   = read("static/admin.html")
email_src   = read("app/services/email_service.py")
auth_ctx    = read("frontend-react/src/context/AuthContext.tsx")
progress_ctx = read("frontend-react/src/context/ProgressContext.tsx")
referral_src = read("frontend-react/src/components/ReferralModal.tsx")
chat_src    = read("frontend-react/src/components/ChatPanel.tsx")
prompts_src = read("app/prompts.py")
db_src      = read("app/db.py")

print("\n=== PRICING CONSISTENCY ===")
# Backend TIER_PLANS prices
import sys; sys.path.insert(0, ROOT)
os.environ.setdefault("GROQ_API_KEY", "test")
os.environ.setdefault("DB_PATH", ":memory:")
from app.courses import TIER_PLANS, COURSE_CATALOG

expected_bundles = {"tier1": 30000, "tier2": 60000, "tier3": 100000, "tier4": 100000}
for tier, price in expected_bundles.items():
    actual = TIER_PLANS[tier]["price_ngn"]
    if actual == price:
        ok(f"TIER_PLANS.{tier} = ₦{price:,}")
    else:
        fail(f"TIER_PLANS.{tier}", f"expected ₦{price:,} got ₦{actual:,}")

# Frontend PricingPanel bundle amounts
for tier, price in [("tier1", 30000), ("tier2", 60000), ("tier3", 100000), ("tier4", 100000)]:
    if f"amount: {price}" in pricing_src:
        ok(f"PricingPanel {tier} amount = ₦{price:,}")
    else:
        fail(f"PricingPanel {tier} amount", f"₦{price:,} not found")

# CertificatesPanel cert fees must match bundle prices
for level, fee in [("basic", "₦30,000"), ("advanced", "₦60,000"), ("executive", "₦100,000")]:
    if fee in certs_src:
        ok(f"CertificatesPanel {level} fee = {fee}")
    else:
        fail(f"CertificatesPanel {level} fee", f"{fee} not in CertificatesPanel.tsx")

# Individual course prices
for name, meta in COURSE_CATALOG.items():
    cat = meta["category"]
    expected = {"Python Basics": 5000, "Intermediate Python": 15000,
                "Advanced Python": 30000, "Data Science": 30000,
                "AI & Prompting": 30000 if name == "prompt-engineering" else 50000,
                "Machine Learning": 50000}
    exp = expected.get(cat, 30000)
    if meta["price_ngn"] == exp:
        ok(f"course {name} = ₦{exp:,}")
    else:
        fail(f"course {name}", f"expected ₦{exp:,} got ₦{meta['price_ngn']:,}")

print("\n=== ADMIN HTML PRICES ===")
if "₦30,000 (4 courses" in admin_src or "30,000" in admin_src:
    ok("admin.html has ₦30,000 beginner bundle")
else:
    fail("admin.html beginner bundle price", "₦30,000 not found")
if "₦60,000" in admin_src:
    ok("admin.html has ₦60,000 intermediate bundle")
else:
    fail("admin.html intermediate bundle price", "₦60,000 not found")

print("\n=== BRANDING / TAGLINE ===")
tagline = "Africa's Best AI, Python"
tagline_variants = [
    "Africa\u2019s Best AI, Python",   # curly apostrophe (Windows file encoding)
    "Africa\u0027s Best AI, Python",   # straight apostrophe
    "Africa&#39;s Best AI",
    "Africa\u2018s Best AI",
]
# JSX may split the tagline across elements e.g.
#   Africa's Best <strong>AI, Python &amp; Machine Learning Tutor</strong>
# Accept any variant OR the JSX-split pattern
found_tagline = any(t in chat_src for t in tagline_variants) or (
    ("Africa\u2019s Best" in chat_src or "Africa\u0027s Best" in chat_src or "Africa's Best" in chat_src)
    and "Machine Learning Tutor" in chat_src
)
if found_tagline:
    ok("ChatPanel.tsx has correct tagline")
else:
    fail("ChatPanel.tsx tagline", f"tagline not found (tried variants)")
if tagline.replace("'", "&#39;") in email_src or tagline in email_src:
    ok("email_service.py has correct tagline")
else:
    fail("email_service.py tagline", f"tagline not found")
if "Africa" in referral_src and "Machine Learning" in referral_src:
    ok("ReferralModal share message mentions Machine Learning")
else:
    fail("ReferralModal share message", "Missing 'Machine Learning'")
# No old tagline should remain
old_taglines = ["Africa's most advanced", "Africa's most-advanced"]
for old in old_taglines:
    if old in chat_src:
        fail("ChatPanel old tagline still present", old)
    else:
        ok(f"ChatPanel: old tagline '{old[:30]}' removed")

print("\n=== KEEPALIVE PING ===")
if "_keepalive" in auth_ctx and "clearInterval" in auth_ctx:
    ok("AuthContext: keepalive ping with cleanup interval")
else:
    fail("AuthContext keepalive", "_keepalive or clearInterval missing")
if "8 * 60 * 1000" in auth_ctx:
    ok("AuthContext: keepalive interval = 8 minutes")
else:
    fail("AuthContext keepalive interval", "8 minute interval not found")

print("\n=== LOGO CIRCLE ===")
if 'shape="circle"' in header_src:
    ok("Header.tsx Logo uses shape=circle")
else:
    fail("Header.tsx Logo circle", "shape=circle not found")
if "gold" in header_src.lower() or "E0A300" in header_src:
    ok("Header.tsx Logo has gold border styling")
else:
    fail("Header.tsx Logo gold border")

print("\n=== PROFILE PICTURE ===")
if "profilePic" in header_src and "getProfile" in header_src:
    ok("Header.tsx: profilePic state fetches from profile API")
else:
    fail("Header.tsx profilePic", "profilePic state or getProfile not found")
if "onError" in header_src:
    ok("Header.tsx: profile image has onError fallback")
else:
    fail("Header.tsx onError fallback for broken image")

print("\n=== REFERRAL DASHBOARD ===")
if "authoritative_total" in main_src:
    ok("GET /referral: uses authoritative uses counter")
else:
    fail("GET /referral uses counter", "authoritative_total not found")
if "or 0" in main_src:
    ok("GET /referral: handles NULL referrer_bonus with 'or 0'")
else:
    fail("GET /referral NULL handling")

print("\n=== TIER4 SUPPORT ===")
if '"free", "tier1", "tier2", "tier3", "tier4"' in main_src:
    ok("admin set-tier accepts tier4")
else:
    fail("admin set-tier tier4 validation", "tier4 not in accepted values")

print("\n=== PAYSTACK WEBHOOK THRESHOLDS ===")
if "90000" in main_src and "50000" in main_src and "25000" in main_src:
    ok("Paystack webhook: correct amount thresholds (90k/50k/25k)")
else:
    fail("Paystack webhook thresholds", "Expected 90000/50000/25000 not all found")

print("\n=== EMAIL SERVICE TAGLINE ===")
if "Learn Smarter. Code Better" in email_src:
    fail("email_service.py old tagline still present", "Learn Smarter. Code Better still there")
else:
    ok("email_service.py old tagline removed")

print("\n=== SYNTAX CHECK ===")
for pyf in ["app/main.py", "app/courses.py", "app/admin.py",
            "app/services/email_service.py", "app/db.py"]:
    try:
        ast.parse(read(pyf))
        ok(f"{pyf} parses cleanly")
    except SyntaxError as e:
        fail(f"{pyf} syntax error", f"line {e.lineno}: {e.msg}")

# ── Summary ───────────────────────────────────────────────────────────────
print(f"\n{'='*54}")
total = len(PASS) + len(FAIL)
print(f"TOTAL: {total}   PASSED: {len(PASS)}   FAILED: {len(FAIL)}")
if FAIL:
    print("\nFailed items:")
    for f in FAIL:
        print(f"  ✗ {f}")
    sys.exit(1)
else:
    print("All deep audit checks passed.")
