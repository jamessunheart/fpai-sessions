#!/usr/bin/env python3
"""
Decrypt Church of Full Potential Solana wallet private key
Requires passphrase for security
"""

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
