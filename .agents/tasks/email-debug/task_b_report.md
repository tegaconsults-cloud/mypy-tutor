# Task B — Deep Debug Report
**Date:** 2025-07-12  
**Scope:** All files listed in the debug brief  
**Total bugs found and fixed:** 7

---

## Bug List

### Group 1 — Core app

| # | FILE:LINE | DESCRIPTION | FIX |
|---|-----------|-------------|-----|
| 1 | `app/main.py:646` | `favicon()` function defined with no `@app.get` route decorator — the endpoint was unreachable (404 on all `/favicon.ico` requests). | Added `@app.get("/favicon.ico", include_in_schema=False)` decorator immediately before the function definition. |
| 2 | `app/main.py:442–443` | Backoff list `[0, 2, 4, 6, 8]` with `range(5)` (5 attempts) contradicts the task requirement of `[0, 1, 2]` (3 attempts). With 5 attempts the total possible wait was 20 seconds before giving up, which is excessive and could cause Render request timeouts. The log message also incorrectly said `/5`. | Changed `_backoffs = [0, 2, 4, 6, 8]` → `[0, 1, 2]`, `range(5)` → `range(3)`, and log format string `%d/5` → `%d/3`. |

### Group 4 — Monetisation (new code)

| # | FILE:LINE | DESCRIPTION | FIX |
|---|-----------|-------------|-----|
| 3 | `app/monetisation/paystack.py:100,147,233,270,305` | All HTTP status checks used `!= 200` instead of `>= 400`. Paystack returns HTTP 201 for some create operations (e.g. `create_customer`). A 201 would have incorrectly triggered a `PaystackError` and failed the entire checkout flow. | Changed `r.status_code != 200` → `r.status_code >= 400` in `initialize_transaction`, `verify_transaction`, `get_customer`, `cancel_subscription`, and `get_subscription`. (Note: `create_customer` already correctly used `not in (200, 201)` and was left unchanged.) |
| 4 | `app/monetisation/db.py:~886` | `init_monetisation_db()` used a hardcoded absolute Windows path for the migration SQL file: `r"c:\Users\LENOVO\..."`. This would cause a `FileNotFoundError` on every Render/Linux deployment. | Replaced with `os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "docs", "migration_v2_monetisation.sql")` — relative to the file's location, works on all platforms. |
| 5 | `app/monetisation/checkout.py:264` | `mdb.update_subscription  # find sub and update status` — a dangling no-op expression. The function was referenced but never called; it had no effect and left a misleading comment. The actual DB update that follows handles the status correctly. | Removed the dead expression line. |
| 6 | `app/monetisation/checkout.py:93` | `txn['amount'] != order['total_kobo']` — Paystack may return the amount as a string or float; comparing directly to an integer `total_kobo` could fail silently or raise a `TypeError`. | Changed to `int(txn['amount']) != int(order['total_kobo'])` for type-safe comparison. |
| 7 | `app/monetisation/routes.py:122–127` | `GET /payments/verify/{reference}` returned `{'status': 'success', 'payment': dict(payment)}` for already-paid orders — no entitlement/access data was included. The frontend could not determine which courses were unlocked without making a second API call. | Updated the already-paid path to also query `mdb.get_user_entitlements(user.learner_id)` and return `{'status': 'success', 'payment': ..., 'entitlements': ..., 'idempotent': True}`. |

---

## Files Verified Clean (no bugs found)

- `app/db.py` — `get_db()` rollback, SQL parameter style, thread safety all correct.
- `app/llm_client.py` — Provider cascade Groq→Gemini→OpenRouter is correct. Backoff handled at provider level correctly.
- `app/classifier.py` — All intent keys present in `scores` dict (concept, debug, codegen, exercise, course); general returned as default.
- `app/formatter.py` — `_detect_topic` returns `None` safely; `format_response` always returns `{intent, content, topic}`.
- `app/prompts.py` — `build_system_prompt()` returns a string in all code paths; all intent keys mapped.
- `app/security.py` — `check_free_prompt_limit` returns `(bool, int)`; rate-limiting store uses locks; `validate_chat_request` raises `HTTPException`.
- `app/auth.py` — `get_current_user` returns `None` on missing/invalid token; `require_user` raises 401; session token algorithm is consistent (itsdangerous `URLSafeTimedSerializer`).
- `app/email_auth.py` — `register_email` returns `(False, message)` for duplicate email; token expiry check correct; `sign_in_email` uses `bcrypt.checkpw` via `verify_password`; `hash_password` returns `str` consistently.
- `app/admin.py` — `verify_admin_token` reads from `SESSION_SECRET`; revenue queries use correct column names; `get_announcements` timestamp conversion is correct.
- `app/courses.py` — COURSE_CATALOG keys are consistent internally; slug naming differs from monetisation migration by design (separate catalog systems).
- `app/certificates.py` — Template variable substitution safe.
- `app/paystack.py` (original DVA) — No naming conflict with `app/monetisation/paystack.py`; uses correct Paystack endpoints and `PAYSTACK_SECRET_KEY`.
- `app/feedback.py` — SQL column names match schema; both insert functions handle DB errors non-fatally.
- `app/progress.py` — `get_profile` always returns a `LearnerProfile` (never None); XP never goes negative; `get_knowledge_gaps` returns a list.
- `app/monetisation/db.py` — All SELECTs use `RealDictCursor`; all INSERTs use `%s`; `create_order` generates unique order numbers; `validate_coupon` uses timezone-aware datetime comparison; `get_active_subscription` correctly filters `status IN ('active', 'trialing')`; `store_webhook_event` handles `UniqueViolation` and returns `None` on duplicate.
- `app/monetisation/entitlements.py` — `PREMIUM_COURSES` has all 23 slugs; `check_ai_quota` reads `ai_tutor` feature key; `resolve_access` gracefully handles no-subscription case.
- `app/monetisation/routes.py` — Webhook handler calls `request.body()` before `json.loads(raw_body)` — correct order; admin header extraction uses `removeprefix('Bearer ')` correctly.
- `app/services/email_service.py` — All 5 Task A functions (`send_referral_signup_to_referrer`, `send_referral_welcome_to_referred`, `send_subscription_activated`, `send_referral_reward_credited`, `send_platform_update`) handle exceptions via `_dispatch_async` which never raises; `send_platform_update` sends to individual user (loop is in `main.py`).

---

## Compile Status

All 21 target files pass `python -m py_compile` without errors:

```
OK: app/main.py
OK: app/db.py
OK: app/llm_client.py
OK: app/classifier.py
OK: app/formatter.py
OK: app/prompts.py
OK: app/security.py
OK: app/auth.py
OK: app/email_auth.py
OK: app/admin.py
OK: app/courses.py
OK: app/certificates.py
OK: app/paystack.py
OK: app/feedback.py
OK: app/progress.py
OK: app/monetisation/db.py
OK: app/monetisation/paystack.py
OK: app/monetisation/entitlements.py
OK: app/monetisation/checkout.py
OK: app/monetisation/routes.py
OK: app/services/email_service.py
ALL FILES COMPILE OK
```

Python version: 3.11.9 — `X | Y` union syntax is natively supported; no `Optional` backport needed.
