"""Commercial features database schema for V5 multi-scope architecture.

This schema defines tables for:
- Subscription management (5-tier pricing structure)
- Billing and payment integration
- Usage tracking and analytics
- Revenue tracking and reporting
- Customer lifecycle management
"""

import json

COMMERCIAL_SCHEMA = """
-- Subscription Plans Table (5-tier pricing structure)
CREATE TABLE IF NOT EXISTS subscription_plans (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    scope           TEXT NOT NULL,  -- my_scope, admin_scope, fx_scope, big_better_scope, regular_scope, public_scope
    price_monthly   REAL NOT NULL,
    price_yearly    REAL NOT NULL,
    currency        TEXT NOT NULL DEFAULT 'USD',
    features        TEXT NOT NULL,  -- JSON array of features
    rate_limit      INTEGER NOT NULL,  -- requests per minute
    api_access      TEXT NOT NULL,  -- JSON object with API access levels
    support_level   TEXT NOT NULL,  -- community, email, priority, dedicated
    sla             TEXT,  -- service level agreement
    max_users       INTEGER,
    storage_gb      REAL,
    active          INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

-- User Subscriptions Table
CREATE TABLE IF NOT EXISTS user_subscriptions (
    id                  TEXT PRIMARY KEY,
    user_id             INTEGER NOT NULL,
    plan_id             TEXT NOT NULL,
    status              TEXT NOT NULL,  -- active, trialing, past_due, canceled, expired
    billing_period      TEXT NOT NULL,  -- monthly, yearly
    current_period_start TEXT NOT NULL,
    current_period_end   TEXT NOT NULL,
    cancel_at_period_end INTEGER NOT NULL DEFAULT 0,
    trial_start         TEXT,
    trial_end           TEXT,
    stripe_customer_id  TEXT,
    stripe_subscription_id TEXT,
    metadata            TEXT,  -- JSON object for custom metadata
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (plan_id) REFERENCES subscription_plans(id)
);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_user ON user_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_status ON user_subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_plan ON user_subscriptions(plan_id);

-- Subscription History Table (for tracking changes)
CREATE TABLE IF NOT EXISTS subscription_history (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    subscription_id     TEXT NOT NULL,
    user_id             INTEGER NOT NULL,
    previous_plan_id    TEXT,
    new_plan_id         TEXT NOT NULL,
    previous_status     TEXT,
    new_status          TEXT NOT NULL,
    change_type         TEXT NOT NULL,  -- upgrade, downgrade, cancel, renew, trial_start, trial_end
    reason              TEXT,
    changed_by          INTEGER,  -- user_id or admin_id
    metadata            TEXT,
    created_at          TEXT NOT NULL,
    FOREIGN KEY (subscription_id) REFERENCES user_subscriptions(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_subscription_history_sub ON subscription_history(subscription_id);
CREATE INDEX IF NOT EXISTS idx_subscription_history_user ON subscription_history(user_id);

-- Payment Methods Table
CREATE TABLE IF NOT EXISTS payment_methods (
    id                  TEXT PRIMARY KEY,
    user_id             INTEGER NOT NULL,
    stripe_payment_method_id TEXT,
    type                TEXT NOT NULL,  -- card, bank_account, etc.
    brand               TEXT,  -- visa, mastercard, etc.
    last4               TEXT,
    expiry_month        INTEGER,
    expiry_year         INTEGER,
    is_default          INTEGER NOT NULL DEFAULT 0,
    metadata            TEXT,
    created_at          TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_payment_methods_user ON payment_methods(user_id);

-- Invoices Table
CREATE TABLE IF NOT EXISTS invoices (
    id                  TEXT PRIMARY KEY,
    user_id             INTEGER NOT NULL,
    subscription_id     TEXT NOT NULL,
    stripe_invoice_id   TEXT,
    amount              REAL NOT NULL,
    currency            TEXT NOT NULL DEFAULT 'USD',
    status              TEXT NOT NULL,  -- draft, open, paid, void, uncollectible
    due_date            TEXT,
    paid_at             TEXT,
    hosted_invoice_url  TEXT,
    invoice_pdf_url     TEXT,
    description         TEXT,
    metadata            TEXT,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (subscription_id) REFERENCES user_subscriptions(id)
);
CREATE INDEX IF NOT EXISTS idx_invoices_user ON invoices(user_id);
CREATE INDEX IF NOT EXISTS idx_invoices_subscription ON invoices(subscription_id);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);
CREATE INDEX IF NOT EXISTS idx_invoices_created ON invoices(created_at DESC);

-- Invoice Line Items Table
CREATE TABLE IF NOT EXISTS invoice_line_items (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id          TEXT NOT NULL,
    description         TEXT NOT NULL,
    quantity            INTEGER NOT NULL DEFAULT 1,
    unit_price          REAL NOT NULL,
    amount              REAL NOT NULL,
    period_start        TEXT,
    period_end          TEXT,
    metadata            TEXT,
    created_at          TEXT NOT NULL,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id)
);
CREATE INDEX IF NOT EXISTS idx_invoice_items_invoice ON invoice_line_items(invoice_id);

-- Usage Tracking Table
CREATE TABLE IF NOT EXISTS usage_tracking (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER NOT NULL,
    subscription_id     TEXT NOT NULL,
    metric_type         TEXT NOT NULL,  -- api_requests, storage, predictions, etc.
    metric_value        REAL NOT NULL,
    unit                TEXT NOT NULL,  -- count, gb, etc.
    period_start        TEXT NOT NULL,
    period_end          TEXT NOT NULL,
    metadata            TEXT,
    created_at          TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (subscription_id) REFERENCES user_subscriptions(id)
);
CREATE INDEX IF NOT EXISTS idx_usage_user ON usage_tracking(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_subscription ON usage_tracking(subscription_id);
CREATE INDEX IF NOT EXISTS idx_usage_period ON usage_tracking(period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_usage_type ON usage_tracking(metric_type);

-- API Usage Logs Table (detailed tracking)
CREATE TABLE IF NOT EXISTS api_usage_logs (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER NOT NULL,
    subscription_id     TEXT,
    endpoint            TEXT NOT NULL,
    method              TEXT NOT NULL,
    status_code         INTEGER,
    response_time_ms    REAL,
    request_size        INTEGER,
    response_size       INTEGER,
    timestamp           TEXT NOT NULL,
    metadata            TEXT,
    created_at          TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_api_usage_user ON api_usage_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_api_usage_timestamp ON api_usage_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_api_usage_endpoint ON api_usage_logs(endpoint);

-- Revenue Table (aggregated revenue data)
CREATE TABLE IF NOT EXISTS revenue (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    period              TEXT NOT NULL,  -- daily, weekly, monthly, yearly
    period_start        TEXT NOT NULL,
    period_end          TEXT NOT NULL,
    plan_id             TEXT NOT NULL,
    mrr                 REAL NOT NULL DEFAULT 0,  -- monthly recurring revenue
    arr                 REAL NOT NULL DEFAULT 0,  -- annual recurring revenue
    new_revenue         REAL NOT NULL DEFAULT 0,
    churn_revenue       REAL NOT NULL DEFAULT 0,
    expansion_revenue   REAL NOT NULL DEFAULT 0,
    total_revenue       REAL NOT NULL DEFAULT 0,
    subscriber_count    INTEGER NOT NULL DEFAULT 0,
    new_subscribers     INTEGER NOT NULL DEFAULT 0,
    churned_subscribers INTEGER NOT NULL DEFAULT 0,
    metadata            TEXT,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,
    FOREIGN KEY (plan_id) REFERENCES subscription_plans(id)
);
CREATE INDEX IF NOT EXISTS idx_revenue_period ON revenue(period, period_start);
CREATE INDEX IF NOT EXISTS idx_revenue_plan ON revenue(plan_id);

-- Customer Lifecycle Events Table
CREATE TABLE IF NOT EXISTS customer_lifecycle (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER NOT NULL,
    event_type          TEXT NOT NULL,  -- signup, trial_start, subscription_start, upgrade, downgrade, cancel, churn, reactivation
    event_data          TEXT,  -- JSON object with event details
    previous_state      TEXT,
    new_state           TEXT,
    source              TEXT,  -- organic, referral, paid, etc.
    campaign            TEXT,
    metadata            TEXT,
    created_at          TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_lifecycle_user ON customer_lifecycle(user_id);
CREATE INDEX IF NOT EXISTS idx_lifecycle_type ON customer_lifecycle(event_type);
CREATE INDEX IF NOT EXISTS idx_lifecycle_created ON customer_lifecycle(created_at DESC);

-- Promo Codes Table
CREATE TABLE IF NOT EXISTS promo_codes (
    id                  TEXT PRIMARY KEY,
    code                TEXT NOT NULL UNIQUE,
    description         TEXT,
    discount_type       TEXT NOT NULL,  -- percentage, fixed_amount
    discount_value      REAL NOT NULL,
    applicable_plans    TEXT,  -- JSON array of plan IDs
    max_uses            INTEGER,
    used_count          INTEGER NOT NULL DEFAULT 0,
    valid_from          TEXT NOT NULL,
    valid_until         TEXT,
    metadata            TEXT,
    active              INTEGER NOT NULL DEFAULT 1,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_promo_code ON promo_codes(code);

-- Promo Code Redemptions Table
CREATE TABLE IF NOT EXISTS promo_redemptions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    promo_code_id       TEXT NOT NULL,
    user_id             INTEGER NOT NULL,
    subscription_id     TEXT,
    discount_amount     REAL NOT NULL,
    metadata            TEXT,
    created_at          TEXT NOT NULL,
    FOREIGN KEY (promo_code_id) REFERENCES promo_codes(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (subscription_id) REFERENCES user_subscriptions(id)
);
CREATE INDEX IF NOT EXISTS idx_promo_redemptions_code ON promo_redemptions(promo_code_id);
CREATE INDEX IF NOT EXISTS idx_promo_redemptions_user ON promo_redemptions(user_id);

-- Billing Alerts Table
CREATE TABLE IF NOT EXISTS billing_alerts (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER NOT NULL,
    subscription_id     TEXT NOT NULL,
    alert_type          TEXT NOT NULL,  -- payment_failed, invoice_created, subscription_expiring, etc.
    alert_level         TEXT NOT NULL,  -- info, warning, critical
    message             TEXT NOT NULL,
    resolved            INTEGER NOT NULL DEFAULT 0,
    resolved_at         TEXT,
    metadata            TEXT,
    created_at          TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (subscription_id) REFERENCES user_subscriptions(id)
);
CREATE INDEX IF NOT EXISTS idx_billing_alerts_user ON billing_alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_billing_alerts_subscription ON billing_alerts(subscription_id);
CREATE INDEX IF NOT EXISTS idx_billing_alerts_resolved ON billing_alerts(resolved);
CREATE INDEX IF NOT EXISTS idx_billing_alerts_created ON billing_alerts(created_at DESC);

-- Feature Gates Table (for feature access control)
CREATE TABLE IF NOT EXISTS feature_gates (
    id                  TEXT PRIMARY KEY,
    feature_key         TEXT NOT NULL UNIQUE,
    feature_name        TEXT NOT NULL,
    description         TEXT,
    category            TEXT,  -- prediction, analysis, trading, ui, api
    pricing_model       TEXT NOT NULL DEFAULT 'subscription',  -- subscription, usage_based, hybrid
    base_price          REAL DEFAULT 0,
    unit_price          REAL DEFAULT 0,  -- price per unit for usage-based
    unit_name           TEXT,  -- request, prediction, gb, etc.
    included_units      INTEGER DEFAULT 0,  -- units included in base subscription
    enabled_plans       TEXT NOT NULL,  -- JSON array of plan IDs that have access
    enabled_scopes      TEXT NOT NULL,  -- JSON array of scopes that have access
    is_beta             INTEGER NOT NULL DEFAULT 0,
    is_public           INTEGER NOT NULL DEFAULT 1,
    metadata            TEXT,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_feature_gates_key ON feature_gates(feature_key);
CREATE INDEX IF NOT EXISTS idx_feature_gates_category ON feature_gates(category);
CREATE INDEX IF NOT EXISTS idx_feature_gates_pricing ON feature_gates(pricing_model);

-- Feature Usage Table (track usage per feature)
CREATE TABLE IF NOT EXISTS feature_usage (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER NOT NULL,
    subscription_id     TEXT,
    feature_key         TEXT NOT NULL,
    usage_count         INTEGER NOT NULL DEFAULT 0,
    usage_value         REAL NOT NULL DEFAULT 0,  -- for usage-based pricing
    period_start        TEXT NOT NULL,
    period_end          TEXT NOT NULL,
    metadata            TEXT,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (subscription_id) REFERENCES user_subscriptions(id),
    FOREIGN KEY (feature_key) REFERENCES feature_gates(feature_key)
);
CREATE INDEX IF NOT EXISTS idx_feature_usage_user ON feature_usage(user_id);
CREATE INDEX IF NOT EXISTS idx_feature_usage_feature ON feature_usage(feature_key);
CREATE INDEX IF NOT EXISTS idx_feature_usage_period ON feature_usage(period_start, period_end);

-- Pricing Tiers Table (for usage-based pricing)
CREATE TABLE IF NOT EXISTS pricing_tiers (
    id                  TEXT PRIMARY KEY,
    feature_key         TEXT NOT NULL,
    tier_name           TEXT NOT NULL,
    min_units           REAL NOT NULL,
    max_units           REAL,
    price_per_unit      REAL NOT NULL,
    currency            TEXT NOT NULL DEFAULT 'USD',
    applies_to_plans    TEXT,  -- JSON array of plan IDs
    active              INTEGER NOT NULL DEFAULT 1,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,
    FOREIGN KEY (feature_key) REFERENCES feature_gates(feature_key)
);
CREATE INDEX IF NOT EXISTS idx_pricing_tiers_feature ON pricing_tiers(feature_key);
CREATE INDEX IF NOT EXISTS idx_pricing_tiers_active ON pricing_tiers(active);

-- Usage Quotas Table (per subscription limits)
CREATE TABLE IF NOT EXISTS usage_quotas (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    subscription_id     TEXT NOT NULL,
    feature_key         TEXT NOT NULL,
    quota_limit         INTEGER NOT NULL,
    quota_used          INTEGER NOT NULL DEFAULT 0,
    quota_reset_at      TEXT NOT NULL,
    warning_threshold   REAL DEFAULT 0.8,  -- percentage
    alert_sent          INTEGER NOT NULL DEFAULT 0,
    metadata            TEXT,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,
    FOREIGN KEY (subscription_id) REFERENCES user_subscriptions(id),
    FOREIGN KEY (feature_key) REFERENCES feature_gates(feature_key),
    UNIQUE (subscription_id, feature_key)
);
CREATE INDEX IF NOT EXISTS idx_usage_quotas_subscription ON usage_quotas(subscription_id);
CREATE INDEX IF NOT EXISTS idx_usage_quotas_feature ON usage_quotas(feature_key);

-- Revenue Attribution Table (track revenue sources)
CREATE TABLE IF NOT EXISTS revenue_attribution (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    period              TEXT NOT NULL,
    period_start        TEXT NOT NULL,
    period_end          TEXT NOT NULL,
    scope               TEXT NOT NULL,
    plan_id             TEXT,
    revenue_source      TEXT NOT NULL,  -- subscription, usage, addon, enterprise
    feature_key         TEXT,
    gross_revenue       REAL NOT NULL DEFAULT 0,
    net_revenue         REAL NOT NULL DEFAULT 0,
    refunds             REAL NOT NULL DEFAULT 0,
    discounts           REAL NOT NULL DEFAULT 0,
    tax_amount          REAL NOT NULL DEFAULT 0,
    customer_count      INTEGER NOT NULL DEFAULT 0,
    metadata            TEXT,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,
    FOREIGN KEY (plan_id) REFERENCES subscription_plans(id),
    FOREIGN KEY (feature_key) REFERENCES feature_gates(feature_key)
);
CREATE INDEX IF NOT EXISTS idx_revenue_attr_period ON revenue_attribution(period, period_start);
CREATE INDEX IF NOT EXISTS idx_revenue_attr_scope ON revenue_attribution(scope);
CREATE INDEX IF NOT EXISTS idx_revenue_attr_source ON revenue_attribution(revenue_source);

-- Commercial Metrics Table (for analytics dashboard)
CREATE TABLE IF NOT EXISTS commercial_metrics (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_name         TEXT NOT NULL,
    metric_value        REAL NOT NULL,
    metric_type         TEXT NOT NULL,  -- counter, gauge, histogram
    labels              TEXT,  -- JSON object with labels (scope, plan, etc.)
    timestamp           TEXT NOT NULL,
    metadata            TEXT,
    created_at          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_commercial_metrics_name ON commercial_metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_commercial_metrics_timestamp ON commercial_metrics(timestamp DESC);
"""


