# 🚀 BRICK 2: AI Marketing Engine

**The all-in-one, elite marketing automation platform powered by AI.**

## Overview

BRICK 2 is a GHL-centered hybrid marketing automation system that:
- Consolidates 15+ marketing tools into 6 core systems
- Uses GoHighLevel as the central hub
- Integrates premium AI services (Claude, GPT-4, Perplexity, Gemini, Midjourney)
- Provides UBIC v1.5 compliance for BRICK 1 AI orchestration
- Generates measurable revenue from Day 1

## Architecture

```
BRICK 2
├── Module 1: GHL Foundation Hub (4 hours)
├── Module 2: AI Integration Layer (3 hours)
├── Module 3: Lead Generation Engine (3 hours)
├── Module 4: Revenue Attribution (2 hours)
├── Module 5: AI Conversation System (2 hours)
└── Module 6: BRICK 1 Integration (4 hours)
```

## Verticals

### 🇵🇭 BPO Staffing & Referral
First test vertical - Philippine call center/VA staffing with referral commission program.

**Commission Tiers:**
| Rate | Commission |
|:----:|:----------:|
| ≤$8/hr | 5.00% |
| $8.01-$8.49 | 5.50% |
| $8.50-$9.99 | 6.50% |
| $10-$11.99 | 8.00% |
| ≥$12/hr | 10.00% |

## Quick Start

```bash
# Clone and setup
cd SERVICES/brick2-marketing-engine
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run locally
uvicorn app.main:app --reload --port 8700

# Health check
curl http://localhost:8700/health
```

## Project Structure

```
brick2-marketing-engine/
├── SPEC.md                     # Master specification
├── README.md                   # This file
├── app/
│   ├── main.py                 # FastAPI entry point
│   ├── ai/                     # AI integration layer
│   ├── ghl/                    # GoHighLevel hub
│   ├── leads/                  # Lead generation
│   ├── revenue/                # Attribution system
│   ├── chat/                   # AI conversation
│   ├── brick1/                 # BRICK 1 integration
│   └── verticals/
│       └── bpo/                # BPO staffing vertical
│           └── commission.py   # Referral commission calculator
├── tests/
└── verticals/
    └── bpo-staffing-referral/
        └── SPEC.md             # BPO vertical specification
```

## Revenue Targets

| Week | Target | Strategy |
|:----:|:------:|:---------|
| 1 | $5K+ | GHL funnels operational |
| 2 | $10K+ | AI-enhanced outreach |
| 3 | $15K+ | Scaling campaigns |
| 4 | $25K+ | Full system live |

## Integration Points

- **Registry (8000):** Auto-register on startup
- **Orchestrator (8001):** Report campaign status
- **Dashboard (8002):** Display marketing metrics
- **Strategic Intel (8500):** Receive market insights
- **Missions Portal:** fullpotential.ai/missions for human tasks

## Port Assignment

**Port 8700** - BRICK 2 Marketing Engine

## Documentation

- [Master SPEC](./SPEC.md) - Complete technical specification
- [BPO Vertical](./verticals/bpo-staffing-referral/SPEC.md) - Staffing & referral system

## Status

🔵 **Specification Complete** - Ready for implementation

---

*"One marketing engine to rule them all."*

