# Ad Portal Command Center

This is the project management hub for human assistants working on the Ad Portal.

## Purpose

The AI Director (Claude) provides strategic direction and technical specifications. Human assistants execute the tasks listed here. James bridges communication between AI and human assistants.

## How to Use

### 1. View the Dashboard

**Option A - Local viewing:**
```bash
cd SERVICES/ad-portal/command-center
python3 -m http.server 8802
# Open http://localhost:8802
```

**Option B - On server:**
```bash
cd /opt/fpai/services/ad-portal/command-center
python3 serve.py
# Access at http://198.54.123.234:8802
```

### 2. Check Tasks

1. Open `index.html` in browser or view `tasks.json`
2. Work through tasks in order (respect dependencies)
3. Update task status as you complete them

### 3. Report Progress

When a task is complete:
1. Update the status in `tasks.json`
2. Report back to James with:
   - Task ID completed
   - Any issues encountered
   - Credentials obtained (if any)

## Files

| File | Purpose |
|------|---------|
| `index.html` | Interactive task dashboard |
| `tasks.json` | Machine-readable task list |
| `serve.py` | Simple server to host the dashboard |
| `README.md` | This file |

## Current Status

- **Code**: 100% complete
- **Deployment**: Pending
- **Integrations**: Pending (Meta, Stripe)
- **Live Campaigns**: 0

## Contact

Questions about tasks → Ask James → James asks AI Director


