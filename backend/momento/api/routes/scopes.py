"""Scope management API routes for V5 multi-scope architecture.

This module provides endpoints for:
- Scope information and configuration
- Tenant management
- Cross-scope communication policies
- Resource access controls
- Subscription enforcement
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from ... import db
from ...scope_auth import (
    create_api_key,
    get_tenant_context,
    get_user_primary_tenant,
    issue_scope_token,
    revoke_api_key,
    validate_api_key,
)
from ...scope_authorization import has_permission
from ...scope_communication import (
    CommunicationPolicy,
    CommunicationType,
    get_communication_policy,
)
from ...tenant_manager import TenantManager
from ...tenant_resources import (
    ResourceType,
    ResourceVisibility,
    get_resource_manager,
)
from ...multi_scope_schema import SCOPES
from ..scope_gateway import get_tenant_context, require_scope, require_permission

router = APIRouter(prefix="/scopes", tags=["scopes"])


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------


class ScopeInfo(BaseModel):
    """Scope information."""

    scope_id: str
    name: str
    description: str
    tier: str
    rate_limit: Optional[int] = None
    api_access: str
    features: List[str]


class TenantInfo(BaseModel):
    """Tenant information."""

    tenant_id: str
    name: str
    display_name: str
    scope: str
    status: str
    user_count: int
    settings: Dict[str, Any]


class CreateTenantRequest(BaseModel):
    """Request to create a tenant."""

    name: str = Field(..., min_length=1, max_length=100)
    scope: str = Field(..., description="Scope for the tenant")
    display_name: Optional[str] = Field(None, max_length=200)
    settings: Optional[Dict[str, Any]] = None
    user_id: Optional[int] = None
    role: str = Field(default="owner")


class UpdateTenantRequest(BaseModel):
    """Request to update a tenant."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    display_name: Optional[str] = Field(None, max_length=200)
    status: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


class CommunicationPolicyRequest(BaseModel):
    """Request to set communication policy."""

    source_scope: str
    target_scope: str
    allowed: bool
    communication_types: List[str]
    requires_approval: bool = False
    rate_limit_multiplier: float = 1.0
    audit_required: bool = True


class APIKeyRequest(BaseModel):
    """Request to create an API key."""

    name: str = Field(..., min_length=1, max_length=100)
    permissions: Optional[Dict[str, Any]] = None
    expires_at: Optional[str] = None


class APIKeyResponse(BaseModel):
    """API key response."""

    key_id: str
    key: str
    name: str
    scope: str
    permissions: Dict[str, Any]
    expires_at: Optional[str]
    created_at: str


# ---------------------------------------------------------------------------
# Scope Information Endpoints
# ---------------------------------------------------------------------------


@router.get("/info", response_model=List[ScopeInfo])
async def list_scopes(
    context: Any = Depends(get_tenant_context),
) -> List[ScopeInfo]:
    """List all available scopes.

    Requires authentication. Returns scope configuration for all scopes.
    """
    scopes = []
    for scope_id, config in SCOPES.items():
        scopes.append(
            ScopeInfo(
                scope_id=scope_id,
                name=config["name"],
                description=config["description"],
                tier=config["tier"],
                rate_limit=config.get("rate_limit"),
                api_access=config["api_access"],
                features=config["features"],
            )
        )
    return scopes


@router.get("/info/{scope_id}", response_model=ScopeInfo)
async def get_scope_info(
    scope_id: str,
    context: Any = Depends(get_tenant_context),
) -> ScopeInfo:
    """Get information about a specific scope."""
    if scope_id not in SCOPES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scope not found: {scope_id}",
        )

    config = SCOPES[scope_id]
    return ScopeInfo(
        scope_id=scope_id,
        name=config["name"],
        description=config["description"],
        tier=config["tier"],
        rate_limit=config.get("rate_limit"),
        api_access=config["api_access"],
        features=config["features"],
    )


# ---------------------------------------------------------------------------
# Tenant Management Endpoints
# ---------------------------------------------------------------------------


@router.post("/tenants", response_model=TenantInfo, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    request: CreateTenantRequest,
    context: Any = Depends(require_permission("tenants", "create")),
) -> TenantInfo:
    """Create a new tenant.

    Requires 'tenants:create' permission.
    """
    if request.scope not in SCOPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scope: {request.scope}",
        )

    tenant = TenantManager.create_tenant(
        name=request.name,
        scope=request.scope,
        display_name=request.display_name,
        settings=request.settings,
        user_id=request.user_id,
        role=request.role,
    )

    return TenantInfo(
        tenant_id=tenant["tenant_id"],
        name=tenant["name"],
        display_name=tenant["display_name"],
        scope=tenant["scope"],
        status=tenant["status"],
        user_count=0,
        settings=tenant["settings"],
    )


