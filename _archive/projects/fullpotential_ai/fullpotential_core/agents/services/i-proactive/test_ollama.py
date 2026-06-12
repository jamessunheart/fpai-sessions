#!/usr/bin/env python3
"""Test Ollama integration with I PROACTIVE"""

import asyncio
import sys
sys.path.insert(0, '.')

from app.model_router import ModelRouter
from app.models import Task, TaskPriority, ModelType


async def test_ollama():
    """Test that Ollama (Llama 3.1) works"""
    router = ModelRouter()

    print(f"\n=== Available Models ===")
    models = router.available_models()
    for model in models:
        print(f"  - {model}")

    print(f"\n=== Testing Ollama Integration ===")

    # Create a simple test task
    task = Task(
        task_id="test-sovereignty-1",
        title="Test Sovereign AI",
        description="What is 2+2? Answer with just the number, nothing else.",
        priority=TaskPriority.HIGH,
        preferred_model=ModelType.AUTO  # Let it auto-select
    )

    # The router should select Llama since we configured ollama_endpoint
    selected_model = router.select_model(task)
    print(f"\nAuto-selected model: {selected_model}")
    print(f"Expected: {ModelType.LLAMA_3_1_8B}")

    if selected_model == ModelType.LLAMA_3_1_8B:
        print("✅ SOVEREIGNTY ACTIVE - Using local Llama!")
    else:
        print("❌ WARNING - Still using corporate API")

    # Execute the task
    print(f"\nExecuting task with {selected_model}...")
    try:
        result = await router.execute_task(task)

        print(f"\n=== Results ===")
        print(f"Model used: {result['model_used']}")
        print(f"Cost: ${result['cost_usd']}")
        print(f"Response: {result['result']}")

        if result['cost_usd'] == 0.0:
            print("\n🎉 SUCCESS! Sovereign AI working - $0 cost!")
        else:
            print(f"\n⚠️  Still costing money: ${result['cost_usd']}")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_ollama())
