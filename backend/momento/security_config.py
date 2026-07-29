"""Security Configuration Management.

Centralized security configuration for the V5 platform following
military-grade security standards.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import logging

from .security.tls_config import SecurityHeaderConfig, TLSVersion

logger = logging.getLogger(__name__)


class SecurityLevel(str, Enum):
    """Security configuration levels."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    HIGH_SECURITY = "high_security"


@dataclass
class AuthenticationConfig:
    """Authentication configuration."""

    # JWT settings
    jwt_algorithm: str = "RS256"
    jwt_access_token_ttl: int = 3600  # 1 hour
    jwt_refresh_token_ttl: int = 604800  # 7 days
    jwt_api_key_ttl: int = 2592000  # 30 days

    # Password policy
    password_min_length: int = 12
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_numbers: bool = True
    password_require_special: bool = True
    password_max_age_days: int = 90

    # MFA settings
    mfa_enabled: bool = True
    mfa_required_for_admin: bool = True
    mfa_required_for_sensitive: bool = True
    mfa_backup_codes_count: int = 10
    mfa_max_failed_attempts: int = 5
    mfa_lockout_duration: int = 900  # 15 minutes

    # Session settings
    session_timeout: int = 3600  # 1 hour
    max_concurrent_sessions: int = 5


@dataclass
class AuthorizationConfig:
    """Authorization configuration."""

    # RBAC settings
    rbac_enabled: bool = True
    default_role: str = "user"

    # ABAC settings
    abac_enabled: bool = True
    abac_risk_threshold: float = 0.7

    # Scope settings
    default_scopes: List[str] = field(default_factory=lambda: ["data:public", "analysis:basic"])

    # Privilege escalation
    require_approval_for_escalation: bool = True
    escalation_approval_timeout: int = 3600  # 1 hour


@dataclass
class EncryptionConfig:
    """Encryption configuration."""

    # Encryption at rest
    encryption_enabled: bool = True
    encryption_algorithm: str = "AES-256-GCM"
    key_rotation_days: int = 90

    # Fields to encrypt
    encrypted_fields: List[str] = field(
        default_factory=lambda: [
            "password",
            "api_key",
            "secret",
            "token",
            "ssn",
            "credit_card",
        ]
    )

    # Key management
    use_kms: bool = False  # Use AWS KMS or similar in production
    kms_key_id: Optional[str] = None


@dataclass
class NetworkSecurityConfig:
    """Network security configuration."""

    # TLS settings
    tls_min_version: TLSVersion = TLSVersion.TLS_1_2
    tls_prefer_server_ciphers: bool = False

    # IP filtering
    ip_filtering_enabled: bool = False
    allowed_ip_ranges: List[str] = field(default_factory=list)
    blocked_ip_ranges: List[str] = field(default_factory=list)

    # Rate limiting
    rate_limiting_enabled: bool = True
    rate_limit_requests_per_minute: int = 60
    rate_limit_burst: int = 10

    # DDoS protection
    ddos_protection_enabled: bool = True
    ddos_threshold: int = 1000  # requests per minute


@dataclass
class MonitoringConfig:
    """Security monitoring configuration."""

    # Event retention
    event_retention_days: int = 90
    anomaly_detection_enabled: bool = True
    intrusion_detection_enabled: bool = True

    # Alerting
    alert_on_critical: bool = True
    alert_on_high: bool = True
    alert_on_medium: bool = False

    # Anomaly thresholds
    auth_failure_threshold: int = 5
    auth_failure_window_minutes: int = 15
    high_rate_threshold: int = 100
    high_rate_window_seconds: int = 60


@dataclass
class AuditConfig:
    """Audit logging configuration."""

    # Retention
    retention_days: int = 365  # 1 year

    # Categories to log
    log_all_categories: bool = True
    logged_categories: Set[str] = field(
        default_factory=lambda: {
            "authentication",
            "authorization",
            "data_access",
            "data_modification",
            "system_config",
            "security_incident",
        }
    )

    # Compliance
    enable_compliance_reports: bool = True
    compliance_standards: List[str] = field(
        default_factory=lambda: ["nist_800_53", "iso_27001", "soc_2"]
    )

    # Streaming
    enable_streaming: bool = False


