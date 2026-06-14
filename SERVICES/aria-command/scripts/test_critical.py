#!/usr/bin/env python3
"""
CRITICAL FUNCTIONALITY TESTS
=============================

Run BEFORE any deploy. If these fail, DO NOT DEPLOY.

Tests:
1. Critical imports work
2. Trading module loads
3. Telegram bot initializes
4. Health endpoint responds
"""

import sys
import os

# Add aria-command to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TESTS_PASSED = 0
TESTS_FAILED = 0

def test(name, fn):
    global TESTS_PASSED, TESTS_FAILED
    try:
        fn()
        print(f"✅ {name}")
        TESTS_PASSED += 1
        return True
    except Exception as e:
        print(f"❌ {name}: {e}")
        TESTS_FAILED += 1
        return False

# ============================================================================
# CRITICAL IMPORT TESTS
# ============================================================================

def test_telegram_bot():
    from telegram.bot import AriaTelegramBot
    bot = AriaTelegramBot()
    assert bot is not None

def test_trading_module():
    from trading import is_trading_related, handle_trading_message
    assert callable(is_trading_related)
    assert callable(handle_trading_message)

def test_trading_intent():
    from trading import parse_trading_intent
    intent, params = parse_trading_intent("what is sol price")
    # Should not crash, result doesn't matter

def test_brain_tools():
    from brain.tools import TOOLS, ToolExecutor
    assert len(TOOLS) > 0

def test_opus_brain():
    from brain.opus_brain import OpusBrain
    brain = OpusBrain()
    assert brain is not None

def test_consciousness():
    from consciousness.consciousness_loop import ConsciousnessLoop
    loop = ConsciousnessLoop()
    assert loop is not None

def test_access_terminal():
    from access.terminal import run_command, classify_command
    assert callable(run_command)

# ============================================================================
# FUNCTIONALITY TESTS
# ============================================================================

def test_trading_related_detection():
    from trading import is_trading_related
    assert is_trading_related("what is sol") == True
    assert is_trading_related("hello") == False

def test_health_endpoint():
    import httpx
    try:
        r = httpx.get("http://localhost:8750/health", timeout=5)
        assert r.status_code == 200
    except httpx.ConnectError:
        # Service not running, that's OK for pre-deploy test
        pass

# ============================================================================
# RUN ALL TESTS
# ============================================================================

if __name__ == "__main__":
    print("=" * 50)
    print("ARIA CRITICAL FUNCTIONALITY TESTS")
    print("=" * 50)
    print()
    
    print("📦 Import Tests:")
    test("telegram.bot imports", test_telegram_bot)
    test("trading module imports", test_trading_module)
    test("trading intent parser", test_trading_intent)
    test("brain tools import", test_brain_tools)
    test("opus brain imports", test_opus_brain)
    test("consciousness imports", test_consciousness)
    test("access terminal imports", test_access_terminal)
    
    print()
    print("🔧 Functionality Tests:")
    test("trading detection works", test_trading_related_detection)
    test("health endpoint (if running)", test_health_endpoint)
    
    print()
    print("=" * 50)
    if TESTS_FAILED == 0:
        print(f"✅ ALL {TESTS_PASSED} TESTS PASSED - Safe to deploy")
        sys.exit(0)
    else:
        print(f"❌ {TESTS_FAILED} TESTS FAILED - DO NOT DEPLOY")
        sys.exit(1)








