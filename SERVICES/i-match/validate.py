#!/usr/bin/env python3
"""
I MATCH Validation Script
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
        "database": lambda: __import__("app.database"),
        "matching_engine": lambda: __import__("app.matching_engine"),
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
        print(f"     Database: {settings.database_url[:30]}...")
        print(f"     Commission %: {settings.default_commission_percent}%")
        print(f"     Min match score: {settings.minimum_match_score}")

        has_anthropic = bool(settings.anthropic_api_key)
        print(f"     Anthropic key configured: {has_anthropic}")

        if not has_anthropic:
            print(f"  ⚠️  WARNING: No Anthropic API key configured")
            print(f"     Matching engine won't work without it")
            print(f"     Add ANTHROPIC_API_KEY to .env file")

        return True, "Config loaded"
    except Exception as e:
        print(f"  ❌ Config failed: {e}")
        traceback.print_exc()
        return False, str(e)


def test_database_models():
    """Test database models"""
    print("\n" + "=" * 60)
    print("TESTING: Database Models")
    print("=" * 60)

    try:
        from app.database import Customer, Provider, Match, Commission, Base

        print(f"  ✅ Database models imported")
        print(f"     Models available:")
        print(f"       - Customer")
        print(f"       - Provider")
        print(f"       - Match")
        print(f"       - Commission")

        # Test model creation (doesn't save to DB)
        customer_data = {
            "name": "Test Customer",
            "email": "test@example.com",
            "service_type": "financial_advisor",
            "needs_description": "Test needs",
            "preferences": {"budget": "high"},
            "values": {"integrity": 10}
        }

        # Just create instance, don't save
        customer = Customer(**customer_data)
        print(f"  ✅ Customer model works")
        print(f"     Test customer: {customer.name}")

        return True, "Database models validated"
    except Exception as e:
        print(f"  ❌ Database models failed: {e}")
        traceback.print_exc()
        return False, str(e)


def test_database_init():
    """Test database initialization"""
    print("\n" + "=" * 60)
    print("TESTING: Database Initialization")
    print("=" * 60)

    try:
        from app.database import init_db, engine

        # Initialize database (creates tables)
        init_db()
        print(f"  ✅ Database initialized")
        print(f"     Tables created successfully")

        # Check tables exist
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        print(f"     Tables ({len(tables)}):")
        for table in tables:
            print(f"       - {table}")

        expected_tables = ["customers", "providers", "matches", "commissions"]
        missing = set(expected_tables) - set(tables)

        if missing:
            print(f"  ⚠️  Missing tables: {missing}")
            return False, f"Missing tables: {missing}"

        return True, "Database ready"
    except Exception as e:
        print(f"  ❌ Database init failed: {e}")
        traceback.print_exc()
        return False, str(e)


def test_matching_engine():
    """Test matching engine"""
    print("\n" + "=" * 60)
    print("TESTING: Matching Engine")
    print("=" * 60)

    try:
        from app.matching_engine import MatchingEngine

        engine = MatchingEngine()
        print(f"  ✅ MatchingEngine initialized")

        # Test commission calculation
        commission = engine.calculate_commission(50000, 20.0)
        print(f"     Commission calc works:")
        print(f"       $50,000 deal @ 20% = ${commission:,.0f}")

        # Test match quality labels
        scores = [95, 85, 75, 65, 55]
        print(f"     Match quality labels:")
        for score in scores:
            label = engine.get_match_quality_label(score)
            print(f"       {score}/100 = {label}")

        has_client = bool(engine.client)
        print(f"     Claude API client: {'✅ Ready' if has_client else '❌ Not configured'}")

        if not has_client:
            print(f"  ⚠️  WARNING: Claude API not available")
            print(f"     Add ANTHROPIC_API_KEY to .env to enable AI matching")

        return True, "Matching engine works"
    except Exception as e:
        print(f"  ❌ Matching engine failed: {e}")
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
        print(f"     UBIC endpoints:")
        for endpoint in ubic_endpoints:
            if endpoint in routes:
                print(f"       ✅ {endpoint}")
            else:
                print(f"       ❌ {endpoint} MISSING")

        # Check key business endpoints
        business_endpoints = [
            "/customers/create",
            "/providers/create",
            "/matches/find",
            "/matches/create",
            "/commissions/list"
        ]
        print(f"     Business endpoints:")
        for endpoint in business_endpoints:
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
    print("I MATCH VALIDATION SUITE")
    print("🔍" * 30 + "\n")

    tests = [
        ("Module Imports", test_imports),
        ("Configuration", test_config),
        ("Database Models", test_database_models),
        ("Database Init", test_database_init),
        ("Matching Engine", test_matching_engine),
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
        print("  uvicorn app.main:app --reload --port 8401")
        print("\nOr test commission calculation:")
        print("  Deal: $50,000 @ 20% = $10,000 commission")
        return 0
    else:
        print(f"\n⚠️  {total_count - passed_count} tests failed. Fix errors above before starting.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
