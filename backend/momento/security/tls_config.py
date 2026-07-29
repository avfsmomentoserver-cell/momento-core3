"""TLS 1.3 Configuration and Security Headers Middleware.

Implements secure HTTP headers and TLS configuration following:
- NIST SP 800-52 Rev. 2 (TLS Configuration)
- OWASP Secure Headers
- RFC 8446 (TLS 1.3)
- CIS Benchmarks
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum
import logging

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class TLSVersion(str, Enum):
    """Supported TLS versions."""

    TLS_1_3 = "TLSv1.3"
    TLS_1_2 = "TLSv1.2"
    TLS_1_1 = "TLSv1.1"
    TLS_1_0 = "TLSv1.0"


class CipherSuite(str, Enum):
    """Secure cipher suites (TLS 1.3)."""

    # TLS 1.3 cipher suites (NIST approved)
    AES_256_GCM_SHA384 = "TLS_AES_256_GCM_SHA384"
    AES_128_GCM_SHA256 = "TLS_AES_128_GCM_SHA256"
    CHACHA20_POLY1305_SHA256 = "TLS_CHACHA20_POLY1305_SHA256"


@dataclass
class SecurityHeaderConfig:
    """Configuration for security headers."""

    # HSTS (HTTP Strict Transport Security)
    hsts_enabled: bool = True
    hsts_max_age: int = 31536000  # 1 year
    hsts_include_subdomains: bool = True
    hsts_preload: bool = False

    # Content Security Policy
    csp_enabled: bool = True
    csp_policy: str = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )

    # X-Content-Type-Options
    x_content_type_options: bool = True

    # X-Frame-Options
    x_frame_options: str = "DENY"

    # X-XSS-Protection
    x_xss_protection: str = "1; mode=block"

    # Referrer-Policy
    referrer_policy: str = "strict-origin-when-cross-origin"

    # Permissions-Policy
    permissions_policy: str = (
        "geolocation=(), "
        "microphone=(), "
        "camera=(), "
        "payment=(), "
        "usb=(), "
        "magnetometer=(), "
        "gyroscope=(), "
        "accelerometer=()"
    )

    # Content-Type Options
    cross_origin_opener_policy: str = "same-origin"
    cross_origin_embedder_policy: str = "require-corp"

    # Cache Control for sensitive endpoints
    cache_control_for_sensitive: str = "no-store, no-cache, must-revalidate, private"

    # Custom headers
    custom_headers: Dict[str, str] = None

    def __post_init__(self):
        if self.custom_headers is None:
            self.custom_headers = {}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses.

    Implements OWASP recommended security headers:
    - HSTS (HTTP Strict Transport Security)
    - CSP (Content Security Policy)
    - X-Content-Type-Options
    - X-Frame-Options
    - X-XSS-Protection
    - Referrer-Policy
    - Permissions-Policy
    """

    def __init__(
        self,
        app: ASGIApp,
        config: Optional[SecurityHeaderConfig] = None,
        sensitive_paths: Optional[List[str]] = None,
    ):
        """Initialize security headers middleware.

        Args:
            app: ASGI application
            config: Security header configuration
            sensitive_paths: Paths that require stricter caching
        """
        super().__init__(app)
        self.config = config or SecurityHeaderConfig()
        self.sensitive_paths = sensitive_paths or [
            "/api/v1/auth/",
            "/api/v1/users/",
            "/api/v1/admin/",
        ]

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and add security headers to response.

        Args:
            request: Incoming request
            call_next: Next middleware/endpoint

        Returns:
            Response with security headers
        """
        response = await call_next(request)

        # Apply security headers
        self._apply_hsts(response)
        self._apply_csp(response)
        self._apply_content_type_options(response)
        self._apply_frame_options(response)
        self._apply_xss_protection(response)
        self._apply_referrer_policy(response)
        self._apply_permissions_policy(response)
        self._apply_cross_origin_policies(response)
        self._apply_custom_headers(response)

        # Apply stricter caching for sensitive paths
        if self._is_sensitive_path(request.url.path):
            response.headers["Cache-Control"] = self.config.cache_control_for_sensitive
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

        # Remove server information
        response.headers.pop("Server", None)

        return response

    def _apply_hsts(self, response: Response) -> None:
        """Apply HSTS header.

        Args:
            response: HTTP response
        """
        if self.config.hsts_enabled:
            hsts_value = f"max-age={self.config.hsts_max_age}"
            if self.config.hsts_include_subdomains:
                hsts_value += "; includeSubDomains"
            if self.config.hsts_preload:
                hsts_value += "; preload"
            response.headers["Strict-Transport-Security"] = hsts_value

    def _apply_csp(self, response: Response) -> None:
        """Apply Content Security Policy header.

        Args:
            response: HTTP response
        """
        if self.config.csp_enabled:
            response.headers["Content-Security-Policy"] = self.config.csp_policy

    def _apply_content_type_options(self, response: Response) -> None:
        """Apply X-Content-Type-Options header.

        Args:
            response: HTTP response
        """
        if self.config.x_content_type_options:
            response.headers["X-Content-Type-Options"] = "nosniff"

    def _apply_frame_options(self, response: Response) -> None:
        """Apply X-Frame-Options header.

        Args:
            response: HTTP response
        """
        response.headers["X-Frame-Options"] = self.config.x_frame_options

    def _apply_xss_protection(self, response: Response) -> None:
        """Apply X-XSS-Protection header.

        Args:
            response: HTTP response
        """
        response.headers["X-XSS-Protection"] = self.config.x_xss_protection

    def _apply_referrer_policy(self, response: Response) -> None:
        """Apply Referrer-Policy header.

        Args:
            response: HTTP response
        """
        response.headers["Referrer-Policy"] = self.config.referrer_policy

    def _apply_permissions_policy(self, response: Response) -> None:
        """Apply Permissions-Policy header.

        Args:
            response: HTTP response
        """
        response.headers["Permissions-Policy"] = self.config.permissions_policy

    def _apply_cross_origin_policies(self, response: Response) -> None:
        """Apply Cross-Origin policies.

        Args:
            response: HTTP response
        """
        response.headers["Cross-Origin-Opener-Policy"] = self.config.cross_origin_opener_policy
        response.headers[
            "Cross-Origin-Embedder-Policy"
        ] = self.config.cross_origin_embedder_policy

    def _apply_custom_headers(self, response: Response) -> None:
        """Apply custom headers.

        Args:
            response: HTTP response
        """
        for name, value in self.config.custom_headers.items():
            response.headers[name] = value

    def _is_sensitive_path(self, path: str) -> bool:
        """Check if path is sensitive.

        Args:
            path: Request path

        Returns:
            True if path is sensitive
        """
        for sensitive in self.sensitive_paths:
            if path.startswith(sensitive):
                return True
        return False


class TLSConfiguration:
    """TLS configuration guidance and validation.

    Provides recommendations for TLS 1.3 configuration.
    """

    # Recommended TLS 1.3 cipher suites (NIST SP 800-52 Rev. 2)
    RECOMMENDED_CIPHER_SUITES = [
        CipherSuite.AES_256_GCM_SHA384,
        CipherSuite.AES_128_GCM_SHA256,
        CipherSuite.CHACHA20_POLY1305_SHA256,
    ]

    # Minimum TLS version by standard
    MIN_TLS_VERSIONS = {
        "nist_800_52": TLSVersion.TLS_1_2,
        "pci_dss": TLSVersion.TLS_1_2,
        "hipaa": TLSVersion.TLS_1_2,
        "iso_27001": TLSVersion.TLS_1_2,
        "best_practice": TLSVersion.TLS_1_3,
    }

    @staticmethod
    def get_uvicorn_ssl_config() -> Dict[str, any]:
        """Get SSL configuration for Uvicorn.

        Returns:
            Dictionary with SSL configuration parameters
        """
        return {
            "ssl_keyfile": "/path/to/private.key",  # Configure via environment
            "ssl_certfile": "/path/to/certificate.crt",  # Configure via environment
            "ssl_ca_certs": "/path/to/ca_bundle.crt",  # Configure via environment
            "ssl_cert_reqs": 2,  # ssl.CERT_REQUIRED
            "ssl_version": 771,  # TLSv1_2 (minimum for compatibility)
            # Note: TLS 1.3 is the default in modern OpenSSL
        }

    @staticmethod
    def get_nginx_config() -> str:
        """Get recommended Nginx TLS configuration.

        Returns:
            Nginx configuration snippet
        """
        return """
