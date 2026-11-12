from app.monetisation.db import (
    get_plan_by_slug,
    get_active_subscription,
    get_plan_by_id,
    has_course_entitlement,
    get_user_entitlements,
    create_entitlement,
    revoke_entitlements_by_source,
    get_ai_usage_this_month,
)

FREE_COURSES = [
    'python-fundamentals',
    'ai-fundamentals',
    'prompt-engineering',
    'ai-tools-productivity',
]

PRO_COURSES = FREE_COURSES + [
    'advanced-python',
    'python-web-dev',
    'python-automation',
    'python-data-analysis',
    'python-cybersecurity',
    'generative-ai',
    'ai-app-development',
]

PREMIUM_COURSES = [
    'python-fundamentals',
    'advanced-python',
    'python-web-dev',
    'python-automation',
    'python-data-analysis',
    'python-cybersecurity',
    'data-science',
    'ai-fundamentals',
    'prompt-engineering',
    'generative-ai',
    'ai-tools-productivity',
    'ai-app-development',
    'ai-agents-automation',
    'rag-llm-development',
    'ml-fundamentals',
    'supervised-ml',
    'unsupervised-ml',
    'deep-learning',
    'nlp',
    'computer-vision',
    'reinforcement-learning',
    'mlops',
    'advanced-ai-ml-engineering',
]

PLAN_COURSES = {
    'free': FREE_COURSES,
    'pro': PRO_COURSES,
    'premium': PREMIUM_COURSES,
}

# Default AI quota limits per plan slug
PLAN_LIMITS = {
    'free':    {'ai_tutor': 20,   'code_explain': 5,   'debug': 3,   'advanced_ai': 0},
    'pro':     {'ai_tutor': 200,  'code_explain': 100, 'debug': 50,  'advanced_ai': 20},
    'premium': {'ai_tutor': 1000, 'code_explain': 500, 'debug': 200, 'advanced_ai': 100},
}


def resolve_access(user_id: str, course_slug: str) -> dict:
    """Return {'allowed': bool, 'reason': str, 'source': str} for the given user and course."""
    # 1. Free courses are always accessible
    if course_slug in FREE_COURSES:
        return {'allowed': True, 'reason': 'free course', 'source': 'free'}

    # 2. Check individual entitlements
    if has_course_entitlement(user_id, course_slug):
        return {'allowed': True, 'reason': 'entitlement', 'source': 'entitlement'}

    # 3. Check active subscription
    subscription = get_active_subscription(user_id)
    if subscription:
        plan = get_plan_by_id(subscription['plan_id'])
        if plan:
            plan_slug = plan.get('slug', 'free')
            course_list = PLAN_COURSES.get(plan_slug, [])
            if course_slug in course_list:
                return {'allowed': True, 'reason': 'subscription', 'source': 'subscription'}

    # 4. No access
    return {'allowed': False, 'reason': 'no access', 'source': 'none'}


def get_plan_quota(user_id: str, feature_key: str) -> dict:
    """Return {'limit': int, 'used': int, 'remaining': int, 'period': 'monthly'}."""
    subscription = get_active_subscription(user_id)
    plan_slug = 'free'
    if subscription:
        plan = get_plan_by_id(subscription['plan_id'])
        if plan:
            plan_slug = plan.get('slug', 'free')

    plan_limits = PLAN_LIMITS.get(plan_slug, PLAN_LIMITS['free'])
    limit = plan_limits.get(feature_key, 0)
    used = get_ai_usage_this_month(user_id, feature_key)
    remaining = max(0, limit - used)

    return {
        'limit': limit,
        'used': used,
        'remaining': remaining,
        'period': 'monthly',
    }


def check_ai_quota(user_id: str, feature_key: str) -> dict:
    """Return {'allowed': bool, 'used': int, 'limit': int, 'reason': str}."""
    quota = get_plan_quota(user_id, feature_key)
    if quota['remaining'] > 0:
        return {
            'allowed': True,
            'used': quota['used'],
            'limit': quota['limit'],
            'reason': 'within limit',
        }
    return {
        'allowed': False,
        'used': quota['used'],
        'limit': quota['limit'],
        'reason': 'monthly limit reached',
    }


def grant_subscription_entitlements(
    user_id: str,
    plan_slug: str,
    subscription_id: str,
    expires_at,
) -> list:
    """Create course entitlements for every course in the plan and return them."""
    course_list = PLAN_COURSES.get(plan_slug, FREE_COURSES)
    created = []
    for course_slug in course_list:
        entitlement = create_entitlement(
            user_id,
            'course',
            course_slug,
            'subscription',
            subscription_id,
            expires_at,
        )
        created.append(entitlement)
    return created


def revoke_subscription_entitlements(subscription_id: str) -> None:
    """Revoke all entitlements tied to the given subscription."""
    revoke_entitlements_by_source('subscription', subscription_id)
