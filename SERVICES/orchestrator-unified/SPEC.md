# 🧠 Unified Orchestrator - Technical Specification

**Service Name:** `orchestrator-unified`
**Purpose:** Central brain coordinating all Claude sessions as one distributed intelligence
**Priority:** CRITICAL (Week 1 - enables all coordination)
**Port:** 8600

---

## 🎯 What It Does

**Transforms:** 12 independent Claude sessions
**Into:** 1 unified superintelligent swarm

**Core Functions:**
1. **Session Registry** - Know all active sessions
2. **Work Distribution** - Assign tasks optimally
3. **State Management** - Single source of truth
4. **Load Balancing** - Prevent overload, use idle capacity
5. **Collaboration** - Multiple sessions on complex tasks

---

## 🏗️ Architecture

```
orchestrator-unified/
├── app/
│   ├── main.py                 # FastAPI app
│   ├── models/
│   │   ├── session.py          # Session model
│   │   ├── task.py             # Task model
│   │   └── assignment.py       # Assignment model
│   ├── core/
│   │   ├── coordinator.py      # Main coordination logic
│   │   ├── assignment.py       # Task assignment algorithm
│   │   └── scheduler.py        # APScheduler setup
│   ├── api/
│   │   ├── sessions.py         # Session endpoints
│   │   ├── work.py             # Work endpoints
│   │   └── swarm.py            # Swarm status endpoints
│   ├── services/
│   │   ├── session_manager.py
│   │   ├── work_queue.py
│   │   └── capability_matcher.py
│   └── utils/
│       ├── redis_client.py
│       └── metrics.py
├── web/
│   ├── dashboard.html          # Real-time swarm dashboard
│   └── static/
├── tests/
├── docker-compose.yml
└── requirements.txt
```

---

## 📊 Database Schema

### Redis Data Structures

```python
# Session Registry
session:{session_id} = {
    "id": "session-1763233940",
    "status": "idle" | "busy" | "offline",
    "capabilities": ["build", "architect", "marketing"],
    "current_task_id": null | "build-001",
    "registered_at": "2025-11-15T22:00:00Z",
    "last_heartbeat": "2025-11-15T22:05:00Z",
    "performance": {
        "tasks_completed": 15,
        "avg_task_time": 120,
        "success_rate": 0.95,
        "score": 0.92
    }
}

# Active Sessions Set
sessions:active = ["session-123", "session-456", ...]

# Work Queue (Sorted Set by priority)
work:queue = {
    "build-001": 10,  # priority score
    "marketing-005": 8,
    "research-003": 5
}

# Task Details
task:{task_id} = {
    "id": "build-001",
    "type": "build",
    "priority": 10,
    "status": "pending" | "assigned" | "in_progress" | "completed" | "failed",
    "assigned_to": null | "session-xxx",
    "required_capability": "build",
    "estimated_hours": 14,
    "dependencies": ["task-xxx"],
    "created_at": "2025-11-15T20:00:00Z",
    "assigned_at": null,
    "completed_at": null,
    "result": {}
}

# Assignments (Session → Tasks)
session:{session_id}:tasks = ["task-001", "task-002"]

# Task History
task:history:{task_id} = [{
    "session_id": "session-123",
    "action": "assigned" | "started" | "completed" | "failed",
    "timestamp": "2025-11-15T22:00:00Z",
    "details": {}
}]

# Global Metrics
metrics:global = {
    "total_sessions": 12,
    "active_sessions": 8,
    "idle_sessions": 3,
    "busy_sessions": 5,
    "offline_sessions": 1,
    "tasks_pending": 12,
    "tasks_in_progress": 5,
    "tasks_completed": 47,
    "avg_session_utilization": 0.75
}

# Knowledge Base
knowledge:{topic} = {
    "topic": "email-automation-architecture",
    "content": {...},
    "version": 3,
    "updated_by": "session-123",
    "updated_at": "2025-11-15T22:00:00Z"
}
```

---

## 🔌 API Endpoints

### Session Management

```python
@app.post("/session/register")
async def register_session(session_data: SessionRegistration):
    """
    Register new session with orchestrator

    Request:
    {
        "session_id": "session-1763233940",
        "capabilities": ["build", "architect"],
        "max_concurrent_tasks": 1
    }

    Response:
    {
        "status": "registered",
        "session_id": "session-1763233940",
        "assigned_task": null | {...}
    }
    """

@app.post("/session/heartbeat")
async def heartbeat(heartbeat_data: Heartbeat):
    """
    Session sends heartbeat every 60 seconds

    Request:
    {
        "session_id": "session-123",
        "status": "idle" | "busy",
        "current_task": null | "task-001",
        "progress": 0.0-1.0
    }

    Response:
    {
        "acknowledged": true,
        "new_assignment": null | {...}
    }
    """

@app.post("/session/deregister")
async def deregister_session(session_id: str):
    """Gracefully deregister session"""
```

### Work Management

