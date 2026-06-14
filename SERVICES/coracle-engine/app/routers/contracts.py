"""
Coracle Contracts Router
========================
CRUD operations for trading contracts.
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Request, HTTPException, Query
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.models import (
    TradingContract, ContractListResponse, TradeOutcome, ContractGrade
)
from app.config import get_settings

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
settings = get_settings()

# In-memory contract storage (will be replaced with database)
CONTRACTS_STORE: dict[str, TradingContract] = {}


@router.get("/contracts", response_model=ContractListResponse)
@limiter.limit("60/minute")
async def list_contracts(
    request: Request,
    symbol: Optional[str] = None,
    grade: Optional[ContractGrade] = None,
    outcome: Optional[TradeOutcome] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100)
) -> ContractListResponse:
    """
    List trading contracts with optional filters.
    
    Args:
        symbol: Filter by asset symbol
        grade: Filter by contract grade (A, B, C, D, F)
        outcome: Filter by outcome (WIN, LOSS, BREAKEVEN, PENDING)
        page: Page number
        page_size: Items per page
    """
    contracts = list(CONTRACTS_STORE.values())
    
    # Apply filters
    if symbol:
        symbol = symbol.upper()
        contracts = [c for c in contracts if c.symbol == symbol]
    
    if grade:
        contracts = [c for c in contracts if c.grade == grade]
    
    if outcome:
        contracts = [c for c in contracts if c.outcome == outcome]
    
    # Sort by generated_at descending
    contracts.sort(key=lambda x: x.generated_at, reverse=True)
    
    # Paginate
    total = len(contracts)
    start = (page - 1) * page_size
    end = start + page_size
    paginated = contracts[start:end]
    
    return ContractListResponse(
        contracts=paginated,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/contracts/{contract_id}", response_model=TradingContract)
@limiter.limit("60/minute")
async def get_contract(request: Request, contract_id: str) -> TradingContract:
    """
    Get a specific contract by ID.
    """
    if contract_id not in CONTRACTS_STORE:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    return CONTRACTS_STORE[contract_id]


@router.post("/contracts/{contract_id}/resolve")
@limiter.limit("30/minute")
async def resolve_contract(
    request: Request,
    contract_id: str,
    outcome: TradeOutcome,
    exit_price: float,
    notes: Optional[str] = None
):
    """
    Resolve a contract with the actual outcome.
    
    Used to track prediction accuracy for Brier score calculation.
    
    Args:
        contract_id: Contract to resolve
        outcome: WIN, LOSS, or BREAKEVEN
        exit_price: Actual exit price
        notes: Optional notes about the trade
    """
    if contract_id not in CONTRACTS_STORE:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    contract = CONTRACTS_STORE[contract_id]
    
    if contract.outcome != TradeOutcome.PENDING:
        raise HTTPException(
            status_code=400, 
            detail=f"Contract already resolved with outcome: {contract.outcome}"
        )
    
    # Calculate actual PnL
    if contract.direction.value == "LONG":
        pnl_pct = ((exit_price - contract.entry_price) / contract.entry_price) * 100
    else:
        pnl_pct = ((contract.entry_price - exit_price) / contract.entry_price) * 100
    
    # Update contract
    contract.outcome = outcome
    contract.actual_exit_price = exit_price
    contract.actual_pnl_pct = pnl_pct
    contract.resolved_at = datetime.utcnow()
    
    CONTRACTS_STORE[contract_id] = contract
    
    return {
        "status": "resolved",
        "contract_id": contract_id,
        "outcome": outcome,
        "exit_price": exit_price,
        "pnl_pct": round(pnl_pct, 4),
        "resolved_at": contract.resolved_at.isoformat()
    }


@router.get("/contracts/stats/summary")
@limiter.limit("30/minute")
async def get_contract_stats(request: Request, symbol: Optional[str] = None):
    """
    Get contract performance statistics.
    
    Returns win rate, average PnL, Brier score, and grade distribution.
    """
    contracts = list(CONTRACTS_STORE.values())
    
    if symbol:
        symbol = symbol.upper()
        contracts = [c for c in contracts if c.symbol == symbol]
    
    resolved = [c for c in contracts if c.outcome != TradeOutcome.PENDING]
    
    if not resolved:
        return {
            "total_contracts": len(contracts),
            "resolved_contracts": 0,
            "pending_contracts": len(contracts),
            "win_rate": 0,
            "avg_pnl_pct": 0,
            "brier_score": 0,
            "grade_distribution": {}
        }
    
    # Calculate stats
    wins = [c for c in resolved if c.outcome == TradeOutcome.WIN]
    win_rate = len(wins) / len(resolved) if resolved else 0
    
    pnl_values = [c.actual_pnl_pct for c in resolved if c.actual_pnl_pct is not None]
    avg_pnl = sum(pnl_values) / len(pnl_values) if pnl_values else 0
    
    # Brier score calculation
    # Brier = (1/N) * Σ(forecast - outcome)²
    # outcome: 1 for win, 0 for loss
    brier_sum = 0
    for c in resolved:
        actual = 1 if c.outcome == TradeOutcome.WIN else 0
        predicted = c.confidence_score
        brier_sum += (predicted - actual) ** 2
    
    brier_score = brier_sum / len(resolved) if resolved else 0
    
    # Grade distribution
    grade_dist = {}
    for c in contracts:
        grade = c.grade.value
        if grade not in grade_dist:
            grade_dist[grade] = {"total": 0, "wins": 0, "win_rate": 0}
        grade_dist[grade]["total"] += 1
        if c.outcome == TradeOutcome.WIN:
            grade_dist[grade]["wins"] += 1
    
    for grade in grade_dist:
        total = grade_dist[grade]["total"]
        wins = grade_dist[grade]["wins"]
        grade_dist[grade]["win_rate"] = wins / total if total > 0 else 0
    
    return {
        "total_contracts": len(contracts),
        "resolved_contracts": len(resolved),
        "pending_contracts": len(contracts) - len(resolved),
        "win_rate": round(win_rate, 4),
        "avg_pnl_pct": round(avg_pnl, 4),
        "brier_score": round(brier_score, 4),
        "grade_distribution": grade_dist,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.delete("/contracts/{contract_id}")
@limiter.limit("30/minute")
async def delete_contract(request: Request, contract_id: str):
    """
    Delete a contract (admin only in production).
    """
    if contract_id not in CONTRACTS_STORE:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    del CONTRACTS_STORE[contract_id]
    
    return {"status": "deleted", "contract_id": contract_id}


# Helper function to store contracts (called by contract generator)
def store_contract(contract: TradingContract):
    """Store a contract in the in-memory store."""
    CONTRACTS_STORE[contract.contract_id] = contract


