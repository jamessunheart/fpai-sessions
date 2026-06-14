# autonomous-agents - SPECS

**Created:** 2025-11-15
**Status:** Foundation Ready

---

## Purpose

24/7 autonomous AI agents that operate independently to grow treasury, monitor services, improve the system, and discover opportunities. Agents run continuously, make decisions using Claude AI, and execute tasks without human interaction except for approvals on high-risk operations.

---

## Requirements

### Functional Requirements
- [ ] Run agents 24/7 as background processes (systemd services)
- [ ] Initialize agents with Claude AI client for decision making
- [ ] Main loop: gather data → analyze with AI → execute actions → log results → sleep
- [ ] Monitoring Agent: Check all services every minute, auto-fix failures, alert on critical issues
- [ ] Treasury Agent: Scan DeFi protocols, execute yield positions, rebalance portfolio, compound rewards
- [ ] Evolution Agent: Analyze system performance, identify bottlenecks, generate code improvements, deploy optimizations
- [ ] Knowledge Agent: Extract insights from logs, learn patterns, update documentation, share knowledge
- [ ] Opportunity Agent: Monitor crypto markets, find new DeFi protocols, identify arbitrage, evaluate opportunities
- [ ] Orchestrator Agent: Coordinate all agents, manage task queue, prevent conflicts, report to human sessions
- [ ] Safety system with three zones: Green (auto-execute), Yellow (execute + log), Red (require approval)
- [ ] Safety bounds: max position size, max daily trades, protocol requirements, risk limits
- [ ] State persistence: Save agent state to JSON files
- [ ] Comprehensive logging of all agent activities
- [ ] Integration with Claude Code sessions for coordination

### Non-Functional Requirements
- [ ] Performance: Decision cycle < 5 seconds, monitoring check < 1 second
- [ ] Reliability: Agent auto-restart on failure, graceful degradation if Claude API unavailable
- [ ] Safety: All high-risk operations require human approval before execution
- [ ] Security: Private keys encrypted, never logged, all transactions simulated before execution
- [ ] Scalability: Support 10+ concurrent agents

---

## API Specs

### Endpoints

**GET /agents**
- **Purpose:** List all agents and their status
- **Input:** None
- **Output:** Array of agent status (name, status, last_run, next_run)
- **Success:** 200 OK
- **Errors:** 500 if status unavailable

**GET /agents/{agent_name}/status**
- **Purpose:** Get detailed status of specific agent
- **Input:** agent_name
- **Output:** Agent state, recent actions, performance metrics
- **Success:** 200 OK
- **Errors:** 404 if agent not found

**POST /agents/{agent_name}/command**
- **Purpose:** Send command to agent (pause, resume, execute_task)
- **Input:** agent_name, command, parameters
- **Output:** Command acknowledgment
- **Success:** 202 Accepted
- **Errors:** 400 if invalid command, 404 if agent not found

**GET /agents/{agent_name}/logs**
- **Purpose:** Retrieve agent logs
- **Input:** agent_name, optional time range
- **Output:** Array of log entries
- **Success:** 200 OK
- **Errors:** 404 if agent not found

**GET /agents/decisions/pending**
- **Purpose:** List decisions awaiting human approval
- **Input:** None
- **Output:** Array of pending decisions (agent, decision, reasoning, risk)
- **Success:** 200 OK
- **Errors:** 500 if unavailable

**POST /agents/decisions/{decision_id}/approve**
- **Purpose:** Approve or reject a pending decision
- **Input:** decision_id, approved (boolean), notes
- **Output:** Decision result
- **Success:** 200 OK
- **Errors:** 404 if decision not found

**GET /health**
- **Purpose:** Health check for agent system
- **Input:** None
- **Output:** {"status": "healthy", "active_agents": 6, "pending_decisions": 2}
- **Success:** 200 OK
- **Errors:** 500 if unhealthy

### Data Models

```python
class Agent:
    name: str
    description: str
    status: str  # "running", "paused", "stopped", "error"
    priority: int
    interval_seconds: int
    last_run: Optional[datetime]
    next_run: Optional[datetime]
    total_cycles: int
    successful_cycles: int
    failed_cycles: int

class AgentAction:
    action_id: str
    agent_name: str
    action_type: str
    description: str
    reasoning: str
    safety_zone: str  # "green", "yellow", "red"
    requires_approval: bool
    approved: Optional[bool]
    executed: bool
    result: Optional[dict]
    timestamp: datetime

class AgentState:
    agent_name: str
    state_data: dict
    last_updated: datetime

class SafetyBounds:
    max_position_size: float
    max_daily_trades: int
    min_protocol_tvl: float
    max_risk_score: int
    allow_code_deployment: bool
    require_tests: bool
    max_downtime_before_alert: int

class PendingDecision:
    decision_id: str
    agent_name: str
    decision_type: str
    description: str
    reasoning: str
    risk_level: str
    estimated_value: Optional[float]
    created_at: datetime
    expires_at: datetime
```

---

## Dependencies

