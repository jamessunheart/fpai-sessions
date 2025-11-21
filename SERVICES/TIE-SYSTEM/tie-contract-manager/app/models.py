"""
Pydantic models for TIE contract management
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class ContractStatus(str, Enum):
    HELD = "held"
    REDEEMED = "redeemed"


class TIEContract(BaseModel):
    """TIE contract NFT representation"""
    contract_id: str
    nft_mint: str
    owner: str

    sol_deposited: float
    contract_value: float  # Always 2x deposited

    status: ContractStatus
    voting_weight: int  # 2 if held, 1 if redeemed

    deposit_tx: str
    issue_date: datetime
    redeemed_date: Optional[datetime] = None

    metadata_uri: str

    class Config:
        from_attributes = True


class MintContractRequest(BaseModel):
    """Request to mint new TIE contract"""
    deposit_tx: str = Field(..., description="Treasury deposit transaction ID")
    wallet: str = Field(..., description="Recipient wallet address")
    sol_deposited: float = Field(..., gt=0, description="Amount of SOL deposited")

    class Config:
        json_schema_extra = {
            "example": {
                "deposit_tx": "5J7Yx...",
                "wallet": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
                "sol_deposited": 10.5
            }
        }


class MintContractResponse(BaseModel):
    """Response after minting contract"""
    contract_id: str
    nft_mint: str
    contract_value: float
    voting_weight: int


class RedeemContractRequest(BaseModel):
    """Request to redeem contract"""
    nft_mint: str
    redeemer: str
    authorization: str = Field(..., description="Authorization from redemption-algorithm")


class RedeemContractResponse(BaseModel):
    """Response after redeeming contract"""
    redeemed: bool
    voting_weight_updated: int


class UserContracts(BaseModel):
    """All contracts for a user"""
    wallet: str
    held_contracts: List[TIEContract]
    redeemed_contracts: List[TIEContract]
    total_held: int
    total_redeemed: int
    total_voting_power: int
