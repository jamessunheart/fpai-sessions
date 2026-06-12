# FULL POTENTIAL GOAL SYSTEM - IMPLEMENTATION GUIDE
## Quick Reference for Building the System

**Last Updated:** 2026-01-17

---

## 📁 SPEC FILES

| Document | Purpose |
|----------|---------|
| `FULL_POTENTIAL_GOAL_SYSTEM.md` | Master spec - complete system architecture |
| `ALIGNMENT_ENGINE.md` | Deep dive on AI alignment logic |
| `goal-library/schema/goal.json` | JSON schema for goal data structure |
| `goal-library/seeds/wealth_goals.json` | Initial seed data for wealth goals |

---

## 🏗️ WHAT WE'RE BUILDING

### The Core Concept

**Full Potential is a goal realization system where:**
1. Humans define their goals
2. AI serves those goals with full support
3. AI gently suggests optimizations toward greater alignment
4. User always has final choice
5. System learns and improves

### The Business Model

```
┌─────────────────────────────────────────────────────────────────┐
│  TIER 1: Self-Guided           │  Under $100/mo              │
│  TIER 2: AI Companion          │  $100-500/mo                │
│  TIER 3: Coach-Led             │  $500-3,000/mo              │
│  TIER 4: Full Partnership      │  $3,000+/mo                 │
└─────────────────────────────────────────────────────────────────┘
```

### The Alignment Innovation

AI serves human goals while optimizing toward:
1. Planetary health
2. Collective wellbeing  
3. Long-term sustainability
4. Personal integrity
5. Immediate desire (always honored)

---

## 🚀 IMPLEMENTATION PHASES

### Phase 1: MVP (Weeks 1-4)

**Goal:** Working intake flow with goal selection and payment

#### Week 1-2: Foundation
- [ ] Update FullPotential.com intake flow
  - Add goal category browser
  - Add goal customization
  - Add budget/investment question
  - Add basic alignment questions
  
- [ ] Create Goal Library service
  - Goal data model
  - CRUD API endpoints
  - Seed with 20 initial goals

#### Week 3-4: Routing & Payments  
- [ ] Implement routing logic
  - Goal complexity assessment
  - Budget tier matching
  - Path recommendation
  
- [ ] Connect Stripe
  - 4 subscription tiers
  - Payment flow
  - Webhook handling

### Phase 2: Core System (Weeks 5-8)

**Goal:** Journey tracking and AI support

#### Week 5-6: Journey System
- [ ] Progress tracking
  - Milestone definitions per goal
  - Progress updates
  - Status dashboard
  
- [ ] AI Check-ins
  - Daily message (Tier 2+)
  - Weekly summary
  - Milestone celebrations

#### Week 7-8: Coaching Integration
- [ ] Coach profiles
- [ ] Matching algorithm
- [ ] Calendly integration
- [ ] Session management

### Phase 3: Intelligence (Weeks 9-12)

**Goal:** Full alignment engine and learning

#### Week 9-10: Alignment Engine
- [ ] Alignment evaluation API
- [ ] Suggestion system
- [ ] Response templates
- [ ] User choice tracking

#### Week 11-12: Optimization
- [ ] Goal Library to 100+ goals
- [ ] Feedback loops active
- [ ] A/B testing
- [ ] Analytics dashboard

---

## 📊 DATA MODELS

### User Journey

```typescript
interface UserJourney {
  id: string;
  user_id: string;
  goal_id: string;
  goal_parameters: Record<string, any>;
  
  tier: 'self_guided' | 'ai_companion' | 'coach_led' | 'partnership';
  status: 'discovery' | 'foundation' | 'momentum' | 'breakthrough' | 'achieved' | 'paused';
  
  started_at: Date;
  target_date: Date | null;
  achieved_at: Date | null;
  
  milestones: Milestone[];
  check_ins: CheckIn[];
  
  coach_id: string | null;
  
  alignment_score: number;
  alignment_adjustments: AlignmentAdjustment[];
}

interface Milestone {
  id: string;
  name: string;
  description: string;
  target_value: any;
  current_value: any;
  status: 'pending' | 'in_progress' | 'achieved';
  achieved_at: Date | null;
}

interface CheckIn {
  id: string;
  type: 'ai_daily' | 'ai_weekly' | 'human_session';
  occurred_at: Date;
  summary: string;
  mood_score: number | null;
  progress_update: string | null;
}
```

