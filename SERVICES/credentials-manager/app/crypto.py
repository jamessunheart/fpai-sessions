"""Cryptography utilities for secure credential storage"""

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
import base64
import secrets

from .config import settings


class CryptoManager:
    """Handles encryption/decryption of credentials"""

    def __init__(self):
        """Initialize with master key"""
        # Derive Fernet key from master key
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'fpai-credentials-salt',  # Static salt for deterministic key
            iterations=100000,
            backend=default_backend()
        )

        key = base64.urlsafe_b64encode(
            kdf.derive(settings.master_encryption_key.encode())
        )

        self.fernet = Fernet(key)

    def encrypt(self, value: str) -> str:
        """
        Encrypt a credential value.

        Returns base64-encoded encrypted string.
        """
        encrypted = self.fernet.encrypt(value.encode())
        return base64.b64encode(encrypted).decode()

    def decrypt(self, encrypted_value: str) -> str:
        """
        Decrypt a credential value.

        Returns original string.
        """
        encrypted = base64.b64decode(encrypted_value.encode())
        decrypted = self.fernet.decrypt(encrypted)
        return decrypted.decode()

    @staticmethod
    def generate_token() -> str:
        """Generate a secure random token"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_token(token: str) -> str:
        """Hash a token for storage"""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.hash(token)

    @staticmethod
    def verify_token(token: str, token_hash: str) -> bool:
        """Verify a token against its hash"""
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.verify(token, token_hash)


# Global instance
crypto = CryptoManager()
