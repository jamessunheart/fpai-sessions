#!/usr/bin/env python3
"""Patch bot.py to add trading commands."""

# Read current bot.py
with open("/opt/fpai/aria-command/telegram/bot.py", "r") as f:
    content = f.read()

# 1. Add trading commands to the command dictionary
old_commands = '''            "/inventory": self._handle_inventory,
            "/activate": self._handle_activate,
            "/deactivate": self._handle_deactivate,
        }'''

new_commands = '''            "/inventory": self._handle_inventory,
            "/activate": self._handle_activate,
            "/deactivate": self._handle_deactivate,
            # Trading commands
            "/trade": self._handle_trade,
            "/close": self._handle_close,
            "/positions": self._handle_positions,
            "/balance": self._handle_balance,
            "/cancel_trade": self._handle_cancel_trade,
        }'''

if old_commands in content:
    content = content.replace(old_commands, new_commands)
    print("Added trading commands to dictionary")
else:
    print("WARNING: Command dictionary pattern not found")

# 2. Add trading command handlers before the _handle_help method
insertion_point = content.find("    async def _handle_help(")

trading_handlers = '''
    # ========================================================================
    # TRADING COMMANDS  
    # ========================================================================
    
    async def _handle_trade(self, chat_id: int, args: str) -> CommandResult:
        """Handle /trade command - place trades."""
        from .trading_commands import handle_trade
        result = await handle_trade(args)
        return CommandResult(text=result.text, success=result.success)
    
    async def _handle_close(self, chat_id: int, args: str) -> CommandResult:
        """Handle /close command - close positions."""
        from .trading_commands import handle_close
        result = await handle_close(args)
        return CommandResult(text=result.text, success=result.success)
    
    async def _handle_positions(self, chat_id: int, args: str) -> CommandResult:
        """Handle /positions command - show open positions."""
        from .trading_commands import handle_positions
        result = await handle_positions(args)
        return CommandResult(text=result.text, success=result.success)
    
    async def _handle_balance(self, chat_id: int, args: str) -> CommandResult:
        """Handle /balance command - show account balance."""
        from .trading_commands import handle_balance
        result = await handle_balance(args)
        return CommandResult(text=result.text, success=result.success)
    
    async def _handle_cancel_trade(self, chat_id: int, args: str) -> CommandResult:
        """Handle /cancel_trade command - cancel pending trade."""
        from .trading_commands import handle_cancel_trade
        result = await handle_cancel_trade(args)
        return CommandResult(text=result.text, success=result.success)

'''

if insertion_point > 0:
    content = content[:insertion_point] + trading_handlers + content[insertion_point:]
    print("Added trading command handlers")
else:
    print("WARNING: Could not find insertion point")

# 3. Update help text
old_help = '''**Trading:**
/positions - Open positions
/signals - Active signals
/market - Market context'''

new_help = '''**Trading:**
/trade <side> <symbol> <amt> - Place trade
/close <symbol> - Close position  
/close all - EMERGENCY stop ALL
/positions - Open positions
/balance - Account summary
/signals - Active signals
/market - Market context'''

if old_help in content:
    content = content.replace(old_help, new_help)
    print("Updated help text")
else:
    print("WARNING: Help text pattern not found")

# Write updated bot.py
with open("/opt/fpai/aria-command/telegram/bot.py", "w") as f:
    f.write(content)

print("Done! Bot.py updated.")


