#!/usr/bin/env python3
"""
I PROACTIVE Validation Script
Tests each component independently to find issues quickly
"""

import sys
import traceback

def test_imports():
    """Test that all modules can be imported"""
    print("=" * 60)
    print("TESTING: Module Imports")
    print("=" * 60)

    tests = {
        "config": lambda: __import__("app.config"),
        "models": lambda: __import__("app.models"),
        "model_router": lambda: __import__("app.model_router"),
        "crew_manager": lambda: __import__("app.crew_manager"),
        "memory_manager": lambda: __import__("app.memory_manager"),
        "decision_engine": lambda: __import__("app.decision_engine"),
        "main": lambda: __import__("app.main"),
    }

    results = {}
    for name, test_func in tests.items():
        try:
            test_func()
            results[name] = "✅ PASS"
            print(f"  ✅ {name:20s} - imports successfully")
        except Exception as e:
            results[name] = f"❌ FAIL: {str(e)}"
            print(f"  ❌ {name:20s} - FAILED")
            print(f"     Error: {str(e)}")

    return all("✅" in v for v in results.values()), results


def test_config():
    """Test configuration loading"""
    print("\n" + "=" * 60)
    print("TESTING: Configuration")
    print("=" * 60)

    try:
        from app.config import settings
        print(f"  ✅ Settings loaded")
        print(f"     Service: {settings.service_name}")
        print(f"     Port: {settings.service_port}")
        print(f"     Droplet ID: {settings.droplet_id}")

        # Check for API keys (won't show actual values)
        has_openai = bool(settings.openai_api_key)
        has_anthropic = bool(settings.anthropic_api_key)
        has_google = bool(settings.google_api_key)

        print(f"     OpenAI key configured: {has_openai}")
        print(f"     Anthropic key configured: {has_anthropic}")
        print(f"     Google key configured: {has_google}")

        if not any([has_openai, has_anthropic, has_google]):
            print(f"  ⚠️  WARNING: No AI API keys configured")
            print(f"     Service will start but AI features won't work")
            print(f"     Add keys to .env file")

        return True, "Config loaded"
    except Exception as e:
        print(f"  ❌ Config failed: {e}")
        traceback.print_exc()
        return False, str(e)


def test_models():
    """Test Pydantic models"""
    print("\n" + "=" * 60)
    print("TESTING: Data Models")
    print("=" * 60)

    try:
        from app.models import (
            Task, TaskPriority, TaskStatus, ModelType,
            HealthStatus, Capabilities, Decision, DecisionCriteria
        )

        # Test creating a task
        task = Task(
            task_id="test-123",
            title="Test Task",
            description="This is a test",
            priority=TaskPriority.HIGH
        )
        print(f"  ✅ Task model works")
        print(f"     Created task: {task.task_id} - {task.title}")

        # Test creating decision criteria
        criteria = DecisionCriteria(
            revenue_impact=0.8,
            risk_level=0.2,
            time_to_value=30,
            resource_requirement=0.5,
            strategic_alignment=0.9
        )
        print(f"  ✅ DecisionCriteria model works")
        print(f"     Revenue impact: {criteria.revenue_impact}")

        return True, "Models validated"
    except Exception as e:
        print(f"  ❌ Models failed: {e}")
        traceback.print_exc()
        return False, str(e)


def test_model_router():
    """Test model router initialization"""
    print("\n" + "=" * 60)
    print("TESTING: Model Router")
    print("=" * 60)

    try:
        from app.model_router import ModelRouter

        router = ModelRouter()
        print(f"  ✅ ModelRouter initialized")

        available = router.available_models()
        print(f"     Available models: {len(available)}")
        for model in available:
            print(f"       - {model.value}")

        if not available:
            print(f"  ⚠️  WARNING: No models available (need API keys)")

        return True, "Router works"
    except Exception as e:
        print(f"  ❌ Router failed: {e}")
        traceback.print_exc()
        return False, str(e)


