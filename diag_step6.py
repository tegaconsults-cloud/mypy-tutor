#!/usr/bin/env python3
"""Test the exact dashboard queries against live Supabase."""
from dotenv import load_dotenv; load_dotenv()
import psycopg2, psycopg2.extras, os, urllib.request, json, ssl

url = os.getenv("DATABASE_URL","").strip()
if "sslmode" not in url: url += "?sslmode=require"
conn = psycopg2.connect(url, connect_timeout=15)
cur = conn.cursor()

print("=== EXACT DASHBOARD QUERIES ===\n")

cur.execute("SELECT COUNT(*) FROM email_accounts WHERE confirmed IS TRUE")
ec = cur.fetchone()[0]
print(f"email_accounts confirmed IS TRUE: {ec}")

cur.execute("SELECT COUNT(*) FROM learner_profiles WHERE tier != 'deleted'")
pc = cur.fetchone()[0]
print(f"learner_profiles (non-deleted): {pc}")

cur.execute("""
    SELECT COUNT(DISTINCT ea.learner_id)
    FROM email_accounts ea WHERE ea.confirmed IS TRUE
""")
cu = cur.fetchone()[0]
print(f"confirmed_unique: {cu}")
print(f"total_users = max({ec}, {pc}, {cu}) = {max(ec, pc, cu)}")

print("\n=== TIER BREAKDOWN ===")
for tier in ["free","tier1","tier2","tier3","tier4"]:
    cur.execute("""
        SELECT COUNT(*) FROM (
            SELECT ea.learner_id
            FROM email_accounts ea
            LEFT JOIN learner_profiles lp ON lp.learner_id = ea.learner_id
            WHERE ea.confirmed IS TRUE
              AND COALESCE(lp.tier, 'free') = %s
              AND COALESCE(lp.tier, 'free') != 'deleted'
        ) t
    """, (tier,))
    print(f"  {tier}: {cur.fetchone()[0]}")

cur.execute("SELECT COUNT(*) FROM certificates")
print(f"\ncertificates: {cur.fetchone()[0]}")

cur.execute("SELECT COUNT(*) FROM payments")
print(f"payments: {cur.fetchone()[0]}")

conn.close()
print("\n=== LIVE ADMIN DASHBOARD API ===")
ctx = ssl.create_default_context()
BASE = "https://mypytutor.onrender.com"
# Try without admin token to see if it's an auth issue
req = urllib.request.Request(BASE + "/admin/dashboard",
    headers={"User-Agent":"DiagBot/1.0", "X-Admin-Token":"wrong"})
try:
    with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
        print(f"[{r.status}]", json.loads(r.read().decode()))
except urllib.error.HTTPError as e:
    print(f"[{e.code}]", e.read().decode()[:200])
except Exception as e:
    print("ERR:", e)
