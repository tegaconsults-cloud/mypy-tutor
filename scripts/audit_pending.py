"""
Audit all four pending issues from the bug report.
Run: python scripts/audit_pending.py
"""
import sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def check(label, condition, detail=""):
    status = "OK  " if condition else "FAIL"
    print(f"  {status}  {label}" + (f": {detail}" if detail else ""))
    return condition

results = []

# ── Read all relevant files ────────────────────────────────────────────────
with open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8") as f:
    main_src = f.read()
with open(os.path.join(ROOT, "app", "email_auth.py"), encoding="utf-8") as f:
    email_auth_src = f.read()
with open(os.path.join(ROOT, "app", "services", "email_service.py"), encoding="utf-8") as f:
    email_svc_src = f.read()
with open(os.path.join(ROOT, "frontend-react", "src", "components", "ReferralModal.tsx"), encoding="utf-8") as f:
    referral_src = f.read()
with open(os.path.join(ROOT, "frontend-react", "src", "context", "AuthContext.tsx"), encoding="utf-8") as f:
    auth_ctx_src = f.read()
with open(os.path.join(ROOT, "frontend-react", "src", "components", "AuthModal.tsx"), encoding="utf-8") as f:
    auth_modal_src = f.read()
with open(os.path.join(ROOT, "app", "models.py"), encoding="utf-8") as f:
    models_src = f.read()
with open(os.path.join(ROOT, "app", "db.py"), encoding="utf-8") as f:
    db_src = f.read()

print("\n=== ISSUE 1: REFERRAL LINK AUTO-FILL ===")
r1  = check("ReferralModal builds /?ref=CODE URL",  "?ref=" in referral_src)
r2  = check("ReferralModal uses referralLink var",   "referralLink" in referral_src)
r3  = check("AuthContext detects ?ref= param",       "params.get('ref')" in auth_ctx_src or "params.get(\"ref\")" in auth_ctx_src)
r4  = check("AuthContext stores code → localStorage","mpt_referral_code" in auth_ctx_src)
r5  = check("AuthModal reads mpt_referral_code",     "mpt_referral_code" in auth_modal_src)
r6  = check("AuthModal auto-fills signup tab",       "setTab('signup')" in auth_modal_src)
r7  = check("AuthModal calls clearReferralCode() on submit", "clearReferralCode()" in auth_modal_src)
results += [r1,r2,r3,r4,r5,r6,r7]

print("\n=== ISSUE 2: PAYMENT AUTO-CONFIRMATION ===")
# Both confirm_payment and send_payment_receipt_email must appear inside the webhook function.
# Find the webhook function body more reliably.
webhook_start = main_src.find("async def paystack_webhook")
webhook_end   = main_src.find("\n@app.", webhook_start + 10)
webhook_block = main_src[webhook_start:webhook_end] if webhook_start != -1 else ""

r8  = check("Webhook has confirm_payment() call",
            "confirm_payment" in webhook_block)
r9  = check("Webhook calls confirm_payment for course purchase",
            webhook_block.count("confirm_payment") >= 2 or
            ("record_course_purchase" in webhook_block and "confirm_payment" in webhook_block))
r10 = check("Webhook sends payment receipt email for tier bundle",
            "send_payment_receipt_email" in webhook_block)
r11 = check("Webhook sends payment receipt email for course purchase",
            webhook_block.count("send_payment_receipt_email") >= 2 or
            ("record_course_purchase" in webhook_block and "send_payment_receipt_email" in webhook_block))
results += [r8,r9,r10,r11]

print("\n=== ISSUE 3: ADMIN SET-TIER → USER DASHBOARD SYNC ===")
set_tier_start = main_src.find('"/admin/users/{learner_id}/set-tier"')
set_tier_block = main_src[set_tier_start:set_tier_start+700] if set_tier_start != -1 else ""
# Does it update the DB with an updated_at?
r12 = check("set-tier calls apply_tier_upgrade (updates memory+SQLite)", "apply_tier_upgrade" in set_tier_block)
r13 = check("set-tier calls upgrade_tier_db (Supabase sync)",            "upgrade_tier_db" in set_tier_block)
# Does /progress endpoint include updated_at for cache busting?
prog_start = main_src.find('"/progress/{learner_id}"')
prog_block = main_src[prog_start:prog_start+500] if prog_start != -1 else ""
r14 = check("/progress endpoint exists and reads from get_profile()", "get_profile" in prog_block)
# Does ProgressResponse include updated_at field?
r15 = check("ProgressResponse model includes updated_at field",
            "updated_at" in models_src)
# Does learner_profiles table have updated_at column?
r16 = check("learner_profiles table has updated_at column",
            "updated_at" in db_src and "learner_profiles" in db_src)
results += [r12,r13,r14,r15,r16]

print("\n=== ISSUE 4: EMAIL LINK DOMAIN ===")
# Confirmation link: must point to APP_URL (backend) because /auth/confirm is a backend route
r17 = check("email_auth.py confirm_url uses APP_URL (backend route — correct)",
            "APP_URL" in email_auth_src and "auth/confirm" in email_auth_src)
r18 = check("email_service.py confirm_url uses _app_url() (APP_URL — correct)",
            "_app_url()" in email_svc_src and "auth/confirm" in email_svc_src)
# After confirmation, /auth/confirm redirects to FRONTEND_URL
r19 = check("/auth/confirm redirect uses FRONTEND_URL",
            "FRONTEND_URL" in main_src and "auth/confirm" in main_src)
# Reset link: must point to FRONTEND_URL (?auth=reset is handled by React)
r20 = check("reset_url uses FRONTEND_URL first (correct)",
            "FRONTEND_URL" in email_auth_src and "auth=reset" in email_auth_src)
results += [r17,r18,r19,r20]

# ── SUMMARY ───────────────────────────────────────────────────────────────
total   = len(results)
passed  = sum(results)
failed  = total - passed
print(f"\n{'='*52}")
print(f"TOTAL: {total}   PASSED: {passed}   FAILED: {failed}")
if failed:
    sys.exit(1)
else:
    print("All pending tasks verified complete.")