def get_default_subscription_plans() -> list[dict]:
    """Return default subscription plans for the 5-tier pricing structure."""
    return [
        {
            "id": "plan_my_scope",
            "name": "My Scope - Platform Owner",
            "scope": "my_scope",
            "price_monthly": 0,
            "price_yearly": 0,
            "currency": "USD",
            "features": json.dumps([
                "Complete system control",
                "Architecture visualization",
                "Performance engineering",
                "Business intelligence",
                "Security configuration",
                "Unlimited API access",
                "24/7 dedicated support",
                "99.999% SLA"
            ]),
            "rate_limit": 999999,
            "api_access": json.dumps({"level": "full", "access": "all_endpoints"}),
            "support_level": "dedicated",
            "sla": "99.999%",
            "max_users": 1,
            "storage_gb": 999999,
            "active": 1
        },
        {
            "id": "plan_admin_scope",
            "name": "Admin Scope - System Administrator",
            "scope": "admin_scope",
            "price_monthly": 0,
            "price_yearly": 0,
            "currency": "USD",
            "features": json.dumps([
                "User management",
                "System monitoring",
                "Vocabulary administration",
                "Pattern administration",
                "Incident response",
                "Administrative API access",
                "24/7 support",
                "99.99% SLA"
            ]),
            "rate_limit": 10000,
            "api_access": json.dumps({"level": "admin", "access": ["admin", "monitoring", "user_management"]}),
            "support_level": "dedicated",
            "sla": "99.99%",
            "max_users": 10,
            "storage_gb": 1000,
            "active": 1
        },
        {
            "id": "plan_fx_scope",
            "name": "FX User Scope - Professional Trading",
            "scope": "fx_scope",
            "price_monthly": 499,
            "price_yearly": 4990,
            "currency": "USD",
            "features": json.dumps([
                "Professional-grade predictions",
                "Real-time data feeds",
                "Advanced analytics",
                "API access (priority)",
                "Risk management tools",
                "Portfolio optimization",
                "24/7 priority support",
                "99.95% SLA"
            ]),
            "rate_limit": 5000,
            "api_access": json.dumps({"level": "professional", "access": ["predictions", "analytics", "api"]}),
            "support_level": "priority",
            "sla": "99.95%",
            "max_users": 5,
            "storage_gb": 500,
            "active": 1
        },
        {
            "id": "plan_big_better_scope",
            "name": "Big Better Scope - Premium Clients",
            "scope": "big_better_scope",
            "price_monthly": 199,
            "price_yearly": 1990,
            "currency": "USD",
            "features": json.dumps([
                "Enhanced predictions",
                "Priority data access",
                "Advanced analytics",
                "API access",
                "Custom dashboards",
                "Market insights",
                "24/7 priority support",
                "99.9% SLA"
            ]),
            "rate_limit": 1000,
            "api_access": json.dumps({"level": "premium", "access": ["predictions", "analytics", "api"]}),
            "support_level": "priority",
            "sla": "99.9%",
            "max_users": 3,
            "storage_gb": 100,
            "active": 1
        },
        {
            "id": "plan_regular_scope",
            "name": "Regular Scope - Budget Predictor",
            "scope": "regular_scope",
            "price_monthly": 29,
            "price_yearly": 290,
            "currency": "USD",
            "features": json.dumps([
                "Standard predictions",
                "Basic charts",
                "Market overview",
                "Limited API access",
                "Community features",
                "Email support",
                "99% SLA"
            ]),
            "rate_limit": 100,
            "api_access": json.dumps({"level": "basic", "access": ["predictions", "basic_api"]}),
            "support_level": "email",
            "sla": "99%",
            "max_users": 1,
            "storage_gb": 10,
            "active": 1
        },
        {
            "id": "plan_public_scope",
            "name": "Public Consumer Scope - Free",
            "scope": "public_scope",
            "price_monthly": 0,
            "price_yearly": 0,
            "currency": "USD",
            "features": json.dumps([
                "Basic predictions",
                "Limited charts",
                "Community access",
                "Educational content",
                "Community support"
            ]),
            "rate_limit": 10,
            "api_access": json.dumps({"level": "limited", "access": ["basic_predictions"]}),
            "support_level": "community",
            "sla": None,
            "max_users": 1,
            "storage_gb": 1,
            "active": 1
        }
    ]


