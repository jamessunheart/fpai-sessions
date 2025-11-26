#!/usr/bin/env python3
"""
🎯 WHALETRACK + MAGNET TRADING SYSTEM

Complete autonomous trading system that combines all engines:
1. Whale Position Engine
2. Magnet Scanner
3. Flow Map
4. Entry Engine
5. Exit Engine
6. Reversal Engine

Trade Loop:
1. Identify whale direction
2. Scan all magnets
3. Score each magnet
4. Determine cheapest path
5. Wait for alignment
6. Enter with whale momentum or on retrace
7. Exit at magnet or front-run
8. After sweep, check reversal
9. If reversal conditions hit → enter opposite
10. Repeat
"""
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
from .whale_engine import WhalePositionEngine, WhaleState, Candle
from .magnet_scanner import MagnetScanner, Magnet
from .flow_map import FlowMapEngine, FlowPath
from .entry_engine import EntryEngine, EntrySignal
from .exit_engine import ExitEngine, ExitSignal
from .reversal_engine import ReversalEngine, ReversalSignal


@dataclass
class Position:
    """Active trading position"""
    entry_price: float
    stop_loss: float
    target_price: float
    size: float
    is_long: bool
    entry_time: datetime
    entry_type: str
    magnet_price: float


@dataclass
class SystemState:
    """Current state of the trading system"""
    whale_state: WhaleState
    magnets: List[Magnet]
    flow_path: Optional[FlowPath]
    entry_signal: Optional[EntrySignal]
    exit_signal: Optional[ExitSignal]
    reversal_signal: Optional[ReversalSignal]
    position: Optional[Position]
    last_update: datetime


