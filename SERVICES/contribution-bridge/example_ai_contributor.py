"""
Example: AI Agent submitting a contribution to the Bridge
This shows how another AI can discover and contribute to the 2X system
"""
import requests
import base64
import json

class AIContributor:
    """AI agent that can submit code to Contribution Bridge"""

    def __init__(self, bridge_url="http://localhost:8053"):
        self.bridge_url = bridge_url
        self.contributor_id = None
        self.api_key = None

    def discover_bridge(self):
        """Step 1: Discover the bridge system"""
        response = requests.get(f"{self.bridge_url}/api/contribution-bridge/info")
        info = response.json()

        print("🔍 Bridge Discovery:")
        print(f"   Name: {info['name']}")
        print(f"   Accepts: {', '.join(info['accepts'])}")
        print(f"   Rewards Paid: ${info['rewards_paid_usd']}")
        print(f"   Security Layers: {info['security_layers']}")
        print()

        return info

    def register(self, name, contact, ai_version="v1.0"):
        """Step 2: Register as a contributor"""
        response = requests.post(
            f"{self.bridge_url}/api/contribution-bridge/register",
            json={
                "name": name,
                "contact": contact,
                "is_ai": True,
                "ai_version": ai_version
            }
        )

        data = response.json()

        if data["success"]:
            self.contributor_id = data["contributor_id"]
            self.api_key = data["api_key"]

            print("✅ Registration Successful:")
            print(f"   Contributor ID: {self.contributor_id}")
            print(f"   API Key: {self.api_key}")
            print()

        return data

    def analyze_system(self):
        """Step 3: AI analyzes the system for improvements"""

        print("🤖 AI Analysis Running...")
        print("   Scanning 2X Treasury codebase...")
        print("   Identifying optimization opportunities...")
        print()

        # Simulated AI analysis
        improvement = {
            "type": "performance",
            "title": "Add Redis caching to Treasury API",
            "description": "Reduces API response time by 20% through intelligent caching of frequently accessed data",
            "expected_impact": "20% faster API responses",
            "expected_reward": 100.0
        }

        print(f"💡 Improvement Identified:")
        print(f"   Type: {improvement['type']}")
        print(f"   Title: {improvement['title']}")
        print(f"   Impact: {improvement['expected_impact']}")
        print()

        return improvement

    def write_code(self, improvement):
        """Step 4: AI writes the code"""

        print("✍️  AI Writing Code...")

        # Example: Redis caching implementation
        code = '''"""
Redis caching layer for 2X Treasury API
Improves performance by caching frequently accessed data
"""
import redis
from functools import wraps
import json

# Redis connection
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

def cache_result(ttl=300):
    """Decorator to cache API results"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"

            # Check cache
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)

            # Execute function
            result = await func(*args, **kwargs)

            # Store in cache
            redis_client.setex(cache_key, ttl, json.dumps(result))

            return result
        return wrapper
    return decorator

# Usage example:
# @cache_result(ttl=60)
# async def get_treasury_state():
#     return treasury_state
'''

        # Example tests
        tests = '''"""
Tests for Redis caching layer
"""
import pytest
from caching import cache_result

@pytest.mark.asyncio
async def test_cache_stores_result():
    """Test that results are cached"""
    call_count = 0

    @cache_result(ttl=5)
    async def test_func():
        nonlocal call_count
        call_count += 1
        return {"value": 42}

    # First call - should execute
    result1 = await test_func()
    assert result1["value"] == 42
    assert call_count == 1

    # Second call - should use cache
    result2 = await test_func()
    assert result2["value"] == 42
    assert call_count == 1  # Not incremented

@pytest.mark.asyncio
async def test_cache_expires():
    """Test that cache expires after TTL"""
    import time

    @cache_result(ttl=1)
    async def test_func():
        return {"timestamp": time.time()}

    result1 = await test_func()
    time.sleep(2)
    result2 = await test_func()

    # Results should be different after cache expires
    assert result1["timestamp"] != result2["timestamp"]
'''

        print("✅ Code Written:")
        print(f"   Lines: {len(code.split(chr(10)))}")
        print(f"   Tests: {len(tests.split(chr(10)))}")
        print()

        return code, tests

    def submit_contribution(self, improvement, code, tests):
        """Step 5: Submit to Bridge"""

        print("📤 Submitting to Bridge...")

        # Encode code
        code_b64 = base64.b64encode(code.encode()).decode()
        tests_b64 = base64.b64encode(tests.encode()).decode()

        response = requests.post(
            f"{self.bridge_url}/api/contribution-bridge/submit",
            json={
                "contributor_id": self.contributor_id,
                "contribution_type": improvement["type"],
                "title": improvement["title"],
                "description": improvement["description"],
                "code": code_b64,
                "tests": tests_b64,
                "expected_reward": improvement["expected_reward"]
            }
        )

        data = response.json()

        print("📥 Submission Response:")
        print(f"   Submission ID: {data['submission_id']}")
        print(f"   Status: {data['status']}")
        print(f"   Security Scan: {'✅ PASS' if data['security_scan']['passed'] else '❌ FAIL'}")
        print(f"   Dependencies: {'✅ PASS' if data['dependency_check']['passed'] else '❌ FAIL'}")
        print(f"   Next Steps: {data['next_steps']}")
        print()

        return data

    def check_status(self, submission_id):
        """Step 6: Check submission status"""

        response = requests.get(
            f"{self.bridge_url}/api/contribution-bridge/submission/{submission_id}"
        )

        data = response.json()
        submission = data["submission"]

        print("📊 Submission Status:")
        print(f"   Status: {submission['status']}")

        if submission.get("review"):
            print(f"   Review: {submission['review']['reason']}")

            if submission['review']['approved']:
                print(f"   💰 Reward: ${submission.get('reward_paid', 0)}")
                print("   ✅ Code deployed to production!")

        print()

        return submission

    def full_workflow_example(self):
        """Complete AI-to-AI collaboration workflow"""

        print("=" * 60)
        print("🤖 AI CONTRIBUTOR - FULL WORKFLOW DEMO")
        print("=" * 60)
        print()

        # Step 1: Discover
        info = self.discover_bridge()

        # Step 2: Register
        self.register(
            name="AI_CodeBot_v1",
            contact="codebot@ai.example.com",
            ai_version="1.0.0"
        )

        # Step 3: Analyze system
        improvement = self.analyze_system()

        # Step 4: Write code
        code, tests = self.write_code(improvement)

        # Step 5: Submit
        submission = self.submit_contribution(improvement, code, tests)

        print("=" * 60)
        print("✅ WORKFLOW COMPLETE")
        print("=" * 60)
        print()
        print("What happens next:")
        print("1. Human reviews submission in dashboard")
        print("2. If approved → Code deployed + Reward sent")
        print("3. If rejected → AI learns and tries again")
        print()
        print(f"Submission ID: {submission['submission_id']}")
        print("Track at: http://localhost:8053")
        print()

        return submission


if __name__ == "__main__":
    # Example usage
    ai = AIContributor(bridge_url="http://localhost:8053")

    # Run full workflow
    ai.full_workflow_example()

    # Later, AI can check status:
    # status = ai.check_status(submission_id)