def get_default_feature_gates() -> list[dict]:
    """Return default feature gates for the platform."""
    return [
        {
            "id": "fg_predictions_basic",
            "feature_key": "predictions.basic",
            "feature_name": "Basic Predictions",
            "description": "Standard prediction models with basic confidence metrics",
            "category": "prediction",
            "pricing_model": "subscription",
            "base_price": 0,
            "unit_price": 0,
            "unit_name": None,
            "included_units": 0,
            "enabled_plans": json.dumps(["plan_regular_scope", "plan_big_better_scope", "plan_fx_scope", "plan_my_scope", "plan_admin_scope", "plan_public_scope"]),
            "enabled_scopes": json.dumps(["regular_scope", "big_better_scope", "fx_scope", "my_scope", "admin_scope", "public_scope"]),
            "is_beta": 0,
            "is_public": 1
        },
        {
            "id": "fg_predictions_enhanced",
            "feature_key": "predictions.enhanced",
            "feature_name": "Enhanced Predictions",
            "description": "Higher accuracy models with real-time updates and advanced confidence",
            "category": "prediction",
            "pricing_model": "subscription",
            "base_price": 0,
            "unit_price": 0,
            "unit_name": None,
            "included_units": 0,
            "enabled_plans": json.dumps(["plan_big_better_scope", "plan_fx_scope", "plan_my_scope", "plan_admin_scope"]),
            "enabled_scopes": json.dumps(["big_better_scope", "fx_scope", "my_scope", "admin_scope"]),
            "is_beta": 0,
            "is_public": 1
        },
        {
            "id": "fg_predictions_professional",
            "feature_key": "predictions.professional",
            "feature_name": "Professional Predictions",
            "description": "Professional-grade predictions with sub-millisecond updates",
            "category": "prediction",
            "pricing_model": "subscription",
            "base_price": 0,
            "unit_price": 0,
            "unit_name": None,
            "included_units": 0,
            "enabled_plans": json.dumps(["plan_fx_scope", "plan_my_scope"]),
            "enabled_scopes": json.dumps(["fx_scope", "my_scope"]),
            "is_beta": 0,
            "is_public": 1
        },
        {
            "id": "fg_api_basic",
            "feature_key": "api.basic",
            "feature_name": "Basic API Access",
            "description": "Limited API access with standard rate limits",
            "category": "api",
            "pricing_model": "subscription",
            "base_price": 0,
            "unit_price": 0,
            "unit_name": None,
            "included_units": 0,
            "enabled_plans": json.dumps(["plan_regular_scope", "plan_big_better_scope", "plan_fx_scope", "plan_my_scope", "plan_admin_scope"]),
            "enabled_scopes": json.dumps(["regular_scope", "big_better_scope", "fx_scope", "my_scope", "admin_scope"]),
            "is_beta": 0,
            "is_public": 1
        },
        {
            "id": "fg_api_priority",
            "feature_key": "api.priority",
            "feature_name": "Priority API Access",
            "description": "Priority API access with higher rate limits",
            "category": "api",
            "pricing_model": "subscription",
            "base_price": 0,
            "unit_price": 0,
            "unit_name": None,
            "included_units": 0,
            "enabled_plans": json.dumps(["plan_big_better_scope", "plan_fx_scope", "plan_my_scope", "plan_admin_scope"]),
            "enabled_scopes": json.dumps(["big_better_scope", "fx_scope", "my_scope", "admin_scope"]),
            "is_beta": 0,
            "is_public": 1
        },
        {
            "id": "fg_api_full",
            "feature_key": "api.full",
            "feature_name": "Full API Access",
            "description": "Complete API access with all endpoints",
            "category": "api",
            "pricing_model": "subscription",
            "base_price": 0,
            "unit_price": 0,
            "unit_name": None,
            "included_units": 0,
            "enabled_plans": json.dumps(["plan_fx_scope", "plan_my_scope", "plan_admin_scope"]),
            "enabled_scopes": json.dumps(["fx_scope", "my_scope", "admin_scope"]),
            "is_beta": 0,
            "is_public": 1
        },
        {
            "id": "fg_analysis_basic",
            "feature_key": "analysis.basic",
            "feature_name": "Basic Analytics",
            "description": "Standard analytics and reporting features",
            "category": "analysis",
            "pricing_model": "subscription",
            "base_price": 0,
            "unit_price": 0,
            "unit_name": None,
            "included_units": 0,
            "enabled_plans": json.dumps(["plan_regular_scope", "plan_big_better_scope", "plan_fx_scope", "plan_my_scope", "plan_admin_scope"]),
            "enabled_scopes": json.dumps(["regular_scope", "big_better_scope", "fx_scope", "my_scope", "admin_scope"]),
            "is_beta": 0,
            "is_public": 1
        },
        {
            "id": "fg_analysis_advanced",
            "feature_key": "analysis.advanced",
            "feature_name": "Advanced Analytics",
            "description": "Advanced analytics with custom dashboards and insights",
            "category": "analysis",
            "pricing_model": "subscription",
            "base_price": 0,
            "unit_price": 0,
            "unit_name": None,
            "included_units": 0,
            "enabled_plans": json.dumps(["plan_big_better_scope", "plan_fx_scope", "plan_my_scope", "plan_admin_scope"]),
            "enabled_scopes": json.dumps(["big_better_scope", "fx_scope", "my_scope", "admin_scope"]),
            "is_beta": 0,
            "is_public": 1
        },
        {
            "id": "fg_trading_tools",
            "feature_key": "trading.tools",
            "feature_name": "Trading Tools",
            "description": "Professional trading tools and strategy builder",
            "category": "trading",
            "pricing_model": "subscription",
            "base_price": 0,
            "unit_price": 0,
            "unit_name": None,
            "included_units": 0,
            "enabled_plans": json.dumps(["plan_fx_scope", "plan_my_scope"]),
            "enabled_scopes": json.dumps(["fx_scope", "my_scope"]),
            "is_beta": 0,
            "is_public": 1
        },
        {
            "id": "fg_system_control",
            "feature_key": "system.control",
            "feature_name": "System Control",
            "description": "Complete system control and architecture management",
            "category": "ui",
            "pricing_model": "subscription",
            "base_price": 0,
            "unit_price": 0,
            "unit_name": None,
            "included_units": 0,
            "enabled_plans": json.dumps(["plan_my_scope"]),
            "enabled_scopes": json.dumps(["my_scope"]),
            "is_beta": 0,
            "is_public": 0
        },
        {
            "id": "fg_user_management",
            "feature_key": "user.management",
            "feature_name": "User Management",
            "description": "User administration and management tools",
            "category": "ui",
            "pricing_model": "subscription",
            "base_price": 0,
            "unit_price": 0,
            "unit_name": None,
            "included_units": 0,
            "enabled_plans": json.dumps(["plan_admin_scope", "plan_my_scope"]),
            "enabled_scopes": json.dumps(["admin_scope", "my_scope"]),
            "is_beta": 0,
            "is_public": 0
        },
        {
            "id": "fg_usage_predictions",
            "feature_key": "usage.predictions",
            "feature_name": "Prediction Usage",
            "description": "Usage-based pricing for predictions",
            "category": "prediction",
            "pricing_model": "usage_based",
            "base_price": 10,
            "unit_price": 0.01,
            "unit_name": "prediction",
            "included_units": 1000,
            "enabled_plans": json.dumps(["plan_regular_scope", "plan_big_better_scope", "plan_fx_scope"]),
            "enabled_scopes": json.dumps(["regular_scope", "big_better_scope", "fx_scope"]),
            "is_beta": 0,
            "is_public": 1
        },
        {
            "id": "fg_usage_api_requests",
            "feature_key": "usage.api_requests",
            "feature_name": "API Request Usage",
            "description": "Usage-based pricing for API requests",
            "category": "api",
            "pricing_model": "usage_based",
            "base_price": 5,
            "unit_price": 0.001,
            "unit_name": "request",
            "included_units": 10000,
            "enabled_plans": json.dumps(["plan_regular_scope", "plan_big_better_scope", "plan_fx_scope"]),
            "enabled_scopes": json.dumps(["regular_scope", "big_better_scope", "fx_scope"]),
            "is_beta": 0,
            "is_public": 1
        },
        {
            "id": "fg_usage_storage",
            "feature_key": "usage.storage",
            "feature_name": "Storage Usage",
            "description": "Usage-based pricing for storage",
            "category": "analysis",
            "pricing_model": "usage_based",
            "base_price": 0,
            "unit_price": 0.1,
            "unit_name": "gb",
            "included_units": 10,
            "enabled_plans": json.dumps(["plan_regular_scope", "plan_big_better_scope", "plan_fx_scope"]),
            "enabled_scopes": json.dumps(["regular_scope", "big_better_scope", "fx_scope"]),
            "is_beta": 0,
            "is_public": 1
        }
    ]


