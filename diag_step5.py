#!/usr/bin/env python3
from dotenv import load_dotenv; load_dotenv()
import psycopg2, os

url = os.getenv("DATABASE_URL","").strip()
if "sslmode" not in url: url += "?sslmode=require"
conn = psycopg2.connect(url, connect_timeout=15)
cur = conn.cursor()

# Check confirmed column type and values
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='email_accounts' ORDER BY ordinal_position")
print("email_accounts schema:", cur.fetchall())

cur.execute("SELECT DISTINCT confirmed FROM email_accounts LIMIT 5")
print("confirmed distinct values:", cur.fetchall())

cur.execute("SELECT COUNT(*) FROM email_accounts")
print("total email_accounts:", cur.fetchone()[0])

cur.execute("SELECT COUNT(*) FROM email_accounts WHERE confirmed=1")
print("confirmed=1:", cur.fetchone()[0])

cur.execute("SELECT COUNT(*) FROM email_accounts WHERE confirmed IS TRUE")
print("confirmed IS TRUE:", cur.fetchone()[0])

cur.execute("SELECT COUNT(*) FROM learner_profiles")
print("learner_profiles:", cur.fetchone()[0])

cur.execute("SELECT COUNT(*) FROM payments")
print("payments:", cur.fetchone()[0])

cur.execute("SELECT COUNT(*) FROM certificates")
print("certificates:", cur.fetchone()[0])

cur.execute("SELECT COUNT(*) FROM activity_log")
print("activity_log rows:", cur.fetchone()[0])

cur.execute("SELECT COUNT(*) FROM prompt_history")
print("prompt_history rows:", cur.fetchone()[0])

# Check what data exists in activity_log
cur.execute("SELECT action, COUNT(*) FROM activity_log GROUP BY action ORDER BY count DESC LIMIT 10")
print("activity_log actions:", cur.fetchall())

conn.close()
print("Done.")
