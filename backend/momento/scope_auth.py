"""Multi-scope authentication and authorization for V5 transformation.

This module implements scope-based authentication and authorization including:
- Scope-aware token generation and validation
- Multi-tenant context management
- Scope-based permission checking
- Subscription validation
- API key authentication
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any, Dict, List, Optional, Set

from . import auth, config, db
from .multi_scope_schema import SCOPES

# Scope definitions
VALID_SCOPES = set(SCOPES.keys())
SCOPE_HIERARCHY = {
    "my_scope": 100,  # Highest privilege
    "admin_scope": 90,
    "fx_user_scope": 80,
    "big_better_scope": 70,
    "regular_low_budget_scope": 60,
    "public_consumer_scope": 50,  # Lowest privilege
}

# Scope permissions mapping
SCOPE_PERMISSIONS = {
    "my_scope": {
        "system": ["read", "write", "delete", "admin"],
        "users": ["read", "write", "delete", "admin"],
        "tenants": ["read", "write", "delete", "admin"],
        "subscriptions": ["read", "write", "delete", "admin"],
        "billing": ["read", "write", "delete", "admin"],
        "api": ["read", "write", "delete", "admin"],
        "data": ["read", "write", "delete", "admin"],
    },
    "admin_scope": {
        "system": ["read", "write"],
        "users": ["read", "write", "delete"],
        "tenants": ["read", "write"],
        "subscriptions": ["read", "write", "delete"],
        "billing": ["read", "write"],
        "api": ["read", "write"],
        "data": ["read", "write"],
    },
    "fx_user_scope": {
        "system": ["read"],
        "users": ["read"],
        "tenants": ["read"],
        "subscriptions": ["read"],
        "billing": ["read"],
        "api": ["read", "write"],
        "data": ["read", "write"],
    },
    "big_better_scope": {
        "system": ["read"],
        "users": ["read"],
        "tenants": ["read"],
        "subscriptions": ["read"],
        "billing": ["read"],
        "api": ["read", "write"],
        "data": ["read", "write"],
    },
    "regular_low_budget_scope": {
        "system": [],
        "users": ["read"],
        "tenants": ["read"],
        "subscriptions": ["read"],
        "billing": ["read"],
        "api": ["read"],
        "data": ["read"],
    },
    "public_consumer_scope": {
        "system": [],
        "users": ["read"],
        "tenants": [],
        "subscriptions": ["read"],
        "billing": [],
        "api": ["read"],
        "data": ["read"],
    },
}


def _b64(data: bytes) -> str:
    """Base64 URL-safe encoding without padding."""
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    """Base64 URL-safe decoding with padding restoration."""
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


def issue_scope_token(
    user: Dict[str, Any],
    scope: str,
    tenant_id: Optional[str] = None,
    additional_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """Issue a scope-aware authentication token.
    
    Args:
        user: User dictionary with at least 'id', 'email', 'role', 'tier'
        scope: User scope (must be in VALID_SCOPES)
        tenant_id: Optional tenant ID for multi-tenant context
        additional_claims: Optional additional claims to include in token
        
    Returns:
        HMAC-signed JWT-like token with scope information
        
    Raises:
        ValueError: If scope is invalid
    """
    if scope not in VALID_SCOPES:
        raise ValueError(f"Invalid scope: {scope}")
    
    payload = {
        "sub": int(user["id"]),
        "email": user["email"],
        "role": user["role"],
        "tier": user["tier"],
        "scope": scope,
        "tenant_id": tenant_id,
        "exp": int(time.time()) + config.TOKEN_TTL_SECONDS,
        "iat": int(time.time()),
    }
    
    if additional_claims:
        payload.update(additional_claims)
    
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    signature = _b64(hmac.new(config.SECRET_KEY.encode(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{signature}"


def decode_scope_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a scope-aware token.
    
    Args:
        token: HMAC-signed token string
        
    Returns:
        Token payload if valid, None otherwise
    """
    if not token or "." not in token:
        return None
    
    body, _, signature = token.partition(".")
    expected = _b64(hmac.new(config.SECRET_KEY.encode(), body.encode(), hashlib.sha256).digest())
    
    if not hmac.compare_digest(signature, expected):
        return None
    
    try:
        payload = json.loads(_unb64(body))
    except (ValueError, json.JSONDecodeError):
        return None
    
    # Check expiration
    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    
    # Validate scope
    if payload.get("scope") not in VALID_SCOPES:
        return None
    
    return payload


def get_user_scopes(user_id: int) -> List[str]:
    """Get all scopes a user has access to through their tenants.
    
    Args:
        user_id: User ID
        
    Returns:
        List of scope names the user can access
    """
    query = """
        SELECT DISTINCT t.scope
        FROM tenants t
        JOIN user_tenants ut ON t.tenant_id = ut.tenant_id
        WHERE ut.user_id = ? AND t.status = 'active' AND ut.is_primary = 1
    """
    rows = db.query(query, (int(user_id),))
    return [row["scope"] for row in rows if row["scope"] in VALID_SCOPES]