def get_default_pricing_tiers() -> list[dict]:
    """Return default pricing tiers for usage-based features."""
    return [
        # Prediction usage tiers
        {
            "id": "pt_predictions_tier1",
            "feature_key": "usage.predictions",
            "tier_name": "Starter",
            "min_units": 0,
            "max_units": 1000,
            "price_per_unit": 0.01,
            "currency": "USD",
            "applies_to_plans": json.dumps(["plan_regular_scope"]),
            "active": 1
        },
        {
            "id": "pt_predictions_tier2",
            "feature_key": "usage.predictions",
            "tier_name": "Standard",
            "min_units": 1001,
            "max_units": 10000,
            "price_per_unit": 0.008,
            "currency": "USD",
            "applies_to_plans": json.dumps(["plan_regular_scope", "plan_big_better_scope"]),
            "active": 1
        },
        {
            "id": "pt_predictions_tier3",
            "feature_key": "usage.predictions",
            "tier_name": "Premium",
            "min_units": 10001,
            "max_units": None,
            "price_per_unit": 0.005,
            "currency": "USD",
            "applies_to_plans": json.dumps(["plan_big_better_scope", "plan_fx_scope"]),
            "active": 1
        },
        # API request tiers
        {
            "id": "pt_api_tier1",
            "feature_key": "usage.api_requests",
            "tier_name": "Basic",
            "min_units": 0,
            "max_units": 10000,
            "price_per_unit": 0.001,
            "currency": "USD",
            "applies_to_plans": json.dumps(["plan_regular_scope"]),
            "active": 1
        },
        {
            "id": "pt_api_tier2",
            "feature_key": "usage.api_requests",
            "tier_name": "Professional",
            "min_units": 10001,
            "max_units": 100000,
            "price_per_unit": 0.0005,
            "currency": "USD",
            "applies_to_plans": json.dumps(["plan_big_better_scope"]),
            "active": 1
        },
        {
            "id": "pt_api_tier3",
            "feature_key": "usage.api_requests",
            "tier_name": "Enterprise",
            "min_units": 100001,
            "max_units": None,
            "price_per_unit": 0.0002,
            "currency": "USD",
            "applies_to_plans": json.dumps(["plan_fx_scope"]),
            "active": 1
        },
        # Storage tiers
        {
            "id": "pt_storage_tier1",
            "feature_key": "usage.storage",
            "tier_name": "Basic",
            "min_units": 0,
            "max_units": 100,
            "price_per_unit": 0.1,
            "currency": "USD",
            "applies_to_plans": json.dumps(["plan_regular_scope"]),
            "active": 1
        },
        {
            "id": "pt_storage_tier2",
            "feature_key": "usage.storage",
            "tier_name": "Professional",
            "min_units": 101,
            "max_units": 1000,
            "price_per_unit": 0.08,
            "currency": "USD",
            "applies_to_plans": json.dumps(["plan_big_better_scope"]),
            "active": 1
        },
        {
            "id": "pt_storage_tier3",
            "feature_key": "usage.storage",
            "tier_name": "Enterprise",
            "min_units": 1001,
            "max_units": None,
            "price_per_unit": 0.05,
            "currency": "USD",
            "applies_to_plans": json.dumps(["plan_fx_scope"]),
            "active": 1
        }
    ]