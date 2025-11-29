# 🇵🇭 BPO Staffing & Referral Vertical - BRICK 2 Module

**Vertical Name:** `bpo-staffing-referral`
**Type:** Lead Generation + Referral Network + Hybrid AI/Human Services
**Market:** Philippines BPO/Call Center + Global VA Services
**Integration:** fullpotential.ai/missions system

---

## 🎯 Business Model

### Core Offering
**Hybrid Human + AI Call Center & BPO Services**
- Traditional Filipino BPO talent (call center, admin, support)
- AI-augmented workflows (AI handles routine, humans handle complex)
- Fully AI solutions for appropriate use cases
- Referral network to scale distribution

### Revenue Streams

#### 1. Direct Staffing Revenue
Client pays for VA/agent hours → We earn margin on hourly rate

#### 2. Referral Commission Program (OneBPO Model)
| Hourly Rate | Commission |
|:-----------:|:----------:|
| $8 and below | 5.00% |
| $8.01 - $8.49 | 5.50% |
| $8.50 - $9.99 | 6.50% |
| $10.00 - $11.99 | 8.00% |
| $12.00 and above | 10.00% |

**Example:** Referrer brings client paying $12/hour for 160 hours/month
- Monthly revenue: $1,920
- Commission (10%): $192/month recurring
- Annual passive income: $2,304 per placement

#### 3. AI-Augmented Premium Services
- Higher margins on AI-enhanced workflows
- Upsell from pure human to hybrid solutions
- Technology licensing to other BPOs

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    BPO STAFFING & REFERRAL SYSTEM                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                    REFERRAL NETWORK LAYER                               │ │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐          │ │
│  │  │  Referrer  │ │ Commission │ │  Tracking  │ │  Payouts   │          │ │
│  │  │   Portal   │ │ Calculator │ │   System   │ │   Engine   │          │ │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘          │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                       │
│  ┌────────────────────────────────────┼────────────────────────────────────┐│
│  │                    CLIENT ACQUISITION LAYER                              ││
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐          ││
│  │  │   Lead     │ │   Needs    │ │    AI      │ │   Quote    │          ││
│  │  │   Capture  │ │ Assessment │ │ Qualifier  │ │ Generator  │          ││
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘          ││
│  └────────────────────────────────────┼────────────────────────────────────┘│
│                                       │                                      │
│  ┌────────────────────────────────────┼────────────────────────────────────┐│
│  │                    SERVICE DELIVERY LAYER                                ││
│  │  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐           ││
│  │  │  PURE HUMAN     │ │  HYBRID AI+H    │ │   PURE AI       │           ││
│  │  │  ─────────────  │ │  ─────────────  │ │  ─────────────  │           ││
│  │  │ • Call Center   │ │ • AI Triage +   │ │ • Chatbots      │           ││
│  │  │ • Admin Support │ │   Human Close   │ │ • Auto-Response │           ││
│  │  │ • Data Entry    │ │ • AI Draft +    │ │ • Data Process  │           ││
│  │  │ • Customer Svc  │ │   Human Review  │ │ • Lead Qual     │           ││
│  │  │ • Virtual Asst  │ │ • AI Monitor +  │ │ • Scheduling    │           ││
│  │  │                 │ │   Human Escal   │ │                 │           ││
│  │  └─────────────────┘ └─────────────────┘ └─────────────────┘           ││
│  └────────────────────────────────────────────────────────────────────────┘│
│                                       │                                      │
│  ┌────────────────────────────────────┼────────────────────────────────────┐│
│  │              MISSIONS INTEGRATION (fullpotential.ai/missions)           ││
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐          ││
│  │  │  Task      │ │   XP &     │ │  Training  │ │  Quality   │          ││
│  │  │  Router    │ │ Leveling   │ │  Missions  │ │  Control   │          ││
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘          ││
│  └────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📱 Referrer Portal Features

