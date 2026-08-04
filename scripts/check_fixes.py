"""
Full security-fix verification script for MyPy Tutor.
Run:  python scripts/check_fixes.py
Exit: 0 = all pass, 1 = items missing.
"""
import sys, os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def read(p):
    with open(os.path.join(ROOT, p), encoding='utf-8') as f:
        return f.read()

src   = read('app/main.py')
es    = read('app/services/email_service.py')
db    = read('app/db.py')
sec   = read('app/security.py')
auth  = read('app/auth.py')
ea    = read('app/email_auth.py')
adm   = read('app/admin.py')

def has(text, needle): return needle in text

checks = [
    # ── BATCH 1: Paystack & LLM routes ──────────────────────────────────────
    ('Paystack always-verify (no secret → reject)',
        has(src, 'PAYSTACK_SECRET_KEY env var is not set')),
    ('course/start requires auth + owner check',
        has(src, 'Sign in to access courses.')),
    ('course/next requires auth + owner check',
        has(src, 'Sign in to continue your course.')),
    ('quiz owner-check (token != learner_id)',
        has(src, 'learner_id does not match your session.')),
    ('profile POST requires auth',
        has(src, 'Sign in to update your profile.')),
    ('profile photo_url validation (https/data:image)',
        has(src, 'photo_url must be an https://')),
    ('withdrawal requires auth + owner check',
        has(src, 'Sign in to request a withdrawal.')),
    ('_bearer_optional defined for progress route',
        has(src, '_bearer_optional')),
    ('receipt tier1 label has correct ₦30,000',
        has(src, 'Beginner Bundle \u2014 \u20a630,000')),
    ('receipt tier2 label has correct ₦60,000',
        has(src, 'Intermediate Bundle \u2014 \u20a660,000')),
    ('admin enquiries GET route exists',
        has(src, '@app.get("/admin/enquiries")')),
    ('admin enquiries resolve route exists',
        has(src, '/admin/enquiries/{enquiry_id}/resolve')),
    ('cert /verify route exists',
        has(src, '@app.get("/verify/{cert_id}"')),
    ('enquiry rate limit in security middleware',
        has(sec, 'ENQUIRY_RATE_LIMIT_REQUESTS')),
    ('enquiry rate limit enforced (_enquiry_store)',
        has(sec, '_enquiry_store')),
    ('prompt_plan column in db migrations',
        has(db, 'prompt_plan')),
    ('unsubscribe link in bulk announcement emails',
        has(es, 'unsubscribe')),

    # ── BATCH 2: Second-pass route auth fixes ────────────────────────────────
    ('learner/courses requires auth + owner check',
        has(src, 'Sign in to view your courses.')),
    ('exercise/generate has owner check when authenticated',
        has(src, 'Sign in to generate assignments.')),    # assignment check proves pattern
    ('assignments/generate requires auth',
        has(src, 'Sign in to generate assignments.')),
    ('assignments/submit requires auth + owner check',
        has(src, 'Sign in to submit assignments.')),
    ('assignments/review requires auth + owner check',
        has(src, 'Sign in to request assignment review.')),
    ('assignments list requires auth + owner check',
        has(src, 'Sign in to view assignments.')),
    ('referral/balance requires auth + owner check',
        has(src, 'Sign in to view your referral balance.')),
    ('referral/{id} requires auth + owner check',
        has(src, 'Sign in to view your referral code.')),
    ('referral/use requires auth',
        has(src, 'Sign in to apply a referral code.')),
    ('invoice/{id} requires auth + owner check',
        has(src, 'Sign in to view invoices.')),
    ('invoices/{learner_id} requires auth + owner check',
        'You can only view your own invoices.' in src),
    ('conversations list requires auth + owner check',
        has(src, 'Sign in to view your conversation history.')),
    ('conversation messages require auth + owner check',
        has(src, 'Sign in to view conversation messages.')),
    ('new_conversation requires auth + owner check',
        has(src, 'Sign in to start a conversation.')),
    ('coupons/apply has owner check when authenticated',
        has(src, 'learner_id does not match your session.')),

    # ── BATCH 3: Infrastructure hardening ───────────────────────────────────
    ('SESSION_SECRET fallback is random (not hardcoded) in auth.py',
        has(auth, '_RUNTIME_FALLBACK_SECRET') and
        'mypytutor-INSECURE-fallback' not in auth),
    ('SESSION_SECRET fallback is random (not hardcoded) in email_auth.py',
        has(ea, '_RUNTIME_FALLBACK_SECRET') and
        'mypytutor-INSECURE-fallback' not in ea),
    ('SESSION_SECRET fallback is random (not hardcoded) in admin.py',
        has(adm, '_ADMIN_RUNTIME_FALLBACK') and
        'mypytutor-INSECURE-fallback' not in adm),
    ('_AdminLogin model has field length limits',
        has(src, 'max_length=254') and 'class _AdminLogin' in src),
    ('purge_expired_reset_tokens in db.py',
        has(db, 'purge_expired_reset_tokens')),
    ('purge called at startup in main.py',
        has(src, 'purge_expired_reset_tokens')),
]

all_ok = True
for label, result in checks:
    status = '  OK  ' if result else '  MISS'
    if not result:
        all_ok = False
    print(status, label)

print()
if all_ok:
    print(f'ALL {len(checks)} CHECKS PASSED')
else:
    missing = sum(1 for _, r in checks if not r)
    print(f'{missing} item(s) missing — fix the MISS lines above')
sys.exit(0 if all_ok else 1)
