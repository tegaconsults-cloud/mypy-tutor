import sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "app", "admin.py"), encoding="utf-8") as f:
    src = f.read()

checks = [
    ("Reads learner_profiles from SQLite",    "SELECT learner_id, email, display_name, tier FROM learner_profiles" in src),
    ("Reads email_accounts from SQLite",       "SELECT learner_id, email, name FROM email_accounts WHERE confirmed=1" in src),
    ("Has Supabase fallback for restarts",     "Supabase fallback" in src),
    ("No stale in-memory _confirmed usage",    "from app.email_auth import _confirmed" not in src),
    ("No stale in-memory _store usage",        "from app.progress import _store as ls" not in src),
    ("Logs total/matching count",              "total_users=%d matching=%d" in src),
]

all_ok = True
for label, ok in checks:
    status = "OK  " if ok else "FAIL"
    print(f"  {status} {label}")
    if not ok:
        all_ok = False

print()
print("All announcement checks passed." if all_ok else "SOME CHECKS FAILED.")
sys.exit(0 if all_ok else 1)
