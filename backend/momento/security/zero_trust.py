"""Zero-Trust Security Middleware for FastAPI.

Implements zero-trust architecture principles:
- Never trust, always verify
- Least privilege access
- Micro-segmentation
- Continuous authentication
- Risk-based authorization

Compliance: NIST SP 800-207, DoD Zero Trust Architecture
"""

from __future__ import annotations

import time
import ipaddress
from typing import Any, Callable, Dict, List, Optional, Set
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum
import logging

from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .. import config
from .jwt_auth import jwt_auth, TokenPayload, TokenType
from .rbac import rbac, Permission, Scope
from .abac import abac, Subject, Resource, Environment, AccessRequest, NetworkTrust

logger = logging.getLogger(__name__)


class SecurityLevel(str, Enum):
    """Security classification levels."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class RiskLevel(str, Enum):
    """Risk assessment levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityContext:
    """Security context for a request."""

    authenticated: bool = False
    user_id: Optional[int] = None
    email: Optional[str] = None
    role: Optional[str] = None
    tier: Optional[str] = None
    scope: Optional[str] = None
    permissions: Set[Permission] = None
    risk_level: RiskLevel = RiskLevel.LOW
    network_trust: NetworkTrust = NetworkTrust.UNTRUSTED
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_age: Optional[int] = None
    mfa_verified: bool = False
    geo_location: Optional[str] = None

    def __post_init__(self):
        if self.permissions is None:
            self.permissions = set()


@dataclass
class SecurityPolicy:
    """Security policy for endpoint protection."""

    require_auth: bool = True
    require_mfa: bool = False
    required_permissions: Set[Permission] = None
    required_scopes: Set[Scope] = None
    allowed_ip_ranges: List[str] = None
    blocked_ip_ranges: List[str] = None
    max_session_age: int = 86400  # 24 hours
    rate_limit_enabled: bool = True
    security_level: SecurityLevel = SecurityLevel.INTERNAL

    def __post_init__(self):
        if self.required_permissions is None:
            self.required_permissions = set()
        if self.required_scopes is None:
            self.required_scopes = set()
        if self.allowed_ip_ranges is None:
            self.allowed_ip_ranges = []
        if self.blocked_ip_ranges is None:
            self.blocked_ip_ranges = []


