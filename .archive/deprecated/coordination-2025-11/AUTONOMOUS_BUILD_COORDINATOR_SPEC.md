# Autonomous Build Coordinator - SPEC
**Created:** 2025-11-15
**By:** Session #12 (Chief Architect)
**Purpose:** Move specs through assembly line automatically - no human intervention needed

---

## 🎯 Problem Statement

**Current State:** Services get stuck at each phase waiting for manual intervention
- SPECS written → needs someone to START building
- BUILD complete → needs someone to TEST it
- TESTS passing → needs someone to DEPLOY it
- **Result:** Human has to keep pushing things forward or progress stops

**Desired State:** Services move through assembly line automatically
- SPECS complete → Auto-assigned to builder → BUILD starts
- BUILD complete → Auto-tested → Tests run automatically
- TESTS passing → Auto-deployed → Production automatically
- **Result:** Specs → Production with ZERO manual intervention

---

## 🏗️ Architecture

### The Autonomous Loop

```
┌─────────────────────────────────────────────────────────────┐
│          Autonomous Build Coordinator                       │
│                (Runs every 60 seconds)                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. SCAN Phase                                              │
│     └─ Scan all SERVICES/ directories                      │
│        └─ Detect phase: SPECS/BUILD/TEST/PRODUCTION        │
│           └─ Check what's blocking progress                │
│                                                             │
│  2. ASSIGN Phase                                            │
│     └─ Match work to available sessions                    │
│        ├─ Check claude_sessions.json for capabilities      │
│        ├─ Assign SPECS → "architect" sessions              │
│        ├─ Assign BUILD → "builder" sessions                │
│        └─ Assign DEPLOY → "devops" sessions                │
│                                                             │
│  3. EXECUTE Phase                                           │
│     └─ Trigger assigned work                               │
│        ├─ Send message to session                          │
│        ├─ Create work ticket in queue                      │
│        └─ Monitor progress via heartbeats                  │
│                                                             │
│  4. VERIFY Phase                                            │
│     └─ Run automated checks                                │
│        ├─ SPECS: completeness check                        │
│        ├─ BUILD: run tests                                 │
│        ├─ TEST: verification protocol                      │
│        └─ PRODUCTION: health check                         │
│                                                             │
│  5. ADVANCE Phase                                           │
│     └─ Move to next phase if ready                         │
│        ├─ SPECS → BUILD (when specs complete)              │
│        ├─ BUILD → TEST (when code done)                    │
│        ├─ TEST → PRODUCTION (when tests pass)              │
│        └─ PRODUCTION → MONITORING (when deployed)          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 Detection Logic

### How to Know What Phase a Service Is In

```python
def detect_service_phase(service_path: str) -> str:
    """Detect what phase a service is currently in"""

    has_spec = exists(f"{service_path}/SPEC.md")
    has_build = exists(f"{service_path}/BUILD/")
    has_tests = exists(f"{service_path}/BUILD/tests/")
    has_production = exists(f"{service_path}/PRODUCTION/")

    # Read README to check status
    readme = read(f"{service_path}/README.md")

    if not has_spec:
        return "NEEDS_SPEC"

    if has_spec and not spec_is_complete(service_path):
        return "SPEC_INCOMPLETE"

    if has_spec and not has_build:
        return "READY_FOR_BUILD"  # ← AUTO-ASSIGN TO BUILDER

    if has_build and build_in_progress(readme):
        return "BUILD_IN_PROGRESS"  # ← MONITOR

    if has_build and not tests_exist(service_path):
        return "NEEDS_TESTS"  # ← AUTO-ASSIGN TEST WRITING

    if has_tests and not tests_passing(service_path):
        return "TESTS_FAILING"  # ← AUTO-ASSIGN FIX

    if has_tests and tests_passing(service_path) and not has_production:
        return "READY_FOR_DEPLOY"  # ← AUTO-ASSIGN TO DEVOPS

    if has_production:
        return "PRODUCTION"  # ← MONITORING MODE

    return "UNKNOWN"
