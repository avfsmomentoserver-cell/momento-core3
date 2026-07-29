"""Revenue analytics and reporting service for V5 commercial features.

This service provides:
- Revenue tracking and aggregation
- Financial reporting (MRR, ARR, ARPU, LTV, CAC, churn)
- Cohort analysis
- Revenue attribution
- Forecasting and projections
- Commercial metrics dashboard
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import statistics

from . import db, commercial_service as cs

logger = logging.getLogger("momento.revenue_service")


# ---------------------------------------------------------------------------
# Enums and Constants
# ---------------------------------------------------------------------------

class RevenuePeriod(str, Enum):
    """Revenue aggregation periods."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class RevenueSource(str, Enum):
    """Revenue source types."""
    SUBSCRIPTION = "subscription"
    USAGE = "usage"
    ADDON = "addon"
    ENTERPRISE = "enterprise"


# ---------------------------------------------------------------------------
# Revenue Metrics Calculation
# ---------------------------------------------------------------------------

def calculate_mrr(
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
) -> Dict[str, Any]:
    """Calculate Monthly Recurring Revenue (MRR)."""
    if period_start is None:
        period_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    if period_end is None:
        period_end = (datetime.now(timezone.utc) + timedelta(days=32)).replace(day=1).isoformat()
    
    # Get all active subscriptions
    rows = db.query(
        """SELECT us.*, sp.price_monthly, sp.price_yearly, sp.scope
           FROM user_subscriptions us
           JOIN subscription_plans sp ON us.plan_id = sp.id
           WHERE us.status = 'active' 
           AND us.current_period_start >= ? 
           AND us.current_period_end <= ?""",
        (period_start, period_end)
    )
    
    subscriptions = [db.rows_to_dicts([row])[0] for row in rows]
    
    # Calculate MRR by scope
    mrr_by_scope = {}
    total_mrr = 0
    total_subscribers = 0
    
    for sub in subscriptions:
        scope = sub["scope"]
        billing_period = sub["billing_period"]
        
        if billing_period == "monthly":
            monthly_amount = sub["price_monthly"]
        else:
            monthly_amount = sub["price_yearly"] / 12
        
        if scope not in mrr_by_scope:
            mrr_by_scope[scope] = {
                "scope": scope,
                "mrr": 0,
                "subscribers": 0
            }
        
        mrr_by_scope[scope]["mrr"] += monthly_amount
        mrr_by_scope[scope]["subscribers"] += 1
        total_mrr += monthly_amount
        total_subscribers += 1
    
    return {
        "period_start": period_start,
        "period_end": period_end,
        "total_mrr": total_mrr,
        "total_subscribers": total_subscribers,
        "mrr_by_scope": list(mrr_by_scope.values()),
        "arpu": total_mrr / total_subscribers if total_subscribers > 0 else 0
    }


def calculate_arr(
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
) -> Dict[str, Any]:
    """Calculate Annual Recurring Revenue (ARR)."""
    mrr_data = calculate_mrr(period_start, period_end)
    
    total_arr = mrr_data["total_mrr"] * 12
    
    # Calculate ARR by scope
    arr_by_scope = []
    for scope_mrr in mrr_data["mrr_by_scope"]:
        arr_by_scope.append({
            "scope": scope_mrr["scope"],
            "arr": scope_mrr["mrr"] * 12,
            "subscribers": scope_mrr["subscribers"]
        })
    
    return {
        "period_start": mrr_data["period_start"],
        "period_end": mrr_data["period_end"],
        "total_arr": total_arr,
        "arr_by_scope": arr_by_scope,
        "total_subscribers": mrr_data["total_subscribers"]
    }


def calculate_arpu(
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
) -> Dict[str, Any]:
    """Calculate Average Revenue Per User (ARPU)."""
    mrr_data = calculate_mrr(period_start, period_end)
    
    # Calculate ARPU by scope
    arpu_by_scope = []
    for scope_mrr in mrr_data["mrr_by_scope"]:
        arpu_by_scope.append({
            "scope": scope_mrr["scope"],
            "arpu": scope_mrr["mrr"] / scope_mrr["subscribers"] if scope_mrr["subscribers"] > 0 else 0,
            "subscribers": scope_mrr["subscribers"]
        })
    
    return {
        "period_start": mrr_data["period_start"],
        "period_end": mrr_data["period_end"],
        "total_arpu": mrr_data["arpu"],
        "arpu_by_scope": arpu_by_scope
    }


