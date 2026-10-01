"""
One-time migration: credit ₦5,000 welcome bonus to EVERY existing user.

Runs on Render where DATABASE_URL is set.
  - Updates all existing referral code holders: bonus_balance += 5000
  - Creates referral codes for confirmed users who don't have one,
    with bonus_balance = 5000 immediately
  - Skips test/diag accounts and accounts with no email

Usage:
  python blow_balances.py
"""
import os, sys, secrets, logging
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

BONUS = 5000.0

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    log.error("psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)

url = os.environ.get("DATABASE_URL", "")
if not url:
    log.error("DATABASE_URL not set.")
    sys.exit(1)

log.info("Connecting to DB...")
try:
    conn = psycopg2.connect(url, sslmode="require", connect_timeout=30)
    conn.autocommit = False
except Exception as e:
    # Try without sslmode for local dev
    try:
        conn = psycopg2.connect(url, connect_timeout=30)
        conn.autocommit = False
    except Exception as e2:
        log.error("Cannot connect: %s", e2)
        sys.exit(1)

log.info("Connected.")

print("=" * 65)
print("  BLOW BALANCE — ₦5,000 to every existing user")
print("=" * 65)

cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# ── STEP 1: Credit ₦5,000 to ALL existing referral code holders ───────
cur.execute("SELECT COUNT(*) AS n FROM referrals")
existing_count = cur.fetchone()["n"]
log.info(f"\nStep 1: Found {existing_count} existing referral codes")

if existing_count > 0:
    plain = conn.cursor()
    plain.execute("UPDATE referrals SET bonus_balance = bonus_balance + %s", (BONUS,))
    updated = plain.rowcount
    conn.commit()
    log.info(f"  ✅ Updated {updated} codes — each +₦{BONUS:,.0f}")
else:
    log.info("  No existing codes to update.")

# ── STEP 2: Create codes for confirmed users without one ───────────────
cur.execute("""
    SELECT lp.learner_id, lp.email, lp.display_name
    FROM learner_profiles lp
    WHERE NOT EXISTS (
        SELECT 1 FROM referrals r WHERE r.owner_id = lp.learner_id
    )
    AND COALESCE(lp.tier, 'free') != 'deleted'
    AND lp.email IS NOT NULL
    AND lp.email != ''
    AND lp.learner_id NOT LIKE 'diag%'
    AND lp.learner_id NOT LIKE 'test%'
    AND lp.learner_id != 'default'
    ORDER BY lp.updated_at DESC
    LIMIT 500
""")
without_code = cur.fetchall()
log.info(f"\nStep 2: {len(without_code)} real users without a referral code")

created = 0
skipped = 0
for u in without_code:
    learner_id = u["learner_id"]
    email      = (u["email"] or "").lower().strip()
    if not email:
        skipped += 1
        continue

    # Generate a unique code
    for attempt in range(5):
        code = secrets.token_hex(4).upper()
        check = conn.cursor()
        check.execute("SELECT 1 FROM referrals WHERE code = %s", (code,))
        if not check.fetchone():
            break
    else:
        skipped += 1
        continue

    try:
        plain = conn.cursor()
        plain.execute("""
            INSERT INTO referrals
              (code, owner_id, owner_email, uses, max_uses,
               reward_tier, bonus_balance, successful_referrals, created_at)
            VALUES (%s, %s, %s, 0, 50, 'tier1', %s, 0, EXTRACT(EPOCH FROM NOW()))
        """, (code, learner_id, email, BONUS))
        conn.commit()
        created += 1
        log.info(f"  Created {code} for {email[:40]}  balance=₦{BONUS:,.0f}")
    except Exception as e:
        conn.rollback()
        skipped += 1
        log.warning(f"  SKIP {learner_id[:20]}: {e}")

log.info(f"\n  ✅ Created {created} new codes, {skipped} skipped")

# ── Final verification ─────────────────────────────────────────────────
vcur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
vcur.execute("SELECT COUNT(*) AS n, COALESCE(SUM(bonus_balance),0) AS total FROM referrals")
row = vcur.fetchone()
log.info(f"\nFinal state:")
log.info(f"  Total referral codes:    {row['n']}")
log.info(f"  Total balance in system: ₦{float(row['total']):,.0f}")

vcur.execute("""
    SELECT code, owner_email, bonus_balance
    FROM referrals
    ORDER BY created_at ASC
""")
all_rows = vcur.fetchall()
print("\nAll referral codes after migration:")
print(f"{'Code':<12} {'Balance':>10}  Email")
print("-" * 65)
for r in all_rows:
    print(f"{r['code']:<12} ₦{float(r['bonus_balance']):>8,.0f}  {r['owner_email'][:40]}")

conn.close()
print("\n" + "=" * 65)
print("  ✅  MIGRATION COMPLETE")
print("=" * 65)
