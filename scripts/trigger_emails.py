"""
Trigger all email automation jobs and confirm delivery.
Usage:
  ADMIN_TOKEN=<token> python scripts/trigger_emails.py
  or set ADMIN_TOKEN in .env

To get admin token: POST /admin/login with admin email+password
"""
import urllib.request, urllib.error, json, sys, os

BASE = "https://mypytutor.onrender.com"

def call(method, path, body=None, admin_token=None, timeout=90):
    h = {"Content-Type": "application/json", "Accept": "application/json"}
    if admin_token:
        h["X-Admin-Token"] = admin_token
    data = json.dumps(body or {}).encode() if body is not None else b"{}"
    req = urllib.request.Request(BASE + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, {"error": str(e)}
    except Exception as ex:
        return 0, {"error": str(ex)}

# ── Get admin token ─────────────────────────────────────────────────────────
ATOK = os.getenv("ADMIN_TOKEN", "")
if not ATOK:
    # Try .env file
    for line in open(".env"):
        k, _, v = line.partition("=")
        if k.strip() == "ADMIN_TOKEN":
            ATOK = v.strip().strip('"')
            break

if not ATOK:
    # Try admin login
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "tega.com.ng@gmail.com")
    ADMIN_PW    = os.getenv("ADMIN_PASSWORD", "")
    if not ADMIN_PW:
        for line in open(".env"):
            k, _, v = line.partition("=")
            if k.strip() == "ADMIN_PASSWORD":
                ADMIN_PW = v.strip().strip('"')
                break
    if ADMIN_PW:
        s, d = call("POST", "/admin/login", {"email": ADMIN_EMAIL, "password": ADMIN_PW})
        ATOK = d.get("token", "")
        print(f"Admin login [{s}]: token={bool(ATOK)}")

if not ATOK:
    print("No admin token. Set ADMIN_TOKEN or ADMIN_PASSWORD env var.")
    print("Run: ADMIN_TOKEN=<token> python scripts/trigger_emails.py")
    sys.exit(1)

# ── Trigger all email jobs ───────────────────────────────────────────────────
print("\n" + "="*55)
print("Triggering all email automation jobs...")
print("="*55)

s, d = call("POST", "/admin/email/trigger-all", admin_token=ATOK, timeout=90)

if s != 200:
    print(f"ERROR [{s}]: {d}")
    sys.exit(1)

total = d.get("total_sent", 0)
print(f"\nTotal emails sent: {total}")
print(f"Message: {d.get('message', '')}\n")

for jname, jr in d.get("jobs", {}).items():
    sent    = jr.get("sent", 0)
    skipped = jr.get("skipped", 0)
    errors  = jr.get("errors", 0)
    sym     = "PASS" if errors == 0 else "WARN"
    print(f"  [{sym}] {jname:<28} sent={sent}  skipped={skipped}  errors={errors}")
    if jr.get("error"):
        print(f"         ERROR: {jr['error'][:80]}")

print("\n" + "="*55)
print("Done. Check tegaconsults@gmail.com and teamsamikokoglobalacademy@gmail.com for emails.")
