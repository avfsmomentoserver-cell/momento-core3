"""JWT-based authentication system for V5.

Implements JWT with RS256 asymmetric signatures for enterprise-grade security.
Supports access tokens, refresh tokens, and OAuth 2.0 integration.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Optional, List

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from jose import JWTError, jwt
from pydantic import BaseModel

from .. import config


class TokenType(str, Enum):
    """Token types for JWT."""

    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"


class TokenPayload(BaseModel):
    """JWT token payload structure."""

    sub: int  # User ID
    email: str
    role: str
    tier: str
    scope: str  # V5 multi-scope
    token_type: TokenType
    exp: int
    iat: int
    jti: str  # JWT ID for revocation
    iss: str = "momento-v5"
    aud: str = "momento-api"


class JWTManager:
    """JWT token manager with RS256 asymmetric signatures."""

    def __init__(self):
        self._private_key: Optional[rsa.RSAPrivateKey] = None
        self._public_key: Optional[rsa.RSAPublicKey] = None
        self._algorithm = "RS256"
        self._access_token_ttl = timedelta(hours=1)
        self._refresh_token_ttl = timedelta(days=7)
        self._api_key_ttl = timedelta(days=30)

    def _generate_keys(self) -> None:
        """Generate RSA key pair for JWT signing."""
        if self._private_key is None:
            self._private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend(),
            )
            self._public_key = self._private_key.public_key()

    def _get_private_key_pem(self) -> bytes:
        """Get private key in PEM format."""
        self._generate_keys()
        return self._private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

    def _get_public_key_pem(self) -> bytes:
        """Get public key in PEM format."""
        self._generate_keys()
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    def create_access_token(
        self,
        user_id: int,
        email: str,
        role: str,
        tier: str,
        scope: str = "public",
        additional_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a JWT access token."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "email": email,
            "role": role,
            "tier": tier,
            "scope": scope,
            "token_type": TokenType.ACCESS,
            "exp": int((now + self._access_token_ttl).timestamp()),
            "iat": int(now.timestamp()),
            "jti": self._generate_jti(),
            "iss": "momento-v5",
            "aud": "momento-api",
        }
        if additional_claims:
            payload.update(additional_claims)

        return jwt.encode(
            payload,
            self._get_private_key_pem(),
            algorithm=self._algorithm,
        )

    def create_refresh_token(
        self,
        user_id: int,
        email: str,
    ) -> str:
        """Create a JWT refresh token."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "email": email,
            "token_type": TokenType.REFRESH,
            "exp": int((now + self._refresh_token_ttl).timestamp()),
            "iat": int(now.timestamp()),
            "jti": self._generate_jti(),
            "iss": "momento-v5",
            "aud": "momento-api",
        }

        return jwt.encode(
            payload,
            self._get_private_key_pem(),
            algorithm=self._algorithm,
        )

    def create_api_key(
        self,
        user_id: int,
        email: str,
        role: str,
        scope: str,
        name: str,
    ) -> str:
        """Create an API key token."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "email": email,
            "role": role,
            "scope": scope,
            "token_type": TokenType.API_KEY,
            "name": name,
            "exp": int((now + self._api_key_ttl).timestamp()),
            "iat": int(now.timestamp()),
            "jti": self._generate_jti(),
            "iss": "momento-v5",
            "aud": "momento-api",
        }

        return jwt.encode(
            payload,
            self._get_private_key_pem(),
            algorithm=self._algorithm,
        )

    def decode_token(self, token: str) -> Optional[TokenPayload]:
        """Decode and validate a JWT token."""
        try:
            payload = jwt.decode(
                token,
                self._get_public_key_pem(),
                algorithms=[self._algorithm],
                audience="momento-api",
                issuer="momento-v5",
            )
            return TokenPayload(**payload)
        except JWTError as e:
            # Log error in production
            return None

    def verify_token(self, token: str, token_type: TokenType) -> Optional[TokenPayload]:
        """Verify token type and return payload if valid."""
        payload = self.decode_token(token)
        if payload and payload.token_type == token_type:
            return payload
        return None

    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """Create a new access token from a refresh token."""
        payload = self.verify_token(refresh_token, TokenType.REFRESH)
        if not payload:
            return None

        # Create new access token with user info from refresh token
        return self.create_access_token(
            user_id=payload.sub,
            email=payload.email,
            role="user",  # Need to fetch from DB
            tier="free",  # Need to fetch from DB
            scope="public",  # Need to fetch from DB
        )

    def _generate_jti(self) -> str:
        """Generate a unique JWT ID."""
        import secrets
        return secrets.token_urlsafe(16)

    def revoke_token(self, jti: str) -> None:
        """Revoke a token by its JTI (store in revocation list)."""
        # TODO: Implement token revocation storage (Redis or database)
        pass

    def is_token_revoked(self, jti: str) -> bool:
        """Check if a token has been revoked."""
        # TODO: Check revocation list
        return False


# Global JWT manager instance
jwt_auth = JWTManager()
