#!/usr/bin/env python3
"""
Local Credential Vault - Secure encrypted storage for development

Uses same encryption as credentials-manager (AES-256 via Fernet)
Stores credentials in encrypted JSON file
Master key from environment variable FPAI_CREDENTIALS_KEY
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64


class CredentialVault:
    """Manages encrypted credential storage"""

    def __init__(self, vault_path: Optional[Path] = None):
        """Initialize vault with encryption key from environment"""
        # Get master key from environment
        master_key = os.getenv("FPAI_CREDENTIALS_KEY")
        if not master_key:
            raise ValueError(
                "FPAI_CREDENTIALS_KEY environment variable not set.\n"
                "Generate with: python3 -c 'import secrets; print(secrets.token_hex(32))'\n"
                "Then: export FPAI_CREDENTIALS_KEY=your_generated_key"
            )

        # Derive Fernet key from master key (same as credentials-manager)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"fpai-credentials-salt",  # Same salt as server
            iterations=100000,
            backend=default_backend(),
        )

        key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
        self.fernet = Fernet(key)

        # Vault file path
        if vault_path is None:
            coord_dir = Path(__file__).parent.parent
            vault_path = coord_dir / ".credentials"
        self.vault_path = vault_path

    def _load_vault(self) -> Dict[str, Any]:
        """Load and decrypt vault"""
        if not self.vault_path.exists():
            return {}

        try:
            encrypted_data = self.vault_path.read_bytes()
            decrypted_data = self.fernet.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode())
        except Exception as e:
            raise ValueError(f"Failed to decrypt vault: {e}")

    def _save_vault(self, data: Dict[str, Any]) -> None:
        """Encrypt and save vault"""
        json_data = json.dumps(data, indent=2)
        encrypted_data = self.fernet.encrypt(json_data.encode())
        self.vault_path.write_bytes(encrypted_data)
        # Set secure permissions (owner read/write only)
        os.chmod(self.vault_path, 0o600)

    def set_credential(
        self,
        name: str,
        value: str,
        credential_type: str = "api_key",
        service: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Store a credential"""
        vault = self._load_vault()

        vault[name] = {
            "value": value,
            "type": credential_type,
            "service": service,
            "metadata": metadata or {},
        }

        self._save_vault(vault)

    def get_credential(self, name: str) -> Optional[str]:
        """Get a credential value"""
        vault = self._load_vault()
        credential = vault.get(name)
        if credential:
            return credential["value"]
        return None

    def get_credential_full(self, name: str) -> Optional[Dict[str, Any]]:
        """Get full credential details"""
        vault = self._load_vault()
        return vault.get(name)

    def list_credentials(self) -> list[str]:
        """List all credential names"""
        vault = self._load_vault()
        return list(vault.keys())

    def delete_credential(self, name: str) -> bool:
        """Delete a credential"""
        vault = self._load_vault()
        if name in vault:
            del vault[name]
            self._save_vault(vault)
            return True
        return False

    def exists(self, name: str) -> bool:
        """Check if credential exists"""
        vault = self._load_vault()
        return name in vault


def main():
    """CLI interface"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  credential_vault.py set <name> <value> [type] [service]")
        print("  credential_vault.py get <name>")
        print("  credential_vault.py list")
        print("  credential_vault.py delete <name>")
        print("  credential_vault.py exists <name>")
        sys.exit(1)

    try:
        vault = CredentialVault()
        command = sys.argv[1]

        if command == "set":
            if len(sys.argv) < 4:
                print("Usage: credential_vault.py set <name> <value> [type] [service]")
                sys.exit(1)
            name = sys.argv[2]
            value = sys.argv[3]
            cred_type = sys.argv[4] if len(sys.argv) > 4 else "api_key"
            service = sys.argv[5] if len(sys.argv) > 5 else None
            vault.set_credential(name, value, cred_type, service)
            print(f"✅ Stored credential: {name}")

        elif command == "get":
            if len(sys.argv) < 3:
                print("Usage: credential_vault.py get <name>")
                sys.exit(1)
            name = sys.argv[2]
            value = vault.get_credential(name)
            if value:
                print(value)
            else:
                print(f"❌ Credential not found: {name}", file=sys.stderr)
                sys.exit(1)

        elif command == "list":
            credentials = vault.list_credentials()
            if credentials:
                print("📋 Stored credentials:")
                for name in credentials:
                    cred = vault.get_credential_full(name)
                    print(f"  - {name} ({cred['type']})" + (f" [{cred['service']}]" if cred.get('service') else ""))
            else:
                print("No credentials stored")

        elif command == "delete":
            if len(sys.argv) < 3:
                print("Usage: credential_vault.py delete <name>")
                sys.exit(1)
            name = sys.argv[2]
            if vault.delete_credential(name):
                print(f"✅ Deleted credential: {name}")
            else:
                print(f"❌ Credential not found: {name}", file=sys.stderr)
                sys.exit(1)

        elif command == "exists":
            if len(sys.argv) < 3:
                print("Usage: credential_vault.py exists <name>")
                sys.exit(1)
            name = sys.argv[2]
            if vault.exists(name):
                print("yes")
                sys.exit(0)
            else:
                print("no")
                sys.exit(1)

        else:
            print(f"Unknown command: {command}")
            sys.exit(1)

    except ValueError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
