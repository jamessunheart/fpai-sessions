"""
Solana client for interacting with treasury smart contract
"""

import logging
from typing import Dict, Optional
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from anchorpy import Provider, Wallet, Program, Idl
import json
import os

logger = logging.getLogger(__name__)


class SolanaClient:
    """Wrapper for Solana treasury program interactions"""

    def __init__(self):
        # Solana RPC endpoint
        self.rpc_url = os.getenv("SOLANA_RPC_URL", "https://api.devnet.solana.com")

        # Program ID (deployed treasury program)
        self.program_id = Pubkey.from_string(
            os.getenv("TREASURY_PROGRAM_ID", "TiE11111111111111111111111111111111111111111")
        )

        # Treasury authority keypair (for withdrawals)
        authority_key = os.getenv("TREASURY_AUTHORITY_PRIVATE_KEY")
        if authority_key:
            self.authority = Keypair.from_base58_string(authority_key)
        else:
            # Generate temp keypair for development
            self.authority = Keypair()
            logger.warning("Using temporary authority keypair - NOT FOR PRODUCTION")

        self.client: Optional[AsyncClient] = None
        self.program: Optional[Program] = None

    async def connect(self):
        """Initialize connection to Solana"""
        try:
            self.client = AsyncClient(self.rpc_url, commitment=Confirmed)

            # Load IDL and create program instance
            # In production, load from file or deployed IDL
            # idl_path = "target/idl/sol_treasury.json"
            # with open(idl_path) as f:
            #     idl = Idl.from_json(f.read())
            #
            # wallet = Wallet(self.authority)
            # provider = Provider(self.client, wallet)
            # self.program = Program(idl, self.program_id, provider)

            logger.info(f"Connected to Solana: {self.rpc_url}")
            logger.info(f"Treasury Program ID: {self.program_id}")
            logger.info(f"Authority: {self.authority.pubkey()}")

        except Exception as e:
            logger.error(f"Failed to connect to Solana: {e}")
            raise

    async def disconnect(self):
        """Close Solana connection"""
        if self.client:
            await self.client.close()
            logger.info("Disconnected from Solana")

    def is_connected(self) -> bool:
        """Check if connected"""
        return self.client is not None

    async def prepare_deposit(self, wallet_address: str, amount_sol: float) -> str:
        """
        Prepare deposit transaction.
        In production, this would create the transaction and return it for the user to sign.
        """
        try:
            amount_lamports = int(amount_sol * 1_000_000_000)  # Convert SOL to lamports

            # TODO: Build deposit instruction using Anchor
            # tx = await self.program.rpc["deposit"](
            #     amount_lamports,
            #     ctx=Context(
            #         accounts={
            #             "treasury": treasury_pda,
            #             "depositor": Pubkey.from_string(wallet_address),
            #             "treasury_vault": vault_pda,
            #             "system_program": SYS_PROGRAM_ID,
            #         }
            #     )
            # )

            # Mock transaction ID for development
            tx_signature = f"deposit_tx_{wallet_address[:8]}_{int(amount_lamports)}"

            logger.info(f"Prepared deposit: {amount_sol} SOL from {wallet_address}")

            return tx_signature

        except Exception as e:
            logger.error(f"Deposit preparation failed: {e}")
            raise

    async def withdraw(self, recipient: str, amount_sol: float) -> str:
        """
        Execute withdrawal from treasury (requires authority signature).
        """
        try:
            amount_lamports = int(amount_sol * 1_000_000_000)

            # TODO: Build withdraw instruction using Anchor
            # tx = await self.program.rpc["withdraw"](
            #     amount_lamports,
            #     ctx=Context(
            #         accounts={
            #             "treasury": treasury_pda,
            #             "authority": self.authority.pubkey(),
            #             "treasury_vault": vault_pda,
            #             "recipient": Pubkey.from_string(recipient),
            #             "system_program": SYS_PROGRAM_ID,
            #         },
            #         signers=[self.authority]
            #     )
            # )

            # Mock transaction ID
            tx_signature = f"withdraw_tx_{recipient[:8]}_{int(amount_lamports)}"

            logger.info(f"Executed withdrawal: {amount_sol} SOL to {recipient}")

            return tx_signature

        except Exception as e:
            logger.error(f"Withdrawal failed: {e}")
            raise

    async def get_treasury_stats(self) -> Dict:
        """
        Get current treasury statistics.
        """
        try:
            # TODO: Call get_stats instruction
            # stats = await self.program.account["Treasury"].fetch(treasury_pda)

            # Mock stats for development
            stats = {
                "total_deposited": 1000.0,  # SOL
                "total_withdrawn": 200.0,   # SOL
                "current_balance": 1640.0,  # SOL (grew from 800 to 1640)
                "treasury_ratio": 1.64,     # current / deposited
                "contract_count": 100,
                "paused": False,
            }

            return stats

        except Exception as e:
            logger.error(f"Failed to get treasury stats: {e}")
            raise

    async def pause_treasury(self):
        """
        Pause treasury (emergency only).
        """
        try:
            # TODO: Call pause instruction
            # tx = await self.program.rpc["pause"](
            #     ctx=Context(
            #         accounts={
            #             "treasury": treasury_pda,
            #             "authority": self.authority.pubkey(),
            #         },
            #         signers=[self.authority]
            #     )
            # )

            logger.warning("Treasury paused")

        except Exception as e:
            logger.error(f"Pause failed: {e}")
            raise

    async def monitor_events(self):
        """
        Monitor deposit/withdrawal events from Solana.
        This would run as a background task.
        """
        logger.info("Event monitor started")

        # TODO: Subscribe to program events
        # while True:
        #     try:
        #         # Listen for DepositEvent, WithdrawEvent, etc.
        #         # Update database when events occur
        #         await asyncio.sleep(1)
        #     except Exception as e:
        #         logger.error(f"Event monitor error: {e}")
