#!/usr/bin/env python3
"""
🏗️ THE ARCHITECT - Spec Generator
Transforms simple ideas into ready-to-code missions with full technical specifications.
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# Using older reliable model name for compatibility
CLAUDE_MODEL = "claude-2.1"
OPENAI_MODEL = "gpt-4o"
WORKSPACE_ROOT = Path(__file__).parent.parent.parent
MISSIONS_DIR = WORKSPACE_ROOT / "orchestration" / "missions" / "open"
TECH_STACK_PATH = WORKSPACE_ROOT / "docs" / "architecture" / "foundation" / "TECH_STACK.md"
UDC_COMPLIANCE_PATH = WORKSPACE_ROOT / "docs" / "architecture" / "foundation" / "UDC_COMPLIANCE.md"

# Determine which LLM provider to use
USE_CLAUDE = ANTHROPIC_API_KEY is not None
USE_OPENAI = OPENAI_API_KEY is not None

if not USE_CLAUDE and not USE_OPENAI:
    print("❌ Error: No AI API key found!")
    print("   Please set either:")
    print("   - ANTHROPIC_API_KEY (for Claude)")
    print("   - OPENAI_API_KEY (for GPT-4)")
    print()
    print("   Example:")
    print("   export ANTHROPIC_API_KEY='sk-ant-...'")
    sys.exit(1)


def load_reference_docs():
    """Load the tech stack and UDC compliance documents for context."""
    tech_stack = ""
    udc_compliance = ""
    
    try:
        if TECH_STACK_PATH.exists():
            with open(TECH_STACK_PATH, 'r') as f:
                tech_stack = f.read()
    except Exception as e:
        print(f"⚠️ Warning: Could not load TECH_STACK.md: {e}")
    
    try:
        if UDC_COMPLIANCE_PATH.exists():
            with open(UDC_COMPLIANCE_PATH, 'r') as f:
                udc_compliance = f.read()
    except Exception as e:
        print(f"⚠️ Warning: Could not load UDC_COMPLIANCE.md: {e}")
    
    return tech_stack, udc_compliance


def get_next_mission_id():
    """Find the next available mission ID."""
    if not MISSIONS_DIR.exists():
        return 1
    
    existing_missions = list(MISSIONS_DIR.glob("M*.md"))
    if not existing_missions:
        return 1
    
    # Extract IDs from filenames like M001_title.md
    ids = []
    for mission in existing_missions:
        try:
            id_str = mission.stem.split('_')[0][1:]  # Remove 'M' prefix
            ids.append(int(id_str))
        except (ValueError, IndexError):
            continue
    
    return max(ids) + 1 if ids else 1


def generate_spec_with_llm(idea: str, tech_stack: str, udc_compliance: str):
    """Use Claude or OpenAI to generate a comprehensive technical specification."""
    
    prompt = f"""You are the Architect AI for Full Potential AI. Your job is to transform a simple idea into a comprehensive, ready-to-code technical specification.

**THE IDEA:**
{idea}

**YOUR TECHNICAL CONTEXT:**

Below are the standards you must follow:

---
TECH STACK STANDARDS:
{tech_stack}
---

---
UDC COMPLIANCE REQUIREMENTS:
{udc_compliance}
---

**YOUR TASK:**

Generate a complete technical specification that includes:

1. **📋 OVERVIEW**
   - Clear description of what this feature/service does
   - Business value and user impact
   - Expected timeline and complexity estimate

