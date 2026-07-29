"""Usage-based pricing calculation service for V5 commercial features.

This service provides:
- Usage-based pricing calculations
- Tiered pricing model support
- Hybrid pricing (subscription + usage)
- Cost estimation and forecasting
- Quota management and enforcement
- Usage aggregation and reporting
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from . import db, commercial_service as cs

logger = logging.getLogger("momento.pricing_service")


# ---------------------------------------------------------------------------
# Enums and Constants
# ---------------------------------------------------------------------------

class PricingModel(str, Enum):
    """Pricing model types."""
    SUBSCRIPTION = "subscription"
    USAGE_BASED = "usage_based"
    HYBRID = "hybrid"


class FeatureCategory(str, Enum):
    """Feature categories for pricing."""
    PREDICTION = "prediction"
    ANALYSIS = "analysis"
    TRADING = "trading"
    API = "api"
    UI = "ui"
    STORAGE = "storage"


# ---------------------------------------------------------------------------
# Usage-Based Pricing Calculations
# ---------------------------------------------------------------------------

def calculate_usage_cost(
    feature_key: str,
    usage_amount: float,
    plan_id: str,
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
) -> Dict[str, Any]:
    """Calculate cost for usage-based feature."""
    # Get feature gate
    feature_gate = cs.get_feature_gate(feature_key)
    if not feature_gate:
        raise ValueError(f"Feature gate {feature_key} not found")
    
    if feature_gate["pricing_model"] != PricingModel.USAGE_BASED:
        raise ValueError(f"Feature {feature_key} is not usage-based")
    
    # Get pricing tiers
    tiers = cs.get_pricing_tiers_for_feature(feature_key, plan_id)
    if not tiers:
        raise ValueError(f"No pricing tiers found for feature {feature_key} and plan {plan_id}")
    
    # Determine applicable tier
    applicable_tier = None
    for tier in sorted(tiers, key=lambda x: x["min_units"]):
        max_units = tier.get("max_units", float("inf"))
        if tier["min_units"] <= usage_amount <= max_units:
            applicable_tier = tier
            break
    
    if not applicable_tier:
        # If usage exceeds all tiers, use the highest tier
        applicable_tier = max(tiers, key=lambda x: x["min_units"])
    
    # Calculate cost
    base_price = feature_gate.get("base_price", 0)
    included_units = feature_gate.get("included_units", 0)
    unit_price = applicable_tier["price_per_unit"]
    
    # Calculate billable units
    billable_units = max(0, usage_amount - included_units)
    
    # Calculate total cost
    usage_cost = base_price + (billable_units * unit_price)
    
    return {
        "feature_key": feature_key,
        "usage_amount": usage_amount,
        "included_units": included_units,
        "billable_units": billable_units,
        "unit_price": unit_price,
        "base_price": base_price,
        "total_cost": usage_cost,
        "applicable_tier": applicable_tier["tier_name"],
        "currency": applicable_tier["currency"]
    }


def calculate_monthly_usage_cost(
    user_id: int,
    subscription_id: str,
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
) -> Dict[str, Any]:
    """Calculate total monthly usage cost for a subscription."""
    if period_start is None:
        period_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    if period_end is None:
        period_end = (datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0) + 
                      timedelta(days=32)).replace(day=1).isoformat()
    
    # Get subscription
    subscription = cs.get_subscription_by_id(subscription_id)
    if not subscription:
        raise ValueError(f"Subscription {subscription_id} not found")
    
    plan_id = subscription["plan_id"]
    
    # Get all usage-based features for the plan
    feature_gates = cs.get_feature_gates_by_plan(plan_id)
    usage_based_features = [fg for fg in feature_gates if fg["pricing_model"] == PricingModel.USAGE_BASED]
    
    total_cost = 0
    feature_costs = []
    
    for feature_gate in usage_based_features:
        feature_key = feature_gate["feature_key"]
        
        # Get usage for this feature
        usage = cs.get_feature_usage(
            user_id=user_id,
            feature_key=feature_key,
            period_start=period_start,
            period_end=period_end
        )
        
        if usage:
            usage_amount = sum(u["usage_value"] for u in usage)
            
            # Calculate cost
            cost_breakdown = calculate_usage_cost(
                feature_key=feature_key,
                usage_amount=usage_amount,
                plan_id=plan_id,
                period_start=period_start,
                period_end=period_end
            )
            
            feature_costs.append(cost_breakdown)
            total_cost += cost_breakdown["total_cost"]
    
    return {
        "subscription_id": subscription_id,
        "period_start": period_start,
        "period_end": period_end,
        "total_cost": total_cost,
        "feature_costs": feature_costs,
        "currency": "USD"
    }


def estimate_cost(
    feature_key: str,
    estimated_usage: float,
    plan_id: str,
) -> Dict[str, Any]:
    """Estimate cost for estimated usage."""
    return calculate_usage_cost(
        feature_key=feature_key,
        usage_amount=estimated_usage,
        plan_id=plan_id
    )


def get_pricing_summary(
    plan_id: str,
) -> Dict[str, Any]:
    """Get pricing summary for a plan."""
    plan = cs.get_subscription_plan(plan_id)
    if not plan:
        raise ValueError(f"Plan {plan_id} not found")
    
    # Get all feature gates for the plan
    feature_gates = cs.get_feature_gates_by_plan(plan_id)
    
    subscription_features = []
    usage_based_features = []
    
    for feature_gate in feature_gates:
        if feature_gate["pricing_model"] == PricingModel.SUBSCRIPTION:
            subscription_features.append({
                "feature_key": feature_gate["feature_key"],
                "feature_name": feature_gate["feature_name"],
                "description": feature_gate["description"],
                "category": feature_gate["category"]
            })
        elif feature_gate["pricing_model"] == PricingModel.USAGE_BASED:
            # Get pricing tiers
            tiers = cs.get_pricing_tiers_for_feature(feature_gate["feature_key"], plan_id)
            
            usage_based_features.append({
                "feature_key": feature_gate["feature_key"],
                "feature_name": feature_gate["feature_name"],
                "description": feature_gate["description"],
                "category": feature_gate["category"],
                "base_price": feature_gate.get("base_price", 0),
                "included_units": feature_gate.get("included_units", 0),
                "unit_price": feature_gate.get("unit_price", 0),
                "unit_name": feature_gate.get("unit_name", "unit"),
                "pricing_tiers": tiers
            })
    
    return {
        "plan_id": plan_id,
        "plan_name": plan["name"],
        "monthly_price": plan["price_monthly"],
        "yearly_price": plan["price_yearly"],
        "currency": plan["currency"],
        "subscription_features": subscription_features,
        "usage_based_features": usage_based_features
    }


# ---------------------------------------------------------------------------
# Quota Management
# ---------------------------------------------------------------------------

def check_quota(
    user_id: int,
    subscription_id: str,
    feature_key: str,
    requested_units: int = 1,
) -> Dict[str, Any]:
    """Check if user has quota available for a feature."""
    # Get feature gate
    feature_gate = cs.get_feature_gate(feature_key)
    if not feature_gate:
        raise ValueError(f"Feature gate {feature_key} not found")
    
    # Get subscription
    subscription = cs.get_subscription_by_id(subscription_id)
    if not subscription:
        raise ValueError(f"Subscription {subscription_id} not found")
    
    plan = cs.get_subscription_plan(subscription["plan_id"])
    if not plan:
        raise ValueError(f"Plan {subscription['plan_id']} not found")
    
    # Get or create quota record
    quota = cs.get_usage_quota(subscription_id, feature_key)
    
    if not quota:
        # Determine quota limit from plan
        # For now, use a default based on plan's rate_limit
        quota_limit = plan.get("rate_limit", 1000)
        
        # Create quota record
        quota = cs.create_usage_quota(
            subscription_id=subscription_id,
            feature_key=feature_key,
            quota_limit=quota_limit
        )
    
    # Check if quota has been reset
    quota_reset_at = quota.get("quota_reset_at")
    now = datetime.now(timezone.utc)
    
    if quota_reset_at:
        reset_time = datetime.fromisoformat(quota_reset_at)
        if now > reset_time:
            # Reset quota
            cs.reset_usage_quota(quota["id"])
            quota = cs.get_usage_quota(subscription_id, feature_key)
    
    # Check if requested units available
    quota_used = quota.get("quota_used", 0)
    quota_limit = quota.get("quota_limit", 0)
    available = quota_limit - quota_used
    
    has_quota = available >= requested_units
    warning_threshold = quota.get("warning_threshold", 0.8)
    should_warn = (available / quota_limit) < warning_threshold if quota_limit > 0 else False
    
    # Send warning alert if needed
    if should_warn and not quota.get("alert_sent", 0):
        cs.send_quota_warning_alert(user_id, subscription_id, feature_key, available, quota_limit)
    
    return {
        "has_quota": has_quota,
        "available": available,
        "requested": requested_units,
        "quota_used": quota_used,
        "quota_limit": quota_limit,
        "should_warn": should_warn
    }


def consume_quota(
    user_id: int,
    subscription_id: str,
    feature_key: str,
    units: int = 1,
) -> Dict[str, Any]:
    """Consume quota for a feature."""
    # Check quota first
    quota_check = check_quota(user_id, subscription_id, feature_key, units)
    
    if not quota_check["has_quota"]:
        raise ValueError(f"Insufficient quota for feature {feature_key}")
    
    # Consume quota
    cs.increment_usage_quota(subscription_id, feature_key, units)
    
    # Track usage
    cs.track_feature_usage(
        user_id=user_id,
        subscription_id=subscription_id,
        feature_key=feature_key,
        usage_value=units
    )
    
    return {
        "consumed": units,
        "remaining": quota_check["available"] - units
    }


def get_quota_status(
    subscription_id: str,
) -> List[Dict[str, Any]]:
    """Get quota status for all features in a subscription."""
    quotas = cs.get_usage_quotas_by_subscription(subscription_id)
    
    status_list = []
    for quota in quotas:
        feature_gate = cs.get_feature_gate(quota["feature_key"])
        if feature_gate:
            quota_used = quota.get("quota_used", 0)
            quota_limit = quota.get("quota_limit", 0)
            percentage = (quota_used / quota_limit * 100) if quota_limit > 0 else 0
            
            status_list.append({
                "feature_key": quota["feature_key"],
                "feature_name": feature_gate.get("feature_name", quota["feature_key"]),
                "quota_used": quota_used,
                "quota_limit": quota_limit,
                "percentage": percentage,
                "available": quota_limit - quota_used,
                "reset_at": quota.get("quota_reset_at")
            })
    
    return status_list


# ---------------------------------------------------------------------------
# Usage Aggregation and Reporting
# ---------------------------------------------------------------------------

def aggregate_usage_by_scope(
    period_start: str,
    period_end: str,
    metric_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Aggregate usage by scope."""
    query = """
        SELECT 
            s.scope,
            ut.metric_type,
            SUM(ut.metric_value) as total_usage,
            COUNT(DISTINCT ut.user_id) as unique_users
        FROM usage_tracking ut
        JOIN user_subscriptions us ON ut.subscription_id = us.id
        JOIN subscription_plans s ON us.plan_id = s.id
        WHERE ut.period_start >= ? AND ut.period_end <= ?
    """
    params = [period_start, period_end]
    
    if metric_type:
        query += " AND ut.metric_type = ?"
        params.append(metric_type)
    
    query += " GROUP BY s.scope, ut.metric_type"
    
    rows = db.query(query, tuple(params))
    
    scope_usage = {}
    for row in rows:
        row_dict = db.rows_to_dicts([row])[0]
        scope = row_dict["scope"]
        
        if scope not in scope_usage:
            scope_usage[scope] = {
                "scope": scope,
                "metrics": []
            }
        
        scope_usage[scope]["metrics"].append({
            "metric_type": row_dict["metric_type"],
            "total_usage": row_dict["total_usage"],
            "unique_users": row_dict["unique_users"]
        })
    
    return list(scope_usage.values())


