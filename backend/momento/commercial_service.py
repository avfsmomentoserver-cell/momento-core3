"""Commercial service layer for V5 multi-scope architecture.

This service provides:
- Subscription management (5-tier pricing structure)
- Billing and payment integration (Stripe)
- Usage tracking and analytics
- Revenue tracking and reporting
- Customer lifecycle management
- Admin workflow integration
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple
from enum import Enum

from . import db, config

logger = logging.getLogger("momento.commercial_service")


# ---------------------------------------------------------------------------
# Enums and Constants
# ---------------------------------------------------------------------------

class SubscriptionStatus(str, Enum):
    """Subscription status values."""
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    EXPIRED = "expired"


class BillingPeriod(str, Enum):
    """Billing period types."""
    MONTHLY = "monthly"
    YEARLY = "yearly"


class SupportLevel(str, Enum):
    """Support level tiers."""
    COMMUNITY = "community"
    EMAIL = "email"
    PRIORITY = "priority"
    DEDICATED = "dedicated"


class ChangeType(str, Enum):
    """Subscription change types."""
    UPGRADE = "upgrade"
    DOWNGRADE = "downgrade"
    CANCEL = "cancel"
    RENEW = "renew"
    TRIAL_START = "trial_start"
    TRIAL_END = "trial_end"


class InvoiceStatus(str, Enum):
    """Invoice status values."""
    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    VOID = "void"
    UNCOLLECTIBLE = "uncollectible"


class MetricType(str, Enum):
    """Usage metric types."""
    API_REQUESTS = "api_requests"
    STORAGE = "storage"
    PREDICTIONS = "predictions"
    FORECASTS = "forecasts"
    ANALYSIS = "analysis"
    SESSIONS = "sessions"


# ---------------------------------------------------------------------------
# Subscription Management
# ---------------------------------------------------------------------------

def get_subscription_plans(active_only: bool = True) -> List[Dict[str, Any]]:
    """Get all subscription plans."""
    query = "SELECT * FROM subscription_plans"
    if active_only:
        query += " WHERE active = 1"
    query += " ORDER BY price_monthly ASC"
    
    rows = db.query(query)
    return [db.rows_to_dicts([row])[0] for row in rows]


def get_subscription_plan(plan_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific subscription plan by ID."""
    rows = db.query(
        "SELECT * FROM subscription_plans WHERE id = ?",
        (plan_id,)
    )
    if not rows:
        return None
    return db.rows_to_dicts([rows[0]])[0]


def get_plan_by_scope(scope: str) -> Optional[Dict[str, Any]]:
    """Get subscription plan by scope."""
    rows = db.query(
        "SELECT * FROM subscription_plans WHERE scope = ? AND active = 1",
        (scope,)
    )
    if not rows:
        return None
    return db.rows_to_dicts([rows[0]])[0]


def create_subscription_plan(
    plan_id: str,
    name: str,
    scope: str,
    price_monthly: float,
    price_yearly: float,
    currency: str = "USD",
    features: List[str] = None,
    rate_limit: int = 1000,
    api_access: Dict[str, Any] = None,
    support_level: str = "community",
    sla: Optional[str] = None,
    max_users: Optional[int] = None,
    storage_gb: Optional[float] = None,
) -> Dict[str, Any]:
    """Create a new subscription plan."""
    if features is None:
        features = []
    if api_access is None:
        api_access = {}
    
    now = db.utc_now()
    
    db.execute(
        """INSERT INTO subscription_plans 
           (id, name, scope, price_monthly, price_yearly, currency, features, 
            rate_limit, api_access, support_level, sla, max_users, storage_gb, 
            active, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)""",
        (
            plan_id, name, scope, price_monthly, price_yearly, currency,
            json.dumps(features), rate_limit, json.dumps(api_access),
            support_level, sla, max_users, storage_gb, now, now
        )
    )
    
    return get_subscription_plan(plan_id)


def update_subscription_plan(
    plan_id: str,
    **updates
) -> Optional[Dict[str, Any]]:
    """Update a subscription plan."""
    if not updates:
        return get_subscription_plan(plan_id)
    
    # Convert JSON fields
    if "features" in updates:
        updates["features"] = json.dumps(updates["features"])
    if "api_access" in updates:
        updates["api_access"] = json.dumps(updates["api_access"])
    
    updates["updated_at"] = db.utc_now()
    
    set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
    values = list(updates.values())
    values.append(plan_id)
    
    db.execute(
        f"UPDATE subscription_plans SET {set_clause} WHERE id = ?",
        values
    )
    
    return get_subscription_plan(plan_id)