def get_user_primary_tenant(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user's primary tenant with scope information.
    
    Args:
        user_id: User ID
        
    Returns:
        Tenant dictionary or None
    """
    query = """
        SELECT t.*, ut.role as user_role, ut.is_primary
        FROM tenants t
        JOIN user_tenants ut ON t.tenant_id = ut.tenant_id
        WHERE ut.user_id = ? AND ut.is_primary = 1 AND t.status = 'active'
    """
    row = db.query_one(query, (int(user_id),))
    if row:
        return {
            "tenant_id": row["tenant_id"],
            "name": row["name"],
            "display_name": row["display_name"],
            "scope": row["scope"],
            "status": row["status"],
            "user_role": row["user_role"],
            "settings": json.loads(row.get("settings", "{}")),
        }
    return None


def check_scope_permission(
    scope: str,
    resource: str,
    action: str,
) -> bool:
    """Check if a scope has permission for a resource/action.
    
    Args:
        scope: Scope name
        resource: Resource type (e.g., 'users', 'system')
        action: Action type (e.g., 'read', 'write', 'delete')
        
    Returns:
        True if permission granted, False otherwise
    """
    if scope not in SCOPE_PERMISSIONS:
        return False
    
    resource_permissions = SCOPE_PERMISSIONS.get(scope, {})
    allowed_actions = resource_permissions.get(resource, [])
    
    return action in allowed_actions


def check_user_permission(
    user_id: int,
    resource: str,
    action: str,
    tenant_id: Optional[str] = None,
) -> bool:
    """Check if a user has permission for a resource/action.
    
    Args:
        user_id: User ID
        resource: Resource type
        action: Action type
        tenant_id: Optional tenant ID for context
        
    Returns:
        True if permission granted, False otherwise
    """
    # Get user's primary tenant and scope
    tenant = get_user_primary_tenant(user_id)
    if not tenant:
        return False
    
    # Check tenant context if provided
    if tenant_id and tenant["tenant_id"] != tenant_id:
        # Check if user has access to the specific tenant
        query = """
            SELECT ut.role
            FROM user_tenants ut
            WHERE ut.user_id = ? AND ut.tenant_id = ?
        """
        ut_row = db.query_one(query, (int(user_id), tenant_id))
        if not ut_row:
            return False
    
    # Check scope permission
    return check_scope_permission(tenant["scope"], resource, action)


def validate_subscription_access(user_id: int, required_features: List[str]) -> bool:
    """Check if user's subscription provides required features.
    
    Args:
        user_id: User ID
        required_features: List of required feature names
        
    Returns:
        True if user has access to all required features
    """
    tenant = get_user_primary_tenant(user_id)
    if not tenant:
        return False
    
    # Get active subscription
    query = """
        SELECT s.features, sp.features as plan_features
        FROM subscriptions s
        LEFT JOIN subscription_plans sp ON s.plan_id = sp.plan_id
        WHERE s.tenant_id = ? AND s.status = 'active'
        ORDER BY s.created_at DESC
        LIMIT 1
    """
    sub_row = db.query_one(query, (tenant["tenant_id"],))
    
    if not sub_row:
        return False
    
    # Combine subscription and plan features
    sub_features = json.loads(sub_row.get("features", "{}"))
    plan_features = json.loads(sub_row.get("plan_features", "{}"))
    
    available_features = set(sub_features.keys()) | set(plan_features.keys())
    
    return all(feature in available_features for feature in required_features)


def get_scope_rate_limit(scope: str) -> Optional[int]:
    """Get rate limit for a scope.
    
    Args:
        scope: Scope name
        
    Returns:
        Rate limit (requests per minute) or None for unlimited
    """
    scope_config = SCOPES.get(scope, {})
    return scope_config.get("rate_limit")


def create_api_key(
    user_id: int,
    tenant_id: str,
    name: str,
    permissions: Optional[Dict[str, Any]] = None,
    expires_at: Optional[str] = None,
) -> str:
    """Create an API key for scope-based access.
    
    Args:
        user_id: User ID
        tenant_id: Tenant ID
        name: API key name
        permissions: Optional permissions dict
        expires_at: Optional expiration timestamp
        
    Returns:
        API key string
    """
    key_id = f"key_{secrets.token_urlsafe(16)}"
    key_secret = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(key_secret.encode()).hexdigest()
    
    # Get tenant scope
    tenant_row = db.query_one("SELECT scope FROM tenants WHERE tenant_id = ?", (tenant_id,))
    if not tenant_row:
        raise ValueError("Tenant not found")
    scope = tenant_row["scope"]
    
    db.execute(
        """INSERT INTO api_keys (key_id, key_hash, user_id, tenant_id, scope, name, permissions, expires_at, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            key_id,
            key_hash,
            int(user_id),
            tenant_id,
            scope,
            name,
            json.dumps(permissions or {}),
            expires_at,
            db.utc_now(),
        ),
    )
    
    return f"{key_id}.{key_secret}"