def aggregate_usage_by_feature(
    period_start: str,
    period_end: str,
) -> List[Dict[str, Any]]:
    """Aggregate usage by feature."""
    query = """
        SELECT 
            fu.feature_key,
            fg.feature_name,
            fg.category,
            SUM(fu.usage_value) as total_usage,
            SUM(fu.usage_count) as total_count,
            COUNT(DISTINCT fu.user_id) as unique_users,
            AVG(fu.usage_value) as avg_usage
        FROM feature_usage fu
        JOIN feature_gates fg ON fu.feature_key = fg.feature_key
        WHERE fu.period_start >= ? AND fu.period_end <= ?
        GROUP BY fu.feature_key
        ORDER BY total_usage DESC
    """
    
    rows = db.query(query, (period_start, period_end))
    return [db.rows_to_dicts([row])[0] for row in rows]


def get_usage_analytics(
    user_id: int,
    subscription_id: str,
    days: int = 30,
) -> Dict[str, Any]:
    """Get usage analytics for a user."""
    period_start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    period_end = datetime.now(timezone.utc).isoformat()
    
    # Get subscription
    subscription = cs.get_subscription_by_id(subscription_id)
    plan = cs.get_subscription_plan(subscription["plan_id"]) if subscription else None
    
    # Get feature usage
    feature_usage = cs.get_feature_usage(
        user_id=user_id,
        period_start=period_start,
        period_end=period_end
    )
    
    # Get API usage
    api_usage = cs.get_api_usage_logs(
        user_id=user_id,
        since=period_start
    )
    
    # Calculate totals
    total_predictions = 0
    total_api_calls = len(api_usage)
    total_storage = 0
    
    for usage in feature_usage:
        if "predictions" in usage["feature_key"]:
            total_predictions += usage["usage_value"]
        elif "storage" in usage["feature_key"]:
            total_storage += usage["usage_value"]
    
    # Calculate estimated cost
    cost_estimate = calculate_monthly_usage_cost(
        user_id=user_id,
        subscription_id=subscription_id,
        period_start=period_start,
        period_end=period_end
    )
    
    return {
        "user_id": user_id,
        "subscription_id": subscription_id,
        "plan_name": plan["name"] if plan else "Unknown",
        "period_start": period_start,
        "period_end": period_end,
        "total_predictions": total_predictions,
        "total_api_calls": total_api_calls,
        "total_storage_gb": total_storage,
        "estimated_cost": cost_estimate["total_cost"],
        "feature_usage": feature_usage,
        "quota_status": get_quota_status(subscription_id)
    }


