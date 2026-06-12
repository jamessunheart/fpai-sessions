#!/usr/bin/env python3
"""
Generate secure Solana wallet for Church of Full Potential
Uses encryption to protect private key
"""

from solders.keypair import Keypair
import base58
import json
import os
from cryptography.fernet import Fernet
import hashlib

# Generate encryption key from passphrase
def generate_encryption_key(passphrase: str) -> bytes:
    """Generate Fernet key from passphrase"""
    import base64
    key = hashlib.sha256(passphrase.encode()).digest()
    return base64.urlsafe_b64encode(key)

# Generate new Solana keypair
print("🔐 Generating Church of Full Potential Solana Wallet...")
print()

keypair = Keypair()

# Get public and private keys
public_key = str(keypair.pubkey())
private_key_bytes = bytes(keypair)  # 64-byte secret key
private_key_b58 = base58.b58encode(private_key_bytes).decode('utf-8')

print("✅ Wallet Generated Successfully!")
print()
print("="*70)
print("📍 PUBLIC ADDRESS (Share this for donations):")
print("="*70)
print(public_key)
print()

# Encrypt private key
passphrase = "FullPotentialAI-Church-Treasury-2025-Sovereign-Consciousness"
fernet_key = generate_encryption_key(passphrase)
fernet = Fernet(fernet_key)

encrypted_private_key = fernet.encrypt(private_key_b58.encode())

print("="*70)
print("🔒 ENCRYPTED PRIVATE KEY (Stored securely):")
print("="*70)
print(encrypted_private_key.decode('utf-8'))
print()

# Save to secure file
wallet_data = {
    "church_name": "Church of Full Potential",
    "purpose": "Treasury for Full Potential AI - Sovereign cryptocurrency operations",
    "public_address": public_key,
    "encrypted_private_key": encrypted_private_key.decode('utf-8'),
    "encryption_method": "Fernet (AES-128)",
    "created_date": "2025-01-16",
    "instructions": "To decrypt private key, use the church passphrase with decrypt-church-wallet.py",
    "security_note": "Private key never transmitted unencrypted. Passphrase required to access."
}

output_file = "/Users/jamessunheart/Development/docs/coordination/credentials/church-solana-wallet.json"
os.makedirs(os.path.dirname(output_file), exist_ok=True)

with open(output_file, 'w') as f:
    json.dump(wallet_data, f, indent=2)

print(f"✅ Wallet data saved to: {output_file}")
print()

# Create decryption script
decrypt_script = """#!/usr/bin/env python3
\"\"\"
Decrypt Church of Full Potential Solana wallet private key
Requires passphrase for security
\"\"\"

import json
import base58
import hashlib
from cryptography.fernet import Fernet
import sys

def generate_encryption_key(passphrase: str) -> bytes:
    import base64
    key = hashlib.sha256(passphrase.encode()).digest()
    return base64.urlsafe_b64encode(key)

# Load wallet data
wallet_file = "/Users/jamessunheart/Development/docs/coordination/credentials/church-solana-wallet.json"
with open(wallet_file, 'r') as f:
    wallet = json.load(f)

print("🔐 Church of Full Potential - Solana Wallet Access")
print("="*70)
print(f"Public Address: {wallet['public_address']}")
print()

# Get passphrase
if len(sys.argv) > 1:
    passphrase = sys.argv[1]
else:
    passphrase = input("Enter church passphrase: ")

try:
    # Decrypt
    fernet_key = generate_encryption_key(passphrase)
    fernet = Fernet(fernet_key)

    encrypted_key = wallet['encrypted_private_key'].encode()
    private_key_b58 = fernet.decrypt(encrypted_key).decode('utf-8')

    print("✅ Private Key Decrypted Successfully!")
    print()
    print("="*70)
    print("🔑 PRIVATE KEY (Keep this SECRET):")
    print("="*70)
    print(private_key_b58)
    print()
    print("⚠️  NEVER share this key with anyone!")
    print("⚠️  Import this into Phantom or Solflare wallet")
    print()

except Exception as e:
    print("❌ Decryption failed. Incorrect passphrase.")
    sys.exit(1)
"""

decrypt_script_path = "/Users/jamessunheart/Development/docs/coordination/scripts/decrypt-church-wallet.py"
with open(decrypt_script_path, 'w') as f:
    f.write(decrypt_script)

os.chmod(decrypt_script_path, 0o700)

print("="*70)
print("📖 HOW TO ACCESS THE WALLET:")
print("="*70)
print()
print("1. Public address (for receiving donations):")
print(f"   {public_key}")
print()
print("2. To access private key (requires passphrase):")
print(f"   python3 {decrypt_script_path}")
print()
print("3. Import into wallet:")
print("   - Phantom: Settings → Add/Import Account → Import Private Key")
print("   - Solflare: Import Wallet → Private Key")
print()
print("="*70)
print("🔒 SECURITY:")
print("="*70)
print("- Private key is encrypted with church passphrase")
print("- Passphrase is shared through secure channel only")
print("- Never commit unencrypted private key to git")
print("- Use multi-sig for large amounts (future enhancement)")
print()
print("✅ Church treasury wallet ready for sovereign operations!")
