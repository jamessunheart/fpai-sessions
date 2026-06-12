"""
Encrypted API Key Vault
Secure storage for member exchange API credentials.
"""

import os
import json
import sqlite3
import logging
import hashlib
import base64
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ExchangeCredentials:
    """Decrypted exchange credentials."""
    user_id: str
    exchange: str
    api_key: str
    api_secret: str
    wallet_address: Optional[str] = None
    permissions: Optional[List[str]] = None
    ip_whitelist: Optional[List[str]] = None
    created_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    is_active: bool = True


class APIKeyVault:
    """
    Encrypted vault for storing exchange API keys.
    Uses Fernet symmetric encryption with key derived from master password.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self.db_path = Path(os.getenv(
            "VAULT_DB_PATH",
            "/opt/fpai/aria-command/data/vault.db"
        ))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Master encryption key derived from environment or generated
        self._master_key = self._get_or_create_master_key()
        self._fernet = Fernet(self._master_key)
        
        self._init_db()
        self._initialized = True
        logger.info("API Key Vault initialized")
    
    def _get_or_create_master_key(self) -> bytes:
        """Get or create the master encryption key."""
        # Try to load from environment
        master_password = os.getenv("VAULT_MASTER_PASSWORD")
        salt = os.getenv("VAULT_SALT")
        
        if master_password and salt:
            # Derive key from password
            return self._derive_key(master_password, base64.b64decode(salt))
        
        # Try to load from file
        key_file = Path("/opt/fpai/aria-command/data/.vault_key")
        if key_file.exists():
            return key_file.read_bytes()
        
        # Generate new key
        key = Fernet.generate_key()
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_bytes(key)
        os.chmod(key_file, 0o600)  # Restrict permissions
        logger.warning("Generated new vault master key")
        return key
    
    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """Derive encryption key from password."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))
    
    def _init_db(self):
        """Initialize the vault database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS credentials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    encrypted_data BLOB NOT NULL,
                    key_hash TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_used TEXT,
                    UNIQUE(user_id, exchange)
                );
                
                CREATE TABLE IF NOT EXISTS access_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    action TEXT NOT NULL,
                    ip_address TEXT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_creds_user ON credentials(user_id);
                CREATE INDEX IF NOT EXISTS idx_access_user ON access_log(user_id);
            """)
    
    def _encrypt(self, data: Dict[str, Any]) -> bytes:
        """Encrypt data dictionary."""
        json_data = json.dumps(data).encode()
        return self._fernet.encrypt(json_data)
    
    def _decrypt(self, encrypted_data: bytes) -> Dict[str, Any]:
        """Decrypt data to dictionary."""
        decrypted = self._fernet.decrypt(encrypted_data)
        return json.loads(decrypted.decode())
    
    def _hash_key(self, api_key: str) -> str:
        """Create a hash of the API key for verification."""
        return hashlib.sha256(api_key.encode()).hexdigest()[:16]
    
    def store_credentials(
        self,
        user_id: str,
        exchange: str,
        api_key: str,
        api_secret: str,
        wallet_address: Optional[str] = None,
        permissions: Optional[List[str]] = None,
        ip_whitelist: Optional[List[str]] = None,
        ip_address: Optional[str] = None
    ) -> bool:
        """
        Store encrypted API credentials for a user.
        """
        try:
            # Prepare data for encryption
            data = {
                "api_key": api_key,
                "api_secret": api_secret,
                "wallet_address": wallet_address,
                "permissions": permissions or [],
                "ip_whitelist": ip_whitelist or [],
            }
            
            encrypted = self._encrypt(data)
            key_hash = self._hash_key(api_key)
            now = datetime.now().isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                # Upsert credentials
                conn.execute("""
                    INSERT INTO credentials 
                    (user_id, exchange, encrypted_data, key_hash, is_active, created_at)
                    VALUES (?, ?, ?, ?, 1, ?)
                    ON CONFLICT(user_id, exchange) DO UPDATE SET
                        encrypted_data = excluded.encrypted_data,
                        key_hash = excluded.key_hash,
                        is_active = 1,
                        created_at = excluded.created_at
                """, (user_id, exchange, encrypted, key_hash, now))
                
                # Log access
                conn.execute("""
                    INSERT INTO access_log (user_id, exchange, action, ip_address)
                    VALUES (?, ?, 'store', ?)
                """, (user_id, exchange, ip_address))
            
            logger.info(f"Stored credentials for user {user_id} on {exchange}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store credentials: {e}")
            return False
    
    def get_credentials(
        self,
        user_id: str,
        exchange: str,
        ip_address: Optional[str] = None
    ) -> Optional[ExchangeCredentials]:
        """
        Retrieve decrypted credentials for a user.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute("""
                    SELECT * FROM credentials 
                    WHERE user_id = ? AND exchange = ? AND is_active = 1
                """, (user_id, exchange)).fetchone()
                
                if not row:
                    return None
                
                # Decrypt
                data = self._decrypt(row["encrypted_data"])
                
                # Update last_used
                now = datetime.now().isoformat()
                conn.execute("""
                    UPDATE credentials SET last_used = ? 
                    WHERE user_id = ? AND exchange = ?
                """, (now, user_id, exchange))
                
                # Log access
                conn.execute("""
                    INSERT INTO access_log (user_id, exchange, action, ip_address)
                    VALUES (?, ?, 'retrieve', ?)
                """, (user_id, exchange, ip_address))
                
                return ExchangeCredentials(
                    user_id=user_id,
                    exchange=exchange,
                    api_key=data["api_key"],
                    api_secret=data["api_secret"],
                    wallet_address=data.get("wallet_address"),
                    permissions=data.get("permissions"),
                    ip_whitelist=data.get("ip_whitelist"),
                    created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
                    last_used=datetime.fromisoformat(row["last_used"]) if row["last_used"] else None,
                    is_active=bool(row["is_active"])
                )
                
        except Exception as e:
            logger.error(f"Failed to retrieve credentials: {e}")
            return None
    
    def delete_credentials(
        self,
        user_id: str,
        exchange: str,
        ip_address: Optional[str] = None
    ) -> bool:
        """
        Delete (deactivate) credentials for a user.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute("""
                    UPDATE credentials SET is_active = 0
                    WHERE user_id = ? AND exchange = ?
                """, (user_id, exchange))
                
                # Log access
                conn.execute("""
                    INSERT INTO access_log (user_id, exchange, action, ip_address)
                    VALUES (?, ?, 'delete', ?)
                """, (user_id, exchange, ip_address))
                
                if result.rowcount > 0:
                    logger.info(f"Deleted credentials for user {user_id} on {exchange}")
                    return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete credentials: {e}")
            return False
    
    def has_credentials(self, user_id: str, exchange: str) -> bool:
        """Check if user has active credentials for exchange."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("""
                SELECT 1 FROM credentials 
                WHERE user_id = ? AND exchange = ? AND is_active = 1
            """, (user_id, exchange)).fetchone()
            return row is not None
    
    def get_user_exchanges(self, user_id: str) -> List[str]:
        """Get list of exchanges where user has credentials."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT exchange FROM credentials 
                WHERE user_id = ? AND is_active = 1
            """, (user_id,)).fetchall()
            return [row[0] for row in rows]
    
    def verify_key_hash(self, user_id: str, exchange: str, api_key: str) -> bool:
        """Verify that the provided key matches stored hash."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("""
                SELECT key_hash FROM credentials 
                WHERE user_id = ? AND exchange = ? AND is_active = 1
            """, (user_id, exchange)).fetchone()
            
            if row:
                return row[0] == self._hash_key(api_key)
            return False
    
    def get_access_log(
        self,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get access log entries."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if user_id:
                rows = conn.execute("""
                    SELECT * FROM access_log 
                    WHERE user_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (user_id, limit)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM access_log 
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,)).fetchall()
            
            return [dict(row) for row in rows]
    
    def rotate_master_key(self, new_password: str, new_salt: bytes) -> bool:
        """
        Rotate the master encryption key.
        Re-encrypts all credentials with new key.
        """
        try:
            # Derive new key
            new_key = self._derive_key(new_password, new_salt)
            new_fernet = Fernet(new_key)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT id, encrypted_data FROM credentials WHERE is_active = 1"
                ).fetchall()
                
                for row in rows:
                    # Decrypt with old key
                    data = self._decrypt(row["encrypted_data"])
                    # Re-encrypt with new key
                    new_encrypted = new_fernet.encrypt(json.dumps(data).encode())
                    # Update
                    conn.execute(
                        "UPDATE credentials SET encrypted_data = ? WHERE id = ?",
                        (new_encrypted, row["id"])
                    )
            
            # Update instance key
            self._master_key = new_key
            self._fernet = new_fernet
            
            logger.info("Master key rotated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to rotate master key: {e}")
            return False