# ---------------------------------------------------------------------------
# Hybrid Pricing Calculations
# ---------------------------------------------------------------------------

def calculate_hybrid_cost(
    subscription_id: str,
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
) -> Dict[str, Any]:
    """Calculate total cost for hybrid pricing (subscription + usage)."""
    # Get subscription
    subscription = cs.get_subscription_by_id(subscription_id)
    if not subscription:
        raise ValueError(f"Subscription {subscription_id} not found")
    
    plan = cs.get_subscription_plan(subscription["plan_id"])
    if not plan:
        raise ValueError(f"Plan {subscription['plan_id']} not found")
    
    # Base subscription cost
    base_cost = plan["price_monthly"] if subscription["billing_period"] == "monthly" else plan["price_yearly"] / 12
    
    # Usage-based cost
    user_id = subscription["user_id"]
    usage_cost = calculate_monthly_usage_cost(
        user_id=user_id,
        subscription_id=subscription_id,
        period_start=period_start,
        period_end=period_end
    )
    
    total_cost = base_cost + usage_cost["total_cost"]
    
    return {
        "subscription_id": subscription_id,
        "base_subscription_cost": base_cost,
        "usage_based_cost": usage_cost["total_cost"],
        "total_cost": total_cost,
        "cost_breakdown": {
            "base": base_cost,
            "usage": usage_cost["feature_costs"]
        },
        "currency": "USD"
    }


