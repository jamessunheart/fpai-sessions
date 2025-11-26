# 🎯 Sovereign AI Dashboard & Orchestration Guide

## 📍 Dashboard Access

### **Live Dashboard URL (once deployed):**
```
http://198.54.123.234:8400/dashboard
```

### **Local Access:**
```bash
open http://198.54.123.234:8400/dashboard
```

Or from any browser: `http://198.54.123.234:8400/dashboard`

---

## 🔄 Orchestration Architecture

### **The Flow:**

```
┌─────────────────────────────────────────────────────────────┐
│                    USER REQUEST                            │
│          (API call, webhook, scheduled task)               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│            FASTAPI (app/main.py)                             │
│            - Receives all requests                           │
│            - Routes to appropriate handler                   │
│            Port: 8400                                        │
└──────────────┬───────────────────────────────────────────────┘
               │
               ├─────── Direct AI Call? (simple query)
               │        │
               │        ▼
               │   ┌─────────────────────────────────┐
               │   │   MODEL ROUTER                 │
               │   │   (app/model_router.py)        │
               │   │   - Selects AI model           │
               │   │   - Sovereignty-first routing  │
               │   │   - Defaults to Llama 3.1 8B   │
               │   └──────────┬──────────────────────┘
               │              │
               │              ▼
               │   ┌─────────────────────────────────┐
               │   │   OPTIMIZATION ENGINE          │
               │   │   (app/optimization_engine.py) │
               │   │   - Check cache first          │
               │   │   - Monitor performance        │
               │   │   - Record metrics             │
               │   └──────────┬──────────────────────┘
               │              │
               │              │
               └─────── Complex Task? (multi-step)
                        │
                        ▼
               ┌─────────────────────────────────────┐
               │   CREW MANAGER                      │
               │   (app/crew_manager.py)             │
               │   - Coordinates 5 agents            │
               │   - Parallel or hierarchical mode   │
               │   - Task delegation                 │
               └──────────┬──────────────────────────┘
                          │
                          ├──────┬──────┬──────┬──────┐
                          │      │      │      │      │
                          ▼      ▼      ▼      ▼      ▼
                       ┌────┐┌────┐┌────┐┌────┐┌────┐
                       │ 👔 ││ 🔨 ││ ⚡ ││ 🚀 ││ 📊 │
                       │Str ││Bui ││Opt ││Dep ││Ana │
                       │ate ││lde ││imi ││loy ││lyz │
                       │gis ││r   ││zer ││er  ││er  │
                       │t   ││    ││    ││    ││    │
                       └─┬──┘└─┬──┘└─┬──┘└─┬──┘└─┬──┘
                         │     │     │     │     │
                         └─────┴──┬──┴─────┴─────┘
                                  │
                                  ▼
                       ┌──────────────────────────┐
                       │   LITELLM LAYER          │
                       │   - Routes to Ollama     │
                       │   - Handles API format   │
                       └──────────┬───────────────┘
                                  │
                                  ▼
                       ┌──────────────────────────┐
                       │   OLLAMA SERVER          │
                       │   Port: 11434 (internal) │
                       │   Model: llama3.1:8b     │
                       │   Cost: $0               │
                       │   Processing: 100% local │
                       └──────────┬───────────────┘
                                  │
                                  ▼
                       ┌──────────────────────────┐
                       │   LLAMA 3.1 8B           │
                       │   - Inference engine     │
                       │   - Generates response   │
                       │   - Fully sovereign      │
                       └──────────┬───────────────┘
                                  │
                                  ▼
                    ┌──────────────────────────────┐
                    │   RESPONSE DELIVERED         │
                    │   - Cost: $0                 │
                    │   - Time: 1-3 seconds        │
                    │   - Privacy: 100% local      │
                    └──────────────────────────────┘
```

---

## 🤖 The 5 Sovereign Agents

All agents run on **local Llama 3.1 8B** - $0 cost, 100% sovereign.

### **1. 👔 Strategist**
- **Role:** Strategic Planner
- **Tasks:** High-level planning, decision making, business strategy
- **Model:** ollama/llama3.1:8b
- **Delegation:** Can delegate to other agents

