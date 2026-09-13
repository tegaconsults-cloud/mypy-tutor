#!/usr/bin/env python3
"""Check actual Supabase column types for email_accounts and email_automation."""
from dotenv import load_dotenv; load_dotenv()
import psycopg2, os

url = os.getenv("DATABASE_URL","").strip()
if "sslmode" not in url: url += "?sslmode=require"
conn = psycopg2.connect(url, connect_timeout=15)
cur = conn.cursor()

for table in ["email_accounts", "email_automation", "learner_profiles", "daily_prompt_counts"]:
    cur.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name=%s ORDER BY ordinal_position
    """, (table,))
    rows = cur.fetchall()
    print(f"\n{table}:")
    for r in rows:
        print(f"  {r[0]:<40} {r[1]:<20} nullable={r[2]} default={r[3]}")

# Check row counts
for table in ["email_accounts","email_automation","learner_profiles","daily_prompt_counts"]:
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    print(f"\n{table} row count: {cur.fetchone()[0]}")

# Check email_automation rows
cur.execute("SELECT learner_id, email, opted_out FROM email_automation LIMIT 5")
print("\nemail_automation sample:", cur.fetchall())

# Check what confirmed looks like
cur.execute("SELECT email, confirmed FROM email_accounts LIMIT 3")
print("\nemail_accounts confirmed sample:", cur.fetchall())

conn.close()
