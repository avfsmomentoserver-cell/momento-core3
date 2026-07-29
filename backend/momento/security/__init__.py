"""V5 Security Hardening Module.

This module implements military-grade security controls for the V5 transformation:
- JWT-based authentication with RS256 signatures
- RBAC (Role-Based Access Control)
- ABAC (Attribute-Based Access Control)
- Multi-factor authentication (MFA)
- Zero-trust security architecture
- AES-256 encryption at rest
- TLS 1.3 configuration for in-transit encryption
- WAF (Web Application Firewall)
- DDoS protection
- Security monitoring and intrusion detection
- Comprehensive audit logging for compliance

Compliance: NIST SP 800-53, ISO 27001, SOC 2
"""

from .jwt_auth import (
    JWTManager,
    jwt_auth,
    TokenPayload,
    TokenType,
)
from .rbac import (
    RBACManager,
    rbac,
    Permission,
    Scope,
    Role,
)
from .abac import (
    ABACManager,
    abac,
    AttributeType,
    ResourceSensitivity,
    NetworkTrust,
    PolicyEffect,
    Attribute,
    Subject,
    Resource,
    Environment,
    AccessRequest,
    PolicyCondition,
    Policy,
)
from .encryption import (
    EncryptionManager,
    encryption,
    EncryptedData,
)
from .mfa import (
    MFAManager,
    mfa,
    MFAConfig,
    MFAStatus,
    MFAVerificationResult,
    MFAEnrollmentResponse,
    MFAVerificationResponse,
)
from .zero_trust import (
    ZeroTrustMiddleware,
    SecurityContext,
    SecurityPolicy,
    SecurityLevel,
    RiskLevel,
    require_permission,
    require_scope,
    require_mfa,
)
from .monitoring import (
    SecurityMonitor,
    security_monitor,
    SecurityEvent,
    SecurityEventSeverity,
    SecurityEventType,
    AnomalyDetectionRule,
    IntrusionDetectionEngine,
    intrusion_detection,
)
from .audit import (
    AuditLogger,
    audit_logger,
    AuditEvent,
    AuditCategory,
    AuditOutcome,
)
from .tls_config import (
    SecurityHeadersMiddleware,
    SecurityHeaderConfig,
    TLSConfiguration,
    TLSVersion,
    CipherSuite,
    get_security_headers_config,
)

__all__ = [
    "JWTManager",
    "jwt_auth",
    "TokenPayload",
    "TokenType",
    "RBACManager",
    "rbac",
    "Permission",
    "Scope",
    "Role",
    "ABACManager",
    "abac",
    "AttributeType",
    "ResourceSensitivity",
    "NetworkTrust",
    "PolicyEffect",
    "Attribute",
    "Subject",
    "Resource",
    "Environment",
    "AccessRequest",
    "PolicyCondition",
    "Policy",
    "EncryptionManager",
    "encryption",
    "EncryptedData",
    "MFAManager",
    "mfa",
    "MFAConfig",
    "MFAStatus",
    "MFAVerificationResult",
    "MFAEnrollmentResponse",
    "MFAVerificationResponse",
    "ZeroTrustMiddleware",
    "SecurityContext",
    "SecurityPolicy",
    "SecurityLevel",
    "RiskLevel",
    "require_permission",
    "require_scope",
    "require_mfa",
    "SecurityMonitor",
    "security_monitor",
    "SecurityEvent",
    "SecurityEventSeverity",
    "SecurityEventType",
    "AnomalyDetectionRule",
    "IntrusionDetectionEngine",
    "intrusion_detection",
    "AuditLogger",
    "audit_logger",
    "AuditEvent",
    "AuditCategory",
    "AuditOutcome",
    "SecurityHeadersMiddleware",
    "SecurityHeaderConfig",
    "TLSConfiguration",
    "TLSVersion",
    "CipherSuite",
    "get_security_headers_config",
]