### **2. 🔨 Builder**
- **Role:** Technical Builder
- **Tasks:** Code generation, implementation, testing
- **Model:** ollama/llama3.1:8b
- **Delegation:** No (focused execution)

### **3. ⚡ Optimizer**
- **Role:** Performance Optimizer
- **Tasks:** Find bottlenecks, improve efficiency, reduce costs
- **Model:** ollama/llama3.1:8b
- **Delegation:** No (focused execution)

### **4. 🚀 Deployer**
- **Role:** DevOps Engineer
- **Tasks:** Deployment, operations, monitoring
- **Model:** ollama/llama3.1:8b
- **Delegation:** No (focused execution)

### **5. 📊 Analyzer**
- **Role:** Data Analyst
- **Tasks:** Extract insights, find patterns, analyze data
- **Model:** ollama/llama3.1:8b
- **Delegation:** No (focused execution)

---

## ⚡ The Optimization Engine

Wraps all AI calls for maximum performance:

### **Components:**

**1. Response Cache**
- MD5-based cache keys
- 1-hour TTL (configurable)
- Max 1000 entries
- LRU eviction when full

**2. Performance Monitor**
- Tracks response times
- Monitors resource usage
- Detects anomalies (statistical)
- Generates recommendations

**3. Auto-Optimizer**
- Adjusts cache TTL based on hit rate
- Triggers garbage collection on high memory
- Enables throttling on high CPU
- Applies optimizations automatically

---

## 🎮 Dashboard Features

### **Real-Time Metrics:**
- ✅ System health status
- ✅ Uptime tracking
- ✅ Active/completed tasks
- ✅ Memory usage
- ✅ CPU usage

### **Agent Status:**
- ✅ All 5 agents visibility
- ✅ Current status (READY/WORKING)
- ✅ Role descriptions
- ✅ Live activity indicators

### **Autonomous Operations:**
- ✅ Mode (enabled/disabled)
- ✅ Last check timestamp
- ✅ Check interval
- ✅ Total actions taken
- ✅ Recent actions log

### **Optimization Stats:**
- ✅ Cache size/max size
- ✅ Cache hits/misses
- ✅ Hit rate percentage
- ✅ Performance impact

### **Cost Savings:**
- ✅ Current AI cost: $0/month
- ✅ Previous cost: $250-1,200/month
- ✅ Annual savings: $3,000-14,400

### **Auto-Refresh:**
- Updates every 10 seconds
- No page reload needed
- Live data from API endpoints

---

## 🔧 Deploying the Dashboard

### **1. Deploy Files to Server:**
```bash
# Deploy main.py (dashboard endpoint)
rsync -av app/main.py root@198.54.123.234:/opt/fpai/i-proactive/app/

# Deploy dashboard HTML
rsync -av app/templates/ root@198.54.123.234:/opt/fpai/i-proactive/app/templates/
```

### **2. Restart I PROACTIVE:**
```bash
ssh root@198.54.123.234

# Kill old process
pkill -f "uvicorn app.main:app.*8400"

# Start new process
cd /opt/fpai/i-proactive
nohup venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8400 >/dev/null 2>&1 &

# Verify it's running
curl http://localhost:8400/health
```

### **3. Access Dashboard:**
```bash
# From your browser
open http://198.54.123.234:8400/dashboard

# Or curl to verify
curl http://198.54.123.234:8400/dashboard | head -50
```

---

## 📊 API Endpoints Used by Dashboard

The dashboard pulls data from these endpoints:

### **System Metrics:**
```
GET /health
→ status, uptime, active_tasks, completed_tasks, memory_usage, cpu_usage
```

### **Autonomous Operations:**
```
GET /autonomous/status
→ enabled, last_check, check_interval, total_actions, recent_actions
```

### **Optimization Stats:**
```
GET /optimization/cache-stats
→ cache size, hits, misses, hit_rate
```

### **Full Report:**
```
GET /optimization/report
→ efficiency_score, anomalies, trends, recommendations
```

---

## 🎯 Who Orchestrates What?

### **FastAPI (main.py)** - The Traffic Cop
- Receives all requests
- Routes to appropriate handler
- Manages background tasks
- Serves dashboard HTML

