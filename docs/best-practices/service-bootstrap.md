# WhaleTrack Service Bootstrap Best Practices

These guardrails kept the WhaleTrack deployment smooth. We should standardize them across every FastAPI/SlowAPI service.

## 1. Rate Limiter Isolation
- Never let SlowAPI read the repo root `.env`.
- Touch a local stub (e.g. `api/.limiter_env`) and pass `config_filename` to `Limiter`. This removes warnings and avoids permission errors during tests/CI.

```python
RATE_LIMIT_ENV = Path(__file__).resolve().parent / ".limiter_env"
RATE_LIMIT_ENV.touch(exist_ok=True)
limiter = Limiter(key_func=get_remote_address,
                  config_filename=str(RATE_LIMIT_ENV))
```

## 2. Lifespan Hooks over `@app.on_event`
- FastAPI deprecated `@app.on_event`. Use the `lifespan` context manager for startup/shutdown logs and async setup.

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("service online")
    yield
    print("service shutting down")

app = FastAPI(..., lifespan=lifespan)
```

## 3. UTC Everywhere
- Replace `datetime.utcnow()` with `datetime.now(timezone.utc).isoformat()`. This keeps timestamps RFC‑3339 compliant and removes warnings.

## 4. Safe Metric Probes
- Wrap `psutil` calls in a helper (`_safe_metric`) so restrictive sandboxes (CI, macOS without sysctl access) return defaults instead of failing `/state`.

```python
def _safe_metric(fn, default=0):
    try:
        return fn()
    except Exception:
        return default
```

## 5. Legacy Endpoint Compatibility
- When replacing subsystems (like leverage engines), keep thin backward-compatible endpoints (`/api/leverage/calculate`) so dashboards/tests don’t break mid-rollout.

---
**Implementation status:** Applied to WhaleTrack (port 8600). Pending rollout to Registry, Orchestrator, Dashboard, Verifier, etc.