@router.get("/tenants", response_model=List[TenantInfo])
async def list_tenants(
    scope: Optional[str] = None,
    status: str = "active",
    limit: int = Query(default=100, ge=1, le=1000),
    context: Any = Depends(require_permission("tenants", "read")),
) -> List[TenantInfo]:
    """List tenants with optional filters.

    Requires 'tenants:read' permission.
    """
    tenants = TenantManager.list_tenants(scope=scope, status=status, limit=limit)

    result = []
    for tenant in tenants:
        user_count = db.query_one(
            "SELECT COUNT(*) as c FROM user_tenants WHERE tenant_id = ?",
            (tenant["tenant_id"],),
        )

        result.append(
            TenantInfo(
                tenant_id=tenant["tenant_id"],
                name=tenant["name"],
                display_name=tenant["display_name"],
                scope=tenant["scope"],
                status=tenant["status"],
                user_count=int(user_count["c"]) if user_count else 0,
                settings=tenant["settings"],
            )
        )

    return result


@router.get("/tenants/{tenant_id}", response_model=TenantInfo)
async def get_tenant(
    tenant_id: str,
    context: Any = Depends(require_permission("tenants", "read")),
) -> TenantInfo:
    """Get a specific tenant by ID.

    Requires 'tenants:read' permission.
    """
    tenant = TenantManager.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant not found: {tenant_id}",
        )

    user_count = db.query_one(
        "SELECT COUNT(*) as c FROM user_tenants WHERE tenant_id = ?",
        (tenant_id,),
    )

    return TenantInfo(
        tenant_id=tenant["tenant_id"],
        name=tenant["name"],
        display_name=tenant["display_name"],
        scope=tenant["scope"],
        status=tenant["status"],
        user_count=int(user_count["c"]) if user_count else 0,
        settings=tenant["settings"],
    )


@router.put("/tenants/{tenant_id}", response_model=TenantInfo)
async def update_tenant(
    tenant_id: str,
    request: UpdateTenantRequest,
    context: Any = Depends(require_permission("tenants", "update")),
) -> TenantInfo:
    """Update a tenant.

    Requires 'tenants:update' permission.
    """
    tenant = TenantManager.update_tenant(
        tenant_id=tenant_id,
        name=request.name,
        display_name=request.display_name,
        status=request.status,
        settings=request.settings,
    )

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant not found: {tenant_id}",
        )

    user_count = db.query_one(
        "SELECT COUNT(*) as c FROM user_tenants WHERE tenant_id = ?",
        (tenant_id,),
    )

    return TenantInfo(
        tenant_id=tenant["tenant_id"],
        name=tenant["name"],
        display_name=tenant["display_name"],
        scope=tenant["scope"],
        status=tenant["status"],
        user_count=int(user_count["c"]) if user_count else 0,
        settings=tenant["settings"],
    )


@router.delete("/tenants/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: str,
    context: Any = Depends(require_permission("tenants", "delete")),
) -> None:
    """Delete a tenant.

    Requires 'tenants:delete' permission.
    """
    success = TenantManager.delete_tenant(tenant_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant not found: {tenant_id}",
        )


# ---------------------------------------------------------------------------
# Cross-Scope Communication Policy Endpoints
# ---------------------------------------------------------------------------


@router.get("/policies")
async def list_communication_policies(
    source_scope: Optional[str] = None,
    context: Any = Depends(require_permission("system", "read")),
) -> List[Dict[str, Any]]:
    """List cross-scope communication policies.

    Requires 'system:read' permission.
    """
    policy_manager = get_communication_policy()
    policies = policy_manager.list_policies(source_scope=source_scope)

    return [
        {
            "source_scope": p.source_scope,
            "target_scope": p.target_scope,
            "allowed": p.allowed,
            "direction": p.direction.value,
            "communication_types": [ct.value for ct in p.communication_types],
            "requires_approval": p.requires_approval,
            "rate_limit_multiplier": p.rate_limit_multiplier,
            "audit_required": p.audit_required,
        }
        for p in policies
    ]


@router.post("/policies", status_code=status.HTTP_201_CREATED)
async def create_communication_policy(
    request: CommunicationPolicyRequest,
    context: Any = Depends(require_permission("system", "admin")),
) -> Dict[str, Any]:
    """Create or update a cross-scope communication policy.

    Requires 'system:admin' permission.
    """
    policy_manager = get_communication_policy()

    # Convert communication types to enum
    comm_types = set()
    for ct in request.communication_types:
        try:
            comm_types.add(CommunicationType(ct))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid communication type: {ct}",
            )

    policy = CommunicationPolicy(
        source_scope=request.source_scope,
        target_scope=request.target_scope,
        allowed=request.allowed,
        direction=policy_manager.get_communication_direction(
            request.source_scope, request.target_scope
        ),
        communication_types=comm_types,
        requires_approval=request.requires_approval,
        rate_limit_multiplier=request.rate_limit_multiplier,
        audit_required=request.audit_required,
    )

    policy_manager.add_policy(policy)

    return {
        "source_scope": policy.source_scope,
        "target_scope": policy.target_scope,
        "allowed": policy.allowed,
        "direction": policy.direction.value,
        "communication_types": [ct.value for ct in policy.communication_types],
        "requires_approval": policy.requires_approval,
        "rate_limit_multiplier": policy.rate_limit_multiplier,
        "audit_required": policy.audit_required,
    }


