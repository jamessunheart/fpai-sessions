# 🎯 MISSION M014: Spec for Coordination Hub

**Status:** 🟡 OPEN  
**Created:** 2025-11-23  
**Estimated Time:** TBD (see spec below)  
**Difficulty:** TBD (see spec below)

---

## 🚀 QUICK START FOR BUILDERS

**This is a ready-to-code mission.** Everything you need is in this file.

### 📦 STARTER KIT

Before you start coding, set up your foundation:

1. **Create a New Repository**
   ```bash
   mkdir mission-m014
   cd mission-m014
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
   source venv/bin/activate  # On Windows: venv\Scripts\activate
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
   - Include: Your name, Mission ID (M014), and any notes

---

## 📝 TECHNICAL SPECIFICATION

# Coordination Hub

- **Priority:** P1 (High/Core)
- **Constitution Principle:** **Consciousness over Computation**
- **Regenerative Impact:** Serves as the central nervous system for multi-agent collaboration, ensuring all droplets act in harmony rather than isolation. It transforms disconnected tasks into a cohesive, conscious movement.

## 1. 📋 OVERVIEW
The Coordination Hub (`coordination-hub`) is the service that manages the high-level "Sessions" and "Missions" of the system. Unlike the `orchestrator` (which handles low-level task routing), the Hub maintains the "state of the world," tracks long-running goals, and facilitates consensus between different AI agents/sessions. It implements the protocols defined in `MULTI_SESSION_COORDINATION.md`.

- **Business Value:** Prevents work duplication and strategic drift across autonomous agents.
- **User Impact:** Seamless experience where different parts of the system "know" about each other.
- **Timeline:** 3-4 days.
- **Complexity:** High (State management, Concurrency).

## 2. 🎯 REQUIREMENTS
- **Functional:**
  - Track active "Sessions" (AI instances currently working).
  - Manage "Claims" on resources (prevent two agents from editing the same file).
  - Store and serve the "SSOT" (Single Source of Truth) state.
  - Broadcast "Heartbeats" and system-wide events.
  - Provide an API for agents to register, claim work, and update status.
- **Non-Functional:**
  - UDC Compliant.
  - High Availability: Must be always-on; if Hub dies, coordination breaks.
  - Persistence: State must survive restarts (Redis + DB).

## 3. 🏗️ ARCHITECTURE
- **Components:**
  - **Session Manager:** Registry of active agents.
  - **Lock Manager:** Distributed locking mechanism (Redis).
  - **Event Bus Interface:** Interface to `nexus-event-bus`.
  - **State Store:** Persistent storage for SSOT documents.
- **Data Flow:**
  1. Agent starts -> Calls `POST /sessions/register`.
  2. Agent wants to edit file -> Calls `POST /locks/acquire`.
  3. Hub checks Redis -> Grants or Denies lock.
  4. Agent completes work -> Calls `POST /locks/release`.
  5. Hub updates SSOT -> Broadcasts "Work Complete" event via Nexus.
- **Integration:**
  - `registry` (discovery).
  - `nexus-event-bus` (pub/sub).
  - Redis (fast locking).

## 4. 🔌 API SPECIFICATION
Base URL: `/api/v1`

- `POST /sessions/register`: Register a new agent session.
- `POST /sessions/heartbeat`: Keep-alive signal.
- `GET /sessions`: List active sessions.
- `POST /claims`: Acquire a lock on a resource (file, task).
- `DELETE /claims/{id}`: Release a lock.
- `GET /ssot`: Get current system state JSON.
- `POST /ssot`: Update system state (delta or full).

**UDC Endpoints:**
- `GET /health`
- `GET /capabilities`
- `GET /state`
- `GET /dependencies`
- `POST /message`

## 5. 💾 DATABASE DESIGN
**Tables (PostgreSQL):**

- **sessions**
  - `id` (UUID, PK)
  - `agent_id` (String)
  - `type` (String) - e.g., "builder", "planner"
  - `started_at` (Timestamp)
  - `last_heartbeat` (Timestamp)
  - `status` (Enum: ACTIVE, IDLE, DISCONNECTED)

- **claims**
  - `id` (UUID, PK)
  - `resource_uri` (String) - Unique identifier for resource
  - `session_id` (UUID, FK)
  - `expires_at` (Timestamp)
  - `created_at` (Timestamp)

- **state_snapshots**
  - `id` (Integer, PK)
  - `payload` (JSONB) - Full SSOT state
  - `created_at` (Timestamp)

**Redis Keys:**
- `lock:{resource_uri}` -> `session_id` (TTL set to expiration)

## 6. 🎨 UI/UX REQUIREMENTS
- **Visualization:** Dashboard page showing active nodes (sessions) and locked resources (visualized as "busy" indicators).

## 7. 🔐 SECURITY CONSIDERATIONS
- **Identity:** Agents must sign requests with a session key (generated at startup).
- **Lock Safety:** Fencing tokens to prevent zombie processes from holding locks forever (TTL is mandatory).
- **Integrity:** SSOT updates must be versioned to prevent race conditions (Optimistic Concurrency Control).

## 8. ✅ TESTING STRATEGY
- **Unit Tests:**
  - Test locking logic (acquire/release/expiry).
  - Test SSOT version merging.
- **Integration Tests:**
  - Simulate multiple concurrent agents trying to claim the same resource.
  - Verify heartbeat timeout logic.
- **Stress Test:**
  - 100 simultaneous sessions sending heartbeats.

## 9. 📦 DEPLOYMENT PLAN
- **Docker:** Python 3.11 slim.
- **Dependencies:** Redis container required.
- **Env Vars:**
  - `DATABASE_URL`
  - `REDIS_URL`
  - `NEXUS_URL`

## 10. 🛠️ BUILDER INSTRUCTIONS
1. Clone repo and `cd coordination-hub`.
2. `python3 -m venv venv && source venv/bin/activate`.
3. `pip install -r requirements.txt`.
4. `docker-compose up -d db redis` (Need Redis!).
5. `alembic upgrade head`.
6. `uvicorn app.main:app --reload`.
7. Test locking with `curl`.

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
- [ ] UDC endpoints implemented
- [ ] README.md with setup instructions
- [ ] Environment variables documented
- [ ] Local testing successful
- [ ] Code committed to repository

---

## 🎓 WHAT YOU'LL LEARN
By completing this mission:
- Distributed system coordination.
- Locking patterns (Redis).
- Real-time state management.
- Building control planes for AI agents.

---

**Original Idea:** "Spec for Coordination Hub"  
**Mission ID:** M014  
**Generated:** 2025-11-23

🚀 **Let's build something awesome!**