# Modern TLS configuration for Nginx
ssl_protocols TLSv1.2 TLSv1.3;
ssl_prefer_server_ciphers off;

# TLS 1.3 cipher suites (server preference)
ssl_ciphers 'TLS_AES_256_GCM_SHA384:TLS_AES_128_GCM_SHA256:TLS_CHACHA20_POLY1305_SHA256';

# Certificate configuration
ssl_certificate /path/to/certificate.crt;
ssl_certificate_key /path/to/private.key;
ssl_trusted_certificate /path/to/ca_bundle.crt;

# Session configuration
ssl_session_timeout 1d;
ssl_session_cache shared:SSL:10m;
ssl_session_tickets off;

# OCSP stapling
ssl_stapling on;
ssl_stapling_verify on;
ssl_ocsp_responses /path/to/ocsp_responses;

# Security headers (also handled by middleware)
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
add_header X-Frame-Options "DENY" always;
add_header X-Content-Type-Options "nosniff" always;
"""

    @staticmethod
    def get_apache_config() -> str:
        """Get recommended Apache TLS configuration.

        Returns:
            Apache configuration snippet
        """
        return """
# Modern TLS configuration for Apache
SSLProtocol all -SSLv2 -SSLv3 -TLSv1 -TLSv1.1
SSLCipherSuite TLS_AES_256_GCM_SHA384:TLS_AES_128_GCM_SHA256:TLS_CHACHA20_POLY1305_SHA256
SSLHonorCipherOrder off

