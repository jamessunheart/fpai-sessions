#!/usr/bin/env python3
"""Create White Rock Church AI wallet with $373K capital"""

import sys
import uuid
from datetime import datetime
sys.path.insert(0, '/root/agents/services/treasury-arena')

from src.tokenization.models import AIWallet, WalletMode, RiskTolerance

db_path = 'treasury_arena_production.db'

# Create White Rock Church wallet with full $373K capital
wallet = AIWallet(
    wallet_address=str(uuid.uuid4()),
    user_id='white-rock-church',
    user_name='White Rock Church Treasury',
    mode=WalletMode.FULL_AI,
    risk_tolerance=RiskTolerance.MODERATE,
    total_capital=373000.0,
    cash_balance=373000.0,
    invested_balance=0.0
)

wallet.save(db_path)

print('✅ White Rock Church AI Wallet Created!')
print()
print(f'Wallet Address: {wallet.wallet_address}')
print(f'User ID: {wallet.user_id}')
print(f'User Name: {wallet.user_name}')
print(f'Management Mode: {wallet.mode.value.upper()} (AI decides everything)')
print(f'Risk Tolerance: {wallet.risk_tolerance.value.upper()}')
print()
print(f'Capital Summary:')
print(f'  Total Capital: ${wallet.total_capital:,.0f}')
print(f'  Cash Balance: ${wallet.cash_balance:,.0f}')
print(f'  Invested Balance: ${wallet.invested_balance:,.0f}')
print()
print('✅ Ready for AI optimization and capital deployment!')
