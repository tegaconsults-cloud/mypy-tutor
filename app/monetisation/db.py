"""
Monetisation persistence layer for MyPy Tutor.

All DB operations use the shared get_db() context manager from app.db,
psycopg2.extras.RealDictCursor for SELECT queries, and parameterised queries only.
"""

import os
import math
import time
import secrets
import logging

import psycopg2
import psycopg2.extras

from app.db import get_db

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _generate_order_number() -> str:
    """Generate a unique, human-readable order number."""
    return "MPT-" + str(int(time.time() * 1000)) + secrets.token_hex(2).upper()


# ---------------------------------------------------------------------------
# Plans
# ---------------------------------------------------------------------------

def get_all_plans() -> list:
    """Return all active subscription plans ordered by price ascending."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM subscription_plans WHERE is_active = TRUE ORDER BY monthly_price_kobo ASC"
            )
            return [dict(row) for row in cur.fetchall()]


def get_plan_by_slug(slug: str) -> "dict | None":
    """Return a single plan by its slug, or None if not found."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM subscription_plans WHERE slug = %s",
                (slug,),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def get_plan_by_id(plan_id: str) -> "dict | None":
    """Return a single plan by its ID, or None if not found."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM subscription_plans WHERE id = %s",
                (plan_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None


# ---------------------------------------------------------------------------
# Course prices
# ---------------------------------------------------------------------------

def get_course_prices() -> list:
    """Return all active course prices ordered by price ascending."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM course_prices WHERE is_active = TRUE ORDER BY price_kobo ASC"
            )
            return [dict(row) for row in cur.fetchall()]


def get_course_price(course_slug: str) -> "dict | None":
    """Return pricing for a single active course, or None."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM course_prices WHERE course_slug = %s AND is_active = TRUE",
                (course_slug,),
            )
            row = cur.fetchone()
            return dict(row) if row else None


# ---------------------------------------------------------------------------
# Bundles
# ---------------------------------------------------------------------------

def _attach_bundle_courses(conn, bundle: dict) -> dict:
    """Fetch course slugs for a bundle and attach them under key 'courses'."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "SELECT course_slug FROM bundle_courses WHERE bundle_id = %s",
            (bundle["id"],),
        )
        bundle["courses"] = [row["course_slug"] for row in cur.fetchall()]
    return bundle


def get_all_bundles() -> list:
    """Return all active bundles ordered by price ascending, each with a 'courses' list."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM bundles WHERE is_active = TRUE ORDER BY price_kobo ASC"
            )
            bundles = [dict(row) for row in cur.fetchall()]
        return [_attach_bundle_courses(conn, b) for b in bundles]


def get_bundle_by_slug(slug: str) -> "dict | None":
    """Return a single active bundle by slug with its 'courses' list, or None."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM bundles WHERE slug = %s AND is_active = TRUE",
                (slug,),
            )
            row = cur.fetchone()
            if row is None:
                return None
        bundle = dict(row)
        return _attach_bundle_courses(conn, bundle)


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

def create_order(
    user_id,
    order_type,
    item_id,
    subtotal_kobo,
    discount_kobo,
    total_kobo,
    currency="NGN",
    coupon_id=None,
    referral_id=None,
) -> dict:
    """Insert a new order and return the inserted row."""
    order_number = _generate_order_number()
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO orders (
                    order_number, user_id, order_type, item_id,
                    subtotal_kobo, discount_kobo, total_kobo,
                    currency, coupon_id, referral_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    order_number,
                    user_id,
                    order_type,
                    item_id,
                    subtotal_kobo,
                    discount_kobo,
                    total_kobo,
                    currency,
                    coupon_id,
                    referral_id,
                ),
            )
            return dict(cur.fetchone())


def get_order(order_id: str) -> "dict | None":
    """Return an order by its ID, or None."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
            row = cur.fetchone()
            return dict(row) if row else None


def update_order_status(order_id: str, status: str, paid_at=None) -> None:
    """Update the status (and optionally paid_at) of an order."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE orders SET status = %s, paid_at = %s WHERE id = %s",
                (status, paid_at, order_id),
            )