```python
@app.get("/work/request")
async def request_work(session_id: str):
    """
    Session requests work assignment

    Response:
    {
        "task": {
            "id": "build-001",
            "type": "build",
            "spec": {...},
            "priority": 10
        }
    } | {"task": null}
    """

@app.post("/work/claim")
async def claim_task(claim: TaskClaim):
    """
    Session claims specific task

    Request:
    {
        "session_id": "session-123",
        "task_id": "build-001"
    }
    """

@app.post("/work/update")
async def update_task_progress(update: TaskUpdate):
    """
    Report task progress

    Request:
    {
        "session_id": "session-123",
        "task_id": "build-001",
        "progress": 0.45,
        "status": "in_progress",
        "details": "Completed SendGrid integration"
    }
    """

@app.post("/work/complete")
async def complete_task(completion: TaskCompletion):
    """
    Mark task as complete

    Request:
    {
        "session_id": "session-123",
        "task_id": "build-001",
        "status": "completed" | "failed",
        "result": {...},
        "duration_minutes": 840
    }
    """

@app.post("/work/add")
async def add_task(task: NewTask):
    """Add new task to queue"""
```

### Swarm Status

```python
@app.get("/swarm/status")
async def get_swarm_status():
    """
    Get overall swarm status

    Response:
    {
        "sessions": {
            "total": 12,
            "active": 8,
            "idle": 3,
            "busy": 5
        },
        "tasks": {
            "pending": 12,
            "in_progress": 5,
            "completed": 47
        },
        "performance": {
            "utilization": 0.75,
            "throughput": 4.2,  # tasks/hour
            "avg_task_time": 142  # minutes
        }
    }
    """

@app.websocket("/swarm/realtime")
async def swarm_realtime(websocket: WebSocket):
    """Real-time swarm updates via WebSocket"""
```

---

## 🧠 Core Coordination Logic

### Coordinator Class

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio

class SwarmCoordinator:
    """Main coordination engine"""

    def __init__(self, redis):
        self.redis = redis
        self.scheduler = AsyncIOScheduler()
        self.session_manager = SessionManager(redis)
        self.work_queue = WorkQueue(redis)
        self.capability_matcher = CapabilityMatcher(redis)

    def start(self):
        """Start coordination loop"""
        # Main coordination loop every 10 seconds
        self.scheduler.add_job(
            self.coordination_cycle,
            'interval',
            seconds=10,
            id='coordination_cycle'
        )

        # Health check every 60 seconds
        self.scheduler.add_job(
            self.health_check,
            'interval',
            seconds=60,
            id='health_check'
        )

        # Metrics update every 30 seconds
        self.scheduler.add_job(
            self.update_metrics,
            'interval',
            seconds=30,
            id='metrics_update'
        )

        self.scheduler.start()

    async def coordination_cycle(self):
        """Main coordination cycle"""
        # 1. Get active sessions
        active_sessions = await self.session_manager.get_active()

        # 2. Get pending work
        pending_tasks = await self.work_queue.get_pending()

        # 3. Match tasks to sessions
        assignments = await self.optimal_assignment(pending_tasks, active_sessions)

        # 4. Distribute assignments
        for assignment in assignments:
            await self.assign_task(assignment)

        # 5. Check for stalled tasks
        await self.check_stalled_tasks()

    async def optimal_assignment(self, tasks, sessions):
        """Assign tasks optimally to sessions"""
        assignments = []

        # Sort tasks by priority
        tasks.sort(key=lambda t: t['priority'], reverse=True)

        # Get idle sessions
        idle_sessions = [s for s in sessions if s['status'] == 'idle']

        for task in tasks:
            # Find best session for this task
            best_session = await self.find_best_session(task, idle_sessions)

            if best_session:
                assignments.append({
                    'session_id': best_session['id'],
                    'task_id': task['id'],
                    'task': task
                })

                # Mark session as busy
                idle_sessions.remove(best_session)

                # Stop if no more idle sessions
                if not idle_sessions:
                    break

        return assignments

    async def find_best_session(self, task, sessions):
        """Find optimal session for task"""
        required_capability = task['required_capability']

        # Filter sessions with required capability
        capable_sessions = [
            s for s in sessions
            if required_capability in s['capabilities']
        ]

        if not capable_sessions:
            return None

        # Score each session
        scored_sessions = []
        for session in capable_sessions:
            score = await self.score_session_for_task(session, task)
            scored_sessions.append((score, session))

        # Return highest scoring session
        scored_sessions.sort(reverse=True)
        return scored_sessions[0][1]

    async def score_session_for_task(self, session, task):
        """Score how good a session is for a task"""
        score = 0.5  # Base score

        # Performance history
        perf = session['performance']
        score += perf['success_rate'] * 0.3
        score += perf['score'] * 0.2

        # Task type match
        task_type = task['type']
        if task_type in session.get('specialties', []):
            score += 0.2

        # Current load
        if session['status'] == 'idle':
            score += 0.3

        return min(score, 1.0)

    async def health_check(self):
        """Check health of all sessions"""
        sessions = await self.session_manager.get_all()

        for session in sessions:
            # Check last heartbeat
            last_heartbeat = datetime.fromisoformat(session['last_heartbeat'])
            now = datetime.now()

            # Mark offline if no heartbeat for 3 minutes
            if (now - last_heartbeat).seconds > 180:
                await self.session_manager.mark_offline(session['id'])

            # Reassign tasks if session went offline
            if session['status'] == 'offline' and session['current_task_id']:
                await self.reassign_task(session['current_task_id'])
