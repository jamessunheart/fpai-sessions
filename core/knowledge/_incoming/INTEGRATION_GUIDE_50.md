# 🔌 Integration Instructions: Mother System -> Mission Control

**Goal:** Connect the Mother System to the new Mission Control backend so it automatically tracks mission progress.

### 1. Install the Client
Copy the `telemetry_client.py` file from this mission folder into the Mother System's `core/` or `utils/` directory.

### 2. Prompt for Cursor (Mother System Context)
Copy and paste the following prompt to the Cursor instance that has access to the Root Directory / Mother System code:

---

> **Prompt:**
> "I need to integrate the Mother System with the new Mission Control service (running at http://198.54.123.234:8010).
>
> 1.  Please locate where the system executes high-level actions or missions (look for `run_mission`, `execute_task`, or similar loops).
> 2.  Import the `TelemetryClient` (I will provide the code or you can assume it's in `core/telemetry_client.py`).
> 3.  Instrument the code to send events:
>     *   When a mission starts: `client.capture('mother_system', 'mission_start', {'mission_id': '...', 'objective': '...'})`
>     *   When a sub-task finishes: `client.capture('mother_system', 'task_complete', {'mission_id': '...', 'result': '...'})`
>     *   If an error occurs: `client.capture('mother_system', 'mission_failed', {'mission_id': '...', 'error': str(e)})`
>
> Here is the client code to use:
> [PASTE CONTENT OF telemetry_client.py HERE]
> "

---

### 3. Verify
Once integrated, run a test mission in the Mother System and check:
`http://198.54.123.234:8010/telemetry`
You should see the new events appearing in real-time.