def get_orders_for_user(user_id: str) -> list:
    """Return all orders for a user, newest first."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM orders WHERE user_id = %s ORDER BY created_at DESC",
                (user_id,),
            )
            return [dict(row) for row in cur.fetchall()]


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------

def create_payment(
    order_id,
    user_id,
    provider_reference,
    amount_kobo,
    currency="NGN",
) -> dict:
    """Insert a new payment record and return the inserted row."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO payments (order_id, user_id, provider_reference, amount_kobo, currency)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING *
                """,
                (order_id, user_id, provider_reference, amount_kobo, currency),
            )
            return dict(cur.fetchone())


def get_payment_by_reference(reference: str) -> "dict | None":
    """Return a payment by its provider reference, or None."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM payments WHERE provider_reference = %s",
                (reference,),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def update_payment(
    payment_id,
    status,
    provider_transaction_id=None,
    channel=None,
    gateway_response=None,
    verified_at=None,
) -> None:
    """Update a payment row with only the supplied non-None fields."""
    fields = ["status = %s"]
    values = [status]

    if provider_transaction_id is not None:
        fields.append("provider_transaction_id = %s")
        values.append(provider_transaction_id)
    if channel is not None:
        fields.append("channel = %s")
        values.append(channel)
    if gateway_response is not None:
        fields.append("gateway_response = %s")
        values.append(psycopg2.extras.Json(gateway_response))
    if verified_at is not None:
        fields.append("verified_at = %s")
        values.append(verified_at)

    values.append(payment_id)
    sql = f"UPDATE payments SET {', '.join(fields)} WHERE id = %s"

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, values)


# ---------------------------------------------------------------------------
# Subscriptions
# ---------------------------------------------------------------------------

def create_subscription(
    user_id,
    plan_id,
    billing_interval,
    paystack_customer_code,
) -> dict:
    """Insert a new subscription and return the inserted row."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO subscriptions (user_id, plan_id, billing_interval, paystack_customer_code)
                VALUES (%s, %s, %s, %s)
                RETURNING *
                """,
                (user_id, plan_id, billing_interval, paystack_customer_code),
            )
            return dict(cur.fetchone())


def get_active_subscription(user_id: str) -> "dict | None":
    """Return the most recent active or trialing subscription for a user, or None."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT * FROM subscriptions
                WHERE user_id = %s AND status IN ('active', 'trialing')
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (user_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def update_subscription(sub_id: str, **kwargs) -> None:
    """Update arbitrary columns on a subscription row plus updated_at = NOW()."""
    if not kwargs:
        return
    fields = ["updated_at = NOW()"]
    values = []
    for key, val in kwargs.items():
        fields.append(f"{key} = %s")
        values.append(val)
    values.append(sub_id)
    sql = f"UPDATE subscriptions SET {', '.join(fields)} WHERE id = %s"
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, values)


def get_subscription_history(user_id: str) -> list:
    """Return all subscriptions for a user, newest first."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM subscriptions WHERE user_id = %s ORDER BY created_at DESC",
                (user_id,),
            )
            return [dict(row) for row in cur.fetchall()]


# ---------------------------------------------------------------------------
# Entitlements
# ---------------------------------------------------------------------------

def create_entitlement(
    user_id,
    resource_type,
    resource_id,
    source_type,
    source_id,
    expires_at=None,
) -> dict:
    """Insert a new entitlement and return the inserted row."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO entitlements (user_id, resource_type, resource_id, source_type, source_id, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (user_id, resource_type, resource_id, source_type, source_id, expires_at),
            )
            return dict(cur.fetchone())


def get_user_entitlements(user_id: str) -> list:
    """Return all active entitlements for a user, newest first."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT * FROM entitlements
                WHERE user_id = %s AND status = 'active'
                ORDER BY created_at DESC
                """,
                (user_id,),
            )
            return [dict(row) for row in cur.fetchall()]


def has_course_entitlement(user_id: str, course_slug: str) -> bool:
    """Return True if the user has an active, non-expired entitlement for the course."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1 FROM entitlements
                WHERE user_id = %s
                  AND resource_type = 'course'
                  AND resource_id = %s
                  AND status = 'active'
                  AND (expires_at IS NULL OR expires_at > NOW())
                """,
                (user_id, course_slug),
            )
            return cur.fetchone() is not None


def revoke_entitlement(entitlement_id: str) -> None:
    """Mark a single entitlement as revoked."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE entitlements SET status = 'revoked' WHERE id = %s",
                (entitlement_id,),
            )


