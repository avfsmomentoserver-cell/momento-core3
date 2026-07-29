"""Attribute-Based Access Control (ABAC) system for V5.

Implements fine-grained authorization based on user attributes, resource attributes,
environmental conditions, and policy rules following NIST SP 800-162 standards.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
import re
import logging

logger = logging.getLogger(__name__)


class AttributeType(str, Enum):
    """Types of attributes for ABAC."""

    # User attributes
    USER_ID = "user_id"
    USER_EMAIL = "user_email"
    USER_ROLE = "user_role"
    USER_TIER = "user_tier"
    USER_DEPARTMENT = "user_department"
    USER_LOCATION = "user_location"
    USER_AUTH_METHOD = "user_auth_method"
    USER_MFA_ENABLED = "user_mfa_enabled"

    # Resource attributes
    RESOURCE_TYPE = "resource_type"
    RESOURCE_ID = "resource_id"
    RESOURCE_OWNER = "resource_owner"
    RESOURCE_SENSITIVITY = "resource_sensitivity"
    RESOURCE_CLASSIFICATION = "resource_classification"
    RESOURCE_SCOPE = "resource_scope"

    # Environmental attributes
    TIME_OF_DAY = "time_of_day"
    DAY_OF_WEEK = "day_of_week"
    IP_ADDRESS = "ip_address"
    USER_AGENT = "user_agent"
    GEOLOCATION = "geolocation"
    NETWORK_TRUST = "network_trust"
    SESSION_AGE = "session_age"

    # Contextual attributes
    RISK_SCORE = "risk_score"
    THREAT_LEVEL = "threat_level"
    ANOMALY_DETECTED = "anomaly_detected"


class ResourceSensitivity(str, Enum):
    """Resource sensitivity levels."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    TOP_SECRET = "top_secret"


class NetworkTrust(str, Enum):
    """Network trust levels."""

    TRUSTED = "trusted"
    SEMI_TRUSTED = "semi_trusted"
    UNTRUSTED = "untrusted"
    BLOCKED = "blocked"


class PolicyEffect(str, Enum):
    """Policy decision effects."""

    PERMIT = "permit"
    DENY = "deny"
    NOT_APPLICABLE = "not_applicable"


@dataclass
class Attribute:
    """An attribute with type and value."""

    type: AttributeType
    value: Any
    source: str = "system"  # Where the attribute comes from


@dataclass
class Subject:
    """The user or system requesting access."""

    user_id: int
    email: str
    role: str
    tier: str
    attributes: Dict[AttributeType, Any] = field(default_factory=dict)

    def get_attribute(self, attr_type: AttributeType) -> Any:
        """Get an attribute value."""
        return self.attributes.get(attr_type)

    def set_attribute(self, attr_type: AttributeType, value: Any) -> None:
        """Set an attribute value."""
        self.attributes[attr_type] = value


@dataclass
class Resource:
    """The resource being accessed."""

    resource_type: str
    resource_id: str
    owner_id: Optional[int] = None
    sensitivity: ResourceSensitivity = ResourceSensitivity.INTERNAL
    classification: str = "internal"
    scope: str = "public"
    attributes: Dict[AttributeType, Any] = field(default_factory=dict)

    def get_attribute(self, attr_type: AttributeType) -> Any:
        """Get an attribute value."""
        return self.attributes.get(attr_type)

    def set_attribute(self, attr_type: AttributeType, value: Any) -> None:
        """Set an attribute value."""
        self.attributes[attr_type] = value


@dataclass
class Environment:
    """Environmental context for the access request."""

    current_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    geolocation: Optional[str] = None
    network_trust: NetworkTrust = NetworkTrust.UNTRUSTED
    session_age: Optional[int] = None  # in seconds
    risk_score: float = 0.0
    threat_level: str = "low"
    anomaly_detected: bool = False
    attributes: Dict[AttributeType, Any] = field(default_factory=dict)

    def get_attribute(self, attr_type: AttributeType) -> Any:
        """Get an attribute value."""
        return self.attributes.get(attr_type)

    def set_attribute(self, attr_type: AttributeType, value: Any) -> None:
        """Set an attribute value."""
        self.attributes[attr_type] = value


@dataclass
class AccessRequest:
    """A complete access request with subject, resource, and environment."""

    subject: Subject
    resource: Resource
    environment: Environment
    action: str  # The action being performed (read, write, delete, etc.)
    request_id: Optional[str] = None