def calculate_churn_rate(
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
) -> Dict[str, Any]:
    """Calculate churn rate for the period."""
    if period_start is None:
        period_start = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    if period_end is None:
        period_end = datetime.now(timezone.utc).isoformat()
    
    # Get subscriptions at start of period
    start_rows = db.query(
        """SELECT COUNT(*) as count FROM user_subscriptions 
           WHERE status = 'active' AND created_at < ?""",
        (period_start,)
    )
    subscribers_at_start = start_rows[0]["count"] if start_rows else 0
    
    # Get churned subscriptions (canceled during period)
    churned_rows = db.query(
        """SELECT COUNT(*) as count FROM user_subscriptions 
           WHERE status = 'canceled' 
           AND updated_at >= ? AND updated_at <= ?""",
        (period_start, period_end)
    )
    churned_count = churned_rows[0]["count"] if churned_rows else 0
    
    # Calculate churn rate
    churn_rate = (churned_count / subscribers_at_start * 100) if subscribers_at_start > 0 else 0
    
    # Calculate churn by scope
    churn_by_scope = []
    scopes = ["my_scope", "admin_scope", "fx_scope", "big_better_scope", "regular_scope", "public_scope"]
    
    for scope in scopes:
        scope_start_rows = db.query(
            """SELECT COUNT(*) as count FROM user_subscriptions us
               JOIN subscription_plans sp ON us.plan_id = sp.id
               WHERE us.status = 'active' AND sp.scope = ? AND us.created_at < ?""",
            (scope, period_start)
        )
        scope_start = scope_start_rows[0]["count"] if scope_start_rows else 0
        
        scope_churned_rows = db.query(
            """SELECT COUNT(*) as count FROM user_subscriptions us
               JOIN subscription_plans sp ON us.plan_id = sp.id
               WHERE us.status = 'canceled' AND sp.scope = ?
               AND us.updated_at >= ? AND us.updated_at <= ?""",
            (scope, period_start, period_end)
        )
        scope_churned = scope_churned_rows[0]["count"] if scope_churned_rows else 0
        
        scope_churn_rate = (scope_churned / scope_start * 100) if scope_start > 0 else 0
        
        churn_by_scope.append({
            "scope": scope,
            "subscribers_at_start": scope_start,
            "churned": scope_churned,
            "churn_rate": scope_churn_rate
        })
    
    return {
        "period_start": period_start,
        "period_end": period_end,
        "subscribers_at_start": subscribers_at_start,
        "churned_count": churned_count,
        "churn_rate": churn_rate,
        "churn_by_scope": churn_by_scope
    }


def calculate_ltv(
    cohort_period: int = 12,  # months to calculate LTV over
) -> Dict[str, Any]:
    """Calculate Customer Lifetime Value (LTV)."""
    # Get average monthly revenue per customer
    mrr_data = calculate_mrr()
    arpu = mrr_data["arpu"]
    
    # Get churn rate
    churn_data = calculate_churn_rate()
    monthly_churn_rate = churn_data["churn_rate"] / 100 if churn_data["churn_rate"] > 0 else 0
    
    # Calculate LTV: ARPU / Churn Rate
    ltv = arpu / monthly_churn_rate if monthly_churn_rate > 0 else arpu * 36  # Default 36 months if no churn
    
    # Calculate LTV by scope
    ltv_by_scope = []
    for scope_churn in churn_data["churn_by_scope"]:
        scope_arpu = next(
            (s["arpu"] for s in mrr_data["mrr_by_scope"] if s["scope"] == scope_churn["scope"]),
            0
        )
        scope_churn_rate = scope_churn["churn_rate"] / 100 if scope_churn["churn_rate"] > 0 else 0
        scope_ltv = scope_arpu / scope_churn_rate if scope_churn_rate > 0 else scope_arpu * 36
        
        ltv_by_scope.append({
            "scope": scope_churn["scope"],
            "ltv": scope_ltv,
            "arpu": scope_arpu,
            "churn_rate": scope_churn["churn_rate"]
        })
    
    return {
        "cohort_period_months": cohort_period,
        "ltv": ltv,
        "arpu": arpu,
        "monthly_churn_rate": monthly_churn_rate,
        "ltv_by_scope": ltv_by_scope
    }