def revoke_entitlements_by_source(source_type: str, source_id: str) -> None:
    """Mark all entitlements from a given source as revoked."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE entitlements SET status = 'revoked' WHERE source_type = %s AND source_id = %s",
                (source_type, source_id),
            )


# ---------------------------------------------------------------------------
# Coupons
# ---------------------------------------------------------------------------

def get_coupon_by_code(code: str) -> "dict | None":
    """Return an active coupon by its code (case-insensitive), or None."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM coupons WHERE code = UPPER(%s) AND is_active = TRUE",
                (code,),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def validate_coupon(code: str, user_id: str, order_total_kobo: int) -> dict:
    """
    Validate a coupon code and compute the discount.

    Returns a dict with keys:
      - valid (bool)
      - discount_kobo (int)
      - reason (str)
    """
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Fetch coupon
            cur.execute(
                "SELECT * FROM coupons WHERE code = UPPER(%s) AND is_active = TRUE",
                (code,),
            )
            coupon = cur.fetchone()
            if not coupon:
                return {"valid": False, "discount_kobo": 0, "reason": "Coupon not found or inactive"}

            coupon = dict(coupon)

            # Check expiry
            if coupon.get("expires_at") is not None:
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc)
                expires_at = coupon["expires_at"]
                # expires_at may be a datetime object (psycopg2 parses TIMESTAMPTZ)
                if isinstance(expires_at, datetime):
                    if expires_at.tzinfo is None:
                        expires_at = expires_at.replace(tzinfo=timezone.utc)
                    if now > expires_at:
                        return {"valid": False, "discount_kobo": 0, "reason": "Coupon has expired"}

            # Check global max_uses
            if coupon.get("max_uses") is not None:
                cur.execute(
                    "SELECT COUNT(*) AS cnt FROM coupon_redemptions WHERE coupon_id = %s",
                    (coupon["id"],),
                )
                total_uses = cur.fetchone()["cnt"]
                if total_uses >= coupon["max_uses"]:
                    return {"valid": False, "discount_kobo": 0, "reason": "Coupon usage limit reached"}

            # Check per-user limit
            if coupon.get("per_user_limit") is not None:
                cur.execute(
                    "SELECT COUNT(*) AS cnt FROM coupon_redemptions WHERE coupon_id = %s AND user_id = %s",
                    (coupon["id"], user_id),
                )
                user_uses = cur.fetchone()["cnt"]
                if user_uses >= coupon["per_user_limit"]:
                    return {"valid": False, "discount_kobo": 0, "reason": "You have already used this coupon"}

            # Calculate discount
            discount_type = coupon.get("discount_type", "flat")
            discount_value = coupon.get("discount_value", 0)
            max_discount_kobo = coupon.get("max_discount_kobo")

            if discount_type == "percent":
                discount_kobo = math.floor(order_total_kobo * discount_value / 100)
                if max_discount_kobo is not None:
                    discount_kobo = min(discount_kobo, max_discount_kobo)
            else:
                discount_kobo = int(discount_value)

            # Clamp to order total
            discount_kobo = min(discount_kobo, order_total_kobo)

            return {"valid": True, "discount_kobo": discount_kobo, "reason": ""}


def redeem_coupon(coupon_id: str, user_id: str, order_id: str, discount_kobo: int) -> None:
    """Record a coupon redemption."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO coupon_redemptions (coupon_id, user_id, order_id, discount_kobo)
                VALUES (%s, %s, %s, %s)
                """,
                (coupon_id, user_id, order_id, discount_kobo),
            )


# ---------------------------------------------------------------------------
# Webhooks
# ---------------------------------------------------------------------------

