#!/usr/bin/env python3
"""
Diagnose the 500 errors on DB-dependent endpoints.
Runs against the live server AND tests the Supabase connection directly.
"""
import urllib.request, json, ssl, time, os
from dotenv import load_dotenv
load_dotenv()

ctx  = ssl.create_default_context()
BASE = "https://mypytutor.onrender.com"

def hit(method, path, body=None, token=None, timeout=30):
    url     = BASE + path
    headers = {"Content-Type": "application/json", "User-Agent": "DiagBot/1.0"}
    if token: headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body else None
    req  = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            b = r.read().decode()
            try:    return r.status, json.loads(b)
            except: return r.status, b[:300]
    except urllib.error.HTTPError as e:
        b = e.read().decode()
        try:    return e.code, json.loads(b)
        except: return e.code, b[:200]
    except Exception as e:
        return 0, str(e)[:120]

print("=" * 60)
print("  PART 1: Test Supabase direct connection from this machine")
print("=" * 60)

DB_URL = os.getenv("DATABASE_URL", "")
if DB_URL:
    try:
        import psycopg2
        url = DB_URL if "sslmode" in DB_URL else DB_URL + "?sslmode=require"
        conn = psycopg2.connect(url, connect_timeout=15)
        cur  = conn.cursor()
        # Check which tables exist
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema='public' ORDER BY table_name
        """)
        tables = [r[0] for r in cur.fetchall()]
        print(f"  ✅ Supabase connected — {len(tables)} tables exist")
        print(f"     Tables: {', '.join(tables[:10])}{'...' if len(tables)>10 else ''}")

        # Check row counts for critical tables
        for t in ["learner_profiles","email_accounts","payments","certificates"]:
            if t in tables:
                cur.execute(f"SELECT COUNT(*) FROM {t}")
                n = cur.fetchone()[0]
                print(f"     {t}: {n} rows")
            else:
                print(f"     {t}: TABLE MISSING ❌")
        conn.close()
    except Exception as e:
        print(f"  ❌ Supabase connection FAILED: {e}")
        print("     This means DATABASE_URL in Render environment is wrong or not set")
else:
    print("  ❌ DATABASE_URL not in local .env — cannot test directly")
    print("     But we can still diagnose via live endpoint responses")

print()
print("=" * 60)
print("  PART 2: Test live endpoints with proper auth")
print("=" * 60)

# Create a test user and get a real token
email = f"diag{int(time.time())}@diagtest.com"
print(f"\n  Creating test user: {email}")

s, d = hit("POST", "/auth/signup", {
    "email": email, "name": "DiagUser", "password": "DiagTest1234!"
})
print(f"  signup: [{s}] {d}")

# Try admin confirm
print("\n  Testing admin login...")
s, d = hit("POST", "/admin/login", {"email": "tega.com.ng@gmail.com", "password": "admin"})
print(f"  admin login: [{s}] — {'token present' if isinstance(d,dict) and 'token' in d else str(d)[:60]}")

admin_token = d.get("token","") if isinstance(d,dict) else ""
if admin_token:
    s, d = hit("POST", "/admin/users/confirm-email",
               {"email": email}, token=admin_token)
    print(f"  admin confirm: [{s}] {d}")

# Try signin after potential confirmation
s, d = hit("POST", "/auth/signin", {"email": email, "password": "DiagTest1234!"})
print(f"  signin: [{s}] {str(d)[:80]}")
token = d.get("token","") if isinstance(d,dict) else ""

if token:
    lid = d.get("learner_id","diagtest")
    print(f"\n  Got token! learner_id={lid}")
    print("\n  Testing authenticated endpoints:")

    tests = [
        ("progress",     "GET",  f"/progress/{lid}",    None),
        ("chat",         "POST", "/chat",               {"message":"What is Python?","learner_id":lid,"level":"beginner","history":[]}),
        ("quiz_gen",     "POST", "/quiz/generate",      {"learner_id":lid,"topic":"variables","level":"beginner"}),
        ("cert_basic",   "GET",  f"/certificate/basic?learner_id={lid}&name=Test", None),
        ("conversations","GET",  f"/conversations/{lid}", None),
    ]
    for name, method, path, body in tests:
        s, d = hit(method, path, body, token=token, timeout=40)
        icon = "✅" if 200 <= s < 300 else "❌"
        detail = str(d)[:80] if not isinstance(d,dict) else (d.get("error") or d.get("content","")[:60] or str(d)[:60])
        print(f"    {icon} [{s}] {name:<15} {detail}")
else:
    print("\n  No token — testing unauthenticated DB endpoints:")
    # progress doesn't require auth
    s, d = hit("GET", "/progress/default")
    print(f"  progress/default: [{s}] {d}")
    s, d = hit("POST", "/coupons/validate", {"code":"TEST123","plan":"any"})
    print(f"  coupon_validate: [{s}] {d}")

print()
print("=" * 60)
print("  PART 3: Check DATABASE_URL is set correctly on Render")
print("=" * 60)
print("  Go to: Render → mypy-tutor → Environment")
print("  Verify DATABASE_URL = postgresql://postgres:sRL3MZjmiErSOurC@db.fzgllhmstxrshsfzcrqu.supabase.co:5432/postgres")
print("  If not set, ALL DB-dependent routes return 500.")
print()
