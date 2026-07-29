"""Feature flag service for scope-based feature access control.

This module provides a clean interface for:
- Checking feature access based on user scope and subscription
- Feature gate management
- Usage quota enforcement
- Feature access caching
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set
from functools import lru_cache
from threading import Lock

from . import db, commercial_service as cs

logger = logging.getLogger("momento.feature_flags")

# Cache for feature access checks (5-minute TTL)
_ACCESS_CACHE: Dict[str, Dict[str, Any]] = {}
_CACHE_LOCK = Lock()
_CACHE_TTL = 300  # 5 minutes


class FeatureAccessResult:
    """Result of a feature access check."""

    def __init__(
        self,
        has_access: bool,
        reason: str,
        feature_key: str,
        user_id: int,
        scope: Optional[str] = None,
        plan_id: Optional[str] = None,
        gate: Optional[Dict[str, Any]] = None,
        quota_info: Optional[Dict[str, Any]] = None,
    ):
        self.has_access = has_access
        self.reason = reason
        self.feature_key = feature_key
        self.user_id = user_id
        self.scope = scope
        self.plan_id = plan_id
        self.gate = gate
        self.quota_info = quota_info

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "has_access": self.has_access,
            "reason": self.reason,
            "feature_key": self.feature_key,
            "user_id": self.user_id,
            "scope": self.scope,
            "plan_id": self.plan_id,
            "gate": self.gate,
            "quota_info": self.quota_info,
        }


def _get_cache_key(user_id: int, feature_key: str, scope: Optional[str] = None) -> str:
    """Generate cache key for feature access check."""
    return f"{user_id}:{feature_key}:{scope or 'default'}"


def _is_cache_valid(entry: Dict[str, Any]) -> bool:
    """Check if cache entry is still valid."""
    cached_at = entry.get("cached_at")
    if not cached_at:
        return False

    try:
        cached_time = datetime.fromisoformat(cached_at)
        return (datetime.now(timezone.utc) - cached_time).total_seconds() < _CACHE_TTL
    except Exception:
        return False


def _clear_cache():
    """Clear expired cache entries."""
    global _ACCESS_CACHE

    with _CACHE_LOCK:
        expired_keys = [
            key for key, entry in _ACCESS_CACHE.items()
            if not _is_cache_valid(entry)
        ]
        for key in expired_keys:
            del _ACCESS_CACHE[key]


def _get_from_cache(cache_key: str) -> Optional[Dict[str, Any]]:
    """Get feature access result from cache."""
    with _CACHE_LOCK:
        entry = _ACCESS_CACHE.get(cache_key)
        if entry and _is_cache_valid(entry):
            return entry
        return None


def _set_in_cache(cache_key: str, result: Dict[str, Any]):
    """Set feature access result in cache."""
    with _CACHE_LOCK:
        result["cached_at"] = datetime.now(timezone.utc).isoformat()
        _ACCESS_CACHE[cache_key] = result


def check_feature_access(
    user_id: int,
    feature_key: str,
    scope: Optional[str] = None,
    use_cache: bool = True,
    check_quota: bool = False,
) -> FeatureAccessResult:
    """Check if a user has access to a feature.

    Args:
        user_id: User ID
        feature_key: Feature key (e.g., "predictions.enhanced")
        scope: User scope (optional, will be determined from subscription if not provided)
        use_cache: Whether to use cached results
        check_quota: Whether to check usage quotas

    Returns:
        FeatureAccessResult with access status and details
    """
    # Check cache first
    cache_key = _get_cache_key(user_id, feature_key, scope)
    if use_cache:
        cached = _get_from_cache(cache_key)
        if cached:
            return FeatureAccessResult(**cached)

    # Clear expired cache entries periodically
    if len(_ACCESS_CACHE) > 1000:
        _clear_cache()

    # Get feature gate
    gate = cs.get_feature_gate(feature_key)
    if not gate:
        result = FeatureAccessResult(
            has_access=False,
            reason="Feature not found",
            feature_key=feature_key,
            user_id=user_id,
            scope=scope,
        )
        if use_cache:
            _set_in_cache(cache_key, result.to_dict())
        return result

    # Get user's subscription
    subscription = cs.get_user_subscription(user_id)
    if not subscription:
        # Check if feature is available to public scope
        enabled_plans = gate.get("enabled_plans", [])
        if "plan_public_scope" in enabled_plans:
            result = FeatureAccessResult(
                has_access=True,
                reason="Public access",
                feature_key=feature_key,
                user_id=user_id,
                scope="public_scope",
                plan_id="plan_public_scope",
                gate=gate,
            )
            if use_cache:
                _set_in_cache(cache_key, result.to_dict())
            return result

        result = FeatureAccessResult(
            has_access=False,
            reason="No subscription",
            feature_key=feature_key,
            user_id=user_id,
            scope=scope,
        )
        if use_cache:
            _set_in_cache(cache_key, result.to_dict())
        return result

    plan_id = subscription.get("plan_id")
    user_scope = scope or subscription.get("scope")

    # Check if plan has access
    enabled_plans = gate.get("enabled_plans", [])
    if plan_id not in enabled_plans:
        result = FeatureAccessResult(
            has_access=False,
            reason="Plan does not include feature",
            feature_key=feature_key,
            user_id=user_id,
            scope=user_scope,
            plan_id=plan_id,
            gate=gate,
        )
        if use_cache:
            _set_in_cache(cache_key, result.to_dict())
        return result

    # Check if scope has access
    enabled_scopes = gate.get("enabled_scopes", [])
    if user_scope and user_scope not in enabled_scopes:
        result = FeatureAccessResult(
            has_access=False,
            reason="Scope does not include feature",
            feature_key=feature_key,
            user_id=user_id,
            scope=user_scope,
            plan_id=plan_id,
            gate=gate,
        )
        if use_cache:
            _set_in_cache(cache_key, result.to_dict())
        return result

    # Check quota if requested
    quota_info = None
    if check_quota and subscription:
        quota_result = cs.check_quota_and_increment(
            subscription["id"],
            feature_key,
            increment=1,
        )
        quota_info = quota_result
        if not quota_result.get("allowed"):
            result = FeatureAccessResult(
                has_access=False,
                reason="Quota exceeded",
                feature_key=feature_key,
                user_id=user_id,
                scope=user_scope,
                plan_id=plan_id,
                gate=gate,
                quota_info=quota_info,
            )
            if use_cache:
                _set_in_cache(cache_key, result.to_dict())
            return result

    result = FeatureAccessResult(
        has_access=True,
        reason="Access granted",
        feature_key=feature_key,
        user_id=user_id,
        scope=user_scope,
        plan_id=plan_id,
        gate=gate,
        quota_info=quota_info,
    )
    if use_cache:
        _set_in_cache(cache_key, result.to_dict())
    return result


def get_user_features(
    user_id: int,
    scope: Optional[str] = None,
    category: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Get all features accessible to a user.

    Args:
        user_id: User ID
        scope: User scope (optional)
        category: Filter by feature category (optional)

    Returns:
        List of accessible feature gates
    """
    # Get all feature gates
    gates = cs.get_all_feature_gates(category=category, is_public=True)

    # Filter by user access
    accessible = []
    for gate in gates:
        result = check_feature_access(user_id, gate["feature_key"], scope, use_cache=True)
        if result.has_access:
            accessible.append(gate)

    return accessible