def validate_api_key(api_key: str) -> Optional[Dict[str, Any]]:
    """Validate an API key and return its context.
    
    Args:
        api_key: API key string in format "key_id.key_secret"
        
    Returns:
        API key context dict or None if invalid
    """
    if "." not in api_key:
        return None
    
    key_id, key_secret = api_key.split(".", 1)
    key_hash = hashlib.sha256(key_secret.encode()).hexdigest()
    
    query = """
        SELECT ak.*, u.email, u.role, u.tier
        FROM api_keys ak
        JOIN users u ON ak.user_id = u.id
        WHERE ak.key_id = ? AND ak.key_hash = ? AND ak.active = 1
    """
    row = db.query_one(query, (key_id, key_hash))
    
    if not row:
        return None
    
    # Check expiration
    if row["expires_at"] and row["expires_at"] < db.utc_now():
        return None
    
    # Update last used
    db.execute("UPDATE api_keys SET last_used = ? WHERE key_id = ?", (db.utc_now(), key_id))
    
    return {
        "user_id": row["user_id"],
        "email": row["email"],
        "role": row["role"],
        "tier": row["tier"],
        "tenant_id": row["tenant_id"],
        "scope": row["scope"],
        "permissions": json.loads(row.get("permissions", "{}")),
        "key_id": key_id,
    }


def revoke_api_key(key_id: str) -> bool:
    """Revoke an API key.
    
    Args:
        key_id: API key ID
        
    Returns:
        True if revoked, False if not found
    """
    db.execute("UPDATE api_keys SET active = 0 WHERE key_id = ?", (key_id,))
    return True


def log_scope_audit(
    tenant_id: Optional[str],
    user_id: Optional[int],
    scope: str,
    action: str,
    resource: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """Log a scope-related action to the audit log.
    
    Args:
        tenant_id: Optional tenant ID
        user_id: Optional user ID
        scope: Scope name
        action: Action performed
        resource: Optional resource affected
        details: Optional action details
        ip_address: Optional client IP address
        user_agent: Optional client user agent
    """
    db.execute(
        """INSERT INTO scope_audit_log (tenant_id, user_id, scope, action, resource, details, ip_address, user_agent, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            tenant_id,
            user_id,
            scope,
            action,
            resource,
            json.dumps(details or {}),
            ip_address,
            user_agent,
            db.utc_now(),
        ),
    )


def get_tenant_context(tenant_id: str) -> Optional[Dict[str, Any]]:
    """Get full tenant context including subscription info.
    
    Args:
        tenant_id: Tenant ID
        
    Returns:
        Tenant context dict or None
    """
    query = """
        SELECT t.*, 
               (SELECT COUNT(*) FROM user_tenants WHERE tenant_id = t.tenant_id) as user_count,
               (SELECT features FROM subscriptions 
                WHERE tenant_id = t.tenant_id AND status = 'active' 
                ORDER BY created_at DESC LIMIT 1) as subscription_features
        FROM tenants t
        WHERE t.tenant_id = ? AND t.status = 'active'
    """
    row = db.query_one(query, (tenant_id,))
    
    if not row:
        return None
    
    return {
        "tenant_id": row["tenant_id"],
        "name": row["name"],
        "display_name": row["display_name"],
        "scope": row["scope"],
        "status": row["status"],
        "settings": json.loads(row.get("settings", "{}")),
        "user_count": row["user_count"],
        "subscription_features": json.loads(row.get("subscription_features", "{}")),
    }


def initialize_default_scopes() -> None:
    """Initialize default scope configuration in database.
    
    This creates the default tenants for each scope type.
    """
    # Check if already initialized
    existing = db.query_one("SELECT COUNT(*) as c FROM tenants")
    if existing and int(existing["c"]) > 0:
        return
    
    # Create default tenant for each scope
    for scope_id, scope_config in SCOPES.items():
        tenant_id = f"default_{scope_id}"
        try:
            db.execute(
                """INSERT INTO tenants (tenant_id, name, display_name, scope, status, settings, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    tenant_id,
                    scope_config["name"],
                    scope_config["description"],
                    scope_id,
                    "active",
                    json.dumps({"is_default": True}),
                    db.utc_now(),
                    db.utc_now(),
                ),
            )
        except Exception:
            # Tenant might already exist
            pass
