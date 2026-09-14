#!/usr/bin/env python3
"""Full diagnostic — DB + live API."""
from dotenv import load_dotenv; load_dotenv()
import psycopg2, os, urllib.request, json, ssl

url = os.getenv("DATABASE_URL","").strip()
if "sslmode" not in url: url += "?sslmode=require"

conn = psycopg2.connect(url, connect_timeout=15)
cur  = conn.cursor()

print("DB DIAGNOSTIC")
for label, sql in [
    ("email_accounts confirmed", "SELECT COUNT(*) FROM email_accounts WHERE confirmed IS TRUE"),
    ("learner_profiles",         "SELECT COUNT(*) FROM learner_profiles WHERE tier!='deleted'"),
    ("certificates",             "SELECT COUNT(*) FROM certificates"),
    ("payments",                 "SELECT COUNT(*) FROM payments"),
    ("tasks",                    "SELECT COUNT(*) FROM tasks"),
    ("team_members",             "SELECT COUNT(*) FROM team_members"),
    ("email_automation",         "SELECT COUNT(*) FROM email_automation"),
]:
    try:
        cur.execute(sql)
        print(f"  {label}: {cur.fetchone()[0]}")
    except Exception as e:
        conn.rollback()
        print(f"  {label}: ERROR {e}")

cur.execute("SELECT COALESCE(lp.tier,'free') t, COUNT(*) n FROM email_accounts ea LEFT JOIN learner_profiles lp ON lp.learner_id=ea.learner_id WHERE ea.confirmed IS TRUE GROUP BY t ORDER BY t")
print(f"  tier_breakdown: {cur.fetchall()}")
conn.close()

BASE="https://mypytutor.onrender.com"
ctx=ssl.create_default_context()
def hit(m,p,b=None,t=None):
    req=urllib.request.Request(BASE+p,data=json.dumps(b).encode() if b else None,
        headers={"Content-Type":"application/json","User-Agent":"DiagBot/1.0",**({"X-Admin-Token":t} if t else {})},method=m)
    try:
        with urllib.request.urlopen(req,timeout=25,context=ctx) as r:
            return r.status,json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try: return e.code,json.loads(e.read().decode())
        except: return e.code,e.read().decode()[:150]
    except Exception as e: return 0,str(e)

print("\nLIVE API DIAGNOSTIC")
s,d=hit("GET","/health"); print(f"  health [{s}]: {d}")

admin_pass=os.getenv("ADMIN_PASSWORD","")
if admin_pass:
    s,d=hit("POST","/admin/login",{"email":os.getenv("ADMIN_EMAIL","tega.com.ng@gmail.com"),"password":admin_pass})
    print(f"  login [{s}]: ok={d.get('ok')} token={bool(d.get('token'))}")
    if d.get("token"):
        tok=d["token"]
        s2,d2=hit("GET","/admin/dashboard",token=tok)
        print(f"  dashboard [{s2}]:")
        if isinstance(d2,dict):
            print(f"    users={d2.get('users')}")
            print(f"    tier={d2.get('users_by_tier')}")
            print(f"    certs={d2.get('certificates')}")
        else: print(f"    {d2}")
        s3,d3=hit("GET","/admin/users",token=tok)
        if isinstance(d3,dict): print(f"  users [{s3}]: total={d3.get('total')} profiles={len(d3.get('learner_profiles',[]))}")
        else: print(f"  users [{s3}]: {d3[:100]}")
else:
    print("  (set ADMIN_PASSWORD in .env for live API test)")
print("Done.")