def calculate_cac(
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
) -> Dict[str, Any]:
    """Calculate Customer Acquisition Cost (CAC)."""
    if period_start is None:
        period_start = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    if period_end is None:
        period_end = datetime.now(timezone.utc).isoformat()
    
    # Get new subscribers in period
    new_subscribers_rows = db.query(
        """SELECT COUNT(*) as count FROM user_subscriptions 
           WHERE created_at >= ? AND created_at <= ?""",
        (period_start, period_end)
    )
    new_subscribers = new_subscribers_rows[0]["count"] if new_subscribers_rows else 0
    
    # Get total marketing/sales spend from attribution
    spend_rows = db.query(
        """SELECT SUM(net_revenue) as total_spend FROM revenue_attribution 
           WHERE revenue_source = 'marketing' 
           AND period_start >= ? AND period_end <= ?""",
        (period_start, period_end)
    )
    total_spend = spend_rows[0]["total_spend"] if spend_rows and spend_rows[0]["total_spend"] else 0
    
    # Calculate CAC
    cac = total_spend / new_subscribers if new_subscribers > 0 else 0
    
    return {
        "period_start": period_start,
        "period_end": period_end,
        "new_subscribers": new_subscribers,
        "total_spend": total_spend,
        "cac": cac
    }


def calculate_ltv_cac_ratio() -> Dict[str, Any]:
    """Calculate LTV:CAC ratio."""
    ltv_data = calculate_ltv()
    cac_data = calculate_cac()
    
    ltv = ltv_data["ltv"]
    cac = cac_data["cac"]
    
    ratio = ltv / cac if cac > 0 else 0
    
    # Industry benchmark: 3:1 is healthy
    is_healthy = ratio >= 3
    
    return {
        "ltv": ltv,
        "cac": cac,
        "ratio": ratio,
        "is_healthy": is_healthy,
        "benchmark": "3:1"
    }


# ---------------------------------------------------------------------------
# Cohort Analysis
# ---------------------------------------------------------------------------

def get_cohort_analysis(
    cohort_period: str = "monthly",
    metric: str = "retention",
    periods: int = 12,
) -> List[Dict[str, Any]]:
    """Perform cohort analysis."""
    # Get cohorts by signup period
    query = """
        SELECT 
            DATE(created_at) as cohort_date,
            COUNT(*) as cohort_size
        FROM user_subscriptions
        WHERE status != 'canceled'
        GROUP BY DATE(created_at)
        ORDER BY cohort_date DESC
        LIMIT ?
    """
    
    rows = db.query(query, (periods,))
    cohorts = [db.rows_to_dicts([row])[0] for row in rows]
    
    cohort_data = []
    
    for cohort in cohorts:
        cohort_date = cohort["cohort_date"]
        cohort_size = cohort["cohort_size"]
        
        # Calculate retention for each period after cohort
        retention_data = []
        
        for period_offset in range(periods):
            period_start = datetime.fromisoformat(cohort_date) + timedelta(days=30 * period_offset)
            period_end = period_start + timedelta(days=30)
            
            # Get active subscribers from this cohort
            active_rows = db.query(
                """SELECT COUNT(*) as count FROM user_subscriptions 
                   WHERE DATE(created_at) = ? 
                   AND status = 'active'
                   AND current_period_end >= ?""",
                (cohort_date, period_end.isoformat())
            )
            active_count = active_rows[0]["count"] if active_rows else 0
            
            retention_rate = (active_count / cohort_size * 100) if cohort_size > 0 else 0
            
            retention_data.append({
                "period": period_offset,
                "active_count": active_count,
                "retention_rate": retention_rate
            })
        
        cohort_data.append({
            "cohort_date": cohort_date,
            "cohort_size": cohort_size,
            "retention_data": retention_data
        })
    
    return cohort_data


