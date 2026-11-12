from app.monetisation import db as mdb
from app.monetisation import paystack as mps
from app.monetisation import entitlements as ment
import logging
import os

logger = logging.getLogger(__name__)


def initialize_checkout(
    user_id: str,
    email: str,
    product_type: str,
    product_id: str,
    billing_interval: str = 'monthly',
    coupon_code: str = None,
    frontend_url: str = None,
) -> dict:
    if product_type == 'subscription':
        plan = mdb.get_plan_by_slug(product_id)
        if not plan:
            raise ValueError(f'Plan not found: {product_id}')
        price = plan['monthly_price_kobo'] if billing_interval == 'monthly' else plan['annual_price_kobo']
    elif product_type == 'course':
        cp = mdb.get_course_price(product_id)
        if not cp:
            raise ValueError(f'Course price not found: {product_id}')
        price = cp['price_kobo']
    elif product_type == 'bundle':
        b = mdb.get_bundle_by_slug(product_id)
        if not b:
            raise ValueError(f'Bundle not found: {product_id}')
        price = b['price_kobo']
    else:
        raise ValueError(f'Unknown product_type: {product_type}')

    coupon = None
    discount_kobo = 0
    if coupon_code:
        result = mdb.validate_coupon(coupon_code, user_id, price)
        if result and result.get('valid'):
            discount_kobo = result['discount_kobo']
            coupon = result

    total_kobo = price - discount_kobo

    order = mdb.create_order(user_id, product_type, product_id, price, discount_kobo, total_kobo)
    payment = mdb.create_payment(order['id'], user_id, f'MPT-{order["order_number"]}', total_kobo)

    callback_url = frontend_url or os.environ.get(
        'FRONTEND_CALLBACK_URL', 'https://www.mypytutor.com.ng/payment/callback'
    )

    tx_result = mps.initialize_transaction(
        email,
        total_kobo,
        payment['provider_reference'],
        callback_url,
        metadata={
            'order_id': str(order['id']),
            'user_id': user_id,
            'product_type': product_type,
            'product_id': product_id,
        },
    )

    if coupon:
        mdb.redeem_coupon(coupon['id'], user_id, order['id'], discount_kobo)

    return {
        'checkout_url': tx_result['authorization_url'],
        'reference': tx_result['reference'],
        'order_id': str(order['id']),
        'amount_kobo': price,
        'discount_kobo': discount_kobo,
        'total_kobo': total_kobo,
    }


def fulfill_order(order_id: str, payment_reference: str) -> dict:
    order = mdb.get_order(order_id)
    if order['status'] == 'paid':
        return {'success': True, 'order_id': order_id, 'entitlements_created': 0, 'idempotent': True}

    payment = mdb.get_payment_by_reference(payment_reference)
    if payment is None:
        raise ValueError(f'Payment not found for reference: {payment_reference}')

    txn = mps.verify_transaction(payment_reference)

    if txn['status'] != 'success':
        raise ValueError(f'Transaction not successful: {txn["status"]}')
    if txn['amount'] != order['total_kobo']:
        raise ValueError('Amount mismatch')
    if txn['currency'] != 'NGN':
        raise ValueError('Currency mismatch')

    import datetime
    now = datetime.datetime.utcnow()

    mdb.update_payment(
        payment['id'],
        'success',
        provider_transaction_id=str(txn.get('id', '')),
        channel=txn.get('channel'),
        gateway_response=txn,
        verified_at=now,
    )
    mdb.update_order_status(order_id, 'paid', paid_at=now)

    entitlements = _grant_access(mdb.get_order(order_id))

    # ── Post-fulfillment emails (subscription activated + referral reward) ──
    try:
        import psycopg2.extras as _pex
        from app.db import get_db as _get_db

        # 1. Look up user email and name
        _user_email = ""
        _user_name  = ""
        try:
            with _get_db() as _conn:
                with _conn.cursor(cursor_factory=_pex.RealDictCursor) as _cur:
                    _cur.execute(
                        "SELECT email, name FROM email_accounts WHERE learner_id = %s",
                        (order['user_id'],),
                    )
                    _row = _cur.fetchone()
                    if not _row:
                        _cur.execute(
                            "SELECT email, display_name AS name FROM user_profiles WHERE learner_id = %s",
                            (order['user_id'],),
                        )
                        _row = _cur.fetchone()
                    if _row:
                        _user_email = _row.get("email", "") or ""
                        _user_name  = _row.get("name", "") or ""
        except Exception as _ue:
            logger.debug("Post-fulfillment user lookup failed: %s", _ue)

        # 2. Look up plan name and AI quota
        _plan_name  = order.get("item_id", "")
        _ai_limit   = 300
        if order.get("order_type") == "subscription":
            try:
                _plan = mdb.get_plan_by_slug(order["item_id"])
                if _plan:
                    _plan_name = _plan.get("name", order["item_id"])
                    _ai_limit  = int(_plan.get("ai_quota_per_day", 300))
            except Exception:
                pass

        # 3. Send subscription activated email (only for actual subscription orders)
        if _user_email and order.get("order_type") == "subscription":
            from app.services.email_service import send_subscription_activated as _ssa
            _ssa(_user_email, _plan_name, user_name=_user_name, ai_limit=_ai_limit)

        # 4. Referral reward email
        if order.get("referral_id") and _user_email:
            try:
                _referrer_email = ""
                _referrer_name  = ""
                with _get_db() as _conn2:
                    with _conn2.cursor(cursor_factory=_pex.RealDictCursor) as _cur2:
                        _cur2.execute(
                            "SELECT email, name FROM email_accounts WHERE learner_id = %s",
                            (order["referral_id"],),
                        )
                        _rrow = _cur2.fetchone()
                        if _rrow:
                            _referrer_email = _rrow.get("email", "") or ""
                            _referrer_name  = _rrow.get("name", "") or ""
                if _referrer_email:
                    _reward_naira = int(order["total_kobo"] * 0.15) // 100
                    from app.services.email_service import send_referral_reward_credited as _srrc
                    _srrc(
                        _referrer_email,
                        referred_email=_user_email,
                        plan_name=_plan_name,
                        reward_naira=_reward_naira,
                        referrer_name=_referrer_name,
                    )
            except Exception as _rre:
                logger.debug("Referral reward email failed (non-fatal): %s", _rre)

    except Exception as _email_exc:
        logger.warning("Post-fulfillment email failed: %s", _email_exc)

    if order.get('referral_id'):
        try:
            mdb.create_referral_reward(
                order['referral_id'],
                order['user_id'],
                order_id,
                int(order['total_kobo'] * 0.15),
            )
        except Exception as e:
            logger.warning('Referral reward creation failed: %s', e)

    return {'success': True, 'order_id': order_id, 'entitlements_created': len(entitlements)}


