import hashlib
import json
import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel

from app.auth import get_current_user, require_user
from app.admin import verify_admin_token
from app.monetisation import db as mdb
from app.monetisation import paystack as mps
from app.monetisation import entitlements as ment
from app.monetisation.checkout import initialize_checkout, fulfill_order, process_webhook_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api', tags=['monetisation'])


# ---------------------------------------------------------------------------
# Request body models
# ---------------------------------------------------------------------------

class CheckoutRequest(BaseModel):
    product_type: str
    product_id: str
    billing_interval: str = 'monthly'
    coupon_code: Optional[str] = None


class CouponValidateRequest(BaseModel):
    code: str
    product_type: str
    product_id: str


class AdminGrantEntitlementRequest(BaseModel):
    user_id: str
    resource_type: str
    resource_id: str
    source_type: str
    expires_at: Optional[str] = None


class AdminRevokeEntitlementRequest(BaseModel):
    entitlement_id: str


class AdminCreateCouponRequest(BaseModel):
    code: str
    discount_type: str
    discount_value: int
    max_discount_kobo: Optional[int] = None
    max_uses: Optional[int] = None
    per_user_limit: int = 1
    starts_at: Optional[str] = None
    expires_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------

@router.get('/pricing/plans')
async def pricing_plans():
    return {'plans': mdb.get_all_plans()}


@router.get('/pricing/courses')
async def pricing_courses():
    return {'courses': mdb.get_course_prices()}


@router.get('/pricing/bundles')
async def pricing_bundles():
    return {'bundles': mdb.get_all_bundles()}


@router.get('/pricing/compare')
async def pricing_compare():
    return {'plans': mdb.get_all_plans(), 'bundles': mdb.get_all_bundles()}


# ---------------------------------------------------------------------------
# Authenticated endpoints
# ---------------------------------------------------------------------------

@router.post('/checkout/initialize')
async def checkout_initialize(body: CheckoutRequest, request: Request, user=Depends(require_user)):
    frontend_url = request.headers.get('origin', '')
    result = initialize_checkout(user.learner_id, user.email, body.product_type, body.product_id, body.billing_interval, body.coupon_code, frontend_url or None)
    return result


@router.get('/payments/verify/{reference}')
async def payment_verify(reference: str, user=Depends(require_user)):
    payment = mdb.get_payment_by_reference(reference)
    if not payment:
        raise HTTPException(404, 'Payment not found')
    if str(payment['user_id']) != user.learner_id:
        raise HTTPException(403, 'Forbidden')
    if payment['status'] == 'success':
        # Already paid — return access status so frontend can unlock courses
        order = mdb.get_order(str(payment['order_id']))
        entitlements = mdb.get_user_entitlements(user.learner_id)
        return {
            'status': 'success',
            'payment': dict(payment),
            'entitlements': entitlements,
            'idempotent': True,
        }
    result = fulfill_order(str(payment['order_id']), reference)
    return result


@router.get('/subscriptions/me')
async def subscription_me(user=Depends(require_user)):
    return {'subscription': mdb.get_active_subscription(user.learner_id)}


@router.get('/subscriptions/history')
async def subscription_history(user=Depends(require_user)):
    return {'subscriptions': mdb.get_subscription_history(user.learner_id)}


@router.post('/subscriptions/cancel')
async def subscription_cancel(user=Depends(require_user)):
    sub = mdb.get_active_subscription(user.learner_id)
    if not sub:
        raise HTTPException(404, 'No active subscription')
    if sub.get('paystack_subscription_code') and sub.get('paystack_email_token_encrypted'):
        mps.cancel_subscription(sub['paystack_subscription_code'], sub['paystack_email_token_encrypted'])
    mdb.update_subscription(str(sub['id']), status='cancelled', cancelled_at=__import__('datetime').datetime.utcnow())
    return {'success': True}


@router.get('/entitlements/me')
async def entitlements_me(user=Depends(require_user)):
    return {'entitlements': mdb.get_user_entitlements(user.learner_id)}


@router.get('/entitlements/course/{course_slug}')
async def entitlements_course(course_slug: str, user=Depends(require_user)):
    return ment.resolve_access(user.learner_id, course_slug)


@router.get('/entitlements/features')
async def entitlements_features(user=Depends(require_user)):
    return {
        'ai_tutor':     ment.check_ai_quota(user.learner_id, 'ai_tutor'),
        'code_explain': ment.check_ai_quota(user.learner_id, 'code_explain'),
        'debug':        ment.check_ai_quota(user.learner_id, 'debug'),
        'advanced_ai':  ment.check_ai_quota(user.learner_id, 'advanced_ai'),
    }


@router.post('/coupons/validate')
async def coupon_validate(body: CouponValidateRequest, user=Depends(require_user)):
    # Determine order total for validation context
    total = 0
    try:
        if body.product_type == 'course':
            cp = mdb.get_course_price(body.product_id)
            total = cp['price_kobo'] if cp else 0
        elif body.product_type == 'bundle':
            b = mdb.get_bundle_by_slug(body.product_id)
            total = b['price_kobo'] if b else 0
        elif body.product_type == 'subscription':
            p = mdb.get_plan_by_slug(body.product_id)
            total = p['monthly_price_kobo'] if p else 0
    except Exception:
        pass
    return mdb.validate_coupon(body.code, user.learner_id, total)


@router.get('/orders/me')
async def orders_me(user=Depends(require_user)):
    return {'orders': mdb.get_orders_for_user(user.learner_id)}


