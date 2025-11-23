#!/usr/bin/env python3
"""
Consult Oracle
Aggregates System State (Pulse + Missions) into a Strategic Prompt.
Designed to be run by a human operator (or agent) to get the "Next Best Move".
"""
import json
import os
from pathlib import Path

# --- Configuration ---
ROOT_DIR = Path(__file__).parent.parent.absolute()
PULSE_FILE = ROOT_DIR / "core/STATE/PULSE.json"
MISSIONS_DIR = ROOT_DIR / "missions"
BRAIN_FILE = ROOT_DIR / "core/INTELLIGENCE/BRAIN.md"
OUTPUT_FILE = ROOT_DIR / "core/INTELLIGENCE/SITUATION_REPORT.md"

def load_file(path):
    if not path.exists():
        return "Not found."
    return path.read_text(encoding='utf-8')

def generate_strategic_prompt():
    pulse_data = load_file(PULSE_FILE)
    brain_context = load_file(BRAIN_FILE)
    
    # Summarize Missions
    active_missions = []
    if MISSIONS_DIR.exists():
        for f in MISSIONS_DIR.glob("*.md"):
            if "completed" not in f.read_text(encoding='utf-8').lower():
                active_missions.append(f.name)
    
    prompt = f"""
# YOU ARE THE CEO OF FPAI (Full Potential AI)

## 1. THE SITUATION (DATA)
{pulse_data}

## 2. ACTIVE INITIATIVES (MISSIONS)
{'- ' + chr(10).join(active_missions) if active_missions else "No active missions."}

## 3. STRATEGIC CONTEXT (BRAIN)
{brain_context}

---

## YOUR TASK
Analyze the data above.
1. **Diagnose:** What is the biggest bottleneck RIGHT NOW? (Revenue, Traffic, Product, or Tech?)
2. **Strategize:** What is the single most high-leverage move we can make?
3. **Direct:** Propose a specific MISSION to solve it. Use the format:
   - **Title:** [Actionable Title]
   - **Goal:** [Specific Outcome]
   - **Steps:** [3-5 clear steps]

*Output your response as a clean Markdown Situation Report.*
"""
    return prompt

def main():
    print("🔮 Consulting the Oracle...")
    prompt = generate_strategic_prompt()
    
    print("\n" + "="*40)
    print("COPY THIS PROMPT TO YOUR LLM:")
    print("="*40 + "\n")
    print(prompt)
    print("\n" + "="*40)
    print("Paste the result into: core/INTELLIGENCE/SITUATION_REPORT.md")

if __name__ == "__main__":
    main()