# Singleton instance
_vault: Optional[APIKeyVault] = None


def get_vault() -> APIKeyVault:
    """Get the singleton vault instance."""
    global _vault
    if _vault is None:
        _vault = APIKeyVault()
    return _vault


def store_api_keys(
    user_id: str,
    exchange: str,
    api_key: str,
    api_secret: str,
    **kwargs
) -> bool:
    """Store API keys for a user."""
    return get_vault().store_credentials(user_id, exchange, api_key, api_secret, **kwargs)


def get_api_keys(user_id: str, exchange: str) -> Optional[ExchangeCredentials]:
    """Get API keys for a user."""
    return get_vault().get_credentials(user_id, exchange)


def delete_api_keys(user_id: str, exchange: str) -> bool:
    """Delete API keys for a user."""
    return get_vault().delete_credentials(user_id, exchange)


# =============================================================================
# ENTITY CREDENTIAL HELPERS
# =============================================================================

def store_entity_api_keys(
    entity_id: str,
    exchange: str,
    api_key: str,
    api_secret: str,
    admin_user_id: str,
    **kwargs
) -> bool:
    """
    Store API keys for an entity (Trust, LLC, Church).
    Uses 'entity:' prefix to distinguish from individual user credentials.
    """
    vault = get_vault()
    
    # Store with entity prefix
    success = vault.store_credentials(
        user_id=f"entity:{entity_id}",
        exchange=exchange,
        api_key=api_key,
        api_secret=api_secret,
        **kwargs
    )
    
    if success:
        # Log who added the credentials
        with sqlite3.connect(vault.db_path) as conn:
            conn.execute("""
                INSERT INTO access_log (user_id, exchange, action, ip_address)
                VALUES (?, ?, 'entity_store', ?)
            """, (f"entity:{entity_id}", exchange, f"by:{admin_user_id}"))
    
    return success


