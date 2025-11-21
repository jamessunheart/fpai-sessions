"""
Secure Credential Vault System
3-Tier Architecture: Critical (Tier 1) | Monitored Shared (Tier 2) | Delegated (Tier 3)
"""

import json
import os
import datetime
from cryptography.fernet import Fernet
from pathlib import Path
from typing import Dict, List, Optional


class CredentialVault:
    """Secure encrypted credential storage with access logging"""

    def __init__(self, vault_path: str = "/root/delegation-system/credentials"):
        self.vault_path = Path(vault_path)
        self.vault_path.mkdir(parents=True, exist_ok=True)

        self.key_file = self.vault_path / ".vault_key"
        self.credentials_file = self.vault_path / "credentials.enc"
        self.access_log_file = self.vault_path / "access_log.json"

        # Initialize encryption key
        if not self.key_file.exists():
            key = Fernet.generate_key()
            self.key_file.write_bytes(key)
            os.chmod(self.key_file, 0o600)  # Owner read/write only

        self.cipher = Fernet(self.key_file.read_bytes())

        # Initialize empty credentials if not exist
        if not self.credentials_file.exists():
            self._save_credentials({
                "tier1_critical": {},
                "tier2_monitored": {},
                "tier3_delegated": {}
            })

    def _load_credentials(self) -> Dict:
        """Load and decrypt credentials"""
        if not self.credentials_file.exists():
            return {"tier1_critical": {}, "tier2_monitored": {}, "tier3_delegated": {}}

        encrypted_data = self.credentials_file.read_bytes()
        decrypted_data = self.cipher.decrypt(encrypted_data)
        return json.loads(decrypted_data.decode())

    def _save_credentials(self, credentials: Dict):
        """Encrypt and save credentials"""
        json_data = json.dumps(credentials, indent=2).encode()
        encrypted_data = self.cipher.encrypt(json_data)
        self.credentials_file.write_bytes(encrypted_data)
        os.chmod(self.credentials_file, 0o600)

    def _log_access(self, tier: str, service: str, requester: str, purpose: str, action: str):
        """Log all credential access"""
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "tier": tier,
            "service": service,
            "requester": requester,
            "purpose": purpose,
            "action": action,
            "ip_address": os.getenv("SSH_CLIENT", "local").split()[0] if os.getenv("SSH_CLIENT") else "local"
        }

        # Load existing logs
        if self.access_log_file.exists():
            logs = json.loads(self.access_log_file.read_text())
        else:
            logs = []

        logs.append(log_entry)

        # Save logs
        self.access_log_file.write_text(json.dumps(logs, indent=2))

        # Also log to syslog for security
        print(f"[CREDENTIAL ACCESS] {log_entry}")

    def add_credential(self, tier: str, service: str, credential_data: Dict, requester: str = "admin"):
        """Add a new credential to the vault"""
        credentials = self._load_credentials()

        tier_key = f"tier{tier}_" + ("critical" if tier == "1" else "monitored" if tier == "2" else "delegated")

        if tier_key not in credentials:
            credentials[tier_key] = {}

        credentials[tier_key][service] = {
            "data": credential_data,
            "added_at": datetime.datetime.now().isoformat(),
            "added_by": requester
        }

        self._save_credentials(credentials)
        self._log_access(tier_key, service, requester, "add_credential", "WRITE")

    def get_credential(self, tier: str, service: str, requester: str, purpose: str) -> Optional[Dict]:
        """Retrieve a credential (with logging)"""
        credentials = self._load_credentials()

        tier_key = f"tier{tier}_" + ("critical" if tier == "1" else "monitored" if tier == "2" else "delegated")

        # Security check: Tier 1 should never be accessed except by owner
        if tier == "1" and requester != "admin":
            self._log_access(tier_key, service, requester, purpose, "DENIED")
            raise PermissionError(f"Tier 1 credentials cannot be accessed by {requester}")

        credential = credentials.get(tier_key, {}).get(service)

        if credential:
            self._log_access(tier_key, service, requester, purpose, "READ")
            return credential["data"]

        self._log_access(tier_key, service, requester, purpose, "NOT_FOUND")
        return None

    def list_credentials(self, tier: str) -> List[str]:
        """List available credentials in a tier"""
        credentials = self._load_credentials()
        tier_key = f"tier{tier}_" + ("critical" if tier == "1" else "monitored" if tier == "2" else "delegated")
        return list(credentials.get(tier_key, {}).keys())

    def get_access_log(self, hours: int = 24) -> List[Dict]:
        """Get access log for last N hours"""
        if not self.access_log_file.exists():
            return []

        logs = json.loads(self.access_log_file.read_text())
        cutoff = datetime.datetime.now() - datetime.timedelta(hours=hours)

        return [
            log for log in logs
            if datetime.datetime.fromisoformat(log["timestamp"]) > cutoff
        ]

    def get_suspicious_activity(self) -> List[Dict]:
        """Detect potentially suspicious access patterns"""
        logs = self.get_access_log(hours=24)
        suspicious = []

        # Check for denied access attempts
        denied = [log for log in logs if log["action"] == "DENIED"]
        if denied:
            suspicious.append({
                "type": "denied_access",
                "count": len(denied),
                "details": denied
            })

        # Check for unusual access volume (>10 requests in 1 hour from same requester)
        from collections import Counter
        requester_counts = Counter([log["requester"] for log in logs])
        for requester, count in requester_counts.items():
            if count > 10:
                suspicious.append({
                    "type": "high_volume_access",
                    "requester": requester,
                    "count": count
                })

        return suspicious