# ---------------------------------------------------------------------------
# Revenue Attribution
# ---------------------------------------------------------------------------

def get_revenue_attribution_report(
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
    group_by: str = "scope",
) -> Dict[str, Any]:
    """Generate revenue attribution report."""
    if period_start is None:
        period_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    if period_end is None:
        period_end = (datetime.now(timezone.utc) + timedelta(days=32)).replace(day=1).isoformat()
    
    # Get revenue attribution data
    rows = db.query(
        """SELECT * FROM revenue_attribution 
           WHERE period_start >= ? AND period_end <= ?""",
        (period_start, period_end)
    )
    
    attribution_data = [db.rows_to_dicts([row])[0] for row in rows]
    
    # Group by specified dimension
    grouped_data = {}
    total_gross = 0
    total_net = 0
    
    for attr in attribution_data:
        group_key = attr.get(group_by, "unknown")
        
        if group_key not in grouped_data:
            grouped_data[group_key] = {
                group_by: group_key,
                "gross_revenue": 0,
                "net_revenue": 0,
                "refunds": 0,
                "discounts": 0,
                "customer_count": 0,
                "sources": {}
            }
        
        grouped_data[group_key]["gross_revenue"] += attr.get("gross_revenue", 0)
        grouped_data[group_key]["net_revenue"] += attr.get("net_revenue", 0)
        grouped_data[group_key]["refunds"] += attr.get("refunds", 0)
        grouped_data[group_key]["discounts"] += attr.get("discounts", 0)
        grouped_data[group_key]["customer_count"] += attr.get("customer_count", 0)
        
        source = attr.get("revenue_source", "unknown")
        if source not in grouped_data[group_key]["sources"]:
            grouped_data[group_key]["sources"][source] = 0
        grouped_data[group_key]["sources"][source] += attr.get("net_revenue", 0)
        
        total_gross += attr.get("gross_revenue", 0)
        total_net += attr.get("net_revenue", 0)
    
    return {
        "period_start": period_start,
        "period_end": period_end,
        "group_by": group_by,
        "total_gross_revenue": total_gross,
        "total_net_revenue": total_net,
        "grouped_data": list(grouped_data.values())
    }


# ---------------------------------------------------------------------------
# Revenue Forecasting
# ---------------------------------------------------------------------------

def forecast_revenue(
    months: int = 12,
    method: str = "linear",
) -> List[Dict[str, Any]]:
    """Forecast revenue for future months."""
    # Get historical revenue data
    historical_months = min(12, months)  # Use last 12 months for prediction
    
    historical_data = []
    for i in range(historical_months):
        period_start = (datetime.now(timezone.utc) - timedelta(days=30 * (historical_months - i))).replace(day=1).isoformat()
        period_end = (datetime.now(timezone.utc) - timedelta(days=30 * (historical_months - i - 1))).replace(day=1).isoformat()
        
        mrr = calculate_mrr(period_start, period_end)
        historical_data.append({
            "period": i,
            "mrr": mrr["total_mrr"],
            "subscribers": mrr["total_subscribers"]
        })
    
    # Simple linear regression for forecasting
    if len(historical_data) >= 2:
        x_values = [d["period"] for d in historical_data]
        y_values = [d["mrr"] for d in historical_data]
        
        # Calculate trend
        n = len(x_values)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x2 = sum(x ** 2 for x in x_values)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2) if (n * sum_x2 - sum_x ** 2) != 0 else 0
        intercept = (sum_y - slope * sum_x) / n if n > 0 else 0
    else:
        slope = 0
        intercept = historical_data[-1]["mrr"] if historical_data else 0
    
    # Generate forecast
    forecasts = []
    current_mrr = historical_data[-1]["mrr"] if historical_data else 0
    current_subscribers = historical_data[-1]["subscribers"] if historical_data else 0
    
    for month in range(1, months + 1):
        forecast_date = datetime.now(timezone.utc) + timedelta(days=30 * month)
        period_start = forecast_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
        period_end = (forecast_date + timedelta(days=32)).replace(day=1).isoformat()
        
        if method == "linear":
            predicted_mrr = intercept + slope * (historical_months + month)
        else:
            # Simple growth projection (5% monthly growth)
            predicted_mrr = current_mrr * (1.05 ** month)
        
        # Estimate subscriber growth
        predicted_subscribers = int(current_subscribers * (1.02 ** month))
        
        forecasts.append({
            "month": month,
            "period_start": period_start,
            "period_end": period_end,
            "predicted_mrr": predicted_mrr,
            "predicted_subscribers": predicted_subscribers,
            "predicted_arr": predicted_mrr * 12
        })
    
    return forecasts


