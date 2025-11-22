#!/usr/bin/env python3
"""Test script to validate MEM0_API_KEY"""
from __future__ import annotations
import os
import sys
from dotenv import load_dotenv
from app.memory_mem0 import MemoryMem0

def test_api_key():
    """Test if the MEM0_API_KEY is valid"""
    load_dotenv()
    
    api_key = os.getenv("MEM0_API_KEY")
    
    if not api_key:
        print("❌ ERROR: MEM0_API_KEY is not set in environment or .env file")
        print("\nTo fix this:")
        print("1. Create a .env file in the project root")
        print("2. Add: MEM0_API_KEY=your-api-key-here")
        print("3. Get your API key from: https://app.mem0.ai/dashboard/api-keys")
        return False
    
    print(f"✓ API key found: {api_key[:10]}...{api_key[-4:]}")
    print("Testing API connection...")
    
    try:
        mem = MemoryMem0(api_key=api_key)
        # Test with a simple message (user_id is required by API)
        result = mem.store("user", "Test message from API key validation", user_id="test_user")
        print("✓ API key is valid! Successfully stored test message.")
        print(f"  Response: {result}")
        return True
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        return False
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_api_key()
    sys.exit(0 if success else 1)

