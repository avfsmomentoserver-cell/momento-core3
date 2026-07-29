"""Database initialization for V5 multi-scope architecture.

This module initializes:
- Multi-scope database schema
- Default scope permissions
- Default subscription plans
- Default tenants for each scope
- Initial communication policies
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from . import db
from .multi_scope_schema import MULTI_SCOPE_SCHEMA, SCOPES
from .scope_auth import initialize_default_scopes, SCOPE_PERMISSIONS
from .subscription_enforcement import SubscriptionEnforcer
from .tenant_resources import create_tenant_resources_table


def initialize_multi_scope_schema() -> None:
    """Initialize the multi-scope database schema."""
    # Execute the schema SQL
    db.execute_script(MULTI_SCOPE_SCHEMA)

    # Create additional tables
    create_tenant_resources_table()

    # Initialize default scope permissions
    initialize_default_permissions()

    # Initialize default subscription plans
    initialize_subscription_plans()

    # Initialize default tenants
    initialize_default_scopes()

    print("Multi-scope schema initialized successfully")


def initialize_default_permissions() -> None:
    """Initialize default scope permissions in the database."""
    now = datetime.now(timezone.utc).isoformat()

    # Clear existing permissions
    db.execute("DELETE FROM scope_permissions")

    # Insert permissions from SCOPE_PERMISSIONS
    for scope, resources in SCOPE_PERMISSIONS.items():
        for resource, actions in resources.items():
            for action in actions:
                db.execute(
                    """INSERT INTO scope_permissions
                       (scope, resource, action, enabled, created_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (scope, resource, action, 1, now),
                )

    # Add wildcard permissions for admin scopes
    admin_scopes = ["my_scope", "admin_scope"]
    for scope in admin_scopes:
        db.execute(
            """INSERT INTO scope_permissions
               (scope, resource, action, enabled, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (scope, "*", "*", 1, now),
        )

    print("Default scope permissions initialized")


def initialize_subscription_plans() -> None:
    """Initialize default subscription plans."""
    enforcer = SubscriptionEnforcer()
    enforcer._initialize_subscription_plans()
    print("Default subscription plans initialized")


def initialize_default_tenants() -> None:
    """Initialize default tenants for each scope."""
    from .tenant_manager import TenantManager

    for scope_id, scope_config in SCOPES.items():
        tenant_id = f"default_{scope_id}"

        # Check if tenant already exists
        existing = db.query_one("SELECT tenant_id FROM tenants WHERE tenant_id = ?", (tenant_id,))
        if existing:
            continue

        try:
            TenantManager.create_tenant(
                name=f"Default {scope_config['name']}",
                scope=scope_id,
                display_name=scope_config["description"],
                settings={"is_default": True, "auto_created": True},
            )
            print(f"Created default tenant for {scope_id}")
        except Exception as e:
            print(f"Failed to create default tenant for {scope_id}: {e}")


def initialize_communication_policies() -> None:
    """Initialize default cross-scope communication policies."""
    from .scope_communication import get_communication_policy

    policy_manager = get_communication_policy()
    # Policies are already initialized in the module
    print("Cross-scope communication policies initialized")


def verify_schema() -> bool:
    """Verify that all required tables exist.

    Returns:
        True if schema is valid
    """
    required_tables = [
        "tenants",
        "user_tenants",
        "subscriptions",
        "subscription_plans",
        "scope_permissions",
        "api_keys",
        "rate_limits",
        "usage_tracking",
        "scope_audit_log",
        "tenant_resources",
        "resource_shares",
    ]

    for table in required_tables:
        result = db.query_one(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        )
        if not result:
            print(f"Missing table: {table}")
            return False

    print("All required tables exist")
    return True


def get_schema_status() -> dict:
    """Get the current schema status.

    Returns:
        Dictionary with schema status information
    """
    tables = db.query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    table_names = [row["name"] for row in tables]

    # Count records in key tables
    counts = {}
    for table in ["tenants", "users", "subscriptions", "scope_permissions", "api_keys"]:
        if table in table_names:
            result = db.query_one(f"SELECT COUNT(*) as c FROM {table}")
            counts[table] = result["c"] if result else 0

    return {
        "tables": table_names,
        "table_count": len(table_names),
        "record_counts": counts,
        "schema_valid": verify_schema(),
    }


def reinitialize_schema() -> None:
    """Reinitialize the entire multi-scope schema (DANGEROUS!)."""
    print("WARNING: This will delete all existing data!")
    print("Type 'yes' to confirm:")

    # This is a safety measure - in production, require explicit confirmation
    # For now, we'll just print a warning
    print("Schema reinitialization skipped (manual confirmation required)")


def create_bootstrap_user_for_scope(scope: str, email: str, password: str) -> dict:
    """Create a bootstrap user for a specific scope.

    Args:
        scope: Scope identifier
        email: User email
        password: User password

    Returns:
        User dictionary
    """
    from .auth import create_user
    from .tenant_manager import TenantManager

    # Create user
    user = create_user(
        email=email,
        password=password,
        role="admin" if scope in ["my_scope", "admin_scope"] else "user",
        tier="pro" if scope in ["my_scope", "admin_scope", "fx_user_scope"] else "free",
        display_name=f"{scope.replace('_', ' ').title()} Bootstrap",
    )

    # Get or create default tenant for scope
    tenant_id = f"default_{scope}"
    tenant = TenantManager.get_tenant(tenant_id)

    if not tenant:
        tenant = TenantManager.create_tenant(
            name=f"Default {scope}",
            scope=scope,
            display_name=SCOPES[scope]["description"],
        )

    # Assign user to tenant
    TenantManager.assign_user_to_tenant(
        user_id=user["id"],
        tenant_id=tenant["tenant_id"],
        role="owner",
        is_primary=True,
    )

    return user


def initialize_complete_system() -> None:
    """Initialize the complete multi-scope system."""
    print("Initializing V5 Multi-Scope Authentication System...")

    # Step 1: Initialize schema
    print("\n1. Initializing database schema...")
    initialize_multi_scope_schema()

    # Step 2: Verify schema
    print("\n2. Verifying schema...")
    if not verify_schema():
        print("ERROR: Schema verification failed!")
        return

    # Step 3: Get status
    print("\n3. Getting schema status...")
    status = get_schema_status()
    print(f"   Tables: {status['table_count']}")
    print(f"   Record counts: {status['record_counts']}")

    # Step 4: Initialize default tenants
    print("\n4. Initializing default tenants...")
    initialize_default_tenants()

    # Step 5: Initialize communication policies
    print("\n5. Initializing communication policies...")
    initialize_communication_policies()

    print("\n✓ V5 Multi-Scope Authentication System initialized successfully!")
    print("\nNext steps:")
    print("  1. Create bootstrap users for each scope")
    print("  2. Configure cross-scope communication policies as needed")
    print("  3. Set up subscription billing integration")
    print("  4. Test authentication flow")


if __name__ == "__main__":
    # Run initialization when executed directly
    initialize_complete_system()
