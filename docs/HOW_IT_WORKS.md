# How Genesis & Mission Hub Integration Works

## The Big Picture

You have a plan with todos. You want to delegate some of them to assistants. This system makes that happen automatically, securely, and trackably.

**The Flow:** Plan → Mission → Email → Delegate → Assistant Enrolls → Works → Completes → Status Syncs Back

---

## Step-by-Step: How It All Works

### Step 1: You Create a Plan

You use the `mcp_create_plan` tool (or create a plan manually) with todos:

```json
{
  "plan_id": "connective-events-plan",
  "todos": [
    {
      "id": "st-george-venue-research",
      "content": "Research and contact St. George Opera House..."
    }
  ]
}
```

**What happens:** Plan exists, todos are pending.

---

### Step 2: Plan-to-Mission Bridge Converts Todos to Missions

A new bridge service watches for plans and converts todos into missions:

**Bridge Service** (`SERVICES/plan-mission-bridge/`):
- Receives: Plan with todos
- Converts: Each todo → Mission Hub mission format
- Sends: `POST http://198.54.123.234:8700/api/missions`

**Mission Created:**
```json
{
  "id": "M-PLAN-001",
  "title": "Contact St. George Opera House",
  "description": "Research and contact...",
  "type": "human_only",
  "priority": "high",
  "plan_id": "connective-events-plan",
  "todo_id": "st-george-venue-research",
  "status": "pending"
}
```

**What happens:** Mission now exists in Mission Hub, linked to your plan.

---

### Step 3: Mission Hub Sends You an Email

Mission Hub has an email module that sends notifications:

**Email Module** (`SERVICES/mission-hub/email_notifications.py`):
- Detects: New mission created
- Uses: Cortex Mail (port 8860) to send email
- Sends to: `james@fullpotential.com`

**Email Content:**
```
Subject: New Mission: Contact St. George Opera House

Mission: Contact St. George Opera House
Description: Research and contact St. George Opera House...

[Delegate] [Claim] [Complete]
```

**What happens:** You get an email with action buttons.

---

### Step 4: You Click "Delegate"

You click the "Delegate" button in the email:

**Email Action Handler:**
- Button links to: `https://team-hub.fullpotential.ai/delegate?mission=M-PLAN-001`
- Opens: Team Hub delegation page
- Shows: List of assistants or "Create New Assistant"

**What happens:** Team Hub delegation page opens.

---

### Step 5: Team Hub Generates Enrollment Link

In Team Hub, you select an assistant (or create new):

**Team Hub** (`SERVICES/team-hub/app/main.py`):
- Generates: Secure enrollment link
- Format: `https://team-hub.fullpotential.ai/enroll/{encrypted-token}`
- Token contains:
  - Encrypted enrollment key: `enroll-1c77b8ce63c4`
  - Mission ID: `M-PLAN-001`
  - Expiration: 24 hours

**Enrollment Link Generated:**
```
https://team-hub.fullpotential.ai/enroll/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**What happens:** Secure link is generated and sent to assistant (via email/SMS/chat).

---

### Step 6: Assistant Clicks Enrollment Link

Assistant receives link and clicks it:

**Enrollment Page** (`SERVICES/team-hub/app/static/enroll.html`):
- Shows: Mission details
- Form: Assistant name, contact info
- Button: "Enroll and Get Agent Key"

**What happens:** Assistant fills form and clicks enroll.

---

### Step 7: Genesis Enrolls Assistant and Generates Agent Key

Team Hub sends enrollment request to Genesis:

**Team Hub → Genesis:**
```http
POST http://198.54.123.234:8150/auth/enroll
{
  "agent_name": "assistant-name",
  "enrollment_key": "enroll-1c77b8ce63c4"
}
```

**Genesis Response:**
```json
{
  "agent_key": "agent-550e8400-e29b-41d4-a716-446655440000",
  "agent_name": "assistant-name",
  "universe_map": {
    "servers": [...],
    "services": [...],
    "ai_brain": "http://162.0.208.88:8101"
  }
}
```

**What happens:** Assistant now has an agent key and is registered in Genesis.

---

### Step 8: Assistant Claims Mission in Mission Hub

Assistant uses agent key to claim the mission:

**Assistant → Mission Hub:**
```http
POST http://198.54.123.234:8700/api/missions/M-PLAN-001/claim
Headers:
  Authorization: Bearer agent-550e8400-e29b-41d4-a716-446655440000
```

**Mission Hub Response:**
```json
{
  "mission_id": "M-PLAN-001",
  "status": "claimed",
  "claimed_by": "assistant-name",
  "claimed_at": "2024-12-01T..."
}
```

**What happens:** Mission is now claimed by assistant, status updated.

---

### Step 9: Assistant Works on Mission

Assistant does the work:
- Researches St. George Opera House
- Finds contact information
- Makes initial contact
- Documents results

**What happens:** Work is in progress.

---

### Step 10: Assistant Completes Mission

Assistant updates mission status:

**Assistant → Mission Hub:**
```http
PATCH http://198.54.123.234:8700/api/missions/M-PLAN-001
Headers:
  Authorization: Bearer agent-550e8400-e29b-41d4-a716-446655440000
