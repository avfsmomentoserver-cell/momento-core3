"""Tenant management for multi-tenant data isolation.

This module implements:
- Tenant lifecycle management (create, update, delete)
- Tenant-scoped data isolation
- Tenant configuration management
- User-tenant relationship management
- Tenant health monitoring
"""

from __future__ import annotations

import json
import secrets
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from . import db
from .scope_authorization import IntegrityError
from .multi_scope_schema import SCOPES


class TenantManager:
    """Manager for tenant operations and data isolation."""
    
    @staticmethod
    def create_tenant(
        name: str,
        scope: str,
        display_name: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
        role: str = "owner",
    ) -> Dict[str, Any]:
        """Create a new tenant.
        
        Args:
            name: Internal tenant name
            scope: Tenant scope (must be in SCOPES)
            display_name: Human-readable display name
            settings: Tenant-specific settings
            user_id: User ID to assign as owner
            role: User's role in tenant (default: owner)
            
        Returns:
            Tenant dictionary
            
        Raises:
            ValueError: If scope is invalid
        """
        if scope not in SCOPES:
            raise ValueError(f"Invalid scope: {scope}")
        
        tenant_id = f"tenant_{uuid.uuid4().hex[:16]}"
        now = datetime.now(timezone.utc).isoformat()
        
        db.execute(
            """INSERT INTO tenants (tenant_id, name, display_name, scope, status, settings, created_at, updated_at)
               VALUES (?, ?, ?, ?, 'active', ?, ?, ?)""",
            (
                tenant_id,
                name,
                display_name or name,
                scope,
                json.dumps(settings or {}),
                now,
                now,
            ),
        )
        
        # Assign user to tenant if provided
        if user_id:
            TenantManager.assign_user_to_tenant(
                user_id=user_id,
                tenant_id=tenant_id,
                role=role,
                is_primary=True,
            )
        
        return TenantManager.get_tenant(tenant_id)
    
    @staticmethod
    def get_tenant(tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get tenant by ID.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            Tenant dictionary or None
        """
        row = db.query_one(
            "SELECT * FROM tenants WHERE tenant_id = ?",
            (tenant_id,),
        )
        
        if not row:
            return None
        
        return {
            "tenant_id": row["tenant_id"],
            "name": row["name"],
            "display_name": row["display_name"],
            "scope": row["scope"],
            "status": row["status"],
            "settings": json.loads(row.get("settings", "{}")),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
    
    @staticmethod
    def get_tenant_by_name(name: str) -> Optional[Dict[str, Any]]:
        """Get tenant by name.
        
        Args:
            name: Tenant name
            
        Returns:
            Tenant dictionary or None
        """
        row = db.query_one(
            "SELECT * FROM tenants WHERE name = ?",
            (name,),
        )
        
        if not row:
            return None
        
        return TenantManager.get_tenant(row["tenant_id"])
    
    @staticmethod
    def list_tenants(
        scope: Optional[str] = None,
        status: str = "active",
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List tenants with optional filters.
        
        Args:
            scope: Filter by scope
            status: Filter by status (default: active)
            limit: Maximum number of results
            
        Returns:
            List of tenant dictionaries
        """
        query = "SELECT * FROM tenants WHERE status = ?"
        params = [status]
        
        if scope:
            query += " AND scope = ?"
            params.append(scope)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(max(1, min(int(limit), 1000)))
        
        rows = db.query(query, tuple(params))
        return [TenantManager.get_tenant(row["tenant_id"]) for row in rows]
    
    @staticmethod
    def update_tenant(
        tenant_id: str,
        name: Optional[str] = None,
        display_name: Optional[str] = None,
        status: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update tenant information.
        
        Args:
            tenant_id: Tenant ID
            name: New name
            display_name: New display name
            status: New status
            settings: New settings
            
        Returns:
            Updated tenant dictionary or None
        """
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        
        if display_name is not None:
            updates.append("display_name = ?")
            params.append(display_name)
        
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        
        if settings is not None:
            updates.append("settings = ?")
            params.append(json.dumps(settings))
        
        if not updates:
            return TenantManager.get_tenant(tenant_id)
        
        updates.append("updated_at = ?")
        params.append(datetime.now(timezone.utc).isoformat())
        params.append(tenant_id)
        
        db.execute(
            f"UPDATE tenants SET {', '.join(updates)} WHERE tenant_id = ?",
            tuple(params),
        )
        
        return TenantManager.get_tenant(tenant_id)
    
    @staticmethod
    def delete_tenant(tenant_id: str) -> bool:
        """Delete a tenant (cascades to user_tenants, subscriptions, etc.).
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            True if deleted, False otherwise
        """
        row = db.query_one("SELECT id FROM tenants WHERE tenant_id = ?", (tenant_id,))
        if not row:
            return False
        
        db.execute("DELETE FROM tenants WHERE tenant_id = ?", (tenant_id,))
        return True
    
    @staticmethod
    def assign_user_to_tenant(
        user_id: int,
        tenant_id: str,
        role: str = "member",
        is_primary: bool = False,
    ) -> Dict[str, Any]:
        """Assign a user to a tenant.
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID
            role: User's role in tenant
            is_primary: Whether this is the user's primary tenant
            
        Returns:
            User-tenant relationship dictionary
        """
        now = datetime.now(timezone.utc).isoformat()
        
        # If setting as primary, unset primary for other tenants
        if is_primary:
            db.execute(
                "UPDATE user_tenants SET is_primary = 0 WHERE user_id = ?",
                (user_id,),
            )
        
        try:
            db.execute(
                """INSERT INTO user_tenants (user_id, tenant_id, role, is_primary, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, tenant_id, role, 1 if is_primary else 0, now),
            )
        except sqlite3.IntegrityError:
            # Relationship already exists, update it
            db.execute(
                """UPDATE user_tenants 
                   SET role = ?, is_primary = ?
                   WHERE user_id = ? AND tenant_id = ?""",
                (role, 1 if is_primary else 0, user_id, tenant_id),
            )
        
        return TenantManager.get_user_tenant_relationship(user_id, tenant_id)
    
    @staticmethod
    def get_user_tenant_relationship(user_id: int, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get user-tenant relationship.
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID
            
        Returns:
            Relationship dictionary or None
        """
        row = db.query_one(
            """SELECT ut.*, t.name as tenant_name, t.scope as tenant_scope
               FROM user_tenants ut
               JOIN tenants t ON ut.tenant_id = t.tenant_id
               WHERE ut.user_id = ? AND ut.tenant_id = ?""",
            (user_id, tenant_id),
        )
        
        if not row:
            return None
        
        return {
            "user_id": row["user_id"],
            "tenant_id": row["tenant_id"],
            "tenant_name": row["tenant_name"],
            "tenant_scope": row["tenant_scope"],
            "role": row["role"],
            "is_primary": bool(row["is_primary"]),
            "created_at": row["created_at"],
        }
    
    @staticmethod
    def get_user_tenants(user_id: int) -> List[Dict[str, Any]]:
        """Get all tenants for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of tenant relationship dictionaries
        """
        rows = db.query(
            """SELECT ut.*, t.name as tenant_name, t.display_name, t.scope, t.status
               FROM user_tenants ut
               JOIN tenants t ON ut.tenant_id = t.tenant_id
               WHERE ut.user_id = ?
               ORDER BY ut.is_primary DESC, t.created_at DESC""",
            (user_id,),
        )
        
        return [
            {
                "tenant_id": row["tenant_id"],
                "name": row["tenant_name"],
                "display_name": row["display_name"],
                "scope": row["scope"],
                "status": row["status"],
                "role": row["role"],
                "is_primary": bool(row["is_primary"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]
    
    @staticmethod
    def get_tenant_users(tenant_id: str) -> List[Dict[str, Any]]:
        """Get all users for a tenant.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            List of user relationship dictionaries
        """
        rows = db.query(
            """SELECT ut.*, u.email, u.display_name as user_display_name, u.role as user_role
               FROM user_tenants ut
               JOIN users u ON ut.user_id = u.id
               WHERE ut.tenant_id = ?
               ORDER BY ut.is_primary DESC, ut.created_at DESC""",
            (tenant_id,),
        )
        
        return [
            {
                "user_id": row["user_id"],
                "email": row["email"],
                "display_name": row["user_display_name"],
                "user_role": row["user_role"],
                "tenant_role": row["role"],
                "is_primary": bool(row["is_primary"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]
    
    @staticmethod
    def remove_user_from_tenant(user_id: int, tenant_id: str) -> bool:
        """Remove a user from a tenant.
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID
            
        Returns:
            True if removed, False otherwise
        """
        row = db.query_one(
            "SELECT id FROM user_tenants WHERE user_id = ? AND tenant_id = ?",
            (user_id, tenant_id),
        )
        if not row:
            return False
        
        db.execute(
            "DELETE FROM user_tenants WHERE user_id = ? AND tenant_id = ?",
            (user_id, tenant_id),
        )
        return True
    
    @staticmethod
    def get_tenant_stats(tenant_id: str) -> Dict[str, Any]:
        """Get statistics for a tenant.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            Statistics dictionary
        """
        # User count
        user_count = db.query_one(
            "SELECT COUNT(*) AS c FROM user_tenants WHERE tenant_id = ?",
            (tenant_id,),
        )
        
        # Active subscription
        subscription = db.query_one(
            """SELECT * FROM subscriptions 
               WHERE tenant_id = ? AND status = 'active' 
               ORDER BY created_at DESC LIMIT 1""",
            (tenant_id,),
        )
        
        # Usage metrics (last 30 days)
        usage = db.query(
            """SELECT metric, SUM(value) as total
               FROM usage_tracking
               WHERE tenant_id = ? AND recorded_at >= datetime('now', '-30 days')
               GROUP BY metric""",
            (tenant_id,),
        )
        
        return {
            "tenant_id": tenant_id,
            "user_count": int(user_count["c"]) if user_count else 0,
            "has_active_subscription": subscription is not None,
            "subscription": subscription,
            "usage_metrics": {row["metric"]: row["total"] for row in usage},
        }
    
    @staticmethod
    def is_tenant_active(tenant_id: str) -> bool:
        """Check if a tenant is active.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            True if active, False otherwise
        """
        tenant = TenantManager.get_tenant(tenant_id)
        return tenant is not None and tenant["status"] == "active"
    
    @staticmethod
    def get_tenant_scope(tenant_id: str) -> Optional[str]:
        """Get a tenant's scope.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            Scope name or None
        """
        tenant = TenantManager.get_tenant(tenant_id)
        return tenant["scope"] if tenant else None


# Convenience functions for data isolation
def with_tenant_filter(query: str, tenant_id: str, table: str = "rounds") -> str:
    """Add tenant filter to a query for data isolation.
    
    Args:
        query: Original query
        tenant_id: Tenant ID
        table: Table name (default: rounds)
        
    Returns:
        Query with tenant filter
    """
    # Add tenant_id column filter
    if "WHERE" in query.upper():
        return query + f" AND {table}.tenant_id = ?"
    else:
        return query + f" WHERE {table}.tenant_id = ?"


def get_tenant_data(
    table: str,
    tenant_id: str,
    columns: str = "*",
    where: Optional[str] = None,
    params: Optional[tuple] = None,
    limit: Optional[int] = None,
    order_by: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Get data for a specific tenant with isolation.
    
    Args:
        table: Table name
        tenant_id: Tenant ID
        columns: Columns to select (default: *)
        where: Additional WHERE clause (without tenant filter)
        params: Parameters for WHERE clause
        limit: Optional LIMIT
        order_by: Optional ORDER BY
        
    Returns:
        List of row dictionaries
    """
    query = f"SELECT {columns} FROM {table}"
    query_params = []
    
    # Add tenant filter
    query += " WHERE tenant_id = ?"
    query_params.append(tenant_id)
    
    # Add additional conditions
    if where:
        query += f" AND {where}"
        if params:
            query_params.extend(params)
    
    # Add ordering
    if order_by:
        query += f" ORDER BY {order_by}"
    
    # Add limit
    if limit:
        query += " LIMIT ?"
        query_params.append(limit)
    
    return db.query(query, tuple(query_params))


def count_tenant_data(table: str, tenant_id: str, where: Optional[str] = None, params: Optional[tuple] = None) -> int:
    """Count data for a specific tenant with isolation.
    
    Args:
        table: Table name
        tenant_id: Tenant ID
        where: Additional WHERE clause
        params: Parameters for WHERE clause
        
    Returns:
        Count of rows
    """
    query = f"SELECT COUNT(*) AS c FROM {table} WHERE tenant_id = ?"
    query_params = [tenant_id]
    
    if where:
        query += f" AND {where}"
        if params:
            query_params.extend(params)
    
    row = db.query_one(query, tuple(query_params))
    return int(row["c"]) if row else 0
