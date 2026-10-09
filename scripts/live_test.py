"""Live integration test — sign in as tegaconsults, test payment + cert."""
import urllib.request, urllib.error, json, sys

BASE = "https://mypytutor.onrender.com"

def api(method, path, body=None, token=None, timeout=30):
    url = BASE + path
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            ct = r.headers.get("Content-Type", "")
            raw = r.read()
            if "json" in ct:
                return r.status, json.loads(raw)
            return r.status, {"_html": len(raw), "_preview": raw[:300].decode("utf-8", errors="replace")}
    except urllib.error.HTTPError as e:
        try:
            ct = e.headers.get("Content-Type", "")
            raw = e.read()
            if "json" in ct:
                return e.code, json.loads(raw)
            return e.code, {"_html": len(raw), "_preview": raw[:300].decode("utf-8", errors="replace")}
        except Exception:
            return e.code, {"error": str(e)}
    except Exception as ex:
        return 0, {"error": str(ex)}

def show(label, status, data, hide=("token",)):
    ok = "OK " if 200 <= status < 300 else "ERR"
    print(f"\n[{ok} {status}] {label}")
    for k, v in data.items():
        if k in hide:
            val = "...{}".format(str(v)[-16:]) if v else "MISSING"
        else:
            val = str(v)[:300]
        print("       {}: {}".format(k, val))

# ── 1. Sign in ────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("TEST 1: Sign in")
status, data = api("POST", "/auth/signin", {
    "email": "tegaconsults@gmail.com",
    "password": "tegaconsults@gmail.com"
})
show("SIGNIN", status, data)
TOKEN = data.get("token", "")
LEARNER = data.get("learner_id", "")
if not TOKEN:
    print("\nABORT: no token."); sys.exit(1)

# ── 2. Auth me ───────────────────────────────────────────────────────────
print("\n" + "="*60)
print("TEST 2: Auth /me")
status, data = api("GET", "/auth/me", token=TOKEN)
show("AUTH/ME", status, data)

# ── 3. Paystack ₦2000 explicit ───────────────────────────────────────────
print("\n" + "="*60)
print("TEST 3: Paystack initialize — Prompt Starter ₦2,000 (explicit amount)")
status, data = api("POST", "/payments/paystack/initialize", {
    "learner_id":  LEARNER,
    "amount_ngn":  2000,
    "plan":        "Prompt Starter Plan",
    "course_name": "",
    "coupon_code": ""
}, token=TOKEN, timeout=25)
show("PAYSTACK INIT ₦2000", status, data)
if data.get("authorization_url"):
    print("   --> OPEN IN BROWSER: " + data["authorization_url"])

# ── 4. Auto-resolve: plan='prompt-starter' amount=0 ─────────────────────
print("\n" + "="*60)
print("TEST 4: Auto-resolve — plan='prompt-starter' amount=0")
status, data = api("POST", "/payments/paystack/initialize", {
    "learner_id":  LEARNER,
    "amount_ngn":  0,
    "plan":        "prompt-starter",
    "course_name": "",
    "coupon_code": ""
}, token=TOKEN, timeout=25)
show("PAYSTACK INIT auto-resolve prompt-starter", status, data)

# ── 5. Auto-resolve: plan='Prompt Starter Plan' amount=0 ─────────────────
print("\n" + "="*60)
print("TEST 5: Auto-resolve — plan='Prompt Starter Plan' amount=0")
status, data = api("POST", "/payments/paystack/initialize", {
    "learner_id":  LEARNER,
    "amount_ngn":  0,
    "plan":        "Prompt Starter Plan",
    "course_name": "",
    "coupon_code": ""
}, token=TOKEN, timeout=25)
show("PAYSTACK INIT auto-resolve Prompt Starter Plan", status, data)

# ── 6. Auto-resolve: tier1 amount=0 ──────────────────────────────────────
print("\n" + "="*60)
print("TEST 6: Auto-resolve — plan='tier1' amount=0")
status, data = api("POST", "/payments/paystack/initialize", {
    "learner_id":  LEARNER,
    "amount_ngn":  0,
    "plan":        "tier1",
    "course_name": "",
    "coupon_code": ""
}, token=TOKEN, timeout=25)
show("PAYSTACK INIT auto-resolve tier1", status, data)

# ── 7. Certificate preview ────────────────────────────────────────────────
print("\n" + "="*60)
print("TEST 7: Certificate preview — GET /certificate/basic")
status, data = api(
    "GET",
    "/certificate/basic?learner_id={}&name=Tega+Consults".format(LEARNER),
    token=TOKEN, timeout=25
)
if "_html" in data:
    preview = data.get("_preview", "")
    if "402" in str(status) or "locked" in preview.lower() or "certificate" in preview.lower():
        print("[OK  {}] CERT BASIC — HTML returned (len={})".format(status, data["_html"]))
        if "locked" in preview.lower() or status == 402:
            print("   --> LOCKED: user needs to purchase plan (expected for free tier)")
        else:
            print("   --> PREVIEW: {}".format(preview[:150]))
    else:
        print("[ERR {}] CERT BASIC — {}".format(status, preview[:200]))
else:
    show("CERT BASIC", status, data, hide=("html","content","svg","pdf"))

# ── 8. Bank transfer proof submission ─────────────────────────────────────
print("\n" + "="*60)
print("TEST 8: Submit bank transfer proof")
TINY_PNG = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAA"
    "DUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)
status, data = api("POST", "/payments/bank-transfer/submit", {
    "plan":               "Prompt Starter Plan",
    "amount":             2000,
    "reference":          "TEST-FINISH-003",
    "proof_image_base64": TINY_PNG,
    "notes":              "Finish-up live test"
}, token=TOKEN, timeout=25)
show("BANK TRANSFER SUBMIT", status, data)
PROOF_ID = data.get("proof_id", "")

# ── 9. Bank transfer status ───────────────────────────────────────────────
print("\n" + "="*60)
print("TEST 9: Bank transfer status")
status, data = api("GET", "/payments/bank-transfer/status/{}".format(LEARNER), token=TOKEN)
show("BANK TRANSFER STATUS", status, data)

# ── 10. Payment metadata — email must be populated ────────────────────────
print("\n" + "="*60)
print("TEST 10: Payment metadata (email should be non-empty)")
status, data = api("GET", "/payments/metadata/{}".format(LEARNER), token=TOKEN)
show("PAYMENT METADATA", status, data)
meta = data.get("metadata", {})
email_in_meta = meta.get("email", "")
if email_in_meta and "@" in email_in_meta:
    print("   --> email OK: {}".format(email_in_meta))
else:
    print("   --> WARNING: email still blank in metadata!")

print("\n" + "="*60)
print("ALL TESTS DONE\n")
