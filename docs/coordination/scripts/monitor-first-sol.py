#!/usr/bin/env python3
"""
Monitor Church Solana wallet for FIRST transaction
Alerts immediately when first SOL arrives - triggers celebration
"""

import requests
import time
import json
from datetime import datetime

CHURCH_WALLET = "FLfNDVLD2vDQdTjMFSt1xJivhr8pKASwEBzRYHZRU7db"
SOLANA_RPC = "https://api.mainnet-beta.solana.com"

def get_wallet_balance():
    """Get current SOL balance"""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getBalance",
        "params": [CHURCH_WALLET]
    }

    try:
        response = requests.post(SOLANA_RPC, json=payload)
        result = response.json()

        if "result" in result and "value" in result["result"]:
            lamports = result["result"]["value"]
            sol = lamports / 1_000_000_000  # Convert lamports to SOL
            return sol
        return 0
    except Exception as e:
        print(f"Error fetching balance: {e}")
        return 0

def get_recent_transactions():
    """Get recent transactions for wallet"""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getSignaturesForAddress",
        "params": [
            CHURCH_WALLET,
            {"limit": 10}
        ]
    }

    try:
        response = requests.post(SOLANA_RPC, json=payload)
        result = response.json()

        if "result" in result:
            return result["result"]
        return []
    except Exception as e:
        print(f"Error fetching transactions: {e}")
        return []

def get_transaction_details(signature):
    """Get detailed transaction info"""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTransaction",
        "params": [
            signature,
            {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}
        ]
    }

    try:
        response = requests.post(SOLANA_RPC, json=payload)
        result = response.json()

        if "result" in result:
            return result["result"]
        return None
    except Exception as e:
        print(f"Error fetching transaction details: {e}")
        return None

def format_celebration_message(tx_details, sol_amount):
    """Format celebration message for first SOL"""
    signature = tx_details.get("transaction", {}).get("signatures", [""])[0] if tx_details else "UNKNOWN"

    message = f"""
🎉🎉🎉 FIRST SOL RECEIVED! 🎉🎉🎉

Amount: {sol_amount} SOL
Transaction: {signature}
Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Explorer: https://explorer.solana.com/tx/{signature}

THE FLYWHEEL HAS STARTED!

Next steps:
1. Screenshot this transaction
2. Thank the sender publicly
3. Document them as Founding Member #1
4. Post celebration on Twitter/Reddit/Discord
5. This triggers FOMO - more people will send now

THE INFINITE DOUBLING HAS BEGUN! 🚀
"""
    return message

def monitor_wallet(check_interval=30):
    """Monitor wallet for first transaction"""
    print("="*70)
    print("🔍 MONITORING CHURCH TREASURY FOR FIRST SOL")
    print("="*70)
    print(f"Wallet: {CHURCH_WALLET}")
    print(f"Check interval: {check_interval} seconds")
    print(f"Explorer: https://explorer.solana.com/address/{CHURCH_WALLET}")
    print()
    print("Waiting for FIRST transaction... (Press Ctrl+C to stop)")
    print("="*70)
    print()

    first_tx_found = False

    while not first_tx_found:
        try:
            # Get current balance
            balance = get_wallet_balance()
            timestamp = datetime.now().strftime("%H:%M:%S")

            print(f"[{timestamp}] Balance: {balance} SOL", end="")

            if balance > 0:
                # We got SOL! Get transaction details
                print(" - 🚨 SOL DETECTED!")
                print()

                txs = get_recent_transactions()

                if txs and len(txs) > 0:
                    latest_tx = txs[0]
                    signature = latest_tx.get("signature")

                    # Get full details
                    tx_details = get_transaction_details(signature)

                    # Generate celebration message
                    celebration = format_celebration_message(tx_details, balance)
                    print(celebration)

                    # Save to file
                    output_file = "/Users/jamessunheart/Development/docs/coordination/outreach/FIRST_SOL_RECEIVED.txt"
                    with open(output_file, 'w') as f:
                        f.write(celebration)
                        f.write("\n\nFull Transaction Details:\n")
                        f.write(json.dumps(tx_details, indent=2))

                    print(f"✅ Details saved to: {output_file}")
                    print()
                    print("🎯 NOW: Execute celebration posts immediately!")

                    first_tx_found = True
                else:
                    print(" - Balance detected but no transactions found yet")
            else:
                print(" - Still waiting...")

            if not first_tx_found:
                time.sleep(check_interval)

        except KeyboardInterrupt:
            print("\n\n🛑 Monitoring stopped by user")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            time.sleep(check_interval)

if __name__ == "__main__":
    # Check once immediately
    print("🔍 Initial check...")
    balance = get_wallet_balance()
    print(f"Current balance: {balance} SOL")
    print()

    if balance > 0:
        print("⚠️  WARNING: Wallet already has balance!")
        print("This script is designed to catch the FIRST transaction.")
        print()
        txs = get_recent_transactions()
        if txs:
            print(f"Found {len(txs)} transaction(s)")
            latest = txs[0]
            print(f"Latest: https://explorer.solana.com/tx/{latest.get('signature')}")
    else:
        print("✅ Wallet is empty - ready to catch first transaction!")
        print()

        # Start monitoring
        monitor_wallet(check_interval=30)