### 1. Dashboard
```
┌─────────────────────────────────────────────────────────────────┐
│  REFERRER DASHBOARD                              [John Smith]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  💰 EARNINGS THIS MONTH                     📊 PERFORMANCE     │
│  ┌───────────────────┐                     ┌──────────────────┐│
│  │      $1,847       │                     │ 12 Active Refs   ││
│  │  Commission YTD   │                     │ 94% Retention    ││
│  └───────────────────┘                     └──────────────────┘│
│                                                                 │
│  📋 YOUR REFERRALS                                              │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Client           │ Rate    │ Hours │ Commission │ Status   ││
│  │──────────────────┼─────────┼───────┼────────────┼──────────││
│  │ TechCorp Inc     │ $12/hr  │ 160   │ $192/mo    │ ✅ Active││
│  │ StartupXYZ       │ $10/hr  │ 80    │ $64/mo     │ ✅ Active││
│  │ LocalBiz LLC     │ $8/hr   │ 120   │ $48/mo     │ ✅ Active││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  🔗 YOUR REFERRAL LINK                                         │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ https://fullpotential.ai/bpo?ref=john-smith-x7k9           ││
│  │                                              [Copy] [Share] ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Referral Tracking
- Unique referral links with attribution
- Real-time conversion tracking
- Monthly commission statements
- Payout history and upcoming payments
- Performance leaderboards

### 3. Marketing Materials
- Pre-built email templates
- Social media graphics
- Case studies and testimonials
- Rate cards and service descriptions

---

## 🔗 Missions System Integration

### How It Works

The **fullpotential.ai/missions** system becomes the task router for BPO work:

```
CLIENT REQUEST → AI TRIAGE → MISSION CREATION → HUMAN CLAIM → DELIVERY
```

### Mission Types for BPO

#### Training Missions (New VAs)
```yaml
Mission: Complete Customer Service Training
Priority: P1
XP Reward: 500 XP
Time: 4 hours
Skills Gained: Customer Service Level 1
Prerequisites: None
```

#### Work Missions (Active VAs)
```yaml
Mission: Handle 50 Support Tickets
Priority: P0 (Client SLA)
XP Reward: 100 XP
Hourly Rate: $8.50/hr
Client: TechCorp Inc
Deadline: EOD
```

#### Quality Missions (Senior VAs)
```yaml
Mission: QA Review - 20 Call Recordings
Priority: P1
XP Reward: 75 XP
Rate: $10/hr
Skills Required: Customer Service Level 3
```

### XP & Leveling System
| Level | XP Required | Unlocks |
|:-----:|:-----------:|:--------|
| 1 | 0 | Basic missions, $6-8/hr work |
| 2 | 1,000 | Standard missions, $8-10/hr work |
| 3 | 3,000 | Advanced missions, $10-12/hr work |
| 4 | 7,000 | Premium missions, $12-15/hr work |
| 5 | 15,000 | Team lead opportunities, revenue share |

---

## 💼 Service Packages

### Package 1: Basic VA ($6-8/hour)
**Services:**
- Data entry
- Email management
- Calendar scheduling
- Basic research
- Social media posting

**AI Enhancement:** AI drafts, human reviews

### Package 2: Professional VA ($8-10/hour)
**Services:**
- Customer support (email/chat)
- CRM management
- Bookkeeping assistance
- Content creation
- Lead generation

**AI Enhancement:** AI handles Level 1 tickets, humans handle escalations

### Package 3: Specialist ($10-12/hour)
**Services:**
- Technical support
- Sales development
- Project management
- Executive assistance
- Specialized admin

**AI Enhancement:** AI monitoring + human expertise

### Package 4: Call Center ($12-15/hour)
**Services:**
- Inbound call handling
- Outbound sales calls
- Appointment setting
- Customer retention
- Technical helpdesk

**AI Enhancement:** AI call routing, sentiment analysis, script suggestions

---

## 🛠️ Technical Implementation

### Database Schema

```sql
-- Referrers
CREATE TABLE referrers (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    referral_code VARCHAR(50) UNIQUE,
    payment_method JSONB,  -- PayPal, bank transfer, crypto
    total_earnings DECIMAL(10,2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Referrals (Clients brought by referrers)
CREATE TABLE referrals (
    id SERIAL PRIMARY KEY,
    referrer_id INTEGER REFERENCES referrers(id),
    client_id INTEGER REFERENCES clients(id),
    hourly_rate DECIMAL(10,2),
    commission_rate DECIMAL(5,4),  -- Calculated based on rate tier
    status VARCHAR(20) DEFAULT 'pending',  -- pending, active, churned
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Commission tracking
CREATE TABLE commissions (
    id SERIAL PRIMARY KEY,
    referral_id INTEGER REFERENCES referrals(id),
    period_start DATE,
    period_end DATE,
    hours_worked DECIMAL(10,2),
    gross_revenue DECIMAL(10,2),
    commission_amount DECIMAL(10,2),
    status VARCHAR(20) DEFAULT 'pending',  -- pending, approved, paid
    paid_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- BPO Workers (VAs/Agents)
CREATE TABLE bpo_workers (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    level INTEGER DEFAULT 1,
    xp INTEGER DEFAULT 0,
    hourly_rate DECIMAL(10,2),
    skills JSONB,
    availability JSONB,
    status VARCHAR(20) DEFAULT 'available',
    rating DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Client placements
CREATE TABLE placements (
    id SERIAL PRIMARY KEY,
    client_id INTEGER REFERENCES clients(id),
    worker_id INTEGER REFERENCES bpo_workers(id),
    service_package VARCHAR(50),
    hourly_rate DECIMAL(10,2),
    hours_per_week INTEGER,
    start_date DATE,
    end_date DATE,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Commission Calculator

```python
def calculate_commission_rate(hourly_rate: float) -> float:
    """
    Calculate commission rate based on OneBPO tier structure.
    
    Tiers:
    - $8 and below: 5.00%
    - $8.01 to $8.49: 5.50%
    - $8.50 to $9.99: 6.50%
    - $10.00 to $11.99: 8.00%
    - $12.00 and above: 10.00%
    """
    if hourly_rate <= 8.00:
        return 0.0500
    elif hourly_rate <= 8.49:
        return 0.0550
    elif hourly_rate <= 9.99:
        return 0.0650
    elif hourly_rate <= 11.99:
        return 0.0800
    else:
        return 0.1000


def calculate_monthly_commission(hourly_rate: float, hours_worked: float) -> dict:
    """Calculate monthly commission for a referral."""
    commission_rate = calculate_commission_rate(hourly_rate)
    gross_revenue = hourly_rate * hours_worked
    commission = gross_revenue * commission_rate
    
    return {
        "hourly_rate": hourly_rate,
        "hours_worked": hours_worked,
        "gross_revenue": round(gross_revenue, 2),
        "commission_rate": f"{commission_rate * 100:.2f}%",
        "commission_amount": round(commission, 2)
    }


# Example
result = calculate_monthly_commission(12.00, 160)
# {
#     "hourly_rate": 12.00,
#     "hours_worked": 160,
#     "gross_revenue": 1920.00,
#     "commission_rate": "10.00%",
#     "commission_amount": 192.00
# }
```

### API Endpoints

```http
# Referrer Management
POST   /api/v1/referrers                    # Register as referrer
GET    /api/v1/referrers/me                 # Get my referrer profile
GET    /api/v1/referrers/me/dashboard       # Dashboard stats
GET    /api/v1/referrers/me/referrals       # My referrals
GET    /api/v1/referrers/me/commissions     # Commission history
GET    /api/v1/referrers/me/payouts         # Payout history
POST   /api/v1/referrers/me/payout-request  # Request payout

# Referral Tracking
POST   /api/v1/referrals                    # Record new referral
GET    /api/v1/referrals/{code}             # Get referral by code
PUT    /api/v1/referrals/{id}/activate      # Activate referral

# Client Intake
POST   /api/v1/clients/inquiry              # New client inquiry
POST   /api/v1/clients/needs-assessment     # Needs assessment
GET    /api/v1/clients/quote/{id}           # Get quote

# BPO Worker Portal
GET    /api/v1/workers/me                   # My profile
GET    /api/v1/workers/me/missions          # Available missions
POST   /api/v1/workers/missions/{id}/claim  # Claim mission
POST   /api/v1/workers/missions/{id}/complete # Complete mission
GET    /api/v1/workers/me/stats             # XP, level, earnings

# Mission Integration
POST   /api/v1/missions/bpo/create          # Create BPO mission
GET    /api/v1/missions/bpo/available       # Available BPO missions
POST   /api/v1/missions/bpo/{id}/assign     # Assign to worker
```

---

## 📊 Success Metrics

### Phase 1 (Month 1)
- [ ] Referrer portal live
- [ ] 10 active referrers onboarded
- [ ] 5 client placements made
- [ ] Commission tracking operational

### Phase 2 (Month 2-3)
- [ ] 50+ active referrers
- [ ] 25+ active placements
- [ ] $5K+ monthly commission payouts
- [ ] Missions integration live

### Phase 3 (Month 4-6)
- [ ] 200+ referrer network
- [ ] 100+ active placements
- [ ] $25K+ monthly revenue
- [ ] Hybrid AI+Human services launched

### Phase 4 (Month 6-12)
- [ ] 1000+ referrer network
- [ ] 500+ active placements
- [ ] $100K+ monthly revenue
- [ ] Global expansion beyond Philippines

---

## 🎯 Go-To-Market Strategy

### Target Referrers
1. **Existing Clients** - Happy customers become advocates
2. **HR Professionals** - Know companies needing staff
3. **Business Coaches** - Advise startups on scaling
4. **Digital Agencies** - Resell as white-label
5. **Tech Communities** - Indie hackers, startup founders
6. **Filipino Diaspora** - Connect homeland talent with global clients

### Target Clients
1. **Startups** - Need affordable support staff
2. **E-commerce** - Customer service scaling
3. **SaaS Companies** - Tech support, success
4. **Agencies** - White-label fulfillment
5. **Real Estate** - Lead handling, scheduling
6. **Healthcare** - Admin, scheduling, billing

### Marketing Channels (BRICK 2 Powered)
1. **Content Marketing** - AI-generated blog posts, case studies
2. **LinkedIn Outreach** - Apollo.io + Instantly.ai sequences
3. **Referral Campaigns** - Existing network activation
4. **Community Building** - missions portal, Discord/Slack
5. **Paid Ads** - GHL funnels for lead capture

---

## 🔄 Integration with BRICK 2

This vertical plugs directly into BRICK 2's core modules:

| BRICK 2 Module | BPO Vertical Usage |
|:---------------|:-------------------|
| GHL Hub (M1) | Client CRM, referrer tracking, email sequences |
| AI Tools (M2) | Content generation, lead qualification, chat |
| Lead Gen (M3) | Apollo.io for B2B prospects, outreach automation |
| Revenue (M4) | Commission tracking, attribution, forecasting |
| AI Chat (M5) | Initial client qualification, VA matching |
| BRICK 1 (M6) | Strategic optimization of pricing, placements |

---

## 💡 Competitive Advantages

1. **Hybrid AI+Human** - Not just humans, not just AI - the best of both
2. **Missions Gamification** - VAs level up, earn more, stay engaged
3. **Referral Network** - Distribution scales without proportional costs
4. **BRICK 2 Marketing** - AI-powered lead gen and conversion
5. **Filipino Talent Pool** - World-class English, cost-effective rates
6. **Quality Control** - AI monitors, humans deliver, quality assured

---

**Status:** 🔵 Spec Complete - Ready for Implementation
**Priority:** HIGH (Revenue Test Case for BRICK 2)
**First Target:** 10 referrers, 5 placements in Month 1

---

*"Referrers earn recurring income. VAs level up their careers. Clients get hybrid AI+Human power. Everyone wins."*

