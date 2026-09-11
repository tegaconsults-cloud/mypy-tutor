#!/usr/bin/env python3
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()
url = os.getenv("DATABASE_URL","") + "?sslmode=require"
conn = psycopg2.connect(url, connect_timeout=15)
cur = conn.cursor()

cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
tables = [r[0] for r in cur.fetchall()]
print(f"Tables ({len(tables)}):", tables)

# Check columns of key tables
for t in ["payments","learner_profiles","email_accounts","certificates"]:
    if t in tables:
        cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='{t}' ORDER BY ordinal_position")
        cols = [r[0] for r in cur.fetchall()]
        print(f"\n{t} columns: {cols}")
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        n = cur.fetchone()[0]
        print(f"{t} row count: {n}")
    else:
        print(f"\n{t}: TABLE MISSING")

conn.close()
print("\nDone.")
