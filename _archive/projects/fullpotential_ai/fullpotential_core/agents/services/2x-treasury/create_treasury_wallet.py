"""
Generate 2X Treasury Wallet
Creates a new Solana wallet for receiving SOL deposits
"""
from solders.keypair import Keypair
import json
import os

# Generate new keypair for treasury
treasury_keypair = Keypair()

# Get public and private keys
public_key = str(treasury_keypair.pubkey())
secret_key = list(treasury_keypair.secret())

print("=" * 60)
print("2X TREASURY WALLET CREATED")
print("=" * 60)
print()
print(f"Public Key (Treasury Address):")
print(public_key)
print()
print(f"Secret Key (KEEP SECURE - NEVER SHARE):")
print(json.dumps(secret_key))
print()
print("=" * 60)
print("SECURITY INSTRUCTIONS:")
print("=" * 60)
print("1. Save the secret key to a secure password manager")
print("2. Never commit the secret key to git")
print("3. For production, use multi-sig wallet (Squads Protocol)")
print("4. This wallet will receive ALL SOL deposits")
print("5. Back up the secret key in multiple secure locations")
print()

# Save to secure file (encrypted)
wallet_data = {
    "public_key": public_key,
    "secret_key": secret_key,
    "created_at": "2025-11-16",
    "purpose": "2X Treasury - SOL deposits",
    "network": "mainnet-beta"
}

# Save wallet (warning: this is not encrypted - for development only)
with open(".treasury_wallet.json", "w") as f:
    json.dump(wallet_data, f, indent=2)

print("Wallet saved to: .treasury_wallet.json (DO NOT COMMIT TO GIT)")
print()
print("Next steps:")
print("1. Add public key to dashboard.html")
print("2. Add .treasury_wallet.json to .gitignore")
print("3. Fund wallet with small amount of SOL for testing")
print("4. Update backend to verify transaction signatures")
