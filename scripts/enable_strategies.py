#!/usr/bin/env python3
"""Enable Momentum Rider and Signal Shark MAX in the trading loop."""

import sys
sys.path.insert(0, "/opt/fpai/services/whaletrack-magnet")

def main():
    # Read the direct_signal_trader.py
    with open("/opt/fpai/services/whaletrack-magnet/core/direct_signal_trader.py", "r") as f:
        content = f.read()
    
    modified = False
    
    # 1. Add MOMENTUM_RIDER_CONFIG if not present
    if "MOMENTUM_RIDER_CONFIG" not in content:
        momentum_config = '''
# Momentum Rider - trades strong 24h moves (>3% change)
MOMENTUM_RIDER_CONFIG = TraderConfig(
    name="Momentum Rider",
    min_confidence=55.0,
    min_probability=50.0,
    base_position_pct=8.0,
    high_conf_position_pct=15.0,
    extreme_conf_position_pct=25.0,
    default_leverage=1.25,
    max_leverage=1.75,
    stop_loss_pct=3.5,
    max_positions=2,
    cooldown_minutes=30.0
)

'''
        insert_point = content.find("class DirectSignalTrader:")
        if insert_point > 0:
            content = content[:insert_point] + momentum_config + content[insert_point:]
            print("✅ Added MOMENTUM_RIDER_CONFIG")
            modified = True
    else:
        print("ℹ️ MOMENTUM_RIDER_CONFIG already exists")
    
    # 2. Add SIGNAL_SHARK_MAX_CONFIG if not present
    if "SIGNAL_SHARK_MAX_CONFIG" not in content:
        shark_max_config = '''
# ⚠️ SIGNAL SHARK MAX - HIGH RISK - Uses up to 5x leverage
SIGNAL_SHARK_MAX_CONFIG = TraderConfig(
    name="Signal Shark MAX",
    min_confidence=70.0,
    min_probability=65.0,
    base_position_pct=40.0,
    high_conf_position_pct=60.0,
    extreme_conf_position_pct=80.0,
    default_leverage=2.0,
    max_leverage=5.0,
    stop_loss_pct=3.0,
    max_positions=2,
    cooldown_minutes=10.0
)

'''
        insert_point = content.find("class DirectSignalTrader:")
        if insert_point > 0:
            content = content[:insert_point] + shark_max_config + content[insert_point:]
            print("✅ Added SIGNAL_SHARK_MAX_CONFIG (⚠️ HIGH RISK)")
            modified = True
    else:
        print("ℹ️ SIGNAL_SHARK_MAX_CONFIG already exists")
    
    # 3. Update get_direct_trader to handle these profiles
    if 'elif profile == "momentum_rider"' not in content:
        # Find the sweep_signal elif and add after it
        old_else = 'else:  # aggressive'
        new_else = '''elif profile == "momentum_rider":
            _traders[profile] = DirectSignalTrader(MOMENTUM_RIDER_CONFIG)
        elif profile == "signal_shark_max":
            _traders[profile] = DirectSignalTrader(SIGNAL_SHARK_MAX_CONFIG)
        else:  # aggressive'''
        
        if old_else in content:
            content = content.replace(old_else, new_else)
            print("✅ Updated get_direct_trader for momentum_rider and signal_shark_max")
            modified = True
    else:
        print("ℹ️ get_direct_trader already handles momentum_rider")
    
    # 4. Update get_all_traders to include the new traders
    if 'get_direct_trader("momentum_rider")' not in content:
        old_return = '''get_direct_trader("sweep_signal")
    return _traders'''
        new_return = '''get_direct_trader("sweep_signal")
    get_direct_trader("momentum_rider")
    get_direct_trader("signal_shark_max")
    return _traders'''
        
        if old_return in content:
            content = content.replace(old_return, new_return)
            print("✅ Updated get_all_traders to include momentum_rider and signal_shark_max")
            modified = True
    else:
        print("ℹ️ get_all_traders already includes momentum_rider")
    
    if modified:
        with open("/opt/fpai/services/whaletrack-magnet/core/direct_signal_trader.py", "w") as f:
            f.write(content)
        print("\n✅ Changes saved! Restart service to apply.")
    else:
        print("\nℹ️ No changes needed")

if __name__ == "__main__":
    main()











