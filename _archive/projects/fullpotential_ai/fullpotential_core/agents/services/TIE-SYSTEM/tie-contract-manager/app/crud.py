"""
CRUD operations for TIE contracts
"""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime

from app.database import TIEContractDB
from app.models import TIEContract, ContractStatus


async def generate_contract_id(db: AsyncSession) -> str:
    """Generate unique contract ID"""
    result = await db.execute(select(func.count()).select_from(TIEContractDB))
    count = result.scalar_one()
    return f"TIE-{count + 1:06d}"


async def create_contract(
    db: AsyncSession,
    contract_id: str,
    nft_mint: str,
    owner: str,
    sol_deposited: float,
    contract_value: float,
    deposit_tx: str,
    status: ContractStatus,
    voting_weight: int
) -> TIEContractDB:
    """Create new contract record"""

    metadata_uri = f"https://tie.fullpotential.com/metadata/{contract_id}.json"

    contract = TIEContractDB(
        contract_id=contract_id,
        nft_mint=nft_mint,
        owner=owner,
        sol_deposited=sol_deposited,
        contract_value=contract_value,
        deposit_tx=deposit_tx,
        status=status.value,
        voting_weight=voting_weight,
        issue_date=datetime.utcnow(),
        metadata_uri=metadata_uri
    )

    db.add(contract)
    await db.commit()
    await db.refresh(contract)

    return contract


async def get_user_contracts(
    db: AsyncSession,
    wallet: str
) -> List[TIEContract]:
    """Get all contracts for a wallet"""

    result = await db.execute(
        select(TIEContractDB).where(TIEContractDB.owner == wallet)
    )

    contracts = result.scalars().all()

    return [TIEContract.model_validate(c) for c in contracts]


async def get_contract_by_mint(
    db: AsyncSession,
    nft_mint: str
) -> Optional[TIEContract]:
    """Get contract by NFT mint address"""

    result = await db.execute(
        select(TIEContractDB).where(TIEContractDB.nft_mint == nft_mint)
    )

    contract = result.scalar_one_or_none()

    return TIEContract.model_validate(contract) if contract else None


async def update_contract_status(
    db: AsyncSession,
    contract_id: str,
    status: ContractStatus,
    voting_weight: int
) -> Optional[TIEContractDB]:
    """Update contract status (held → redeemed)"""

    result = await db.execute(
        select(TIEContractDB).where(TIEContractDB.contract_id == contract_id)
    )

    contract = result.scalar_one_or_none()

    if contract:
        contract.status = status.value
        contract.voting_weight = voting_weight

        if status == ContractStatus.REDEEMED:
            contract.redeemed_date = datetime.utcnow()

        await db.commit()
        await db.refresh(contract)

    return contract
