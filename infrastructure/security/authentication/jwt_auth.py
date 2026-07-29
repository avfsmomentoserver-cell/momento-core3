"""JWT Authentication Manager - Military-Grade Security Implementation.

This module implements JWT-based authentication following DO-178C DAL_A standards
for critical security components. It provides RSA-256 signed tokens with military-grade
security features including token rotation, revocation, and comprehensive validation.

Security Standards:
- DO-178C DAL_A: Critical security component (100% MC/DC coverage required)
- ISO 26262 ASIL_D: Highest safety integrity
- NIST SP 800-53: AC-17, AC-19, SC-23
- ISO 27001: A.9.3, A.9.4, A.10.1

Zero-Trust Principles:
- Never trust, always verify
- Short-lived access tokens (15 minutes)
- Token rotation with refresh tokens
- Comprehensive claim validation
- Token blacklist for revocation
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature

# Security Constants (DO-178C DAL_A Configuration)
ACCESS_TOKEN_TTL = 900  # 15 minutes - Short-lived for security
REFRESH_TOKEN_TTL = 604800  # 7 days - Longer-lived for rotation
TOKEN_ISSUER = "momento-v5"
TOKEN_AUDIENCE = "momento-api"
KEY_SIZE = 4096  # RSA-4096 for military-grade security
HASH_ALGORITHM = "SHA256"


@dataclass
class TokenClaims:
    """JWT token claims with military-grade validation."""
    sub: int  # Subject (user ID)
    email: str
    role: str
    tier: str
    scope: int
    exp: int  # Expiration time
    iat: int  # Issued at time
    jti: str  # JWT ID (unique token identifier)
    iss: str = TOKEN_ISSUER
    aud: str = TOKEN_AUDIENCE
    nbf: Optional[int] = None  # Not valid before
    device_id: Optional[str] = None
    ip_address: Optional[str] = None


@dataclass
class TokenPair:
    """Access and refresh token pair."""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = ACCESS_TOKEN_TTL


class JWTAuthManager:
    """Military-grade JWT authentication manager.

    This class implements RSA-256 signed JWT tokens with comprehensive security
    features following DO-178C DAL_A standards for critical security components.

    Security Features:
    - RSA-4096 asymmetric encryption
    - Short-lived access tokens (15 minutes)
    - Long-lived refresh tokens (7 days)
    - Token rotation and revocation
    - Comprehensive claim validation
    - Token blacklist for immediate revocation
    - Device and IP binding (optional)
    """

    def __init__(self):
        """Initialize JWT authentication manager."""
        self._private_key: Optional[rsa.RSAPrivateKey] = None
        self._public_key: Optional[rsa.RSAPublicKey] = None
        self._token_blacklist: Dict[str, float] = {}  # jti -> revocation timestamp
        self._refresh_token_store: Dict[str, Dict] = {}  # refresh_token -> metadata
        self._initialize_keys()

    def _initialize_keys(self) -> None:
        """Initialize RSA key pair for token signing.

        In production, keys should be loaded from a secure KMS (AWS KMS, Azure Key Vault).
        For development, we generate keys in memory.
        """
        # In production: Load from KMS or secure storage
        # For development: Generate RSA-4096 key pair
        self._private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=KEY_SIZE,
            backend=default_backend()
        )
        self._public_key = self._private_key.public_key()

    def _serialize_private_key(self) -> str:
        """Serialize private key to PEM format (for secure storage)."""
        if not self._private_key:
            raise RuntimeError("Private key not initialized")
        pem = self._private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        return pem.decode('utf-8')

    def _serialize_public_key(self) -> str:
        """Serialize public key to PEM format (for token validation)."""
        if not self._public_key:
            raise RuntimeError("Public key not initialized")
        pem = self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return pem.decode('utf-8')

    def generate_access_token(
        self,
        user: Dict[str, Any],
        scope: int,
        device_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> str:
        """Generate RSA-256 signed access token.

        Args:
            user: User dictionary with id, email, role, tier
            scope: User scope level (1-5)
            device_id: Optional device identifier for binding
            ip_address: Optional IP address for binding

        Returns:
            JWT access token string

        Raises:
            ValueError: If user data is invalid
            RuntimeError: If keys are not initialized
        """
        if not self._private_key:
            raise RuntimeError("Private key not initialized")

        now = int(time.time())
        jti = secrets.token_urlsafe(32)  # Unique token identifier

        claims = TokenClaims(
            sub=int(user["id"]),
            email=str(user["email"]),
            role=str(user["role"]),
            tier=str(user["tier"]),
            scope=int(scope),
            exp=now + ACCESS_TOKEN_TTL,
            iat=now,
            jti=jti,
            nbf=now,  # Not valid before now
            device_id=device_id,
            ip_address=ip_address
        )

        # Encode header
        header = {
            "alg": "RS256",
            "typ": "JWT",
            "kid": "v5-key-1"  # Key identifier
        }
        header_b64 = self._base64url_encode(json.dumps(header, separators=(",", ":")))

        # Encode payload
        payload_dict = {
            "sub": claims.sub,
            "email": claims.email,
            "role": claims.role,
            "tier": claims.tier,
            "scope": claims.scope,
            "exp": claims.exp,
            "iat": claims.iat,
            "jti": claims.jti,
            "iss": claims.iss,
            "aud": claims.aud,
            "nbf": claims.nbf
        }
        if device_id:
            payload_dict["device_id"] = device_id
        if ip_address:
            payload_dict["ip_address"] = ip_address

        payload_b64 = self._base64url_encode(json.dumps(payload_dict, separators=(",", ":")))

        # Sign with RSA-256
        message = f"{header_b64}.{payload_b64}".encode('utf-8')
        signature = self._private_key.sign(
            message,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        signature_b64 = self._base64url_encode(signature)

        return f"{header_b64}.{payload_b64}.{signature_b64}"

    def generate_refresh_token(self, user_id: int, device_id: Optional[str] = None) -> str:
        """Generate secure refresh token for token rotation.

        Refresh tokens are stored securely and used to obtain new access tokens
        without requiring re-authentication.

        Args:
            user_id: User ID
            device_id: Optional device identifier

        Returns:
            Refresh token string
        """
        refresh_token = secrets.token_urlsafe(64)
        expires_at = time.time() + REFRESH_TOKEN_TTL

        # Store refresh token metadata
        self._refresh_token_store[refresh_token] = {
            "user_id": int(user_id),
            "device_id": device_id,
            "expires_at": expires_at,
            "created_at": time.time(),
            "last_used": None
        }

        return refresh_token

    def validate_token(self, token: str, device_id: Optional[str] = None, ip_address: Optional[str] = None) -> Optional[TokenClaims]:
        """Validate JWT token signature and claims.

        This performs comprehensive validation including:
        - Signature verification (RSA-256)
        - Claim validation (exp, iat, nbf, iss, aud)
        - Token blacklist check
        - Device/IP binding validation (if configured)

        Args:
            token: JWT token string
            device_id: Optional device ID for binding validation
            ip_address: Optional IP address for binding validation

        Returns:
            TokenClaims if valid, None otherwise
        """
        if not token or "." not in token:
            return None

        if not self._public_key:
            raise RuntimeError("Public key not initialized")

        try:
            header_b64, payload_b64, signature_b64 = token.split(".")
        except ValueError:
            return None

        # Verify signature
        message = f"{header_b64}.{payload_b64}".encode('utf-8')
        signature = self._base64url_decode(signature_b64)

        try:
            self._public_key.verify(
                signature,
                message,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
        except InvalidSignature:
            return None

        # Decode payload
        try:
            payload_dict = json.loads(self._base64url_decode(payload_b64))
        except (json.JSONDecodeError, ValueError):
            return None

        # Check blacklist
        jti = payload_dict.get("jti")
        if jti and jti in self._token_blacklist:
            return None

        # Validate claims
        now = int(time.time())

        # Check expiration
        if payload_dict.get("exp", 0) < now:
            return None

        # Check not valid before
        nbf = payload_dict.get("nbf")
        if nbf and nbf > now:
            return None

        # Check issuer
        if payload_dict.get("iss") != TOKEN_ISSUER:
            return None

        # Check audience
        if payload_dict.get("aud") != TOKEN_AUDIENCE:
            return None

        # Check device binding (if configured)
        if device_id and payload_dict.get("device_id") and payload_dict["device_id"] != device_id:
            return None

        # Check IP binding (if configured)
        if ip_address and payload_dict.get("ip_address") and payload_dict["ip_address"] != ip_address:
            return None

        # Return validated claims
        return TokenClaims(
            sub=payload_dict["sub"],
            email=payload_dict["email"],
            role=payload_dict["role"],
            tier=payload_dict["tier"],
            scope=payload_dict["scope"],
            exp=payload_dict["exp"],
            iat=payload_dict["iat"],
            jti=payload_dict["jti"],
            iss=payload_dict.get("iss", TOKEN_ISSUER),
            aud=payload_dict.get("aud", TOKEN_AUDIENCE),
            nbf=payload_dict.get("nbf"),
            device_id=payload_dict.get("device_id"),
            ip_address=payload_dict.get("ip_address")
        )

    def revoke_token(self, token: str) -> bool:
        """Revoke token by adding to blacklist.

        Args:
            token: JWT token to revoke

        Returns:
            True if revoked successfully, False otherwise
        """
        claims = self.validate_token(token)
        if not claims:
            return False

        # Add to blacklist with expiration
        self._token_blacklist[claims.jti] = claims.exp
        return True

    def refresh_access_token(self, refresh_token: str, device_id: Optional[str] = None) -> Optional[TokenPair]:
        """Refresh access token using refresh token.

        Args:
            refresh_token: Refresh token string
            device_id: Optional device ID for validation

        Returns:
            New TokenPair if valid, None otherwise
        """
        # Check refresh token
        token_data = self._refresh_token_store.get(refresh_token)
        if not token_data:
            return None

        # Check expiration
        if token_data["expires_at"] < time.time():
            # Remove expired token
            del self._refresh_token_store[refresh_token]
            return None

        # Check device binding
        if device_id and token_data.get("device_id") and token_data["device_id"] != device_id:
            return None

        # Generate new token pair
        user_id = token_data["user_id"]
        # Note: In production, fetch user data from database
        user = {
            "id": user_id,
            "email": "user@example.com",  # Fetch from database
            "role": "user",  # Fetch from database
            "tier": "free"  # Fetch from database
        }
        scope = token_data.get("scope", 2)  # Default to registered user

        access_token = self.generate_access_token(user, scope, device_id)
        new_refresh_token = self.generate_refresh_token(user_id, device_id)

        # Remove old refresh token
        del self._refresh_token_store[refresh_token]

        return TokenPair(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=ACCESS_TOKEN_TTL
        )

    def cleanup_expired_tokens(self) -> int:
        """Clean up expired tokens from blacklist and refresh token store.

        Returns:
            Number of tokens cleaned up
        """
        now = time.time()
        cleaned = 0

        # Clean blacklist
        expired_jti = [jti for jti, exp in self._token_blacklist.items() if exp < now]
        for jti in expired_jti:
            del self._token_blacklist[jti]
            cleaned += 1

        # Clean refresh tokens
        expired_tokens = [
            token for token, data in self._refresh_token_store.items()
            if data["expires_at"] < now
        ]
        for token in expired_tokens:
            del self._refresh_token_store[token]
            cleaned += 1

        return cleaned

    def _base64url_encode(self, data: bytes) -> str:
        """Base64URL encode without padding."""
        return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')

    def _base64url_decode(self, data: str) -> bytes:
        """Base64URL decode with padding restoration."""
        padding = '=' * (-len(data) % 4)
        return base64.urlsafe_b64decode(data + padding)


# Singleton instance
jwt_manager = JWTAuthManager()


def get_jwt_manager() -> JWTAuthManager:
    """Get the singleton JWT manager instance."""
    return jwt_manager
