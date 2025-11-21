#!/usr/bin/env python3
"""Run AI optimizer to get optimal allocation for White Rock Church wallet"""

import sys
sys.path.insert(0, '/root/SERVICES/treasury-arena')

from src.tokenization.ai_optimizer import AIWalletOptimizer
from src.tokenization.models import AIWallet, StrategyToken

db_path = 'treasury_arena_production.db'

print('🤖 TREASURY ARENA AI OPTIMIZER')
print('=' * 60)
print()

# Load wallet and tokens
print('Loading White Rock Church wallet...')
# Load wallet from database
import sqlite3
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT * FROM ai_wallets WHERE user_id = ?", ('white-rock-church',))
row = cursor.fetchone()
conn.close()

if not row:
    print('❌ Wallet not found!')
    sys.exit(1)

# Reconstruct wallet object
from src.tokenization.models import WalletMode, RiskTolerance
wallet = AIWallet(
    id=row[0],
    wallet_address=row[1],
    user_id=row[2],
    user_name=row[3],
    mode=WalletMode(row[4]),
    risk_tolerance=RiskTolerance(row[5]),
    total_capital=row[6],
    cash_balance=row[7],
    invested_balance=row[8]
)

print(f'✅ Wallet loaded: ${wallet.total_capital:,.0f} capital')
print()

print('Loading available strategy tokens...')
tokens = StrategyToken.list_active(db_path)
print(f'✅ Found {len(tokens)} active strategy tokens')
print()

# Run optimizer
print('Running mean-variance optimization...')
print('Objective: Maximize Sharpe ratio')
print('Constraints: Risk tolerance = MODERATE')
print()

optimizer = AIWalletOptimizer(db_path)
recommendation = optimizer.optimize_wallet(wallet, tokens)

print('=' * 60)
print('📊 AI OPTIMIZATION RESULTS')
print('=' * 60)
print()

print(f'Expected Annual Return: {recommendation.expected_return_pct:.1f}%')
print(f'Expected Volatility: {recommendation.expected_volatility:.1f}%')
print(f'Expected Sharpe Ratio: {recommendation.expected_sharpe:.2f}')
print()

print('=' * 60)
print('💰 RECOMMENDED ALLOCATION ($373,000 total)')
print('=' * 60)
print()

# Sort by allocation amount
allocations = sorted(recommendation.target_allocations,
                     key=lambda x: x.target_weight, reverse=True)

total_allocated = 0
for alloc in allocations:
    amount = wallet.total_capital * alloc.target_weight
    total_allocated += amount

    # Find the token to get its details
    token = next((t for t in tokens if t.token_symbol == alloc.token_symbol), None)
    if token:
        print(f'{alloc.token_symbol}')
        print(f'  Strategy: {token.strategy_name}')
        print(f'  Allocation: ${amount:,.0f} ({alloc.target_weight*100:.1f}%)')
        print(f'  Sharpe: {token.sharpe_ratio}')
        print(f'  Current NAV: ${token.current_nav:.4f}')
        print(f'  Tokens to buy: {alloc.target_quantity:.2f}')
        print()

print('=' * 60)
print(f'Total Allocated: ${total_allocated:,.0f}')
print(f'Cash Remaining: ${wallet.total_capital - total_allocated:,.0f}')
print('=' * 60)
print()

print('📋 BUY ORDERS TO EXECUTE:')
print()
for order in recommendation.buy_orders:
    token = next((t for t in tokens if t.token_symbol == order.token_symbol), None)
    if token:
        cost = order.quantity * token.current_nav
        print(f'BUY {order.quantity:.2f} {order.token_symbol} @ ${token.current_nav:.4f} = ${cost:,.2f}')

print()
print('✅ AI optimization complete!')
print()
print('Next step: Execute these buy orders to deploy capital')
