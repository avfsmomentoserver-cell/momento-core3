"""Multi-scope database schema for V5 transformation.

This module defines the database schema for:
- Multi-tenant data isolation
- Scope-based authentication and authorization
- Subscription management
- API key management
- Rate limiting per scope
"""

MULTI_SCOPE_SCHEMA = """
-- Tenants table for multi-tenant data isolation
CREATE TABLE IF NOT EXISTS tenants (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id       TEXT    NOT NULL UNIQUE,
    name            TEXT    NOT NULL,
    display_name    TEXT,
    scope           TEXT    NOT NULL,
    status          TEXT    NOT NULL DEFAULT 'active',
    settings        TEXT    DEFAULT '{}',
    created_at      TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL,
    UNIQUE (tenant_id)
);
CREATE INDEX IF NOT EXISTS idx_tenants_scope ON tenants (scope);
CREATE INDEX IF NOT EXISTS idx_tenants_status ON tenants (status);

-- User-tenant relationship table
CREATE TABLE IF NOT EXISTS user_tenants (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    tenant_id       TEXT    NOT NULL,
    role            TEXT    NOT NULL DEFAULT 'member',
    is_primary      INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT    NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE (user_id, tenant_id)
);
CREATE INDEX IF NOT EXISTS idx_user_tenants_user ON user_tenants (user_id);
CREATE INDEX IF NOT EXISTS idx_user_tenants_tenant ON user_tenants (tenant_id);

-- Subscriptions table for commercial model
CREATE TABLE IF NOT EXISTS subscriptions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    subscription_id TEXT    NOT NULL UNIQUE,
    tenant_id       TEXT    NOT NULL,
    plan_id         TEXT    NOT NULL,
    scope           TEXT    NOT NULL,
    status          TEXT    NOT NULL DEFAULT 'active',
    billing_cycle   TEXT    NOT NULL DEFAULT 'monthly',
    amount          REAL    NOT NULL,
    currency        TEXT    NOT NULL DEFAULT 'USD',
    start_date      TEXT    NOT NULL,
    end_date        TEXT,
    auto_renew      INTEGER NOT NULL DEFAULT 1,
    features        TEXT    DEFAULT '{}',
    created_at      TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    UNIQUE (subscription_id)
);
CREATE INDEX IF NOT EXISTS idx_subscriptions_tenant ON subscriptions (tenant_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_scope ON subscriptions (scope);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions (status);

-- Subscription plans configuration
CREATE TABLE IF NOT EXISTS subscription_plans (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id         TEXT    NOT NULL UNIQUE,
    name            TEXT    NOT NULL,
    scope           TEXT    NOT NULL,
    tier            TEXT    NOT NULL,
    price_monthly   REAL    NOT NULL,
    price_yearly    REAL,
    currency        TEXT    NOT NULL DEFAULT 'USD',
    features        TEXT    NOT NULL DEFAULT '{}',
    rate_limit      INTEGER NOT NULL DEFAULT 100,
    api_access      TEXT NOT NULL DEFAULT 'basic',
    max_users       INTEGER,
    storage_limit   INTEGER,
    active          INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL,
    UNIQUE (plan_id)
);
CREATE INDEX IF NOT EXISTS idx_plans_scope ON subscription_plans (scope);
CREATE INDEX IF NOT EXISTS idx_plans_tier ON subscription_plans (tier);

-- Scope permissions for RBAC/ABAC
CREATE TABLE IF NOT EXISTS scope_permissions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    scope           TEXT    NOT NULL,
    resource        TEXT    NOT NULL,
    action          TEXT    NOT NULL,
    condition       TEXT,
    enabled         INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT    NOT NULL,
    UNIQUE (scope, resource, action)
);
CREATE INDEX IF NOT EXISTS idx_scope_permissions_scope ON scope_permissions (scope);
CREATE INDEX IF NOT EXISTS idx_scope_permissions_resource ON scope_permissions (resource);

-- API keys for scope-based access
CREATE TABLE IF NOT EXISTS api_keys (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    key_id          TEXT    NOT NULL UNIQUE,
    key_hash        TEXT    NOT NULL,
    user_id         INTEGER NOT NULL,
    tenant_id       TEXT    NOT NULL,
    scope           TEXT    NOT NULL,
    name            TEXT,
    permissions     TEXT    DEFAULT '{}',
    rate_limit      INTEGER,
    expires_at      TEXT,
    last_used       TEXT,
    active          INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT    NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    UNIQUE (key_id)
);
CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys (user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_tenant ON api_keys (tenant_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_scope ON api_keys (scope);
CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys (key_hash);

-- Rate limiting tracking
CREATE TABLE IF NOT EXISTS rate_limits (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id       TEXT    NOT NULL,
    scope           TEXT    NOT NULL,
    endpoint        TEXT    NOT NULL,
    window_start    TEXT    NOT NULL,
    request_count   INTEGER NOT NULL DEFAULT 0,
    blocked         INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT    NOT NULL,
    UNIQUE (client_id, scope, endpoint, window_start)
);
CREATE INDEX IF NOT EXISTS idx_rate_limits_client ON rate_limits (client_id);
CREATE INDEX IF NOT EXISTS idx_rate_limits_window ON rate_limits (window_start);

-- Usage tracking for billing
CREATE TABLE IF NOT EXISTS usage_tracking (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id       TEXT    NOT NULL,
    user_id         INTEGER,
    scope           TEXT    NOT NULL,
    metric          TEXT    NOT NULL,
    value           REAL NOT NULL,
    unit            TEXT,
    period          TEXT NOT NULL,
    recorded_at      TEXT    NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_usage_tenant ON usage_tracking (tenant_id);
CREATE INDEX IF NOT EXISTS idx_usage_scope ON usage_tracking (scope);
CREATE INDEX IF NOT EXISTS idx_usage_period ON usage_tracking (period, recorded_at);

-- Audit log for scope operations
CREATE TABLE IF NOT EXISTS scope_audit_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id       TEXT,
    user_id         INTEGER,
    scope           TEXT,
    action          TEXT NOT NULL,
    resource        TEXT,
    details         TEXT,
    ip_address      TEXT,
    user_agent      TEXT,
    created_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_scope_audit_tenant ON scope_audit_log (tenant_id);
CREATE INDEX IF NOT EXISTS idx_scope_audit_user ON scope_audit_log (user_id);
CREATE INDEX IF NOT EXISTS idx_scope_audit_scope ON scope_audit_log (scope);
CREATE INDEX IF NOT EXISTS idx_scope_audit_created ON scope_audit_log (created_at DESC);
"""