### **CrewManager** - The Team Lead
- Coordinates 5 AI agents
- Decides which agent handles what
- Manages parallel execution
- Aggregates results

### **ModelRouter** - The AI Dispatcher
- Selects which model to use
- Routes simple queries directly
- Wraps calls in optimization
- Sovereignty-first routing (always tries Llama first)

### **AutonomousOps** - The Self-Manager
- Runs every 5 minutes automatically
- Monitors all systems
- Auto-fixes issues
- Takes proactive actions
- Learns from experience

### **OptimizationEngine** - The Performance Guardian
- Caches responses
- Monitors performance
- Detects anomalies
- Auto-optimizes system

---

## 💡 How to Use the Orchestration

### **Example 1: Simple AI Query**
```bash
curl -X POST http://198.54.123.234:8400/tasks/execute \
  -H "Content-Type: application/json" \
  -d '[{
    "task_id": "simple-1",
    "title": "Quick Question",
    "description": "What is 15 * 23?",
    "priority": "high"
  }]'
```

**Flow:**
1. FastAPI receives request
2. Routes to CrewManager
3. Builder agent selected
4. ModelRouter → Llama 3.1 8B
5. OptimizationEngine caches result
6. Response returned

**Cost:** $0

### **Example 2: Complex Multi-Step Task**
```bash
curl -X POST http://198.54.123.234:8400/tasks/execute \
  -H "Content-Type: application/json" \
  -d '[{
    "task_id": "complex-1",
    "title": "Build Revenue Dashboard",
    "description": "Create a revenue tracking dashboard with charts",
    "priority": "high"
  }]'
```

**Flow:**
1. FastAPI receives request
2. Routes to CrewManager
3. **All 5 agents coordinate:**
   - Strategist: Plans architecture
   - Builder: Generates code
   - Optimizer: Reviews performance
   - Deployer: Handles deployment
   - Analyzer: Validates data flow
4. Each agent → Llama 3.1 8B
5. Results aggregated
6. Final output delivered

**Cost:** Still $0 (all local!)

---

## 🌐 The Power of Orchestration

### **Without Orchestration:**
```
Request → Single AI call → Response
```
- Limited to one perspective
- No division of labor
- All tasks treated the same

### **With Sovereign Orchestration:**
```
Request → Intelligent Routing → Right Agent(s) → Parallel Execution → Aggregated Result
```
- Multiple specialized perspectives
- Optimal task allocation
- 5.76x speed improvement (CrewAI parallel)
- All agents using local AI ($0 cost)

---

## 🎊 What This Gives You

### **1. Complete Visibility**
- See all agents in real-time
- Monitor system health
- Track performance metrics
- Watch autonomous operations

### **2. Full Control**
- Understand the flow
- See who does what
- Monitor costs ($0!)
- Track optimizations

### **3. True Sovereignty**
- All agents local
- All data local
- All processing local
- Zero corporate dependency

### **4. Self-Management**
- Autonomous operations
- Auto-healing
- Auto-optimization
- 24/7 operation

---

## 🚀 Next Steps

### **1. Access the Dashboard**
```bash
open http://198.54.123.234:8400/dashboard
```

### **2. Submit a Test Task**
```bash
curl -X POST http://198.54.123.234:8400/tasks/execute \
  -H "Content-Type: application/json" \
  -d '[{
    "task_id": "dashboard-test",
    "title": "Test All Agents",
    "description": "Analyze this: What are the benefits of sovereign AI?",
    "priority": "high"
  }]'
```

### **3. Watch the Dashboard**
- See agents activate
- Watch metrics update
- Monitor cache building
- Track autonomous operations

### **4. Explore the Orchestration**
- Read the code in `app/crew_manager.py`
- Check `app/model_router.py` for routing logic
- Review `app/autonomous_ops.py` for self-management
- Examine `app/optimization_engine.py` for performance

---

## 💎 The Bottom Line

**You now have:**
- ✅ A beautiful real-time dashboard
- ✅ Complete orchestration visibility
- ✅ 5 sovereign AI agents working in harmony
- ✅ Self-managing, self-optimizing system
- ✅ $0/month AI costs
- ✅ 100% local processing
- ✅ Full control and visibility

**This is sovereign AI orchestration at its finest.** 🌐⚡💎