def get_billing_forecast(
    subscription_id: str,
    months: int = 3,
) -> List[Dict[str, Any]]:
    """Forecast billing for upcoming months."""
    forecasts = []
    
    # Get current usage pattern
    subscription = cs.get_subscription_by_id(subscription_id)
    if not subscription:
        return forecasts
    
    user_id = subscription["user_id"]
    
    # Get usage for last 30 days
    now = datetime.now(timezone.utc)
    period_start = (now - timedelta(days=30)).isoformat()
    period_end = now.isoformat()
    
    current_cost = calculate_monthly_usage_cost(
        user_id=user_id,
        subscription_id=subscription_id,
        period_start=period_start,
        period_end=period_end
    )
    
    # Project for future months (simplified - assumes similar usage)
    for month in range(1, months + 1):
        forecast_date = now + timedelta(days=30 * month)
        forecast_start = forecast_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        forecast_end = (forecast_start + timedelta(days=32)).replace(day=1)
        
        # Apply growth factor (adjust as needed)
        growth_factor = 1.0  # No growth by default
        projected_cost = current_cost["total_cost"] * growth_factor
        
        forecasts.append({
            "month": month,
            "period_start": forecast_start.isoformat(),
            "period_end": forecast_end.isoformat(),
            "projected_cost": projected_cost,
            "currency": "USD"
        })
    
    return forecasts
