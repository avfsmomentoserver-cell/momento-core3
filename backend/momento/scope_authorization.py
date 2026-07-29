"""Scope-based authorization framework (RBAC/ABAC).

This module implements a hybrid RBAC/ABAC authorization system:
- Role-Based Access Control (RBAC) for scope-based permissions
- Attribute-Based Access Control (ABAC) for fine-grained conditions
- Resource-action permission model
- Policy evaluation engine
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Set

from . import db
from .scope_auth import SCOPE_PERMISSIONS

# Permission cache (in production, use Redis)
_PERMISSION_CACHE: Dict[str, Set[str]] = {}


def clear_permission_cache() -> None:
    """Clear the permission cache."""
    _PERMISSION_CACHE.clear()


def load_scope_permissions(scope: str) -> Set[str]:
    """Load permissions for a scope from database.

    Args:
        scope: Scope identifier

    Returns:
        Set of permission strings in format "resource:action"
    """
    cache_key = f"scope:{scope}"

    if cache_key in _PERMISSION_CACHE:
        return _PERMISSION_CACHE[cache_key]

    rows = db.query(
        """SELECT resource, action FROM scope_permissions
           WHERE scope = ? AND enabled = 1""",
        (scope,),
    )

    permissions = {f"{row['resource']}:{row['action']}" for row in rows}
    _PERMISSION_CACHE[cache_key] = permissions

    return permissions


def has_permission(
    scope: str,
    resource: str,
    action: str,
    context: Optional[Dict[str, Any]] = None,
) -> bool:
    """Check if a scope has permission for a resource-action pair.

    Args:
        scope: Scope identifier
        resource: Resource being accessed (e.g., "users", "predictions")
        action: Action being performed (e.g., "read", "write", "delete")
        context: Optional context for ABAC evaluation

    Returns:
        True if permission granted, False otherwise
    """
    # My Scope has full access
    if scope == "my_scope":
        return True

    # Admin Scope has most access (except owner-only operations)
    if scope == "admin_scope":
        if resource in ["billing", "deployment"]:
            return False
        return True

    # Load permissions for scope
    permissions = load_scope_permissions(scope)

    # Check for wildcard permission
    if "*:*" in permissions:
        return True

    # Check for resource wildcard
    if f"{resource}:*" in permissions:
        return True

    # Check for action wildcard
    if f"*:{action}" in permissions:
        return True

    # Check for exact match
    if f"{resource}:{action}" in permissions:
        # Evaluate ABAC conditions if context provided
        if context:
            return evaluate_conditions(scope, resource, action, context)

        return True

    return False


def evaluate_conditions(
    scope: str,
    resource: str,
    action: str,
    context: Dict[str, Any],
) -> bool:
    """Evaluate ABAC conditions for a permission.

    Args:
        scope: Scope identifier
        resource: Resource being accessed
        action: Action being performed
        context: Context dictionary with attributes

    Returns:
        True if conditions pass, False otherwise
    """
    row = db.query_one(
        """SELECT condition FROM scope_permissions
           WHERE scope = ? AND resource = ? AND action = ? AND enabled = 1""",
        (scope, resource, action),
    )

    if not row or not row["condition"]:
        return True

    try:
        condition = json.loads(row["condition"])
    except (json.JSONDecodeError, TypeError):
        return True

    # Evaluate conditions
    for key, expected in condition.items():
        if key not in context:
            return False

        actual = context[key]

        # Handle different comparison types
        if isinstance(expected, dict):
            # Complex condition with operator
            op = expected.get("op", "eq")
            value = expected.get("value")

            if op == "eq":
                if actual != value:
                    return False
            elif op == "ne":
                if actual == value:
                    return False
            elif op == "gt":
                if not (isinstance(actual, (int, float)) and actual > value):
                    return False
            elif op == "gte":
                if not (isinstance(actual, (int, float)) and actual >= value):
                    return False
            elif op == "lt":
                if not (isinstance(actual, (int, float)) and actual < value):
                    return False
            elif op == "lte":
                if not (isinstance(actual, (int, float)) and actual <= value):
                    return False
            elif op == "in":
                if actual not in value:
                    return False
            elif op == "contains":
                if value not in actual:
                    return False
        else:
            # Simple equality check
            if actual != expected:
                return False

    return True


def check_feature_access(scope: str, feature: str) -> bool:
    """Check if a scope has access to a specific feature.

    Args:
        scope: Scope identifier
        feature: Feature name (e.g., "hft_predictions", "realtime_feed")

    Returns:
        True if feature is accessible, False otherwise
    """
    from .multi_scope_schema import SCOPES

    scope_config = SCOPES.get(scope, {})
    features = scope_config.get("features", [])

    return feature in features


def get_allowed_resources(scope: str) -> List[str]:
    """Get all resources a scope can access.

    Args:
        scope: Scope identifier

    Returns:
        List of resource names
    """
    permissions = load_scope_permissions(scope)
    resources = set()

    for perm in permissions:
        resource, _ = perm.split(":")
        if resource != "*":
            resources.add(resource)

    return sorted(list(resources))


def get_allowed_actions(scope: str, resource: str) -> List[str]:
    """Get all allowed actions for a scope on a resource.

    Args:
        scope: Scope identifier
        resource: Resource name

    Returns:
        List of action names
    """
    permissions = load_scope_permissions(scope)
    actions = set()

    for perm in permissions:
        perm_resource, perm_action = perm.split(":")
        if perm_resource == resource or perm_resource == "*":
            if perm_action != "*":
                actions.add(perm_action)

    return sorted(list(actions))


def require_scope(required_scope: str) -> callable:
    """Decorator to require a specific scope for access.

    Args:
        required_scope: Required scope identifier

    Returns:
        Decorator function
    """

    def decorator(func: callable) -> callable:
        def wrapper(*args, **kwargs):
            # Extract user scope from context (implementation depends on framework)
            # This is a placeholder for the actual implementation
            user_scope = kwargs.get("scope")
            if user_scope != required_scope:
                raise PermissionError(f"Scope {required_scope} required")
            return func(*args, **kwargs)

        return wrapper

    return decorator


def require_permission(resource: str, action: str) -> callable:
    """Decorator to require a specific permission for access.

    Args:
        resource: Resource name
        action: Action name

    Returns:
        Decorator function
    """

    def decorator(func: callable) -> callable:
        def wrapper(*args, **kwargs):
            scope = kwargs.get("scope")
            context = kwargs.get("context", {})

            if not has_permission(scope, resource, action, context):
                raise PermissionError(f"Permission {resource}:{action} required")

            return func(*args, **kwargs)

        return wrapper

    return decorator


def require_feature(feature: str) -> callable:
    """Decorator to require a specific feature for access.

    Args:
        feature: Feature name

    Returns:
        Decorator function
    """

    def decorator(func: callable) -> callable:
        def wrapper(*args, **kwargs):
            scope = kwargs.get("scope")

            if not check_feature_access(scope, feature):
                raise PermissionError(f"Feature {feature} not available in scope {scope}")

            return func(*args, **kwargs)

        return wrapper

    return decorator


def initialize_default_permissions() -> None:
    """Initialize default permissions in the database.

    This should be called during database initialization.
    """
    from .scope_auth import SCOPE_PERMISSIONS

    now = db.utc_now()

    for scope, resources in SCOPE_PERMISSIONS.items():
        for resource, actions in resources.items():
            for action in actions:
                db.execute(
                    """INSERT INTO scope_permissions (scope, resource, action, enabled, created_at)
                       VALUES (?, ?, ?, ?, ?)
                       ON CONFLICT(scope, resource, action) DO UPDATE SET enabled = excluded.enabled""",
                    (scope, resource, action, 1, now),
                )


def add_permission(
    scope: str,
    resource: str,
    action: str,
    condition: Optional[Dict[str, Any]] = None,
) -> bool:
    """Add a new permission for a scope.

    Args:
        scope: Scope identifier
        resource: Resource name
        action: Action name
        condition: Optional ABAC condition

    Returns:
        True if added, False if already exists
    """
    try:
        db.execute(
            """INSERT INTO scope_permissions (scope, resource, action, condition, enabled, created_at)
               VALUES (?, ?, ?, ?, 1, ?)""",
            (scope, resource, action, json.dumps(condition) if condition else None, db.utc_now()),
        )
        clear_permission_cache()
        return True
    except Exception:
        return False


def remove_permission(scope: str, resource: str, action: str) -> bool:
    """Remove a permission from a scope.

    Args:
        scope: Scope identifier
        resource: Resource name
        action: Action name

    Returns:
        True if removed, False if not found
    """
    result = db.execute(
        """DELETE FROM scope_permissions WHERE scope = ? AND resource = ? AND action = ?""",
        (scope, resource, action),
    )
    clear_permission_cache()
    return result > 0


def get_scope_permissions(scope: str) -> List[Dict[str, Any]]:
    """Get all permissions for a scope.

    Args:
        scope: Scope identifier

    Returns:
        List of permission dictionaries
    """
    rows = db.query(
        """SELECT resource, action, condition, enabled FROM scope_permissions
           WHERE scope = ?
           ORDER BY resource, action""",
        (scope,),
    )

    return [
        {
            "resource": row["resource"],
            "action": row["action"],
            "condition": json.loads(row["condition"]) if row["condition"] else None,
            "enabled": bool(row["enabled"]),
        }
        for row in rows
    ]


class AuthorizationContext:
    """Context object for authorization checks."""

    def __init__(
        self,
        scope: str,
        user_id: Optional[int] = None,
        tenant_id: Optional[str] = None,
        **attributes: Any,
    ):
        """Initialize authorization context.

        Args:
            scope: User scope
            user_id: Optional user ID
            tenant_id: Optional tenant ID
            **attributes: Additional context attributes
        """
        self.scope = scope
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.attributes = attributes

    def can(self, resource: str, action: str) -> bool:
        """Check if context has permission for resource-action.

        Args:
            resource: Resource name
            action: Action name

        Returns:
            True if permission granted
        """
        context = {
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            **self.attributes,
        }
        return has_permission(self.scope, resource, action, context)

    def has_feature(self, feature: str) -> bool:
        """Check if context has access to a feature.

        Args:
            feature: Feature name

        Returns:
            True if feature accessible
        """
        return check_feature_access(self.scope, feature)

    def require(self, resource: str, action: str) -> None:
        """Require permission, raise exception if not granted.

        Args:
            resource: Resource name
            action: Action name

        Raises:
            PermissionError: If permission not granted
        """
        if not self.can(resource, action):
            raise PermissionError(f"Permission denied: {resource}:{action}")

    def require_feature(self, feature: str) -> None:
        """Require feature access, raise exception if not available.

        Args:
            feature: Feature name

        Raises:
            PermissionError: If feature not available
        """
        if not self.has_feature(feature):
            raise PermissionError(f"Feature not available: {feature}")
