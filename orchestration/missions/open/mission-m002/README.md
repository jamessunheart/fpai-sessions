# Mission Control Dashboard (M002)

This repository houses the backend service for Mission M002: a Mission Control Dashboard that aggregates build telemetry and exposes it via a FastAPI-powered API. The initial step sets up a minimal project structure, dependency list, and a health endpoint that can be expanded into the full specification.

## Getting Started

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Visit `http://127.0.0.1:8000/health` to verify that the service is running.

> **Note:** The platform blocked creation of `.env.example`, so an
> `env.example` file is included instead. Copy or rename it to `.env`
> before running the service so the settings loader can pick up your
> environment values.

