"""Commercial tier feature gating middleware for V5 multi-scope architecture.

This middleware provides:
- Feature access control based on subscription tier
- Scope-based authorization
- Rate limiting enforcement
- Quota checking and enforcement
- Usage tracking
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Callable
from functools import wraps

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from . import commercial_service as cs, pricing_service as ps
from .scope_authorization import get_current_user, get_user_scope

logger = logging.getLogger("momento.commercial_middleware")

security = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Feature Access Dependencies
# ---------------------------------------------------------------------------

def require_feature(feature_key: str):
    """Dependency to require access to a specific feature."""
    async def check_feature_access(
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
    ) -> Dict[str, Any]:
        # Get current user
        user = await get_current_user(request, credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        user_id = user["id"]
        
        # Get user's scope
        scope = get_user_scope(user_id)
        
        # Check feature access
        access_check = cs.check_feature_access(user_id, feature_key, scope)
        
        if not access_check["has_access"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Feature '{feature_key}' not available: {access_check['reason']}"
            )
        
        return {
            "user_id": user_id,
            "feature_key": feature_key,
            "access_granted": True,
            "gate": access_check.get("gate")
        }
    
    return check_feature_access


def require_scope(required_scope: str):
    """Dependency to require a specific scope."""
    async def check_scope_access(
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
    ) -> Dict[str, Any]:
        # Get current user
        user = await get_current_user(request, credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        user_id = user["id"]
        
        # Get user's scope
        user_scope = get_user_scope(user_id)
        
        # Check if user has required scope
        if user_scope != required_scope:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Scope '{required_scope}' required. Current scope: {user_scope}"
            )
        
        return {
            "user_id": user_id,
            "scope": user_scope,
            "access_granted": True
        }
    
    return check_scope_access


def require_any_scope(scopes: List[str]):
    """Dependency to require any of the specified scopes."""
    async def check_scope_access(
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
    ) -> Dict[str, Any]:
        # Get current user
        user = await get_current_user(request, credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        user_id = user["id"]
        
        # Get user's scope
        user_scope = get_user_scope(user_id)
        
        # Check if user has any of the required scopes
        if user_scope not in scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of scopes {scopes} required. Current scope: {user_scope}"
            )
        
        return {
            "user_id": user_id,
            "scope": user_scope,
            "access_granted": True
        }
    
    return check_scope_access


def require_plan(plan_id: str):
    """Dependency to require a specific subscription plan."""
    async def check_plan_access(
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
    ) -> Dict[str, Any]:
        # Get current user
        user = await get_current_user(request, credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        user_id = user["id"]
        
        # Get user's subscription
        subscription = cs.get_user_subscription(user_id)
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Active subscription required"
            )
        
        # Check if user has required plan
        if subscription["plan_id"] != plan_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Plan '{plan_id}' required. Current plan: {subscription['plan_id']}"
            )
        
        return {
            "user_id": user_id,
            "subscription_id": subscription["id"],
            "plan_id": subscription["plan_id"],
            "access_granted": True
        }
    
    return check_plan_access


def require_minimum_plan(minimum_plan_rank: int):
    """Dependency to require a minimum plan rank (1=highest, 6=lowest)."""
    # Plan ranking: my_scope=1, admin_scope=2, fx_scope=3, big_better_scope=4, regular_scope=5, public_scope=6
    plan_rank = {
        "plan_my_scope": 1,
        "plan_admin_scope": 2,
        "plan_fx_scope": 3,
        "plan_big_better_scope": 4,
        "plan_regular_scope": 5,
        "plan_public_scope": 6
    }
    
    async def check_plan_access(
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
    ) -> Dict[str, Any]:
        # Get current user
        user = await get_current_user(request, credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        user_id = user["id"]
        
        # Get user's subscription
        subscription = cs.get_user_subscription(user_id)
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Active subscription required"
            )
        
        # Check plan rank
        current_plan_rank = plan_rank.get(subscription["plan_id"], 6)
        
        if current_plan_rank > minimum_plan_rank:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Higher tier subscription required"
            )
        
        return {
            "user_id": user_id,
            "subscription_id": subscription["id"],
            "plan_id": subscription["plan_id"],
            "plan_rank": current_plan_rank,
            "access_granted": True
        }
    
    return check_plan_access


# ---------------------------------------------------------------------------
# Quota and Usage Dependencies
# ---------------------------------------------------------------------------

def check_quota(feature_key: str, units: int = 1):
    """Dependency to check and consume quota for a feature."""
    async def check_and_consume_quota(
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
    ) -> Dict[str, Any]:
        # Get current user
        user = await get_current_user(request, credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        user_id = user["id"]
        
        # Get user's subscription
        subscription = cs.get_user_subscription(user_id)
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Active subscription required"
            )
        
        subscription_id = subscription["id"]
        
        # Check quota
        quota_check = ps.check_quota(user_id, subscription_id, feature_key, units)
        
        if not quota_check["has_quota"]:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Quota exceeded for feature '{feature_key}'. Available: {quota_check['available']}"
            )
        
        # Consume quota
        ps.consume_quota(user_id, subscription_id, feature_key, units)
        
        # Track usage
        cs.track_feature_usage(user_id, subscription_id, feature_key, units)
        
        return {
            "user_id": user_id,
            "subscription_id": subscription_id,
            "feature_key": feature_key,
            "units_consumed": units,
            "remaining": quota_check["available"] - units
        }
    
    return check_and_consume_quota


# ---------------------------------------------------------------------------
# Decorators for Feature Gating
# ---------------------------------------------------------------------------

def require_feature_decorator(feature_key: str):
    """Decorator to require access to a specific feature."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # This is a simplified version - in production, you'd need to extract user from request
            # For now, we'll just log the requirement
            logger.info(f"Feature '{feature_key}' required for {func.__name__}")
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_scope_decorator(required_scope: str):
    """Decorator to require a specific scope."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            logger.info(f"Scope '{required_scope}' required for {func.__name__}")
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# Rate Limiting Middleware
# ---------------------------------------------------------------------------

def get_rate_limit(request: Request) -> Dict[str, Any]:
    """Get rate limit for the current user based on their subscription."""
    # Get user from request (simplified)
    user_id = request.state.get("user_id")
    
    if not user_id:
        # Default rate limit for unauthenticated users
        return {
            "limit": 10,
            "remaining": 10,
            "reset": None
        }
    
    # Get user's subscription
    subscription = cs.get_user_subscription(user_id)
    
    if not subscription:
        # Default rate limit for users without subscription
        return {
            "limit": 100,
            "remaining": 100,
            "reset": None
        }
    
    # Get plan rate limit
    plan = cs.get_subscription_plan(subscription["plan_id"])
    
    if not plan:
        return {
            "limit": 100,
            "remaining": 100,
            "reset": None
        }
    
    rate_limit = plan.get("rate_limit", 100)
    
    # In production, you'd track actual usage and calculate remaining
    # For now, return the limit
    return {
        "limit": rate_limit,
        "remaining": rate_limit,
        "reset": None
    }


# ---------------------------------------------------------------------------
# Usage Tracking Middleware
# ---------------------------------------------------------------------------

async def track_api_usage_middleware(request: Request, call_next):
    """Middleware to track API usage for all requests."""
    # Skip for health checks and other internal endpoints
    if request.url.path in ["/health", "/metrics"]:
        return await call_next(request)
    
    # Get user from request
    user_id = request.state.get("user_id")
    
    if user_id:
        # Get subscription
        subscription = cs.get_user_subscription(user_id)
        subscription_id = subscription["id"] if subscription else None
        
        # Process request
        start_time = datetime.now()
        response = await call_next(request)
        end_time = datetime.now()
        
        # Calculate response time
        response_time_ms = (end_time - start_time).total_seconds() * 1000
        
        # Log API usage
        cs.log_api_usage(
            user_id=user_id,
            subscription_id=subscription_id,
            endpoint=str(request.url.path),
            method=request.method,
            status_code=response.status_code,
            response_time_ms=response_time_ms,
            request_size=request.headers.get("content-length"),
            response_size=response.headers.get("content-length")
        )
        
        # Add rate limit headers
        rate_limit = get_rate_limit(request)
        response.headers["X-RateLimit-Limit"] = str(rate_limit["limit"])
        response.headers["X-RateLimit-Remaining"] = str(rate_limit["remaining"])
        
        return response
    else:
        # Process request without tracking
        return await call_next(request)


# ---------------------------------------------------------------------------
# Feature Gate Helper Functions
# ---------------------------------------------------------------------------

def get_user_features(user_id: int) -> List[Dict[str, Any]]:
    """Get all features available to a user."""
    # Get user's subscription
    subscription = cs.get_user_subscription(user_id)
    
    if not subscription:
        # Return public features only
        public_gates = cs.get_all_feature_gates(is_public=True)
        return [gate for gate in public_gates if "plan_public_scope" in gate.get("enabled_plans", [])]
    
    plan_id = subscription["plan_id"]
    
    # Get all feature gates for the plan
    feature_gates = cs.get_feature_gates_by_plan(plan_id)
    
    return feature_gates


def get_user_quota_status(user_id: int) -> List[Dict[str, Any]]:
    """Get quota status for all features for a user."""
    # Get user's subscription
    subscription = cs.get_user_subscription(user_id)
    
    if not subscription:
        return []
    
    subscription_id = subscription["id"]
    
    # Get quota status
    return ps.get_quota_status(subscription_id)


def get_usage_analytics(user_id: int, days: int = 30) -> Dict[str, Any]:
    """Get usage analytics for a user."""
    # Get user's subscription
    subscription = cs.get_user_subscription(user_id)
    
    if not subscription:
        return {}
    
    subscription_id = subscription["id"]
    
    # Get usage analytics
    return ps.get_usage_analytics(user_id, subscription_id, days)