class PolicyCondition:
    """A condition that evaluates to true or false based on attributes."""

    def __init__(
        self,
        attribute_type: AttributeType,
        operator: str,
        value: Any,
    ):
        self.attribute_type = attribute_type
        self.operator = operator  # eq, ne, gt, lt, gte, lte, in, contains, regex
        self.value = value

    def evaluate(self, request: AccessRequest) -> bool:
        """Evaluate the condition against the access request."""
        # Get attribute value from appropriate source
        attr_value = self._get_attribute_value(request)
        if attr_value is None:
            return False

        # Apply operator
        try:
            if self.operator == "eq":
                return attr_value == self.value
            elif self.operator == "ne":
                return attr_value != self.value
            elif self.operator == "gt":
                return attr_value > self.value
            elif self.operator == "lt":
                return attr_value < self.value
            elif self.operator == "gte":
                return attr_value >= self.value
            elif self.operator == "lte":
                return attr_value <= self.value
            elif self.operator == "in":
                return attr_value in self.value
            elif self.operator == "contains":
                return self.value in attr_value
            elif self.operator == "regex":
                return bool(re.match(self.value, str(attr_value)))
            else:
                logger.warning(f"Unknown operator: {self.operator}")
                return False
        except Exception as e:
            logger.warning(f"Condition evaluation error: {e}")
            return False

    def _get_attribute_value(self, request: AccessRequest) -> Any:
        """Get the attribute value from the appropriate source."""
        attr_type = self.attribute_type

        # User attributes
        if attr_type in [
            AttributeType.USER_ID,
            AttributeType.USER_EMAIL,
            AttributeType.USER_ROLE,
            AttributeType.USER_TIER,
            AttributeType.USER_DEPARTMENT,
            AttributeType.USER_LOCATION,
            AttributeType.USER_AUTH_METHOD,
            AttributeType.USER_MFA_ENABLED,
        ]:
            if attr_type == AttributeType.USER_ID:
                return request.subject.user_id
            elif attr_type == AttributeType.USER_EMAIL:
                return request.subject.email
            elif attr_type == AttributeType.USER_ROLE:
                return request.subject.role
            elif attr_type == AttributeType.USER_TIER:
                return request.subject.tier
            else:
                return request.subject.get_attribute(attr_type)

        # Resource attributes
        elif attr_type in [
            AttributeType.RESOURCE_TYPE,
            AttributeType.RESOURCE_ID,
            AttributeType.RESOURCE_OWNER,
            AttributeType.RESOURCE_SENSITIVITY,
            AttributeType.RESOURCE_CLASSIFICATION,
            AttributeType.RESOURCE_SCOPE,
        ]:
            if attr_type == AttributeType.RESOURCE_TYPE:
                return request.resource.resource_type
            elif attr_type == AttributeType.RESOURCE_ID:
                return request.resource.resource_id
            elif attr_type == AttributeType.RESOURCE_OWNER:
                return request.resource.owner_id
            elif attr_type == AttributeType.RESOURCE_SENSITIVITY:
                return request.resource.sensitivity
            elif attr_type == AttributeType.RESOURCE_CLASSIFICATION:
                return request.resource.classification
            elif attr_type == AttributeType.RESOURCE_SCOPE:
                return request.resource.scope
            else:
                return request.resource.get_attribute(attr_type)

        # Environmental attributes
        elif attr_type in [
            AttributeType.TIME_OF_DAY,
            AttributeType.DAY_OF_WEEK,
            AttributeType.IP_ADDRESS,
            AttributeType.USER_AGENT,
            AttributeType.GEOLOCATION,
            AttributeType.NETWORK_TRUST,
            AttributeType.SESSION_AGE,
            AttributeType.RISK_SCORE,
            AttributeType.THREAT_LEVEL,
            AttributeType.ANOMALY_DETECTED,
        ]:
            if attr_type == AttributeType.TIME_OF_DAY:
                return request.environment.current_time.hour
            elif attr_type == AttributeType.DAY_OF_WEEK:
                return request.environment.current_time.weekday()
            elif attr_type == AttributeType.IP_ADDRESS:
                return request.environment.ip_address
            elif attr_type == AttributeType.USER_AGENT:
                return request.environment.user_agent
            elif attr_type == AttributeType.GEOLOCATION:
                return request.environment.geolocation
            elif attr_type == AttributeType.NETWORK_TRUST:
                return request.environment.network_trust
            elif attr_type == AttributeType.SESSION_AGE:
                return request.environment.session_age
            elif attr_type == AttributeType.RISK_SCORE:
                return request.environment.risk_score
            elif attr_type == AttributeType.THREAT_LEVEL:
                return request.environment.threat_level
            elif attr_type == AttributeType.ANOMALY_DETECTED:
                return request.environment.anomaly_detected
            else:
                return request.environment.get_attribute(attr_type)

        return None


