# Implementation Plan — Payment Flow Audit & Bug Fix

> Workspace: `c:\Users\LENOVO\Downloads\mypy-tutor-main\mypy-tutor-main`
> Run server with: `uvicorn app.main:app --reload` (or `python -m uvicorn app.main:app`)
> Smoke-test each change: `curl -s http://localhost:8000/health` → `{"status":"ok"}`

---

## PART 1 — Delete Unnecessary Files

- [ ] 1. Delete the four confirmed orphan / stale files.
      These files are not imported, not served, and clutter the workspace.
      Files to delete:
      - `_diag_admin.py`
      - `_diag_admin2.py`
      - `.agents/tasks/review.md`
      - `.agents/tasks/review.json`
      
      Do NOT touch: `tests/`, `docs/`, `static/voice-integration.html`, `frontend/`,
      `.github/`, any `app/` file, or the new `plan.md` being written by this step.
      
      Files: (delete, do not modify)
      Verify: `python -c "import os; [print(p) for p in ['_diag_admin.py','_diag_admin2.py','.agents/tasks/review.md','.agents/tasks/review.json'] if os.path.exists(p)]"` — prints nothing (all gone).

---

## PART 2 — Payment Flow Bugs

### A. Paystack Initialize — email blank bug

- [ ] 2. Fix blank-email guard in `POST /payments/paystack/initialize`.
      
      **Bug** (file `app/main.py`, line ~3806):
      ```python
      email = user.email or ""
      ```
      If `user.email` is blank (possible for email-auth users whose profile email
      wasn't persisted, or Google users whose session was reconstructed after restart),
      Paystack receives an empty `email` field and rejects the request with a 400.
      
      **Fix**: after `email = user.email or ""`, if `email` is still blank or missing
      `@`, do the same DB fallback that `POST /payments/dedicated-account` already does
      (lines ~3985–3993): query `email_accounts` for `learner_id`, then
      `learner_profiles`. Add this block immediately after line 3806, before
      `amount_kobo` is computed:
      
      ```python
      if not email or "@" not in email:
          _prof = get_profile(learner_id or user.learner_id)
          email = _prof.email or ""
          if not email or "@" not in email:
              try:
                  from app.db import get_db as _gdb_init
                  with _gdb_init() as _dc:
                      with _dc.cursor() as _dcur:
                          _dcur.execute(
                              "SELECT email FROM email_accounts WHERE learner_id=%s LIMIT 1",
                              (learner_id or user.learner_id,)
                          )
                          _erow = _dcur.fetchone()
                          if _erow and _erow[0]:
                              email = _erow[0]
              except Exception:
                  pass
      if not email or "@" not in email:
          raise HTTPException(
              status_code=400,
              detail="We could not find your email address. Please update your profile before checkout."
          )
      ```
      
      Files: `app/main.py` (around line 3806–3808)
      Verify: Start the server, call `POST /payments/paystack/initialize` with a
      Bearer token for a user whose `user.email` is blank but whose email is in
      `email_accounts`. Confirm 200 response (or expected Paystack error), NOT a
      400 "No such customer" from Paystack. Also confirm that a user with a valid
      email still gets 200 as before.

### B. Paystack Initialize — callback_url

- [ ] 3. Verify and document `callback_url` in `POST /payments/paystack/initialize`.
      
      **Current code** (line ~3809–3811):
      ```python
      callback_url = _os.getenv(
          "PAYSTACK_CALLBACK_URL",
          _os.getenv("FRONTEND_URL", "https://mypytutor.com.ng") + "/payment/callback"
      )
      ```
      This is **correct** — it uses `PAYSTACK_CALLBACK_URL` env var if set, falls
      back to `FRONTEND_URL + "/payment/callback"`. No code change needed here.
      The route `/payment/callback` on the **frontend** (mypytutor.com.ng SPA) must
      exist; if it does not, Paystack's redirect lands on a 404. Item 6 below adds
      a **backend** GET route at `/payment/callback` that serves a success page so
      that even if the frontend SPA cannot handle this path, the user sees confirmation.
      
      Files: (informational — no change needed to callback_url logic)
      Verify: Confirm `PAYSTACK_CALLBACK_URL` is set in Render env or that
      `FRONTEND_URL` is correct. No code change; verification is configuration-only.

### C. Paystack Webhook — learner_id blank fallback bug

- [ ] 4. Fix `learner_id` becoming an email string when no `email_accounts` row is found.
      
      **Bug** (file `app/main.py`, line ~2545):
      ```python
      learner_id = acct["learner_id"] if acct else email
      ```
      When `load_email_account(email)` returns `None` (e.g. Google OAuth user whose
      email is in `learner_profiles` but not `email_accounts`), `learner_id` becomes
      the raw email string (e.g. `"user@gmail.com"`). Calling `upgrade_tier_db` with
      an email as the learner_id silently creates a garbage profile row.
      
      **Fix**: after the existing DVA customer_code fallback block (lines ~2548–2557),
      also check the webhook's own `metadata` dict for a `learner_id` field, then
      fall back to looking up `learner_profiles.email`:
      
      Replace the line:
      ```python
      learner_id = acct["learner_id"] if acct else email
      ```
      With:
      ```python
      learner_id = acct["learner_id"] if acct else (
          str(meta.get("learner_id", "") or "").strip() or email
      )
      ```
      
      Then, after the full DVA/customer_code fallback block, add a final safety check:
      ```python
      # Final safety: if learner_id still looks like an email, try learner_profiles
      if learner_id and "@" in learner_id:
          try:
              from app.db import get_db as _gdb_lid
              with _gdb_lid() as _lc:
                  with _lc.cursor() as _lcur:
                      _lcur.execute(
                          "SELECT learner_id FROM learner_profiles WHERE email=%s LIMIT 1",
                          (learner_id,)
                      )
                      _lrow = _lcur.fetchone()
                      if _lrow and _lrow[0]:
                          learner_id = _lrow[0]
          except Exception:
              pass
      ```
      
      Files: `app/main.py` (around lines 2544–2557)
      Verify: Simulate a webhook with an email belonging to a Google-OAuth learner
      (no `email_accounts` row). Confirm `learner_id` resolves to the real learner_id,
      not the email string. Confirm `upgrade_tier_db` is called with the correct ID.

### D. Paystack Webhook — get_all_courses() coverage

- [ ] 5. Verify course-slug check in webhook covers all slugs.
      
      **Current code** (line ~2588):
      ```python
      if course_meta and course_meta in (c.name for c in get_all_courses()):
      ```
      `get_all_courses()` returns `list(COURSES.values())` from `app/courses.py`.
      After reading `courses.py`, confirmed COURSES dict contains:
      `python-fundamentals`, `python-strings`, `python-collections`,
      `python-control-flow`, `python-functions-advanced`, `python-oop`,
      `python-modules-stdlib`, `python-dsa`, `data-science-python`,
      `python-databases`, `numpy-mastery`, `pandas-mastery`, `web-apis`,
      `prompt-engineering`, `ai-prompt-engineering`, `machine-learning`,
      `ai-automation` — all 17 courses. Coverage is complete.
      
      **HOWEVER**, `COURSE_CATALOG` in `courses.py` (line ~636–656) includes
      `"prompt-engineering"` as a catalog slug but COURSES also has `"prompt-engineering"`.
      Both are present. No code change needed.
      
      Files: (no change — confirmed OK)
      Verify: `python -c "from app.courses import get_all_courses; print([c.name for c in get_all_courses()])"` — prints all 17+ slugs including `prompt-engineering` and `ai-prompt-engineering`.

### E. Paystack Webhook — referral bonus uses wrong learner_id

- [ ] 6. Fix referral bonus credit using potentially wrong `learner_id`.
      
      **Bug** (lines ~2720–2735): The referral bonus block runs AFTER `upgrade_tier_db`
      is called with `learner_id`. If item 4 above has not corrected a bad
      `learner_id`, the `SELECT code FROM referral_uses WHERE used_by_id=%s OR
      used_by_email=%s` query will fail silently — no bonus credited.
      
      This item has no extra code change of its own: it is already fixed as a
      consequence of item 4. After item 4 is applied, `learner_id` is guaranteed
      to be a real learner_id by the time the referral block runs.
      
      Files: `app/main.py` (verified, no separate change)
      Verify: After item 4 is in place, check that a payment by a referral user
      correctly credits the referrer's `bonus_balance` in the `referrals` table.

### F. Missing `/payment/callback` GET route

- [ ] 7. Add `GET /payment/callback` route in `app/main.py`.
      
      **Bug**: Paystack redirects the user back to `{FRONTEND_URL}/payment/callback`
      after card/transfer checkout. If the frontend SPA does not handle that path
      (React Router not configured, or user opens link directly), the browser shows
      a blank or 404 page. There is **no backend GET handler** for this path at all
      (`grep` confirmed zero matches).
      
      **Fix**: Add a lightweight GET handler that serves an inline HTML confirmation
      page. Place it immediately after the existing `@app.get("/payment", ...)` route
      (around line 7146), before the course landing routes:
      
      ```python
      @app.get("/payment/callback", response_class=HTMLResponse, include_in_schema=False)
      async def payment_callback(
          reference: str = "",
          trxref: str = "",
          request: Request = None,
      ) -> HTMLResponse:
          """
          Paystack redirects the user here after checkout (both card and bank transfer).
          Serves a success confirmation page. The reference param is set by Paystack.
          If the user is already on the frontend SPA, JS will detect ?payment=success
          instead (see payment.html fix in item 9).
          """
          ref = reference or trxref or ""
          frontend_url = _os.getenv("FRONTEND_URL", "https://mypytutor.com.ng")
          html_content = f"""<!DOCTYPE html>
      <html lang="en">
      <head>
        <meta charset="UTF-8"/>
        <meta name="viewport" content="width=device-width,initial-scale=1"/>
        <title>Payment — MyPy Tutor</title>
        <meta http-equiv="refresh" content="4; url={frontend_url}/?payment=success&ref={ref}"/>
        <style>
          body{{font-family:'Segoe UI',Arial,sans-serif;background:#07090f;color:#e2e8f0;
               display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;}}
          .card{{background:rgba(255,255,255,.05);border:1px solid rgba(16,185,129,.3);
                border-radius:16px;padding:40px 32px;max-width:460px;text-align:center;}}
          h2{{color:#6ee7b7;font-size:1.4rem;margin:0 0 12px;}}
          p{{color:#94a3b8;font-size:.9rem;line-height:1.7;margin:0 0 20px;}}
          a{{color:#60a5fa;text-decoration:none;font-weight:600;}}
          .ref{{font-size:.75rem;color:#475569;margin-top:8px;}}
        </style>
      </head>
      <body>
        <div class="card">
          <div style="font-size:2.5rem;margin-bottom:12px;">✅</div>
          <h2>Payment Received!</h2>
          <p>Thank you for your payment. Your account will be updated
             automatically. Redirecting you to MyPy Tutor…</p>
          <a href="{frontend_url}/?payment=success&ref={ref}">← Back to MyPy Tutor</a>
          {f'<p class="ref">Reference: {ref}</p>' if ref else ''}
        </div>
      </body>
      </html>"""
          return HTMLResponse(content=html_content)
      ```
      
      Files: `app/main.py` (insert after line ~7146, after the `serve_payment_page` function)
      Verify: `curl -s "http://localhost:8000/payment/callback?reference=TEST123"` →
      returns HTTP 200 with HTML containing "Payment Received!" and a redirect to
      `/?payment=success&ref=TEST123`.

### G. Missing `/payments/paystack/verify/{reference}` endpoint

- [ ] 8. Add `GET /payments/paystack/verify/{reference}` endpoint.
      
      **Bug**: The frontend (payment.html, certificate-locked.html) has no way to
      confirm a payment after the Paystack redirect — it must poll or rely solely on
      the webhook. Adding a verify endpoint lets the frontend confirm payment status
      immediately on the callback page.
      
      **Fix**: Add the following route near the other `/payments/paystack/*` routes
      (after `/payments/paystack/initialize`, around line ~3880):
      
      ```python
      @app.get("/payments/paystack/verify/{reference}")
      async def paystack_verify(
          reference: str,
          user=Depends(get_current_user),
      ) -> dict:
          """
          Verify a Paystack payment by reference.
          Calls Paystack GET /transaction/verify/{reference} and returns
          {status, paid, plan, amount_kobo, amount_ngn}.
          Frontend calls this on the /payment/callback page to confirm payment.
          Requires authentication — prevents unauthenticated balance probing.
          """
          if user is None:
              raise HTTPException(status_code=401, detail="Sign in to verify payment.")
          import re as _re_ref
          if not _re_ref.match(r'^[a-zA-Z0-9_\-]{4,100}$', reference):
              raise HTTPException(status_code=400, detail="Invalid reference format.")
          secret_key = _os.getenv("PAYSTACK_SECRET_KEY", "")
          if not secret_key:
              raise HTTPException(status_code=503, detail="Payment system not configured.")
          try:
              import httpx as _hx2
              resp = _hx2.get(
                  f"https://api.paystack.co/transaction/verify/{reference}",
                  headers={"Authorization": f"Bearer {secret_key}"},
                  timeout=15,
              )
              data = resp.json()
          except Exception as exc:
              logger.error("Paystack verify error: %s", exc)
              raise HTTPException(status_code=502, detail="Could not reach Paystack.")
          if not data.get("status"):
              raise HTTPException(status_code=400, detail=data.get("message", "Verification failed."))
          txn = data.get("data", {})
          paid = txn.get("status") == "success"
          amount_kobo = int(txn.get("amount", 0))
          meta = txn.get("metadata") or {}
          plan = str(meta.get("plan", "") or meta.get("tier", "") or "")
          return {
              "status":      txn.get("status", ""),
              "paid":        paid,
              "plan":        plan,
              "amount_kobo": amount_kobo,
              "amount_ngn":  amount_kobo / 100,
              "reference":   reference,
          }
      ```
      
      Files: `app/main.py` (insert after the `paystack_initialize` function, ~line 3880)
      Verify: `curl -s -H "Authorization: Bearer <token>" http://localhost:8000/payments/paystack/verify/TEST_REF` →
      returns 502 (Paystack unreachable in test) or a structured JSON with `paid`, `amount_ngn`. Does NOT return 401 when a valid token is used.

### H. Bank Transfer Submit — missing learner receipt email

- [ ] 9. Add a "receipt submitted" confirmation email to the learner in `POST /payments/bank-transfer/submit`.
      
      **Bug** (file `app/main.py`, lines ~4095–4120): The submit handler:
      - ✅ Notifies admin via `send_admin_notification`
      - ❌ Does NOT send any email to the learner confirming receipt was received
      
      This causes learners to think their submission was lost.
      
      **Fix**: Add a learner confirmation email immediately after the admin notification
      block (after line ~4120), before the `return` statement:
      
      ```python
      # Send learner confirmation email (non-blocking)
      try:
          from app.services.email_service import _dispatch_async, _shell, _box, _cta, PRIMARY, GOLD
          import datetime as _dt_btp
          _btp_name  = user.name or email.split("@")[0]
          _btp_first = _btp_name.split()[0] if _btp_name else "Learner"
          _btp_date  = _dt_btp.datetime.utcnow().strftime("%d %B %Y, %H:%M UTC")
          _body_html = (
              f"<p style='color:#1e293b;margin:0 0 12px;'>Hi <strong>{_btp_first}</strong>,</p>"
              f"<h2 style='color:{PRIMARY};font-size:1.2rem;margin:0 0 12px;'>&#9989; Receipt Received</h2>"
              f"<p style='color:#475569;line-height:1.7;margin:0 0 16px;'>"
              f"We have received your bank transfer receipt for "
              f"<strong>{plan}</strong> and it is now pending admin review.</p>"
              + _box(
                  f"<strong>Plan:</strong> {plan}<br/>"
                  f"<strong>Amount:</strong> &#8358;{amount:,.0f}<br/>"
                  f"<strong>Reference:</strong> {ref or '—'}<br/>"
                  f"<strong>Proof ID:</strong> {proof_id}<br/>"
                  f"<strong>Submitted:</strong> {_btp_date}",
                  bg="#f0fdf4", border="#16A34A",
              )
              + "<p style='color:#475569;font-size:.85rem;line-height:1.7;'>"
                "Your account will be upgraded within <strong>24 hours</strong> after admin review. "
                "You will receive another email once approved.</p>"
              + _cta("&#128640; Go to MyPy Tutor", _os.getenv("FRONTEND_URL", "https://mypytutor.com.ng"))
          )
          _html_full = _shell(_btp_html := _body_html, "Receipt received — pending admin review.")
          _dispatch_async(
              email,
              f"Receipt Received — {plan} | MyPy Tutor",
              _html_full,
              f"Hi {_btp_first},\n\nWe received your payment receipt for {plan} (₦{amount:,.0f}).\n"
              f"Proof ID: {proof_id}\nYour account will be upgraded within 24 hours.\n\n— MyPy Tutor Team",
              "bank_transfer_received",
          )
      except Exception as _btp_email_exc:
          logger.debug("Learner bank-transfer receipt email failed (non-fatal): %s", _btp_email_exc)
      ```
      
      **Note**: There is also a local variable name collision above (`_btp_html := _body_html`). Clean it up to `_html_full = _shell(_body_html, ...)`.
      
      Files: `app/main.py` (inside `submit_bank_transfer_proof`, after line ~4120 before `return`)
      Verify: Submit a bank transfer proof via `POST /payments/bank-transfer/submit` with
      a valid token. Confirm the learner's email (check Resend logs or SMTP inbox) receives
      a "Receipt Received" email in addition to the admin notification.

### I. Bank Transfer Approve — course slug plan handling

- [ ] 10. Fix `POST /admin/payments/bank-transfer/{proof_id}/approve` — if `plan` is a course slug, call `record_course_purchase` instead of only `upgrade_tier_db`.
      
      **Bug** (file `app/main.py`, lines ~4171–4280): The approve handler:
      1. Infers a tier from the plan name
      2. Calls `upgrade_tier_db(learner_id, tier)` 
      3. Falls back to `tier = "tier1"` if no tier matched
      
      If an admin approves a bank-transfer proof where `plan` is a course slug (e.g.
      `"python-dsa"` or `"machine-learning"`), the handler upgrades the user's tier to
      `tier1` (the default fallback) instead of granting individual course access.
      
      **Fix**: Before the tier inference block (line ~4209), check if `proof["plan"]`
      (lowercased, stripped) matches any key in `COURSE_CATALOG`. If yes, call
      `record_course_purchase` and skip the tier upgrade:
      
      ```python
      # Check if plan is an individual course slug
      from app.courses import COURSE_CATALOG as _CC_approve
      plan_slug = (proof["plan"] or "").strip().lower()
      if plan_slug in _CC_approve:
          # Individual course purchase — grant course access, not a tier
          record_course_purchase(learner_id, plan_slug,
                                 float(proof["amount"]), proof_id)
          # Record + confirm in payments table (already done below for tier purchases)
          _p_course = add_payment(
              user_email=proof["email"],
              user_name=proof.get("email", "").split("@")[0],
              amount=float(proof["amount"]),
              plan=proof["plan"],
              method="bank_transfer",
              notes=f"Proof ID: {proof_id}" + (f" | {admin_notes}" if admin_notes else ""),
          )
          _cfp(_p_course.id)
          # Send receipt and return early
          try:
              from app.services.email_service import send_payment_receipt_email
              send_payment_receipt_email(
                  name=proof["email"].split("@")[0],
                  email=proof["email"],
                  amount=float(proof["amount"]),
                  plan=proof["plan"],
                  payment_id=_p_course.id,
                  currency="NGN",
              )
          except Exception:
              pass
          log_activity("admin", "payment:bank-transfer-approved-course",
                       f"proof={proof_id} learner={learner_id} course={plan_slug}")
          return {
              "ok": True, "proof_id": proof_id,
              "tier": None, "tier_label": f"Course: {plan_slug}",
              "message": f"Bank transfer approved. {proof['email']} granted access to {plan_slug}.",
          }
      ```
      
      Insert this block just before the `_valid_tiers` tier inference block.
      
      Files: `app/main.py` (inside `admin_approve_bank_transfer`, around line ~4209)
      Verify: Create a test bank_transfer_proof row with `plan="python-dsa"` in the DB.
      Call `POST /admin/payments/bank-transfer/{id}/approve` with admin token.
      Confirm `course_purchases` table has a new row for the learner + `python-dsa`,
      and that the learner's `tier` was NOT changed to `tier1`.

---

## PART 3 — DVA and paystack.py

- [ ] 11. Audit `app/paystack.py` — verify `get_or_create_dva` and `preferred_bank`.
      
      **Findings from reading `app/paystack.py`**:
      
      1. `create_dedicated_account` (line ~47): uses `preferred_bank: str = "titan-paystack"`.
         This is **correct** — Paystack's API expects `"titan-paystack"` not `"paystack-titan"`.
      
      2. `get_or_create_dva` (line ~85–130): idempotent check (`get_paystack_customer`)
         before creating — correct. Error handling: `create_customer` and
         `create_dedicated_account` both raise `RuntimeError` on Paystack API errors,
         which is caught by the caller in `main.py` and returned as HTTP 502. Correct.
      
      3. **BUG FOUND**: `create_dedicated_account` is called with:
         ```python
         dva = create_dedicated_account(customer_code, learner_name=name or email.split("@")[0])
         ```
         But `create_dedicated_account`'s signature is:
         ```python
         def create_dedicated_account(customer_code: str, preferred_bank: str = "titan-paystack",
                                       learner_name: str = "") -> dict:
         ```
         The call in `get_or_create_dva` passes `preferred_bank` **positionally** to
         `create_dedicated_account` — BUT it actually passes `learner_name` as a keyword arg
         and omits `preferred_bank` entirely (uses default `"titan-paystack"`). This is fine.
         
         **No change needed** — the default `preferred_bank="titan-paystack"` is already used,
         which is the Paystack-Titan bank. Confirmed correct.
      
      4. `fetch_dedicated_account` handles the "already exists" case correctly.
      
      Files: `app/paystack.py` (read-only audit — no changes needed)
      Verify: `python -c "from app.paystack import get_or_create_dva; print('import OK')"` — no import errors.

---

## PART 4 — Static HTML Audit

### J. payment.html — success state after Paystack callback

- [ ] 12. Add JS in `static/payment.html` to detect `?payment=success` and show a success banner.
      
      **Bug**: After Paystack redirects to `/payment/callback` (item 7), that route
      immediately redirects to `{FRONTEND_URL}/?payment=success&ref=XXX`. If the user
      ends up on the SPA's root page, the SPA may not handle `?payment=success`. But
      if the user lands back on `/payment` (the static payment.html page), there is
      **no code at all** that checks for `?payment=success` query param and shows a
      confirmation message.
      
      **Fix**: Add this JS snippet at the **top of the existing `<script>` block**
      (before the `const API = ...` line) in `static/payment.html`:
      
      ```javascript
      // ── Payment success detection ─────────────────────────────────────────
      (function detectPaymentSuccess() {
        const _sp = new URLSearchParams(location.search);
        if (_sp.get('payment') === 'success' || _sp.get('status') === 'success') {
          const ref = _sp.get('ref') || _sp.get('reference') || _sp.get('trxref') || '';
          const banner = document.createElement('div');
          banner.innerHTML = `
            <div style="position:fixed;top:0;left:0;right:0;z-index:9999;
              background:rgba(16,185,129,.15);border-bottom:1px solid rgba(16,185,129,.4);
              padding:14px 24px;text-align:center;font-size:.9rem;color:#6ee7b7;
              font-family:'Segoe UI',Arial,sans-serif;">
              ✅ <strong>Payment received!</strong> Your account will be updated automatically.
              ${ref ? ` Reference: <code style="background:rgba(255,255,255,.08);padding:1px 6px;border-radius:4px;">${ref}</code>` : ''}
              &nbsp;·&nbsp;<a href="https://mypytutor.com.ng" style="color:#93c5fd;">Go to MyPy Tutor →</a>
            </div>`;
          document.body.prepend(banner);
        }
      })();
      ```
      
      Files: `static/payment.html` (insert at top of `<script>` block, before `const API`)
      Verify: Open `http://localhost:8000/payment?payment=success&ref=TEST123` in a browser.
      Confirm a green banner appears at the top saying "Payment received!" with the reference code.

### K. certificate-locked.html — `SERVER_AMOUNT` inline script bug

- [ ] 13. Fix the inline `<script>` in the Paystack panel of `static/certificate-locked.html` that references `SERVER_AMOUNT` before it is defined.
      
      **Bug** (in `certificate-locked.html`, inside the Paystack panel `<div>`):
      ```html
      <script>
        (function(){
          var a = SERVER_AMOUNT || PLAN_AMOUNTS[SERVER_PLAN] || 0;
          if(a) document.getElementById('ps-label').textContent = ...
        })();
      </script>
      ```
      This inline `<script>` runs BEFORE the main `<script>` block at the bottom of the
      page where `SERVER_AMOUNT` and `PLAN_AMOUNTS` are defined. This causes a
      `ReferenceError: SERVER_AMOUNT is not defined` in the browser console and the
      button label is never updated.
      
      **Fix**: Remove this inline `<script>` block from inside the Paystack panel `<div>`.
      Instead, update the button label inside the `startPaystackCheckout()` function
      at the top (it already resets the label on error), and add the initial label update
      at the very bottom of the main `<script>` block, after all variable declarations:
      
      Add this line at the end of the main `<script>` block, after all the function
      definitions (just before the closing `</script>`):
      ```javascript
      // Set button label immediately once SERVER_AMOUNT is known
      (function(){
        var a = SERVER_AMOUNT || PLAN_AMOUNTS[SERVER_PLAN] || 0;
        if(a) document.getElementById('ps-label').textContent =
          '\uD83D\uDE80 Pay \u20A6' + a.toLocaleString() + ' \u2014 Unlock Certificate';
      })();
      ```
      
      Files: `static/certificate-locked.html`
      Verify: Open `http://localhost:8000/certificate/basic` (with a learner that has no tier).
      Confirm the payment button shows the correct price (e.g. "🚀 Pay ₦30,000 — Unlock Certificate")
      without any console `ReferenceError`.

### L. certificate-locked.html — Paystack checkout passes correct learner_id

- [ ] 14. Verify `startPaystackCheckout()` in `static/certificate-locked.html` passes `learner_id` from JWT decode correctly.
      
      **Current code** (in `startPaystackCheckout`):
      ```javascript
      const lid = _getLearnerID();
      const resp = await fetch(API + '/payments/paystack/initialize', {
        ...
        body: JSON.stringify({
          learner_id:  lid,
          amount_ngn:  amount,
          plan:        SERVER_PLAN,
          ...
        }),
      });
      ```
      
      `_getLearnerID()` already tries `localStorage` keys first, then falls back to
      JWT decode — same pattern as `payment.html`. This is **correct**.
      
      **However**: if `_getToken()` returns empty (user not signed in), the call
      will hit the `/payments/paystack/initialize` endpoint which returns 401
      `"Sign in to start checkout."` — the error is caught and shown in `errEl`.
      This is correct behavior.
      
      **One improvement needed**: the error display element `ps-error` is a `<p>` tag
      with `style="display:none"`. The JS sets `errEl.style.display = 'block'` and
      `errEl.innerHTML = ...`. This is fine as-is.
      
      **Fix needed**: The auth check already redirects to sign-in on 401, but the
      message says "sign in to MyPy Tutor first" without a direct link. Add an `<a>`
      tag in the error message to make it clickable. In `startPaystackCheckout`:
      
      Replace:
      ```javascript
      errEl.innerHTML = 'Please <a href="https://mypytutor.com.ng" style="color:#93c5fd">sign in to MyPy Tutor</a> first to start checkout.';
      ```
      (This is already correct in the current code — no change needed.)
      
      **Confirmed**: No code change needed. `_getLearnerID()` correctly decodes JWT.
      
      Files: `static/certificate-locked.html` (read-only audit — no changes needed)
      Verify: Open `/certificate/basic` as an unauthenticated user. Click "Pay Now".
      Confirm the error message appears with a clickable link to mypytutor.com.ng.

---

## PART 5 — Integration Smoke Test

- [ ] 15. End-to-end smoke test of the payment flow.
      
      After all changes above, verify the complete flow:
      
      1. `GET /health` → `{"status": "ok"}`
      2. `POST /auth/signin` with test credentials → get JWT token
      3. `GET /payment?plan=tier1&amount=30000` → HTTP 200, returns `payment.html`
      4. `POST /payments/paystack/initialize` with JWT token →
         - If `PAYSTACK_SECRET_KEY` is set: returns `{authorization_url, reference}`
         - If not set: returns 503 "Payment system not configured" (expected in dev)
      5. `POST /payments/bank-transfer/submit` with JWT token, plan, amount, proof_b64 →
         HTTP 200 `{ok: true, proof_id: ...}`, AND learner receives confirmation email
      6. `GET /payment/callback?reference=TEST` → HTTP 200 HTML with "Payment Received!"
      7. `GET /payments/paystack/verify/TEST` with JWT → HTTP 502 from Paystack
         (since `TEST` is not a real reference — but no 401 or 500)
      8. Admin: `POST /admin/payments/bank-transfer/{proof_id}/approve` →
         - if proof plan is a course slug: `course_purchases` table has new row
         - if proof plan is a tier name: `learner_profiles.tier` is updated
      
      Files: no changes — this is verification only
      Verify: All 8 steps above pass without unhandled exceptions in the server log.
