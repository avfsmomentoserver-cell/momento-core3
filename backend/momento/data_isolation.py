"""Cross-scope data access controls for multi-tenant isolation.

This module implements:
- Tenant-scoped database queries
- Row-level security for data isolation
- Cross-tenant data access validation
- Data filtering by scope
- Audit logging for data access
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass

from . import db
from .scope_communication import check_cross_scope_access
from .scope_authorization import has_permission


@dataclass
class DataAccessContext:
    """Context for data access operations."""

    tenant_id: Optional[str]
    scope: Optional[str]
    user_id: Optional[int]
    is_admin: bool = False
    is_owner: bool = False

    def can_access_all_tenants(self) -> bool:
        """Check if context can access all tenant data."""
        return self.is_admin or self.is_owner or self.scope in ["my_scope", "admin_scope"]

    def get_tenant_filter(self) -> str:
        """Get SQL WHERE clause for tenant filtering."""
        if self.can_access_all_tenants():
            return "1=1"  # No filter
        if self.tenant_id:
            return f"tenant_id = '{self.tenant_id}'"
        return "1=0"  # No access


class DataIsolationManager:
    """Manager for cross-scope data access controls."""

    def __init__(self):
        self._access_cache: Dict[str, bool] = {}

    def build_tenant_aware_query(
        self,
        base_query: str,
        context: DataAccessContext,
        tenant_column: str = "tenant_id",
    ) -> str:
        """Build a tenant-aware SQL query with proper filtering.

        Args:
            base_query: Base SQL query
            context: Data access context
            tenant_column: Column name for tenant ID

        Returns:
            Filtered SQL query
        """
        if context.can_access_all_tenants():
            return base_query

        # Add tenant filter
        if context.tenant_id:
            # Check if query already has WHERE clause
            if "WHERE" in base_query.upper():
                return f"{base_query} AND {tenant_column} = ?"
            else:
                return f"{base_query} WHERE {tenant_column} = ?"

        # No tenant context - return no results
        if "WHERE" in base_query.upper():
            return f"{base_query} AND 1=0"
        else:
            return f"{base_query} WHERE 1=0"

    def apply_tenant_filter(
        self,
        query: str,
        params: Tuple,
        context: DataAccessContext,
        tenant_column: str = "tenant_id",
    ) -> Tuple[str, Tuple]:
        """Apply tenant filter to a query.

        Args:
            query: SQL query
            params: Query parameters
            context: Data access context
            tenant_column: Column name for tenant ID

        Returns:
            Tuple of (filtered_query, filtered_params)
        """
        if context.can_access_all_tenants():
            return query, params

        if context.tenant_id:
            filtered_query = self.build_tenant_aware_query(query, context, tenant_column)
            return filtered_query, params + (context.tenant_id,)

        # No access
        return f"{query} WHERE 1=0", params

    def check_cross_tenant_access(
        self,
        source_tenant_id: str,
        source_scope: str,
        target_tenant_id: str,
        resource: str,
        action: str,
    ) -> Tuple[bool, Optional[str]]:
        """Check if cross-tenant data access is allowed.

        Args:
            source_tenant_id: Source tenant ID
            source_scope: Source scope
            target_tenant_id: Target tenant ID
            resource: Resource being accessed
            action: Action being performed

        Returns:
            Tuple of (allowed, reason)
        """
        # Same tenant is always allowed
        if source_tenant_id == target_tenant_id:
            return True, None

        # Check cross-scope policy
        target_tenant = db.query_one("SELECT scope FROM tenants WHERE tenant_id = ?", (target_tenant_id,))
        if not target_tenant:
            return False, "Target tenant not found"

        return check_cross_scope_access(
            source_scope=source_scope,
            target_scope=target_tenant["scope"],
            resource=resource,
            action=action,
        )

    def log_data_access(
        self,
        tenant_id: str,
        user_id: Optional[int],
        scope: str,
        resource: str,
        action: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log data access for audit.

        Args:
            tenant_id: Tenant ID
            user_id: User ID
            scope: Scope
            resource: Resource accessed
            action: Action performed
            resource_id: Optional resource ID
            details: Optional details
        """
        try:
            db.execute(
                """INSERT INTO scope_audit_log 
                   (tenant_id, user_id, scope, action, resource, details, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    tenant_id,
                    user_id,
                    scope,
                    action,
                    resource,
                    json.dumps(
                        {
                            "resource_id": resource_id,
                            **(details or {}),
                        }
                    ),
                    db.utc_now(),
                ),
            )
        except Exception:
            # Don't fail the operation if audit logging fails
            pass

    def enforce_row_level_security(
        self,
        table: str,
        rows: List[Dict[str, Any]],
        context: DataAccessContext,
        tenant_column: str = "tenant_id",
    ) -> List[Dict[str, Any]]:
        """Filter rows based on row-level security.

        Args:
            table: Table name
            rows: Raw rows from database
            context: Data access context
            tenant_column: Column name for tenant ID

        Returns:
            Filtered rows
        """
        if context.can_access_all_tenants():
            return rows

        filtered = []
        for row in rows:
            row_tenant_id = row.get(tenant_column)
            if row_tenant_id == context.tenant_id:
                filtered.append(row)

        return filtered

    def get_accessible_tenants(
        self,
        tenant_id: str,
        scope: str,
        resource: str,
        action: str,
    ) -> List[str]:
        """Get list of tenant IDs that can be accessed.

        Args:
            tenant_id: Current tenant ID
            scope: Current scope
            resource: Resource being accessed
            action: Action being performed

        Returns:
            List of accessible tenant IDs
        """
        # If admin/owner, can access all
        if scope in ["my_scope", "admin_scope"]:
            all_tenants = db.query("SELECT tenant_id FROM tenants WHERE status = 'active'")
            return [row["tenant_id"] for row in all_tenants]

        # Otherwise, only own tenant
        return [tenant_id]

    def sanitize_output(
        self,
        data: Dict[str, Any],
        context: DataAccessContext,
        sensitive_fields: Optional[Set[str]] = None,
    ) -> Dict[str, Any]:
        """Sanitize output data based on scope and permissions.

        Args:
            data: Raw data
            context: Data access context
            sensitive_fields: Set of sensitive field names

        Returns:
            Sanitized data
        """
        if sensitive_fields is None:
            sensitive_fields = {"password_hash", "salt", "api_key_secret", "webhook_secret"}

        # Remove sensitive fields for non-admin scopes
        if not context.can_access_all_tenants():
            sanitized = {k: v for k, v in data.items() if k not in sensitive_fields}
            return sanitized

        return data

    def check_data_ownership(
        self,
        resource_id: str,
        tenant_id: str,
        table: str = "tenant_resources",
    ) -> Tuple[bool, Optional[str]]:
        """Check if a resource belongs to a tenant.

        Args:
            resource_id: Resource ID
            tenant_id: Tenant ID
            table: Table name

        Returns:
            Tuple of (is_owner, reason)
        """
        row = db.query_one(
            f"SELECT tenant_id FROM {table} WHERE resource_id = ?",
            (resource_id,),
        )

        if not row:
            return False, "Resource not found"

        if row["tenant_id"] != tenant_id:
            return False, "Resource belongs to different tenant"

        return True, None


# Global manager instance
_data_isolation_manager = DataIsolationManager()


def get_data_isolation_manager() -> DataIsolationManager:
    """Get the global data isolation manager instance."""
    return _data_isolation_manager


def create_data_access_context(
    tenant_id: Optional[str],
    scope: Optional[str],
    user_id: Optional[int],
    is_admin: bool = False,
    is_owner: bool = False,
) -> DataAccessContext:
    """Create a data access context.

    Args:
        tenant_id: Tenant ID
        scope: Scope
        user_id: User ID
        is_admin: Admin flag
        is_owner: Owner flag

    Returns:
        DataAccessContext
    """
    return DataAccessContext(
        tenant_id=tenant_id,
        scope=scope,
        user_id=user_id,
        is_admin=is_admin,
        is_owner=is_owner,
    )


def query_with_tenant_isolation(
    query: str,
    params: Tuple,
    context: DataAccessContext,
    tenant_column: str = "tenant_id",
) -> List[Dict[str, Any]]:
    """Execute a query with tenant isolation.

    Args:
        query: SQL query
        params: Query parameters
        context: Data access context
        tenant_column: Column name for tenant ID

    Returns:
        Query results
    """
    manager = get_data_isolation_manager()
    filtered_query, filtered_params = manager.apply_tenant_filter(
        query, params, context, tenant_column
    )
    return db.query(filtered_query, filtered_params)


def query_one_with_tenant_isolation(
    query: str,
    params: Tuple,
    context: DataAccessContext,
    tenant_column: str = "tenant_id",
) -> Optional[Dict[str, Any]]:
    """Execute a single-row query with tenant isolation.

    Args:
        query: SQL query
        params: Query parameters
        context: Data access context
        tenant_column: Column name for tenant ID

    Returns:
        Query result or None
    """
    manager = get_data_isolation_manager()
    filtered_query, filtered_params = manager.apply_tenant_filter(
        query, params, context, tenant_column
    )
    return db.query_one(filtered_query, filtered_params)