class Policy:
    """An ABAC policy with conditions and effect."""

    def __init__(
        self,
        policy_id: str,
        name: str,
        description: str,
        effect: PolicyEffect,
        conditions: List[PolicyCondition],
        priority: int = 0,
    ):
        self.policy_id = policy_id
        self.name = name
        self.description = description
        self.effect = effect
        self.conditions = conditions
        self.priority = priority  # Higher priority policies are evaluated first
        self.enabled = True

    def evaluate(self, request: AccessRequest) -> PolicyEffect:
        """Evaluate the policy against the access request."""
        if not self.enabled:
            return PolicyEffect.NOT_APPLICABLE

        # All conditions must be true for the policy to apply
        for condition in self.conditions:
            if not condition.evaluate(request):
                return PolicyEffect.NOT_APPLICABLE

        return self.effect


class ABACManager:
    """ABAC manager for fine-grained authorization.

    Implements NIST SP 800-162 (Attribute-Based Access Control).
    """

    def __init__(self):
        self._policies: Dict[str, Policy] = {}
        self._initialize_default_policies()

    def _initialize_default_policies(self) -> None:
        """Initialize default ABAC policies for V5 platform."""

        # Policy: MFA required for sensitive data access
        mfa_policy = Policy(
            policy_id="mfa_required",
            name="MFA Required for Sensitive Data",
            description="Require MFA for accessing sensitive or restricted resources",
            effect=PolicyEffect.DENY,
            conditions=[
                PolicyCondition(
                    AttributeType.RESOURCE_SENSITIVITY,
                    "in",
                    [ResourceSensitivity.CONFIDENTIAL, ResourceSensitivity.RESTRICTED, ResourceSensitivity.TOP_SECRET],
                ),
                PolicyCondition(
                    AttributeType.USER_MFA_ENABLED,
                    "eq",
                    False,
                ),
            ],
            priority=100,
        )

        # Policy: Trusted network required for high-risk operations
        trusted_network_policy = Policy(
            policy_id="trusted_network_required",
            name="Trusted Network Required",
            description="Require trusted network for write/delete operations",
            effect=PolicyEffect.DENY,
            conditions=[
                PolicyCondition(
                    AttributeType.NETWORK_TRUST,
                    "ne",
                    NetworkTrust.TRUSTED,
                ),
                PolicyCondition(
                    AttributeType.RESOURCE_SENSITIVITY,
                    "in",
                    [ResourceSensitivity.CONFIDENTIAL, ResourceSensitivity.RESTRICTED, ResourceSensitivity.TOP_SECRET],
                ),
            ],
            priority=90,
        )

        # Policy: Business hours only for sensitive operations
        business_hours_policy = Policy(
            policy_id="business_hours_only",
            name="Business Hours Only",
            description="Restrict sensitive operations to business hours (8am-6pm weekdays)",
            effect=PolicyEffect.DENY,
            conditions=[
                PolicyCondition(
                    AttributeType.RESOURCE_SENSITIVITY,
                    "in",
                    [ResourceSensitivity.RESTRICTED, ResourceSensitivity.TOP_SECRET],
                ),
                PolicyCondition(
                    AttributeType.DAY_OF_WEEK,
                    "in",
                    [5, 6],  # Saturday, Sunday
                ),
            ],
            priority=80,
        )

        # Policy: High risk score denies access
        high_risk_policy = Policy(
            policy_id="high_risk_deny",
            name="High Risk Score Deny",
            description="Deny access when risk score is high",
            effect=PolicyEffect.DENY,
            conditions=[
                PolicyCondition(
                    AttributeType.RISK_SCORE,
                    "gte",
                    0.8,
                ),
            ],
            priority=95,
        )

        # Policy: Anomaly detected denies access
        anomaly_policy = Policy(
            policy_id="anomaly_deny",
            name="Anomaly Detected Deny",
            description="Deny access when anomaly is detected",
            effect=PolicyEffect.DENY,
            conditions=[
                PolicyCondition(
                    AttributeType.ANOMALY_DETECTED,
                    "eq",
                    True,
                ),
            ],
            priority=100,
        )

        # Policy: Resource owner can always access
        owner_policy = Policy(
            policy_id="owner_access",
            name="Resource Owner Access",
            description="Resource owners can always access their own resources",
            effect=PolicyEffect.PERMIT,
            conditions=[
                PolicyCondition(
                    AttributeType.USER_ID,
                    "eq",
                    "resource_owner",  # Special marker, will be handled in evaluation
                ),
            ],
            priority=70,
        )

        # Register policies
        self._policies = {
            "mfa_required": mfa_policy,
            "trusted_network_required": trusted_network_policy,
            "business_hours_only": business_hours_policy,
            "high_risk_deny": high_risk_policy,
            "anomaly_deny": anomaly_policy,
            "owner_access": owner_policy,
        }

    def add_policy(self, policy: Policy) -> None:
        """Add a new policy to the system."""
        if policy.policy_id in self._policies:
            raise ValueError(f"Policy {policy.policy_id} already exists")
        self._policies[policy.policy_id] = policy
        logger.info(f"Added policy: {policy.policy_id}")

    def remove_policy(self, policy_id: str) -> None:
        """Remove a policy from the system."""
        if policy_id not in self._policies:
            raise ValueError(f"Policy {policy_id} does not exist")
        del self._policies[policy_id]
        logger.info(f"Removed policy: {policy_id}")

    def get_policy(self, policy_id: str) -> Optional[Policy]:
        """Get a policy by ID."""
        return self._policies.get(policy_id)

    def get_all_policies(self) -> Dict[str, Policy]:
        """Get all policies."""
        return self._policies.copy()

    def enable_policy(self, policy_id: str) -> None:
        """Enable a policy."""
        policy = self.get_policy(policy_id)
        if not policy:
            raise ValueError(f"Policy {policy_id} does not exist")
        policy.enabled = True
        logger.info(f"Enabled policy: {policy_id}")

    def disable_policy(self, policy_id: str) -> None:
        """Disable a policy."""
        policy = self.get_policy(policy_id)
        if not policy:
            raise ValueError(f"Policy {policy_id} does not exist")
        policy.enabled = False
        logger.info(f"Disabled policy: {policy_id}")

    def evaluate(self, request: AccessRequest) -> PolicyEffect:
        """Evaluate all policies against the access request.

        Returns:
            PolicyEffect.PERMIT if access is allowed
            PolicyEffect.DENY if access is denied
            PolicyEffect.NOT_APPLICABLE if no policies apply (default deny)
        """
        # Special handling for owner access
        if request.resource.owner_id and request.subject.user_id == request.resource.owner_id:
            owner_policy = self.get_policy("owner_access")
            if owner_policy and owner_policy.enabled:
                # Update condition to match actual user ID
                for condition in owner_policy.conditions:
                    if condition.attribute_type == AttributeType.USER_ID:
                        condition.value = request.subject.user_id
                result = owner_policy.evaluate(request)
                if result == PolicyEffect.PERMIT:
                    return PolicyEffect.PERMIT

        # Sort policies by priority (highest first)
        sorted_policies = sorted(
            self._policies.values(),
            key=lambda p: p.priority,
            reverse=True,
        )

        # Evaluate policies in priority order
        # First DENY that applies wins
        for policy in sorted_policies:
            if not policy.enabled:
                continue

            result = policy.evaluate(request)
            if result == PolicyEffect.DENY:
                logger.info(f"Access denied by policy: {policy.policy_id}")
                return PolicyEffect.DENY

        # If no DENY policies applied, check for PERMIT policies
        for policy in sorted_policies:
            if not policy.enabled:
                continue

            result = policy.evaluate(request)
            if result == PolicyEffect.PERMIT:
                logger.info(f"Access permitted by policy: {policy.policy_id}")
                return PolicyEffect.PERMIT

        # Default deny (fail-safe)
        logger.info("Access denied: no applicable permit policies")
        return PolicyEffect.DENY

    def check_access(
        self,
        subject: Subject,
        resource: Resource,
        environment: Environment,
        action: str,
    ) -> bool:
        """Check if access is granted (convenience method)."""
        request = AccessRequest(
            subject=subject,
            resource=resource,
            environment=environment,
            action=action,
        )
        result = self.evaluate(request)
        return result == PolicyEffect.PERMIT


# Global ABAC manager instance
abac = ABACManager()
