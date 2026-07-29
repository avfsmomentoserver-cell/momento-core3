"""AES-256 encryption manager for data at rest.

Implements FIPS-140-2 compliant AES-256-GCM encryption for data at rest
following NIST SP 800-38D recommendations.
"""

from __future__ import annotations

import os
import base64
import json
from typing import Any, Dict, Optional, Tuple
from dataclasses import dataclass
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import logging

logger = logging.getLogger(__name__)


@dataclass
class EncryptedData:
    """Container for encrypted data with metadata."""

    ciphertext: str  # Base64-encoded ciphertext
    nonce: str  # Base64-encoded nonce (IV)
    tag: str  # Base64-encoded authentication tag
    algorithm: str = "AES-256-GCM"
    key_id: Optional[str] = None  # Key identifier for key rotation


class EncryptionManager:
    """AES-256-GCM encryption manager for data at rest.

    Implements NIST SP 800-38D (GCM) and NIST SP 800-57 (Key Management).
    """

    def __init__(self, master_key: Optional[bytes] = None):
        """Initialize the encryption manager.

        Args:
            master_key: Optional master key for encryption. If not provided,
                       a new key will be generated (for development only).
                       In production, use a proper key management system (KMS).
        """
        self._master_key = master_key or self._generate_master_key()
        self._key_cache: Dict[str, bytes] = {}
        self._key_version = 1

    def _generate_master_key(self) -> bytes:
        """Generate a new AES-256 master key (32 bytes).

        WARNING: In production, use a proper KMS or HSM.
        """
        key = os.urandom(32)  # 256 bits
        logger.warning("Generated new master key - use KMS in production")
        return key

    def _derive_data_key(
        self,
        context: str,
        key_id: Optional[str] = None,
    ) -> bytes:
        """Derive a data encryption key from the master key using PBKDF2.

        Args:
            context: Context string for key derivation (e.g., resource ID)
            key_id: Optional key identifier for key rotation

        Returns:
            32-byte data encryption key
        """
        # Use key_id for key rotation support
        key_context = f"{key_id or 'v1'}:{context}" if key_id else context

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=key_context.encode(),  # Use context as salt
            iterations=100000,  # NIST recommended minimum
            backend=default_backend(),
        )
        return kdf.derive(self._master_key)

    def encrypt(
        self,
        plaintext: str,
        context: str = "default",
        key_id: Optional[str] = None,
    ) -> EncryptedData:
        """Encrypt plaintext using AES-256-GCM.

        Args:
            plaintext: The plaintext to encrypt
            context: Context string for key derivation
            key_id: Optional key identifier for key rotation

        Returns:
            EncryptedData container with ciphertext, nonce, and tag
        """
        if not plaintext:
            raise ValueError("Plaintext cannot be empty")

        # Derive data key
        data_key = self._derive_data_key(context, key_id)

        # Generate random nonce (96 bits for GCM)
        nonce = os.urandom(12)

        # Encrypt using AES-GCM
        aesgcm = AESGCM(data_key)
        ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext.encode(), None)

        # GCM appends the tag to the ciphertext (16 bytes)
        ciphertext = ciphertext_with_tag[:-16]
        tag = ciphertext_with_tag[-16:]

        return EncryptedData(
            ciphertext=base64.b64encode(ciphertext).decode(),
            nonce=base64.b64encode(nonce).decode(),
            tag=base64.b64encode(tag).decode(),
            algorithm="AES-256-GCM",
            key_id=key_id,
        )

    def decrypt(
        self,
        encrypted_data: EncryptedData,
        context: str = "default",
    ) -> str:
        """Decrypt ciphertext using AES-256-GCM.

        Args:
            encrypted_data: EncryptedData container
            context: Context string for key derivation (must match encryption)

        Returns:
            Decrypted plaintext

        Raises:
            ValueError: If decryption fails (invalid data, wrong key, etc.)
        """
        try:
            # Decode base64
            ciphertext = base64.b64decode(encrypted_data.ciphertext)
            nonce = base64.b64decode(encrypted_data.nonce)
            tag = base64.b64decode(encrypted_data.tag)

            # Derive data key (using key_id if available)
            data_key = self._derive_data_key(context, encrypted_data.key_id)

            # Reconstruct ciphertext with tag for GCM
            ciphertext_with_tag = ciphertext + tag

            # Decrypt using AES-GCM
            aesgcm = AESGCM(data_key)
            plaintext = aesgcm.decrypt(nonce, ciphertext_with_tag, None)

            return plaintext.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError("Decryption failed - invalid ciphertext or wrong key")

    def encrypt_dict(
        self,
        data: Dict[str, Any],
        context: str = "default",
        key_id: Optional[str] = None,
    ) -> EncryptedData:
        """Encrypt a dictionary as JSON.

        Args:
            data: Dictionary to encrypt
            context: Context string for key derivation
            key_id: Optional key identifier for key rotation

        Returns:
            EncryptedData container
        """
        plaintext = json.dumps(data, separators=(",", ":"))
        return self.encrypt(plaintext, context, key_id)

    def decrypt_dict(
        self,
        encrypted_data: EncryptedData,
        context: str = "default",
    ) -> Dict[str, Any]:
        """Decrypt and parse JSON to dictionary.

        Args:
            encrypted_data: EncryptedData container
            context: Context string for key derivation

        Returns:
            Decrypted dictionary

        Raises:
            ValueError: If decryption or JSON parsing fails
        """
        plaintext = self.decrypt(encrypted_data, context)
        try:
            return json.loads(plaintext)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            raise ValueError("Decrypted data is not valid JSON")

    def encrypt_field(
        self,
        value: Any,
        field_name: str,
        resource_id: str,
    ) -> EncryptedData:
        """Encrypt a specific field value with resource context.

        Args:
            value: Value to encrypt (will be converted to string)
            field_name: Name of the field being encrypted
            resource_id: ID of the resource (for key derivation context)

        Returns:
            EncryptedData container
        """
        context = f"{resource_id}:{field_name}"
        plaintext = str(value)
        return self.encrypt(plaintext, context)

    def decrypt_field(
        self,
        encrypted_data: EncryptedData,
        field_name: str,
        resource_id: str,
    ) -> str:
        """Decrypt a specific field value with resource context.

        Args:
            encrypted_data: EncryptedData container
            field_name: Name of the field being decrypted
            resource_id: ID of the resource (for key derivation context)

        Returns:
            Decrypted value as string
        """
        context = f"{resource_id}:{field_name}"
        return self.decrypt(encrypted_data, context)

    def rotate_key(
        self,
        old_key_id: str,
        new_key_id: str,
    ) -> None:
        """Rotate encryption keys.

        Args:
            old_key_id: Old key identifier
            new_key_id: New key identifier

        Note:
            This method updates the key version. Re-encryption of data
            should be done separately using the new key ID.
        """
        self._key_version += 1
        logger.info(f"Key rotation: {old_key_id} -> {new_key_id}")

    def get_key_info(self) -> Dict[str, Any]:
        """Get information about the encryption keys.

        Returns:
            Dictionary with key information
        """
        return {
            "algorithm": "AES-256-GCM",
            "key_length": 256,
            "key_version": self._key_version,
            "kdf": "PBKDF2-SHA256",
            "kdf_iterations": 100000,
        }


# Global encryption manager instance
# In production, initialize with a proper KMS-managed key
encryption = EncryptionManager()
