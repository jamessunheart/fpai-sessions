# Autonomous Executor (M001)

Mission M001 delivers the Autonomous Executor service: an API-driven task execution engine that receives jobs from the orchestrator, runs AI workflows, and reports real-time status back to Mission Control.

## Local Development

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Visit `http://127.0.0.1:8000/docs` for interactive API docs.

## Core Features

- `POST /message` intake for new task assignments (JWT-ready)
- Task queue & processor loop with priority handling
- Task status tracking and telemetry hooks
- Extensible adapters for external AI tools

See `M001_service_autonomous_executor_ai_task.md` for the full specification.