2. **🎯 REQUIREMENTS**
   - Functional requirements (what it must do)
   - Non-functional requirements (performance, security, etc.)
   - Success criteria (how we know it's done)

3. **🏗️ ARCHITECTURE**
   - System components needed
   - Data flow diagram (describe in text)
   - Integration points with existing services
   - Database schema (if applicable)

4. **🔌 API SPECIFICATION**
   - All endpoints with HTTP methods
   - Request/response schemas (JSON examples)
   - Authentication requirements
   - Error handling

5. **💾 DATABASE DESIGN**
   - Table schemas with fields and types
   - Relationships and foreign keys
   - Indexes for performance
   - (Use PostgreSQL as per tech stack)

6. **🎨 UI/UX REQUIREMENTS**
   - User interface components needed
   - User flows and interactions
   - Responsive design considerations
   - (If this is a frontend feature)

7. **🔐 SECURITY CONSIDERATIONS**
   - Authentication/authorization approach
   - Data validation requirements
   - Sensitive data handling
   - Rate limiting if applicable

8. **✅ TESTING STRATEGY**
   - Unit test requirements
   - Integration test scenarios
   - End-to-end test cases
   - Performance benchmarks

9. **📦 DEPLOYMENT PLAN**
   - Environment variables needed
   - Docker configuration
   - Dependencies to install
   - Migration steps (if database changes)

10. **🛠️ BUILDER INSTRUCTIONS**
    - Step-by-step setup guide
    - How to use the starter kit
    - Where to find foundation files
    - How to test locally
    - Submission process

**IMPORTANT GUIDELINES:**
- Follow the TECH_STACK.md standards strictly (FastAPI, PostgreSQL, etc.)
- Implement UDC compliance if this is a new droplet/service
- Be specific with code examples where helpful
- Make this detailed enough that ANY developer can implement it
- Think through edge cases and error scenarios
- Provide realistic estimates for complexity and time

**CONSTITUTIONAL REQUIREMENT (MANDATORY):**
At the very top of your specification, after the title, you MUST include these three fields:

- **Priority:** Choose P0 (Critical/Urgent), P1 (High/Core), P2 (Strategic), or P3 (Stretch)
- **Constitution Principle:** Choose ONE that this mission best serves:
  - "Optimization over Extraction" (creates net-new resources/efficiency)
  - "Autonomy over Dependency" (liberates operators from manual work)
  - "Consciousness over Computation" (expands awareness/alignment)
- **Regenerative Impact:** Write 1-2 sentences explaining how this mission increases abundance, autonomy, or awareness (not just throughput). Think about long-term value creation.

**EXAMPLE:**
- **Priority:** P1
- **Constitution Principle:** **Autonomy over Dependency**
- **Regenerative Impact:** Automated mission feed sync eliminates manual coordination bottlenecks, freeing operators to focus on strategic work instead of toil.

**OUTPUT FORMAT:**
Return ONLY the markdown content for the specification. No preamble, no "here is the spec", just the raw markdown starting with the title.

Begin the spec with:
# [Feature/Service Name]

Then immediately add the three MANDATORY fields above, then proceed with all sections.
"""

    if USE_CLAUDE:
        # Use Claude (Anthropic)
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        
        # Fallback logic for models
        models_to_try = [
            "claude-3-5-haiku-20241022",
            "claude-3-haiku-20240307"
        ]
        
        last_error = None
        for model in models_to_try:
            try:
                print(f"   Attempting with model: {model}")
                message = client.messages.create(
                    model=model,
                    max_tokens=4000, # Reduced from 8000 for older models
                    temperature=0.7,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                return message.content[0].text
            except Exception as e:
                print(f"   ⚠️  Failed with {model}: {str(e)}")
                last_error = e
                continue
        
        # If we get here, all models failed
        raise last_error
    
    elif USE_OPENAI:
        # Use OpenAI
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are the Architect AI for Full Potential AI. You transform simple ideas into comprehensive, ready-to-code technical specifications."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=4000,
            temperature=0.7
        )
        return response.choices[0].message.content
    
    else:
        raise ValueError("No AI provider configured")


def generate_mission_file(idea: str, spec: str, mission_id: int):
    """Wrap the spec in a mission template with builder instructions."""
    
    # Generate a slug from the idea
    slug = idea.lower()
    slug = ''.join(c if c.isalnum() or c.isspace() else '' for c in slug)
    slug = '_'.join(slug.split()[:5])  # First 5 words max
    
    mission_content = f"""# 🎯 MISSION M{mission_id:03d}: {idea}

**Status:** 🟡 OPEN  
**Created:** {datetime.now().strftime("%Y-%m-%d")}  
**Estimated Time:** TBD (see spec below)  
**Difficulty:** TBD (see spec below)

---

## 🚀 QUICK START FOR BUILDERS

**This is a ready-to-code mission.** Everything you need is in this file.

### 📦 STARTER KIT

Before you start coding, set up your foundation:

1. **Create a New Repository**
   ```bash
   mkdir mission-m{mission_id:03d}
   cd mission-m{mission_id:03d}
   git init
   ```

2. **Copy Foundation Files**
   
   You'll need these files from the Full Potential AI codebase:
   
   - `TECH_STACK.md` - Technology standards to follow
   - `UDC_COMPLIANCE.md` - Required endpoints (if building a service)
   - `.env.example` - Environment variable template
   
   Copy them from: `https://github.com/fullpotentialai/fpai-cockpit/tree/main/docs/architecture/foundation`

3. **Set Up Your Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   pip install -r requirements.txt
   ```

4. **Build According to Spec**
   
   Follow the detailed specification below. It includes:
   - Complete architecture
   - API endpoints
   - Database schemas
   - Testing requirements
   - Everything you need!

5. **Test Locally**
   ```bash
   # Run tests
   pytest tests/ -v
   
   # Start the service (if applicable)
   uvicorn app.main:app --reload
   
   # Test the endpoints
   curl http://localhost:8000/health
   ```

6. **Submit Your Work**
   
   When complete:
   - Push your code to GitHub (or your preferred platform)
   - Test that all requirements are met
   - Submit your repo URL: https://fullpotential.ai/feedback
   - Include: Your name, Mission ID (M{mission_id:03d}), and any notes

---

## 📝 TECHNICAL SPECIFICATION

{spec}

---

## 💬 GETTING HELP

**Stuck?** Don't struggle alone!

- **Ask Questions:** https://fullpotential.ai/feedback
- **Report Issues:** Same form, tell us what's blocking you
- **Suggest Improvements:** If the spec is unclear, let us know

**Your feedback makes the system better for everyone.**

---

## ✅ COMPLETION CHECKLIST

Before submitting, verify:

- [ ] All requirements implemented
- [ ] Tests passing (>80% coverage)
- [ ] Code follows TECH_STACK.md standards
- [ ] UDC endpoints implemented (if applicable)
- [ ] README.md with setup instructions
- [ ] Environment variables documented
- [ ] Local testing successful
- [ ] Code committed to repository

---

## 🎓 WHAT YOU'LL LEARN

By completing this mission:
- Modern Python backend development (FastAPI)
- Database design and ORMs (PostgreSQL + SQLAlchemy)
- API design and documentation
- Testing and quality assurance
- Docker containerization
- Professional development workflows

---

**Original Idea:** "{idea}"  
**Mission ID:** M{mission_id:03d}  
**Generated:** {datetime.now().isoformat()}

🚀 **Let's build something awesome!**
"""
    
    return mission_content, slug


def save_mission(content: str, mission_id: int, slug: str):
    """Save the mission file to the missions directory."""
    filename = f"M{mission_id:03d}_{slug}.md"
    filepath = MISSIONS_DIR / filename
    
    # Ensure directory exists
    MISSIONS_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    return filepath


def main():
    """Main execution function."""
    if len(sys.argv) < 2:
        print("Usage: python generate_spec.py \"Your idea here\"")
        print("\nExample:")
        print('  python generate_spec.py "Build a referral system"')
        sys.exit(1)
    
    idea = sys.argv[1]
    
    print("🏗️  THE ARCHITECT - Spec Generator")
    print("=" * 60)
    print(f"📝 Idea: {idea}")
    print()
    
    # Load reference documents
    print("📚 Loading reference documents...")
    tech_stack, udc_compliance = load_reference_docs()
    print(f"   ✓ TECH_STACK.md: {len(tech_stack)} chars")
    print(f"   ✓ UDC_COMPLIANCE.md: {len(udc_compliance)} chars")
    print()
    
    # Generate spec using LLM
    provider = "Claude" if USE_CLAUDE else "GPT-4"
    print(f"🤖 Consulting the Mind ({provider})...")
    try:
        spec = generate_spec_with_llm(idea, tech_stack, udc_compliance)
        print(f"   ✓ Generated specification: {len(spec)} chars")
    except Exception as e:
        print(f"   ✗ Error generating spec: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    print()
    
    # Get next mission ID
    mission_id = get_next_mission_id()
    print(f"🎯 Mission ID: M{mission_id:03d}")
    print()
    
    # Generate mission file
    print("📄 Generating mission file...")
    mission_content, slug = generate_mission_file(idea, spec, mission_id)
    print(f"   ✓ Mission template created")
    print()
    
    # Save mission
    print("💾 Saving mission...")
    filepath = save_mission(mission_content, mission_id, slug)
    print(f"   ✓ Saved to: {filepath}")
    print()
    
    # Auto-regenerate mission feed
    print("🔄 Updating mission feed...")
    feed_generator = WORKSPACE_ROOT / "fullpotential_ai/fullpotential_core/orchestration/tools/generate_mission_feed.py"
    if feed_generator.exists():
        try:
            import subprocess
            result = subprocess.run([sys.executable, str(feed_generator)], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print("   ✓ Mission feed updated - mission will appear on dashboard")
            else:
                print(f"   ⚠️  Feed update had issues: {result.stderr[:200]}")
        except Exception as e:
            print(f"   ⚠️  Could not auto-update feed: {e}")
            print(f"   Run manually: python3 {feed_generator}")
    else:
        print("   ⚠️  Feed generator not found at expected location")
        print("   Mission will need manual sync to appear on dashboard")
    print()
    
    # Summary
    print("=" * 60)
    print("✅ MISSION GENERATED SUCCESSFULLY!")
    print()
    print(f"📍 Location: {filepath}")
    print(f"🆔 Mission ID: M{mission_id:03d}")
    print(f"📝 Title: {idea}")
    print()
    print("Next steps:")
    print("1. Review the mission file")
    print("2. Check the mission board: https://fullpotential.ai/missions (should appear within 5 min)")
    print("3. Share with builders")
    print()
    print("🚀 Ready to build!")


if __name__ == "__main__":
    main()
