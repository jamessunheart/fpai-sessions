#!/usr/bin/env python3
"""Add Sweep Signal trader to direct_signal_trader.py"""

import os
import sys

BASE_PATH = "/opt/fpai/services/whaletrack-magnet"

def update_direct_signal_trader():
    filepath = os.path.join(BASE_PATH, "core/direct_signal_trader.py")
    
    with open(filepath, "r") as f:
        content = f.read()
    
    modified = False
    
    # 1. Add SWEEP_SIGNAL_CONFIG if not present
    if "SWEEP_SIGNAL_CONFIG" not in content:
        insert_point = content.find("class DirectSignalTrader:")
        if insert_point > 0:
            sweep_config = '''
# Sweep Signal Trader - trades on sweep alerts using direct signal methodology
SWEEP_SIGNAL_CONFIG = TraderConfig(
    name="Sweep Signal",
    min_confidence=70.0,
    min_probability=65.0,
    base_position_pct=15.0,
    high_conf_position_pct=30.0,
    extreme_conf_position_pct=50.0,
    default_leverage=1.25,
    max_leverage=1.5,
    stop_loss_pct=3.0,
    max_positions=3,
    cooldown_minutes=10.0
)

'''
            content = content[:insert_point] + sweep_config + content[insert_point:]
            print("✅ Added SWEEP_SIGNAL_CONFIG")
            modified = True
    else:
        print("ℹ️ SWEEP_SIGNAL_CONFIG already present")
    
    # 2. Update get_direct_trader to handle sweep_signal
    if 'elif profile == "sweep_signal"' not in content:
        old_pattern = 'else:  # aggressive'
        new_pattern = '''elif profile == "sweep_signal":
            _traders[profile] = DirectSignalTrader(SWEEP_SIGNAL_CONFIG)
        else:  # aggressive'''
        
        if old_pattern in content:
            content = content.replace(old_pattern, new_pattern)
            print("✅ Updated get_direct_trader for sweep_signal")
            modified = True
    else:
        print("ℹ️ get_direct_trader already handles sweep_signal")
    
    # 3. Update get_all_traders to include sweep_signal
    if 'get_direct_trader("sweep_signal")' not in content:
        old_all = '''get_direct_trader("aggressive")
    return _traders'''
        new_all = '''get_direct_trader("aggressive")
    get_direct_trader("sweep_signal")
    return _traders'''
        
        if old_all in content:
            content = content.replace(old_all, new_all)
            print("✅ Updated get_all_traders to include sweep_signal")
            modified = True
    else:
        print("ℹ️ get_all_traders already includes sweep_signal")
    
    if modified:
        with open(filepath, "w") as f:
            f.write(content)
        print("\n✅ direct_signal_trader.py updated successfully!")
    else:
        print("\nℹ️ No changes needed")

if __name__ == "__main__":
    update_direct_signal_trader()











