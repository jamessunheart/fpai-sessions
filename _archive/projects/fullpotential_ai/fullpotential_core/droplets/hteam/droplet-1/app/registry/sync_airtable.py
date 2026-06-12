import os, time, threading, logging, traceback, fcntl

from adapters.airtable_client import Airtable
from .store import list_droplets

log = logging.getLogger("airtable")
log.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("[airtable] %(message)s"))
log.addHandler(handler)

LOCK_PATH = os.getenv("AIRTABLE_SYNC_LOCK", "/tmp/airtable_sync.lock")

def _acquire_singleton_lock():
    """Returns a file object if we hold the lock; None otherwise."""
    try:
        f = open(LOCK_PATH, "w")
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        f.write(str(os.getpid()))
        f.flush()
        return f
    except Exception:
        return None

def start_sync_loop(interval=60):
    token = os.getenv("AIRTABLE_TOKEN")
    base  = os.getenv("AIRTABLE_BASE_ID")
    table = os.getenv("AIRTABLE_TABLE", "Droplets")
    if not (token and base):
        log.info("disabled: missing AIRTABLE_* envs")
        return

    lock = _acquire_singleton_lock()
    if lock is None:
        log.info("another worker already runs the sync loop; skipping")
        return

    at = Airtable()  # single global client
    log.info(f"sync loop started → table={table} interval={interval}s")

    def loop():
        while True:
            try:
                data = list_droplets()
                rows = data.get("droplets", [])
                if not rows:
                    log.info("nothing to sync")
                else:
                    synced = 0
                    for d in rows:
                        fields = {
                            "fqdn": d.get("fqdn"),
                            "name": d.get("name"),
                            "status": d.get("status"),
                            "last_seen": int(d.get("last_seen") or 0),
                            # cpu/mem/disk are 0–100 numeric now
                            "cpu": d.get("cpu"),
                            "mem": d.get("mem"),
                            "disk": d.get("disk"),
                            "cost_hour": d.get("cost_hour"),
                            "ip": d.get("ip"),
                            "role": d.get("role"),
                            "env": d.get("env"),
                            "version": d.get("version"),
                        }
                        at.upsert_one(fields)
                        synced += 1
                    log.info(f"upserted {synced} records")
            except Exception as e:
                log.info(f"sync error: {e}")
                traceback.print_exc()
            time.sleep(int(os.getenv("AIRTABLE_SYNC_SEC", str(interval))))
    threading.Thread(target=loop, daemon=True).start()