"""Role-Based Access Control (RBAC) system for V5.

Implements military-grade RBAC with hierarchical roles, fine-grained permissions,
and scope-based access control following NIST SP 800-53 AC-3 requirements.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


class Permission(str, Enum):
    """System permissions following principle of least privilege."""

    # User Management
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_LIST = "user:list"

    # Data Access
    DATA_READ = "data:read"
    DATA_WRITE = "data:write"
    DATA_DELETE = "data:delete"
    DATA_EXPORT = "data:export"
    DATA_IMPORT = "data:import"

    # Analysis Operations
    ANALYSIS_RUN = "analysis:run"
    ANALYSIS_READ = "analysis:read"
    ANALYSIS_DELETE = "analysis:delete"
    ANALYSIS_CONFIG = "analysis:config"

    # Forecast Operations
    FORECAST_RUN = "forecast:run"
    FORECAST_READ = "forecast:read"
    FORECAST_DELETE = "forecast:delete"
    FORECAST_CONFIG = "forecast:config"

    # System Administration
    SYSTEM_CONFIG = "system:config"
    SYSTEM_MONITOR = "system:monitor"
    SYSTEM_BACKUP = "system:backup"
    SYSTEM_RESTORE = "system:restore"

    # Security Operations
    SECURITY_AUDIT = "security:audit"
    SECURITY_MANAGE = "security:manage"
    SECURITY_MONITOR = "security:monitor"

    # API Operations
    API_CREATE = "api:create"
    API_READ = "api:read"
    API_DELETE = "api:delete"
    API_CONFIG = "api:config"

    # Scope Operations
    SCOPE_CREATE = "scope:create"
    SCOPE_READ = "scope:read"
    SCOPE_UPDATE = "scope:update"
    SCOPE_DELETE = "scope:delete"


class Scope(str, Enum):
    """Access scopes for multi-tenant architecture."""

    # System-wide scopes
    SYSTEM = "system"
    ADMIN = "admin"

    # Data scopes
    DATA_PUBLIC = "data:public"
    DATA_PRIVATE = "data:private"
    DATA_SENSITIVE = "data:sensitive"

    # Analysis scopes
    ANALYSIS_BASIC = "analysis:basic"
    ANALYSIS_ADVANCED = "analysis:advanced"
    ANALYSIS_REALTIME = "analysis:realtime"

    # Forecast scopes
    FORECAST_BASIC = "forecast:basic"
    FORECAST_ADVANCED = "forecast:advanced"
    FORECAST_PRO = "forecast:pro"

    # API scopes
    API_READ = "api:read"
    API_WRITE = "api:write"
    API_ADMIN = "api:admin"


@dataclass
class Role:
    """Role definition with permissions and scope access."""

    name: str
    description: str
    permissions: Set[Permission] = field(default_factory=set)
    allowed_scopes: Set[Scope] = field(default_factory=set)
    inherits_from: Optional[str] = None  # Parent role for inheritance

    def has_permission(self, permission: Permission) -> bool:
        """Check if role has a specific permission."""
        return permission in self.permissions

    def has_scope_access(self, scope: Scope) -> bool:
        """Check if role has access to a specific scope."""
        return scope in self.allowed_scopes


class RBACManager:
    """RBAC manager with role hierarchy and permission checking.

    Implements NIST SP 800-53 AC-3 (Access Enforcement) and AC-6 (Least Privilege).
    """

    def __init__(self):
        self._roles: Dict[str, Role] = {}
        self._role_hierarchy: Dict[str, List[str]] = {}
        self._initialize_default_roles()

    def _initialize_default_roles(self) -> None:
        """Initialize default role hierarchy for V5 platform."""

        # Guest role - minimal access
        guest = Role(
            name="guest",
            description="Guest user with read-only access to public data",
            permissions={
                Permission.DATA_READ,
            },
            allowed_scopes={
                Scope.DATA_PUBLIC,
                Scope.ANALYSIS_BASIC,
                Scope.FORECAST_BASIC,
                Scope.API_READ,
            },
        )

        # User role - standard user access
        user = Role(
            name="user",
            description="Standard user with basic data and analysis access",
            permissions={
                Permission.USER_READ,
                Permission.DATA_READ,
                Permission.DATA_WRITE,
                Permission.ANALYSIS_READ,
                Permission.ANALYSIS_RUN,
                Permission.FORECAST_READ,
                Permission.FORECAST_RUN,
            },
            allowed_scopes={
                Scope.DATA_PUBLIC,
                Scope.DATA_PRIVATE,
                Scope.ANALYSIS_BASIC,
                Scope.ANALYSIS_ADVANCED,
                Scope.FORECAST_BASIC,
                Scope.FORECAST_ADVANCED,
                Scope.API_READ,
                Scope.API_WRITE,
            },
            inherits_from="guest",
        )

        # Analyst role - advanced analysis access
        analyst = Role(
            name="analyst",
            description="Analyst with advanced analysis and forecast capabilities",
            permissions={
                Permission.USER_READ,
                Permission.DATA_READ,
                Permission.DATA_WRITE,
                Permission.DATA_EXPORT,
                Permission.ANALYSIS_READ,
                Permission.ANALYSIS_RUN,
                Permission.ANALYSIS_CONFIG,
                Permission.FORECAST_READ,
                Permission.FORECAST_RUN,
                Permission.FORECAST_CONFIG,
                Permission.SYSTEM_MONITOR,
            },
            allowed_scopes={
                Scope.DATA_PUBLIC,
                Scope.DATA_PRIVATE,
                Scope.ANALYSIS_BASIC,
                Scope.ANALYSIS_ADVANCED,
                Scope.ANALYSIS_REALTIME,
                Scope.FORECAST_BASIC,
                Scope.FORECAST_ADVANCED,
                Scope.FORECAST_PRO,
                Scope.API_READ,
                Scope.API_WRITE,
            },
            inherits_from="user",
        )

        # Operator role - operational access
        operator = Role(
            name="operator",
            description="Operator with system management capabilities",
            permissions={
                Permission.USER_READ,
                Permission.USER_UPDATE,
                Permission.USER_LIST,
                Permission.DATA_READ,
                Permission.DATA_WRITE,
                Permission.DATA_DELETE,
                Permission.DATA_EXPORT,
                Permission.DATA_IMPORT,
                Permission.ANALYSIS_READ,
                Permission.ANALYSIS_RUN,
                Permission.ANALYSIS_DELETE,
                Permission.ANALYSIS_CONFIG,
                Permission.FORECAST_READ,
                Permission.FORECAST_RUN,
                Permission.FORECAST_DELETE,
                Permission.FORECAST_CONFIG,
                Permission.SYSTEM_CONFIG,
                Permission.SYSTEM_MONITOR,
                Permission.SYSTEM_BACKUP,
                Permission.SECURITY_MONITOR,
                Permission.API_READ,
                Permission.API_CONFIG,
                Permission.SCOPE_READ,
                Permission.SCOPE_UPDATE,
            },
            allowed_scopes={
                Scope.DATA_PUBLIC,
                Scope.DATA_PRIVATE,
                Scope.DATA_SENSITIVE,
                Scope.ANALYSIS_BASIC,
                Scope.ANALYSIS_ADVANCED,
                Scope.ANALYSIS_REALTIME,
                Scope.FORECAST_BASIC,
                Scope.FORECAST_ADVANCED,
                Scope.FORECAST_PRO,
                Scope.API_READ,
                Scope.API_WRITE,
                Scope.API_ADMIN,
            },
            inherits_from="analyst",
        )

        # Admin role - full system access
        admin = Role(
            name="admin",
            description="Administrator with full system access",
            permissions={
                # All permissions
                Permission.USER_CREATE,
                Permission.USER_READ,
                Permission.USER_UPDATE,
                Permission.USER_DELETE,
                Permission.USER_LIST,
                Permission.DATA_READ,
                Permission.DATA_WRITE,
                Permission.DATA_DELETE,
                Permission.DATA_EXPORT,
                Permission.DATA_IMPORT,
                Permission.ANALYSIS_RUN,
                Permission.ANALYSIS_READ,
                Permission.ANALYSIS_DELETE,
                Permission.ANALYSIS_CONFIG,
                Permission.FORECAST_RUN,
                Permission.FORECAST_READ,
                Permission.FORECAST_DELETE,
                Permission.FORECAST_CONFIG,
                Permission.SYSTEM_CONFIG,
                Permission.SYSTEM_MONITOR,
                Permission.SYSTEM_BACKUP,
                Permission.SYSTEM_RESTORE,
                Permission.SECURITY_AUDIT,
                Permission.SECURITY_MANAGE,
                Permission.SECURITY_MONITOR,
                Permission.API_CREATE,
                Permission.API_READ,
                Permission.API_DELETE,
                Permission.API_CONFIG,
                Permission.SCOPE_CREATE,
                Permission.SCOPE_READ,
                Permission.SCOPE_UPDATE,
                Permission.SCOPE_DELETE,
            },
            allowed_scopes=set(Scope),  # All scopes
            inherits_from="operator",
        )

        # Register roles
        self._roles = {
            "guest": guest,
            "user": user,
            "analyst": analyst,
            "operator": operator,
            "admin": admin,
        }

        # Build hierarchy
        self._role_hierarchy = {
            "guest": [],
            "user": ["guest"],
            "analyst": ["user", "guest"],
            "operator": ["analyst", "user", "guest"],
            "admin": ["operator", "analyst", "user", "guest"],
        }

    def get_role(self, role_name: str) -> Optional[Role]:
        """Get a role by name."""
        return self._roles.get(role_name)

    def get_all_roles(self) -> Dict[str, Role]:
        """Get all registered roles."""
        return self._roles.copy()

    def add_role(self, role: Role) -> None:
        """Add a new role to the system."""
        if role.name in self._roles:
            raise ValueError(f"Role {role.name} already exists")
        self._roles[role.name] = role
        if role.inherits_from:
            self._role_hierarchy[role.name] = self._get_inherited_roles(role.inherits_from)
        else:
            self._role_hierarchy[role.name] = []
        logger.info(f"Added role: {role.name}")

    def remove_role(self, role_name: str) -> None:
        """Remove a role from the system."""
        if role_name not in self._roles:
            raise ValueError(f"Role {role_name} does not exist")
        # Check if any other roles inherit from this role
        for role in self._roles.values():
            if role.inherits_from == role_name:
                raise ValueError(f"Cannot remove role {role_name}: role {role.name} inherits from it")
        del self._roles[role_name]
        del self._role_hierarchy[role_name]
        logger.info(f"Removed role: {role_name}")

    def _get_inherited_roles(self, role_name: str) -> List[str]:
        """Get all roles inherited by a role (transitive closure)."""
        if role_name not in self._role_hierarchy:
            return []
        inherited = []
        for parent in self._role_hierarchy[role_name]:
            inherited.append(parent)
            inherited.extend(self._get_inherited_roles(parent))
        return list(set(inherited))  # Remove duplicates

    def check_permission(
        self,
        role_name: str,
        permission: Permission,
        scope: Optional[Scope] = None,
    ) -> bool:
        """Check if a role has a specific permission (with optional scope check).

        Implements NIST SP 800-53 AC-3 (Access Enforcement).
        """
        role = self.get_role(role_name)
        if not role:
            logger.warning(f"Role not found: {role_name}")
            return False

        # Check direct permission
        if not role.has_permission(permission):
            # Check inherited permissions
            inherited = self._get_inherited_roles(role_name)
            for parent_role_name in inherited:
                parent_role = self.get_role(parent_role_name)
                if parent_role and parent_role.has_permission(permission):
                    break
            else:
                return False

        # Check scope if provided
        if scope:
            if not role.has_scope_access(scope):
                # Check inherited scope access
                inherited = self._get_inherited_roles(role_name)
                for parent_role_name in inherited:
                    parent_role = self.get_role(parent_role_name)
                    if parent_role and parent_role.has_scope_access(scope):
                        break
                else:
                    return False

        return True

    def get_permissions(self, role_name: str) -> Set[Permission]:
        """Get all permissions for a role (including inherited)."""
        role = self.get_role(role_name)
        if not role:
            return set()

        permissions = set(role.permissions)
        inherited = self._get_inherited_roles(role_name)
        for parent_role_name in inherited:
            parent_role = self.get_role(parent_role_name)
            if parent_role:
                permissions.update(parent_role.permissions)

        return permissions

    def get_scopes(self, role_name: str) -> Set[Scope]:
        """Get all scopes for a role (including inherited)."""
        role = self.get_role(role_name)
        if not role:
            return set()

        scopes = set(role.allowed_scopes)
        inherited = self._get_inherited_roles(role_name)
        for parent_role_name in inherited:
            parent_role = self.get_role(parent_role_name)
            if parent_role:
                scopes.update(parent_role.allowed_scopes)

        return scopes

    def grant_permission(self, role_name: str, permission: Permission) -> None:
        """Grant a permission to a role."""
        role = self.get_role(role_name)
        if not role:
            raise ValueError(f"Role {role_name} does not exist")
        role.permissions.add(permission)
        logger.info(f"Granted permission {permission} to role {role_name}")

    def revoke_permission(self, role_name: str, permission: Permission) -> None:
        """Revoke a permission from a role."""
        role = self.get_role(role_name)
        if not role:
            raise ValueError(f"Role {role_name} does not exist")
        role.permissions.discard(permission)
        logger.info(f"Revoked permission {permission} from role {role_name}")

    def grant_scope(self, role_name: str, scope: Scope) -> None:
        """Grant scope access to a role."""
        role = self.get_role(role_name)
        if not role:
            raise ValueError(f"Role {role_name} does not exist")
        role.allowed_scopes.add(scope)
        logger.info(f"Granted scope {scope} to role {role_name}")

    def revoke_scope(self, role_name: str, scope: Scope) -> None:
        """Revoke scope access from a role."""
        role = self.get_role(role_name)
        if not role:
            raise ValueError(f"Role {role_name} does not exist")
        role.allowed_scopes.discard(scope)
        logger.info(f"Revoked scope {scope} from role {role_name}")


# Global RBAC manager instance
rbac = RBACManager()
