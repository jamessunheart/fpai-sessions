"""
Quick test script to verify setup before running the full app.

This checks:
1. All dependencies are installed
2. Environment variables are set
3. API key is valid (optional check)
"""

import sys


def check_dependencies():
    """Check if all required packages are installed."""
    print("🔍 Checking dependencies...")
    
    required_packages = {
        "chainlit": "chainlit",
        "anthropic": "anthropic",
        "python-dotenv": "dotenv"
    }
    
    missing = []
    for package_name, import_name in required_packages.items():
        try:
            __import__(import_name)
            print(f"  ✅ {package_name}")
        except ImportError:
            print(f"  ❌ {package_name} - MISSING")
            missing.append(package_name)
    
    if missing:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    print("✅ All dependencies installed!")
    return True


def check_environment():
    """Check if environment variables are set."""
    print("\n🔍 Checking environment variables...")
    
    try:
        from dotenv import load_dotenv
        import os
        
        load_dotenv()
        
        api_key = os.getenv("ANTHROPIC_API_KEY")
        
        if not api_key:
            print("  ❌ ANTHROPIC_API_KEY not found")
            print("     Create a .env file with: ANTHROPIC_API_KEY=sk-ant-...")
            return False
        
        if not api_key.startswith("sk-ant-"):
            print("  ⚠️  API key format looks incorrect (should start with 'sk-ant-')")
            return False
        
        print("  ✅ ANTHROPIC_API_KEY found")
        print(f"     Key starts with: {api_key[:10]}...")
        return True
        
    except Exception as e:
        print(f"  ❌ Error checking environment: {e}")
        return False


def check_api_connection():
    """Optional: Test if API key works (makes a small API call)."""
    print("\n🔍 Testing API connection (optional)...")
    
    try:
        from anthropic import Anthropic
        from dotenv import load_dotenv
        import os
        
        load_dotenv()
        api_key = os.getenv("ANTHROPIC_API_KEY")
        
        if not api_key:
            print("  ⏭️  Skipping (no API key)")
            return True
        
        client = Anthropic(api_key=api_key)
        
        # Make a minimal test call
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=10,
            messages=[{"role": "user", "content": "Say 'test'"}]
        )
        
        print("  ✅ API connection successful!")
        return True
        
    except Exception as e:
        print(f"  ⚠️  API test failed: {e}")
        print("     This might be okay - API key might be valid but check connection")
        return True  # Don't fail the test, just warn


def main():
    """Run all checks."""
    print("=" * 50)
    print("Voice Interface - Setup Verification")
    print("=" * 50)
    
    all_good = True
    
    # Check dependencies
    if not check_dependencies():
        all_good = False
    
    # Check environment
    if not check_environment():
        all_good = False
    
    # Optional API check
    if all_good:
        check_api_connection()
    
    print("\n" + "=" * 50)
    if all_good:
        print("✅ Setup looks good! Ready to run:")
        print("   chainlit run app.py -w")
    else:
        print("❌ Setup incomplete. Fix the issues above first.")
        sys.exit(1)
    print("=" * 50)


if __name__ == "__main__":
    main()
