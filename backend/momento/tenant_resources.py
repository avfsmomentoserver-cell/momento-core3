"""Tenant-specific resource management for multi-tenant data isolation.

This module implements:
- Tenant-scoped data isolation
- Resource ownership tracking
- Cross-tenant resource sharing
- Tenant quota management
- Resource lifecycle management
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum

from . import db
from .scope_communication import check_cross_scope_access
from .multi_scope_schema import SCOPES


class ResourceType(str, Enum):
    """Types of tenant resources."""

    ROUND_DATA = "round_data"
    ANALYSIS_RESULT = "analysis_result"
    FORECAST_MODEL = "forecast_model"
    VOCABULARY = "vocabulary"
    PATTERN = "pattern"
    CUSTOM_FEATURE = "custom_feature"
    API_KEY = "api_key"
    WEBHOOK = "webhook"
    EXPORT = "export"
    REPORT = "report"


class ResourceVisibility(str, Enum):
    """Resource visibility levels."""

    PRIVATE = "private"  # Only tenant owner
    SHARED = "shared"  # Shared with approved tenants
    PUBLIC = "public"  # Available to all scopes (read-only)


class TenantResourceManager:
    """Manager for tenant-specific resources with isolation."""

    def __init__(self):
        self._resource_cache: Dict[str, Dict[str, Any]] = {}

    def create_resource(
        self,
        tenant_id: str,
        resource_type: ResourceType,
        name: str,
        data: Dict[str, Any],
        visibility: ResourceVisibility = ResourceVisibility.PRIVATE,
        owner_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new tenant-scoped resource.

        Args:
            tenant_id: Tenant ID
            resource_type: Type of resource
            name: Resource name
            data: Resource data
            visibility: Resource visibility level
            owner_id: Optional user ID of owner
            metadata: Optional metadata

        Returns:
            Resource dictionary
        """
        resource_id = f"res_{uuid.uuid4().hex[:16]}"
        now = datetime.now(timezone.utc).isoformat()

        db.execute(
            """INSERT INTO tenant_resources 
               (resource_id, tenant_id, resource_type, name, data, visibility, owner_id, metadata, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                resource_id,
                tenant_id,
                resource_type.value,
                name,
                json.dumps(data),
                visibility.value,
                owner_id,
                json.dumps(metadata or {}),
                now,
                now,
            ),
        )

        return self.get_resource(resource_id)

    def get_resource(self, resource_id: str) -> Optional[Dict[str, Any]]:
        """Get a resource by ID.

        Args:
            resource_id: Resource ID

        Returns:
            Resource dictionary or None
        """
        row = db.query_one(
            "SELECT * FROM tenant_resources WHERE resource_id = ?",
            (resource_id,),
        )

        if not row:
            return None

        return {
            "resource_id": row["resource_id"],
            "tenant_id": row["tenant_id"],
            "resource_type": row["resource_type"],
            "name": row["name"],
            "data": json.loads(row.get("data", "{}")),
            "visibility": row["visibility"],
            "owner_id": row["owner_id"],
            "metadata": json.loads(row.get("metadata", "{}")),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def check_access(
        self,
        resource_id: str,
        requesting_tenant_id: str,
        requesting_scope: str,
        action: str = "read",
    ) -> Tuple[bool, Optional[str]]:
        """Check if a tenant can access a resource.

        Args:
            resource_id: Resource ID
            requesting_tenant_id: Requesting tenant ID
            requesting_scope: Requesting scope
            action: Action being performed (read, write, delete)

        Returns:
            Tuple of (allowed, reason)
        """
        resource = self.get_resource(resource_id)
        if not resource:
            return False, "Resource not found"

        # Owner always has full access
        if resource["tenant_id"] == requesting_tenant_id:
            return True, None

        # Check visibility
        visibility = resource["visibility"]

        if visibility == ResourceVisibility.PRIVATE.value:
            # Private resources are only accessible by owner
            return False, "Private resource - owner access only"

        elif visibility == ResourceVisibility.SHARED.value:
            # Check if resource is shared with requesting tenant
            is_shared = db.query_one(
                """SELECT 1 FROM resource_shares
                   WHERE resource_id = ? AND target_tenant_id = ? AND approved = 1""",
                (resource_id, requesting_tenant_id),
            )

            if not is_shared:
                return False, "Resource not shared with this tenant"

            # Check write permissions
            if action in ["write", "delete"]:
                return False, "Read-only access to shared resource"

            return True, None

        elif visibility == ResourceVisibility.PUBLIC.value:
            # Public resources are read-only for all scopes
            if action in ["write", "delete"]:
                return False, "Read-only access to public resource"

            return True, None

        return False, "Access denied"

    def list_resources(
        self,
        tenant_id: str,
        resource_type: Optional[ResourceType] = None,
        visibility: Optional[ResourceVisibility] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List resources for a tenant.

        Args:
            tenant_id: Tenant ID
            resource_type: Optional filter by resource type
            visibility: Optional filter by visibility
            limit: Maximum number of results

        Returns:
            List of resource dictionaries
        """
        query = "SELECT * FROM tenant_resources WHERE tenant_id = ?"
        params = [tenant_id]

        if resource_type:
            query += " AND resource_type = ?"
            params.append(resource_type.value)

        if visibility:
            query += " AND visibility = ?"
            params.append(visibility.value)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(max(1, min(int(limit), 1000)))

        rows = db.query(query, tuple(params))
        return [self.get_resource(row["resource_id"]) for row in rows]

    def update_resource(
        self,
        resource_id: str,
        tenant_id: str,
        data: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
        visibility: Optional[ResourceVisibility] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update a resource.

        Args:
            resource_id: Resource ID
            tenant_id: Tenant ID (for ownership check)
            data: New data
            name: New name
            visibility: New visibility
            metadata: New metadata

        Returns:
            Updated resource dictionary or None
        """
        # Check ownership
        resource = self.get_resource(resource_id)
        if not resource or resource["tenant_id"] != tenant_id:
            return None

        updates = []
        params = []

        if data is not None:
            updates.append("data = ?")
            params.append(json.dumps(data))

        if name is not None:
            updates.append("name = ?")
            params.append(name)

        if visibility is not None:
            updates.append("visibility = ?")
            params.append(visibility.value)

        if metadata is not None:
            updates.append("metadata = ?")
            params.append(json.dumps(metadata))

        if not updates:
            return resource

        updates.append("updated_at = ?")
        params.append(datetime.now(timezone.utc).isoformat())
        params.append(resource_id)

        db.execute(
            f"UPDATE tenant_resources SET {', '.join(updates)} WHERE resource_id = ?",
            tuple(params),
        )

        return self.get_resource(resource_id)

    def delete_resource(self, resource_id: str, tenant_id: str) -> bool:
        """Delete a resource.

        Args:
            resource_id: Resource ID
            tenant_id: Tenant ID (for ownership check)

        Returns:
            True if deleted, False otherwise
        """
        resource = self.get_resource(resource_id)
        if not resource or resource["tenant_id"] != tenant_id:
            return False

        db.execute("DELETE FROM tenant_resources WHERE resource_id = ?", (resource_id,))
        return True

    def share_resource(
        self,
        resource_id: str,
        source_tenant_id: str,
        target_tenant_id: str,
        permissions: List[str],
    ) -> bool:
        """Share a resource with another tenant.

        Args:
            resource_id: Resource ID
            source_tenant_id: Source tenant ID
            target_tenant_id: Target tenant ID
            permissions: List of permissions (read, write, etc.)

        Returns:
            True if shared, False otherwise
        """
        # Check ownership
        resource = self.get_resource(resource_id)
        if not resource or resource["tenant_id"] != source_tenant_id:
            return False

        # Check cross-scope access
        source_tenant = db.query_one("SELECT scope FROM tenants WHERE tenant_id = ?", (source_tenant_id,))
        target_tenant = db.query_one("SELECT scope FROM tenants WHERE tenant_id = ?", (target_tenant_id,))

        if not source_tenant or not target_tenant:
            return False

        allowed, _ = check_cross_scope_access(
            source_scope=source_tenant["scope"],
            target_scope=target_tenant["scope"],
            resource="resource",
            action="share",
        )

        if not allowed:
            return False

        # Create share record
        share_id = f"share_{uuid.uuid4().hex[:16]}"
        now = datetime.now(timezone.utc).isoformat()

        db.execute(
            """INSERT INTO resource_shares 
               (share_id, resource_id, source_tenant_id, target_tenant_id, permissions, approved, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                share_id,
                resource_id,
                source_tenant_id,
                target_tenant_id,
                json.dumps(permissions),
                1,  # Auto-approve for now
                now,
            ),
        )

        return True

    def get_tenant_quota(self, tenant_id: str) -> Dict[str, Any]:
        """Get tenant resource quota and usage.

        Args:
            tenant_id: Tenant ID

        Returns:
            Quota dictionary with usage
        """
        tenant = db.query_one("SELECT scope, settings FROM tenants WHERE tenant_id = ?", (tenant_id,))
        if not tenant:
            return {}

        scope_config = SCOPES.get(tenant["scope"], {})
        settings = json.loads(tenant.get("settings", "{}"))

        # Get quota from settings or scope defaults
        quota = settings.get("quota", {})
        if not quota:
            # Default quotas based on scope
            if tenant["scope"] == "my_scope":
                quota = {"resources": float("inf"), "storage": float("inf"), "api_calls": float("inf")}
            elif tenant["scope"] == "admin_scope":
                quota = {"resources": 10000, "storage": 1000000, "api_calls": 100000}
            elif tenant["scope"] == "fx_user_scope":
                quota = {"resources": 5000, "storage": 500000, "api_calls": 50000}
            elif tenant["scope"] == "big_better_scope":
                quota = {"resources": 2000, "storage": 200000, "api_calls": 20000}
            elif tenant["scope"] == "regular_low_budget_scope":
                quota = {"resources": 500, "storage": 50000, "api_calls": 5000}
            else:
                quota = {"resources": 100, "storage": 10000, "api_calls": 1000}

        # Get current usage
        resource_count = db.query_one(
            "SELECT COUNT(*) as c FROM tenant_resources WHERE tenant_id = ?",
            (tenant_id,),
        )

        usage = {
            "resources": int(resource_count["c"]) if resource_count else 0,
            "storage": 0,  # TODO: Calculate actual storage
            "api_calls": 0,  # TODO: Track API calls
        }

        return {
            "tenant_id": tenant_id,
            "scope": tenant["scope"],
            "quota": quota,
            "usage": usage,
            "remaining": {
                key: max(0, quota[key] - usage[key]) if quota[key] != float("inf") else float("inf")
                for key in quota
            },
        }

    def check_quota_exceeded(self, tenant_id: str, resource_type: ResourceType) -> Tuple[bool, Optional[str]]:
        """Check if tenant has exceeded quota for a resource type.

        Args:
            tenant_id: Tenant ID
            resource_type: Resource type being created

        Returns:
            Tuple of (exceeded, reason)
        """
        quota_info = self.get_tenant_quota(tenant_id)
        if not quota_info:
            return False, None

        quota = quota_info["quota"]
        usage = quota_info["usage"]
        remaining = quota_info["remaining"]

        if resource_type == ResourceType.ROUND_DATA:
            if remaining["resources"] <= 0:
                return True, "Resource quota exceeded"

        return False, None


# Global resource manager instance
_resource_manager = TenantResourceManager()


def get_resource_manager() -> TenantResourceManager:
    """Get the global resource manager instance."""
    return _resource_manager


def create_tenant_resources_table() -> None:
    """Create tenant resources table if not exists."""
    db.execute(
        """CREATE TABLE IF NOT EXISTS tenant_resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resource_id TEXT NOT NULL UNIQUE,
            tenant_id TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            name TEXT NOT NULL,
            data TEXT NOT NULL,
            visibility TEXT NOT NULL DEFAULT 'private',
            owner_id INTEGER,
            metadata TEXT DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
            FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE SET NULL
        )"""
    )

    db.execute(
        """CREATE TABLE IF NOT EXISTS resource_shares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            share_id TEXT NOT NULL UNIQUE,
            resource_id TEXT NOT NULL,
            source_tenant_id TEXT NOT NULL,
            target_tenant_id TEXT NOT NULL,
            permissions TEXT NOT NULL,
            approved INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (resource_id) REFERENCES tenant_resources(resource_id) ON DELETE CASCADE,
            FOREIGN KEY (source_tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
            FOREIGN KEY (target_tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
        )"""
    )

    # Create indexes
    db.execute("CREATE INDEX IF NOT EXISTS idx_tenant_resources_tenant ON tenant_resources (tenant_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_tenant_resources_type ON tenant_resources (resource_type)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_tenant_resources_visibility ON tenant_resources (visibility)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_resource_shares_resource ON resource_shares (resource_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_resource_shares_target ON resource_shares (target_tenant_id)")
