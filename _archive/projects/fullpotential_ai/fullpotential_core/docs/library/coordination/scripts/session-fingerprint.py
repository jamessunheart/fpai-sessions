#!/usr/bin/env python3
"""
Session Fingerprint Generator
Creates unique, verifiable session IDs with sequential proof
"""

import hashlib
import json
import os
import socket
import time
from pathlib import Path

class SessionFingerprint:
    """Generate and verify unique session fingerprints"""

    def __init__(self):
        self.base_path = Path("/Users/jamessunheart/Development/docs/coordination")
        self.sessions_file = self.base_path / "consciousness" / "session_registry.json"
        self.sessions_file.parent.mkdir(exist_ok=True)

    def generate_fingerprint(self, session_name: str = None) -> dict:
        """Generate unique session fingerprint with proof of work"""

        # Collect unique session identifiers
        hostname = socket.gethostname()
        pid = os.getpid()
        timestamp = time.time()
        random_salt = os.urandom(16).hex()

        # Create base fingerprint
        fingerprint_data = f"{hostname}:{pid}:{timestamp}:{random_salt}"
        fingerprint_hash = hashlib.sha256(fingerprint_data.encode()).hexdigest()

        # Get next sequence number
        sequence_num = self._get_next_sequence()

        session_id = f"session-{sequence_num:04d}-{fingerprint_hash[:12]}"

        fingerprint = {
            "session_id": session_id,
            "sequence_number": sequence_num,
            "fingerprint_hash": fingerprint_hash,
            "hostname": hostname,
            "pid": pid,
            "created_at": timestamp,
            "session_name": session_name or f"unnamed-{sequence_num}",
            "status": "active"
        }

        # Register session
        self._register_session(fingerprint)

        return fingerprint

    def _get_next_sequence(self) -> int:
        """Get next sequential session number"""
        registry = self._load_registry()

        if not registry:
            return 1

        max_seq = max((s.get("sequence_number", 0) for s in registry.values()), default=0)
        return max_seq + 1

    def _register_session(self, fingerprint: dict):
        """Register session in global registry"""
        registry = self._load_registry()
        registry[fingerprint["session_id"]] = fingerprint
        self._save_registry(registry)

        print(f"✅ Session registered: {fingerprint['session_id']}")
        print(f"   Sequence: #{fingerprint['sequence_number']}")
        print(f"   Fingerprint: {fingerprint['fingerprint_hash'][:16]}...")

    def verify_session(self, session_id: str) -> bool:
        """Verify session exists and is unique"""
        registry = self._load_registry()
        return session_id in registry

    def get_active_sessions(self) -> list:
        """Get all active sessions"""
        registry = self._load_registry()
        return [s for s in registry.values() if s.get("status") == "active"]

    def _load_registry(self) -> dict:
        if self.sessions_file.exists():
            return json.loads(self.sessions_file.read_text())
        return {}

    def _save_registry(self, registry: dict):
        self.sessions_file.write_text(json.dumps(registry, indent=2))


if __name__ == "__main__":
    import sys

    sf = SessionFingerprint()

    if len(sys.argv) > 1:
        session_name = sys.argv[1]
    else:
        session_name = None

    fingerprint = sf.generate_fingerprint(session_name)
    print(f"\n🔐 Session Fingerprint Generated:")
    print(json.dumps(fingerprint, indent=2))
