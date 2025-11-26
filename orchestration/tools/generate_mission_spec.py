#!/usr/bin/env python3
"""
Mission Spec Generator
======================
Generates complete, actionable mission specs from brief mission descriptions.

Usage:
    python generate_mission_spec.py <mission_id> [--output-dir PATH]
    
This tool:
1. Reads the existing mission brief
2. Analyzes the codebase for relevant files/context
3. Generates a complete spec with step-by-step instructions
4. Saves the spec for review before publishing

The generated spec follows MISSION_SPEC_TEMPLATE.md format.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Setup paths
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parents[1]
MISSIONS_DIR = ROOT_DIR / "fullpotential_ai" / "fullpotential_core" / "orchestration" / "missions"
SPECS_DIR = MISSIONS_DIR / "specs"
TEMPLATE_PATH = MISSIONS_DIR / "MISSION_SPEC_TEMPLATE.md"

# Ensure specs directory exists
SPECS_DIR.mkdir(parents=True, exist_ok=True)


def load_mission_brief(mission_id: str) -> Optional[Dict]:
    """Load existing mission brief from open/ directory"""
    open_dir = MISSIONS_DIR / "open"
    
    # Find mission file
    for f in open_dir.glob(f"{mission_id}*.md"):
        content = f.read_text()
        return parse_mission_brief(content, f.name)
    
    return None


def parse_mission_brief(content: str, filename: str) -> Dict:
    """Parse mission markdown into structured data"""
    mission = {
        "filename": filename,
        "raw_content": content,
        "title": "",
        "priority": "",
        "status": "",
        "owner": "",
        "principle": "",
        "impact": "",
        "objective": "",
        "files": [],
        "dependencies": [],
        "actions": [],
        "notes": []
    }
    
    lines = content.split('\n')
    current_section = None
    
    for line in lines:
        line = line.strip()
        
        # Title
        if line.startswith('# Mission:'):
            mission["title"] = line.replace('# Mission:', '').strip()
            continue
        
        # Metadata fields
        if line.startswith('- **Priority:**'):
            mission["priority"] = line.split(':**')[1].strip()
        elif line.startswith('- **Status:**'):
            mission["status"] = line.split(':**')[1].strip()
        elif line.startswith('- **Owner:**'):
            mission["owner"] = line.split(':**')[1].strip()
        elif line.startswith('- **Constitution Principle:**'):
            mission["principle"] = line.split(':**')[1].strip()
        elif line.startswith('- **Regenerative Impact:**'):
            mission["impact"] = line.split(':**')[1].strip()
        elif line.startswith('- **Objective:**'):
            mission["objective"] = line.split(':**')[1].strip()
        elif line.startswith('- **Files/Systems:**'):
            files_str = line.split(':**')[1].strip()
            mission["files"] = [f.strip().strip('`') for f in files_str.split(',')]
        elif line.startswith('- **Dependencies:**'):
            mission["dependencies"] = line.split(':**')[1].strip()
        
        # Sections
        if line.startswith('## '):
            current_section = line[3:].lower()
            continue
        
        # Collect section content
        if current_section == 'required actions' or current_section == 'deliverables':
            if line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
                mission["actions"].append(line[2:].strip())
        elif current_section == 'notes':
            if line.startswith('-'):
                mission["notes"].append(line[1:].strip())
    
    return mission


def estimate_difficulty(mission: Dict) -> str:
    """Estimate mission difficulty based on content"""
    content = mission.get("raw_content", "").lower()
    
    # Advanced indicators
    if any(word in content for word in ['vault', 'secrets', 'production', 'treasury', 'deploy']):
        return "Advanced"
    
    # Intermediate indicators
    if any(word in content for word in ['api', 'backend', 'database', 'integration']):
        return "Intermediate"
    
    return "Beginner"


def estimate_time(mission: Dict) -> str:
    """Estimate completion time based on actions"""
    num_actions = len(mission.get("actions", []))
    
    if num_actions <= 2:
        return "1-2 hours"
    elif num_actions <= 4:
        return "2-4 hours"
    elif num_actions <= 6:
        return "4-8 hours"
    else:
        return "1-2 days"


def classify_mission_type(mission: Dict) -> str:
    """Classify as AI-Only, Hybrid, or Human-Required"""
    content = mission.get("raw_content", "").lower()
    title = mission.get("title", "").lower()
    
    # Human-required indicators
    if any(word in content for word in ['human', 'manual', 'review', 'approve', 'decision', 'strategy', 'community']):
        return "👤 Human-Required"
    
    # AI-only indicators
    if any(word in content for word in ['automate', 'script', 'deploy', 'fix', 'refactor', 'test']):
        return "🤖 AI-Only"
    
    return "🤝 Hybrid"


def generate_prerequisites(mission: Dict) -> List[str]:
    """Generate prerequisite checklist"""
    prereqs = []
    content = mission.get("raw_content", "").lower()
    
    # Common prereqs
    prereqs.append("Git installed and configured")
    prereqs.append("Access to the FPAI_Cockpit repository")
    
    # Context-specific
    if 'python' in content:
        prereqs.append("Python 3.10+ installed")
    if 'node' in content or 'npm' in content or 'frontend' in content:
        prereqs.append("Node.js 18+ and npm installed")
    if 'docker' in content:
        prereqs.append("Docker installed and running")
    if 'binance' in content or 'trading' in content:
        prereqs.append("Binance testnet account and API keys")
    if 'server' in content or 'deploy' in content:
        prereqs.append("SSH access to deployment server")
    
    # Dependencies
    if mission.get("dependencies"):
        prereqs.append(f"Dependencies completed: {mission['dependencies']}")
    
    return prereqs


def generate_step_instructions(mission: Dict) -> str:
    """Generate detailed step-by-step instructions"""
    actions = mission.get("actions", [])
    files = mission.get("files", [])
    
    if not actions:
        return """### Step 1: Review Requirements