def test_memory_manager():
    """Test memory manager"""
    print("\n" + "=" * 60)
    print("TESTING: Memory Manager")
    print("=" * 60)

    try:
        from app.memory_manager import MemoryManager

        memory = MemoryManager()
        print(f"  ✅ MemoryManager initialized")

        summary = memory.get_memory_summary()
        print(f"     Memory stores:")
        for key, count in summary.items():
            print(f"       - {key}: {count}")

        return True, "Memory works"
    except Exception as e:
        print(f"  ❌ Memory failed: {e}")
        traceback.print_exc()
        return False, str(e)


def test_decision_engine():
    """Test decision engine"""
    print("\n" + "=" * 60)
    print("TESTING: Decision Engine")
    print("=" * 60)

    try:
        from app.decision_engine import DecisionEngine
        from app.memory_manager import MemoryManager
        from app.models import DecisionCriteria

        memory = MemoryManager()
        engine = DecisionEngine(memory)
        print(f"  ✅ DecisionEngine initialized")

        # Test a simple decision
        criteria = DecisionCriteria(
            revenue_impact=0.8,
            risk_level=0.2,
            time_to_value=30,
            resource_requirement=0.5,
            strategic_alignment=0.9
        )

        decision = engine.make_decision(
            title="Test Decision",
            description="Should we test this?",
            options=["Yes", "No"],
            criteria=criteria
        )

        print(f"     Decision made:")
        print(f"       Recommended: {decision.recommended_option}")
        print(f"       Confidence: {decision.confidence_score:.2f}")
        print(f"       Reasoning: {decision.reasoning[:100]}...")

        return True, "Decision engine works"
    except Exception as e:
        print(f"  ❌ Decision engine failed: {e}")
        traceback.print_exc()
        return False, str(e)


def test_fastapi_app():
    """Test FastAPI app creation"""
    print("\n" + "=" * 60)
    print("TESTING: FastAPI Application")
    print("=" * 60)

    try:
        from app.main import app

        print(f"  ✅ FastAPI app created")
        print(f"     Title: {app.title}")
        print(f"     Version: {app.version}")

        # Check routes
        routes = [route.path for route in app.routes]
        print(f"     Routes: {len(routes)}")

        # Check UBIC endpoints
        ubic_endpoints = ["/health", "/capabilities", "/state", "/dependencies", "/message"]
        for endpoint in ubic_endpoints:
            if endpoint in routes:
                print(f"       ✅ {endpoint}")
            else:
                print(f"       ❌ {endpoint} MISSING")

        return True, "FastAPI app ready"
    except Exception as e:
        print(f"  ❌ FastAPI app failed: {e}")
        traceback.print_exc()
        return False, str(e)


def main():
    """Run all validation tests"""
    print("\n" + "🔍" * 30)
    print("I PROACTIVE VALIDATION SUITE")
    print("🔍" * 30 + "\n")

    tests = [
        ("Module Imports", test_imports),
        ("Configuration", test_config),
        ("Data Models", test_models),
        ("Model Router", test_model_router),
        ("Memory Manager", test_memory_manager),
        ("Decision Engine", test_decision_engine),
        ("FastAPI App", test_fastapi_app),
    ]

    results = []
    for name, test_func in tests:
        try:
            passed, message = test_func()
            results.append((name, passed, message))
        except Exception as e:
            results.append((name, False, str(e)))
            print(f"\n❌ CRITICAL ERROR in {name}: {e}")
            traceback.print_exc()

    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)

    passed_count = sum(1 for _, passed, _ in results if passed)
    total_count = len(results)

    for name, passed, message in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status:10s} {name:30s} - {message}")

    print(f"\n  {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("\n🎉 ALL TESTS PASSED! Service is ready to start.")
        print("\nNext step: Start the service with:")
        print("  uvicorn app.main:app --reload --port 8400")
        return 0
    else:
        print(f"\n⚠️  {total_count - passed_count} tests failed. Fix errors above before starting.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