Body:
{
  "status": "completed",
  "completion_notes": "Contacted venue, available dates: ..."
}
```

**What happens:** Mission marked as completed in Mission Hub.

---

### Step 11: Status Syncs Back to Plan

Mission Hub sends webhook to bridge service:

**Mission Hub → Bridge:**
```http
POST http://bridge-service/api/webhooks/mission-completed
{
  "mission_id": "M-PLAN-001",
  "plan_id": "connective-events-plan",
  "todo_id": "st-george-venue-research",
  "status": "completed"
}
```

**Bridge → Plan:**
- Updates: Plan todo status to "completed"
- Links: Mission results to plan todo

**What happens:** Your plan now shows the todo as completed.

---

### Step 12: You Get Completion Notification

Mission Hub sends completion email:

**Email:**
```
Subject: Mission Completed: Contact St. George Opera House

Mission completed by: assistant-name
Completion notes: Contacted venue, available dates: ...

[View Mission] [View Plan]
```

**What happens:** You're notified that the mission is done.

---

## The Components Explained

### Genesis (Port 8150)
**Role:** Authentication & Registry
- **What it does:** Enrolls agents, generates keys, tracks who's who
- **Key concept:** "The Source Point" - where agents are born
- **Current state:** 31 agents enrolled, 21 services registered

### Mission Hub (Port 8700)
**Role:** Mission Management
- **What it does:** Tracks missions, manages claims, updates status
- **Key concept:** Where work happens and progress is tracked
- **Current state:** Running, has `/api/missions` endpoint

### Team Hub (Port 8355)
**Role:** Human-Agent Bridge
- **What it does:** Delegation interface, enrollment link generation
- **Key concept:** Where humans meet agents
- **Current state:** Has Genesis tab, needs enrollment link generator

### Plan-to-Mission Bridge (New Service)
**Role:** Plan-Mission Translator
- **What it does:** Converts plan todos to missions, syncs status back
- **Key concept:** The bridge between planning and execution
- **Status:** Needs to be created

### Cortex Mail (Port 8860)
**Role:** Email Routing
- **What it does:** Sends emails, handles email actions
- **Key concept:** Notification layer
- **Current state:** Running, ready to use

---

## Security Flow

**How keys work:**

1. **Enrollment Key** (`enroll-1c77b8ce63c4`)
   - Master key for initial registration
   - Stored securely in Genesis
   - Used once per assistant enrollment

2. **Agent Key** (`agent-{uuid}`)
   - Personal key for each assistant
   - Generated by Genesis after enrollment
   - Used for all mission operations
   - Scoped to specific permissions

3. **Mission Access**
   - Assistant uses agent key to claim missions
   - Mission Hub verifies key with Genesis
   - Only enrolled agents can claim missions

**Security features:**
- Keys encrypted in transit
- Enrollment links expire (24 hours)
- Agent keys tied to specific permissions
- All actions logged and auditable

---

## Real-World Example

**Scenario:** You want to research venues for an event.

1. **You create plan:** "Event Planning Plan" with todo "Research venues"
2. **Bridge converts:** Todo → Mission "Research Event Venues"
3. **Email arrives:** "New Mission: Research Event Venues [Delegate]"
4. **You delegate:** Click Delegate → Select assistant → Link sent
5. **Assistant enrolls:** Clicks link → Gets agent key → Registered
6. **Assistant claims:** Uses key → Claims mission → Starts research
7. **Work happens:** Assistant researches, contacts venues, documents
8. **Mission completes:** Assistant marks done → Status updates
9. **Plan syncs:** Your plan todo shows "completed"
10. **You're notified:** "Mission Completed: Research Event Venues"

**Result:** You delegated, assistant worked, mission completed, plan updated - all automatically tracked.

---

## What Makes This Powerful

1. **Automatic Conversion:** Plans → Missions (no manual work)
2. **Secure Delegation:** Enrollment links with expiration
3. **Tracked Execution:** Every step is logged and visible
4. **Status Sync:** Plan and mission stay in sync
5. **Email Integration:** Notifications keep you informed
6. **Scalable:** Works with any number of assistants and missions

---

## Current Status

**✅ Already Working:**
- Genesis (authentication & registry)
- Mission Hub (mission management)
- Team Hub (delegation interface)
- Cortex Mail (email routing)

**🔨 Needs Building:**
- Plan-to-Mission Bridge service
- Enrollment link generator in Team Hub
- Email notification module in Mission Hub
- Status sync between plans and missions

**🎯 End Goal:**
- Create plan → Missions appear → Delegate → Assistant works → Plan updates automatically

---

## Questions?

This system connects:
- **Planning** (your plans)
- **Execution** (missions)
- **Delegation** (Team Hub)
- **Authentication** (Genesis)
- **Notification** (email)

All working together to turn your intentions into completed actions.







