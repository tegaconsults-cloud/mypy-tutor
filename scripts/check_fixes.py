"""
Full security-fix verification — all three passes.
Run:  python scripts/check_fixes.py
Exit: 0 = all pass, 1 = items missing.
"""
import sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def read(p):
    with open(os.path.join(ROOT, p), encoding='utf-8') as f:
        return f.read()

src    = read('app/main.py')
es     = read('app/services/email_service.py')
db     = read('app/db.py')
sec    = read('app/security.py')
auth   = read('app/auth.py')
ea     = read('app/email_auth.py')
adm    = read('app/admin.py')
models = read('app/models.py')

def has(text, needle): return needle in text

checks = [
    # ── PASS 1: Critical original fixes ─────────────────────────────────────
    ('Paystack always-verify (rejects if key missing)',
        has(src, 'PAYSTACK_SECRET_KEY env var is not set')),
    ('course/start requires auth + owner check',
        has(src, 'Sign in to access courses.')),
    ('course/next requires auth + owner check',
        has(src, 'Sign in to continue your course.')),
    ('quiz owner-check when authenticated',
        has(src, 'learner_id does not match your session.')),
    ('profile POST requires auth',
        has(src, 'Sign in to update your profile.')),
    ('profile photo_url URL/content validation',
        has(src, 'photo_url must be an https://')),
    ('withdrawal requires auth + owner check',
        has(src, 'Sign in to request a withdrawal.')),
    ('_bearer_optional at module top-level (not after use)',
        src.index('_bearer_optional = _HTTPBearer') < src.index('async def get_progress')),
    ('receipt tier1 price label correct (30k)',
        has(src, 'Beginner Bundle \u2014 \u20a630,000')),
    ('admin enquiries GET route exists',
        has(src, '@app.get("/admin/enquiries")')),
    ('cert /verify route exists',
        has(src, '@app.get("/verify/{cert_id}"')),
    ('enquiry rate limit in security middleware',
        has(sec, 'ENQUIRY_RATE_LIMIT_REQUESTS')),
    ('prompt_plan column in db migrations',
        has(db, 'prompt_plan')),
    ('unsubscribe link in bulk announcements',
        has(es, 'unsubscribe')),

    # ── PASS 2: Route auth hardening ─────────────────────────────────────────
    ('learner/courses requires auth + owner check',
        has(src, 'Sign in to view your courses.')),
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
    ('conversations requires auth + owner check',
        has(src, 'Sign in to view your conversation history.')),
    ('new_conversation requires auth + owner check',
        has(src, 'Sign in to start a conversation.')),
    ('SESSION_SECRET fallback random in auth.py',
        has(auth, '_RUNTIME_FALLBACK_SECRET') and
        'mypytutor-INSECURE-fallback' not in auth),
    ('SESSION_SECRET fallback random in email_auth.py',
        has(ea, '_RUNTIME_FALLBACK_SECRET') and
        'mypytutor-INSECURE-fallback' not in ea),
    ('SESSION_SECRET fallback random in admin.py',
        has(adm, '_ADMIN_RUNTIME_FALLBACK') and
        'mypytutor-INSECURE-fallback' not in adm),
    ('_AdminLogin model has max_length limits',
        has(src, 'max_length=254') and 'class _AdminLogin' in src),
    ('purge_expired_reset_tokens in db.py',
        has(db, 'purge_expired_reset_tokens')),
    ('purge called at startup in main.py',
        has(src, 'purge_expired_reset_tokens')),

    # ── PASS 3: Third-pass audit fixes ───────────────────────────────────────
    ('history/{id} requires auth + owner check',
        has(src, 'Sign in to view your learning history.')),
    ('history quiz requires auth + owner check',
        has(src, 'Sign in to view your quiz history.')),
    ('invoice PDF requires auth + owner check',
        has(src, 'Sign in to download invoices.')),
    ('payments/metadata requires auth (email oracle closed)',
        has(src, 'Sign in to generate payment metadata.')),
    ('certificate name spoofing fixed (session name used)',
        has(src, 'learner_id = user.learner_id') and
        has(src, 'This prevents name spoofing')),
    ('supabase/status behind admin auth',
        '_require_admin(request)' in src[src.find('async def supabase_status'):
                                         src.find('async def supabase_status') + 300]),
    ('supabase/status does NOT leak URL',
        'url": _os.getenv("SUPABASE_URL' not in src),
    ('feedback/message has rate limit',
        has(src, 'fb_{ip}') and 'message_feedback' in src),
    ('feedback/survey has rate limit',
        has(src, 'surv_{ip}') and 'survey_feedback' in src),
    ('feedback/summary is admin-only',
        '_require_admin(request)' in src[src.find('async def feedback_summary'):
                                          src.find('async def feedback_summary') + 200]),
    ('chat route validates learner_id against session',
        has(src, 'learner_id in request does not match your session.')),
    ('resend-confirmation has rate limit (3/15min)',
        has(src, 'resend_{ip}') and has(src, '3, 900')),
    ('photo_url model max_length tightened to 2.8MB',
        has(models, 'max_length=2_800_000') and
        'max_length=4_000_000' not in models),
]

all_ok = True
for label, result in checks:
    status = '  OK  ' if result else '  MISS'
    if not result:
        all_ok = False
    print(status, label)

print()
total   = len(checks)
passed  = sum(1 for _, r in checks if r)
missing = total - passed
if all_ok:
    print(f'ALL {total} CHECKS PASSED')
else:
    print(f'{missing} item(s) missing — fix the MISS lines above')
sys.exit(0 if all_ok else 1)