def _grant_access(order: dict) -> list:
    order_type = order['order_type']
    user_id = order['user_id']
    item_id = order['item_id']

    if order_type == 'subscription':
        plan = mdb.get_plan_by_slug(item_id)
        sub = mdb.create_subscription(user_id, str(plan['id']), order.get('billing_interval', 'monthly'), '')
        import datetime
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(
            days=365 if order.get('billing_interval') == 'annual' else 31
        )
        return ment.grant_subscription_entitlements(user_id, item_id, str(sub['id']), expires_at)
    elif order_type == 'course':
        e = mdb.create_entitlement(user_id, 'course', item_id, 'order', str(order['id']))
        return [e]
    elif order_type == 'bundle':
        bundle = mdb.get_bundle_by_slug(item_id)
        result = []
        for course_slug in (bundle.get('courses') or []):
            e = mdb.create_entitlement(user_id, 'course', course_slug, 'order', str(order['id']))
            result.append(e)
        return result
    return []


def process_webhook_event(event_type: str, payload: dict) -> None:
    data = payload.get('data', {})
    reference = (data.get('reference') or data.get('transaction_reference') or '')
    try:
        if event_type == 'charge.success':
            payment = mdb.get_payment_by_reference(reference)
            if payment:
                fulfill_order(str(payment['order_id']), reference)
        elif event_type == 'subscription.create':
            sub_code = data.get('subscription_code', '')
            email_token = data.get('email_token', '')
            customer_code = data.get('customer', {}).get('customer_code', '')
            if customer_code and sub_code:
                with __import__('app.db', fromlist=['get_db']).get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE subscriptions SET paystack_subscription_code=%s, paystack_email_token_encrypted=%s, status='active', updated_at=NOW() WHERE paystack_customer_code=%s",
                            (sub_code, email_token, customer_code),
                        )
        elif event_type == 'subscription.disable':
            sub_code = data.get('subscription_code', '')
            if sub_code:
                with __import__('app.db', fromlist=['get_db']).get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE subscriptions SET status='cancelled', cancelled_at=NOW(), updated_at=NOW() WHERE paystack_subscription_code=%s",
                            (sub_code,),
                        )
        elif event_type == 'invoice.payment_failed':
            sub_code = (
                data.get('subscription', {}).get('subscription_code', '')
                if isinstance(data.get('subscription'), dict)
                else ''
            )
            if sub_code:
                mdb.update_subscription  # find sub and update status
                with __import__('app.db', fromlist=['get_db']).get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE subscriptions SET status='past_due', updated_at=NOW() WHERE paystack_subscription_code=%s",
                            (sub_code,),
                        )
                mdb.write_audit_log(None, 'invoice.payment_failed', 'subscription', sub_code, new_values=data)
        elif event_type == 'invoice.update':
            sub_code = (
                data.get('subscription', {}).get('subscription_code', '')
                if isinstance(data.get('subscription'), dict)
                else ''
            )
            next_date_str = data.get('next_payment_date') or data.get('next_payment_attempt')
            if sub_code and next_date_str:
                with __import__('app.db', fromlist=['get_db']).get_db() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE subscriptions SET next_payment_date=%s, updated_at=NOW() WHERE paystack_subscription_code=%s",
                            (next_date_str, sub_code),
                        )
    except Exception as e:
        logger.error('process_webhook_event error (%s): %s', event_type, e)