# ---------------------------------------------------------------------------
# Dashboard Metrics
# ---------------------------------------------------------------------------

def get_revenue_dashboard(
    period: str = "monthly",
) -> Dict[str, Any]:
    """Get comprehensive revenue dashboard metrics."""
    now = datetime.now(timezone.utc)
    
    if period == "monthly":
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
        period_end = (now + timedelta(days=32)).replace(day=1).isoformat()
    elif period == "yearly":
        period_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
        period_end = (now.replace(year=now.year + 1, month=1, day=1)).isoformat()
    else:
        period_start = (now - timedelta(days=7)).isoformat()
        period_end = now.isoformat()
    
    # Calculate all metrics
    mrr = calculate_mrr(period_start, period_end)
    arr = calculate_arr(period_start, period_end)
    arpu = calculate_arpu(period_start, period_end)
    churn = calculate_churn_rate(period_start, period_end)
    ltv = calculate_ltv()
    cac = calculate_cac(period_start, period_end)
    ltv_cac = calculate_ltv_cac_ratio()
    
    # Get revenue attribution
    attribution = get_revenue_attribution_report(period_start, period_end, "scope")
    
    # Get forecasts
    forecasts = forecast_revenue(months=6)
    
    return {
        "period": period,
        "period_start": period_start,
        "period_end": period_end,
        "mrr": mrr,
        "arr": arr,
        "arpu": arpu,
        "churn_rate": churn,
        "ltv": ltv,
        "cac": cac,
        "ltv_cac_ratio": ltv_cac,
        "revenue_attribution": attribution,
        "forecasts": forecasts
    }


def get_scope_revenue_summary(
    scope: str,
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
) -> Dict[str, Any]:
    """Get revenue summary for a specific scope."""
    if period_start is None:
        period_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    if period_end is None:
        period_end = (datetime.now(timezone.utc) + timedelta(days=32)).replace(day=1).isoformat()
    
    # Get subscriptions for scope
    rows = db.query(
        """SELECT us.*, sp.price_monthly, sp.price_yearly 
           FROM user_subscriptions us
           JOIN subscription_plans sp ON us.plan_id = sp.id
           WHERE sp.scope = ? AND us.status = 'active'
           AND us.current_period_start >= ? AND us.current_period_end <= ?""",
        (scope, period_start, period_end)
    )
    
    subscriptions = [db.rows_to_dicts([row])[0] for row in rows]
    
    # Calculate metrics
    total_mrr = 0
    total_subscribers = len(subscriptions)
    
    for sub in subscriptions:
        if sub["billing_period"] == "monthly":
            total_mrr += sub["price_monthly"]
        else:
            total_mrr += sub["price_yearly"] / 12
    
    # Get usage-based revenue (simplified calculation)
    usage_revenue = 0
    for sub in subscriptions:
        # Get feature usage for this subscription
        feature_usage = cs.get_feature_usage(
            user_id=sub["user_id"],
            period_start=period_start,
            period_end=period_end
        )
        
        # Calculate usage revenue (simplified multiplier)
        for usage in feature_usage:
            usage_revenue += usage.get("usage_value", 0) * 0.01
    
    total_revenue = total_mrr + usage_revenue
    
    return {
        "scope": scope,
        "period_start": period_start,
        "period_end": period_end,
        "total_mrr": total_mrr,
        "usage_revenue": usage_revenue,
        "total_revenue": total_revenue,
        "subscribers": total_subscribers,
        "arpu": total_revenue / total_subscribers if total_subscribers > 0 else 0
    }
