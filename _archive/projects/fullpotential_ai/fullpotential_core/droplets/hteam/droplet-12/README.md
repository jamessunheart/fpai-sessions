# UDC v1.0

## Droplet #12: Chat Orchestrator

**Repo:** `droplet-12-chat-orchestrator`

**Purpose:** An intelligent routing service that uses AI-powered reasoning to understand natural language user requests and orchestrates interactions with multiple system droplets.

---

## 1. IDENTITY & STATUS

- **Droplet ID:** 12
- **Function:** Manages task routing and workflow management for the mesh.
- **Steward:** Zainab
- **Status:** IN_DEVELOPMENT
- **Live Endpoint:** `https://drop12.fullpotential.ai`
- **Healthcheck:** `https://drop12.fullpotential.ai/health`

---

## 2. SYSTEM CONTEXT

- **Upstream Dependencies:** #1 Registry, #10 Orchestrator
- **Downstream Outputs:** #2 Dashboard, #14 Visibility Deck, #16 Onboarding, #18 Voice
- **Related Droplets:** None

---

## 3. ASSEMBLY LINE SPRINT (Current Work)

Tracks current development state aligned with the SSoT.

- **Current Sprint:** "GitHub PR Monitoring"
- **Spec:** `SPEC_Chat_Orchestrator_Droplet_12.md`
- **Apprentice:** [@builder]
- **Verifier:** [@verifier]
- **PR / Branch:** [Link to active PR or branch]
- **Cost / Time (Reported):** "5 h (Apprentice), 1.5 h (Verifier)"

---

## 4. TECHNICAL SSOT (How to Run)

### A. Core Foundation Files

Built against and must adhere to:

- `FOUNDATIONAL FILES/2.1-UDC_COMPLIANCE.md`
- `FOUNDATIONAL FILES/2.2-TECH_STACK.md`
- `FOUNDATIONAL FILES/5-SECURITY_REQUIREMENTS.md`
- `FOUNDATIONAL FILES/4-CODE_STANDARDS.md`
- `FOUNDATIONAL FILES/3-INTEGRATION_GUIDE.md`

### B. Repository Map

```
/app/
├── api/
│ └── routes/
│   ├── chat.py
│   ├── health.py
│   ├── process.py
│   ├── sessions.py
│   └── websocket.py
├── models/
│   ├── chat.py
│   ├── envelopes.py
│   └── udc.py
├── services/
│   ├── data_extractor.py
│   ├── memory.py
│   ├── orchestrator.py
│   ├── reasoning.py
│   ├── registry_info.py
│   ├── response_formatter.py
│   └── session.py
├── utils/
│   ├── auth.py
│   └── logging.py
├── config.py
├── globals.py
└── main.py
/tests/
├── test_chat.py
├── test_health.py
├── test_memory.py
├── test_orchestrator_routing.py
├── test_reasoning.py
└── test_websocket.py
.env.example
Dockerfile
HANDOFF.md
README.md
SPEC.md
requirements.txt
```

### C. AI Context

- **Primary Model:** Gemini 2.5 Flash
- **Foundation Files Used:** 5 (UDC, TECH_STACK, SECURITY, CODE_STANDARDS, INTEGRATION_GUIDE)
- **AI Prompts Stored:** Yes (in SPEC.md)

### D. Setup & Run

1.  **Clone the repository**
2.  **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Copy the environment template**
    ```bash
    cp .env.example .env
    ```
4.  **Fill in credentials in `.env`**
5.  **Run locally**
    ```bash
    uvicorn app.main:app --reload
    ```
6.  **Run tests**
    ```bash
    pytest
    ```

---

## 5. VERIFICATION HISTORY

| Date       | Verifier         | Branch/PR | Result | Notes                       |
|------------|------------------|-----------|--------|-----------------------------|
| 2025-11-11 | @verifier-name   | pr-1      | PASS   | Deployed to production      |
| 2025-11-10 | @verifier-name   | branch-a  | FAIL   | UDC compliance failure      |

---

## 6. NOTES & IMPROVEMENTS

- **[Apprentice Note 2025-11-10]:** Had trouble with GitHub webhook signature verification; fixed in `auth.py`.
- **[Verifier Note 2025-11-11]:** Missed test case for empty payloads; logic sound, approved with minor fix.

---

**Related Docs:**

- `ASSEMBLY_LINE_SOP.md`
- `COORDINATOR_HANDBOOK.md`
- `VERIFICATION_PROTOCOL.md`