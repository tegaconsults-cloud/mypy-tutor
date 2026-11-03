"""
Trigger all email automation jobs via admin API and report results.
Reads admin credentials from env or prompts. Run from workspace root.
"""
import urllib.request, urllib.error, json, sys, os

BASE = "https://mypytutor.onrender.com"

def call(path, body=None, admin_token=None, user_token=None, timeout=60):
    h = {"Content-Type": "application/json", "Accept": "application/json"}
    if admin_token: h["X-Admin-Token"] = admin_token
    if user_token:  h["Authorization"] = "Bearer " + user_token
    d = json.dumps(body or {}).encode()
    req = urllib.request.Request(BASE + path, data=d, headers=h, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read())
        except: return e.code, {"error": str(e)}
    except Exception as ex:
        return 0, {"error": str(ex)}

# Try to get admin token — password may be in .env or env var
ADMIN_PW = ""
ADMIN_EMAIL = "tega.com.ng@gmail.com"
for line in open(".env"):
    if line.startswith("ADMIN_PASSWORD="):
        ADMIN_PW = line.split("=", 1)[1].strip().strip('"')
    if line.startswith("ADMIN_EMAIL="):
        ADMIN_EMAIL = line.split("=", 1)[1].strip().strip('"')
# Also check environment variable directly
ADMIN_PW = ADMIN_PW or os.getenv("ADMIN_PASSWORD", "")

if not ADMIN_PW:
    print("ADMIN_PASSWORD not found. Please set it as an env var or in .env")
    sys.exit(1)

s, d = call("/admin/login", {"email": ADMIN_EMAIL, "password": ADMIN_PW})
ATOK = d.get("token", "")
print(f"Admin login [{s}]: token={'OK' if ATOK else 'FAILED'}")
if not ATOK:
    print("Login failed:", d)
    sys.exit(1)

# ── Trigger every email automation job ──────────────────────────────────────
jobs = [
    ("Re-engagement (7-day inactive)",       "/admin/reengagement/trigger"),
    ("Course reminder",                       "/admin/email/course-reminder/trigger"),
    ("Assignment reminder",                   "/admin/email/assignment-reminder/trigger"),
    ("Weekend motivation",                    "/admin/email/weekend-motivation/trigger"),
]

print("\n" + "="*60)
total_sent = 0
for label, path in jobs:
    print(f"\n  Triggering: {label} ...")
    s, d = call(path, admin_token=ATOK, timeout=60)
    sent   = d.get("sent", 0)
    skip   = d.get("skipped", 0)
    errors = d.get("errors", 0)
    total_sent += sent
    stat = "OK " if s == 200 else "ERR"
    print(f"  [{stat} {s}]  sent={sent}  skipped={skip}  errors={errors}")
    if d.get("message"):
        print(f"         {d['message']}")
    if d.get("error"):
        print(f"         ERROR: {d['error']}")

print("\n" + "="*60)
print(f"TOTAL REAL EMAILS SENT: {total_sent}")
print()
