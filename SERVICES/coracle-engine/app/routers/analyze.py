"""
Coracle Analysis Router
========================
Main endpoint for generating trading contracts from signal analysis.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.models import (
    AnalysisRequest, AnalysisResponse, Direction,
    SignalSnapshot, TradingContract
)
from app.config import get_settings

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
settings = get_settings()


@router.post("/analyze", response_model=AnalysisResponse)
@limiter.limit("30/minute")
async def analyze_market(request: Request, req: AnalysisRequest) -> AnalysisResponse:
    """
    Analyze market and generate trading contract.
    
    This is the main endpoint for contract generation. It:
    1. Gathers all signals for the asset
    2. Validates the Sacred Three-Key Gate
    3. Calculates confluence score
    4. Generates contract with entry, SL, and TP levels
    
    Args:
        ticker: Asset symbol (BTC, ETH, XRP, SOL)
        direction: Force direction (LONG/SHORT) or auto-detect
        entry_type: MOMENTUM, RETRACE, or REVERSAL
        capital: Capital amount for position sizing
    
    Returns:
        Complete trading contract or error if gate validation fails
    """
    ticker = req.ticker.upper().replace("/USDT", "").replace("USDT", "")
    
    if ticker not in settings.tracked_assets:
        raise HTTPException(
            status_code=400,
            detail=f"Asset {ticker} not tracked. Available: {settings.tracked_assets}"
        )
    
    try:
        # Get engine components from app state
        ingestor = request.app.state.ingestor
        processor = request.app.state.processor
        sacred_gate = request.app.state.sacred_gate
        confluence = request.app.state.confluence
        contract_generator = request.app.state.contract_generator
        
        # 1. Ingest raw signals from all sources
        raw_signals = await ingestor.gather_signals(ticker)
        
        # 2. Process and compute derived signals
        signals = await processor.process_signals(ticker, raw_signals)
        
        # 3. Determine direction if not specified
        direction = req.direction
        if direction is None:
            direction = confluence.detect_direction(signals)
        
        # 4. Validate Sacred Three-Key Gate
        gate_result = sacred_gate.validate(signals, direction)
        
        if not gate_result.passed:
            return AnalysisResponse(
                success=False,
                signals=signals,
                gate_status=gate_result,
                error=f"Sacred gate failed: {gate_result.keys_passed}/3 keys passed",
                analysis_timestamp=datetime.utcnow()
            )
        
        # 5. Calculate confluence score
        confluence_result = confluence.calculate(signals, direction)
        
        # 6. Generate contract
        contract = contract_generator.generate(
            symbol=ticker,
            direction=direction,
            entry_type=req.entry_type,
            signals=signals,
            gate_result=gate_result,
            confluence_result=confluence_result,
            capital=req.capital
        )
        
        return AnalysisResponse(
            success=True,
            contract=contract,
            signals=signals,
            gate_status=gate_result,
            confluence=confluence_result,
            analysis_timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        return AnalysisResponse(
            success=False,
            error=str(e),
            analysis_timestamp=datetime.utcnow()
        )


@router.get("/signals/{symbol}", response_model=SignalSnapshot)
@limiter.limit("60/minute")
async def get_signals(request: Request, symbol: str) -> SignalSnapshot:
    """
    Get current signal snapshot for a symbol.
    
    Returns all available signals without contract generation.
    Useful for monitoring and debugging.
    """
    symbol = symbol.upper().replace("/USDT", "").replace("USDT", "")
    
    if symbol not in settings.tracked_assets:
        raise HTTPException(
            status_code=400,
            detail=f"Asset {symbol} not tracked. Available: {settings.tracked_assets}"
        )
    
    try:
        ingestor = request.app.state.ingestor
        processor = request.app.state.processor
        
        raw_signals = await ingestor.gather_signals(symbol)
        signals = await processor.process_signals(symbol, raw_signals)
        
        return signals
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/gate-check/{symbol}")
@limiter.limit("60/minute")
async def check_gate(
    request: Request, 
    symbol: str, 
    direction: Direction = Direction.LONG
):
    """
    Check Sacred Gate status without generating contract.
    
    Quick validation to see if trading conditions are met.
    """
    symbol = symbol.upper().replace("/USDT", "").replace("USDT", "")
    
    if symbol not in settings.tracked_assets:
        raise HTTPException(
            status_code=400,
            detail=f"Asset {symbol} not tracked."
        )
    
    try:
        ingestor = request.app.state.ingestor
        processor = request.app.state.processor
        sacred_gate = request.app.state.sacred_gate
        
        raw_signals = await ingestor.gather_signals(symbol)
        signals = await processor.process_signals(symbol, raw_signals)
        gate_result = sacred_gate.validate(signals, direction)
        
        return {
            "symbol": symbol,
            "direction": direction,
            "gate_passed": gate_result.passed,
            "keys_passed": gate_result.keys_passed,
            "whale_key": gate_result.whale_key.dict(),
            "liquidity_key": gate_result.liquidity_key.dict(),
            "gamma_key": gate_result.gamma_key.dict(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/capacity/{symbol}")
@limiter.limit("60/minute")
async def get_capacity(request: Request, symbol: str):
    """
    Get capacity oracle state for a symbol.
    
    Returns current capacity level and max position sizing recommendation.
    """
    symbol = symbol.upper()
    
    if symbol not in settings.tracked_assets:
        raise HTTPException(
            status_code=400,
            detail=f"Asset {symbol} not tracked."
        )
    
    # Placeholder - will be populated when capacity oracle is implemented
    return {
        "symbol": symbol,
        "capacity_level": "high",
        "max_position_pct": 100,
        "contributing_signals": {},
        "timestamp": datetime.utcnow().isoformat()
    }


