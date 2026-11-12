# Task A Review — Email Automation (Pass 2)

**Files reviewed:** `app/services/email_service.py`, `app/main.py`, `app/monetisation/checkout.py`  
**Prior verdict:** CHANGES_REQUESTED (B-1: missing order_type guard on `send_subscription_activated`)  
**Current verdict:** APPROVED

---

## Evidence Summary

### Prior Blocker B-1 — Resolved

The prior review required adding `and order.get("order_type") == "subscription"` to the
`send_subscription_activated` guard in `fulfill_order()`.

`checkout.py` now reads:
```python
# 3. Send subscription activated email (only for actual subscription orders)
if _user_email and order.get("order_type") == "subscription":
    from app.services.email_service import send_subscription_activated as _ssa
    _ssa(_user_email, _plan_name, user_name=_user_name, ai_limit=_ai_limit)
```
The comment and the double condition (`_user_email and order.get("order_type") == "subscription"`)
match the required correction exactly. B-1 is resolved. ✅

---

### Requirement 1 — Five new email functions in `email_service.py`

All five functions present at lines 1113–1274:

| # | Function | Line |
|---|----------|------|
| 21 | `send_referral_signup_to_referrer` | 1113 |
| 22 | `send_referral_welcome_to_referred` | 1146 |
| 23 | `send_subscription_activated` | 1177 |
| 24 | `send_referral_reward_credited` | 1213 |
| 25 | `send_platform_update` | 1248 |

Each uses `_shell()`, `_cta()`, `_box()`, the branded colour constants (`PRIMARY`, `GOLD`, `NAVY`),
and ends with a `_dispatch_async()` call. ✅

### Requirement 2 — Referral emails fired in `/auth/signup`

**Path A — auto-confirmed user:** `auth_signup` lines ~1263–1277: thread fires both referral
emails in `try/except Exception: pass`. ✅

**Path B — email confirmation (`/auth/confirm`):** `_send_confirm_emails` background thread,
both emails in a nested `try/except Exception: pass`. ✅

### Requirement 3 — `send_subscription_activated` in `fulfill_order()`

Guard is `if _user_email and order.get("order_type") == "subscription"` (B-1 fix confirmed).
Covered by the outer `try/except Exception as _email_exc` — cannot break payment flow. ✅

### Requirement 4 — `send_referral_reward_credited` in `fulfill_order()`

Guard is `if order.get("referral_id") and _user_email:`. Inner `try/except` + outer
`try/except`. Reward = `int(order["total_kobo"] * 0.15) // 100` (15% in naira). ✅

### Requirement 5 — `send_platform_update` auto-fired in admin announcement route

`/admin/announce` fires `_auto_platform_update` in a `threading.Thread` (non-blocking).
Per-recipient `try/except` + outer `try/except`. Existing `send_announcement` call preserved. ✅

### Requirement 6 — No `X | Y` union type syntax in new code

All five new function signatures use only `str = ''` / `int = 300` default-valued parameters.
No union syntax introduced. The pre-existing `list[str] | None` on function 16
(`send_assignment_reminder_email`, line 884) is out of scope. ✅

### Requirement 7 — Email failures never break signup, payment, or announcement flows

- Signup: `try/except Exception` wrapping all email calls. ✅  
- `fulfill_order()`: outer `try/except Exception as _email_exc` covers all five email calls. ✅  
- Announcement: double `try/except`. ✅

---

## Blockers

None.