class SpendingMonitor:
    """Monitor spending on operations card"""

    def __init__(self, log_path: str = "/root/delegation-system/monitoring"):
        self.log_path = Path(log_path)
        self.log_path.mkdir(parents=True, exist_ok=True)
        self.spending_log = self.log_path / "spending_log.json"

        if not self.spending_log.exists():
            self.spending_log.write_text(json.dumps([], indent=2))

    def log_transaction(self, amount: float, merchant: str, category: str, requester: str, description: str = ""):
        """Log a spending transaction"""
        transaction = {
            "timestamp": datetime.datetime.now().isoformat(),
            "amount": amount,
            "merchant": merchant,
            "category": category,
            "requester": requester,
            "description": description
        }

        logs = json.loads(self.spending_log.read_text())
        logs.append(transaction)
        self.spending_log.write_text(json.dumps(logs, indent=2))

    def get_spending_24h(self) -> float:
        """Get total spending in last 24 hours"""
        logs = json.loads(self.spending_log.read_text())
        cutoff = datetime.datetime.now() - datetime.timedelta(hours=24)

        recent = [
            log for log in logs
            if datetime.datetime.fromisoformat(log["timestamp"]) > cutoff
        ]

        return sum(log["amount"] for log in recent)

    def get_spending_by_category(self, hours: int = 168) -> Dict[str, float]:
        """Get spending by category for last N hours (default 1 week)"""
        logs = json.loads(self.spending_log.read_text())
        cutoff = datetime.datetime.now() - datetime.timedelta(hours=hours)

        recent = [
            log for log in logs
            if datetime.datetime.fromisoformat(log["timestamp"]) > cutoff
        ]

        by_category = {}
        for log in recent:
            category = log["category"]
            by_category[category] = by_category.get(category, 0) + log["amount"]

        return by_category

    def check_alerts(self, thresholds: Dict[str, float]) -> List[Dict]:
        """Check spending against thresholds and return alerts"""
        alerts = []

        # 24-hour spending check
        spending_24h = self.get_spending_24h()
        if spending_24h > thresholds.get("daily", 500):
            alerts.append({
                "type": "high_daily_spending",
                "amount": spending_24h,
                "threshold": thresholds.get("daily", 500),
                "severity": "WARNING"
            })

        # Category-based checks
        spending_by_cat = self.get_spending_by_category(hours=24)
        for category, amount in spending_by_cat.items():
            threshold = thresholds.get(f"category_{category}", 200)
            if amount > threshold:
                alerts.append({
                    "type": "high_category_spending",
                    "category": category,
                    "amount": amount,
                    "threshold": threshold,
                    "severity": "WARNING"
                })

        return alerts


if __name__ == "__main__":
    # Test the vault
    vault = CredentialVault()

    # Example: Add Tier 2 credentials
    vault.add_credential(
        tier="2",
        service="operations_card",
        credential_data={
            "card_number": "XXXX-XXXX-XXXX-1234",
            "expiry": "12/27",
            "cvv": "123",
            "spending_limit": 5000,
            "provider": "Privacy.com"
        },
        requester="admin"
    )

    vault.add_credential(
        tier="2",
        service="upwork_api",
        credential_data={
            "client_id": "your_client_id",
            "client_secret": "your_client_secret",
            "access_token": "your_access_token"
        },
        requester="admin"
    )

    # Example: Retrieve credential
    cred = vault.get_credential("2", "operations_card", "va_assistant", "setup_facebook_ads")
    print(f"Retrieved credential: {cred}")

    # Example: Check access log
    recent_access = vault.get_access_log(hours=1)
    print(f"\nRecent access log:")
    for entry in recent_access:
        print(f"  {entry['timestamp']} - {entry['requester']} accessed {entry['service']} - {entry['action']}")

    print("\n✅ Credential vault system operational!")