@router.delete("/policies/{source_scope}/{target_scope}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_communication_policy(
    source_scope: str,
    target_scope: str,
    context: Any = Depends(require_permission("system", "admin")),
) -> None:
    """Delete a cross-scope communication policy.

    Requires 'system:admin' permission.
    """
    policy_manager = get_communication_policy()
    success = policy_manager.remove_policy(source_scope, target_scope)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found",
        )


@router.get("/policies/check")
async def check_cross_scope_access(
    source_scope: str = Query(...),
    target_scope: str = Query(...),
    resource: str = Query(...),
    action: str = Query(...),
    context: Any = Depends(get_tenant_context),
) -> Dict[str, Any]:
    """Check if cross-scope access is allowed.

    Requires authentication.
    """
    from ...scope_communication import check_cross_scope_access

    allowed, reason = check_cross_scope_access(
        source_scope=source_scope,
        target_scope=target_scope,
        resource=resource,
        action=action,
    )

    return {
        "allowed": allowed,
        "reason": reason,
        "source_scope": source_scope,
        "target_scope": target_scope,
        "resource": resource,
        "action": action,
    }


# ---------------------------------------------------------------------------
# API Key Management Endpoints
# ---------------------------------------------------------------------------


@router.post("/api-keys", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: APIKeyRequest,
    context: Any = Depends(get_tenant_context),
) -> APIKeyResponse:
    """Create an API key for the current tenant.

    Requires authentication.
    """
    if not context.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No tenant associated with user",
        )

    key = create_api_key(
        user_id=context.user_id,
        tenant_id=context.tenant_id,
        name=request.name,
        permissions=request.permissions,
        expires_at=request.expires_at,
    )

    return APIKeyResponse(
        key_id=key.split(".")[0],
        key=key,
        name=request.name,
        scope=context.scope,
        permissions=request.permissions or {},
        expires_at=request.expires_at,
        created_at=db.utc_now(),
    )


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key_endpoint(
    key_id: str,
    context: Any = Depends(get_tenant_context),
) -> None:
    """Revoke an API key.

    Requires authentication.
    """
    # Verify ownership
    key_data = db.query_one(
        "SELECT tenant_id FROM api_keys WHERE key_id = ?",
        (key_id,),
    )

    if not key_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    if key_data["tenant_id"] != context.tenant_id and not context.is_admin_scope:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to revoke this key",
        )

    revoke_api_key(key_id)


# ---------------------------------------------------------------------------
# User-Tenant Assignment Endpoints
# ---------------------------------------------------------------------------


@router.post("/tenants/{tenant_id}/users/{user_id}")
async def assign_user_to_tenant(
    tenant_id: str,
    user_id: int,
    role: str = Query(default="member"),
    is_primary: bool = Query(default=False),
    context: Any = Depends(require_permission("tenants", "update")),
) -> Dict[str, Any]:
    """Assign a user to a tenant.

    Requires 'tenants:update' permission.
    """
    from ...tenant_manager import TenantManager

    relation = TenantManager.assign_user_to_tenant(
        user_id=user_id,
        tenant_id=tenant_id,
        role=role,
        is_primary=is_primary,
    )

    return relation


@router.delete("/tenants/{tenant_id}/users/{user_id}")
async def remove_user_from_tenant(
    tenant_id: str,
    user_id: int,
    context: Any = Depends(require_permission("tenants", "update")),
) -> None:
    """Remove a user from a tenant.

    Requires 'tenants:update' permission.
    """
    from ...tenant_manager import TenantManager

    success = TenantManager.remove_user_from_tenant(user_id, tenant_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User-tenant relationship not found",
        )


# ---------------------------------------------------------------------------
# Current Context Endpoints
# ---------------------------------------------------------------------------


@router.get("/me")
async def get_current_scope_context(
    context: Any = Depends(get_tenant_context),
) -> Dict[str, Any]:
    """Get the current scope context for the authenticated user.

    Requires authentication.
    """
    return context.to_dict()


@router.get("/me/permissions")
async def get_current_permissions(
    context: Any = Depends(get_tenant_context),
) -> Dict[str, List[str]]:
    """Get the current user's permissions based on scope.

    Requires authentication.
    """
    from ...scope_authorization import get_allowed_resources, get_allowed_actions

    resources = get_allowed_resources(context.scope)

    permissions = {}
    for resource in resources:
        actions = get_allowed_actions(context.scope, resource)
        permissions[resource] = actions

    return permissions


@router.get("/me/features")
async def get_current_features(
    context: Any = Depends(get_tenant_context),
) -> Dict[str, Any]:
    """Get the features available to the current scope.

    Requires authentication.
    """
    return {
        "scope": context.scope,
        "features": context.get_features(),
    }
