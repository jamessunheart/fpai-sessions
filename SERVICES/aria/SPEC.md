# ARIA - Autonomous Recursive Intelligence Assistant

**Service Name:** aria
**Port:** 8710
**Version:** 1.0.0
**Server:** Primary (198.54.123.234) — DEMO-ACTIVE
**Status:** Demo Active (routes inference to Secondary)

---

## 1. PURPOSE

ARIA is the unified AI assistant for the Full Potential ecosystem. It combines:
- **Sovereignty-first AI routing** (local GPUs → GPU Bridge → fallback to paid APIs)
- **Self-improvement capabilities** (learns from interactions, improves prompts)
- **Human recruitment** (can request help for tasks beyond its capabilities)
- **Multi-model consensus** (uses multiple models for critical decisions)

ARIA is designed to be the "best AI assistant in the world" by continuously improving itself using the builder pipeline.

---

## 2. CORE CAPABILITIES

### 2.1 Intelligent Conversation
- Natural language understanding and generation
- Context-aware responses with memory
- Multi-turn conversation handling
- Code generation and explanation

### 2.2 Sovereignty-First AI Routing
- **Primary:** Local Ollama models via GPU Bridge (FREE)
  - `qwen2.5-coder:7b` - Code tasks
  - `deepseek-coder:6.7b` - Code analysis
  - `llama3.1:8b` - General reasoning
  - `mistral:7b` - Fast responses
- **Fallback:** Paid APIs only when quality threshold not met
  - Claude Haiku → Claude Sonnet → Claude Opus
  - GPT-4o → GPT-4

### 2.3 Quality-Based Model Selection
- Automatic quality scoring of responses
- Fallback chain if quality < threshold
- Cost tracking and optimization
- Success rate monitoring

### 2.4 Self-Improvement Loop
- Analyzes conversation patterns
- Identifies weak areas
- Generates improvement SPECs
- Submits to builder pipeline
- Deploys improvements automatically

### 2.5 Human Recruitment
- Detects tasks beyond AI capability
- Creates clear task descriptions
- Routes to human helpers
- Tracks completion and integrates results

---

## 3. API SPECIFICATION

### 3.1 UDC Endpoints

#### GET /health
```json
{
  "status": "healthy",
  "service": "aria",
  "version": "1.0.0",
  "gpu_bridge_status": "connected",
  "models_available": ["qwen2.5-coder:7b", "deepseek-coder:6.7b", "llama3.1:8b"],
  "conversations_today": 42,
  "self_improvements_queued": 3
}
```

#### GET /capabilities
```json
{
  "service": "aria",
  "capabilities": [
    "chat",
    "code_generation",
    "code_review",
    "self_improvement",
    "human_recruitment",
    "multi_model_consensus"
  ],
  "supported_models": {
    "primary": ["qwen2.5-coder:7b", "deepseek-coder:6.7b", "llama3.1:8b"],
    "fallback": ["claude-3-5-haiku", "gpt-4o"]
  }
}
```

#### GET /stats
```json
{
  "total_conversations": 1500,
  "successful_responses": 1450,
  "fallback_rate": 0.03,
  "avg_response_time_ms": 2500,
  "cost_saved_usd": 45.00,
  "self_improvements_deployed": 12
}
```

### 3.2 Chat Endpoints

#### POST /chat
```json
// Request
{
  "message": "Write a Python function to calculate fibonacci",
  "context": {"task_type": "code_generation"},
  "session_id": "optional-session-uuid"
}

// Response
{
  "response": "Here's an efficient fibonacci function...",
  "model_used": "qwen2.5-coder:7b",
  "quality_score": 85,
  "tokens": 150,
  "cost": 0.0,
  "session_id": "uuid"
}
```

#### POST /chat/stream (WebSocket)
Real-time streaming responses for interactive chat.

### 3.3 Self-Improvement Endpoints

#### GET /improvements
List pending/completed self-improvement tasks.

#### POST /improvements/trigger
Manually trigger self-improvement analysis.

---

## 4. ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────┐
│                         ARIA                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │   Chat API   │  │ Quality Gate │  │ Self-Improver     │  │
│  └──────┬──────┘  └──────┬───────┘  └─────────┬─────────┘  │
│         │                │                     │            │
│         ▼                ▼                     ▼            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Model Router                            │   │
│  │  ┌─────────┐  ┌───────────┐  ┌──────────────────┐   │   │
│  │  │GPU Bridge│  │Local Ollama│  │ Paid API Fallback│   │   │
│  │  │(Primary) │  │ (Backup)   │  │ (Last Resort)    │   │   │
│  │  └─────────┘  └───────────┘  └──────────────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Builder Pipeline                        │   │
│  │  (For self-improvement SPECs)                        │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. CONFIGURATION

```bash
# Service
SERVICE_NAME=aria
SERVICE_PORT=8710
SERVER=primary

# AI Routing
# Optional GPU bridge (leave empty to disable)
GPU_BRIDGE_URL=
# Two-server architecture: Ollama lives on secondary
LOCAL_OLLAMA_URL=http://162.0.208.88:11434
QUALITY_THRESHOLD=70

# Fallback APIs (only used if local quality < threshold)
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...

# Consciousness (two-server architecture: secondary)
CONSCIOUSNESS_DECISION_ENGINE_URL=http://162.0.208.88:8150
CONSCIOUSNESS_VERIFIER_URL=http://162.0.208.88:8140
CONSCIOUSNESS_OPTIMIZER_URL=http://162.0.208.88:8160

# Self-Improvement
BUILDER_QUEUE_DB=/opt/fpai/ai-brain/v2/thinking_v2.db
IMPROVEMENT_CHECK_INTERVAL=3600
```

---

## 6. LEARNINGS APPLIED

This service incorporates all learnings from the GPU Bridge and Builder fixes:

1. **Model-Aware Routing**: Routes to GPUs that actually have the requested model
2. **Quality-Based Fallbacks**: Only falls back when quality < threshold
3. **Proper Error Handling**: Graceful degradation, not crashes
4. **Stats Tracking**: Detailed metrics for optimization
5. **Self-Healing**: Retries with exponential backoff
6. **Cost Optimization**: Prefers free local models, tracks savings

---

## 7. COMPLIANCE

- [x] UDC Endpoints (/health, /capabilities, /stats)
- [x] Sovereignty-first (local AI preferred)
- [x] Cost tracking
- [x] Quality metrics
- [ ] Tests (auto-generated via builder)



