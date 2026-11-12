-- =============================================================================
-- Migration: v2 Monetisation Schema
-- Idempotent: safe to run multiple times
-- All monetary values stored in kobo (BIGINT)
-- user_id columns as TEXT
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. subscription_plans
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS subscription_plans (
    id                          UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    name                        VARCHAR(60),
    slug                        VARCHAR(60) UNIQUE,
    description                 TEXT,
    monthly_price_kobo          BIGINT      DEFAULT 0,
    annual_price_kobo           BIGINT      DEFAULT 0,
    currency                    VARCHAR(3)  DEFAULT 'NGN',
    is_active                   BOOLEAN     DEFAULT TRUE,
    features                    JSONB,
    ai_tutor_monthly_limit      INT         DEFAULT 20,
    code_explain_monthly_limit  INT         DEFAULT 5,
    debug_monthly_limit         INT         DEFAULT 3,
    advanced_ai_monthly_limit   INT         DEFAULT 0,
    created_at                  TIMESTAMPTZ DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- 2. plan_features
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS plan_features (
    id            UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    plan_id       UUID        REFERENCES subscription_plans(id),
    feature_key   VARCHAR(80),
    enabled       BOOLEAN     DEFAULT TRUE,
    limit_value   BIGINT,
    limit_period  VARCHAR(20),
    metadata      JSONB
);

-- ---------------------------------------------------------------------------
-- 3. course_prices
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS course_prices (
    id                   UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    course_slug          VARCHAR(120) UNIQUE,
    price_kobo           BIGINT      NOT NULL,
    currency             VARCHAR(3)  DEFAULT 'NGN',
    access_duration_days INT,
    is_active            BOOLEAN     DEFAULT TRUE,
    effective_from       TIMESTAMPTZ DEFAULT NOW(),
    effective_until      TIMESTAMPTZ,
    created_at           TIMESTAMPTZ DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- 4. bundles
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bundles (
    id                   UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    name                 VARCHAR(120),
    slug                 VARCHAR(120) UNIQUE,
    description          TEXT,
    price_kobo           BIGINT      NOT NULL,
    currency             VARCHAR(3)  DEFAULT 'NGN',
    access_duration_days INT,
    is_active            BOOLEAN     DEFAULT TRUE,
    created_at           TIMESTAMPTZ DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- 5. bundle_courses
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bundle_courses (
    id          UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    bundle_id   UUID        REFERENCES bundles(id) ON DELETE CASCADE,
    course_slug VARCHAR(120) NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (bundle_id, course_slug)
);

-- ---------------------------------------------------------------------------
-- 6. subscriptions
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS subscriptions (
    id                            UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id                       TEXT        NOT NULL,
    plan_id                       UUID        REFERENCES subscription_plans(id),
    billing_interval              VARCHAR(10) NOT NULL,
    status                        VARCHAR(20) DEFAULT 'pending',
    provider                      VARCHAR(30) DEFAULT 'paystack',
    paystack_customer_code        VARCHAR(100),
    paystack_subscription_code    VARCHAR(100),
    paystack_email_token_encrypted TEXT,
    current_period_start          TIMESTAMPTZ,
    current_period_end            TIMESTAMPTZ,
    next_payment_date             TIMESTAMPTZ,
    cancel_at_period_end          BOOLEAN     DEFAULT FALSE,
    cancelled_at                  TIMESTAMPTZ,
    created_at                    TIMESTAMPTZ DEFAULT NOW(),
    updated_at                    TIMESTAMPTZ DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- 7. orders
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS orders (
    id              UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id         TEXT        NOT NULL,
    order_number    VARCHAR(60) NOT NULL UNIQUE,
    order_type      VARCHAR(30) NOT NULL,
    item_id         TEXT        NOT NULL,
    subtotal_kobo   BIGINT      NOT NULL CHECK (subtotal_kobo >= 0),
    discount_kobo   BIGINT      NOT NULL DEFAULT 0 CHECK (discount_kobo >= 0),
    total_kobo      BIGINT      NOT NULL CHECK (total_kobo >= 0),
    currency        VARCHAR(3)  DEFAULT 'NGN',
    status          VARCHAR(20) DEFAULT 'pending',
    coupon_id       UUID,
    referral_id     TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    paid_at         TIMESTAMPTZ
);

-- ---------------------------------------------------------------------------
-- 8. payments
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS payments (
    id                      UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    order_id                UUID        NOT NULL REFERENCES orders(id),
    user_id                 TEXT        NOT NULL,
    provider                VARCHAR(30) DEFAULT 'paystack',
    provider_reference      VARCHAR(100) NOT NULL UNIQUE,
    provider_transaction_id VARCHAR(100),
    amount_kobo             BIGINT      NOT NULL CHECK (amount_kobo >= 0),
    currency                VARCHAR(3)  DEFAULT 'NGN',
    status                  VARCHAR(20) DEFAULT 'pending',
    channel                 VARCHAR(50),
    gateway_response        JSONB,
    verified_at             TIMESTAMPTZ,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- 9. entitlements
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS entitlements (
    id            UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id       TEXT        NOT NULL,
    resource_type VARCHAR(30) NOT NULL,
    resource_id   TEXT        NOT NULL,
    source_type   VARCHAR(30) NOT NULL,
    source_id     TEXT        NOT NULL,
    starts_at     TIMESTAMPTZ DEFAULT NOW(),
    expires_at    TIMESTAMPTZ,
    status        VARCHAR(20) DEFAULT 'active',
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- 10. coupons
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS coupons (
    id                UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    code              VARCHAR(60) NOT NULL UNIQUE,
    discount_type     VARCHAR(20) NOT NULL,
    discount_value    BIGINT      NOT NULL,
    max_discount_kobo BIGINT,
    max_uses          INT,
    per_user_limit    INT         DEFAULT 1,
    starts_at         TIMESTAMPTZ,
    expires_at        TIMESTAMPTZ,
    is_active         BOOLEAN     DEFAULT TRUE,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- 11. coupon_redemptions
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS coupon_redemptions (
    id            UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    coupon_id     UUID        NOT NULL REFERENCES coupons(id),
    user_id       TEXT        NOT NULL,
    order_id      UUID        NOT NULL REFERENCES orders(id),
    discount_kobo BIGINT      NOT NULL,
    redeemed_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- 12. ai_usage_logs
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ai_usage_logs (
    id                   UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id              TEXT        NOT NULL,
    plan_id              UUID,
    provider             VARCHAR(50),
    model                VARCHAR(100),
    feature_key          VARCHAR(50),
    request_id           TEXT,
    input_tokens         INT         DEFAULT 0,
    output_tokens        INT         DEFAULT 0,
    estimated_cost_kobo  INT         DEFAULT 0,
    status               VARCHAR(20) DEFAULT 'success',
    created_at           TIMESTAMPTZ DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- 13. webhook_events
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS webhook_events (
    id                  UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    provider            VARCHAR(30) DEFAULT 'paystack',
    event_fingerprint   VARCHAR(150) NOT NULL UNIQUE,
    event_type          VARCHAR(100) NOT NULL,
    provider_reference  VARCHAR(100),
    payload             JSONB       NOT NULL,
    signature_verified  BOOLEAN     DEFAULT FALSE,
    processing_status   VARCHAR(20) DEFAULT 'received',
    received_at         TIMESTAMPTZ DEFAULT NOW(),
    processed_at        TIMESTAMPTZ,
    error_message       TEXT
);

-- ---------------------------------------------------------------------------
-- 14. refunds
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS refunds (
    id                      UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    payment_id              UUID        NOT NULL REFERENCES payments(id),
    order_id                UUID        NOT NULL REFERENCES orders(id),
    user_id                 TEXT        NOT NULL,
    provider_refund_reference TEXT,
    amount_kobo             BIGINT      NOT NULL,
    reason                  TEXT,
    status                  VARCHAR(20) DEFAULT 'pending',
    requested_at            TIMESTAMPTZ DEFAULT NOW(),
    processed_at            TIMESTAMPTZ
);

-- ---------------------------------------------------------------------------
-- 15. referral_rewards
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS referral_rewards (
    id                  UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    referrer_user_id    TEXT        NOT NULL,
    referred_user_id    TEXT        NOT NULL,
    qualifying_order_id UUID        REFERENCES orders(id),
    reward_type         VARCHAR(30) DEFAULT 'cash',
    reward_value_kobo   BIGINT      NOT NULL,
    reward_status       VARCHAR(20) DEFAULT 'pending',
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    approved_at         TIMESTAMPTZ,
    paid_at             TIMESTAMPTZ
);

-- ---------------------------------------------------------------------------
-- 16. audit_logs
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_logs (
    id              UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    actor_user_id   TEXT,
    action          VARCHAR(100) NOT NULL,
    entity_type     VARCHAR(50),
    entity_id       TEXT,
    previous_values JSONB,
    new_values      JSONB,
    ip_address      TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- Indexes
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_entitlements_user_resource
    ON entitlements (user_id, resource_type, resource_id, status);

CREATE INDEX IF NOT EXISTS idx_ai_usage_user_feature
    ON ai_usage_logs (user_id, feature_key, created_at);

CREATE INDEX IF NOT EXISTS idx_payments_provider_txn
    ON payments (provider, provider_transaction_id)
    WHERE provider_transaction_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_subscriptions_user_status
    ON subscriptions (user_id, status);

CREATE INDEX IF NOT EXISTS idx_orders_user_created
    ON orders (user_id, created_at DESC);

-- =============================================================================
-- Seed Data
-- =============================================================================

-- ---------------------------------------------------------------------------
-- subscription_plans
-- ---------------------------------------------------------------------------
INSERT INTO subscription_plans (
    slug, name, description, monthly_price_kobo, annual_price_kobo,
    ai_tutor_monthly_limit, code_explain_monthly_limit,
    debug_monthly_limit, advanced_ai_monthly_limit
) VALUES
    ('free',    'Free',    'For beginners exploring the platform',                   0,       0,        20,   5,   3,   0),
    ('pro',     'Pro',     'For serious individual learners',                        450000,  4500000,  300,  100, 60,  20),
    ('premium', 'Premium', 'For developers and aspiring AI/ML professionals',        850000,  8500000,  800,  300, 200, 100)
ON CONFLICT (slug) DO NOTHING;

-- ---------------------------------------------------------------------------
-- course_prices
-- ---------------------------------------------------------------------------
INSERT INTO course_prices (course_slug, price_kobo) VALUES
    ('python-fundamentals',         990000),
    ('advanced-python',             1490000),
    ('python-web-dev',              1490000),
    ('python-automation',           1250000),
    ('python-data-analysis',        1490000),
    ('python-cybersecurity',        1490000),
    ('data-science',                1990000),
    ('ai-fundamentals',             750000),
    ('prompt-engineering',          750000),
    ('generative-ai',               990000),
    ('ai-tools-productivity',       750000),
    ('ai-app-development',          1990000),
    ('ai-agents-automation',        1990000),
    ('rag-llm-development',         2490000),
    ('ml-fundamentals',             1490000),
    ('supervised-ml',               1750000),
    ('unsupervised-ml',             1750000),
    ('deep-learning',               2490000),
    ('nlp',                         1990000),
    ('computer-vision',             1990000),
    ('reinforcement-learning',      2490000),
    ('mlops',                       2490000),
    ('advanced-ai-ml-engineering',  3490000)
ON CONFLICT (course_slug) DO NOTHING;

-- ---------------------------------------------------------------------------
-- bundles
-- ---------------------------------------------------------------------------
INSERT INTO bundles (slug, name, price_kobo, description) VALUES
    ('python-starter-pack',   'Python Starter Pack',          1990000,  'Python fundamentals, advanced Python, and practical exercises'),
    ('python-developer-pack', 'Python Developer Pack',        3490000,  'Python, APIs, web development, and automation'),
    ('ai-starter-pack',       'AI Starter Pack',              1750000,  'AI fundamentals, prompt engineering, and generative AI'),
    ('ai-professional-pack',  'AI Professional Pack',         3990000,  'Generative AI, prompt engineering, agents, and AI applications'),
    ('ml-starter-pack',       'Machine Learning Starter Pack',3490000,  'ML foundations, supervised and unsupervised learning'),
    ('deep-learning-pack',    'Deep Learning Pack',           4990000,  'Deep learning, NLP, and computer vision'),
    ('ai-ml-engineer-pack',   'AI/ML Engineer Pack',          7990000,  'Python, data science, ML, deep learning, and deployment'),
    ('complete-tech-pack',    'Complete Technology Pack',     9990000,  'All available Python, AI and ML courses')
ON CONFLICT (slug) DO NOTHING;

-- ---------------------------------------------------------------------------
-- bundle_courses  (look up bundle_id by slug via CTE)
-- ---------------------------------------------------------------------------
WITH b AS (
    SELECT id, slug FROM bundles
    WHERE slug IN (
        'python-starter-pack', 'python-developer-pack', 'ai-starter-pack', 'ai-professional-pack',
        'ml-starter-pack', 'deep-learning-pack', 'ai-ml-engineer-pack', 'complete-tech-pack'
    )
)
INSERT INTO bundle_courses (bundle_id, course_slug)
SELECT b.id, v.course_slug
FROM b
JOIN (VALUES
    -- Python Starter Pack: fundamentals, advanced Python, practical exercises (web dev as exercises proxy)
    ('python-starter-pack', 'python-fundamentals'),
    ('python-starter-pack', 'advanced-python'),
    ('python-starter-pack', 'python-automation'),

    -- Python Developer Pack: Python, APIs, web development, automation
    ('python-developer-pack', 'python-fundamentals'),
    ('python-developer-pack', 'advanced-python'),
    ('python-developer-pack', 'python-web-dev'),
    ('python-developer-pack', 'python-automation'),
    ('python-developer-pack', 'python-data-analysis'),

    -- AI Starter Pack: AI fundamentals, prompt engineering, generative AI
    ('ai-starter-pack', 'ai-fundamentals'),
    ('ai-starter-pack', 'prompt-engineering'),
    ('ai-starter-pack', 'generative-ai'),

    -- AI Professional Pack: generative AI, prompt engineering, agents, AI applications
    ('ai-professional-pack', 'generative-ai'),
    ('ai-professional-pack', 'prompt-engineering'),
    ('ai-professional-pack', 'ai-agents-automation'),
    ('ai-professional-pack', 'ai-app-development'),
    ('ai-professional-pack', 'rag-llm-development'),
    ('ai-professional-pack', 'ai-tools-productivity'),

    -- Machine Learning Starter Pack: ML foundations, supervised and unsupervised learning
    ('ml-starter-pack', 'ml-fundamentals'),
    ('ml-starter-pack', 'supervised-ml'),
    ('ml-starter-pack', 'unsupervised-ml'),

    -- Deep Learning Pack: deep learning, NLP, computer vision
    ('deep-learning-pack', 'deep-learning'),
    ('deep-learning-pack', 'nlp'),
    ('deep-learning-pack', 'computer-vision'),

    -- AI/ML Engineer Pack: Python, data science, ML, deep learning, deployment
    ('ai-ml-engineer-pack', 'python-fundamentals'),
    ('ai-ml-engineer-pack', 'advanced-python'),
    ('ai-ml-engineer-pack', 'data-science'),
    ('ai-ml-engineer-pack', 'ml-fundamentals'),
    ('ai-ml-engineer-pack', 'supervised-ml'),
    ('ai-ml-engineer-pack', 'unsupervised-ml'),
    ('ai-ml-engineer-pack', 'deep-learning'),
    ('ai-ml-engineer-pack', 'nlp'),
    ('ai-ml-engineer-pack', 'mlops'),
    ('ai-ml-engineer-pack', 'advanced-ai-ml-engineering'),

    -- Complete Technology Pack: all 23 courses
    ('complete-tech-pack', 'python-fundamentals'),
    ('complete-tech-pack', 'advanced-python'),
    ('complete-tech-pack', 'python-web-dev'),
    ('complete-tech-pack', 'python-automation'),
    ('complete-tech-pack', 'python-data-analysis'),
    ('complete-tech-pack', 'python-cybersecurity'),
    ('complete-tech-pack', 'data-science'),
    ('complete-tech-pack', 'ai-fundamentals'),
    ('complete-tech-pack', 'prompt-engineering'),
    ('complete-tech-pack', 'generative-ai'),
    ('complete-tech-pack', 'ai-tools-productivity'),
    ('complete-tech-pack', 'ai-app-development'),
    ('complete-tech-pack', 'ai-agents-automation'),
    ('complete-tech-pack', 'rag-llm-development'),
    ('complete-tech-pack', 'ml-fundamentals'),
    ('complete-tech-pack', 'supervised-ml'),
    ('complete-tech-pack', 'unsupervised-ml'),
    ('complete-tech-pack', 'deep-learning'),
    ('complete-tech-pack', 'nlp'),
    ('complete-tech-pack', 'computer-vision'),
    ('complete-tech-pack', 'reinforcement-learning'),
    ('complete-tech-pack', 'mlops'),
    ('complete-tech-pack', 'advanced-ai-ml-engineering')
) AS v (bundle_slug, course_slug) ON b.slug = v.bundle_slug
ON CONFLICT (bundle_id, course_slug) DO NOTHING;