class ZeroTrustMiddleware(BaseHTTPMiddleware):
    """Zero-trust security middleware for FastAPI.

    Implements continuous verification and risk-based access control.
    """

    def __init__(
        self,
        app,
        public_paths: Optional[List[str]] = None,
        strict_mode: bool = False,
    ):
        """Initialize zero-trust middleware.

        Args:
            app: FastAPI application
            public_paths: List of public paths (no auth required)
            strict_mode: Enable strict security (deny by default)
        """
        super().__init__(app)
        self.public_paths = public_paths or [
            "/health",
            "/",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
        ]
        self.strict_mode = strict_mode
        self._security_bearer = HTTPBearer(auto_error=False)

        # IP-based trust lists
        self._trusted_networks: List[ipaddress.IPv4Network] = []
        self._blocked_networks: List[ipaddress.IPv4Network] = []

        # Rate limiting tracking (in-memory - use Redis in production)
        self._rate_limits: Dict[str, List[float]] = {}

    def add_trusted_network(self, cidr: str) -> None:
        """Add a trusted network CIDR range.

        Args:
            cidr: CIDR notation (e.g., "10.0.0.0/8")
        """
        self._trusted_networks.append(ipaddress.IPv4Network(cidr))
        logger.info(f"Added trusted network: {cidr}")

    def add_blocked_network(self, cidr: str) -> None:
        """Add a blocked network CIDR range.

        Args:
            cidr: CIDR notation (e.g., "192.168.1.0/24")
        """
        self._blocked_networks.append(ipaddress.IPv4Network(cidr))
        logger.info(f"Added blocked network: {cidr}")

    def _is_public_path(self, path: str) -> bool:
        """Check if path is public (no auth required)."""
        for public_path in self.public_paths:
            if path.startswith(public_path):
                return True
        return False

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request.

        Handles proxies and load balancers.
        """
        # Check for forwarded headers (reverse proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # Direct connection
        return request.client.host if request.client else "unknown"

    def _assess_network_trust(self, ip_address: str) -> NetworkTrust:
        """Assess trust level of client IP address.

        Args:
            ip_address: Client IP address

        Returns:
            NetworkTrust level
        """
        try:
            ip = ipaddress.IPv4Address(ip_address)

            # Check blocked networks first
            for network in self._blocked_networks:
                if ip in network:
                    logger.warning(f"Blocked IP access attempt: {ip_address}")
                    return NetworkTrust.BLOCKED

            # Check trusted networks
            for network in self._trusted_networks:
                if ip in network:
                    return NetworkTrust.TRUSTED

            # Private networks are semi-trusted
            if ip.is_private:
                return NetworkTrust.SEMI_TRUSTED

            # Loopback is trusted
            if ip.is_loopback:
                return NetworkTrust.TRUSTED

            # Public IP is untrusted by default
            return NetworkTrust.UNTRUSTED

        except (ipaddress.AddressValueError, ValueError):
            logger.warning(f"Invalid IP address: {ip_address}")
            return NetworkTrust.UNTRUSTED

    def _extract_token(self, request: Request) -> Optional[str]:
        """Extract JWT token from request.

        Args:
            request: FastAPI request

        Returns:
            JWT token string or None
        """
        # Try Authorization header
        credentials: Optional[HTTPAuthorizationCredentials] = self._security_bearer(
            request
        )
        if credentials:
            return credentials.credentials

        # Try query parameter (less secure, but convenient)
        token = request.query_params.get("token")
        if token:
            return token

        return None

    def _build_security_context(
        self,
        request: Request,
        token: Optional[str],
    ) -> SecurityContext:
        """Build security context from request and token.

        Args:
            request: FastAPI request
            token: JWT token (optional)

        Returns:
            SecurityContext with all available information
        """
        context = SecurityContext()

        # Request metadata
        context.ip_address = self._get_client_ip(request)
        context.user_agent = request.headers.get("User-Agent")
        context.network_trust = self._assess_network_trust(context.ip_address)

        # Token validation
        if token:
            payload = jwt_auth.decode_token(token)
            if payload:
                context.authenticated = True
                context.user_id = payload.sub
                context.email = payload.email
                context.role = payload.role
                context.tier = payload.tier
                context.scope = payload.scope

                # Calculate session age
                iat = datetime.fromtimestamp(payload.iat, timezone.utc)
                context.session_age = int((datetime.now(timezone.utc) - iat).total_seconds())

                # Get user permissions from RBAC
                if context.role:
                    role = rbac.get_role(context.role)
                    if role:
                        context.permissions = role.permissions

        # Risk assessment
        context.risk_level = self._assess_risk(context)

        return context

    def _assess_risk(self, context: SecurityContext) -> RiskLevel:
        """Assess risk level based on security context.

        Args:
            context: SecurityContext

        Returns:
            RiskLevel
        """
        risk_score = 0

        # Network trust factor
        if context.network_trust == NetworkTrust.BLOCKED:
            return RiskLevel.CRITICAL
        elif context.network_trust == NetworkTrust.UNTRUSTED:
            risk_score += 30
        elif context.network_trust == NetworkTrust.SEMI_TRUSTED:
            risk_score += 10

        # Authentication factor
        if not context.authenticated:
            risk_score += 40
        elif not context.mfa_verified:
            risk_score += 20

        # Session age factor
        if context.session_age and context.session_age > 86400:  # > 24 hours
            risk_score += 15
        elif context.session_age and context.session_age > 3600:  # > 1 hour
            risk_score += 5

        # Tier factor
        if context.tier == "free":
            risk_score += 10
        elif context.tier in ("premium", "pro"):
            risk_score -= 5

        # Determine risk level
        if risk_score >= 70:
            return RiskLevel.CRITICAL
        elif risk_score >= 50:
            return RiskLevel.HIGH
        elif risk_score >= 30:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _check_rate_limit(self, identifier: str, limit: int = 100, window: int = 60) -> bool:
        """Check rate limit for an identifier.

        Args:
            identifier: Unique identifier (IP or user ID)
            limit: Max requests per window
            window: Time window in seconds

        Returns:
            True if request is allowed, False otherwise
        """
        now = time.time()

        # Clean old entries
        if identifier in self._rate_limits:
            self._rate_limits[identifier] = [
                t for t in self._rate_limits[identifier] if now - t < window
            ]

        # Check limit
        if identifier not in self._rate_limits:
            self._rate_limits[identifier] = []

        if len(self._rate_limits[identifier]) >= limit:
            logger.warning(f"Rate limit exceeded for {identifier}")
            return False

        # Add current request
        self._rate_limits[identifier].append(now)
        return True

    async def dispatch(self, request: Request, call_next: Callable) -> JSONResponse:
        """Process request through zero-trust middleware.

        Args:
            request: FastAPI request
            call_next: Next middleware/endpoint

        Returns:
            JSONResponse
        """
        path = request.url.path

        # Skip public paths
        if self._is_public_path(path):
            return await call_next(request)

        # Extract token
        token = self._extract_token(request)

        # Build security context
        context = self._build_security_context(request, token)

        # Store context in request state for use in endpoints
        request.state.security_context = context

        # Check if authentication is required
        if not context.authenticated:
            if self.strict_mode:
                logger.warning(f"Unauthenticated access attempt to {path} from {context.ip_address}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            # In non-strict mode, continue without auth (legacy compatibility)
            return await call_next(request)

        # Check network trust
        if context.network_trust == NetworkTrust.BLOCKED:
            logger.warning(f"Blocked IP access attempt: {context.ip_address}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access from this IP is blocked",
            )

        # Check rate limit
        identifier = str(context.user_id) if context.user_id else context.ip_address
        if not self._check_rate_limit(identifier):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
            )

        # Log high-risk requests
        if context.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            logger.warning(
                f"High-risk request: {path} from {context.ip_address}, "
                f"risk={context.risk_level}, user={context.email}"
            )

        # Continue to next middleware/endpoint
        return await call_next(request)


def require_permission(permission: Permission) -> Callable:
    """Dependency to require a specific permission.

    Args:
        permission: Required permission

    Returns:
        FastAPI dependency function
    """
    async def check_permission(request: Request) -> bool:
        context: SecurityContext = getattr(request.state, "security_context", SecurityContext())

        if not context.authenticated:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        if permission not in context.permissions:
            logger.warning(
                f"Permission denied: {permission} for user {context.email} "
                f"accessing {request.url.path}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required",
            )

        return True

    return check_permission


def require_scope(scope: Scope) -> Callable:
    """Dependency to require a specific scope.

    Args:
        scope: Required scope

    Returns:
        FastAPI dependency function
    """
    async def check_scope(request: Request) -> bool:
        context: SecurityContext = getattr(request.state, "security_context", SecurityContext())

        if not context.authenticated:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        # Check if user has scope access via RBAC
        if context.role:
            role = rbac.get_role(context.role)
            if role and scope in role.allowed_scopes:
                return True

        logger.warning(
            f"Scope denied: {scope} for user {context.email} "
            f"accessing {request.url.path}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Scope '{scope}' required",
        )

    return check_scope


def require_mfa() -> Callable:
    """Dependency to require MFA verification.

    Returns:
        FastAPI dependency function
    """
    async def check_mfa(request: Request) -> bool:
        context: SecurityContext = getattr(request.state, "security_context", SecurityContext())

        if not context.authenticated:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        if not context.mfa_verified:
            logger.warning(
                f"MFA required for user {context.email} accessing {request.url.path}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Multi-factor authentication required",
            )

        return True

    return check_mfa
