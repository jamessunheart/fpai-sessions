# Per-Prompt Power Strategy

## The Goal
Maximize what gets accomplished with each prompt to me (Cursor/Claude).

## Current Reality
| Task | Prompts Before | Prompts After |
|------|----------------|---------------|
| Create new droplet | 5-8 | **1** |
| Deploy droplet | 2-3 | **0** (auto) |
| Debug syntax errors | 1-3 | **0** (pre-validated) |
| Verify UDC compliance | 1-2 | **0** (auto-tested) |
| **Total per feature** | **~15** | **~2** |

## Power Multipliers

### 1. Droplet Factory (IMPLEMENTED ✅)
```bash
# Before: Multiple prompts for each file
# After: One prompt describes what you want

# You say: "Create an analytics droplet that tracks usage"
# I generate the spec and run:
./SERVICES/create-droplet.sh analytics 8764 "Usage tracking and metrics"
./SERVICES/deploy-droplet.sh analytics 8764
# Done in 1 prompt
```

### 2. Smart Prompting Patterns

**HIGH POWER prompts:**
```
"Create a droplet called X that does Y"
"Add endpoint /foo to the analytics droplet that calculates Z"
"Find and fix the bug where Aria doesn't respond to SOL status"
```

**LOW POWER prompts (avoid):**
```
"What should we do next?" (too open)
"Can you check if..." (use tools instead)
"Let me know your thoughts" (no action)
```

### 3. Batch Operations
Instead of:
- "Create droplet A" → wait → "Deploy A" → wait → "Create droplet B"

Do:
- "Create and deploy droplets A, B, and C with these specs..."

### 4. Context Preloading
Before complex work, I can read multiple files in parallel:
- Plan file
- Existing code
- Dependencies
- Test files

One prompt with full context > many prompts building context

## Recommended Workflow

### For New Features
```
1. You: Describe what you want in plain English
2. Me: Create spec + all files + deploy + verify
3. You: Test in production or request changes
4. Repeat
```

### For Bug Fixes
```
1. You: "Aria isn't responding to X"
2. Me: Find root cause + fix + deploy + verify
3. You: Confirm fixed
```

### For Architecture Changes
```
1. You: Describe desired end state
2. Me: Create plan with phases
3. You: Approve
4. Me: Execute all phases in sequence
```

## Tools Created

| Script | Purpose |
|--------|---------|
| `create-droplet.sh` | Generate all droplet files from name + port + description |
| `deploy-droplet.sh` | Deploy, validate, start, verify health |
| `verify-new-droplets.sh` | Check UDC compliance of all droplets |
| `test-e2e-new-droplets.sh` | End-to-end functional tests |

## Future Power Upgrades

### CI/CD Pipeline (Recommended Next)
- Push to git → auto-deploy
- Zero deployment prompts needed
- Tests run automatically

### Voice Commands
- "Hey Aria, create a dashboard droplet"
- Aria talks to me, I execute

### Self-Modifying System
- Aria detects need for new capability
- Creates spec, asks for approval
- Builds and deploys itself

## The Bottom Line

**Before:** Building = conversation + coding + debugging + deploying
**After:** Building = describing what you want

Each prompt should CREATE something, not just DISCUSS something.