### Alignment Record

```typescript
interface AlignmentEvaluation {
  id: string;
  goal_id: string;
  user_id: string;
  
  original_goal_text: string;
  evaluated_at: Date;
  
  scores: {
    planetary: number;
    collective: number;
    sustainability: number;
    integrity: number;
    overall: number;
  };
  
  issues_detected: string[];
  suggestions_offered: Suggestion[];
  
  user_response: 'accepted_suggestion' | 'kept_original' | 'modified' | 'abandoned';
  final_goal_id: string;
}

interface Suggestion {
  type: 'optimization' | 'alternative' | 'question';
  content: string;
  alternative_goal_id: string | null;
}
```

---

## 🔌 API ENDPOINTS

### Goals API

```
GET    /api/goals/categories
GET    /api/goals/library?category=wealth
GET    /api/goals/:id
POST   /api/goals/match     { goal_text: string }
POST   /api/goals/custom    { ...custom goal data }
```

### Journey API

```
POST   /api/journey/start   { goal_id, parameters, tier }
GET    /api/journey/current
PUT    /api/journey/progress  { milestone_id, value }
GET    /api/journey/milestones
POST   /api/journey/checkin   { type, summary, mood }
POST   /api/journey/complete
```

### Alignment API

```
POST   /api/alignment/evaluate  { goal_text, user_context }
GET    /api/alignment/suggestions/:evaluation_id
POST   /api/alignment/respond   { evaluation_id, response }
```

### Routing API

```
POST   /api/routing/recommend  { goal_id, budget, urgency }
GET    /api/routing/tiers
POST   /api/routing/select     { tier, payment_method }
```

---

## 🎨 UI COMPONENTS NEEDED

### Intake Flow

1. **GoalCategoryPicker** - Visual category selection
2. **GoalBrowser** - Browse goals within category
3. **GoalCustomizer** - Customize goal parameters
4. **BudgetSelector** - Investment level selection
5. **AlignmentQuestions** - Integrity question flow
6. **TierRecommendation** - Show recommended tier
7. **PaymentFlow** - Stripe checkout integration

### Dashboard

1. **JourneyOverview** - Current goal progress
2. **MilestoneTracker** - Visual milestone progress
3. **CheckInWidget** - Daily/weekly check-in
4. **AICompanion** - Chat interface with Aria
5. **SessionScheduler** - Book coach sessions
6. **ProgressCharts** - Analytics visualization

---

## 🔗 INTEGRATIONS

| Service | Purpose | Priority |
|---------|---------|----------|
| Stripe | Payments | P0 |
| Aria (AI) | Companion | P0 |
| Calendly | Coach scheduling | P1 |
| Telegram | Notifications | P1 |
| Mem0 | AI memory | P1 |
| SendGrid | Email | P2 |
| Twilio | SMS check-ins | P2 |

---

## 📈 SUCCESS METRICS

### North Star
**Goals Achieved Per Month**

### Leading Indicators
- Daily active users in journeys
- Check-in completion rate
- Milestone achievement rate
- Suggestion acceptance rate

### Lagging Indicators  
- Goal completion rate
- Customer lifetime value
- Net Promoter Score
- Churn rate

---

## 🚦 IMMEDIATE NEXT STEPS

1. **Update intake flow** on FullPotential.com
   - File: `fullpotential_ai/fullpotential_core/core/applications/website-ai/frontend/app/intake/page.tsx`
   - Add goal category selection
   - Add budget question

2. **Create goal-library service**
   - New service: `SERVICES/goal-library/`
   - FastAPI backend
   - PostgreSQL storage
   - Seed with initial goals

3. **Connect Stripe** for new tiers
   - Products: Self-Guided, AI Companion, Coach-Led, Partnership
   - Subscription billing

4. **Deploy Aria** as AI companion
   - Already exists: `SERVICES/aria-command/`
   - Integrate with journey system
   - Configure daily check-ins

---

## 📞 QUESTIONS FOR JAMES

1. **Coach Network:** Do we have coaches ready, or do we need to recruit?
2. **Content Library:** What existing content can we map to goals?
3. **Pricing:** Are the tier prices correct? ($29, $197, $797, $5K)
4. **Discovery Calls:** Who handles them initially?
5. **Launch Strategy:** Soft launch with existing leads or broader marketing?

---

*This is a living document. Update as we learn and build.*