def get_entity_api_keys(entity_id: str, exchange: str) -> Optional[ExchangeCredentials]:
    """Get API keys for an entity."""
    return get_vault().get_credentials(f"entity:{entity_id}", exchange)


def delete_entity_api_keys(entity_id: str, exchange: str, admin_user_id: str) -> bool:
    """Delete API keys for an entity."""
    vault = get_vault()
    
    success = vault.delete_credentials(f"entity:{entity_id}", exchange)
    
    if success:
        with sqlite3.connect(vault.db_path) as conn:
            conn.execute("""
                INSERT INTO access_log (user_id, exchange, action, ip_address)
                VALUES (?, ?, 'entity_delete', ?)
            """, (f"entity:{entity_id}", exchange, f"by:{admin_user_id}"))
    
    return success


def has_entity_credentials(entity_id: str, exchange: str) -> bool:
    """Check if entity has active credentials for exchange."""
    return get_vault().has_credentials(f"entity:{entity_id}", exchange)


def list_all_entities_with_credentials(exchange: str = "hyperliquid") -> List[str]:
    """List all entities with credentials for a given exchange."""
    vault = get_vault()
    entities = []
    
    with sqlite3.connect(vault.db_path) as conn:
        rows = conn.execute("""
            SELECT user_id FROM credentials 
            WHERE exchange = ? AND is_active = 1 AND user_id LIKE 'entity:%'
        """, (exchange,)).fetchall()
        
        for row in rows:
            # Remove 'entity:' prefix
            entity_id = row[0].replace("entity:", "")
            entities.append(entity_id)
    
    return entities