# Certificate configuration
SSLCertificateFile /path/to/certificate.crt
SSLCertificateKeyFile /path/to/private.key
SSLCertificateChainFile /path/to/ca_bundle.crt

# Session configuration
SSLSessionCache shmcb:/var/run/apache2/ssl_scache(512000)
SSLSessionCacheTimeout 300
SSLSessionTickets off

# OCSP stapling
SSLUseStapling on
SSLStaplingCache shmcb:/var/run/apache2/ocsp(128000)

# Security headers (also handled by middleware)
Header always set Strict-Transport-Security "max-age=63072000; includeSubDomains; preload"
Header always set X-Frame-Options "DENY"
Header always set X-Content-Type-Options "nosniff"
"""

    @staticmethod
    def validate_tls_version(version: str) -> bool:
        """Validate TLS version meets minimum requirements.

        Args:
            version: TLS version string

        Returns:
            True if version is acceptable
        """
        acceptable_versions = [TLSVersion.TLS_1_2.value, TLSVersion.TLS_1_3.value]
        return version in acceptable_versions

    @staticmethod
    def validate_cipher_suite(cipher: str) -> bool:
        """Validate cipher suite is recommended.

        Args:
            cipher: Cipher suite name

        Returns:
            True if cipher is recommended
        """
        recommended = [cs.value for cs in TLSConfiguration.RECOMMENDED_CIPHER_SUITES]
        return cipher in recommended


def get_security_headers_config(
    hsts_enabled: bool = True,
    csp_enabled: bool = True,
    hsts_preload: bool = False,
) -> SecurityHeaderConfig:
    """Get security headers configuration.

    Args:
        hsts_enabled: Enable HSTS
        csp_enabled: Enable CSP
        hsts_preload: Enable HSTS preload

    Returns:
        SecurityHeaderConfig
    """
    return SecurityHeaderConfig(
        hsts_enabled=hsts_enabled,
        csp_enabled=csp_enabled,
        hsts_preload=hsts_preload,
    )
