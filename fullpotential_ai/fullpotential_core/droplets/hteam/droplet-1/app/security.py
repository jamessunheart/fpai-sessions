import os, time, jwt
from fastapi import Request, HTTPException, status, Depends

JWT_SECRET = os.getenv("REGISTRY_JWT_SECRET", "")
_RATE = {}  # token -> [timestamps]


async def require_jwt(request: Request):
    """
    FastAPI dependency: validates JWT and required headers.
    """
    # If JWT is disabled (no secret set) → skip verification
    if not JWT_SECRET:
        return

    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Bearer token")

    token = auth.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        request.state.user = payload
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    # Required trace headers
    if not request.headers.get("X-Trace-Id") or not request.headers.get("X-Source"):
        raise HTTPException(status_code=400, detail="X-Trace-Id and X-Source headers required")

    # Basic rate limit: 60 requests/min/token
    now = time.time()
    win = [t for t in _RATE.get(token, []) if now - t < 60]
    if len(win) >= 60:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    win.append(now)
    _RATE[token] = win
