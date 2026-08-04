import sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def read(p):
    with open(os.path.join(ROOT, p), encoding='utf-8') as f:
        return f.read()

src = read('app/main.py')
es  = read('app/services/email_service.py')
db  = read('app/db.py')
sec = read('app/security.py')

checks = [
    ('Paystack always-verify',            'PAYSTACK_SECRET_KEY env var is not set' in src),
    ('course/start requires auth',        'Sign in to access courses.' in src),
    ('course/next requires auth',         'Sign in to continue your course.' in src),
    ('quiz owner-check',                  'learner_id does not match your session.' in src),
    ('profile POST requires auth',        'Sign in to update your profile.' in src),
    ('profile photo_url validation',      'photo_url must be an https://' in src),
    ('withdraw requires auth',            'Sign in to request a withdrawal.' in src),
    ('_bearer_optional defined',          '_bearer_optional' in src),
    ('receipt tier1 price correct',       'Beginner Bundle — \u20a630,000' in src),
    ('receipt tier2 price correct',       'Intermediate Bundle — \u20a660,000' in src),
    ('admin enquiries GET route',         '@app.get("/admin/enquiries")' in src),
    ('admin enquiries resolve route',     '/admin/enquiries/{enquiry_id}/resolve' in src),
    ('cert /verify route',                '@app.get("/verify/{cert_id}"' in src),
    ('enquiry rate limit in security',    'ENQUIRY_RATE_LIMIT_REQUESTS' in sec),
    ('enquiry rate limit enforced',       '_enquiry_store' in sec),
    ('prompt_plan in db migrations',      'prompt_plan' in db),
    ('unsubscribe in email_service',      'unsubscribe' in es),
]

all_ok = True
for label, result in checks:
    status = '  OK  ' if result else '  MISS'
    if not result:
        all_ok = False
    print(status, label)

print()
print('ALL DONE' if all_ok else 'ITEMS MISSING — see MISS lines above')
sys.exit(0 if all_ok else 1)
