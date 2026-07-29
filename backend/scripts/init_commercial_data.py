"""Initialize commercial data for V5 multi-scope architecture.

This script populates the database with:
- Default subscription plans (5-tier pricing structure)
- Feature gates for feature access control
- Pricing tiers for usage-based pricing
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from momento import db, commercial_service as cs
from momento.commercial_schema import (
    get_default_subscription_plans,
    get_default_feature_gates,
    get_default_pricing_tiers
)


def init_subscription_plans():
    """Initialize default subscription plans."""
    print("Initializing subscription plans...")
    plans = get_default_subscription_plans()

    for plan_data in plans:
        existing = cs.get_subscription_plan(plan_data["id"])
        if not existing:
            cs.create_subscription_plan(**plan_data)
            print(f"  ✓ Created plan: {plan_data['id']} - {plan_data['name']}")
        else:
            print(f"  - Plan already exists: {plan_data['id']}")

    print(f"Subscription plans initialized: {len(plans)} plans\n")


def init_feature_gates():
    """Initialize default feature gates."""
    print("Initializing feature gates...")
    gates = get_default_feature_gates()

    for gate_data in gates:
        existing = cs.get_feature_gate(gate_data["feature_key"])
        if not existing:
            cs.create_feature_gate(**gate_data)
            print(f"  ✓ Created feature gate: {gate_data['feature_key']} - {gate_data['feature_name']}")
        else:
            print(f"  - Feature gate already exists: {gate_data['feature_key']}")

    print(f"Feature gates initialized: {len(gates)} gates\n")


def init_pricing_tiers():
    """Initialize default pricing tiers."""
    print("Initializing pricing tiers...")
    tiers = get_default_pricing_tiers()

    for tier_data in tiers:
        # Check if tier exists
        rows = db.query(
            "SELECT * FROM pricing_tiers WHERE id = ?",
            (tier_data["id"],)
        )
        if not rows:
            cs.create_pricing_tier(**tier_data)
            print(f"  ✓ Created pricing tier: {tier_data['id']} - {tier_data['tier_name']}")
        else:
            print(f"  - Pricing tier already exists: {tier_data['id']}")

    print(f"Pricing tiers initialized: {len(tiers)} tiers\n")


def main():
    """Main initialization function."""
    print("=" * 60)
    print("V5 Commercial Data Initialization")
    print("=" * 60)
    print()

    # Initialize commercial schema
    print("Initializing commercial schema...")
    cs.initialize_commercial_schema()
    print()

    # Initialize subscription plans
    init_subscription_plans()

    # Initialize feature gates
    init_feature_gates()

    # Initialize pricing tiers
    init_pricing_tiers()

    print("=" * 60)
    print("Commercial data initialization complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
