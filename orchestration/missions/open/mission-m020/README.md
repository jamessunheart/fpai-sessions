# Treasury Growth System (M020)

This service manages financial assets, transactions, and analytics to support the Full Potential AI treasury operations. It exposes a FastAPI backend with PostgreSQL persistence so internal systems can ingest data and operators can view real-time performance.

## Local Development

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Visit `http://127.0.0.1:8000/docs` for interactive API docs.

## Mission Scope

* Asset registry with risk metadata
* Transaction logging (buys, sells, transfers)
* Analytics endpoints (predicted returns, risk scoring)
* JWT-auth ready (hooks in place for future auth)

See `M020_build_treasury_growth_system.md` for the full specification.

