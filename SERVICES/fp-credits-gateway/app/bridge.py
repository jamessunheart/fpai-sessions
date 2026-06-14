import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
import json

# Solana Imports (Graceful Fallback)
SOLANA_AVAILABLE = False
try:
    from solana.rpc.api import Client
    from solders.pubkey import Pubkey
    from solders.signature import Signature
    SOLANA_AVAILABLE = True
except ImportError:
    pass

logger = logging.getLogger("fp-bridge")

class BridgeService:
    """
    Monitors the Solana blockchain for incoming deposits.
    Automatically mints UC credits when SOL/USDC is received.
    """
    def __init__(self, store, config):
        self.store = store
        self.config = config
        self.rpc_url = config.SOLANA_RPC_URL
        self.treasury_wallet = config.SOLANA_TREASURY_WALLET
        self.is_running = False
        self.last_signature = None  # Track last processed tx
        self.client = None
        
    async def start(self):
        """Start the background watcher task."""
        if not SOLANA_AVAILABLE:
            logger.warning("[BRIDGE] Solana libraries not installed. Bridge disabled.")
            return

        self.is_running = True
        self.client = Client(self.rpc_url)
        logger.info(f"[BRIDGE] Starting Inbound Bridge Watcher for {self.treasury_wallet}")
        
        # Start polling loop
        asyncio.create_task(self._poll_loop())

    async def stop(self):
        """Stop the watcher."""
        self.is_running = False
        logger.info("[BRIDGE] Stopping Inbound Bridge Watcher")

    async def _poll_loop(self):
        """Main polling loop."""
        while self.is_running:
            try:
                await self.sync_transactions()
            except Exception as e:
                logger.error(f"[BRIDGE] Error in poll loop: {e}")
            
            # Sleep for 30 seconds (don't spam RPC)
            await asyncio.sleep(30)

    async def sync_transactions(self):
        """Fetch and process new transactions."""
        if not self.client:
            return

        try:
            # 1. Get signatures for address
            # Note: This is a sync call in the library, might block slightly
            # In production, use async client or thread pool
            pubkey = Pubkey.from_string(self.treasury_wallet)
            
            # Get last 10 transactions
            # We use 'before' parameter to paginate if we had last_signature
            resp = self.client.get_signatures_for_address(
                pubkey,
                limit=10,
                until=self.last_signature
            )
            
            signatures = resp.value
            if not signatures:
                return

            # Process from oldest to newest
            for sig_info in reversed(signatures):
                sig = str(sig_info.signature)
                if sig_info.err:
                    continue # Skip failed txs
                
                # Check if already processed
                if self.store.get_audit_block(sig):
                    continue
                    
                await self._process_transaction(sig)
                self.last_signature = sig_info.signature

        except Exception as e:
            logger.error(f"[BRIDGE] Sync failed: {e}")

    async def _process_transaction(self, signature: str):
        """Analyze a transaction and credit the user."""
        try:
            tx_resp = self.client.get_transaction(
                Signature.from_string(signature),
                max_supported_transaction_version=0
            )
            
            if not tx_resp.value:
                return

            tx = tx_resp.value.transaction
            meta = tx_resp.value.meta
            
            # Logic to extract deposit amount
            # This is complex: need to check balance changes for treasury account
            
            # 1. Identify sender (first signer usually)
            sender = str(tx.message.account_keys[0])
            
            # 2. Calculate SOL change for Treasury
            # Find index of treasury wallet
            treasury_idx = -1
            for i, key in enumerate(tx.message.account_keys):
                if str(key) == self.treasury_wallet:
                    treasury_idx = i
                    break
            
            if treasury_idx == -1:
                return # Treasury not involved?

            pre_bal = meta.pre_balances[treasury_idx]
            post_bal = meta.post_balances[treasury_idx]
            amount_lamports = post_bal - pre_bal
            
            if amount_lamports <= 0:
                return # Outbound or zero transfer
                
            amount_sol = amount_lamports / 1_000_000_000
            
            # 3. Get current price
            # We use the store's cached price
            health = self.store.calculate_treasury_health()
            sol_price = health["assets_breakdown"]["prices"].get("SOL", 150.0)
            
            value_usd = amount_sol * sol_price
            
            logger.info(f"[BRIDGE] Detected deposit: {amount_sol} SOL (${value_usd:.2f}) from {sender}")
            
            # 4. Credit the user
            # Find or create account for sender
            user_id = f"sol_{sender[:8]}"
            account = self.store.get_or_create_account(
                user_id, 
                display_name=f"Wallet {sender[:6]}...",
                metadata={"solana_address": sender}
            )
            
            # Mint UC
            self.store.credit(
                account_id=user_id,
                credit_type="uc",
                amount=value_usd,
                description=f"Deposit {amount_sol:.4f} SOL (Tx: {signature[:8]})",
                metadata={
                    "tx_hash": signature,
                    "sol_amount": amount_sol,
                    "sol_price": sol_price,
                    "source": "bridge"
                }
            )
            
            # Record revenue event
            self.store._record_audit_block("bridge_deposit", {
                "tx": signature,
                "amount_sol": amount_sol,
                "value_usd": value_usd,
                "sender": sender
            })
            
        except Exception as e:
            logger.error(f"[BRIDGE] Tx processing failed ({signature}): {e}")