### External Services
- Claude API (Anthropic): AI decision making for all agents
- DeFi Protocols: Aave, Pendle, Curve (for Treasury Agent)
- CoinGecko: Market data (for Treasury and Opportunity Agents)
- GitHub API: Code deployment (for Evolution Agent)

### APIs Required
- Anthropic Claude API: All agents use Claude for decision making
- Web3 RPC: Ethereum/Arbitrum for DeFi operations
- Registry: Service discovery for Monitoring Agent
- Orchestrator: System health data

### Data Sources
- Service logs: For Knowledge Agent
- System metrics: For Evolution Agent
- DeFi protocol data: For Treasury and Opportunity Agents
- Agent state files: Persistent state storage

---

## Success Criteria

How do we know this works?

- [ ] Monitoring Agent runs 24/7 and detects service failures
- [ ] Treasury Agent successfully executes at least 1 yield position
- [ ] Evolution Agent identifies and deploys at least 1 optimization
- [ ] All agents log activities comprehensively
- [ ] Safety system prevents high-risk operations without approval
- [ ] Agents recover gracefully from Claude API failures
- [ ] State persistence works across agent restarts
- [ ] Orchestrator successfully coordinates multiple agents
- [ ] Human approval workflow functions correctly
- [ ] System runs autonomously for 7+ days without intervention

---

## Agent Specifications

### 1. Monitoring Agent (Priority 1)
**Purpose:** 24/7 service health monitoring and auto-recovery
- Check all services every 60 seconds
- Detect failures (health endpoint down, high error rate)
- Auto-fix common issues (restart service, clear cache)
- Alert on critical problems that need human intervention
- Log all checks and actions

**Decision Making:**
- Service down < 5 minutes: Auto-restart (Green zone)
- Service down > 5 minutes: Alert human (Yellow zone)
- Multiple services down: Emergency alert (Red zone)

### 2. Treasury Growth Agent (Priority 1)
**Purpose:** Autonomous DeFi portfolio management for yield optimization
- Scan DeFi protocols for yields every hour
- Evaluate opportunities (APY, risk, protocol safety)
- Execute positions based on market intelligence
- Rebalance portfolio when thresholds hit
- Compound rewards daily
- Emergency exit on risk signals

**Decision Making:**
- Position < $1000, protocol TVL > $10M, APY > 10%: Auto-execute (Green)
- Position $1000-5000: Execute + flag for review (Yellow)
- Position > $5000 or new protocol: Require approval (Red)

### 3. System Evolution Agent (Priority 2)
**Purpose:** Continuous system improvement and optimization
- Analyze system performance metrics daily
- Identify bottlenecks (slow APIs, inefficient code)
- Generate code improvements using Claude
- Test improvements in isolated environment
- Deploy safe optimizations automatically
- Track improvement impact

**Decision Making:**
- Code quality improvements: Auto-deploy (Green)
- Performance optimizations with tests: Deploy + log (Yellow)
- Architecture changes: Require approval (Red)

### 4. Knowledge Synthesis Agent (Priority 2)
**Purpose:** Learning and knowledge management
- Extract insights from all agent logs
- Learn patterns (what works, what fails)
- Update system documentation automatically
- Share knowledge with other agents
- Generate reports on system behavior

**Decision Making:**
- Documentation updates: Auto-apply (Green)
- Pattern learning: Log and share (Green)
- All actions are low-risk information processing

### 5. Opportunity Scout Agent (Priority 2)
**Purpose:** Market opportunity discovery
- Monitor crypto markets for trends
- Find new high-yield DeFi protocols
- Identify arbitrage opportunities
- Evaluate new investment opportunities
- Alert on time-sensitive opportunities

**Decision Making:**
- Market analysis: Auto-run (Green)
- New protocol discovery: Flag for review (Yellow)
- Arbitrage > $100 profit: Require approval (Red)

### 6. Orchestrator Agent (Priority 1)
**Purpose:** Multi-agent coordination
- Coordinate task execution across agents
- Prevent conflicting operations (e.g., two agents deploying simultaneously)
- Manage shared resource access
- Aggregate reports for human sessions
- Emergency stop for all agents

**Decision Making:**
- Task scheduling: Auto-coordinate (Green)
- Resource conflicts: Pause and escalate (Yellow)
- System-wide emergency: Require approval (Red)

---

## Technical Constraints

- **Language/Framework:** Python 3.11+ with asyncio
- **Deployment:** systemd services (one per agent)
- **Resource limits:**
  - Memory: 256MB per agent
  - CPU: 0.5 cores per agent
  - Storage: 1GB for state and logs
- **Response time:** < 5 seconds per decision cycle
- **Uptime:** 99.9% target per agent
- **Restart policy:** Always restart on failure
- **Logging:** All actions logged with reasoning

---

## Deployment

### Systemd Service Template
```ini
[Unit]
Description=FPAI {AgentName} Agent
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/fpai/autonomous-agents
Environment="ANTHROPIC_API_KEY=sk-..."
ExecStart=/usr/bin/python3 agents/{agent_name}_agent.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

**Next Step:** Deploy Monitoring Agent first, then Treasury Agent for revenue generation