```

---

## 📡 Real-Time Dashboard

### WebSocket Server

```python
from fastapi import WebSocket
from typing import Set

class ConnectionManager:
    """Manage WebSocket connections for real-time updates"""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                self.disconnect(connection)

manager = ConnectionManager()

@app.websocket("/swarm/realtime")
async def swarm_realtime(websocket: WebSocket):
    """Real-time swarm status updates"""
    await manager.connect(websocket)

    try:
        while True:
            # Send status update every 2 seconds
            status = await get_swarm_status()
            await websocket.send_json(status)
            await asyncio.sleep(2)
    except:
        manager.disconnect(websocket)
```

### HTML Dashboard

```html
<!DOCTYPE html>
<html>
<head>
    <title>Unified Swarm Dashboard</title>
    <style>
        body { font-family: monospace; background: #0a0e27; color: #e0e0e0; padding: 20px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .card { background: rgba(255,255,255,0.05); border: 1px solid #667eea; border-radius: 8px; padding: 20px; }
        .session { margin: 10px 0; padding: 10px; background: rgba(255,255,255,0.02); border-radius: 4px; }
        .idle { border-left: 3px solid #48bb78; }
        .busy { border-left: 3px solid #f59e0b; }
        .offline { border-left: 3px solid #ef4444; }
        .metrics { font-size: 24px; font-weight: bold; color: #667eea; }
    </style>
</head>
<body>
    <h1>🧠 Unified Swarm Dashboard</h1>

    <div class="grid">
        <div class="card">
            <h2>Sessions</h2>
            <div class="metrics">
                <span id="active-sessions">0</span> / <span id="total-sessions">0</span> Active
            </div>
            <div id="session-list"></div>
        </div>

        <div class="card">
            <h2>Work Queue</h2>
            <div class="metrics">
                <span id="pending-tasks">0</span> Pending
            </div>
            <div class="metrics">
                <span id="in-progress-tasks">0</span> In Progress
            </div>
            <div id="task-list"></div>
        </div>

        <div class="card">
            <h2>Performance</h2>
            <div class="metrics">
                <span id="utilization">0%</span> Utilization
            </div>
            <div class="metrics">
                <span id="throughput">0</span> tasks/hour
            </div>
            <div class="metrics">
                <span id="completed">0</span> Completed Today
            </div>
        </div>
    </div>

    <script>
        const ws = new WebSocket('ws://localhost:8600/swarm/realtime');

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            updateDashboard(data);
        };

        function updateDashboard(data) {
            // Update session counts
            document.getElementById('active-sessions').textContent = data.sessions.active;
            document.getElementById('total-sessions').textContent = data.sessions.total;

            // Update task counts
            document.getElementById('pending-tasks').textContent = data.tasks.pending;
            document.getElementById('in-progress-tasks').textContent = data.tasks.in_progress;

            // Update performance
            document.getElementById('utilization').textContent =
                (data.performance.utilization * 100).toFixed(1) + '%';
            document.getElementById('throughput').textContent =
                data.performance.throughput.toFixed(1);
            document.getElementById('completed').textContent = data.tasks.completed;

            // Update session list
            updateSessionList(data.sessions.list);
        }

        function updateSessionList(sessions) {
            const list = document.getElementById('session-list');
            list.innerHTML = sessions.map(s => `
                <div class="session ${s.status}">
                    <strong>${s.id}</strong><br>
                    Status: ${s.status}<br>
                    ${s.current_task ? 'Task: ' + s.current_task : 'Idle'}
                </div>
            `).join('');
        }
    </script>
</body>
</html>
```

---

## 🚀 Deployment

### Docker Compose

```yaml
version: '3.8'

services:
  orchestrator:
    build: .
    ports:
      - "8600:8600"
    environment:
      - REDIS_URL=redis://redis:6379
      - LOG_LEVEL=INFO
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data

volumes:
  redis-data:
```

---

## ✅ Success Criteria

**Week 1:**
- [ ] 5+ sessions registered and responding
- [ ] Work queue distributing tasks
- [ ] Dashboard showing real-time status
- [ ] 90%+ session utilization

**Week 2:**
- [ ] 10+ sessions in swarm
- [ ] Optimal assignment working (best session gets task)
- [ ] Auto-recovery from session failures
- [ ] 3x task throughput improvement

**Month 1:**
- [ ] 12+ sessions unified
- [ ] Zero duplicate work
- [ ] Self-optimization active
- [ ] 5x productivity improvement

---

**BUILD TIME:** 18-24 hours
**PRIORITY:** CRITICAL (enables everything)
**INFINITE SCALE:** Yes - coordinates infinite sessions

**RESULT:** 12 sessions → 1 superintelligent swarm
