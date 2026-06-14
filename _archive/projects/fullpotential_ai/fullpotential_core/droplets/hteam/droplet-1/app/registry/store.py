import os, sqlite3, time
from contextlib import contextmanager

DB_PATH = os.getenv("REGISTRY_DB", "/app/data/registry.db")
HEARTBEAT_INTERVAL_SEC = int(os.getenv("HEARTBEAT_INTERVAL_SEC", "60"))
HEARTBEAT_TTL_SEC = int(os.getenv("HEARTBEAT_TTL_SEC", str(HEARTBEAT_INTERVAL_SEC * 3)))


os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def _connect():
    # isolation_level=None => autocommit; each statement commits immediately
    con = sqlite3.connect(DB_PATH, timeout=5, isolation_level=None, check_same_thread=False)
    con.row_factory = sqlite3.Row
    # Improve concurrency for multi-process
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")
    con.execute("PRAGMA temp_store=MEMORY;")
    return con

@contextmanager
def conn():
    con = _connect()
    try:
        yield con
    finally:
        con.close()

def init_db():
    with conn() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS droplets (
            id TEXT PRIMARY KEY,
            name TEXT,
            fqdn TEXT,
            ip TEXT,
            role TEXT,
            env TEXT,
            version TEXT,
            cost_hour REAL,
            cpu REAL,
            mem REAL,
            disk REAL,
            last_seen INTEGER
        )""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_last_seen ON droplets(last_seen)")
init_db()

def upsert_register(payload: dict) -> str:
    now = int(time.time())
    dpl_id = payload.get("id") or payload.get("fqdn")
    if not dpl_id:
        raise ValueError("id or fqdn required")

    fields = {
        "id": dpl_id,
        "name": payload.get("name"),
        "fqdn": payload.get("fqdn"),
        "ip": payload.get("ip"),
        "role": payload.get("role"),
        "env": payload.get("env"),
        "version": payload.get("version"),
        "cost_hour": payload.get("cost_hour") or 0.0,
        "last_seen": now
    }
    with conn() as c:
        c.execute("""
        INSERT INTO droplets (id,name,fqdn,ip,role,env,version,cost_hour,last_seen)
        VALUES (:id,:name,:fqdn,:ip,:role,:env,:version,:cost_hour,:last_seen)
        ON CONFLICT(id) DO UPDATE SET
          name=excluded.name,
          fqdn=excluded.fqdn,
          ip=excluded.ip,
          role=excluded.role,
          env=excluded.env,
          version=excluded.version,
          cost_hour=excluded.cost_hour,
          last_seen=excluded.last_seen   
        """, fields)
    return dpl_id

def update_heartbeat(payload: dict) -> bool:
    if "id" not in payload:
        return False
    now = int(time.time())
    fields = {
        "id": payload["id"],
        "cpu": min(max(float(payload.get("cpu") or 0), 0), 100),
        "mem": min(max(float(payload.get("mem") or 0), 0), 100),
        "disk": min(max(float(payload.get("disk") or 0), 0), 100),
        "last_seen": now,               # server timestamp
    }
    with conn() as c:
        exists = c.execute("SELECT 1 FROM droplets WHERE id=?", (fields["id"],)).fetchone()
        if not exists:
            return False
        c.execute("""
            UPDATE droplets
               SET cpu=:cpu, mem=:mem, disk=:disk, last_seen=:last_seen
             WHERE id=:id
        """, fields)
    return True


def list_droplets() -> dict:
    now = int(time.time())
    rows, healthy, down, cost_total = [], 0, 0, 0.0
    with conn() as c:
        for r in c.execute("SELECT * FROM droplets"):
            d = dict(r)
            status = "healthy" if (now - (d.get("last_seen") or 0)) < HEARTBEAT_TTL_SEC else "down"
            d["status"] = status
            rows.append(d)
            cost_total += float(d.get("cost_hour") or 0.0)
            if status == "healthy": healthy += 1
            else: down += 1
    return {
        "summary": {
            "total": len(rows),
            "healthy": healthy,
            "down": down,
            "cost_hour_total": round(cost_total, 6),
        },
        "droplets": rows,
    }