```

---

## 🤖 Auto-Assignment Logic

### Match Work to Available Sessions

```python
class WorkMatcher:
    """Match work to sessions based on capabilities"""

    def assign_work(self, service: str, phase: str) -> Optional[str]:
        """Find best session for this work"""

        # Load available sessions
        sessions = self.get_available_sessions()

        # Match based on phase
        if phase == "READY_FOR_BUILD":
            # Find session with "builder" capability
            builders = [s for s in sessions if "builder" in s['capabilities']]
            if builders:
                best = self.score_sessions(builders, criteria="build_speed")
                return best['session_id']

        elif phase == "NEEDS_TESTS":
            # Find session with "tester" capability
            testers = [s for s in sessions if "tester" in s['capabilities']]
            if testers:
                return testers[0]['session_id']

        elif phase == "READY_FOR_DEPLOY":
            # Find session with "devops" capability
            devops = [s for s in sessions if "devops" in s['capabilities']]
            if devops:
                return devops[0]['session_id']

        return None  # No available session

    def get_available_sessions(self) -> List[Dict]:
        """Get sessions that are idle/available"""
        sessions = load_json("claude_sessions.json")

        available = []
        for session in sessions.values():
            if session['status'] == 'active':
                # Check if idle (no current work)
                if not session.get('current_work'):
                    available.append(session)

        return available
```

---

## 🚀 Auto-Execution

### How Work Gets Triggered

```python
async def trigger_build(service_name: str, assigned_session: str):
    """Automatically start build for a service"""

    # 1. Create work ticket
    work_ticket = {
        "id": generate_id(),
        "service": service_name,
        "phase": "BUILD",
        "assigned_to": assigned_session,
        "spec_file": f"/Users/jamessunheart/Development/SERVICES/{service_name}/SPEC.md",
        "deadline": "24 hours",
        "created_at": now()
    }

    # 2. Save to work queue
    save_json("work_queue.json", work_ticket)

    # 3. Send message to assigned session
    await send_message(
        to=assigned_session,
        subject=f"BUILD ASSIGNED: {service_name}",
        body=f"""
        You have been assigned to build: {service_name}

        SPEC: /Users/jamessunheart/Development/SERVICES/{service_name}/SPEC.md
        DEADLINE: 24 hours

        INSTRUCTIONS:
        1. Read SPEC.md thoroughly
        2. Follow ASSEMBLY_LINE_SOP.md
        3. Create BUILD/ directory structure
        4. Implement according to spec
        5. Write tests (>80% coverage)
        6. Update README with progress
        7. Broadcast when complete

        START NOW.
        """,
        priority="high"
    )

    # 4. Update service README
    update_readme(service_name, f"🚧 BUILD IN PROGRESS by {assigned_session}")

    # 5. Log assignment
    log(f"✅ Auto-assigned {service_name} BUILD to {assigned_session}")
```

---

## ✅ Auto-Verification

### Automated Quality Checks

```python
class AutoVerifier:
    """Run verification checks automatically"""

    async def verify_spec(self, service: str) -> bool:
        """Check if SPEC is complete"""
        spec_path = f"SERVICES/{service}/SPEC.md"
        spec_content = read(spec_path)

        required_sections = [
            "## Purpose",
            "## Requirements",
            "## API Specs",
            "## Dependencies",
            "## Success Criteria"
        ]

        for section in required_sections:
            if section not in spec_content:
                log(f"❌ {service}: Missing section: {section}")
                return False

        log(f"✅ {service}: SPEC complete")
        return True

    async def verify_build(self, service: str) -> bool:
        """Check if BUILD is ready for testing"""
        build_path = f"SERVICES/{service}/BUILD"

        # Check required files exist
        required = [
            "src/main.py",
            "requirements.txt",
            "Dockerfile",
            ".env.example"
        ]

        for file in required:
            if not exists(f"{build_path}/{file}"):
                log(f"❌ {service}: Missing {file}")
                return False

        log(f"✅ {service}: BUILD structure complete")
        return True

    async def verify_tests(self, service: str) -> bool:
        """Run tests and check if passing"""
        build_path = f"SERVICES/{service}/BUILD"

        # Run pytest
        result = subprocess.run(
            ["pytest", "tests/", "-v", "--cov=src", "--cov-report=term"],
            cwd=build_path,
            capture_output=True
        )

        if result.returncode == 0:
            log(f"✅ {service}: All tests passing")
            return True
        else:
            log(f"❌ {service}: Tests failing")
            log(result.stdout.decode())
            return False

    async def verify_production(self, service: str) -> bool:
        """Check if production deployment is healthy"""
        # Get service port from SPEC
        port = get_service_port(service)

        # Health check
        try:
            response = httpx.get(f"http://localhost:{port}/health", timeout=5)
            if response.status_code == 200:
                log(f"✅ {service}: Production healthy")
                return True
        except:
            log(f"❌ {service}: Production health check failed")
            return False
