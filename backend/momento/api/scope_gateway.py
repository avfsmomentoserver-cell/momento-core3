"""API Gateway middleware for V5 multi-scope authentication and authorization.

This module implements the API gateway layer that:
- Validates authentication tokens (JWT and API keys)
- Extracts scope and tenant context
- Enforces scope-based routing
- Applies rate limiting per scope
- Injects tenant context into requests
- Logs scope operations for audit
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional, Set, Tuple
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .. import db
from ..scope_auth import decode_scope_token, get_user_primary_tenant
from ..scope_authorization import has_permission
from ..scope_communication import check_cross_scope_access, get_communication_policy
from ..multi_scope_schema import SCOPES, SCOPE_ROUTES
from ..rate_limiter import check_rate_limit_or_raise

security = HTTPBearer(auto_error=False)


class TenantContext:
    """Tenant context for multi-tenant isolation.
    
    This class encapsulates the tenant, user, and scope information
    for the current request, providing a clean interface for accessing
    multi-tenant context throughout the request lifecycle.
    """
    
    def __init__(
        self,
        tenant_id: Optional[str] = None,
        user_id: Optional[int] = None,
        scope: Optional[str] = None,
        user_role: Optional[str] = None,
        user_email: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None,
    ):
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.scope = scope
        self.user_role = user_role
        self.user_email = user_email
        self.settings = settings or {}
        self._permissions: Optional[Set[str]] = None
    
    @property
    def is_authenticated(self) -> bool:
        """Check if the context has valid authentication."""
        return self.user_id is not None and self.scope is not None
    
    @property
    def is_my_scope(self) -> bool:
        """Check if this is My Scope (platform owner)."""
        return self.scope == "my_scope"
    
    @property
    def is_admin_scope(self) -> bool:
        """Check if this is Admin Scope."""
        return self.scope == "admin_scope"
    
    @property
    def is_paid_scope(self) -> bool:
        """Check if this is a paid scope (FX, Big Better, Regular)."""
        return self.scope in ["fx_user_scope", "big_better_scope", "regular_low_budget_scope"]
    
    def has_permission(self, resource: str, action: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Check if the scope has permission for a resource-action pair.
        
        Args:
            resource: Resource being accessed
            action: Action being performed
            context: Optional context for ABAC evaluation
            
        Returns:
            True if permission granted, False otherwise
        """
        if not self.scope:
            return False
        return has_permission(self.scope, resource, action, context)
    
    def can_access_tenant(self, target_tenant_id: str, target_scope: str, resource: str, action: str) -> Tuple[bool, Optional[str]]:
        """Check if this context can access another tenant.
        
        Args:
            target_tenant_id: Target tenant ID
            target_scope: Target scope
            resource: Resource being accessed
            action: Action being performed
            
        Returns:
            Tuple of (allowed, reason)
        """
        if not self.scope:
            return False, "No scope in context"
        
        # Same tenant access is always allowed (subject to permissions)
        if self.tenant_id == target_tenant_id:
            return True, None
        
        # Cross-tenant access requires cross-scope policy check
        return check_cross_scope_access(
            source_scope=self.scope,
            target_scope=target_scope,
            resource=resource,
            action=action,
            context={"user_id": self.user_id, "tenant_id": self.tenant_id},
        )
    
    def get_data_isolation_scope(self) -> str:
        """Get the data isolation scope for queries.
        
        Returns:
            Tenant ID for data isolation or '*' for all tenants (admin only)
        """
        if self.is_my_scope or self.is_admin_scope:
            return "*"  # Can see all data
        return self.tenant_id or "none"
    
    def get_rate_limit(self) -> int:
        """Get the rate limit for this scope.
        
        Returns:
            Requests per minute (None for unlimited)
        """
        if not self.scope:
            return 100  # Default conservative limit
        
        scope_config = SCOPES.get(self.scope, {})
        return scope_config.get("rate_limit", 100)
    
    def get_features(self) -> List[str]:
        """Get the features available to this scope.
        
        Returns:
            List of feature names
        """
        if not self.scope:
            return []
        
        scope_config = SCOPES.get(self.scope, {})
        return scope_config.get("features", [])
    
    def has_feature(self, feature: str) -> bool:
        """Check if a feature is available to this scope.
        
        Args:
            feature: Feature name
            
        Returns:
            True if feature is available, False otherwise
        """
        return feature in self.get_features()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for logging/serialization."""
        return {
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "scope": self.scope,
            "user_role": self.user_role,
            "user_email": self.user_email,
            "is_authenticated": self.is_authenticated,
        }


class ScopeGatewayMiddleware(BaseHTTPMiddleware):
    """API Gateway middleware for scope-based routing and enforcement.
    
    This middleware:
    1. Extracts and validates authentication tokens
    2. Resolves tenant context from tokens
    3. Enforces scope-based routing rules
    4. Applies rate limiting
    5. Injects tenant context into request state
    6. Logs scope operations for audit
    """
    
    # Paths that don't require authentication
    PUBLIC_PATHS = {
        "/health",
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
    }
    
    # Scope-specific route prefixes
    SCOPE_ROUTES = {
        "my_scope": ["/my-scope", "/admin", "/system"],
        "admin_scope": ["/admin", "/users", "/monitoring"],
        "fx_user_scope": ["/fx", "/trading", "/professional"],
        "big_better_scope": ["/premium", "/big-better"],
        "regular_low_budget_scope": ["/consumer", "/basic"],
        "public_consumer_scope": ["/public", "/free"],
    }
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self._rate_limit_cache: Dict[str, Dict[str, Any]] = {}
    
    async def dispatch(self, request: Request, call_next):
        """Process request through scope gateway."""
        path = request.url.path
        
        # Skip authentication for public paths
        if any(path.startswith(p) or path == p for p in self.PUBLIC_PATHS):
            request.state.tenant_context = TenantContext()
            return await call_next(request)
        
        # Extract and validate token
        credentials: Optional[HTTPAuthorizationCredentials] = await security(request)
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Decode token and resolve tenant context
        context = await self._resolve_context(credentials.credentials, request)
        if not context or not context.is_authenticated:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication token",
            )
        
        # Enforce scope-based routing
        self._enforce_scope_routing(path, context)
        
        # Check cross-scope access for tenant-specific endpoints
        self._check_cross_scope_access(path, context, request)
        
        # Apply rate limiting
        await self._apply_rate_limit(request, context)
        
        # Inject context into request state
        request.state.tenant_context = context
        
        # Log audit event
        self._log_audit(request, context)
        
        # Process request
        response = await call_next(request)
        
        # Add scope headers to response
        response.headers["X-Scope"] = context.scope or "unknown"
        response.headers["X-Tenant-ID"] = context.tenant_id or "none"
        
        return response
    
    async def _resolve_context(self, token: str, request: Request) -> Optional[TenantContext]:
        """Resolve tenant context from authentication token.
        
        Args:
            token: Authentication token (JWT or API key)
            request: Current request
            
        Returns:
            TenantContext or None if invalid
        """
        # Try to decode as scope token
        payload = decode_scope_token(token)
        if not payload:
            return None
        
        user_id = payload.get("sub")
        scope = payload.get("scope")
        tenant_id = payload.get("tenant_id")
        
        if not user_id or not scope:
            return None
        
        # Get user's primary tenant if tenant_id not in token
        if not tenant_id:
            tenant = get_user_primary_tenant(user_id)
            if tenant:
                tenant_id = tenant["tenant_id"]
                scope = tenant["scope"]
        
        # Get user details
        user = db.query_one("SELECT * FROM users WHERE id = ?", (user_id,))
        if not user:
            return None
        
        # Get tenant settings
        settings = {}
        if tenant_id:
            tenant = db.query_one("SELECT settings FROM tenants WHERE tenant_id = ?", (tenant_id,))
            if tenant and tenant.get("settings"):
                try:
                    settings = json.loads(tenant["settings"])
                except (json.JSONDecodeError, TypeError):
                    pass
        
        return TenantContext(
            tenant_id=tenant_id,
            user_id=user_id,
            scope=scope,
            user_role=user.get("role"),
            user_email=user.get("email"),
            settings=settings,
        )
    
    def _enforce_scope_routing(self, path: str, context: TenantContext) -> None:
        """Enforce scope-based routing rules.
        
        Args:
            path: Request path
            context: Tenant context
            
        Raises:
            HTTPException: If routing violation detected
        """
        if not context.scope:
            return
        
        # My Scope can access everything
        if context.scope == "my_scope":
            return
        
        # Admin Scope can access admin routes
        if context.scope == "admin_scope":
            if path.startswith("/my-scope"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="My Scope access requires platform owner privileges",
                )
            return
        
        # Check if path is allowed for this scope
        allowed_prefixes = self.SCOPE_ROUTES.get(context.scope, [])
        is_allowed = any(path.startswith(prefix) for prefix in allowed_prefixes)
        
        # Also allow general API paths
        if path.startswith("/api/v1") and not any(
            path.startswith(f"/api/v1{prefix}") for prefix in ["/my-scope", "/admin"]
        ):
            is_allowed = True
        
        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Path '{path}' not accessible for scope '{context.scope}'",
            )
    
    def _check_cross_scope_access(self, path: str, context: TenantContext, request: Request) -> None:
        """Check cross-scope access for tenant-specific endpoints.
        
        Args:
            path: Request path
            context: Tenant context
            request: Current request
            
        Raises:
            HTTPException: If cross-scope access denied
        """
        # Extract target tenant from path if present
        # Pattern: /api/v1/tenants/{tenant_id}/...
        if "/tenants/" in path:
            parts = path.split("/tenants/")
            if len(parts) > 1:
                target_tenant_id = parts[1].split("/")[0]
                
                # Get target scope
                target_tenant = db.query_one("SELECT scope FROM tenants WHERE tenant_id = ?", (target_tenant_id,))
                if not target_tenant:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Target tenant not found",
                    )
                
                target_scope = target_tenant["scope"]
                
                # Determine resource and action from path and method
                resource = self._extract_resource_from_path(path)
                action = self._map_method_to_action(request.method)
                
                # Check cross-scope access
                allowed, reason = context.can_access_tenant(target_tenant_id, target_scope, resource, action)
                
                if not allowed:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Cross-scope access denied: {reason}",
                    )
    
    def _extract_resource_from_path(self, path: str) -> str:
        """Extract resource type from path.
        
        Args:
            path: Request path
            
        Returns:
            Resource name
        """
        if "/rounds" in path:
            return "rounds"
        elif "/analysis" in path:
            return "analysis"
        elif "/forecasts" in path:
            return "forecasts"
        elif "/users" in path:
            return "users"
        elif "/predictions" in path:
            return "predictions"
        else:
            return "api"
    
    def _map_method_to_action(self, method: str) -> str:
        """Map HTTP method to action.
        
        Args:
            method: HTTP method
            
        Returns:
            Action name
        """
        if method == "GET":
            return "read"
        elif method in ["POST", "PUT", "PATCH"]:
            return "write"
        elif method == "DELETE":
            return "delete"
        else:
            return "read"
    
    async def _apply_rate_limit(self, request: Request, context: TenantContext) -> None:
        """Apply rate limiting based on scope.
        
        Args:
            request: Current request
            context: Tenant context
            
        Raises:
            HTTPException: If rate limit exceeded
        """
        rate_limit = context.get_rate_limit()
        if rate_limit is None:
            # Unlimited for My Scope
            return
        
        # Get client identifier
        client_id = context.tenant_id or request.client.host
        if not client_id:
            return
        
        # Simple in-memory rate limiting (use Redis in production)
        now = int(time.time())
        window_start = now - 60  # 1-minute window
        
        cache_key = f"{client_id}:{context.scope}"
        
        # Clean old entries
        if cache_key in self._rate_limit_cache:
            if self._rate_limit_cache[cache_key]["window_start"] < window_start:
                self._rate_limit_cache[cache_key] = {
                    "count": 1,
                    "window_start": now,
                }
            else:
                self._rate_limit_cache[cache_key]["count"] += 1
        else:
            self._rate_limit_cache[cache_key] = {
                "count": 1,
                "window_start": now,
            }
        
        current_count = self._rate_limit_cache[cache_key]["count"]
        
        if current_count > rate_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded: {rate_limit} requests per minute",
                headers={
                    "X-RateLimit-Limit": str(rate_limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(self._rate_limit_cache[cache_key]["window_start"] + 60),
                },
            )
    
    def _log_audit(self, request: Request, context: TenantContext) -> None:
        """Log scope operation for audit.
        
        Args:
            request: Current request
            context: Tenant context
        """
        try:
            db.execute(
                """INSERT INTO scope_audit_log 
                   (tenant_id, user_id, scope, action, resource, details, ip_address, user_agent, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    context.tenant_id,
                    context.user_id,
                    context.scope,
                    request.method,
                    request.url.path,
                    json.dumps({"query_params": dict(request.query_params)}),
                    request.client.host if request.client else None,
                    request.headers.get("user-agent"),
                    db.utc_now(),
                ),
            )
        except Exception:
            # Don't fail the request if audit logging fails
            pass