# ---------------------------------------------------------------------------
# Webhook endpoint
# ---------------------------------------------------------------------------

@router.post('/payments/paystack/webhook')
async def paystack_webhook(request: Request, background_tasks: BackgroundTasks):
    raw_body = await request.body()
    sig = request.headers.get('x-paystack-signature', '')
    if not mps.validate_webhook_signature(raw_body, sig):
        raise HTTPException(status_code=400, detail='Invalid signature')
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail='Invalid JSON')
    event_type = payload.get('event', '')
    data = payload.get('data', {})
    reference = (data.get('reference') or data.get('transaction_reference') or '')
    amount = str(data.get('amount', ''))
    fingerprint = hashlib.sha256(f'{event_type}:{reference}:{amount}'.encode()).hexdigest()
    event = mdb.store_webhook_event('paystack', fingerprint, event_type, reference, payload, True)
    if event is None:
        return {'status': 'duplicate'}
    background_tasks.add_task(_process_webhook_bg, event_type, payload, str(event['id']))
    return {'status': 'received'}


async def _process_webhook_bg(event_type: str, payload: dict, event_id: str):
    try:
        process_webhook_event(event_type, payload)
        mdb.mark_webhook_processed(event_id)
    except Exception as e:
        logger.error('Webhook processing error: %s', e)
        mdb.mark_webhook_processed(event_id, error=str(e))


# ---------------------------------------------------------------------------
# Admin helpers
# ---------------------------------------------------------------------------

def _check_admin(request: Request):
    auth = request.headers.get('authorization', '')
    token = auth.removeprefix('Bearer ').strip()
    if not verify_admin_token(token):
        raise HTTPException(status_code=401, detail='Invalid admin token')


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------

@router.get('/admin/revenue/summary')
async def admin_revenue_summary(request: Request):
    _check_admin(request)
    return mdb.get_revenue_summary_v2()


@router.get('/admin/revenue/transactions')
async def admin_revenue_transactions(request: Request):
    _check_admin(request)
    return {'orders': mdb.get_all_orders_admin()}


@router.get('/admin/subscriptions')
async def admin_subscriptions(request: Request):
    _check_admin(request)
    return {'subscriptions': mdb.get_all_subscriptions_admin()}


@router.get('/admin/orders')
async def admin_orders(request: Request):
    _check_admin(request)
    return {'orders': mdb.get_all_orders_admin()}


@router.post('/admin/entitlements/grant')
async def admin_grant_entitlement(request: Request, body: AdminGrantEntitlementRequest):
    _check_admin(request)
    import datetime
    expires_at = datetime.datetime.fromisoformat(body.expires_at) if body.expires_at else None
    e = mdb.create_entitlement(body.user_id, body.resource_type, body.resource_id, body.source_type, 'admin', expires_at)
    mdb.write_audit_log('admin', 'grant_entitlement', body.resource_type, body.resource_id, new_values={'user_id': body.user_id})
    return {'entitlement': e}


@router.post('/admin/entitlements/revoke')
async def admin_revoke_entitlement(request: Request, body: AdminRevokeEntitlementRequest):
    _check_admin(request)
    mdb.revoke_entitlement(body.entitlement_id)
    mdb.write_audit_log('admin', 'revoke_entitlement', 'entitlement', body.entitlement_id)
    return {'success': True}


@router.get('/admin/ai-usage')
async def admin_ai_usage(request: Request):
    _check_admin(request)
    return mdb.get_ai_usage_summary()


@router.get('/admin/audit-logs')
async def admin_audit_logs(request: Request):
    _check_admin(request)
    return {'logs': mdb.get_all_audit_logs()}


@router.get('/admin/coupons')
async def admin_get_coupons(request: Request):
    _check_admin(request)
    with __import__('app.db', fromlist=['get_db']).get_db() as conn:
        import psycopg2.extras
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT * FROM coupons ORDER BY created_at DESC')
            return {'coupons': [dict(r) for r in cur.fetchall()]}


@router.post('/admin/coupons')
async def admin_create_coupon(request: Request, body: AdminCreateCouponRequest):
    _check_admin(request)
    with __import__('app.db', fromlist=['get_db']).get_db() as conn:
        import psycopg2.extras
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                'INSERT INTO coupons (code, discount_type, discount_value, max_discount_kobo, max_uses, per_user_limit, starts_at, expires_at) VALUES (UPPER(%s), %s, %s, %s, %s, %s, %s, %s) RETURNING *',
                (body.code, body.discount_type, body.discount_value, body.max_discount_kobo, body.max_uses, body.per_user_limit, body.starts_at, body.expires_at),
            )
            row = dict(cur.fetchone())
    return {'coupon': row}


@router.patch('/admin/coupons/{coupon_id}')
async def admin_update_coupon(request: Request, coupon_id: str):
    _check_admin(request)
    body = await request.json()
    allowed = {'discount_type', 'discount_value', 'max_discount_kobo', 'max_uses', 'per_user_limit', 'starts_at', 'expires_at', 'is_active'}
    updates = {k: v for k, v in body.items() if k in allowed}
    if not updates:
        raise HTTPException(400, 'No valid fields to update')
    set_clause = ', '.join(f'{k}=%s' for k in updates)
    with __import__('app.db', fromlist=['get_db']).get_db() as conn:
        import psycopg2.extras
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(f'UPDATE coupons SET {set_clause} WHERE id=%s RETURNING *', list(updates.values()) + [coupon_id])
            row = cur.fetchone()
    if not row:
        raise HTTPException(404, 'Coupon not found')
    return {'coupon': dict(row)}
