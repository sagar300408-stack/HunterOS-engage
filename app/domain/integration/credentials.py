import abc
import base64
import hashlib
import json
import logging
import os
from typing import Dict, Any, Optional
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken

from app.domain.integration.models import IntegrationConnection
from app.config import get_settings

logger = logging.getLogger("hunteros.integration.credentials")


class CredentialError(Exception):
    """Base exception for all integration credential errors."""
    pass


class CredentialEncryptionError(CredentialError):
    """Raised when credential encryption fails."""
    pass


class CredentialDecryptionError(CredentialError):
    """Raised when credential decryption fails."""
    pass


class CredentialProvider(abc.ABC):
    """
    Abstract interface for managing integration credentials securely.
    Ensures that the rest of HunterOS never accesses the raw JSON directly,
    allowing future migration to KMS or Vault.
    """
    
    @abc.abstractmethod
    def store_credentials(self, connection: IntegrationConnection, credentials: Dict[str, Any]) -> None:
        pass
        
    @abc.abstractmethod
    def retrieve_credentials(self, connection: IntegrationConnection) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    def clear_credentials(self, connection: IntegrationConnection) -> None:
        pass


class EncryptedCredentialProvider(CredentialProvider):
    """
    Authenticated encryption provider using Fernet (AES-128-CBC + HMAC-SHA256).
    Encrypts access and refresh tokens before storing in database JSON column.
    Guarantees that tokens are never persisted in plaintext.
    Supports token refresh workflows and backward-compatible access for unencrypted legacy records.
    """
    
    def __init__(self, key: Optional[str] = None):
        self._key = key
        self._fernet: Optional[Fernet] = None
        self._init_fernet()

    def _init_fernet(self) -> None:
        key = self._key
        settings = get_settings()
        
        if not key:
            key = getattr(settings, "oauth_encryption_key", None)
            
        if not key:
            key = os.environ.get("OAUTH_ENCRYPTION_KEY")
            
        if not key:
            if settings.is_production:
                raise RuntimeError("OAUTH_ENCRYPTION_KEY must be configured in production environment.")
            # For development and testing environments, derive a stable deterministic Fernet key from dashboard_secret_key
            secret = getattr(settings, "dashboard_secret_key", "change-me-in-production-32-chars-min")
            derived = hashlib.sha256(secret.encode("utf-8")).digest()
            key = base64.urlsafe_b64encode(derived).decode("utf-8")
            logger.warning("OAUTH_ENCRYPTION_KEY not set. Using derived development encryption key.")
            
        try:
            key_bytes = key.encode("utf-8") if isinstance(key, str) else key
            self._fernet = Fernet(key_bytes)
        except Exception as e:
            raise ValueError(f"Invalid OAUTH_ENCRYPTION_KEY: {e}")

    def store_credentials(self, connection: IntegrationConnection, credentials: Dict[str, Any]) -> None:
        """
        Encrypts credentials with Fernet and persists ciphertext envelope in connection.credentials_json.
        Never persists plaintext credentials. Prevents double-encryption.
        """
        if not credentials:
            connection.credentials_json = {}
            return
            
        # Prevent double-encryption if credentials are already encrypted envelope
        if isinstance(credentials, dict) and credentials.get("__encrypted__") is True:
            connection.credentials_json = credentials
            return
            
        try:
            raw_json = json.dumps(credentials)
            ciphertext = self._fernet.encrypt(raw_json.encode("utf-8")).decode("utf-8")
            connection.credentials_json = {
                "__encrypted__": True,
                "version": 1,
                "ciphertext": ciphertext,
            }
        except Exception as e:
            logger.error("Failed to encrypt integration credentials")
            raise CredentialEncryptionError(f"Encryption failed: {e}")

    def retrieve_credentials(self, connection: IntegrationConnection) -> Dict[str, Any]:
        """
        Decrypts and returns credentials dict from connection.credentials_json.
        Fails safely if ciphertext or key is invalid.
        Transparently returns plaintext for unmigrated legacy records.
        """
        data = connection.credentials_json
        if not data:
            return {}
            
        # Check if record is encrypted
        if isinstance(data, dict) and data.get("__encrypted__") is True:
            ciphertext = data.get("ciphertext")
            if not ciphertext:
                return {}
            try:
                decrypted_bytes = self._fernet.decrypt(ciphertext.encode("utf-8"))
                return json.loads(decrypted_bytes.decode("utf-8"))
            except InvalidToken:
                logger.error("Decryption failed: invalid encryption key or corrupted ciphertext")
                raise CredentialDecryptionError("Invalid encryption key or corrupted ciphertext")
            except Exception as e:
                logger.error("Failed to decrypt credentials")
                raise CredentialDecryptionError(f"Decryption failed: {e}")
                
        # Unencrypted legacy record: return as-is for backward compatibility
        return data

    def clear_credentials(self, connection: IntegrationConnection) -> None:
        """Wipes credentials from connection record."""
        connection.credentials_json = {}


class JsonCredentialProvider(EncryptedCredentialProvider):
    """
    Subclasses EncryptedCredentialProvider for backward compatibility.
    All existing callers automatically benefit from encrypted persistence and transparent decryption.
    """
    pass


def get_credential_provider(key: Optional[str] = None) -> CredentialProvider:
    """Factory function for retrieving default CredentialProvider."""
    return EncryptedCredentialProvider(key=key)