class WhaleTrackTradingSystem:
    """
    Complete trading system orchestration.
    """
    
    def __init__(self,
                 max_positions: int = 1,
                 max_trades_per_session: int = 2):
        # Initialize all engines
        self.whale_engine = WhalePositionEngine()
        self.magnet_scanner = MagnetScanner()
        self.flow_engine = FlowMapEngine()
        self.entry_engine = EntryEngine()
        self.exit_engine = ExitEngine()
        self.reversal_engine = ReversalEngine()
        
        # Risk management
        self.max_positions = max_positions
        self.max_trades_per_session = max_trades_per_session
        
        # State
        self.position: Optional[Position] = None
        self.trades_today = 0
        self.last_state: Optional[SystemState] = None
    
    def update(self, 
               candles: List[Candle],
               liquidation_data: Optional[List[dict]] = None,
               volume_profile: Optional[List] = None) -> SystemState:
        """
        Main system update.
        
        Call this on every new candle.
        
        Returns current SystemState.
        """
        current_price = candles[-1].close
        
        # 1. Analyze whale position
        whale_state = self.whale_engine.analyze(candles)
        
        # 2. Scan for magnets
        magnets = self.magnet_scanner.scan(
            candles=candles,
            current_price=current_price,
            whale_direction=whale_state.direction.value,
            liquidation_data=liquidation_data,
            volume_profile=volume_profile
        )
        
        # 3. Calculate flow path
        flow_path = self.flow_engine.calculate_flow(
            whale_state=whale_state,
            magnets=magnets,
            current_price=current_price
        )
        
        # 4. Check for exit (if position exists)
        exit_signal = None
        if self.position:
            exit_signal = self.exit_engine.check_exit(
                position_entry=self.position.entry_price,
                position_stop=self.position.stop_loss,
                position_target=self.position.target_price,
                current_price=current_price,
                magnet_price=self.position.magnet_price,
                is_long=self.position.is_long,
                candles=candles
            )
            
            if exit_signal:
                # Close position
                self._close_position(exit_signal)
        
        # 5. Check for reversal
        reversal_signal = None
        if not self.position:  # Only check if no position
            magnet_price = flow_path.selected_magnet.price if flow_path else None
            reversal_signal = self.reversal_engine.detect_reversal(
                candles=candles,
                whale_state=whale_state,
                magnet_price=magnet_price
            )
        
        # 6. Generate entry signal (if no position)
        entry_signal = None
        if not self.position and self.trades_today < self.max_trades_per_session:
            if flow_path:
                entry_signal = self.entry_engine.generate_signal(
                    whale_state=whale_state,
                    flow_path=flow_path,
                    current_price=current_price,
                    candles=candles
                )
                
                if entry_signal:
                    # Check if we should enter
                    if self._should_enter(entry_signal):
                        self._open_position(entry_signal, flow_path, current_price)
        
        # 7. Update state
        state = SystemState(
            whale_state=whale_state,
            magnets=magnets,
            flow_path=flow_path,
            entry_signal=entry_signal,
            exit_signal=exit_signal,
            reversal_signal=reversal_signal,
            position=self.position,
            last_update=datetime.now()
        )
        
        self.last_state = state
        
        return state
    
    def _should_enter(self, entry_signal: EntrySignal) -> bool:
        """
        Risk checks before entering.
        """
        # Check confidence
        if entry_signal.confidence < 60:
            return False
        
        # Check R:R
        if entry_signal.risk_reward < 2.0:
            return False
        
        # Check max positions
        if self.position is not None:
            return False
        
        # Check max trades
        if self.trades_today >= self.max_trades_per_session:
            return False
        
        return True
    
    def _open_position(self, entry_signal: EntrySignal, 
                      flow_path: FlowPath, current_price: float):
        """Open a new position."""
        
        # Determine size based on confidence
        base_size = 1.0
        size = base_size * entry_signal.size_multiplier
        
        self.position = Position(
            entry_price=entry_signal.entry_price,
            stop_loss=entry_signal.stop_loss,
            target_price=entry_signal.target_price,
            size=size,
            is_long=entry_signal.entry_price < entry_signal.target_price,
            entry_time=datetime.now(),
            entry_type=entry_signal.entry_type.value,
            magnet_price=flow_path.selected_magnet.price
        )
        
        self.trades_today += 1
    
    def _close_position(self, exit_signal: ExitSignal):
        """Close the current position."""
        self.position = None
    
    def get_summary(self) -> dict:
        """Get system summary for API/Dashboard."""
        if not self.last_state:
            return {"status": "initializing"}
        
        state = self.last_state
        
        return {
            "timestamp": state.last_update.isoformat(),
            "whale": {
                "direction": state.whale_state.direction.value,
                "velocity": round(state.whale_state.velocity, 1),
                "confidence": round(state.whale_state.confidence, 1),
                "displacement": round(state.whale_state.displacement_score, 1)
            },
            "magnets": {
                "total": len(state.magnets),
                "top_3": [
                    {
                        "price": m.price,
                        "score": round(m.score, 1),
                        "type": m.type.value,
                        "distance": round(m.distance, 2)
                    }
                    for m in state.magnets[:3]
                ]
            },
            "flow": {
                "active": state.flow_path is not None,
                "target": state.flow_path.selected_magnet.price if state.flow_path else None,
                "efficiency": round(state.flow_path.efficiency_score, 1) if state.flow_path else 0,
                "confidence": round(state.flow_path.confidence, 1) if state.flow_path else 0
            },
            "signals": {
                "entry": {
                    "active": state.entry_signal is not None,
                    "type": state.entry_signal.entry_type.value if state.entry_signal else None,
                    "price": state.entry_signal.entry_price if state.entry_signal else None,
                    "confidence": round(state.entry_signal.confidence, 1) if state.entry_signal else 0
                },
                "exit": {
                    "active": state.exit_signal is not None,
                    "type": state.exit_signal.exit_type.value if state.exit_signal else None
                },
                "reversal": {
                    "active": state.reversal_signal is not None,
                    "type": state.reversal_signal.reversal_type.value if state.reversal_signal else None,
                    "confidence": round(state.reversal_signal.confidence, 1) if state.reversal_signal else 0
                }
            },
            "position": {
                "active": state.position is not None,
                "entry": state.position.entry_price if state.position else None,
                "target": state.position.target_price if state.position else None,
                "stop": state.position.stop_loss if state.position else None,
                "type": "LONG" if state.position and state.position.is_long else "SHORT" if state.position else None
            },
            "trades_today": self.trades_today
        }

