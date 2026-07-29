"""Subscription enforcement service for V5 commercial model.

This module implements:
- Subscription validation and enforcement
- Feature access control based on subscription tier
- Usage tracking and quota enforcement
- Subscription lifecycle management
- Billing cycle management
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum

from . import db
from .multi_scope_schema import SCOPES


class SubscriptionStatus(str, Enum):
    """Subscription status values."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PENDING = "pending"


class BillingCycle(str, Enum):
    """Billing cycle types."""

    MONTHLY = "monthly"
    YEARLY = "yearly"


class FeatureAccess(str, Enum):
    """Feature access levels."""

    FULL = "full"
    LIMITED = "limited"
    READ_ONLY = "read_only"
    DISABLED = "disabled"


class SubscriptionEnforcer:
    """Enforcer for subscription-based feature access."""

    def __init__(self):
        self._feature_cache: Dict[str, Dict[str, Any]] = {}
        self._plans_initialized = False

    def _initialize_subscription_plans(self) -> None:
        """Initialize default subscription plans for each scope."""
        # Check if plans already exist
        try:
            existing = db.query_one("SELECT COUNT(*) as c FROM subscription_plans")
            if existing and int(existing["c"]) > 0:
                self._plans_initialized = True
                return
        except Exception:
            # Table doesn't exist yet, will be initialized later
            self._plans_initialized = False
            return

        now = datetime.now(timezone.utc).isoformat()

        # My Scope - Included in platform
        db.execute(
            """INSERT INTO subscription_plans 
               (plan_id, name, scope, tier, price_monthly, price_yearly, currency, features, rate_limit, api_access, max_users, storage_limit, active, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "my_scope_included",
                "My Scope (Included)",
                "my_scope",
                "owner",
                0,
                0,
                "USD",
                json.dumps({"all_features": True, "unlimited": True}),
                None,  # Unlimited
                "full",
                None,  # Unlimited
                None,  # Unlimited
                1,
                now,
                now,
            ),
        )

        # Admin Scope - Included in platform
        db.execute(
            """INSERT INTO subscription_plans 
               (plan_id, name, scope, tier, price_monthly, price_yearly, currency, features, rate_limit, api_access, max_users, storage_limit, active, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "admin_scope_included",
                "Admin Scope (Included)",
                "admin_scope",
                "admin",
                0,
                0,
                "USD",
                json.dumps({"user_management": True, "monitoring": True, "vocabulary_admin": True}),
                10000,
                "administrative",
                100,
                1000000,
                1,
                now,
                now,
            ),
        )

        # FX User Scope - Premium ($499/mo)
        db.execute(
            """INSERT INTO subscription_plans 
               (plan_id, name, scope, tier, price_monthly, price_yearly, currency, features, rate_limit, api_access, max_users, storage_limit, active, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "fx_user_premium",
                "FX User Professional",
                "fx_user_scope",
                "premium",
                499,
                4990,
                "USD",
                json.dumps({
                    "hft_predictions": True,
                    "realtime_feed": True,
                    "advanced_analysis": True,
                    "api_access": "full",
                    "custom_models": True,
                }),
                50000,
                "full",
                50,
                5000000,
                1,
                now,
                now,
            ),
        )

        # Big Better Scope - Premium ($199/mo)
        db.execute(
            """INSERT INTO subscription_plans 
               (plan_id, name, scope, tier, price_monthly, price_yearly, currency, features, rate_limit, api_access, max_users, storage_limit, active, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "big_better_premium",
                "Big Better Premium",
                "big_better_scope",
                "premium",
                199,
                1990,
                "USD",
                json.dumps({
                    "advanced_predictions": True,
                    "realtime_feed": True,
                    "analysis_tools": True,
                    "api_access": "full",
                }),
                20000,
                "full",
                25,
                2000000,
                1,
                now,
                now,
            ),
        )

        # Regular Low Budget Scope - Basic ($29/mo)
        db.execute(
            """INSERT INTO subscription_plans 
               (plan_id, name, scope, tier, price_monthly, price_yearly, currency, features, rate_limit, api_access, max_users, storage_limit, active, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "regular_basic",
                "Regular Low Budget Basic",
                "regular_low_budget_scope",
                "basic",
                29,
                290,
                "USD",
                json.dumps({
                    "basic_predictions": True,
                    "delayed_feed": True,
                    "basic_analysis": True,
                    "api_access": "basic",
                }),
                5000,
                "basic",
                5,
                500000,
                1,
                now,
                now,
            ),
        )

        # Public Consumer Scope - Free
        db.execute(
            """INSERT INTO subscription_plans 
               (plan_id, name, scope, tier, price_monthly, price_yearly, currency, features, rate_limit, api_access, max_users, storage_limit, active, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "public_free",
                "Public Consumer Free",
                "public_consumer_scope",
                "free",
                0,
                0,
                "USD",
                json.dumps({
                    "public_predictions": True,
                    "public_feed": True,
                    "api_access": "read_only",
                }),
                1000,
                "read",
                1,
                100000,
                1,
                now,
                now,
            ),
        )

    def get_subscription(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get active subscription for a tenant.

        Args:
            tenant_id: Tenant ID

        Returns:
            Subscription dictionary or None
        """
        row = db.query_one(
            """SELECT s.*, sp.name as plan_name, sp.features as plan_features, sp.rate_limit as plan_rate_limit
               FROM subscriptions s
               LEFT JOIN subscription_plans sp ON s.plan_id = sp.plan_id
               WHERE s.tenant_id = ? AND s.status = 'active'
               ORDER BY s.created_at DESC
               LIMIT 1""",
            (tenant_id,),
        )

        if not row:
            return None

        return {
            "subscription_id": row["subscription_id"],
            "tenant_id": row["tenant_id"],
            "plan_id": row["plan_id"],
            "plan_name": row["plan_name"],
            "scope": row["scope"],
            "status": row["status"],
            "billing_cycle": row["billing_cycle"],
            "amount": row["amount"],
            "currency": row["currency"],
            "start_date": row["start_date"],
            "end_date": row["end_date"],
            "auto_renew": bool(row["auto_renew"]),
            "features": json.loads(row.get("features", "{}")),
            "plan_features": json.loads(row.get("plan_features", "{}")),
            "rate_limit": row.get("plan_rate_limit"),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def check_feature_access(
        self,
        tenant_id: str,
        feature: str,
        access_level: FeatureAccess = FeatureAccess.FULL,
    ) -> Tuple[bool, Optional[str]]:
        """Check if a tenant has access to a feature.

        Args:
            tenant_id: Tenant ID
            feature: Feature name
            access_level: Required access level

        Returns:
            Tuple of (allowed, reason)
        """
        subscription = self.get_subscription(tenant_id)

        if not subscription:
            # Check if tenant has a default scope-based plan
            tenant = db.query_one("SELECT scope FROM tenants WHERE tenant_id = ?", (tenant_id,))
            if not tenant:
                return False, "Tenant not found"

            # Use scope defaults
            scope_config = SCOPES.get(tenant["scope"], {})
            features = scope_config.get("features", [])

            if feature not in features:
                return False, f"Feature '{feature}' not available for scope '{tenant['scope']}'"

            return True, None

        # Check subscription features
        all_features = {**subscription["plan_features"], **subscription["features"]}

        if feature not in all_features:
            return False, f"Feature '{feature}' not included in subscription"

        # Check access level
        feature_config = all_features[feature]

        if isinstance(feature_config, bool):
            if not feature_config:
                return False, f"Feature '{feature}' is disabled"
        elif isinstance(feature_config, dict):
            level = feature_config.get("access", "full")
            if self._compare_access_level(level, access_level.value) < 0:
                return False, f"Feature '{feature}' requires higher access level"

        return True, None

    def _compare_access_level(self, current: str, required: str) -> int:
        """Compare access levels.

        Returns:
            1 if current >= required, -1 if current < required, 0 if equal
        """
        levels = {
            "disabled": 0,
            "read_only": 1,
            "limited": 2,
            "full": 3,
        }

        current_level = levels.get(current, 0)
        required_level = levels.get(required, 3)

        if current_level >= required_level:
            return 1
        elif current_level < required_level:
            return -1
        return 0

    def check_quota(
        self,
        tenant_id: str,
        resource_type: str,
        amount: int = 1,
    ) -> Tuple[bool, Optional[str]]:
        """Check if tenant has quota for a resource type.

        Args:
            tenant_id: Tenant ID
            resource_type: Resource type (api_calls, storage, etc.)
            amount: Amount to consume

        Returns:
            Tuple of (allowed, reason)
        """
        subscription = self.get_subscription(tenant_id)

        if not subscription:
            # Use scope defaults
            tenant = db.query_one("SELECT scope FROM tenants WHERE tenant_id = ?", (tenant_id,))
            if not tenant:
                return False, "Tenant not found"

            scope_config = SCOPES.get(tenant["scope"], {})
            if scope_config.get("rate_limit") is None:
                return True, None  # Unlimited

            quota = scope_config.get("rate_limit", 100)
        else:
            quota = subscription.get("rate_limit", 100)

        if quota is None:
            return True, None  # Unlimited

        # Get current usage
        now = datetime.now(timezone.utc)
        window_start = (now - timedelta(minutes=1)).isoformat()

        usage = db.query_one(
            """SELECT SUM(value) as total FROM usage_tracking
               WHERE tenant_id = ? AND metric = ? AND recorded_at >= ?""",
            (tenant_id, resource_type, window_start),
        )

        current_usage = int(usage["total"]) if usage and usage["total"] else 0

        if current_usage + amount > quota:
            return False, f"Quota exceeded for {resource_type}: {current_usage + amount}/{quota}"

        return True, None

    def record_usage(
        self,
        tenant_id: str,
        metric: str,
        value: float,
        unit: Optional[str] = None,
    ) -> None:
        """Record usage for billing/quota tracking.

        Args:
            tenant_id: Tenant ID
            metric: Metric name (api_calls, storage, etc.)
            value: Value to record
            unit: Optional unit
        """
        now = datetime.now(timezone.utc).isoformat()
        period = now[:7]  # YYYY-MM for monthly aggregation

        db.execute(
            """INSERT INTO usage_tracking 
               (tenant_id, scope, metric, value, unit, period, recorded_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                tenant_id,
                "",  # Scope from tenant query if needed
                metric,
                value,
                unit,
                period,
                now,
            ),
        )

    def create_subscription(
        self,
        tenant_id: str,
        plan_id: str,
        billing_cycle: BillingCycle = BillingCycle.MONTHLY,
        start_date: Optional[str] = None,
        auto_renew: bool = True,
    ) -> Dict[str, Any]:
        """Create a new subscription for a tenant.

        Args:
            tenant_id: Tenant ID
            plan_id: Plan ID
            billing_cycle: Billing cycle
            start_date: Optional start date
            auto_renew: Auto-renew flag

        Returns:
            Subscription dictionary
        """
        # Get plan details
        plan = db.query_one(
            "SELECT * FROM subscription_plans WHERE plan_id = ? AND active = 1",
            (plan_id,),
        )

        if not plan:
            raise ValueError(f"Plan not found: {plan_id}")

        # Calculate end date
        now = datetime.now(timezone.utc)
        start = datetime.fromisoformat(start_date) if start_date else now

        if billing_cycle == BillingCycle.MONTHLY:
            end = start + timedelta(days=30)
            amount = plan["price_monthly"]
        else:
            end = start + timedelta(days=365)
            amount = plan["price_yearly"]

        subscription_id = f"sub_{tenant_id[:8]}_{now.strftime('%Y%m%d%H%M%S')}"

        db.execute(
            """INSERT INTO subscriptions 
               (subscription_id, tenant_id, plan_id, scope, status, billing_cycle, amount, currency, start_date, end_date, auto_renew, features, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                subscription_id,
                tenant_id,
                plan_id,
                plan["scope"],
                "active",
                billing_cycle.value,
                amount,
                plan["currency"],
                start.isoformat(),
                end.isoformat(),
                1 if auto_renew else 0,
                "{}",
                now.isoformat(),
                now.isoformat(),
            ),
        )

        return self.get_subscription(tenant_id)

    def cancel_subscription(
        self,
        tenant_id: str,
        reason: Optional[str] = None,
    ) -> bool:
        """Cancel a tenant's subscription.

        Args:
            tenant_id: Tenant ID
            reason: Optional cancellation reason

        Returns:
            True if cancelled
        """
        subscription = self.get_subscription(tenant_id)
        if not subscription:
            return False

        db.execute(
            """UPDATE subscriptions 
               SET status = 'cancelled', end_date = ?, updated_at = ?
               WHERE subscription_id = ?""",
            (datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat(), subscription["subscription_id"]),
        )

        return True

    def check_subscription_status(self, tenant_id: str) -> Tuple[SubscriptionStatus, Optional[str]]:
        """Check and update subscription status.

        Args:
            tenant_id: Tenant ID

        Returns:
            Tuple of (status, reason)
        """
        subscription = self.get_subscription(tenant_id)

        if not subscription:
            return SubscriptionStatus.PENDING, "No active subscription"

        # Check expiration
        if subscription["end_date"]:
            end_date = datetime.fromisoformat(subscription["end_date"])
            if end_date < datetime.now(timezone.utc):
                # Update to expired
                db.execute(
                    """UPDATE subscriptions 
                       SET status = 'expired', updated_at = ?
                       WHERE subscription_id = ?""",
                    (datetime.now(timezone.utc).isoformat(), subscription["subscription_id"]),
                )
                return SubscriptionStatus.EXPIRED, "Subscription expired"

        return SubscriptionStatus(subscription["status"]), None

    def get_usage_report(
        self,
        tenant_id: str,
        period: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get usage report for a tenant.

        Args:
            tenant_id: Tenant ID
            period: Optional period (YYYY-MM format)

        Returns:
            Usage report dictionary
        """
        if not period:
            period = datetime.now(timezone.utc).isoformat()[:7]

        usage_rows = db.query(
            """SELECT metric, SUM(value) as total, unit
               FROM usage_tracking
               WHERE tenant_id = ? AND period = ?
               GROUP BY metric, unit""",
            (tenant_id, period),
        )

        usage = {
            row["metric"]: {"total": float(row["total"]), "unit": row["unit"]}
            for row in usage_rows
        }

        subscription = self.get_subscription(tenant_id)

        return {
            "tenant_id": tenant_id,
            "period": period,
            "usage": usage,
            "subscription": subscription,
        }


# Global enforcer instance
_subscription_enforcer = SubscriptionEnforcer()


def get_subscription_enforcer() -> SubscriptionEnforcer:
    """Get the global subscription enforcer instance."""
    return _subscription_enforcer
