"""Authentication module for V5 security hardening.

This module provides military-grade authentication systems including:
- JWT-based stateless authentication (RSA-256 signed)
- OAuth 2.0 / OpenID Connect provider
- Multi-factor authentication (TOTP, SMS, Hardware keys)
- Session management

Security Standards:
- DO-178C DAL_A: Critical security components
- ISO 26262 ASIL_D: Highest safety integrity
- NIST SP 800-53: AC-2, AC-7, AC-11, AC-12, AC-17, AC-19
- ISO 27001: A.9.3, A.9.4
"""

from .jwt_auth import JWTAuthManager, TokenClaims, TokenPair, get_jwt_manager

__all__ = [
    "JWTAuthManager",
    "TokenClaims",
    "TokenPair",
    "get_jwt_manager",
]