@dataclass
class SecurityConfig:
    """Complete security configuration."""

    level: SecurityLevel = SecurityLevel.PRODUCTION

    # Sub-configurations
    authentication: AuthenticationConfig = field(default_factory=AuthenticationConfig)
    authorization: AuthorizationConfig = field(default_factory=AuthorizationConfig)
    encryption: EncryptionConfig = field(default_factory=EncryptionConfig)
    network: NetworkSecurityConfig = field(default_factory=NetworkSecurityConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    audit: AuditConfig = field(default_factory=AuditConfig)

    # Security headers
    security_headers: SecurityHeaderConfig = field(default_factory=SecurityHeaderConfig)

    # Zero-trust settings
    zero_trust_enabled: bool = True
    zero_trust_strict_mode: bool = False

    # Public paths (no auth required)
    public_paths: List[str] = field(
        default_factory=lambda: [
            "/health",
            "/",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
        ]
    )

    @classmethod
    def from_environment(cls) -> "SecurityConfig":
        """Load security configuration from environment variables.

        Returns:
            SecurityConfig instance
        """
        level_str = os.environ.get("MOMENTO_SECURITY_LEVEL", "production")
        try:
            level = SecurityLevel(level_str)
        except ValueError:
            level = SecurityLevel.PRODUCTION
            logger.warning(f"Invalid security level: {level_str}, using production")

        config = cls(level=level)

        # Override from environment
        config.authentication.mfa_enabled = _env_bool(
            "MOMENTO_MFA_ENABLED", config.authentication.mfa_enabled
        )
        config.authentication.mfa_required_for_admin = _env_bool(
            "MOMENTO_MFA_REQUIRED_ADMIN", config.authentication.mfa_required_for_admin
        )
        config.network.rate_limiting_enabled = _env_bool(
            "MOMENTO_RATE_LIMITING", config.network.rate_limiting_enabled
        )
        config.network.ddos_protection_enabled = _env_bool(
            "MOMENTO_DDOS_PROTECTION", config.network.ddos_protection_enabled
        )
        config.monitoring.anomaly_detection_enabled = _env_bool(
            "MOMENTO_ANOMALY_DETECTION", config.monitoring.anomaly_detection_enabled
        )
        config.zero_trust_strict_mode = _env_bool(
            "MOMENTO_ZERO_TRUST_STRICT", config.zero_trust_strict_mode
        )

        # Security headers
        config.security_headers.hsts_enabled = _env_bool(
            "MOMENTO_HSTS_ENABLED", config.security_headers.hsts_enabled
        )
        config.security_headers.hsts_preload = _env_bool(
            "MOMENTO_HSTS_PRELOAD", config.security_headers.hsts_preload
        )

        return config

    def get_headers_config(self) -> SecurityHeaderConfig:
        """Get security headers configuration.

        Returns:
            SecurityHeaderConfig
        """
        if self.level == SecurityLevel.DEVELOPMENT:
            # More relaxed for development
            return SecurityHeaderConfig(
                hsts_enabled=False,
                csp_enabled=False,
            )
        elif self.level == SecurityLevel.STAGING:
            # Moderate security
            return SecurityHeaderConfig(
                hsts_enabled=True,
                hsts_max_age=86400,  # 1 day
                hsts_preload=False,
                csp_enabled=True,
            )
        else:
            # Production / High Security
            return SecurityHeaderConfig(
                hsts_enabled=True,
                hsts_max_age=31536000,  # 1 year
                hsts_include_subdomains=True,
                hsts_preload=True,
                csp_enabled=True,
            )


def _env_bool(name: str, default: bool) -> bool:
    """Get boolean environment variable.

    Args:
        name: Environment variable name
        default: Default value

    Returns:
        Boolean value
    """
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    """Get integer environment variable.

    Args:
        name: Environment variable name
        default: Default value

    Returns:
        Integer value
    """
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


# Global security configuration
security_config = SecurityConfig.from_environment()