**Goal:** Understand what needs to be done

1. Read through this spec completely
2. Review the related files listed in Resources
3. Ask questions in the help channel if anything is unclear

**Expected Result:** Clear understanding of the mission objectives

### Step 2: Implementation
**Goal:** Complete the core work

[Detailed steps to be filled in by spec reviewer]

### Step 3: Testing
**Goal:** Verify your implementation works

```bash
# Run tests
pytest -v

# Manual verification
# [Add specific verification steps]
```

### Step 4: Submission
**Goal:** Submit for review

1. Commit your changes with a clear message
2. Push to your fork/branch
3. Go to https://fullpotential.ai/services/harvester
4. Submit your repository URL
"""
    
    steps = []
    
    # Setup step
    steps.append("""### Step 1: Setup & Preparation
**Goal:** Prepare your environment

```bash
# Clone/pull latest code
cd /path/to/FPAI_Cockpit
git pull origin main

# Create a working branch
git checkout -b mission-[MISSION_ID]
```

**Expected Result:** Fresh codebase ready for changes
""")
    
    # Generate steps from actions
    for i, action in enumerate(actions, start=2):
        step = f"""### Step {i}: {action[:50]}...
**Goal:** {action}

**Files involved:**
"""
        for f in files:
            step += f"- `{f}`\n"
        
        step += """
**Instructions:**
1. [Detailed sub-step]
2. [Detailed sub-step]
3. [Detailed sub-step]

**Expected Result:** [What success looks like]

**Troubleshooting:**
- If you encounter [problem]: [solution]
"""
        steps.append(step)
    
    # Testing step
    test_step_num = len(actions) + 2
    steps.append(f"""### Step {test_step_num}: Testing & Verification
**Goal:** Ensure everything works correctly

```bash
# Run automated tests
pytest -v

# Check for linting issues
rg -i "TODO|FIXME|XXX" --type py
```

**Success Criteria:**
- [ ] All tests pass
- [ ] No new linting errors
- [ ] Manual verification complete
""")
    
    # Submission step
    step_num = len(actions) + 3
    steps.append(f"""### Step {step_num}: Submission
**Goal:** Submit your work for review

1. Commit all changes:
   ```bash
   git add -A
   git commit -m "Complete mission [MISSION_ID]: [brief description]"
   git push origin mission-[MISSION_ID]
   ```

2. Go to https://fullpotential.ai/services/harvester

3. Fill in:
   - Your name
   - Select this mission
   - Paste your GitHub repo URL
   - Add any notes