# Scope definitions with their properties
SCOPES = {
    "my_scope": {
        "name": "My Scope",
        "description": "Platform Owner/Architect - Complete system control",
        "tier": "owner",
        "rate_limit": None,  # Unlimited
        "api_access": "full",
        "features": [
            "system_architecture",
            "performance_engineering",
            "business_intelligence",
            "security_compliance",
            "deployment_control",
            "billing_management",
        ],
    },
    "admin_scope": {
        "name": "Admin Scope",
        "description": "System Administrators - Operational control",
        "tier": "admin",
        "rate_limit": 10000,  # 10K requests/minute
        "api_access": "administrative",
        "features": [
            "user_management",
            "scope_management",
            "system_monitoring",
            "vocabulary_admin",
            "pattern_admin",
            "incident_management",
            "billing_management",
        ],
    },
    "fx_user_scope": {
        "name": "FX User Scope",
        "description": "Professional Trading - High-frequency trading",
        "tier": "premium",
        "rate_limit": 5000,  # 5K requests/minute
        "api_access": "professional",
        "features": [
            "hft_predictions",
            "realtime_feed",
            "gpu_acceleration",
            "sub_ms_latency",
            "advanced_risk",
            "api_websocket",
            "backtesting",
        ],
    },
    "big_better_scope": {
        "name": "Big Better Scope",
        "description": "Premium Clients - Enhanced predictions",
        "tier": "premium",
        "rate_limit": 1000,  # 1K requests/minute
        "api_access": "enhanced",
        "features": [
            "enhanced_predictions",
            "priority_access",
            "advanced_analytics",
            "custom_dashboards",
            "confidence_analysis",
            "portfolio_optimization",
            "priority_support",
        ],
    },
    "regular_low_budget_scope": {
        "name": "Regular Low Budget Scope",
        "description": "Low Budget Predictor - Basic predictions",
        "tier": "basic",
        "rate_limit": 100,  # 100 requests/minute
        "api_access": "basic",
        "features": [
            "basic_predictions",
            "standard_features",
            "basic_charts",
            "market_overview",
            "price_alerts",
            "community_forum",
            "educational_content",
        ],
    },
    "public_consumer_scope": {
        "name": "Public Consumer Scope",
        "description": "Free/Freemium - Limited access",
        "tier": "free",
        "rate_limit": 50,  # 50 requests/minute
        "api_access": "read",
        "features": [
            "public_predictions",
            "market_overview",
            "community_forum",
        ],
    },
}

