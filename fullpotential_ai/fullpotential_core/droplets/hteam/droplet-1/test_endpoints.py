#!/usr/bin/env python3
"""Test script for Full Potential OS API endpoints"""
from __future__ import annotations
import requests
import json
import sys

BASE_URL = "http://localhost:7860"


def print_test(test_name: str):
    """Print test header."""
    print(f"\n{'='*50}")
    print(f"Test: {test_name}")
    print(f"{'='*50}")


def test_health():
    """Test health endpoint."""
    print_test("Health Check")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_chat_basic():
    """Test chat endpoint with basic message."""
    print_test("Chat - Basic Message")
    try:
        payload = {
            "role": "user",
            "content": "Hello, this is a test message"
        }
        response = requests.post(
            f"{BASE_URL}/chat",
            json=payload,
            timeout=10
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_chat_with_user_id():
    """Test chat endpoint with user_id."""
    print_test("Chat - With User ID")
    try:
        payload = {
            "role": "user",
            "content": "Test with custom user ID",
            "user_id": "test_user_123"
        }
        response = requests.post(
            f"{BASE_URL}/chat",
            json=payload,
            timeout=10
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_reflect():
    """Test reflect endpoint."""
    print_test("Reflect")
    try:
        payload = {
            "summary": "Test reflection summary",
            "insights": ["Insight 1", "Insight 2"],
            "decisions": ["Decision A", "Decision B"],
            "user_id": "test_user_123"
        }
        response = requests.post(
            f"{BASE_URL}/reflect",
            json=payload,
            timeout=10
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_intent():
    """Test intent endpoint."""
    print_test("Intent")
    try:
        payload = {
            "intent": "Complete project documentation",
            "horizon_min": 120,
            "tags": ["work", "documentation"],
            "user_id": "test_user_123"
        }
        response = requests.post(
            f"{BASE_URL}/intent",
            json=payload,
            timeout=10
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_error_handling():
    """Test error handling."""
    print_test("Error Handling - Missing Content")
    try:
        payload = {"role": "user"}
        response = requests.post(
            f"{BASE_URL}/chat",
            json=payload,
            timeout=10
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 400  # Should return 400 for missing content
    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "="*50)
    print("Full Potential OS API Endpoint Tests")
    print("="*50)
    
    tests = [
        ("Health Check", test_health),
        ("Chat - Basic", test_chat_basic),
        ("Chat - With User ID", test_chat_with_user_id),
        ("Reflect", test_reflect),
        ("Intent", test_intent),
        ("Error Handling", test_error_handling),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} failed with exception: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*50)
    print("Test Summary")
    print("="*50)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