def store_webhook_event(
    provider,
    fingerprint,
    event_type,
    reference,
    payload,
    signature_verified,
) -> "dict | None":
    """
    Insert a webhook event.  Returns the inserted row dict, or None if the
    fingerprint already exists (duplicate event).
    """
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO webhook_events
                        (provider, event_fingerprint, event_type, reference, payload, signature_verified)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        provider,
                        fingerprint,
                        event_type,
                        reference,
                        psycopg2.extras.Json(payload),
                        signature_verified,
                    ),
                )
                return dict(cur.fetchone())
            except psycopg2.errors.UniqueViolation:
                conn.rollback()
                return None


def mark_webhook_processed(event_id: str, error: str = None) -> None:
    """Mark a webhook event as processed or failed."""
    processing_status = "processed" if error is None else "failed"
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE webhook_events
                SET processing_status = %s,
                    processed_at = NOW(),
                    error_message = %s
                WHERE id = %s
                """,
                (processing_status, error, event_id),
            )


# ---------------------------------------------------------------------------
# AI usage
# ---------------------------------------------------------------------------

def log_ai_usage(
    user_id,
    feature_key,
    provider,
    model,
    input_tokens,
    output_tokens,
    estimated_cost_kobo,
    status="success",
    plan_id=None,
    request_id=None,
) -> None:
    """Record a single AI feature invocation."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ai_usage_logs
                    (user_id, feature_key, provider, model,
                     input_tokens, output_tokens, estimated_cost_kobo,
                     status, plan_id, request_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    feature_key,
                    provider,
                    model,
                    input_tokens,
                    output_tokens,
                    estimated_cost_kobo,
                    status,
                    plan_id,
                    request_id,
                ),
            )


def get_ai_usage_this_month(user_id: str, feature_key: str) -> int:
    """Return the number of successful AI calls this calendar month for a user+feature."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS cnt FROM ai_usage_logs
                WHERE user_id = %s
                  AND feature_key = %s
                  AND status = 'success'
                  AND created_at >= date_trunc('month', NOW())
                """,
                (user_id, feature_key),
            )
            return cur.fetchone()["cnt"]


def get_ai_usage_summary() -> dict:
    """Return aggregated AI usage stats for the current month grouped by feature_key."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    feature_key,
                    COUNT(*) AS total_calls,
                    SUM(input_tokens + output_tokens) AS total_tokens,
                    SUM(estimated_cost_kobo) AS total_estimated_cost_kobo
                FROM ai_usage_logs
                WHERE created_at >= date_trunc('month', NOW())
                GROUP BY feature_key
                ORDER BY feature_key
                """
            )
            rows = [dict(row) for row in cur.fetchall()]
    return {"by_feature": rows}


# ---------------------------------------------------------------------------
# Refunds
# ---------------------------------------------------------------------------

def create_refund_request(
    payment_id,
    order_id,
    user_id,
    amount_kobo,
    reason,
) -> dict:
    """Insert a refund request and return the inserted row."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO refunds (payment_id, order_id, user_id, amount_kobo, reason)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING *
                """,
                (payment_id, order_id, user_id, amount_kobo, reason),
            )
            return dict(cur.fetchone())


def update_refund(
    refund_id,
    status,
    provider_refund_reference=None,
    processed_at=None,
) -> None:
    """Update a refund record's status and optionally other fields."""
    fields = ["status = %s"]
    values = [status]

    if provider_refund_reference is not None:
        fields.append("provider_refund_reference = %s")
        values.append(provider_refund_reference)
    if processed_at is not None:
        fields.append("processed_at = %s")
        values.append(processed_at)

    values.append(refund_id)
    sql = f"UPDATE refunds SET {', '.join(fields)} WHERE id = %s"

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, values)


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

