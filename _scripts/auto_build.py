#!/usr/bin/env python3
"""
Autonomous Builder
The "Hands" of the AI.
Executes [AUTO-CANDIDATE] missions using LLM intelligence.
"""
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# --- Configuration ---
ROOT_DIR = Path(__file__).parent.parent.absolute()
MISSIONS_DIR = ROOT_DIR / "missions"
ENV_PATH = ROOT_DIR / "_scripts/.env"

load_dotenv(ENV_PATH)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODE = os.getenv("BUILDER_MODE", "mock")

def get_client():
    """Initialize the AI Client."""
    if ANTHROPIC_API_KEY:
        from anthropic import Anthropic
        return Anthropic(api_key=ANTHROPIC_API_KEY), "anthropic"
    elif OPENAI_API_KEY:
        from openai import OpenAI
        return OpenAI(api_key=OPENAI_API_KEY), "openai"
    return None, None

def find_next_job():
    """Finds the highest priority [AUTO-CANDIDATE] mission."""
    if not MISSIONS_DIR.exists():
        return None
        
    for file in MISSIONS_DIR.glob("*.md"):
        content = file.read_text(encoding='utf-8')
        if "[AUTO-CANDIDATE]" in content:
            return file
    return None

def generate_plan(client, client_type, mission_text):
    """Asks the LLM to generate a JSON plan."""
    
    system_prompt = """You are an Autonomous DevOps Agent.
    Your goal is to execute the given Mission Spec.
    
    Output a JSON object with this structure:
    {
      "reasoning": "Analysis of what needs to be done...",
      "files_to_create": [
        {"path": "relative/path.ts", "content": "code content..."}
      ],
      "commands_to_run": [
        "npm install package",
        "python3 script.py"
      ]
    }
    
    CONSTRAINTS:
    - Only edit files within the project root.
    - Do not use sudo.
    - Prefer creating new files over complex regex edits.
    """
    
    if client_type == "anthropic":
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4000,
            system=system_prompt,
            messages=[{"role": "user", "content": f"MISSION SPEC:\n{mission_text}"}]
        )
        return json.loads(message.content[0].text)
        
    elif client_type == "openai":
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"MISSION SPEC:\n{mission_text}"}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)

    return None

def execute_plan(plan):
    """Executes the JSON plan."""
    print(f"📝 Reasoning: {plan.get('reasoning')}")
    
    # 1. File Operations
    for file in plan.get("files_to_create", []):
        path = ROOT_DIR / file["path"]
        print(f"📄 Writing: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(file["content"], encoding='utf-8')
        
    # 2. Commands (Stubbed for Safety in v1)
    for cmd in plan.get("commands_to_run", []):
        print(f"⚠️  Skipping Command (Safety Mode): {cmd}")
        # subprocess.run(cmd, shell=True, cwd=ROOT_DIR)

def execute_mission(mission_file):
    print(f"🏗️  Starting Build: {mission_file.name}")
    
    client, client_type = get_client()
    if not client and MODE == "live":
        print("❌ No API Keys found. Cannot build.")
        return

    # 1. Read Spec
    content = mission_file.read_text(encoding='utf-8')
    
    # 2. Generate Plan
    if MODE == "mock":
        print("🎭 Mock Mode: Simulating build...")
        plan = {
            "reasoning": "Mock build. Would create files.",
            "files_to_create": [],
            "commands_to_run": []
        }
    else:
        print(f"🧠 Consulting {client_type}...")
        try:
            plan = generate_plan(client, client_type, content)
        except Exception as e:
            print(f"❌ LLM Error: {e}")
            return

    # 3. Execute
    execute_plan(plan)
    
    # 4. Update Status
    new_content = content.replace("[AUTO-CANDIDATE]", "[VERIFYING]")
    mission_file.write_text(new_content, encoding='utf-8')
    print("✅ Build Complete. Status -> [VERIFYING]")

def main():
    print("🦾 Auto-Builder Initializing...")
    print(f"🔧 Mode: {MODE}")
    
    job = find_next_job()
    if job:
        execute_mission(job)
    else:
        print("💤 No auto-safe missions in queue.")

if __name__ == "__main__":
    main()