```

---

## 🔄 The Complete Autonomous Loop

### Main Coordinator Loop (Runs every 60 seconds)

```python
class AutonomousBuildCoordinator:
    """Moves services through assembly line automatically"""

    async def run(self):
        """Main coordination loop"""

        while True:
            log("🔄 Starting coordination cycle...")

            # 1. SCAN all services
            services = self.scan_services()

            for service in services:
                phase = self.detect_phase(service)
                log(f"📍 {service}: {phase}")

                # 2. AUTO-ADVANCE based on phase
                if phase == "READY_FOR_BUILD":
                    await self.auto_start_build(service)

                elif phase == "BUILD_COMPLETE":
                    await self.auto_run_tests(service)

                elif phase == "TESTS_PASSING":
                    await self.auto_deploy(service)

                elif phase == "PRODUCTION":
                    await self.auto_monitor(service)

            # 3. Sleep for 60 seconds
            await asyncio.sleep(60)

    async def auto_start_build(self, service: str):
        """Automatically assign and start build"""

        # Find available builder
        builder = self.work_matcher.assign_work(service, "READY_FOR_BUILD")

        if builder:
            await self.trigger_build(service, builder)
            log(f"✅ Auto-started BUILD for {service} (assigned to {builder})")
        else:
            log(f"⏳ {service}: No available builders, queued")

    async def auto_run_tests(self, service: str):
        """Automatically run tests when build complete"""

        log(f"🧪 Running tests for {service}...")

        tests_pass = await self.verifier.verify_tests(service)

        if tests_pass:
            log(f"✅ {service}: Tests passing, ready for deploy")
            # Update phase
            self.mark_ready_for_deploy(service)
        else:
            log(f"❌ {service}: Tests failing, assigning fix")
            # Auto-assign to fixer
            await self.auto_fix_tests(service)

    async def auto_deploy(self, service: str):
        """Automatically deploy when tests pass"""

        # Find available devops session
        devops = self.work_matcher.assign_work(service, "READY_FOR_DEPLOY")

        if devops:
            await self.trigger_deploy(service, devops)
            log(f"✅ Auto-deploying {service} (assigned to {devops})")
        else:
            log(f"⏳ {service}: No available devops, queued")

    async def auto_monitor(self, service: str):
        """Monitor production service health"""

        healthy = await self.verifier.verify_production(service)

        if not healthy:
            log(f"🚨 {service}: Production unhealthy, auto-recovering")
            await self.auto_recover(service)