def get_revenue_summary_v2() -> dict:
    """Return high-level revenue and subscription metrics."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT COALESCE(SUM(total_kobo), 0) AS total FROM orders WHERE status = 'paid'"
            )
            total_revenue_kobo = cur.fetchone()["total"]

            cur.execute(
                """
                SELECT COALESCE(SUM(total_kobo), 0) AS total FROM orders
                WHERE status = 'paid'
                  AND created_at >= date_trunc('month', NOW())
                """
            )
            revenue_this_month_kobo = cur.fetchone()["total"]

            cur.execute("SELECT COUNT(*) AS cnt FROM orders")
            total_orders = cur.fetchone()["cnt"]

            cur.execute("SELECT COUNT(*) AS cnt FROM orders WHERE status = 'paid'")
            paid_orders = cur.fetchone()["cnt"]

            cur.execute("SELECT COUNT(*) AS cnt FROM subscriptions")
            total_subscriptions = cur.fetchone()["cnt"]

            cur.execute(
                "SELECT COUNT(*) AS cnt FROM subscriptions WHERE status IN ('active', 'trialing')"
            )
            active_subscriptions = cur.fetchone()["cnt"]

            cur.execute("SELECT COALESCE(SUM(amount_kobo), 0) AS total FROM refunds")
            total_refunds_kobo = cur.fetchone()["total"]

    return {
        "total_revenue_kobo": total_revenue_kobo,
        "revenue_this_month_kobo": revenue_this_month_kobo,
        "total_orders": total_orders,
        "paid_orders": paid_orders,
        "total_subscriptions": total_subscriptions,
        "active_subscriptions": active_subscriptions,
        "total_refunds_kobo": total_refunds_kobo,
    }


def get_all_subscriptions_admin(limit=100) -> list:
    """Return subscriptions ordered by created_at desc, up to limit."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM subscriptions ORDER BY created_at DESC LIMIT %s",
                (limit,),
            )
            return [dict(row) for row in cur.fetchall()]


def get_all_orders_admin(limit=100) -> list:
    """Return orders ordered by created_at desc, up to limit."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM orders ORDER BY created_at DESC LIMIT %s",
                (limit,),
            )
            return [dict(row) for row in cur.fetchall()]


def get_all_audit_logs(limit=100) -> list:
    """Return audit log entries ordered by created_at desc, up to limit."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT %s",
                (limit,),
            )
            return [dict(row) for row in cur.fetchall()]


def write_audit_log(
    actor_user_id,
    action,
    entity_type=None,
    entity_id=None,
    previous_values=None,
    new_values=None,
    ip_address=None,
) -> None:
    """Insert an audit log entry. JSONB fields are wrapped with psycopg2.extras.Json."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO audit_logs
                    (actor_user_id, action, entity_type, entity_id,
                     previous_values, new_values, ip_address)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    actor_user_id,
                    action,
                    entity_type,
                    entity_id,
                    psycopg2.extras.Json(previous_values),
                    psycopg2.extras.Json(new_values),
                    ip_address,
                ),
            )


# ---------------------------------------------------------------------------
# Referral rewards
# ---------------------------------------------------------------------------

def create_referral_reward(
    referrer_user_id,
    referred_user_id,
    qualifying_order_id,
    reward_value_kobo,
) -> dict:
    """Insert a referral reward and return the inserted row."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO referral_rewards
                    (referrer_user_id, referred_user_id, qualifying_order_id, reward_value_kobo)
                VALUES (%s, %s, %s, %s)
                RETURNING *
                """,
                (referrer_user_id, referred_user_id, qualifying_order_id, reward_value_kobo),
            )
            return dict(cur.fetchone())


def get_referral_rewards(user_id: str) -> list:
    """Return all referral rewards earned by a user, newest first."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT * FROM referral_rewards
                WHERE referrer_user_id = %s
                ORDER BY created_at DESC
                """,
                (user_id,),
            )
            return [dict(row) for row in cur.fetchall()]


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------

def init_monetisation_db() -> None:
    """
    Read and execute the monetisation migration SQL.
    Logs a warning and returns early if DATABASE_URL is not set.
    """
    if not os.getenv("DATABASE_URL", "").strip():
        logger.warning(
            "DATABASE_URL not set — skipping monetisation database initialisation."
        )
        return

    sql_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "docs",
        "migration_v2_monetisation.sql",
    )
    with open(sql_path, "r", encoding="utf-8") as fh:
        migration_sql = fh.read()

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(migration_sql)

    logger.info("Monetisation DB migration applied successfully.")
