"""Multi-Factor Authentication (MFA) system for V5.

Implements TOTP (Time-based One-Time Password) and backup codes following
NIST SP 800-63B Digital Identity Guidelines and RFC 6238.
"""

from __future__ import annotations

import secrets
import pyotp
import qrcode
import io
import base64
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class MFAStatus(str, Enum):
    """MFA enrollment and verification status."""

    DISABLED = "disabled"
    ENROLLING = "enrolling"
    ENABLED = "enabled"
    LOCKED = "locked"


class MFAVerificationResult(str, Enum):
    """MFA verification result."""

    SUCCESS = "success"
    INVALID_CODE = "invalid_code"
    EXPIRED_CODE = "expired_code"
    RATE_LIMITED = "rate_limited"
    BACKUP_USED = "backup_used"
    ACCOUNT_LOCKED = "account_locked"


@dataclass
class MFAConfig:
    """MFA configuration for a user."""

    user_id: int
    status: MFAStatus = MFAStatus.DISABLED
    secret: Optional[str] = None  # TOTP secret
    backup_codes: List[str] = None  # Backup recovery codes
    backup_codes_used: List[str] = None  # Used backup codes
    verified_at: Optional[datetime] = None
    failed_attempts: int = 0
    locked_until: Optional[datetime] = None
    last_used_at: Optional[datetime] = None

    def __post_init__(self):
        if self.backup_codes is None:
            self.backup_codes = []
        if self.backup_codes_used is None:
            self.backup_codes_used = []


@dataclass
class MFAEnrollmentResponse:
    """Response when initiating MFA enrollment."""

    secret: str
    qr_code_url: str  # Data URL for QR code image
    backup_codes: List[str]
    uri: str  # otpauth:// URI for manual entry


@dataclass
class MFAVerificationResponse:
    """Response after MFA verification."""

    result: MFAVerificationResult
    message: str
    backup_remaining: int = 0  # Remaining backup codes
    lockout_remaining: Optional[int] = None  # Seconds until lockout expires


