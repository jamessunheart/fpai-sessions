#!/usr/bin/env python3
"""Add SOL holdings to White Rock Church treasury wallet"""

import sys
import sqlite3
sys.path.insert(0, '/root/agents/services/treasury-arena')

db_path = 'treasury_arena_production.db'

# SOL holdings to add
sol_holdings = 373  # SOL
sol_price = 148  # USD per SOL
sol_value = sol_holdings * sol_price  # $55,204

print('💰 ADDING SOL HOLDINGS TO TREASURY')
print('=' * 60)
print()
print(f'SOL Holdings: {sol_holdings} SOL @ ${sol_price}')
print(f'SOL Value: ${sol_value:,.0f}')
print()

# Update wallet capital
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get current wallet
cursor.execute("SELECT total_capital, cash_balance FROM ai_wallets WHERE user_id = ?",
               ('white-rock-church',))
row = cursor.fetchone()

if not row:
    print('❌ Wallet not found!')
    sys.exit(1)

current_capital = row[0]
current_cash = row[1]

new_capital = current_capital + sol_value
new_cash = current_cash + sol_value

print(f'Current Capital: ${current_capital:,.0f}')
print(f'Adding SOL: ${sol_value:,.0f}')
print(f'New Capital: ${new_capital:,.0f}')
print()

# Update wallet
cursor.execute("""
    UPDATE ai_wallets
    SET total_capital = ?, cash_balance = ?
    WHERE user_id = ?
""", (new_capital, new_cash, 'white-rock-church'))

conn.commit()
conn.close()

print('✅ SOL holdings added to treasury!')
print()
print('Updated White Rock Church Wallet:')
print(f'  Total Capital: ${new_capital:,.0f}')
print(f'  Cash Balance: ${new_cash:,.0f}')
print(f'  Ready for AI management')
print()
print('=' * 60)
print(f'TREASURY NOW MANAGING: ${new_capital:,.0f}')
print('=' * 60)