def get_scope_features(scope: str) -> List[Dict[str, Any]]:
    """Get all features available to a scope.

    Args:
        scope: Scope identifier (e.g., "fx_scope", "big_better_scope")

    Returns:
        List of feature gates available to the scope
    """
    gates = cs.get_all_feature_gates(is_public=True)

    # Filter by scope
    accessible = []
    for gate in gates:
        enabled_scopes = gate.get("enabled_scopes", [])
        if scope in enabled_scopes:
            accessible.append(gate)

    return accessible


def get_plan_features(plan_id: str) -> List[Dict[str, Any]]:
    """Get all features available to a subscription plan.

    Args:
        plan_id: Plan identifier (e.g., "plan_fx_scope")

    Returns:
        List of feature gates available to the plan
    """
    gates = cs.get_all_feature_gates(is_public=True)

    # Filter by plan
    accessible = []
    for gate in gates:
        enabled_plans = gate.get("enabled_plans", [])
        if plan_id in enabled_plans:
            accessible.append(gate)

    return accessible


def require_feature_access(
    user_id: int,
    feature_key: str,
    scope: Optional[str] = None,
    check_quota: bool = False,
) -> None:
    """Require feature access, raise exception if not available.

    Args:
        user_id: User ID
        feature_key: Feature key
        scope: User scope (optional)
        check_quota: Whether to check usage quotas

    Raises:
        PermissionError: If user does not have access
    """
    result = check_feature_access(user_id, feature_key, scope, check_quota=check_quota)

    if not result.has_access:
        raise PermissionError(
            f"Feature access denied: {feature_key} - {result.reason}"
        )


def track_feature_usage(
    user_id: int,
    feature_key: str,
    usage_value: float = 1.0,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Track usage for a feature.

    Args:
        user_id: User ID
        feature_key: Feature key
        usage_value: Usage value to track
        metadata: Optional metadata

    Returns:
        Updated usage record
    """
    return cs.track_feature_usage(user_id, feature_key, usage_value, metadata=metadata)


def get_feature_usage(
    user_id: int,
    feature_key: str,
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Get usage for a feature.

    Args:
        user_id: User ID
        feature_key: Feature key
        period_start: Period start ISO string (optional)
        period_end: Period end ISO string (optional)

    Returns:
        Usage record or None
    """
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
        return None

    return db.rows_to_dicts([rows[0]])[0]


def calculate_feature_cost(
    user_id: int,
    feature_key: str,
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
) -> Dict[str, Any]:
    """Calculate cost for feature usage.

    Args:
        user_id: User ID
        feature_key: Feature key
        period_start: Period start ISO string (optional)
        period_end: Period end ISO string (optional)

    Returns:
        Cost calculation with breakdown
    """
    return cs.calculate_usage_cost(user_id, feature_key, period_start, period_end)


def invalidate_user_cache(user_id: int):
    """Invalidate cache entries for a user.

    Args:
        user_id: User ID
    """
    global _ACCESS_CACHE

    with _CACHE_LOCK:
        keys_to_remove = [
            key for key in _ACCESS_CACHE.keys()
            if key.startswith(f"{user_id}:")
        ]
        for key in keys_to_remove:
            del _ACCESS_CACHE[key]

    logger.debug(f"Invalidated cache for user {user_id}")


def invalidate_feature_cache(feature_key: str):
    """Invalidate cache entries for a feature.

    Args:
        feature_key: Feature key
    """
    global _ACCESS_CACHE

    with _CACHE_LOCK:
        keys_to_remove = [
            key for key in _ACCESS_CACHE.keys()
            if f":{feature_key}:" in key
        ]
        for key in keys_to_remove:
            del _ACCESS_CACHE[key]

    logger.debug(f"Invalidated cache for feature {feature_key}")


def clear_all_cache():
    """Clear all feature access cache."""
    global _ACCESS_CACHE

    with _CACHE_LOCK:
        _ACCESS_CACHE.clear()

    logger.debug("Cleared all feature access cache")