class MFAManager:
    """Multi-Factor Authentication manager.

    Implements NIST SP 800-63B Section 5.1.3.2 (Memorized Secret Verifiers)
    and RFC 6238 (TOTP).
    """

    def __init__(
        self,
        issuer: str = "Momento V5",
        digits: int = 6,
        interval: int = 30,
        backup_codes_count: int = 10,
        max_failed_attempts: int = 5,
        lockout_duration: int = 900,  # 15 minutes
    ):
        """Initialize the MFA manager.

        Args:
            issuer: Application name for TOTP URI
            digits: Number of digits in TOTP code (6 or 8)
            interval: TOTP time interval in seconds
            backup_codes_count: Number of backup codes to generate
            max_failed_attempts: Maximum failed attempts before lockout
            lockout_duration: Lockout duration in seconds
        """
        self.issuer = issuer
        self.digits = digits
        self.interval = interval
        self.backup_codes_count = backup_codes_count
        self.max_failed_attempts = max_failed_attempts
        self.lockout_duration = lockout_duration

    def generate_secret(self) -> str:
        """Generate a new TOTP secret.

        Returns:
            Base32-encoded secret key
        """
        return pyotp.random_base32()

    def generate_backup_codes(self, count: Optional[int] = None) -> List[str]:
        """Generate backup recovery codes.

        Args:
            count: Number of codes to generate (default from config)

        Returns:
            List of backup codes (8-character alphanumeric)
        """
        count = count or self.backup_codes_count
        codes = []
        for _ in range(count):
            # Generate 8-character alphanumeric code
            code = secrets.token_hex(4).upper()
            codes.append(code)
        return codes

    def create_totp(self, secret: str) -> pyotp.TOTP:
        """Create a TOTP object for a given secret.

        Args:
            secret: Base32-encoded secret

        Returns:
            pyotp.TOTP object
        """
        return pyotp.TOTP(
            secret,
            digits=self.digits,
            interval=self.interval,
            issuer=self.issuer,
        )

    def initiate_enrollment(
        self,
        user_id: int,
        email: str,
    ) -> MFAEnrollmentResponse:
        """Initiate MFA enrollment for a user.

        Args:
            user_id: User ID
            email: User email for TOTP URI

        Returns:
            MFAEnrollmentResponse with secret, QR code, and backup codes
        """
        secret = self.generate_secret()
        backup_codes = self.generate_backup_codes()

        # Create TOTP URI
        totp = self.create_totp(secret)
        uri = totp.provisioning_uri(
            name=email,
            issuer_name=self.issuer,
        )

        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        qr_code_url = f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}"

        logger.info(f"MFA enrollment initiated for user {user_id}")

        return MFAEnrollmentResponse(
            secret=secret,
            qr_code_url=qr_code_url,
            backup_codes=backup_codes,
            uri=uri,
        )

    def verify_code(
        self,
        config: MFAConfig,
        code: str,
        window: int = 1,
    ) -> MFAVerificationResponse:
        """Verify a TOTP code or backup code.

        Args:
            config: MFA configuration for the user
            code: Code to verify (6-digit TOTP or backup code)
            window: Time window for TOTP (default 1 = +/- 30 seconds)

        Returns:
            MFAVerificationResponse with result and details
        """
        now = datetime.now(timezone.utc)

        # Check if account is locked
        if config.locked_until and now < config.locked_until:
            remaining = int((config.locked_until - now).total_seconds())
            return MFAVerificationResponse(
                result=MFAVerificationResult.ACCOUNT_LOCKED,
                message="Account is temporarily locked due to too many failed attempts",
                lockout_remaining=remaining,
            )

        # Clear expired lockout
        if config.locked_until and now >= config.locked_until:
            config.locked_until = None
            config.failed_attempts = 0

        # Check if it's a backup code
        if len(code) == 8 and code.upper() in config.backup_codes:
            if code.upper() in config.backup_codes_used:
                return MFAVerificationResponse(
                    result=MFAVerificationResult.INVALID_CODE,
                    message="Backup code has already been used",
                )

            # Mark backup code as used
            config.backup_codes_used.append(code.upper())
            config.backup_codes.remove(code.upper())
            config.failed_attempts = 0
            config.last_used_at = now

            logger.info(f"Backup code used for user {config.user_id}")

            return MFAVerificationResponse(
                result=MFAVerificationResult.BACKUP_USED,
                message="Backup code verified successfully",
                backup_remaining=len(config.backup_codes),
            )

        # Verify TOTP code
        if not config.secret:
            return MFAVerificationResponse(
                result=MFAVerificationResult.INVALID_CODE,
                message="MFA not configured for this account",
            )

        totp = self.create_totp(config.secret)

        # Verify with time window (allow 1 interval before/after)
        if totp.verify(code, valid_window=window):
            # Reset failed attempts on success
            config.failed_attempts = 0
            config.last_used_at = now

            logger.info(f"TOTP code verified for user {config.user_id}")

            return MFAVerificationResponse(
                result=MFAVerificationResult.SUCCESS,
                message="Code verified successfully",
            )
        else:
            # Increment failed attempts
            config.failed_attempts += 1

            # Check if should lock account
            if config.failed_attempts >= self.max_failed_attempts:
                config.locked_until = now + timedelta(seconds=self.lockout_duration)
                config.status = MFAStatus.LOCKED

                logger.warning(
                    f"User {config.user_id} locked after {config.failed_attempts} failed MFA attempts"
                )

                return MFAVerificationResponse(
                    result=MFAVerificationResult.ACCOUNT_LOCKED,
                    message=f"Too many failed attempts. Account locked for {self.lockout_duration // 60} minutes.",
                    lockout_remaining=self.lockout_duration,
                )

            logger.warning(f"Failed MFA attempt {config.failed_attempts} for user {config.user_id}")

            return MFAVerificationResponse(
                result=MFAVerificationResult.INVALID_CODE,
                message="Invalid code",
            )

    def enable_mfa(
        self,
        config: MFAConfig,
        verification_code: str,
    ) -> bool:
        """Enable MFA after successful verification.

        Args:
            config: MFA configuration
            verification_code: Code to verify before enabling

        Returns:
            True if MFA enabled successfully
        """
        result = self.verify_code(config, verification_code)

        if result.result == MFAVerificationResult.SUCCESS:
            config.status = MFAStatus.ENABLED
            config.verified_at = datetime.now(timezone.utc)
            config.failed_attempts = 0
            logger.info(f"MFA enabled for user {config.user_id}")
            return True

        return False

    def disable_mfa(
        self,
        config: MFAConfig,
        verification_code: Optional[str] = None,
    ) -> bool:
        """Disable MFA for a user.

        Args:
            config: MFA configuration
            verification_code: Optional code to verify before disabling

        Returns:
            True if MFA disabled successfully
        """
        # If verification code provided, verify it
        if verification_code:
            result = self.verify_code(config, verification_code)
            if result.result not in [
                MFAVerificationResult.SUCCESS,
                MFAVerificationResult.BACKUP_USED,
            ]:
                return False

        config.status = MFAStatus.DISABLED
        config.secret = None
        config.backup_codes = []
        config.backup_codes_used = []
        config.verified_at = None
        config.failed_attempts = 0
        config.locked_until = None

        logger.info(f"MFA disabled for user {config.user_id}")
        return True

    def regenerate_backup_codes(
        self,
        config: MFAConfig,
        verification_code: str,
    ) -> Optional[List[str]]:
        """Regenerate backup codes after verification.

        Args:
            config: MFA configuration
            verification_code: Code to verify before regenerating

        Returns:
            New backup codes if successful, None otherwise
        """
        result = self.verify_code(config, verification_code)

        if result.result in [
            MFAVerificationResult.SUCCESS,
            MFAVerificationResult.BACKUP_USED,
        ]:
            new_codes = self.generate_backup_codes()
            config.backup_codes = new_codes
            config.backup_codes_used = []
            logger.info(f"Backup codes regenerated for user {config.user_id}")
            return new_codes

        return None

    def get_mfa_status(self, config: MFAConfig) -> Dict[str, Any]:
        """Get MFA status information.

        Args:
            config: MFA configuration

        Returns:
            Dictionary with MFA status (excludes sensitive data)
        """
        now = datetime.now(timezone.utc)
        is_locked = config.locked_until and now < config.locked_until

        return {
            "status": config.status,
            "enabled": config.status == MFAStatus.ENABLED,
            "locked": is_locked,
            "lockout_remaining": int((config.locked_until - now).total_seconds()) if is_locked else 0,
            "backup_codes_remaining": len(config.backup_codes),
            "last_used_at": config.last_used_at.isoformat() if config.last_used_at else None,
            "verified_at": config.verified_at.isoformat() if config.verified_at else None,
        }


# Global MFA manager instance
mfa = MFAManager()
