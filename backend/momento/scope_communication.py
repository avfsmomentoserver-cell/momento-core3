"""Cross-scope communication policies for V5 multi-scope architecture.

This module implements:
- Scope-to-scope communication rules
- Data sharing policies between scopes
- Cross-scope request validation
- Tenant isolation enforcement
- Scope elevation/degradation policies
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
import logging

from .multi_scope_schema import SCOPES

logger = logging.getLogger(__name__)


class CommunicationDirection(str, Enum):
    """Direction of cross-scope communication."""

    UPWARD = "upward"  # Lower privilege to higher privilege
    DOWNWARD = "downward"  # Higher privilege to lower privilege
    PEER = "peer"  # Same privilege level
    CROSS = "cross"  # Cross-domain communication


class CommunicationType(str, Enum):
    """Types of cross-scope communication."""

    DATA_READ = "data_read"
    DATA_WRITE = "data_write"
    API_CALL = "api_call"
    RESOURCE_ACCESS = "resource_access"
    NOTIFICATION = "notification"
    SYNC = "sync"


@dataclass
class CommunicationPolicy:
    """Policy for cross-scope communication."""

    source_scope: str
    target_scope: str
    allowed: bool
    direction: CommunicationDirection
    communication_types: Set[CommunicationType] = field(default_factory=set)
    requires_approval: bool = False
    rate_limit_multiplier: float = 1.0
    audit_required: bool = True
    conditions: Optional[Dict[str, Any]] = None


class ScopeCommunicationPolicy:
    """Manager for cross-scope communication policies.

    Implements the scope hierarchy from V5 architecture:
    - my_scope (100) - Platform Owner
    - admin_scope (90) - System Admin
    - fx_user_scope (80) - Professional Trading
    - big_better_scope (70) - Premium Clients
    - regular_low_budget_scope (60) - Basic Users
    - public_consumer_scope (50) - Free/Public
    """

    # Scope hierarchy from architecture
    SCOPE_HIERARCHY = {
        "my_scope": 100,
        "admin_scope": 90,
        "fx_user_scope": 80,
        "big_better_scope": 70,
        "regular_low_budget_scope": 60,
        "public_consumer_scope": 50,
    }

    def __init__(self):
        self._policies: Dict[Tuple[str, str], CommunicationPolicy] = {}
        self._initialize_default_policies()

    def _initialize_default_policies(self) -> None:
        """Initialize default cross-scope communication policies.

        Based on V5 architecture security model:
        - Higher scopes can access lower scopes (downward)
        - Lower scopes cannot access higher scopes (upward) without approval
        - Peer scopes have limited communication
        - Public scope is read-only for most
        """

        # My Scope (Platform Owner) - Full access to all scopes
        for target in self.SCOPE_HIERARCHY:
            if target != "my_scope":
                self._policies[("my_scope", target)] = CommunicationPolicy(
                    source_scope="my_scope",
                    target_scope=target,
                    allowed=True,
                    direction=CommunicationDirection.DOWNWARD,
                    communication_types={
                        CommunicationType.DATA_READ,
                        CommunicationType.DATA_WRITE,
                        CommunicationType.API_CALL,
                        CommunicationType.RESOURCE_ACCESS,
                        CommunicationType.NOTIFICATION,
                        CommunicationType.SYNC,
                    },
                    requires_approval=False,
                    rate_limit_multiplier=10.0,  # Unlimited effectively
                    audit_required=True,
                )

        # Admin Scope - Access to operational scopes
        for target in ["fx_user_scope", "big_better_scope", "regular_low_budget_scope", "public_consumer_scope"]:
            self._policies[("admin_scope", target)] = CommunicationPolicy(
                source_scope="admin_scope",
                target_scope=target,
                allowed=True,
                direction=CommunicationDirection.DOWNWARD,
                communication_types={
                    CommunicationType.DATA_READ,
                    CommunicationType.DATA_WRITE,
                    CommunicationType.API_CALL,
                    CommunicationType.RESOURCE_ACCESS,
                    CommunicationType.NOTIFICATION,
                },
                requires_approval=False,
                rate_limit_multiplier=2.0,
                audit_required=True,
            )

        # FX User Scope - Professional trading access
        self._policies[("fx_user_scope", "big_better_scope")] = CommunicationPolicy(
            source_scope="fx_user_scope",
            target_scope="big_better_scope",
            allowed=True,
            direction=CommunicationDirection.DOWNWARD,
            communication_types={
                CommunicationType.DATA_READ,
                CommunicationType.API_CALL,
            },
            requires_approval=False,
            rate_limit_multiplier=1.5,
            audit_required=True,
        )

        self._policies[("fx_user_scope", "regular_low_budget_scope")] = CommunicationPolicy(
            source_scope="fx_user_scope",
            target_scope="regular_low_budget_scope",
            allowed=True,
            direction=CommunicationDirection.DOWNWARD,
            communication_types={
                CommunicationType.DATA_READ,
            },
            requires_approval=False,
            rate_limit_multiplier=1.0,
            audit_required=True,
        )

        # Big Better Scope - Premium client access
        self._policies[("big_better_scope", "regular_low_budget_scope")] = CommunicationPolicy(
            source_scope="big_better_scope",
            target_scope="regular_low_budget_scope",
            allowed=True,
            direction=CommunicationDirection.DOWNWARD,
            communication_types={
                CommunicationType.DATA_READ,
            },
            requires_approval=False,
            rate_limit_multiplier=1.0,
            audit_required=True,
        )

        # Regular Low Budget Scope - Read access to public
        self._policies[("regular_low_budget_scope", "public_consumer_scope")] = CommunicationPolicy(
            source_scope="regular_low_budget_scope",
            target_scope="public_consumer_scope",
            allowed=True,
            direction=CommunicationDirection.DOWNWARD,
            communication_types={
                CommunicationType.DATA_READ,
            },
            requires_approval=False,
            rate_limit_multiplier=1.0,
            audit_required=False,
        )

        # Upward communication (lower to higher) - Requires approval
        for source in ["public_consumer_scope", "regular_low_budget_scope", "big_better_scope"]:
            for target in ["fx_user_scope", "admin_scope", "my_scope"]:
                if (source, target) not in self._policies:
                    self._policies[(source, target)] = CommunicationPolicy(
                        source_scope=source,
                        target_scope=target,
                        allowed=False,  # By default not allowed
                        direction=CommunicationDirection.UPWARD,
                        communication_types=set(),
                        requires_approval=True,
                        rate_limit_multiplier=0.5,
                        audit_required=True,
                    )

        # Peer communication - Limited
        peer_pairs = [
            ("fx_user_scope", "big_better_scope"),
            ("big_better_scope", "fx_user_scope"),
            ("regular_low_budget_scope", "big_better_scope"),
            ("big_better_scope", "regular_low_budget_scope"),
        ]

        for source, target in peer_pairs:
            if (source, target) not in self._policies:
                self._policies[(source, target)] = CommunicationPolicy(
                    source_scope=source,
                    target_scope=target,
                    allowed=True,
                    direction=CommunicationDirection.PEER,
                    communication_types={
                        CommunicationType.DATA_READ,
                        CommunicationType.NOTIFICATION,
                    },
                    requires_approval=False,
                    rate_limit_multiplier=1.0,
                    audit_required=True,
                )

    def get_policy(self, source_scope: str, target_scope: str) -> Optional[CommunicationPolicy]:
        """Get communication policy between two scopes.

        Args:
            source_scope: Source scope identifier
            target_scope: Target scope identifier

        Returns:
            CommunicationPolicy or None if no policy exists
        """
        return self._policies.get((source_scope, target_scope))

    def check_communication_allowed(
        self,
        source_scope: str,
        target_scope: str,
        comm_type: CommunicationType,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Check if cross-scope communication is allowed.

        Args:
            source_scope: Source scope identifier
            target_scope: Target scope identifier
            comm_type: Type of communication
            context: Optional context for policy evaluation

        Returns:
            Tuple of (allowed, reason)
        """
        policy = self.get_policy(source_scope, target_scope)

        if not policy:
            return False, f"No policy defined for {source_scope} -> {target_scope}"

        if not policy.allowed:
            if policy.requires_approval:
                return False, f"Communication requires approval: {source_scope} -> {target_scope}"
            return False, f"Communication not allowed: {source_scope} -> {target_scope}"

        if comm_type not in policy.communication_types:
            return False, f"Communication type {comm_type} not allowed for {source_scope} -> {target_scope}"

        # Evaluate conditions if provided
        if policy.conditions and context:
            if not self._evaluate_conditions(policy.conditions, context):
                return False, f"Policy conditions not met for {source_scope} -> {target_scope}"

        return True, None

    def _evaluate_conditions(self, conditions: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Evaluate policy conditions.

        Args:
            conditions: Policy conditions
            context: Current context

        Returns:
            True if conditions pass
        """
        for key, expected in conditions.items():
            if key not in context:
                return False

            actual = context[key]

            if isinstance(expected, dict):
                op = expected.get("op", "eq")
                value = expected.get("value")

                if op == "eq" and actual != value:
                    return False
                elif op == "ne" and actual == value:
                    return False
                elif op == "gt" and not (isinstance(actual, (int, float)) and actual > value):
                    return False
                elif op == "gte" and not (isinstance(actual, (int, float)) and actual >= value):
                    return False
                elif op == "lt" and not (isinstance(actual, (int, float)) and actual < value):
                    return False
                elif op == "lte" and not (isinstance(actual, (int, float)) and actual <= value):
                    return False
                elif op == "in" and actual not in value:
                    return False
            else:
                if actual != expected:
                    return False

        return True

    def get_communication_direction(self, source_scope: str, target_scope: str) -> CommunicationDirection:
        """Get the direction of communication between scopes.

        Args:
            source_scope: Source scope identifier
            target_scope: Target scope identifier

        Returns:
            CommunicationDirection
        """
        source_level = self.SCOPE_HIERARCHY.get(source_scope, 0)
        target_level = self.SCOPE_HIERARCHY.get(target_scope, 0)

        if source_level > target_level:
            return CommunicationDirection.DOWNWARD
        elif source_level < target_level:
            return CommunicationDirection.UPWARD
        else:
            return CommunicationDirection.PEER

    def get_allowed_targets(self, source_scope: str, comm_type: Optional[CommunicationType] = None) -> List[str]:
        """Get all allowed target scopes for a source scope.

        Args:
            source_scope: Source scope identifier
            comm_type: Optional filter by communication type

        Returns:
            List of target scope identifiers
        """
        allowed = []
        for (src, tgt), policy in self._policies.items():
            if src == source_scope and policy.allowed:
                if comm_type is None or comm_type in policy.communication_types:
                    allowed.append(tgt)
        return allowed

    def get_rate_limit_multiplier(self, source_scope: str, target_scope: str) -> float:
        """Get rate limit multiplier for cross-scope communication.

        Args:
            source_scope: Source scope identifier
            target_scope: Target scope identifier

        Returns:
            Rate limit multiplier
        """
        policy = self.get_policy(source_scope, target_scope)
        if policy:
            return policy.rate_limit_multiplier
        return 1.0

    def is_audit_required(self, source_scope: str, target_scope: str) -> bool:
        """Check if audit is required for cross-scope communication.

        Args:
            source_scope: Source scope identifier
            target_scope: Target scope identifier

        Returns:
            True if audit required
        """
        policy = self.get_policy(source_scope, target_scope)
        if policy:
            return policy.audit_required
        return True  # Default to audit required

    def add_policy(self, policy: CommunicationPolicy) -> None:
        """Add or update a communication policy.

        Args:
            policy: CommunicationPolicy to add
        """
        self._policies[(policy.source_scope, policy.target_scope)] = policy
        logger.info(
            "Added policy: %s -> %s (allowed=%s, direction=%s)",
            policy.source_scope,
            policy.target_scope,
            policy.allowed,
            policy.direction,
        )

    def remove_policy(self, source_scope: str, target_scope: str) -> bool:
        """Remove a communication policy.

        Args:
            source_scope: Source scope identifier
            target_scope: Target scope identifier

        Returns:
            True if removed, False if not found
        """
        if (source_scope, target_scope) in self._policies:
            del self._policies[(source_scope, target_scope)]
            logger.info("Removed policy: %s -> %s", source_scope, target_scope)
            return True
        return False

    def list_policies(self, source_scope: Optional[str] = None) -> List[CommunicationPolicy]:
        """List all policies or policies for a specific source scope.

        Args:
            source_scope: Optional source scope filter

        Returns:
            List of CommunicationPolicy
        """
        if source_scope:
            return [p for (src, _), p in self._policies.items() if src == source_scope]
        return list(self._policies.values())


# Global policy instance
_communication_policy = ScopeCommunicationPolicy()


def get_communication_policy() -> ScopeCommunicationPolicy:
    """Get the global communication policy instance."""
    return _communication_policy


def check_cross_scope_access(
    source_scope: str,
    target_scope: str,
    resource: str,
    action: str,
    context: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, Optional[str]]:
    """Check if cross-scope access is allowed for a resource-action pair.

    Args:
        source_scope: Source scope identifier
        target_scope: Target scope identifier
        resource: Resource being accessed
        action: Action being performed
        context: Optional context for evaluation

    Returns:
        Tuple of (allowed, reason)
    """
    policy_manager = get_communication_policy()

    # Map resource-action to communication type
    comm_type = _map_to_communication_type(resource, action)

    return policy_manager.check_communication_allowed(source_scope, target_scope, comm_type, context)


def _map_to_communication_type(resource: str, action: str) -> CommunicationType:
    """Map resource-action pair to communication type.

    Args:
        resource: Resource name
        action: Action name

    Returns:
        CommunicationType
    """
    if action == "read":
        return CommunicationType.DATA_READ
    elif action in ["write", "create", "update"]:
        return CommunicationType.DATA_WRITE
    elif resource == "api":
        return CommunicationType.API_CALL
    elif action == "delete":
        return CommunicationType.RESOURCE_ACCESS
    else:
        return CommunicationType.API_CALL
