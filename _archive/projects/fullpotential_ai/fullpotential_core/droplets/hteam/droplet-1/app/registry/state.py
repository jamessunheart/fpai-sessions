import os
REGISTRY = {}
HEARTBEAT_TTL_SEC = int(os.getenv("REGISTRY_TTL_SEC", "180"))