# Subscription plans with pricing
SUBSCRIPTION_PLANS = [
    {
        "plan_id": "my_scope_included",
        "name": "My Scope (Included)",
        "scope": "my_scope",
        "tier": "owner",
        "price_monthly": 0,
        "price_yearly": 0,
        "currency": "USD",
        "features": SCOPES["my_scope"]["features"],
        "rate_limit": None,
        "api_access": "full",
        "max_users": None,
        "storage_limit": None,
    },
    {
        "plan_id": "admin_scope_included",
        "name": "Admin Scope (Included)",
        "scope": "admin_scope",
        "tier": "admin",
        "price_monthly": 0,
        "price_yearly": 0,
        "currency": "USD",
        "features": SCOPES["admin_scope"]["features"],
        "rate_limit": 10000,
        "api_access": "administrative",
        "max_users": None,
        "storage_limit": None,
    },
    {
        "plan_id": "fx_user_monthly",
        "name": "FX User Professional (Monthly)",
        "scope": "fx_user_scope",
        "tier": "premium",
        "price_monthly": 499,
        "price_yearly": 4990,
        "currency": "USD",
        "features": SCOPES["fx_user_scope"]["features"],
        "rate_limit": 5000,
        "api_access": "professional",
        "max_users": 5,
        "storage_limit": 1000,
    },
    {
        "plan_id": "big_better_monthly",
        "name": "Big Better Premium (Monthly)",
        "scope": "big_better_scope",
        "tier": "premium",
        "price_monthly": 199,
        "price_yearly": 1990,
        "currency": "USD",
        "features": SCOPES["big_better_scope"]["features"],
        "rate_limit": 1000,
        "api_access": "enhanced",
        "max_users": 10,
        "storage_limit": 500,
    },
    {
        "plan_id": "regular_low_budget_monthly",
        "name": "Regular Low Budget (Monthly)",
        "scope": "regular_low_budget_scope",
        "tier": "basic",
        "price_monthly": 29,
        "price_yearly": 290,
        "currency": "USD",
        "features": SCOPES["regular_low_budget_scope"]["features"],
        "rate_limit": 100,
        "api_access": "basic",
        "max_users": 1,
        "storage_limit": 100,
    },
    {
        "plan_id": "public_consumer_free",
        "name": "Public Consumer Free",
        "scope": "public_consumer_scope",
        "tier": "free",
        "price_monthly": 0,
        "price_yearly": 0,
        "currency": "USD",
        "features": SCOPES["public_consumer_scope"]["features"],
        "rate_limit": 50,
        "api_access": "read",
        "max_users": 1,
        "storage_limit": 10,
    },
]

# Default scope permissions
DEFAULT_PERMISSIONS = [
    # My Scope - Full access
    {"scope": "my_scope", "resource": "*", "action": "*", "enabled": True},
    # Admin Scope - Administrative access
    {"scope": "admin_scope", "resource": "users", "action": "read", "enabled": True},
    {"scope": "admin_scope", "resource": "users", "action": "write", "enabled": True},
    {"scope": "admin_scope", "resource": "tenants", "action": "read", "enabled": True},
    {"scope": "admin_scope", "resource": "tenants", "action": "write", "enabled": True},
    {"scope": "admin_scope", "resource": "subscriptions", "action": "read", "enabled": True},
    {"scope": "admin_scope", "resource": "subscriptions", "action": "write", "enabled": True},
    {"scope": "admin_scope", "resource": "system", "action": "monitor", "enabled": True},
    # FX User Scope - Professional trading access
    {"scope": "fx_user_scope", "resource": "predictions", "action": "read", "enabled": True},
    {"scope": "fx_user_scope", "resource": "predictions", "action": "hft", "enabled": True},
    {"scope": "fx_user_scope", "resource": "data", "action": "realtime", "enabled": True},
    {"scope": "fx_user_scope", "resource": "backtest", "action": "run", "enabled": True},
    {"scope": "fx_user_scope", "resource": "websocket", "action": "connect", "enabled": True},
    # Big Better Scope - Premium access
    {"scope": "big_better_scope", "resource": "predictions", "action": "read", "enabled": True},
    {"scope": "big_better_scope", "resource": "predictions", "action": "enhanced", "enabled": True},
    {"scope": "big_better_scope", "resource": "analytics", "action": "read", "enabled": True},
    {"scope": "big_better_scope", "resource": "reports", "action": "custom", "enabled": True},
    {"scope": "big_better_scope", "resource": "websocket", "action": "connect", "enabled": True},
    # Regular Low Budget Scope - Basic access
    {"scope": "regular_low_budget_scope", "resource": "predictions", "action": "read", "enabled": True},
    {"scope": "regular_low_budget_scope", "resource": "predictions", "action": "basic", "enabled": True},
    {"scope": "regular_low_budget_scope", "resource": "data", "action": "read", "enabled": True},
    {"scope": "regular_low_budget_scope", "resource": "community", "action": "read", "enabled": True},
    # Public Consumer Scope - Free access
    {"scope": "public_consumer_scope", "resource": "predictions", "action": "read", "enabled": True},
    {"scope": "public_consumer_scope", "resource": "data", "action": "read", "enabled": True},
    {"scope": "public_consumer_scope", "resource": "community", "action": "read", "enabled": True},
]