def get_tenant_context(request: Request) -> TenantContext:
    """Get tenant context from request state.
    
    This is a dependency function for FastAPI routes.
    
    Args:
        request: Current request
        
    Returns:
        TenantContext from request state
        
    Raises:
        HTTPException: If context not found
    """
    context = getattr(request.state, "tenant_context", None)
    if not context:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Tenant context not initialized",
        )
    return context


def require_scope(*scopes: str) -> callable:
    """Decorator to require specific scopes for access.
    
    Args:
        *scopes: Required scope identifiers
        
    Returns:
        Dependency function for FastAPI
    """
    async def dependency(request: Request) -> TenantContext:
        context = get_tenant_context(request)
        
        if not context.is_authenticated:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        
        if context.scope not in scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access restricted to scopes: {', '.join(scopes)}",
            )
        
        return context
    
    return dependency


def require_permission(resource: str, action: str) -> callable:
    """Decorator to require specific permission for access.
    
    Args:
        resource: Resource name
        action: Action name
        
    Returns:
        Dependency function for FastAPI
    """
    async def dependency(request: Request) -> TenantContext:
        context = get_tenant_context(request)
        
        if not context.is_authenticated:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        
        if not context.has_permission(resource, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{resource}:{action}' required",
            )
        
        return context
    
    return dependency


def require_feature(feature: str) -> callable:
    """Decorator to require a specific feature for access.
    
    Args:
        feature: Feature name
        
    Returns:
        Dependency function for FastAPI
    """
    async def dependency(request: Request) -> TenantContext:
        context = get_tenant_context(request)
        
        if not context.is_authenticated:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        
        if not context.has_feature(feature):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Feature '{feature}' not available for current scope",
            )
        
        return context
    
    return dependency
