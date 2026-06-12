"""
Optimized Signal Weights
========================

Based on tracked accuracy data:
- BAI and CVD work best for BTC, SOL
- LS_RATIO and FR work best for ETH, XRP
- BTC_CORR hurts altcoin predictions - REMOVED
- FGI is too noisy - REDUCED weight

Each asset gets custom signal weights based on proven performance.
"""

from typing import Dict

# Asset-specific signal weights (0-100, higher = more important)
# Based on accuracy analysis of 456+ predictions

OPTIMIZED_WEIGHTS: Dict[str, Dict[str, float]] = {
    "BTC": {
        # Best performers for BTC
        "BAI": 90,      # Order book imbalance - PROVEN
        "CVD": 85,      # Volume delta - PROVEN
        "WADI": 70,     # Whale activity
        "OBS": 60,      # Order book slope
        
        # Medium performers
        "VRC": 50,      # Volatility regime
        "LCP": 45,      # Liquidity cascade
        
        # Reduced weight (underperforming)
        "FGI": 30,      # Fear/Greed - too contrarian
        "LS_RATIO": 25, # Long/short ratio
        "FR": 25,       # Funding rate
        
        # DISABLED
        "BTC_CORR": 0,  # N/A for BTC itself
    },
    
    "ETH": {
        # Best performers for ETH
        "LS_RATIO": 85, # Long/short - PROVEN
        "FR": 80,       # Funding rate - PROVEN
        "BAI": 70,      # Order book
        
        # Medium performers
        "CVD": 60,
        "OBS": 55,
        "VRC": 50,
        
        # Reduced weight
        "WADI": 30,     # Whale activity - unreliable for ETH
        "FGI": 25,      # Fear/Greed
        
        # DISABLED - was hurting accuracy
        "BTC_CORR": 0,  # Correlation adjustment OFF
    },
    
    "SOL": {
        # Best performers for SOL
        "BAI": 90,      # Order book - PROVEN
        "CVD": 85,      # Volume delta - PROVEN
        "WADI": 75,     # Whale activity
        
        # Medium performers
        "OBS": 60,
        "VRC": 55,
        "LCP": 50,
        
        # Reduced weight (underperforming for SOL)
        "LS_RATIO": 20, # Was hurting predictions
        "FR": 20,       # Funding rate
        "FGI": 25,
        
        # DISABLED - was the WORST signal for SOL
        "BTC_CORR": 0,  # Correlation OFF - SOL doesn't always follow BTC
    },
    
    "XRP": {
        # Best performers for XRP
        "LS_RATIO": 85, # Long/short - PROVEN
        "FR": 80,       # Funding rate - PROVEN
        "BAI": 70,
        
        # Medium performers
        "CVD": 55,
        "OBS": 50,
        "VRC": 45,
        
        # Reduced weight
        "WADI": 25,     # Unreliable for XRP
        "FGI": 20,
        
        # DISABLED
        "BTC_CORR": 0,  # Correlation OFF
    },
}

# Minimum confidence to generate a prediction
MIN_CONFIDENCE_THRESHOLD = 60  # Was 50, raised to reduce noise

# Minimum confidence to consider "tradeable"
TRADEABLE_THRESHOLD = 65

# Signals that should be IGNORED entirely (proven harmful)
DISABLED_SIGNALS = ["BTC_CORR"]

# Signal tier weights (how much each category matters)
TIER_WEIGHTS = {
    "LIQUIDITY": 0.30,    # BAI, OBS, LCP
    "WHALE": 0.25,        # WADI, WC
    "DERIVATIVES": 0.25,  # CVD, FR, LS_RATIO
    "SENTIMENT": 0.10,    # FGI (reduced from 0.15)
    "TECHNICAL": 0.10,    # VRC
}


def get_signal_weight(symbol: str, signal_name: str) -> float:
    """Get the optimized weight for a signal on a specific asset."""
    symbol = symbol.upper()
    signal = signal_name.upper()
    
    # Check if signal is disabled
    if signal in DISABLED_SIGNALS:
        return 0.0
    
    # Get asset-specific weights
    asset_weights = OPTIMIZED_WEIGHTS.get(symbol, OPTIMIZED_WEIGHTS["BTC"])
    
    # Return weight (default to 50 if not specified)
    return asset_weights.get(signal, 50.0)


def calculate_optimized_score(symbol: str, signals: Dict) -> Dict:
    """
    Calculate an optimized directional score using asset-specific weights.
    
    Returns:
        {
            "direction": "LONG" | "SHORT" | "NEUTRAL",
            "confidence": float (0-100),
            "bullish_score": float,
            "bearish_score": float,
            "signals_used": list,
            "signals_ignored": list
        }
    """
    symbol = symbol.upper()
    
    bullish_score = 0
    bearish_score = 0
    total_weight = 0
    signals_used = []
    signals_ignored = []
    
    for sig_name, sig_data in signals.items():
        if not sig_data or not isinstance(sig_data, dict):
            continue
        
        # Get optimized weight
        weight = get_signal_weight(symbol, sig_name)
        
        if weight == 0:
            signals_ignored.append(sig_name)
            continue
        
        signal_val = sig_data.get("signal", "").upper()
        strength = sig_data.get("strength", 50)
        
        # Weighted contribution
        contribution = (weight / 100) * strength
        
        if "BULLISH" in signal_val or signal_val == "UP":
            bullish_score += contribution
            signals_used.append(f"{sig_name}:BULL")
        elif "BEARISH" in signal_val or signal_val == "DOWN":
            bearish_score += contribution
            signals_used.append(f"{sig_name}:BEAR")
        elif signal_val == "FEAR":  # Contrarian
            bullish_score += contribution * 0.5  # Reduced contrarian weight
            signals_used.append(f"{sig_name}:FEAR(bull)")
        elif signal_val == "GREED":
            bearish_score += contribution * 0.5
            signals_used.append(f"{sig_name}:GREED(bear)")
        elif signal_val == "LEAN_SHORT":
            bullish_score += contribution * 0.3  # Contrarian
            signals_used.append(f"{sig_name}:LS(bull)")
        elif signal_val == "LEAN_LONG":
            bearish_score += contribution * 0.3
            signals_used.append(f"{sig_name}:LL(bear)")
        else:
            signals_used.append(f"{sig_name}:NEUTRAL")
        
        total_weight += weight
    
    # Calculate direction and confidence
    total = bullish_score + bearish_score
    
    if total > 0:
        if bullish_score > bearish_score * 1.1:  # Need 10% edge
            direction = "LONG"
            confidence = min(90, 50 + (bullish_score - bearish_score) / 3)
        elif bearish_score > bullish_score * 1.1:
            direction = "SHORT"
            confidence = min(90, 50 + (bearish_score - bullish_score) / 3)
        else:
            direction = "NEUTRAL"
            confidence = 50
    else:
        direction = "NEUTRAL"
        confidence = 50
    
    # Apply minimum threshold
    if confidence < MIN_CONFIDENCE_THRESHOLD:
        direction = "NEUTRAL"
    
    return {
        "direction": direction,
        "confidence": confidence,
        "bullish_score": bullish_score,
        "bearish_score": bearish_score,
        "signals_used": signals_used,
        "signals_ignored": signals_ignored,
        "tradeable": confidence >= TRADEABLE_THRESHOLD
    }