```

---

## 📊 Dashboard Integration

### Real-Time Assembly Line Visualization

```html
<!-- Dashboard at fullpotential.com/dashboard/assembly-line -->
<div class="assembly-line-dashboard">
    <h1>🏭 Autonomous Assembly Line</h1>

    <!-- Pipeline View -->
    <div class="pipeline">
        <div class="phase">
            <h3>📋 SPECS</h3>
            <div class="services">
                <!-- Services in SPEC phase -->
                <div class="service ready">
                    <span class="name">email-automation-system</span>
                    <span class="status">✅ SPEC Complete</span>
                    <button>→ Auto-Assign Build</button>
                </div>
            </div>
        </div>

        <div class="phase">
            <h3>🔨 BUILD</h3>
            <div class="services">
                <!-- Services being built -->
                <div class="service in-progress">
                    <span class="name">content-generation-engine</span>
                    <span class="status">🚧 Building (Session #11)</span>
                    <span class="progress">45%</span>
                </div>
            </div>
        </div>

        <div class="phase">
            <h3>🧪 TEST</h3>
            <div class="services">
                <!-- Services being tested -->
                <div class="service testing">
                    <span class="name">reddit-auto-responder</span>
                    <span class="status">🧪 Tests Running...</span>
                    <span class="progress">12/15 passing</span>
                </div>
            </div>
        </div>

        <div class="phase">
            <h3>🚀 PRODUCTION</h3>
            <div class="services">
                <!-- Services deployed -->
                <div class="service deployed">
                    <span class="name">i-match</span>
                    <span class="status">✅ Production (Healthy)</span>
                    <span class="uptime">99.9%</span>
                </div>
            </div>
        </div>
    </div>

    <!-- Metrics -->
    <div class="metrics">
        <div class="metric">
            <span class="label">Cycle Time</span>
            <span class="value">18 hours</span>
            <span class="trend">↓ 40% from last week</span>
        </div>
        <div class="metric">
            <span class="label">Auto-Assignments</span>
            <span class="value">23 today</span>
        </div>
        <div class="metric">
            <span class="label">Services Deployed</span>
            <span class="value">5 this week</span>
        </div>
    </div>
</div>
```

---

## 🎯 Success Criteria

### When This Is Working:

1. ✅ **Zero Manual Intervention**
   - Spec written → Automatically assigned to builder
   - Build complete → Tests run automatically
   - Tests pass → Deployment happens automatically

2. ✅ **Continuous Flow**
   - Services move through pipeline at steady pace
   - No services "stuck" waiting for attention
   - Average cycle time: SPEC → PRODUCTION in <24 hours

3. ✅ **Quality Maintained**
   - All services pass verification at each phase
   - No shortcuts (tests must pass before deploy)
   - Production services are healthy

4. ✅ **Visibility**
   - Dashboard shows real-time pipeline status
   - Any session can see what's in progress
   - Metrics track velocity and quality

---

## 🚀 Deployment Plan

### Phase 1: Build the Coordinator (4 hours)
```bash
# Create autonomous-build-coordinator service
cd /Users/jamessunheart/Development/SERVICES
mkdir -p autonomous-build-coordinator/BUILD/src
cd autonomous-build-coordinator

# Write coordinator code
# - Service scanner
# - Phase detector
# - Work matcher
# - Auto-executor
# - Verifier
# - Main loop
```

### Phase 2: Integrate with Existing System (2 hours)
- Read claude_sessions.json for available sessions
- Send messages via session-send-message.sh
- Update SERVICE_REGISTRY.json
- Log to coordination dashboard

### Phase 3: Deploy and Monitor (1 hour)
- Deploy coordinator to server (port 8900)
- Start coordination loop
- Monitor first auto-assignment
- Verify complete cycle works

### Phase 4: Dashboard (1 hour)
- Create real-time assembly line dashboard
- WebSocket updates for live progress
- Metrics and velocity tracking

**Total Time:** 8 hours to full automation

---

## 💡 Key Insight

**The coordinator doesn't BUILD services - it COORDINATES builders.**

```
Current: Human sees spec → manually assigns → manually checks → manually deploys
With Coordinator: Spec written → AUTO everything else

Current: 5 specs sitting ready → nothing happening
With Coordinator: 5 specs → 5 builders auto-assigned → all building simultaneously
```

**Result:**
- Specs don't sit idle
- Builds don't wait for testing
- Tested code doesn't wait for deployment
- **Everything flows automatically**

---

## 🔗 Integration with My Other Specs

Once the coordinator is running:

1. **orchestrator-unified** (my spec) coordinates CLAUDE SESSIONS
2. **autonomous-build-coordinator** (this spec) coordinates THE ASSEMBLY LINE
3. Together: Sessions work on tasks assigned by orchestrator, while coordinator ensures assembly line keeps moving

**Synergy:**
- Orchestrator: "Session #5, you're free, here's optimal work"
- Coordinator: "Service X needs building, assigning to available builder"
- Session #5: Gets assigned, builds, tests run automatically, deploys automatically

---

## ✅ Validation

**This solves the problem:** "Right now I have to keep moving it forward or it stops"

**Before:** You manually push each service forward
**After:** Coordinator detects phase, auto-assigns work, verifies quality, advances automatically

**Your role:** Write specs, review quality, make strategic decisions
**Coordinator's role:** Keep the assembly line moving 24/7 without stopping

---

**Session #12 recommends: Build THIS coordinator FIRST (even before orchestrator-unified)**

**Why:** This unblocks the entire system immediately. Every spec becomes a self-executing build.

**Build time:** 8 hours
**Impact:** INFINITE (every future build flows automatically)
**ROI:** ∞