4. Click Submit and wait for automated review
""")
    
    return '\n'.join(steps)


def generate_spec(mission: Dict, mission_id: str) -> str:
    """Generate complete mission spec"""
    
    difficulty = estimate_difficulty(mission)
    time_estimate = estimate_time(mission)
    mission_type = classify_mission_type(mission)
    prereqs = generate_prerequisites(mission)
    steps = generate_step_instructions(mission)
    
    # Format prerequisites
    prereqs_md = '\n'.join([f"- [ ] {p}" for p in prereqs])
    
    # Format deliverables from actions
    deliverables = mission.get("actions", ["Implementation complete", "Tests passing", "Documentation updated"])
    deliverables_md = '\n'.join([f"- [ ] {d}" for d in deliverables])
    
    # Format notes
    notes = mission.get("notes", [])
    notes_md = '\n'.join([f"- ⚠️ {n}" for n in notes]) if notes else "- 💡 Ask questions early if anything is unclear"
    
    # Format files
    files = mission.get("files", [])
    files_md = '\n'.join([f"- `{f}`" for f in files]) if files else "- See step-by-step instructions"
    
    spec = f"""# Mission: {mission.get('title', 'Untitled')}

## Overview
- **Priority:** {mission.get('priority', 'P2')}
- **Status:** SPEC_REVIEW
- **Owner:** {mission.get('owner', 'Unassigned')}
- **Estimated Time:** {time_estimate}
- **Difficulty:** {difficulty}
- **Mission Type:** {mission_type}

## Constitution Alignment
- **Principle:** {mission.get('principle', 'Optimization over Extraction')}
- **Regenerative Impact:** {mission.get('impact', 'Contributes to the Full Potential mission')}

## Objective
{mission.get('objective', '[Objective to be defined]')}

## Background & Context
This mission is part of the Full Potential AI ecosystem. Completing it will help advance our goal of building regenerative systems that empower humanity.

{mission.get('raw_content', '').split('## ')[0] if '## ' in mission.get('raw_content', '') else ''}

## Prerequisites
{prereqs_md}

## Step-by-Step Instructions

{steps}

## Deliverables Checklist
{deliverables_md}
- [ ] Code pushed to GitHub
- [ ] Submitted via Harvester
- [ ] Score 80+ on automated review

## Resources
**Related Files:**
{files_md}

**Documentation:**
- [Mission Hub](https://fullpotential.ai/missions)
- [Contribution Guide](https://fullpotential.ai/missions/contribute)
- [Harvester](https://fullpotential.ai/services/harvester)

**Help:**
- Ask questions by creating a GitHub issue
- Check existing mission completions for examples

## Acceptance Criteria
| Criteria | Required | How to Verify |
|----------|----------|---------------|
| Core objective met | ✅ | Manual review |
| Tests pass | ✅ | Automated via Harvester |
| No secrets committed | ✅ | Automated scan |
| Documentation updated | ⚠️ Nice-to-have | Manual review |

## Notes & Warnings
{notes_md}

---
*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*
*Spec Status: DRAFT - Requires human review before publishing*
*Mission ID: {mission_id}*
"""
    
    return spec


def main():
    parser = argparse.ArgumentParser(description="Generate mission specs")
    parser.add_argument("mission_id", help="Mission ID (e.g., M001)")
    parser.add_argument("--output-dir", "-o", default=str(SPECS_DIR), help="Output directory")
    parser.add_argument("--publish", "-p", action="store_true", help="Move to open/ after generation")
    
    args = parser.parse_args()
    
    print(f"🎯 Generating spec for mission: {args.mission_id}")
    
    # Load existing brief
    mission = load_mission_brief(args.mission_id)
    
    if not mission:
        print(f"❌ Mission {args.mission_id} not found in {MISSIONS_DIR / 'open'}")
        sys.exit(1)
    
    print(f"📄 Found mission: {mission.get('title', 'Untitled')}")
    
    # Generate spec
    spec = generate_spec(mission, args.mission_id)
    
    # Save to specs directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"{args.mission_id}_SPEC.md"
    output_file.write_text(spec)
    
    print(f"✅ Spec generated: {output_file}")
    print(f"\n📋 Next steps:")
    print(f"   1. Review the generated spec at: {output_file}")
    print(f"   2. Fill in any [placeholders] with specific details")
    print(f"   3. Have a human review and approve")
    print(f"   4. Move to open/ when ready for contributors")
    
    if args.publish:
        target = MISSIONS_DIR / "open" / f"{args.mission_id}_SPEC.md"
        output_file.rename(target)
        print(f"\n🚀 Published to: {target}")


if __name__ == "__main__":
    main()