def get_user_subscription(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user's current subscription."""
    rows = db.query(
        """SELECT * FROM user_subscriptions 
           WHERE user_id = ? 
           ORDER BY created_at DESC 
           LIMIT 1""",
        (user_id,)
    )
    if not rows:
        return None
    return db.rows_to_dicts([rows[0]])[0]


def create_user_subscription(
    user_id: int,
    plan_id: str,
    billing_period: str = "monthly",
    trial_days: Optional[int] = None,
    stripe_customer_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a new user subscription."""
    plan = get_subscription_plan(plan_id)
    if not plan:
        raise ValueError(f"Plan {plan_id} not found")
    
    now = db.utc_now()
    subscription_id = f"sub_{user_id}_{int(datetime.now(timezone.utc).timestamp())}"
    
    # Calculate period dates
    if billing_period == "monthly":
        period_end = datetime.now(timezone.utc) + timedelta(days=30)
    else:
        period_end = datetime.now(timezone.utc) + timedelta(days=365)
    
    # Trial setup
    trial_start = None
    trial_end = None
    status = SubscriptionStatus.ACTIVE
    
    if trial_days:
        trial_start = now
        trial_end = (datetime.now(timezone.utc) + timedelta(days=trial_days)).isoformat()
        status = SubscriptionStatus.TRIALING
    
    current_period_start = now
    current_period_end = period_end.isoformat()
    
    if metadata is None:
        metadata = {}
    
    db.execute(
        """INSERT INTO user_subscriptions 
           (id, user_id, plan_id, status, billing_period, 
            current_period_start, current_period_end, cancel_at_period_end,
            trial_start, trial_end, stripe_customer_id, stripe_subscription_id,
            metadata, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?)""",
        (
            subscription_id, user_id, plan_id, status, billing_period,
            current_period_start, current_period_end,
            trial_start, trial_end, stripe_customer_id, None,
            json.dumps(metadata), now, now
        )
    )
    
    # Record subscription history
    _record_subscription_history(
        subscription_id, user_id, None, plan_id, None, status,
        ChangeType.TRIAL_START if trial_days else ChangeType.RENEW,
        "New subscription created"
    )
    
    return get_user_subscription(user_id)


def update_user_subscription(
    subscription_id: str,
    **updates
) -> Optional[Dict[str, Any]]:
    """Update user subscription."""
    current = get_subscription_by_id(subscription_id)
    if not current:
        return None
    
    # Track changes for history
    previous_plan_id = current.get("plan_id")
    previous_status = current.get("status")
    
    change_type = None
    reason = updates.get("reason", "Subscription updated")
    
    if "plan_id" in updates and updates["plan_id"] != previous_plan_id:
        new_plan = get_subscription_plan(updates["plan_id"])
        old_plan = get_subscription_plan(previous_plan_id)
        if new_plan and old_plan:
            if new_plan["price_monthly"] > old_plan["price_monthly"]:
                change_type = ChangeType.UPGRADE
            else:
                change_type = ChangeType.DOWNGRADE
    
    if "status" in updates and updates["status"] != previous_status:
        if updates["status"] == SubscriptionStatus.CANCELED:
            change_type = ChangeType.CANCEL
        elif updates["status"] == SubscriptionStatus.ACTIVE:
            change_type = ChangeType.RENEW
    
    # Convert JSON fields
    if "metadata" in updates:
        updates["metadata"] = json.dumps(updates["metadata"])
    
    updates["updated_at"] = db.utc_now()
    
    # Remove reason from updates (not a column)
    reason = updates.pop("reason", "Subscription updated")
    
    set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
    values = list(updates.values())
    values.append(subscription_id)
    
    db.execute(
        f"UPDATE user_subscriptions SET {set_clause} WHERE id = ?",
        values
    )
    
    # Record history if significant change
    if change_type:
        _record_subscription_history(
            subscription_id, current["user_id"],
            previous_plan_id, updates.get("plan_id", previous_plan_id),
            previous_status, updates.get("status", previous_status),
            change_type, reason
        )
    
    return get_subscription_by_id(subscription_id)


def get_subscription_by_id(subscription_id: str) -> Optional[Dict[str, Any]]:
    """Get subscription by ID."""
    rows = db.query(
        "SELECT * FROM user_subscriptions WHERE id = ?",
        (subscription_id,)
    )
    if not rows:
        return None
    return db.rows_to_dicts([rows[0]])[0]


def cancel_subscription(
    subscription_id: str,
    cancel_at_period_end: bool = True,
    reason: str = "User requested cancellation"
) -> Optional[Dict[str, Any]]:
    """Cancel a subscription."""
    if cancel_at_period_end:
        return update_user_subscription(
            subscription_id,
            cancel_at_period_end=1,
            reason=reason
        )
    else:
        return update_user_subscription(
            subscription_id,
            status=SubscriptionStatus.CANCELED,
            reason=reason
        )


def _record_subscription_history(
    subscription_id: str,
    user_id: int,
    previous_plan_id: Optional[str],
    new_plan_id: str,
    previous_status: Optional[str],
    new_status: str,
    change_type: str,
    reason: str,
    changed_by: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Record subscription change in history."""
    if metadata is None:
        metadata = {}
    
    db.execute(
        """INSERT INTO subscription_history 
           (subscription_id, user_id, previous_plan_id, new_plan_id, 
            previous_status, new_status, change_type, reason, changed_by, 
            metadata, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            subscription_id, user_id, previous_plan_id, new_plan_id,
            previous_status, new_status, change_type, reason, changed_by,
            json.dumps(metadata), db.utc_now()
        )
    )


def get_subscription_history(
    user_id: Optional[int] = None,
    subscription_id: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Get subscription history."""
    query = "SELECT * FROM subscription_history"
    params = []
    
    if user_id:
        query += " WHERE user_id = ?"
        params.append(user_id)
    elif subscription_id:
        query += " WHERE subscription_id = ?"
        params.append(subscription_id)
    
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    
    rows = db.query(query, tuple(params))
    return db.rows_to_dicts(rows)


# ---------------------------------------------------------------------------
# Billing and Payment Integration
# ---------------------------------------------------------------------------

def create_payment_method(
    user_id: int,
    stripe_payment_method_id: str,
    payment_type: str,
    brand: Optional[str] = None,
    last4: Optional[str] = None,
    expiry_month: Optional[int] = None,
    expiry_year: Optional[int] = None,
    is_default: bool = False,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a payment method for user."""
    payment_method_id = f"pm_{user_id}_{int(datetime.now(timezone.utc).timestamp())}"
    
    if is_default:
        # Unset existing default
        db.execute(
            "UPDATE payment_methods SET is_default = 0 WHERE user_id = ?",
            (user_id,)
        )
    
    if metadata is None:
        metadata = {}
    
    db.execute(
        """INSERT INTO payment_methods 
           (id, user_id, stripe_payment_method_id, type, brand, last4, 
            expiry_month, expiry_year, is_default, metadata, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            payment_method_id, user_id, stripe_payment_method_id, payment_type,
            brand, last4, expiry_month, expiry_year, 1 if is_default else 0,
            json.dumps(metadata), db.utc_now()
        )
    )
    
    return get_payment_method(payment_method_id)


def get_payment_method(payment_method_id: str) -> Optional[Dict[str, Any]]:
    """Get payment method by ID."""
    rows = db.query(
        "SELECT * FROM payment_methods WHERE id = ?",
        (payment_method_id,)
    )
    if not rows:
        return None
    return db.rows_to_dicts([rows[0]])[0]


def get_user_payment_methods(user_id: int) -> List[Dict[str, Any]]:
    """Get all payment methods for user."""
    rows = db.query(
        "SELECT * FROM payment_methods WHERE user_id = ? ORDER BY is_default DESC, created_at DESC",
        (user_id,)
    )
    return db.rows_to_dicts(rows)


def set_default_payment_method(user_id: int, payment_method_id: str) -> bool:
    """Set default payment method for user."""
    # First unset all
    db.execute(
        "UPDATE payment_methods SET is_default = 0 WHERE user_id = ?",
        (user_id,)
    )
    
    # Set new default
    db.execute(
        "UPDATE payment_methods SET is_default = 1 WHERE id = ? AND user_id = ?",
        (payment_method_id, user_id)
    )
    
    return True


def create_invoice(
    user_id: int,
    subscription_id: str,
    amount: float,
    currency: str = "USD",
    status: str = InvoiceStatus.DRAFT,
    due_date: Optional[str] = None,
    description: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create an invoice."""
    invoice_id = f"inv_{user_id}_{int(datetime.now(timezone.utc).timestamp())}"
    
    if metadata is None:
        metadata = {}
    
    db.execute(
        """INSERT INTO invoices 
           (id, user_id, subscription_id, stripe_invoice_id, amount, currency, 
            status, due_date, paid_at, hosted_invoice_url, invoice_pdf_url, 
            description, metadata, created_at, updated_at)
           VALUES (?, ?, ?, NULL, ?, ?, ?, ?, NULL, NULL, NULL, ?, ?, ?, ?)""",
        (
            invoice_id, user_id, subscription_id, amount, currency, status,
            due_date, description, json.dumps(metadata), db.utc_now(), db.utc_now()
        )
    )
    
    return get_invoice(invoice_id)


def get_invoice(invoice_id: str) -> Optional[Dict[str, Any]]:
    """Get invoice by ID."""
    rows = db.query(
        "SELECT * FROM invoices WHERE id = ?",
        (invoice_id,)
    )
    if not rows:
        return None
    return db.rows_to_dicts([rows[0]])[0]


def get_user_invoices(
    user_id: int,
    status: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Get invoices for user."""
    query = "SELECT * FROM invoices WHERE user_id = ?"
    params = [user_id]
    
    if status:
        query += " AND status = ?"
        params.append(status)
    
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    
    rows = db.query(query, tuple(params))
    return db.rows_to_dicts(rows)


def update_invoice(
    invoice_id: str,
    **updates
) -> Optional[Dict[str, Any]]:
    """Update invoice."""
    if not updates:
        return get_invoice(invoice_id)
    
    # Convert JSON fields
    if "metadata" in updates:
        updates["metadata"] = json.dumps(updates["metadata"])
    
    updates["updated_at"] = db.utc_now()
    
    set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
    values = list(updates.values())
    values.append(invoice_id)
    
    db.execute(
        f"UPDATE invoices SET {set_clause} WHERE id = ?",
        values
    )
    
    return get_invoice(invoice_id)


def add_invoice_line_item(
    invoice_id: str,
    description: str,
    quantity: int = 1,
    unit_price: float = 0.0,
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Add line item to invoice."""
    amount = quantity * unit_price
    
    if metadata is None:
        metadata = {}
    
    db.execute(
        """INSERT INTO invoice_line_items 
           (invoice_id, description, quantity, unit_price, amount, 
            period_start, period_end, metadata, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            invoice_id, description, quantity, unit_price, amount,
            period_start, period_end, json.dumps(metadata), db.utc_now()
        )
    )
    
    # Update invoice total
    invoice = get_invoice(invoice_id)
    if invoice:
        new_amount = invoice["amount"] + amount
        update_invoice(invoice_id, amount=new_amount)
    
    return {"invoice_id": invoice_id, "amount": amount}


def get_invoice_line_items(invoice_id: str) -> List[Dict[str, Any]]:
    """Get line items for invoice."""
    rows = db.query(
        "SELECT * FROM invoice_line_items WHERE invoice_id = ? ORDER BY id",
        (invoice_id,)
    )
    return db.rows_to_dicts(rows)


# ---------------------------------------------------------------------------
# Usage Tracking and Analytics
# ---------------------------------------------------------------------------

def track_usage(
    user_id: int,
    subscription_id: str,
    metric_type: str,
    metric_value: float,
    unit: str = "count",
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Track usage metric for user."""
    if period_start is None:
        period_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    if period_end is None:
        period_end = (datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0) + 
                      timedelta(days=32)).replace(day=1).isoformat()
    
    if metadata is None:
        metadata = {}
    
    db.execute(
        """INSERT INTO usage_tracking 
           (user_id, subscription_id, metric_type, metric_value, unit, 
            period_start, period_end, metadata, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            user_id, subscription_id, metric_type, metric_value, unit,
            period_start, period_end, json.dumps(metadata), db.utc_now()
        )
    )
    
    return {"user_id": user_id, "metric_type": metric_type, "metric_value": metric_value}


def log_api_usage(
    user_id: int,
    subscription_id: Optional[str],
    endpoint: str,
    method: str,
    status_code: int,
    response_time_ms: float,
    request_size: Optional[int] = None,
    response_size: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Log API usage for analytics."""
    if metadata is None:
        metadata = {}
    
    db.execute(
        """INSERT INTO api_usage_logs 
           (user_id, subscription_id, endpoint, method, status_code, 
            response_time_ms, request_size, response_size, timestamp, metadata, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            user_id, subscription_id, endpoint, method, status_code,
            response_time_ms, request_size, response_size, db.utc_now(),
            json.dumps(metadata), db.utc_now()
        )
    )


def get_user_usage(
    user_id: int,
    metric_type: Optional[str] = None,
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Get usage data for user."""
    query = "SELECT * FROM usage_tracking WHERE user_id = ?"
    params = [user_id]
    
    if metric_type:
        query += " AND metric_type = ?"
        params.append(metric_type)
    
    if period_start:
        query += " AND period_start >= ?"
        params.append(period_start)
    
    if period_end:
        query += " AND period_end <= ?"
        params.append(period_end)
    
    query += " ORDER BY period_start DESC"
    
    rows = db.query(query, tuple(params))
    return db.rows_to_dicts(rows)


def get_aggregated_usage(
    user_id: int,
    metric_type: str,
    period_start: str,
    period_end: str,
) -> Dict[str, Any]:
    """Get aggregated usage for a metric and period."""
    rows = db.query(
        """SELECT metric_type, SUM(metric_value) as total_value, 
                  COUNT(*) as record_count, unit
           FROM usage_tracking 
           WHERE user_id = ? AND metric_type = ? 
           AND period_start >= ? AND period_end <= ?
           GROUP BY metric_type, unit""",
        (user_id, metric_type, period_start, period_end)
    )
    
    if not rows:
        return {
            "metric_type": metric_type,
            "total_value": 0,
            "record_count": 0,
            "unit": "count"
        }
    
    return db.rows_to_dicts([rows[0]])[0]


def get_api_usage_stats(
    user_id: Optional[int] = None,
    endpoint: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 1000
) -> List[Dict[str, Any]]:
    """Get API usage statistics."""
    query = "SELECT * FROM api_usage_logs"
    params = []
    conditions = []
    
    if user_id:
        conditions.append("user_id = ?")
        params.append(user_id)
    
    if endpoint:
        conditions.append("endpoint = ?")
        params.append(endpoint)
    
    if start_date:
        conditions.append("timestamp >= ?")
        params.append(start_date)
    
    if end_date:
        conditions.append("timestamp <= ?")
        params.append(end_date)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    
    rows = db.query(query, tuple(params))
    return db.rows_to_dicts(rows)


# ---------------------------------------------------------------------------
# Revenue Tracking and Reporting
# ---------------------------------------------------------------------------

def calculate_revenue(
    period: str = "monthly",
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
) -> Dict[str, Any]:
    """Calculate revenue metrics for a period."""
    if period_start is None:
        if period == "daily":
            period_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        elif period == "weekly":
            period_start = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        elif period == "monthly":
            period_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
        else:  # yearly
            period_start = datetime.now(timezone.utc).replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    
    if period_end is None:
        period_end = db.utc_now()
    
    # Get active subscriptions and their plans
    rows = db.query(
        """SELECT us.id, us.user_id, us.plan_id, us.status, sp.price_monthly, sp.price_yearly, us.billing_period
           FROM user_subscriptions us
           JOIN subscription_plans sp ON us.plan_id = sp.id
           WHERE us.status IN ('active', 'trialing')
           AND us.current_period_start >= ? AND us.current_period_end <= ?""",
        (period_start, period_end)
    )
    
    subscriptions = db.rows_to_dicts(rows)
    
    mrr = 0.0
    arr = 0.0
    subscriber_count = len(subscriptions)
    
    for sub in subscriptions:
        if sub["billing_period"] == "monthly":
            mrr += sub["price_monthly"]
            arr += sub["price_monthly"] * 12
        else:
            mrr += sub["price_yearly"] / 12
            arr += sub["price_yearly"]
    
    # Get new subscribers in period
    new_rows = db.query(
        """SELECT COUNT(*) as count FROM user_subscriptions 
           WHERE created_at >= ? AND created_at <= ?""",
        (period_start, period_end)
    )
    new_subscribers = new_rows[0]["count"] if new_rows else 0
    
    # Get churned subscribers in period
    churned_rows = db.query(
        """SELECT COUNT(*) as count FROM user_subscriptions 
           WHERE status = 'canceled' AND updated_at >= ? AND updated_at <= ?""",
        (period_start, period_end)
    )
    churned_subscribers = churned_rows[0]["count"] if churned_rows else 0
    
    # Calculate revenue metrics
    total_revenue = mrr  # Simplified - in production would use actual payments
    
    return {
        "period": period,
        "period_start": period_start,
        "period_end": period_end,
        "mrr": round(mrr, 2),
        "arr": round(arr, 2),
        "new_revenue": 0.0,  # Would be calculated from new subscriptions
        "churn_revenue": 0.0,  # Would be calculated from churned subscriptions
        "expansion_revenue": 0.0,  # Would be calculated from upgrades
        "total_revenue": round(total_revenue, 2),
        "subscriber_count": subscriber_count,
        "new_subscribers": new_subscribers,
        "churned_subscribers": churned_subscribers
    }


def save_revenue_snapshot(
    period: str,
    period_start: str,
    period_end: str,
    plan_id: str,
    **metrics
) -> Dict[str, Any]:
    """Save revenue snapshot to database."""
    db.execute(
        """INSERT INTO revenue 
           (period, period_start, period_end, plan_id, mrr, arr, 
            new_revenue, churn_revenue, expansion_revenue, total_revenue,
            subscriber_count, new_subscribers, churned_subscribers, 
            metadata, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            period, period_start, period_end, plan_id,
            metrics.get("mrr", 0), metrics.get("arr", 0),
            metrics.get("new_revenue", 0), metrics.get("churn_revenue", 0),
            metrics.get("expansion_revenue", 0), metrics.get("total_revenue", 0),
            metrics.get("subscriber_count", 0), metrics.get("new_subscribers", 0),
            metrics.get("churned_subscribers", 0),
            json.dumps(metrics.get("metadata", {})),
            db.utc_now(), db.utc_now()
        )
    )
    
    return {"period": period, "period_start": period_start, "period_end": period_end}


def get_revenue_history(
    period: Optional[str] = None,
    plan_id: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Get revenue history."""
    query = "SELECT * FROM revenue"
    params = []
    conditions = []
    
    if period:
        conditions.append("period = ?")
        params.append(period)
    
    if plan_id:
        conditions.append("plan_id = ?")
        params.append(plan_id)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY period_start DESC LIMIT ?"
    params.append(limit)
    
    rows = db.query(query, tuple(params))
    return db.rows_to_dicts(rows)


def get_revenue_by_plan(plan_id: str, months: int = 12) -> List[Dict[str, Any]]:
    """Get monthly revenue for a specific plan."""
    start_date = (datetime.now(timezone.utc) - timedelta(days=30*months)).isoformat()
    
    rows = db.query(
        """SELECT * FROM revenue 
           WHERE plan_id = ? AND period_start >= ? 
           ORDER BY period_start DESC""",
        (plan_id, start_date)
    )
    
    return db.rows_to_dicts(rows)


# ---------------------------------------------------------------------------
# Customer Lifecycle Management
# ---------------------------------------------------------------------------

def get_customer_lifecycle_data(user_id: int) -> Dict[str, Any]:
    """Get comprehensive customer lifecycle data."""
    # Get user info
    user_rows = db.query("SELECT * FROM users WHERE id = ?", (user_id,))
    if not user_rows:
        return {}
    user = db.rows_to_dicts([user_rows[0]])[0]
    
    # Get subscription
    subscription = get_user_subscription(user_id)
    
    # Get subscription history
    history = get_subscription_history(user_id=user_id)
    
    # Get usage data
    usage = get_user_usage(user_id)
    
    # Get invoices
    invoices = get_user_invoices(user_id)
    
    # Calculate lifecycle metrics
    total_revenue = sum(inv.get("amount", 0) for inv in invoices if inv.get("status") == "paid")
    subscription_age = 0
    if subscription and subscription.get("created_at"):
        try:
            created = datetime.fromisoformat(subscription["created_at"])
            subscription_age = (datetime.now(timezone.utc) - created).days
        except:
            pass
    
    return {
        "user": user,
        "subscription": subscription,
        "subscription_history": history,
        "usage": usage,
        "invoices": invoices,
        "lifecycle_metrics": {
            "total_revenue": total_revenue,
            "subscription_age_days": subscription_age,
            "invoice_count": len(invoices),
            "usage_records": len(usage)
        }
    }


def get_churn_risk_analysis(user_id: int) -> Dict[str, Any]:
    """Analyze churn risk for a user."""
    lifecycle = get_customer_lifecycle_data(user_id)
    subscription = lifecycle.get("subscription")
    
    if not subscription:
        return {"risk": "no_subscription", "score": 0}
    
    risk_factors = []
    risk_score = 0
    
    # Factor 1: Payment issues
    if subscription.get("status") == "past_due":
        risk_factors.append("past_due_payment")
        risk_score += 30
    
    # Factor 2: Low usage
    usage = lifecycle.get("usage", [])
    recent_usage = [u for u in usage if u.get("period_start", "") > (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()]
    if len(recent_usage) < 5:
        risk_factors.append("low_usage")
        risk_score += 20
    
    # Factor 3: Cancellation scheduled
    if subscription.get("cancel_at_period_end"):
        risk_factors.append("cancellation_scheduled")
        risk_score += 50
    
    # Factor 4: Recent downgrades
    history = lifecycle.get("subscription_history", [])
    recent_changes = [h for h in history if h.get("created_at", "") > (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()]
    downgrades = [h for h in recent_changes if h.get("change_type") == "downgrade"]
    if downgrades:
        risk_factors.append("recent_downgrade")
        risk_score += 25
    
    # Determine risk level
    if risk_score >= 50:
        risk_level = "high"
    elif risk_score >= 25:
        risk_level = "medium"
    else:
        risk_level = "low"
    
    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "risk_factors": risk_factors,
        "recommendations": _get_churn_mitigation_recommendations(risk_factors)
    }


def _get_churn_mitigation_recommendations(risk_factors: List[str]) -> List[str]:
    """Get recommendations for churn mitigation."""
    recommendations = []
    
    if "past_due_payment" in risk_factors:
        recommendations.append("Send payment reminder email")
        recommendations.append("Offer payment plan options")
    
    if "low_usage" in risk_factors:
        recommendations.append("Send engagement email with tips")
        recommendations.append("Offer onboarding assistance")
    
    if "cancellation_scheduled" in risk_factors:
        recommendations.append("Send retention survey")
        recommendations.append("Offer discount for renewal")
    
    if "recent_downgrade" in risk_factors:
        recommendations.append("Schedule check-in call")
        recommendations.append("Gather feedback on downgrade reason")
    
    return recommendations


def get_expansion_opportunities(user_id: int) -> List[Dict[str, Any]]:
    """Identify expansion opportunities for a user."""
    lifecycle = get_customer_lifecycle_data(user_id)
    subscription = lifecycle.get("subscription")
    
    if not subscription:
        return []
    
    opportunities = []
    current_plan = get_subscription_plan(subscription["plan_id"])
    
    if not current_plan:
        return []
    
    # Check for upgrade opportunities
    all_plans = get_subscription_plans()
    current_price = current_plan.get("price_monthly", 0)
    
    for plan in all_plans:
        if plan["price_monthly"] > current_price:
            opportunities.append({
                "type": "upgrade",
                "target_plan": plan["id"],
                "target_plan_name": plan["name"],
                "price_difference": plan["price_monthly"] - current_price,
                "reason": "higher_tier_available"
            })
    
    # Check for annual billing opportunity
    if subscription.get("billing_period") == "monthly" and current_plan.get("price_yearly"):
        monthly_equivalent = current_plan["price_yearly"] / 12
        savings = (current_plan["price_monthly"] * 12) - current_plan["price_yearly"]
        if savings > 0:
            opportunities.append({
                "type": "annual_billing",
                "savings": round(savings, 2),
                "reason": "annual_savings"
            })
    
    return opportunities


# ---------------------------------------------------------------------------
# Admin Workflow Integration
# ---------------------------------------------------------------------------

def get_admin_dashboard_data() -> Dict[str, Any]:
    """Get comprehensive data for admin dashboard."""
    # Revenue metrics
    revenue_metrics = calculate_revenue("monthly")
    
    # Subscription metrics
    total_subscriptions = len(db.query("SELECT * FROM user_subscriptions WHERE status = 'active'"))
    trial_subscriptions = len(db.query("SELECT * FROM user_subscriptions WHERE status = 'trialing"))
    past_due_subscriptions = len(db.query("SELECT * FROM user_subscriptions WHERE status = 'past_due'"))
    
    # User metrics
    total_users = len(db.query("SELECT * FROM users WHERE active = 1"))
    
    # Recent activity
    recent_invoices = get_user_invoices(user_id=0, limit=10)  # Get all recent invoices
    recent_subscriptions = db.query(
        "SELECT * FROM user_subscriptions ORDER BY created_at DESC LIMIT 10"
    )
    
    # Plan distribution
    plan_distribution = db.query(
        """SELECT sp.name, COUNT(*) as count 
           FROM user_subscriptions us
           JOIN subscription_plans sp ON us.plan_id = sp.id
           WHERE us.status = 'active'
           GROUP BY sp.id, sp.name"""
    )
    
    return {
        "revenue": revenue_metrics,
        "subscriptions": {
            "total": total_subscriptions,
            "trialing": trial_subscriptions,
            "past_due": past_due_subscriptions
        },
        "users": {
            "total": total_users
        },
        "recent_activity": {
            "invoices": [db.rows_to_dicts([row])[0] for row in recent_invoices] if recent_invoices else [],
            "subscriptions": [db.rows_to_dicts([row])[0] for row in recent_subscriptions] if recent_subscriptions else []
        },
        "plan_distribution": [db.rows_to_dicts([row])[0] for row in plan_distribution] if plan_distribution else []
    }


def get_admin_user_management_data(limit: int = 50) -> List[Dict[str, Any]]:
    """Get user data for admin management."""
    rows = db.query(
        """SELECT u.*, us.plan_id, us.status as subscription_status, sp.name as plan_name
           FROM users u
           LEFT JOIN user_subscriptions us ON u.id = us.user_id
           LEFT JOIN subscription_plans sp ON us.plan_id = sp.id
           WHERE u.active = 1
           ORDER BY u.created_at DESC
           LIMIT ?""",
        (limit,)
    )
    return db.rows_to_dicts(rows)


def get_admin_financial_report(
    period_start: Optional[str] = None,
    period_end: Optional[str] = None
) -> Dict[str, Any]:
    """Generate financial report for admin."""
    if period_start is None:
        period_start = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    if period_end is None:
        period_end = db.utc_now()
    
    # Revenue by plan
    revenue_by_plan = db.query(
        """SELECT sp.name, sp.price_monthly, COUNT(*) as subscribers
           FROM user_subscriptions us
           JOIN subscription_plans sp ON us.plan_id = sp.id
           WHERE us.status = 'active' AND us.created_at >= ? AND us.created_at <= ?
           GROUP BY sp.id, sp.name, sp.price_monthly""",
        (period_start, period_end)
    )
    
    # Invoice totals
    invoice_totals = db.query(
        """SELECT status, SUM(amount) as total, COUNT(*) as count
           FROM invoices
           WHERE created_at >= ? AND created_at <= ?
           GROUP BY status""",
        (period_start, period_end)
    )
    
    # Churn analysis
    churned = db.query(
        """SELECT COUNT(*) as count FROM user_subscriptions 
           WHERE status = 'canceled' AND updated_at >= ? AND updated_at <= ?""",
        (period_start, period_end)
    )
    
    return {
        "period": {"start": period_start, "end": period_end},
        "revenue_by_plan": [db.rows_to_dicts([row])[0] for row in revenue_by_plan] if revenue_by_plan else [],
        "invoice_totals": [db.rows_to_dicts([row])[0] for row in invoice_totals] if invoice_totals else [],
        "churned_count": churned[0]["count"] if churned else 0
    }


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

def initialize_default_plans() -> None:
    """Initialize default subscription plans based on V5 architecture."""
    plans = [
        {
            "id": "my_scope",
            "name": "My Scope - Platform Owner",
            "scope": "my_scope",
            "price_monthly": 0,
            "price_yearly": 0,
            "currency": "USD",
            "features": [
                "Full system access",
                "Architecture control",
                "Business intelligence",
                "24/7 dedicated support",
                "99.999% SLA"
            ],
            "rate_limit": 100000,
            "api_access": {"all": True, "admin": True},
            "support_level": "dedicated",
            "sla": "99.999%",
            "max_users": 1,
            "storage_gb": None
        },
        {
            "id": "admin_scope",
            "name": "Admin Scope - System Administrator",
            "scope": "admin_scope",
            "price_monthly": 0,
            "price_yearly": 0,
            "currency": "USD",
            "features": [
                "User management",
                "System monitoring",
                "Admin vocabulary access",
                "Incident management",
                "Priority support"
            ],
            "rate_limit": 10000,
            "api_access": {"admin": True, "monitoring": True},
            "support_level": "priority",
            "sla": "99.9%",
            "max_users": 10,
            "storage_gb": 100
        },
        {
            "id": "fx_scope",
            "name": "FX User Scope - Professional Trading",
            "scope": "fx_scope",
            "price_monthly": 499,
            "price_yearly": 4990,
            "currency": "USD",
            "features": [
                "Real-time predictions",
                "Advanced analytics",
                "API access",
                "Priority support",
                "99.9% SLA"
            ],
            "rate_limit": 5000,
            "api_access": {"predictions": True, "analysis": True, "api": True},
            "support_level": "priority",
            "sla": "99.9%",
            "max_users": 5,
            "storage_gb": 50
        },
        {
            "id": "big_better_scope",
            "name": "Big Better Scope - Premium Clients",
            "scope": "big_better_scope",
            "price_monthly": 199,
            "price_yearly": 1990,
            "currency": "USD",
            "features": [
                "Advanced predictions",
                "Basic analytics",
                "API access",
                "Email support",
                "99.5% SLA"
            ],
            "rate_limit": 2000,
            "api_access": {"predictions": True, "analysis": True, "api": True},
            "support_level": "email",
            "sla": "99.5%",
            "max_users": 3,
            "storage_gb": 25
        },
        {
            "id": "regular_scope",
            "name": "Regular Scope - Low Budget Predictor",
            "scope": "regular_scope",
            "price_monthly": 29,
            "price_yearly": 290,
            "currency": "USD",
            "features": [
                "Basic predictions",
                "Limited analytics",
                "Web access only",
                "Community support",
                "99.0% SLA"
            ],
            "rate_limit": 500,
            "api_access": {"predictions": True, "web": True},
            "support_level": "community",
            "sla": "99.0%",
            "max_users": 1,
            "storage_gb": 5
        },
        {
            "id": "public_scope",
            "name": "Public Consumer Scope - Free",
            "scope": "public_scope",
            "price_monthly": 0,
            "price_yearly": 0,
            "currency": "USD",
            "features": [
                "Limited predictions",
                "Basic interface",
                "Community support",
                "No SLA"
            ],
            "rate_limit": 100,
            "api_access": {"web": True},
            "support_level": "community",
            "sla": None,
            "max_users": 1,
            "storage_gb": 1
        }
    ]
    
    for plan_data in plans:
        existing = get_subscription_plan(plan_data["id"])
        if not existing:
            create_subscription_plan(**plan_data)
            logger.info(f"Created default plan: {plan_data['id']}")
        else:
            logger.info(f"Plan already exists: {plan_data['id']}")


def initialize_commercial_schema() -> None:
    """Initialize commercial schema in database."""
    from .commercial_schema import COMMERCIAL_SCHEMA

    with db.transaction() as conn:
        # Split schema into individual statements
        statements = [s.strip() for s in COMMERCIAL_SCHEMA.split(';') if s.strip()]

        for statement in statements:
            try:
                conn.execute(statement)
            except Exception as e:
                logger.warning(f"Schema initialization warning: {e}")

    logger.info("Commercial schema initialized")

    # Initialize default plans
    initialize_default_plans()


# ---------------------------------------------------------------------------
# Feature Gating System
# ---------------------------------------------------------------------------

def get_feature_gate(feature_key: str) -> Optional[Dict[str, Any]]:
    """Get a feature gate by key."""
    rows = db.query(
        "SELECT * FROM feature_gates WHERE feature_key = ?",
        (feature_key,)
    )
    if not rows:
        return None
    gate = db.rows_to_dicts([rows[0]])[0]
    # Parse JSON fields
    if gate.get("enabled_plans"):
        gate["enabled_plans"] = json.loads(gate["enabled_plans"])
    if gate.get("enabled_scopes"):
        gate["enabled_scopes"] = json.loads(gate["enabled_scopes"])
    return gate


def get_all_feature_gates(
    category: Optional[str] = None,
    pricing_model: Optional[str] = None,
    is_public: Optional[bool] = None
) -> List[Dict[str, Any]]:
    """Get all feature gates with optional filters."""
    query = "SELECT * FROM feature_gates WHERE 1=1"
    params = []

    if category:
        query += " AND category = ?"
        params.append(category)
    if pricing_model:
        query += " AND pricing_model = ?"
        params.append(pricing_model)
    if is_public is not None:
        query += " AND is_public = ?"
        params.append(1 if is_public else 0)

    query += " ORDER BY category, feature_name"

    rows = db.query(query, tuple(params))
    gates = [db.rows_to_dicts([row])[0] for row in rows]

    # Parse JSON fields
    for gate in gates:
        if gate.get("enabled_plans"):
            gate["enabled_plans"] = json.loads(gate["enabled_plans"])
        if gate.get("enabled_scopes"):
            gate["enabled_scopes"] = json.loads(gate["enabled_scopes"])

    return gates


def check_feature_access(
    user_id: int,
    feature_key: str,
    scope: Optional[str] = None
) -> Dict[str, Any]:
    """Check if a user has access to a feature."""
    gate = get_feature_gate(feature_key)
    if not gate:
        return {"has_access": False, "reason": "Feature not found"}

    # Get user's subscription
    subscription = get_user_subscription(user_id)
    if not subscription:
        # Check if feature is available to public scope
        if "plan_public_scope" in gate.get("enabled_plans", []):
            return {"has_access": True, "reason": "Public access", "gate": gate}
        return {"has_access": False, "reason": "No subscription"}

    plan_id = subscription.get("plan_id")
    user_scope = scope or subscription.get("scope")

    # Check if plan has access
    enabled_plans = gate.get("enabled_plans", [])
    if plan_id not in enabled_plans:
        return {"has_access": False, "reason": "Plan does not include feature"}

    # Check if scope has access
    enabled_scopes = gate.get("enabled_scopes", [])
    if user_scope and user_scope not in enabled_scopes:
        return {"has_access": False, "reason": "Scope does not include feature"}

    return {"has_access": True, "reason": "Access granted", "gate": gate}


def create_feature_gate(
    feature_key: str,
    feature_name: str,
    description: Optional[str] = None,
    category: str = "general",
    pricing_model: str = "subscription",
    base_price: float = 0,
    unit_price: float = 0,
    unit_name: Optional[str] = None,
    included_units: int = 0,
    enabled_plans: List[str] = None,
    enabled_scopes: List[str] = None,
    is_beta: bool = False,
    is_public: bool = True,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a new feature gate."""
    if enabled_plans is None:
        enabled_plans = []
    if enabled_scopes is None:
        enabled_scopes = []
    if metadata is None:
        metadata = {}

    now = db.utc_now()

    db.execute(
        """INSERT INTO feature_gates
           (id, feature_key, feature_name, description, category, pricing_model,
            base_price, unit_price, unit_name, included_units, enabled_plans,
            enabled_scopes, is_beta, is_public, metadata, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            f"fg_{feature_key.replace('.', '_')}", feature_key, feature_name,
            description, category, pricing_model, base_price, unit_price,
            unit_name, included_units, json.dumps(enabled_plans),
            json.dumps(enabled_scopes), 1 if is_beta else 0,
            1 if is_public else 0, json.dumps(metadata), now, now
        )
    )

    return get_feature_gate(feature_key)


# ---------------------------------------------------------------------------
# Usage-Based Pricing
# ---------------------------------------------------------------------------

def track_feature_usage(
    user_id: int,
    feature_key: str,
    usage_value: float = 1.0,
    subscription_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Track usage for a feature."""
    if subscription_id is None:
        subscription = get_user_subscription(user_id)
        if not subscription:
            raise ValueError("User has no subscription")
        subscription_id = subscription["id"]

    # Get period dates (current month)
    now = datetime.now(timezone.utc)
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    period_end = (now.replace(day=1, hour=0, minute=0, second=0, microsecond=0) +
                  timedelta(days=32)).replace(day=1).isoformat()

    # Check if usage record exists for this period
    rows = db.query(
        """SELECT * FROM feature_usage
           WHERE user_id = ? AND feature_key = ? AND period_start = ?""",
        (user_id, feature_key, period_start)
    )

    if rows:
        # Update existing record
        existing = db.rows_to_dicts([rows[0]])[0]
        db.execute(
            """UPDATE feature_usage
               SET usage_count = usage_count + 1,
                   usage_value = usage_value + ?,
                   updated_at = ?
               WHERE id = ?""",
            (usage_value, db.utc_now(), existing["id"])
        )
        return db.rows_to_dicts([db.query(
            "SELECT * FROM feature_usage WHERE id = ?",
            (existing["id"],)
        )[0]])[0]
    else:
        # Create new record
        if metadata is None:
            metadata = {}

        db.execute(
            """INSERT INTO feature_usage
               (user_id, subscription_id, feature_key, usage_count, usage_value,
                period_start, period_end, metadata, created_at, updated_at)
               VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?, ?)""",
            (user_id, subscription_id, feature_key, usage_value,
             period_start, period_end, json.dumps(metadata),
             db.utc_now(), db.utc_now())
        )

        return db.rows_to_dicts([db.query(
            """SELECT * FROM feature_usage
               WHERE user_id = ? AND feature_key = ? AND period_start = ?""",
            (user_id, feature_key, period_start)
        )[0]])[0]


def calculate_usage_cost(
    user_id: int,
    feature_key: str,
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
) -> Dict[str, Any]:
    """Calculate cost for usage-based pricing."""
    gate = get_feature_gate(feature_key)
    if not gate or gate.get("pricing_model") != "usage_based":
        return {"cost": 0, "breakdown": [], "reason": "Not usage-based feature"}

    # Get usage for period
    if not period_start:
        now = datetime.now(timezone.utc)
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    if not period_end:
        now = datetime.now(timezone.utc)
        period_end = (now.replace(day=1, hour=0, minute=0, second=0, microsecond=0) +
                      timedelta(days=32)).replace(day=1).isoformat()

    rows = db.query(
        """SELECT * FROM feature_usage
           WHERE user_id = ? AND feature_key = ? AND period_start = ?""",
        (user_id, feature_key, period_start)
    )

    if not rows:
        return {"cost": 0, "breakdown": [], "usage": 0}

    usage_record = db.rows_to_dicts([rows[0]])[0]
    total_usage = usage_record["usage_value"]
    included_units = gate.get("included_units", 0)

    # Get pricing tiers
    tier_rows = db.query(
        """SELECT * FROM pricing_tiers
           WHERE feature_key = ? AND active = 1
           ORDER BY min_units ASC""",
        (feature_key,)
    )

    tiers = [db.rows_to_dicts([row])[0] for row in tier_rows]

    # Calculate cost based on tiers
    cost = gate.get("base_price", 0)
    breakdown = []
    remaining_usage = max(0, total_usage - included_units)

    for tier in tiers:
        if remaining_usage <= 0:
            break

        tier_min = tier["min_units"]
        tier_max = tier.get("max_units")
        tier_price = tier["price_per_unit"]

        # Calculate units in this tier
        tier_units = remaining_usage
        if tier_max is not None:
            tier_units = min(remaining_usage, tier_max - tier_min + 1)

        tier_cost = tier_units * tier_price
        cost += tier_cost
        breakdown.append({
            "tier": tier["tier_name"],
            "units": tier_units,
            "price_per_unit": tier_price,
            "cost": tier_cost
        })

        remaining_usage -= tier_units

    return {
        "cost": cost,
        "breakdown": breakdown,
        "usage": total_usage,
        "included_units": included_units,
        "billable_units": max(0, total_usage - included_units),
        "currency": "USD"
    }


def get_pricing_tiers(feature_key: str) -> List[Dict[str, Any]]:
    """Get pricing tiers for a feature."""
    rows = db.query(
        """SELECT * FROM pricing_tiers
           WHERE feature_key = ? AND active = 1
           ORDER BY min_units ASC""",
        (feature_key,)
    )

    tiers = [db.rows_to_dicts([row])[0] for row in rows]

    # Parse JSON fields
    for tier in tiers:
        if tier.get("applies_to_plans"):
            tier["applies_to_plans"] = json.loads(tier["applies_to_plans"])

    return tiers


def create_pricing_tier(
    feature_key: str,
    tier_name: str,
    min_units: float,
    max_units: Optional[float],
    price_per_unit: float,
    currency: str = "USD",
    applies_to_plans: List[str] = None,
) -> Dict[str, Any]:
    """Create a pricing tier for a feature."""
    if applies_to_plans is None:
        applies_to_plans = []

    now = db.utc_now()
    tier_id = f"pt_{feature_key.replace('.', '_')}_{tier_name.lower().replace(' ', '_')}"

    db.execute(
        """INSERT INTO pricing_tiers
           (id, feature_key, tier_name, min_units, max_units, price_per_unit,
            currency, applies_to_plans, active, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)""",
        (tier_id, feature_key, tier_name, min_units, max_units,
         price_per_unit, currency, json.dumps(applies_to_plans), now, now)
    )

    return db.rows_to_dicts([db.query(
        "SELECT * FROM pricing_tiers WHERE id = ?",
        (tier_id,)
    )[0]])[0]


# ---------------------------------------------------------------------------
# Usage Quotas
# ---------------------------------------------------------------------------

def get_usage_quota(
    subscription_id: str,
    feature_key: str
) -> Optional[Dict[str, Any]]:
    """Get usage quota for a subscription feature."""
    rows = db.query(
        "SELECT * FROM usage_quotas WHERE subscription_id = ? AND feature_key = ?",
        (subscription_id, feature_key)
    )
    if not rows:
        return None
    return db.rows_to_dicts([rows[0]])[0]


def set_usage_quota(
    subscription_id: str,
    feature_key: str,
    quota_limit: int,
    warning_threshold: float = 0.8,
) -> Dict[str, Any]:
    """Set usage quota for a subscription feature."""
    now = datetime.now(timezone.utc)
    # Reset at end of current month
    quota_reset_at = (now.replace(day=1, hour=0, minute=0, second=0, microsecond=0) +
                     timedelta(days=32)).replace(day=1).isoformat()

    # Check if quota exists
    existing = get_usage_quota(subscription_id, feature_key)

    if existing:
        db.execute(
            """UPDATE usage_quotas
               SET quota_limit = ?, warning_threshold = ?, quota_reset_at = ?, updated_at = ?
               WHERE id = ?""",
            (quota_limit, warning_threshold, quota_reset_at, now, existing["id"])
        )
        return get_usage_quota(subscription_id, feature_key)
    else:
        db.execute(
            """INSERT INTO usage_quotas
               (subscription_id, feature_key, quota_limit, quota_used, quota_reset_at,
                warning_threshold, alert_sent, metadata, created_at, updated_at)
               VALUES (?, ?, ?, 0, ?, ?, 0, '{}', ?, ?)""",
            (subscription_id, feature_key, quota_limit, quota_reset_at,
             warning_threshold, now, now)
        )
        return get_usage_quota(subscription_id, feature_key)


def check_quota_and_increment(
    subscription_id: str,
    feature_key: str,
    increment: int = 1,
) -> Dict[str, Any]:
    """Check quota and increment usage. Returns True if under limit."""
    quota = get_usage_quota(subscription_id, feature_key)
    if not quota:
        # No quota set, allow
        return {"allowed": True, "quota_used": 0, "quota_limit": None}

    # Check if quota needs reset
    now = datetime.now(timezone.utc)
    reset_at = datetime.fromisoformat(quota["quota_reset_at"])
    if now >= reset_at:
        # Reset quota
        db.execute(
            "UPDATE usage_quotas SET quota_used = 0, alert_sent = 0 WHERE id = ?",
            (quota["id"],)
        )
        quota["quota_used"] = 0

    new_usage = quota["quota_used"] + increment
    warning_threshold = quota.get("warning_threshold", 0.8)

    # Check if over limit
    if new_usage > quota["quota_limit"]:
        return {
            "allowed": False,
            "quota_used": quota["quota_used"],
            "quota_limit": quota["quota_limit"],
            "exceeded_by": new_usage - quota["quota_limit"]
        }

    # Check if warning threshold reached
    warning_reached = (new_usage / quota["quota_limit"]) >= warning_threshold
    if warning_reached and not quota["alert_sent"]:
        db.execute(
            "UPDATE usage_quotas SET alert_sent = 1 WHERE id = ?",
            (quota["id"],)
        )

    # Increment usage
    db.execute(
        "UPDATE usage_quotas SET quota_used = ? WHERE id = ?",
        (new_usage, quota["id"])
    )

    return {
        "allowed": True,
        "quota_used": new_usage,
        "quota_limit": quota["quota_limit"],
        "warning_reached": warning_reached
    }


# ---------------------------------------------------------------------------
# Revenue Analytics
# ---------------------------------------------------------------------------

def calculate_revenue_metrics(
    period: str = "monthly",
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
) -> Dict[str, Any]:
    """Calculate revenue metrics for a period."""
    if not period_start:
        now = datetime.now(timezone.utc)
        if period == "daily":
            period_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            period_end = (now.replace(hour=0, minute=0, second=0, microsecond=0) +
                        timedelta(days=1)).isoformat()
        elif period == "weekly":
            period_start = (now - timedelta(days=now.weekday())).replace(
                hour=0, minute=0, second=0, microsecond=0).isoformat()
            period_end = (now - timedelta(days=now.weekday()) + timedelta(days=7)).replace(
                hour=0, minute=0, second=0, microsecond=0).isoformat()
        else:  # monthly
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
            period_end = (now.replace(day=1, hour=0, minute=0, second=0, microsecond=0) +
                        timedelta(days=32)).replace(day=1).isoformat()

    # Get active subscriptions
    rows = db.query(
        """SELECT plan_id, COUNT(*) as count,
                  SUM(CASE WHEN billing_period = 'monthly' THEN price_monthly ELSE price_yearly / 12 END) as mrr
           FROM user_subscriptions us
           JOIN subscription_plans sp ON us.plan_id = sp.id
           WHERE us.status = 'active'
           GROUP BY plan_id"""
    )

    total_mrr = 0
    total_subscribers = 0
    plan_revenue = {}

    for row in rows:
        plan_data = db.rows_to_dicts([row])[0]
        plan_id = plan_data["plan_id"]
        count = plan_data["count"]
        mrr = plan_data["mrr"] or 0

        total_mrr += mrr
        total_subscribers += count
        plan_revenue[plan_id] = {
            "subscribers": count,
            "mrr": mrr,
            "arr": mrr * 12
        }

    # Get new subscriptions in period
    new_rows = db.query(
        """SELECT plan_id, COUNT(*) as count
           FROM user_subscriptions
           WHERE created_at >= ? AND created_at < ?
           GROUP BY plan_id""",
        (period_start, period_end)
    )

    new_subscribers = 0
    for row in new_rows:
        plan_data = db.rows_to_dicts([row])[0]
        new_subscribers += plan_data["count"]

    # Get churned subscriptions in period
    churn_rows = db.query(
        """SELECT plan_id, COUNT(*) as count
           FROM user_subscriptions
           WHERE status = 'canceled' AND updated_at >= ? AND updated_at < ?
           GROUP BY plan_id""",
        (period_start, period_end)
    )

    churned_subscribers = 0
    for row in churn_rows:
        plan_data = db.rows_to_dicts([row])[0]
        churned_subscribers += plan_data["count"]

    return {
        "period": period,
        "period_start": period_start,
        "period_end": period_end,
        "mrr": total_mrr,
        "arr": total_mrr * 12,
        "total_subscribers": total_subscribers,
        "new_subscribers": new_subscribers,
        "churned_subscribers": churned_subscribers,
        "plan_revenue": plan_revenue,
        "arpu": total_mrr / total_subscribers if total_subscribers > 0 else 0,
        "churn_rate": churned_subscribers / total_subscribers if total_subscribers > 0 else 0
    }


def record_revenue_attribution(
    period: str,
    period_start: str,
    period_end: str,
    scope: str,
    revenue_source: str,
    gross_revenue: float,
    net_revenue: Optional[float] = None,
    refunds: float = 0,
    discounts: float = 0,
    tax_amount: float = 0,
    plan_id: Optional[str] = None,
    feature_key: Optional[str] = None,
    customer_count: int = 0,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Record revenue attribution data."""
    if net_revenue is None:
        net_revenue = gross_revenue - refunds - discounts

    if metadata is None:
        metadata = {}

    now = db.utc_now()

    db.execute(
        """INSERT INTO revenue_attribution
           (period, period_start, period_end, scope, revenue_source, feature_key,
            gross_revenue, net_revenue, refunds, discounts, tax_amount,
            plan_id, customer_count, metadata, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (period, period_start, period_end, scope, revenue_source, feature_key,
         gross_revenue, net_revenue, refunds, discounts, tax_amount,
         plan_id, customer_count, json.dumps(metadata), now, now)
    )

    return db.rows_to_dicts([db.query(
        """SELECT * FROM revenue_attribution
           WHERE period = ? AND period_start = ? AND scope = ? AND revenue_source = ?
           ORDER BY id DESC LIMIT 1""",
        (period, period_start, scope, revenue_source)
    )[0]])[0]


def get_revenue_attribution(
    period: str,
    scope: Optional[str] = None,
    revenue_source: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Get revenue attribution data."""
    query = "SELECT * FROM revenue_attribution WHERE period = ?"
    params = [period]

    if scope:
        query += " AND scope = ?"
        params.append(scope)
    if revenue_source:
        query += " AND revenue_source = ?"
        params.append(revenue_source)

    query += " ORDER BY period_start DESC"

    rows = db.query(query, tuple(params))
    attribution = [db.rows_to_dicts([row])[0] for row in rows]

    # Parse JSON fields
    for attr in attribution:
        if attr.get("metadata"):
            attr["metadata"] = json.loads(attr["metadata"])

    return attribution


def record_commercial_metric(
    metric_name: str,
    metric_value: float,
    metric_type: str = "gauge",
    labels: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Record a commercial metric for analytics."""
    if labels is None:
        labels = {}
    if metadata is None:
        metadata = {}

    now = db.utc_now()

    db.execute(
        """INSERT INTO commercial_metrics
           (metric_name, metric_value, metric_type, labels, timestamp, metadata, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (metric_name, metric_value, metric_type, json.dumps(labels),
         now, json.dumps(metadata), now)
    )


def get_commercial_metrics(
    metric_name: Optional[str] = None,
    since: Optional[str] = None,
    limit: int = 1000,
) -> List[Dict[str, Any]]:
    """Get commercial metrics."""
    query = "SELECT * FROM commercial_metrics WHERE 1=1"
    params = []

    if metric_name:
        query += " AND metric_name = ?"
        params.append(metric_name)
    if since:
        query += " AND timestamp >= ?"
        params.append(since)

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    rows = db.query(query, tuple(params))
    metrics = [db.rows_to_dicts([row])[0] for row in rows]

    # Parse JSON fields
    for metric in metrics:
        if metric.get("labels"):
            metric["labels"] = json.loads(metric["labels"])
        if metric.get("metadata"):
            metric["metadata"] = json.loads(metric["metadata"])

    return metrics


# ---------------------------------------------------------------------------
# Stripe Integration Helpers
# ---------------------------------------------------------------------------

def get_subscription_by_stripe_id(stripe_subscription_id: str) -> Optional[Dict[str, Any]]:
    """Get subscription by Stripe subscription ID."""
    rows = db.query(
        "SELECT * FROM user_subscriptions WHERE stripe_subscription_id = ?",
        (stripe_subscription_id,)
    )
    if not rows:
        return None
    return db.rows_to_dicts([rows[0]])[0]


def get_invoice_by_stripe_id(stripe_invoice_id: str) -> Optional[Dict[str, Any]]:
    """Get invoice by Stripe invoice ID."""
    rows = db.query(
        "SELECT * FROM invoices WHERE stripe_invoice_id = ?",
        (stripe_invoice_id,)
    )
    if not rows:
        return None
    return db.rows_to_dicts([rows[0]])[0]


def update_user_stripe_customer(user_id: int, stripe_customer_id: str) -> None:
    """Update user with Stripe customer ID."""
    db.execute(
        "UPDATE users SET stripe_customer_id = ? WHERE id = ?",
        (stripe_customer_id, user_id)
    )


def resolve_billing_alerts(subscription_id: str, alert_type: str) -> None:
    """Resolve billing alerts for a subscription."""
    db.execute(
        """UPDATE billing_alerts 
           SET resolved = 1, resolved_at = ? 
           WHERE subscription_id = ? AND alert_type = ? AND resolved = 0""",
        (db.utc_now(), subscription_id, alert_type)
    )


def get_feature_gates_by_plan(plan_id: str) -> List[Dict[str, Any]]:
    """Get all feature gates enabled for a specific plan."""
    gates = get_all_feature_gates()
    return [gate for gate in gates if plan_id in gate.get("enabled_plans", [])]


def get_pricing_tiers_for_feature(feature_key: str, plan_id: str) -> List[Dict[str, Any]]:
    """Get pricing tiers for a feature that apply to a specific plan."""
    rows = db.query(
        """SELECT * FROM pricing_tiers 
           WHERE feature_key = ? AND active = 1""",
        (feature_key,)
    )
    tiers = [db.rows_to_dicts([row])[0] for row in rows]
    
    # Filter by plan applicability
    filtered_tiers = []
    for tier in tiers:
        applies_to_plans = json.loads(tier.get("applies_to_plans", "[]"))
        if not applies_to_plans or plan_id in applies_to_plans:
            filtered_tiers.append(tier)
    
    return filtered_tiers


def get_feature_usage(
    user_id: int,
    feature_key: Optional[str] = None,
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Get feature usage for a user."""
    query = "SELECT * FROM feature_usage WHERE user_id = ?"
    params = [user_id]
    
    if feature_key:
        query += " AND feature_key = ?"
        params.append(feature_key)
    
    if period_start:
        query += " AND period_start >= ?"
        params.append(period_start)
    
    if period_end:
        query += " AND period_end <= ?"
        params.append(period_end)
    
    query += " ORDER BY period_start DESC"
    
    rows = db.query(query, tuple(params))
    return [db.rows_to_dicts([row])[0] for row in rows]


def track_feature_usage(
    user_id: int,
    subscription_id: str,
    feature_key: str,
    usage_value: float = 1.0,
    usage_count: int = 1,
) -> Dict[str, Any]:
    """Track feature usage for billing and analytics."""
    # Determine period (current month)
    now = datetime.now(timezone.utc)
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    period_end = (now + timedelta(days=32)).replace(day=1).isoformat()
    
    # Check if usage record exists for this period
    rows = db.query(
        """SELECT * FROM feature_usage 
           WHERE user_id = ? AND subscription_id = ? AND feature_key = ? 
           AND period_start = ? AND period_end = ?""",
        (user_id, subscription_id, feature_key, period_start, period_end)
    )
    
    if rows:
        # Update existing record
        existing = db.rows_to_dicts([rows[0]])[0]
        db.execute(
            """UPDATE feature_usage 
               SET usage_count = usage_count + ?, usage_value = usage_value + ?, updated_at = ?
               WHERE id = ?""",
            (usage_count, usage_value, db.utc_now(), existing["id"])
        )
    else:
        # Create new record
        db.execute(
            """INSERT INTO feature_usage 
               (user_id, subscription_id, feature_key, usage_count, usage_value, 
                period_start, period_end, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, subscription_id, feature_key, usage_count, usage_value,
             period_start, period_end, db.utc_now(), db.utc_now())
        )
    
    return {"user_id": user_id, "feature_key": feature_key, "usage_value": usage_value}


def create_usage_quota(
    subscription_id: str,
    feature_key: str,
    quota_limit: int,
    warning_threshold: float = 0.8,
) -> Dict[str, Any]:
    """Create a usage quota record."""
    now = datetime.now(timezone.utc)
    # Reset at end of current month
    reset_at = (now + timedelta(days=32)).replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    
    db.execute(
        """INSERT INTO usage_quotas 
           (subscription_id, feature_key, quota_limit, quota_used, quota_reset_at, 
            warning_threshold, alert_sent, created_at, updated_at)
           VALUES (?, ?, ?, 0, ?, ?, 0, ?, ?)""",
        (subscription_id, feature_key, quota_limit, reset_at, warning_threshold, db.utc_now(), db.utc_now())
    )
    
    return get_usage_quota(subscription_id, feature_key)


def get_usage_quota(subscription_id: str, feature_key: str) -> Optional[Dict[str, Any]]:
    """Get usage quota for a subscription and feature."""
    rows = db.query(
        """SELECT * FROM usage_quotas 
           WHERE subscription_id = ? AND feature_key = ?""",
        (subscription_id, feature_key)
    )
    if not rows:
        return None
    return db.rows_to_dicts([rows[0]])[0]


def reset_usage_quota(quota_id: int) -> None:
    """Reset a usage quota."""
    now = datetime.now(timezone.utc)
    reset_at = (now + timedelta(days=32)).replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    
    db.execute(
        """UPDATE usage_quotas 
           SET quota_used = 0, quota_reset_at = ?, alert_sent = 0, updated_at = ?
           WHERE id = ?""",
        (reset_at, db.utc_now(), quota_id)
    )


def increment_usage_quota(subscription_id: str, feature_key: str, units: int = 1) -> None:
    """Increment usage quota."""
    db.execute(
        """UPDATE usage_quotas 
           SET quota_used = quota_used + ?, updated_at = ?
           WHERE subscription_id = ? AND feature_key = ?""",
        (units, db.utc_now(), subscription_id, feature_key)
    )


def send_quota_warning_alert(user_id: int, subscription_id: str, feature_key: str, available: int, limit: int) -> None:
    """Send quota warning alert."""
    feature_gate = get_feature_gate(feature_key)
    feature_name = feature_gate.get("feature_name", feature_key) if feature_gate else feature_key
    
    db.execute(
        """INSERT INTO billing_alerts 
           (user_id, subscription_id, alert_type, alert_level, message, resolved, created_at)
           VALUES (?, ?, 'quota_warning', 'warning', ?, 0, ?)""",
        (user_id, subscription_id, 
         f"Quota warning for {feature_name}: {available} remaining of {limit}",
         db.utc_now())
    )
    
    # Mark alert as sent
    db.execute(
        """UPDATE usage_quotas 
           SET alert_sent = 1 
           WHERE subscription_id = ? AND feature_key = ?""",
        (subscription_id, feature_key)
    )


def get_usage_quotas_by_subscription(subscription_id: str) -> List[Dict[str, Any]]:
    """Get all usage quotas for a subscription."""
    rows = db.query(
        "SELECT * FROM usage_quotas WHERE subscription_id = ?",
        (subscription_id,)
    )
    return [db.rows_to_dicts([row])[0] for row in rows]


def get_api_usage_logs(
    user_id: int,
    since: Optional[str] = None,
    limit: int = 1000,
) -> List[Dict[str, Any]]:
    """Get API usage logs for a user."""
    query = "SELECT * FROM api_usage_logs WHERE user_id = ?"
    params = [user_id]
    
    if since:
        query += " AND timestamp >= ?"
        params.append(since)
    
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    
    rows = db.query(query, tuple(params))
    return [db.rows_to_dicts([row])[0] for row in rows]


def create_billing_alert(
    user_id: int,
    subscription_id: str,
    alert_type: str,
    alert_level: str,
    message: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a billing alert."""
    if metadata is None:
        metadata = {}
    
    db.execute(
        """INSERT INTO billing_alerts 
           (user_id, subscription_id, alert_type, alert_level, message, 
            resolved, metadata, created_at)
           VALUES (?, ?, ?, ?, ?, 0, ?, ?)""",
        (user_id, subscription_id, alert_type, alert_level, message,
         json.dumps(metadata), db.utc_now())
    )
    
    return {"user_id": user_id, "alert_type": alert_type, "message": message}


def get_billing_alerts(
    user_id: Optional[int] = None,
    subscription_id: Optional[str] = None,
    alert_type: Optional[str] = None,
    resolved: Optional[bool] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Get billing alerts with optional filters."""
    query = "SELECT * FROM billing_alerts WHERE 1=1"
    params = []
    
    if user_id:
        query += " AND user_id = ?"
        params.append(user_id)
    
    if subscription_id:
        query += " AND subscription_id = ?"
        params.append(subscription_id)
    
    if alert_type:
        query += " AND alert_type = ?"
        params.append(alert_type)
    
    if resolved is not None:
        query += " AND resolved = ?"
        params.append(1 if resolved else 0)
    
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    
    rows = db.query(query, tuple(params))
    return [db.rows_to_dicts([row])[0] for row in rows]