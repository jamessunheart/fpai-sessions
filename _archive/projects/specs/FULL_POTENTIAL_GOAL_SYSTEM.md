# FULL POTENTIAL GOAL SYSTEM (FPGS)
## The Human-First AI Alignment Architecture

**Version:** 1.0.0  
**Status:** SPEC DRAFT  
**Created:** 2026-01-17  
**Author:** James + AI Collaboration

---

## 🌟 THE VISION

### One Sentence
**Full Potential is a goal realization system that aligns AI with human goals while gently optimizing those goals toward the greater good of all.**

### The Core Insight
Traditional AI alignment tries to program "good behavior" into AI. We flip this:
- **AI serves human-defined goals** (maintains human agency)
- **AI offers wisdom** (suggests optimizations, not mandates)  
- **User always chooses** (no paternalistic override)
- **Goals naturally evolve** toward planetary health through gentle guidance

### The Tagline
> "Full Potential isn't just YOUR full potential — it's the full potential of YOU within the whole."

---

## 🏗️ SYSTEM ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FULL POTENTIAL GOAL SYSTEM                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌────────────┐  │
│  │   INTAKE    │───▶│   ALIGNMENT  │───▶│   ROUTING   │───▶│  JOURNEY   │  │
│  │    FLOW     │    │    ENGINE    │    │   SYSTEM    │    │   SYSTEM   │  │
│  └─────────────┘    └──────────────┘    └─────────────┘    └────────────┘  │
│         │                  │                  │                  │          │
│         ▼                  ▼                  ▼                  ▼          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         GOAL LIBRARY                                 │   │
│  │                    (The Collective Intelligence)                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                  │                  │                  │          │
│         ▼                  ▼                  ▼                  ▼          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      FEEDBACK & LEARNING                             │   │
│  │              (What works, what doesn't, evolve the system)           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📚 COMPONENT 1: THE GOAL LIBRARY

### Purpose
A structured, evolving database of human goals — from specific targets to life aspirations. Becomes smarter as more humans use it.

### Goal Categories (Top Level)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           GOAL CATEGORIES                                   │
├──────────────┬──────────────┬──────────────┬──────────────┬────────────────┤
│  💰 WEALTH   │  ❤️ HEALTH   │  😊 HAPPINESS │  🎯 PURPOSE  │  🤝 CONNECTION │
├──────────────┼──────────────┼──────────────┼──────────────┼────────────────┤
│ Income       │ Physical     │ Emotional    │ Career       │ Relationships  │
│ Savings      │ Mental       │ Fulfillment  │ Impact       │ Community      │
│ Debt Freedom │ Energy       │ Peace        │ Legacy       │ Belonging      │
│ Investment   │ Longevity    │ Joy          │ Calling      │ Intimacy       │
│ Passive Inc  │ Fitness      │ Gratitude    │ Contribution │ Family         │
│ Business     │ Nutrition    │ Presence     │ Growth       │ Friendship     │
└──────────────┴──────────────┴──────────────┴──────────────┴────────────────┘
```

### Goal Data Structure

```json
{
  "goal_id": "string (unique)",
  "version": "1.0.0",
  
  "display": {
    "name": "Earn $10,000/month",
    "description": "Consistent monthly income of $10K or more",
    "icon": "💰",
    "category": "wealth/income",
    "subcategory": "monthly_income",
    "difficulty": "moderate",
    "typical_duration": "6-18 months"
  },
  
  "parameters": {
    "target_value": {
      "type": "currency",
      "default": 10000,
      "min": 1000,
      "max": 1000000,
      "customizable": true
    },
    "timeline": {
      "type": "duration",
      "default": "12 months",
      "customizable": true
    }
  },
  
  "alignment": {
    "planetary_impact": "neutral|positive|negative|depends",
    "collective_impact": "neutral|positive|negative|depends",
    "sustainability_score": 0.8,
    "integrity_questions": [
      "What will change in your life at this income level?",
      "What are you willing to give in exchange for this?",
      "Who else benefits when you achieve this?",
      "What would you do with the extra income?"
    ],
    "red_flags": [
      "mentions 'at any cost'",
      "exploitation-based methods",
      "get-rich-quick expectations"
    ],
    "alignment_suggestions": [
      {
        "trigger": "expense_reduction_viable",
        "suggest_goal": "wealth_financial_freedom",
        "message": "I notice you could reach financial freedom faster by combining income growth with expense optimization. Interested?"
      },
      {
        "trigger": "mentions_extraction",
        "suggest_goal": "wealth_10k_value_creation",
        "message": "What if you could reach $10K/month by creating value people genuinely want? Often more sustainable and fulfilling."
      }
    ]
  },
  
  "journey": {
    "phases": [
      {
        "name": "Foundation",
        "description": "Assess current state, identify leverage points",
        "typical_duration": "2-4 weeks",
        "milestones": ["income_audit_complete", "skill_inventory_done", "market_research_started"]
      },
      {
        "name": "Build",
        "description": "Develop income streams, build skills",
        "typical_duration": "2-6 months",
        "milestones": ["first_new_income", "skill_improvement_measurable", "systems_in_place"]
      },
      {
        "name": "Scale",
        "description": "Optimize and grow what's working",
        "typical_duration": "3-12 months",
        "milestones": ["50_percent_to_goal", "sustainable_growth_rate", "target_achieved"]
      }
    ],
    "recommended_check_ins": "weekly",
    "key_metrics": ["current_monthly_income", "growth_rate", "income_sources_count"]
  },
  
  "resources": {
    "tools": ["budget_tracker", "income_analyzer", "opportunity_scanner"],
    "content": ["income_growth_course", "negotiation_guide", "side_hustle_handbook"],
    "support": ["financial_coach", "accountability_partner", "mastermind_group"]
  },
  
  "connections": {
    "prerequisites": ["wealth_emergency_fund"],
    "enables": ["wealth_20k_monthly", "wealth_passive_income", "purpose_help_others_earn"],
    "synergizes_with": ["health_energy_optimization", "happiness_work_life_balance"],
    "conflicts_with": ["happiness_more_free_time"] 
  },
  
  "social_proof": {
    "total_attempts": 15420,
    "success_rate": 0.34,
    "average_duration_to_success": "14 months",
    "common_obstacles": [
      "inconsistent effort",
      "wrong income vehicle",
      "limiting beliefs about money"
    ],
    "success_factors": [
      "daily action consistency",
      "multiple income stream approach",
      "skill development investment"
    ]
  },
  
  "meta": {
    "created_at": "2026-01-17",
    "updated_at": "2026-01-17",
    "created_by": "system",
    "popularity_rank": 5,
    "trending": true
  }
}
```

### Goal Library Hierarchy

```
GOAL LIBRARY
│
├── 💰 WEALTH
│   ├── Income
│   │   ├── First $1K/month online
│   │   ├── $5K/month milestone
│   │   ├── $10K/month milestone
│   │   ├── $25K/month milestone
│   │   ├── $50K/month milestone
│   │   ├── $100K/month milestone
│   │   └── Income replacement (match current job)
│   │
│   ├── Savings
│   │   ├── Emergency fund ($1K)
│   │   ├── 3-month runway
│   │   ├── 6-month runway
│   │   ├── 1-year runway
│   │   └── Financial independence number
│   │
│   ├── Debt Freedom
│   │   ├── Credit card debt elimination
│   │   ├── Student loan payoff
│   │   ├── Mortgage payoff
│   │   └── Complete debt freedom
│   │
│   ├── Investment
│   │   ├── First $10K invested
│   │   ├── First $100K invested
│   │   ├── First $1M invested
│   │   └── Passive income goal ($/month)
│   │
│   └── Business
│       ├── Validate business idea
│       ├── First paying customer
│       ├── First $10K revenue
│       ├── First $100K revenue
│       ├── First profitable month
│       └── Exit/acquisition
│
├── ❤️ HEALTH
│   ├── Physical
│   │   ├── Weight loss (X lbs)
│   │   ├── Weight gain (X lbs)
│   │   ├── Run a 5K
│   │   ├── Run a marathon
│   │   ├── Strength goals (specific lifts)
│   │   ├── Flexibility goals
│   │   └── Sport-specific performance
│   │
│   ├── Energy
│   │   ├── Sleep optimization
│   │   ├── Morning routine mastery
│   │   ├── All-day energy
│   │   └── Eliminate chronic fatigue
│   │
│   ├── Nutrition
│   │   ├── Clean eating habit
│   │   ├── Meal prep mastery
│   │   ├── Eliminate specific food
│   │   └── Optimize for performance
│   │
│   ├── Mental
│   │   ├── Overcome anxiety
│   │   ├── Manage depression
│   │   ├── Build resilience
│   │   └── Cognitive enhancement
│   │
│   └── Longevity
│       ├── Optimize biomarkers
│       ├── Reverse biological age
│       └── Disease prevention
│
├── 😊 HAPPINESS
│   ├── Emotional
│   │   ├── Daily joy practice
│   │   ├── Gratitude mastery
│   │   ├── Emotional regulation
│   │   └── Inner peace
│   │
│   ├── Fulfillment
│   │   ├── Find what lights you up
│   │   ├── Daily fulfillment routine
│   │   └── Life satisfaction score improvement
│   │
│   ├── Balance
│   │   ├── Work-life balance
│   │   ├── Reduce stress
│   │   └── More free time
│   │
│   └── Presence
│       ├── Meditation practice
│       ├── Mindfulness in daily life
│       └── Flow state mastery
│
├── 🎯 PURPOSE
│   ├── Career
│   │   ├── Get promoted
│   │   ├── Change careers
│   │   ├── Find dream job
│   │   └── Become industry leader
│   │
│   ├── Impact
│   │   ├── Help X people
│   │   ├── Start a movement
│   │   ├── Create lasting change
│   │   └── Leave a legacy
│   │
│   ├── Growth
│   │   ├── Learn new skill
│   │   ├── Master a domain
│   │   ├── Personal transformation
│   │   └── Become best version of self
│   │
│   └── Calling
│       ├── Discover life purpose
│       ├── Align work with purpose
│       └── Live purposefully daily
│
└── 🤝 CONNECTION
    ├── Relationships
    │   ├── Find life partner
    │   ├── Improve existing relationship
    │   ├── Heal family relationships
    │   └── Make deep friendships
    │
    ├── Community
    │   ├── Find your tribe
    │   ├── Build a community
    │   └── Become community leader
    │
    └── Social
        ├── Overcome social anxiety
        ├── Become more charismatic
        └── Build professional network
```

---

## 🔄 COMPONENT 2: THE INTAKE FLOW

### Purpose
Capture the user's goal, understand their context, and begin the alignment process.

### Flow Stages

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           INTAKE FLOW                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  STAGE 1: WELCOME & CONTEXT                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ • Name, email                                                        │   │
│  │ • WhiteRock PMA membership (legal protection)                        │   │
│  │ • How did you hear about us?                                         │   │
│  │ • Quick context: "What brings you here today?"                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                   │                                         │
│                                   ▼                                         │
│  STAGE 2: GOAL EXPLORATION                                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Option A: BROWSE GOAL LIBRARY                                        │   │
│  │   • Show categories: Wealth, Health, Happiness, Purpose, Connection  │   │
│  │   • Let them browse and select                                       │   │
│  │   • Customize parameters (amount, timeline, etc.)                    │   │
│  │                                                                      │   │
│  │ Option B: DESCRIBE YOUR GOAL                                         │   │
│  │   • Free-form text input                                             │   │
│  │   • AI matches to Goal Library or creates custom                     │   │
│  │   • "I want to..." prompt                                            │   │
│  │                                                                      │   │
│  │ Option C: NOT SURE YET                                               │   │
│  │   • "Help me discover my goal"                                       │   │
│  │   • Triggers Discovery Call path                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                   │                                         │
│                                   ▼                                         │
│  STAGE 3: GOAL VALUE ASSESSMENT                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ "What would achieving this goal be worth to you?"                    │   │
│  │                                                                      │   │
│  │ • What changes in your life when you achieve this?                   │   │
│  │ • On a scale of 1-10, how important is this right now?               │   │
│  │ • What have you already tried?                                       │   │
│  │ • What's stopped you before?                                         │   │
│  │                                                                      │   │
│  │ INVESTMENT QUESTION:                                                 │   │
│  │ "If we could guarantee you'd achieve this goal, what would          │   │
│  │  that be worth investing per month?"                                 │   │
│  │                                                                      │   │
│  │  ○ Under $100/month                                                  │   │
│  │  ○ $100-300/month                                                    │   │
│  │  ○ $300-500/month                                                    │   │
│  │  ○ $500-1,000/month                                                  │   │
│  │  ○ $1,000-3,000/month                                                │   │
│  │  ○ $3,000+/month                                                     │   │
│  │  ○ Not sure - let's discuss                                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                   │                                         │
│                                   ▼                                         │
│  STAGE 4: ALIGNMENT CHECK (AI-DRIVEN)                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ AI reviews the goal and asks integrity questions:                    │   │
│  │                                                                      │   │
│  │ • "Who benefits when you achieve this goal?"                         │   │
│  │ • "What impact does this have on people around you?"                 │   │
│  │ • "Is this goal in alignment with your deeper values?"               │   │
│  │                                                                      │   │
│  │ If alignment concerns detected:                                      │   │
│  │ → Offer optimized goal alternatives                                  │   │
│  │ → "Would you be open to a version of this goal that also..."        │   │
│  │                                                                      │   │
│  │ User always has final choice.                                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                   │                                         │
│                                   ▼                                         │
│  STAGE 5: COMMITMENT & ROUTING                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Based on goal + budget + urgency, route to:                          │   │
│  │                                                                      │   │
│  │ PATH A: SELF-GUIDED (Under $100/month)                               │   │
│  │   → Goal Library resources                                           │   │
│  │   → AI check-ins                                                     │   │
│  │   → Community access                                                 │   │
│  │                                                                      │   │
│  │ PATH B: AI-SUPPORTED ($100-500/month)                                │   │
│  │   → All of Path A                                                    │   │
│  │   → Personal AI companion                                            │   │
│  │   → Weekly accountability                                            │   │
│  │   → Tool access                                                      │   │
│  │                                                                      │   │
│  │ PATH C: COACH-LED ($500-3,000/month)                                 │   │
│  │   → All of Path B                                                    │   │
│  │   → Human coach assignment                                           │   │
│  │   → 1-on-1 sessions                                                  │   │
│  │   → Personalized strategy                                            │   │
│  │                                                                      │   │
│  │ PATH D: FULL PARTNERSHIP ($3,000+/month)                             │   │
│  │   → All of Path C                                                    │   │
│  │   → Direct access to James/founders                                  │   │
│  │   → Custom solution building                                         │   │
│  │   → Done-with-you service                                            │   │
│  │                                                                      │   │
│  │ PATH E: DISCOVERY CALL (Not sure)                                    │   │
│  │   → Schedule call with team                                          │   │
│  │   → Clarify goal together                                            │   │
│  │   → Find right path                                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚖️ COMPONENT 3: THE ALIGNMENT ENGINE

### Purpose
The intelligence layer that evaluates goals, suggests optimizations, and ensures goals serve both the individual AND the greater good.

### Alignment Hierarchy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      ALIGNMENT EVALUATION HIERARCHY                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Level 1: PLANETARY HEALTH                                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Does this goal harm Earth's systems?                                 │   │
│  │                                                                      │   │
│  │ Check for:                                                           │   │
│  │ • Environmental destruction                                          │   │
│  │ • Unsustainable resource extraction                                  │   │
│  │ • Pollution generation                                               │   │
│  │ • Biodiversity harm                                                  │   │
│  │                                                                      │   │
│  │ If detected → Suggest aligned alternative                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                   │                                         │
│                                   ▼                                         │
│  Level 2: COLLECTIVE WELLBEING                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Does this goal extract value from others unfairly?                   │   │
│  │                                                                      │   │
│  │ Check for:                                                           │   │
│  │ • Zero-sum thinking ("I win, you lose")                              │   │
│  │ • Exploitation-based models                                          │   │
│  │ • Manipulation tactics                                               │   │
│  │ • Harm to communities                                                │   │
│  │                                                                      │   │
│  │ If detected → Suggest win-win version                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                   │                                         │
│                                   ▼                                         │
│  Level 3: LONG-TERM SUSTAINABILITY                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Is this a short-term fix that creates future problems?               │   │
│  │                                                                      │   │
│  │ Check for:                                                           │   │
│  │ • Quick-fix mentality                                                │   │
│  │ • Unsustainable pace                                                 │   │
│  │ • Deferred consequences                                              │   │
│  │ • Burnout risk                                                       │   │
│  │                                                                      │   │
│  │ If detected → Suggest sustainable path                               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                   │                                         │
│                                   ▼                                         │
│  Level 4: PERSONAL INTEGRITY                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Does this goal align with who they want to become?                   │   │
│  │                                                                      │   │
│  │ Check for:                                                           │   │
│  │ • Value conflicts                                                    │   │
│  │ • Identity misalignment                                              │   │
│  │ • Pursuing others' goals                                             │   │
│  │ • "Should" vs "Want"                                                 │   │
│  │                                                                      │   │
│  │ If detected → Surface the conflict gently                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                   │                                         │
│                                   ▼                                         │
│  Level 5: IMMEDIATE DESIRE                                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Serve their stated desire, optimized through the layers above.       │   │
│  │                                                                      │   │
│  │ User ALWAYS has final choice.                                        │   │
│  │ AI suggests, never mandates.                                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Alignment Response Patterns

```
PATTERN 1: DIRECT ALIGNMENT
User goal passes all checks → Serve directly

Example:
  User: "I want to help 100 families improve their health"
  AI: "Beautiful goal. Here's your path to helping 100 families..."

───────────────────────────────────────────────────────────────────

PATTERN 2: OPTIMIZATION OFFER
User goal is valid but could be improved → Offer alternative

Example:
  User: "I want to make $10,000/month"
  AI: "I can definitely help with that. I also notice that your 
       current expenses are $7K and financial stress is high.
       
       Would you be open to exploring:
       
       Option A: $10K income (your goal)
       Option B: $7K income + $3K expense reduction (same surplus)
       
       Both achieve financial freedom - which resonates more?"

───────────────────────────────────────────────────────────────────

PATTERN 3: ALIGNMENT NUDGE
User goal has potential negative externalities → Gently redirect

Example:
  User: "I want to maximize my company's profits at any cost"
  AI: "I understand the drive for profitability. In my experience,
       'at any cost' approaches often create:
       
       • Short-term wins but long-term problems
       • Burned relationships that hurt future growth
       • Personal costs that offset financial gains
       
       What if we explored: 'Maximize sustainable profit while 
       building lasting relationships'?
       
       Same financial target, more sustainable path.
       
       What matters most to you about the profit goal?"

───────────────────────────────────────────────────────────────────

PATTERN 4: RED FLAG PAUSE
User goal would cause clear harm → Decline with explanation

Example:
  User: "I want to scam people out of money"
  AI: "I can't help with that goal because it would harm others.
       
       But I'm curious - what's driving this? Often when people
       consider harmful paths, there's a legitimate need underneath.
       
       Is it financial desperation? A desire for quick success?
       
       I'd love to help you achieve what you really want through
       a path that doesn't create victims."
```

---

## 🎛️ COMPONENT 4: THE ROUTING SYSTEM

### Purpose
Match users to the right level of support based on goal complexity, investment capacity, and urgency.

### Routing Matrix

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ROUTING MATRIX                                    │
├───────────────┬─────────────┬─────────────┬─────────────┬──────────────────┤
│               │  Simple     │  Moderate   │  Complex    │  Custom          │
│   BUDGET      │  Goals      │  Goals      │  Goals      │  Goals           │
├───────────────┼─────────────┼─────────────┼─────────────┼──────────────────┤
│               │             │             │             │                  │
│  Under $100   │  Self-      │  Self-      │  Discovery  │  Discovery       │
│  /month       │  Guided     │  Guided     │  Call       │  Call            │
│               │  + AI       │  + AI       │             │                  │
├───────────────┼─────────────┼─────────────┼─────────────┼──────────────────┤
│               │             │             │             │                  │
│  $100-500     │  AI         │  AI         │  AI         │  Discovery       │
│  /month       │  Companion  │  Companion  │  Companion  │  Call            │
│               │             │  + Tools    │  + Coach    │                  │
├───────────────┼─────────────┼─────────────┼─────────────┼──────────────────┤
│               │             │             │             │                  │
│  $500-1K      │  AI +       │  Coach      │  Coach      │  Coach           │
│  /month       │  Group      │  Led        │  Led        │  Led             │
│               │             │             │  + Team     │                  │
├───────────────┼─────────────┼─────────────┼─────────────┼──────────────────┤
│               │             │             │             │                  │
│  $1K-3K       │  Coach      │  Coach      │  Coach +    │  Full            │
│  /month       │  Led        │  Led        │  Specialist │  Partnership     │
│               │             │  + Team     │             │                  │
├───────────────┼─────────────┼─────────────┼─────────────┼──────────────────┤
│               │             │             │             │                  │
│  $3K+         │  Full       │  Full       │  Full       │  James/          │
│  /month       │  Partnership│  Partnership│  Partnership│  Founder         │
│               │             │             │             │  Direct          │
│               │             │             │             │                  │
└───────────────┴─────────────┴─────────────┴─────────────┴──────────────────┘
```

### Service Tiers Detail

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ TIER 1: SELF-GUIDED                                        Under $100/mo   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ What's Included:                                                            │
│ • Access to Goal Library                                                    │
│ • AI chatbot for questions                                                  │
│ • Weekly email check-ins                                                    │
│ • Community forum access                                                    │
│ • Basic progress tracking                                                   │
│                                                                             │
│ Pricing:                                                                    │
│ • Free tier: Very limited                                                   │
│ • $29/mo: Full access                                                       │
│ • $97/mo: Premium content                                                   │
│                                                                             │
│ Best For:                                                                   │
│ • Self-motivated individuals                                                │
│ • Simple, clear goals                                                       │
│ • Those exploring the system                                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ TIER 2: AI COMPANION                                       $100-500/mo     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ What's Included:                                                            │
│ • Everything in Self-Guided                                                 │
│ • Personal AI companion (Aria)                                              │
│ • Daily check-ins via chat/SMS                                              │
│ • Weekly accountability calls (AI)                                          │
│ • Personalized action plans                                                 │
│ • Tool access (relevant to goal)                                            │
│ • Progress analytics                                                        │
│                                                                             │
│ Pricing:                                                                    │
│ • $197/mo: Standard                                                         │
│ • $297/mo: With tools                                                       │
│ • $497/mo: Premium AI                                                       │
│                                                                             │
│ Best For:                                                                   │
│ • Those who need accountability                                             │
│ • Moderate complexity goals                                                 │
│ • Want support but can self-execute                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ TIER 3: COACH-LED                                          $500-3,000/mo   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ What's Included:                                                            │
│ • Everything in AI Companion                                                │
│ • Assigned human coach                                                      │
│ • 2-4 live sessions per month                                               │
│ • Custom strategy development                                               │
│ • Direct messaging with coach                                               │
│ • Expert referrals as needed                                                │
│ • Milestone celebrations                                                    │
│                                                                             │
│ Pricing:                                                                    │
│ • $797/mo: 2 sessions                                                       │
│ • $1,497/mo: 4 sessions                                                     │
│ • $2,497/mo: 4 sessions + team                                              │
│                                                                             │
│ Best For:                                                                   │
│ • Complex transformation goals                                              │
│ • Those who value human guidance                                            │
│ • Serious about change                                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ TIER 4: FULL PARTNERSHIP                                   $3,000+/mo      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ What's Included:                                                            │
│ • Everything in Coach-Led                                                   │
│ • Access to James/founders                                                  │
│ • Custom solution building                                                  │
│ • Done-with-you service                                                     │
│ • Priority support                                                          │
│ • Network introductions                                                     │
│ • Investment opportunities                                                  │
│                                                                             │
│ Pricing:                                                                    │
│ • $5,000/mo: Standard partnership                                           │
│ • $10,000/mo: Intensive partnership                                         │
│ • Custom: Major life transformations                                        │
│                                                                             │
│ Best For:                                                                   │
│ • High-net-worth individuals                                                │
│ • Business owners                                                           │
│ • Those seeking major life transformation                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Team Roles

```
WHO HANDLES WHAT
────────────────────────────────────────────────────────────────────────────

🤖 ARIA (AI)
   • First response to all inquiries
   • Intake flow management
   • Daily check-ins
   • Goal tracking
   • Resource recommendations
   • Tier 1-2 primary support
   • Tier 3-4 support assistant

👥 COACH NETWORK (Human)
   • Tier 3 primary support
   • Live sessions
   • Complex problem solving
   • Emotional support
   • Specialized expertise
   
   Specializations:
   • Wealth coaches
   • Health coaches
   • Life coaches
   • Business coaches
   • Relationship coaches

👤 JAMES (Founder)
   • Tier 4 primary
   • Discovery calls (high value)
   • Strategic guidance
   • Network connections
   • Custom solutions

🏢 TEAM (Operations)
   • Scheduling
   • Billing
   • Technical support
   • Community management
```

---

## 🛤️ COMPONENT 5: THE JOURNEY SYSTEM

### Purpose
Guide users through their goal achievement with the right support at each phase.

### Journey Phases

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          THE GOAL JOURNEY                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PHASE 1: DISCOVERY (Week 1-2)                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Purpose: Understand where they are and where they want to go         │   │
│  │                                                                      │   │
│  │ Activities:                                                          │   │
│  │ • Complete intake flow                                               │   │
│  │ • Current state assessment                                           │   │
│  │ • Goal refinement (with alignment check)                             │   │
│  │ • Identify obstacles and resources                                   │   │
│  │ • Match to right tier/coach                                          │   │
│  │                                                                      │   │
│  │ Deliverables:                                                        │   │
│  │ • Personal Goal Blueprint                                            │   │
│  │ • Success metrics defined                                            │   │
│  │ • Initial action plan                                                │   │
│  │                                                                      │   │
│  │ Check-ins: Daily (AI), 1 live session (if Tier 3+)                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                   │                                         │
│                                   ▼                                         │
│  PHASE 2: FOUNDATION (Week 3-6)                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Purpose: Build the habits and systems needed for success             │   │
│  │                                                                      │   │
│  │ Activities:                                                          │   │
│  │ • Habit installation                                                 │   │
│  │ • System setup (tools, tracking, environment)                        │   │
│  │ • Skill development begins                                           │   │
│  │ • Quick wins for momentum                                            │   │
│  │ • Identify and address early blockers                                │   │
│  │                                                                      │   │
│  │ Deliverables:                                                        │   │
│  │ • Core habits established                                            │   │
│  │ • Tools configured                                                   │   │
│  │ • First milestone achieved                                           │   │
│  │                                                                      │   │
│  │ Check-ins: Daily (AI), Weekly (human if Tier 3+)                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                   │                                         │
│                                   ▼                                         │
│  PHASE 3: MOMENTUM (Month 2-3)                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Purpose: Build on foundation, start seeing real results              │   │
│  │                                                                      │   │
│  │ Activities:                                                          │   │
│  │ • Consistent execution                                               │   │
│  │ • Metrics tracking                                                   │   │
│  │ • Obstacle resolution                                                │   │
│  │ • Strategy refinement                                                │   │
│  │ • Expand what's working                                              │   │
│  │                                                                      │   │
│  │ Deliverables:                                                        │   │
│  │ • 25% progress toward goal                                           │   │
│  │ • Clear what's working/not working                                   │   │
│  │ • Adjusted plan based on data                                        │   │
│  │                                                                      │   │
│  │ Check-ins: Daily (AI), Weekly or bi-weekly (human)                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                   │                                         │
│                                   ▼                                         │
│  PHASE 4: BREAKTHROUGH (Month 3-6)                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Purpose: Push through plateaus, achieve major milestones             │   │
│  │                                                                      │   │
│  │ Activities:                                                          │   │
│  │ • Double down on what works                                          │   │
│  │ • Address deeper blockers                                            │   │
│  │ • Level-up interventions                                             │   │
│  │ • Celebrate wins                                                     │   │
│  │ • Maintain motivation through middle slog                            │   │
│  │                                                                      │   │
│  │ Deliverables:                                                        │   │
│  │ • 50%+ progress toward goal                                          │   │
│  │ • Major breakthrough moment                                          │   │
│  │ • New capabilities developed                                         │   │
│  │                                                                      │   │
│  │ Check-ins: Daily (AI), As needed (human)                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                   │                                         │
│                                   ▼                                         │
│  PHASE 5: ACHIEVEMENT (Month 6-12)                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Purpose: Cross the finish line, solidify the transformation          │   │
│  │                                                                      │   │
│  │ Activities:                                                          │   │
│  │ • Final push to goal                                                 │   │
│  │ • Troubleshoot last obstacles                                        │   │
│  │ • Document what worked                                               │   │
│  │ • Prepare for goal completion                                        │   │
│  │ • Plan what's next                                                   │   │
│  │                                                                      │   │
│  │ Deliverables:                                                        │   │
│  │ • GOAL ACHIEVED ✅                                                   │   │
│  │ • Success story documented                                           │   │
│  │ • Next goal identified                                               │   │
│  │                                                                      │   │
│  │ Check-ins: Weekly (AI), Celebration session (human)                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                   │                                         │
│                                   ▼                                         │
│  PHASE 6: INTEGRATION & NEXT LEVEL                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Purpose: Lock in gains, choose next transformation                   │   │
│  │                                                                      │   │
│  │ Activities:                                                          │   │
│  │ • Ensure goal is sustained                                           │   │
│  │ • Capture learnings                                                  │   │
│  │ • Contribute to community                                            │   │
│  │ • Select next goal                                                   │   │
│  │ • Continue or adjust service tier                                    │   │
│  │                                                                      │   │
│  │ Deliverables:                                                        │   │
│  │ • Transformation case study                                          │   │
│  │ • Mentor/coach others option                                         │   │
│  │ • Next goal journey started                                          │   │
│  │                                                                      │   │
│  │ Check-ins: Monthly (AI), As desired (human)                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 💰 COMPONENT 6: THE BUSINESS MODEL

### Revenue Streams

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          REVENUE MODEL                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PRIMARY REVENUE: SUBSCRIPTIONS                                            │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  Tier 1: Self-Guided                                                        │
│    Free         • Very limited access                                       │
│    $29/mo       • Full library access                                       │
│    $97/mo       • Premium content                                           │
│                                                                             │
│  Tier 2: AI Companion                                                       │
│    $197/mo      • Personal AI                                               │
│    $297/mo      • AI + Tools                                                │
│    $497/mo      • Premium AI                                                │
│                                                                             │
│  Tier 3: Coach-Led                                                          │
│    $797/mo      • 2 sessions/mo                                             │
│    $1,497/mo    • 4 sessions/mo                                             │
│    $2,497/mo    • 4 sessions + team                                         │
│                                                                             │
│  Tier 4: Full Partnership                                                   │
│    $5,000/mo    • Standard partnership                                      │
│    $10,000/mo   • Intensive partnership                                     │
│    Custom       • Major transformations                                     │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  SECONDARY REVENUE: TRANSACTIONS                                           │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  • Course purchases                                                         │
│  • Tool access fees                                                         │
│  • Specialist referral fees (10-20%)                                        │
│  • Community events                                                         │
│  • Certification programs                                                   │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  TERTIARY REVENUE: SUCCESS-BASED                                           │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  • Performance bonuses (opt-in)                                             │
│    "Pay 10% of income increase if goal achieved"                            │
│                                                                             │
│  • Investment opportunities                                                 │
│    For wealth goals: option to invest together                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Unit Economics

```
CUSTOMER ECONOMICS
────────────────────────────────────────────────────────────────────────────

Average Customer Value (ACV):
  Tier 1: $29/mo × 3 months avg = $87
  Tier 2: $297/mo × 6 months avg = $1,782
  Tier 3: $1,497/mo × 12 months avg = $17,964
  Tier 4: $5,000/mo × 18 months avg = $90,000

Blended ACV (estimated mix):
  60% Tier 1, 25% Tier 2, 12% Tier 3, 3% Tier 4
  = (0.60 × $87) + (0.25 × $1,782) + (0.12 × $17,964) + (0.03 × $90,000)
  = $52 + $446 + $2,156 + $2,700
  = $5,354 average lifetime value

Customer Acquisition Cost (target):
  Tier 1: Under $20
  Tier 2: Under $200
  Tier 3: Under $500
  Tier 4: Under $1,000

LTV:CAC Ratio Target: 5:1 minimum

COACH ECONOMICS
────────────────────────────────────────────────────────────────────────────

Coach revenue share: 60% of session fees
  $797/mo client = ~$480/mo to coach
  $1,497/mo client = ~$900/mo to coach
  $2,497/mo client = ~$1,500/mo to coach

Coach capacity: 15-20 clients max per coach
Coach income potential: $7,200 - $30,000/mo

MARGIN ANALYSIS
────────────────────────────────────────────────────────────────────────────

Tier 1: 90% margin (mostly automated)
Tier 2: 80% margin (AI + minimal support)
Tier 3: 35% margin (after coach payout)
Tier 4: 50% margin (James time is valuable)

Target blended margin: 55-65%
```

---

## 🔄 COMPONENT 7: FEEDBACK & LEARNING

### Purpose
The system gets smarter over time by learning what works and what doesn't.

### Data Collection

```
WHAT WE TRACK
────────────────────────────────────────────────────────────────────────────

Goal Level:
• Success rate per goal type
• Average time to achievement
• Common failure points
• Best practices that work

Individual Level:
• Progress against milestones
• Engagement patterns
• Support utilization
• Satisfaction scores

System Level:
• Conversion rates per path
• Churn patterns
• NPS and testimonials
• Revenue per goal category
```

### Learning Loops

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          LEARNING LOOPS                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  LOOP 1: GOAL IMPROVEMENT                                                  │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  Input: User outcomes for each goal type                                    │
│  Process: Analyze success/failure patterns                                  │
│  Output: Improved goal templates, better journeys                           │
│                                                                             │
│  Frequency: Monthly                                                         │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  LOOP 2: ALIGNMENT REFINEMENT                                              │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  Input: User responses to alignment suggestions                             │
│  Process: Track which suggestions are accepted/rejected                     │
│  Output: Better alignment prompts, timing, phrasing                         │
│                                                                             │
│  Frequency: Weekly                                                          │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  LOOP 3: COACH OPTIMIZATION                                                │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  Input: Client outcomes per coach                                           │
│  Process: Identify what top coaches do differently                          │
│  Output: Coach training, better matching                                    │
│                                                                             │
│  Frequency: Quarterly                                                       │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  LOOP 4: COLLECTIVE INTELLIGENCE                                           │
│  ────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│  Input: Aggregate patterns across all users                                 │
│  Process: Identify universal truths about goal achievement                  │
│  Output: "What humanity has learned about achieving X"                      │
│                                                                             │
│  Frequency: Ongoing (AI-driven)                                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔧 TECHNICAL IMPLEMENTATION

### System Components

```
FRONTEND
────────────────────────────────────────────────────────────────────────────
• FullPotential.com (Next.js) - Main website
• Intake wizard - Goal selection and onboarding
• Dashboard - Progress tracking
• Chat interface - Aria AI companion
• Community - Forum/discussion

BACKEND SERVICES
────────────────────────────────────────────────────────────────────────────
• Goal Service - Goal library management
• User Service - Profiles and preferences
• Journey Service - Progress tracking
• Alignment Service - Goal evaluation engine
• Routing Service - Tier assignment
• Coaching Service - Coach management
• Billing Service - Stripe integration
• AI Service - Aria brain (Claude + Ollama)

DATA STORES
────────────────────────────────────────────────────────────────────────────
• PostgreSQL - Core data
• Redis - Caching, sessions
• Mem0 - AI memory (already integrated)
• S3 - Files, assets

INTEGRATIONS
────────────────────────────────────────────────────────────────────────────
• Stripe - Payments
• Calendly - Scheduling
• Telegram - Notifications
• SMS - Check-ins
• Email - Communications
```

### API Endpoints (Draft)

```
GOALS API
────────────────────────────────────────────────────────────────────────────
GET    /api/goals/categories        - List goal categories
GET    /api/goals/library           - Browse all goals
GET    /api/goals/:id               - Get goal details
POST   /api/goals/match             - AI match free-form to goal
POST   /api/goals/custom            - Create custom goal

USER JOURNEY API
────────────────────────────────────────────────────────────────────────────
POST   /api/journey/start           - Start new journey
GET    /api/journey/current         - Get active journey
PUT    /api/journey/progress        - Update progress
GET    /api/journey/milestones      - Get milestones
POST   /api/journey/complete        - Mark goal achieved

ALIGNMENT API
────────────────────────────────────────────────────────────────────────────
POST   /api/alignment/evaluate      - Evaluate goal alignment
GET    /api/alignment/suggestions   - Get optimization suggestions
POST   /api/alignment/respond       - User response to suggestion

ROUTING API
────────────────────────────────────────────────────────────────────────────
POST   /api/routing/assign          - Assign user to tier
GET    /api/routing/options         - Get available tiers
POST   /api/routing/upgrade         - Upgrade tier

COACHING API
────────────────────────────────────────────────────────────────────────────
GET    /api/coaches                 - List available coaches
GET    /api/coaches/:id             - Get coach profile
POST   /api/coaching/match          - Match user to coach
POST   /api/coaching/session        - Book session
```

---

## 🚀 IMPLEMENTATION ROADMAP

### Phase 1: MVP (Weeks 1-4)

```
WEEK 1-2: Foundation
• [ ] Update intake flow with goal library browser
• [ ] Create basic goal data structure
• [ ] Implement 20 starter goals (5 per category)
• [ ] Add alignment questions to intake

WEEK 3-4: Routing & Payments
• [ ] Implement routing logic
• [ ] Connect Stripe for subscription tiers
• [ ] Create basic dashboard for users
• [ ] AI companion basic integration
```

### Phase 2: Core System (Weeks 5-8)

```
WEEK 5-6: Journey System
• [ ] Progress tracking
• [ ] Milestone definitions
• [ ] Daily AI check-ins
• [ ] Email sequences

WEEK 7-8: Coaching Integration
• [ ] Coach profiles
• [ ] Matching algorithm
• [ ] Scheduling integration
• [ ] Session management
```

### Phase 3: Intelligence (Weeks 9-12)

```
WEEK 9-10: Alignment Engine
• [ ] Full alignment evaluation
• [ ] Suggestion system
• [ ] User response tracking
• [ ] Learning from outcomes

WEEK 11-12: Optimization
• [ ] Goal Library expansion (100+ goals)
• [ ] Feedback loops active
• [ ] Analytics dashboard
• [ ] A/B testing framework
```

---

## 📝 IMMEDIATE NEXT STEPS

1. **Update current intake flow** to include:
   - Goal category selection
   - Budget/investment question
   - Alignment questions

2. **Create Goal Library data structure** and seed with initial goals

3. **Implement routing logic** to match user to right tier

4. **Connect Stripe** for new pricing tiers

5. **Deploy Aria** as the AI companion for Tier 2+

---

## 🎯 SUCCESS METRICS

### North Star
**Number of goals achieved per month**

### Supporting Metrics
- Goal completion rate
- Average time to goal achievement
- Customer lifetime value
- Net Promoter Score
- Alignment acceptance rate (users accepting optimization suggestions)

---

*This spec is a living document. As we learn from users, it will evolve.*

**Version History:**
- v1.0.0 (2026-01-17): Initial spec created



