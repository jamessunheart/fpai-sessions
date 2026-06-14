# Memory Droplet - SPECS

**Droplet ID:** #105
**Version:** 1.0.0
**Status:** Planning

---

## Purpose

Store and retrieve memories using a hybrid local (SQLite) + cloud (Mem0) system. Provides persistent memory for all other droplets.

---

## Requirements

### Functional Requirements
- [ ] Store memories with metadata
- [ ] Retrieve memories by query (semantic search)
- [ ] Sync local memories to Mem0 cloud
- [ ] Handle memory deduplication
- [ ] Support memory categories (trading, conversation, system)
- [ ] Provide memory decay/cleanup

### Non-Functional Requirements
- [ ] Must respond to queries within 500ms
- [ ] Must persist locally even if cloud unavailable
- [ ] Must handle concurrent read/write
- [ ] Must not exceed 1GB local storage

---

## API Specs

### UDC Endpoints (Required)

```
GET /health
Response: {"status": "healthy", "timestamp": "...", "uptime_seconds": N, "version": "1.0.0"}

GET /capabilities
Response: {"service_name": "memory", "droplet_id": 105, "capabilities": [...]}

GET /state
Response: {"status": "active", "local_memories": N, "cloud_synced": N}

GET /dependencies
Response: {"required_services": [...], "optional_services": [...]}

POST /message
Request: {"from_service": "brain", "message_type": "query", "payload": {"action": "remember", "content": "..."}}
Response: {"received": true, "status": "completed", "result": {"memory_id": "..."}}
```

### Business Endpoints

```
POST /remember
Request: {"content": "...", "category": "trading", "metadata": {...}}
Response: {"memory_id": "...", "stored_at": "..."}

POST /recall
Request: {"query": "...", "category": "trading", "limit": 5}
Response: {"memories": [...], "count": N}

DELETE /forget/{memory_id}
Response: {"deleted": true}

GET /memories
Response: List of all memories (paginated)

POST /sync
Response: Trigger manual sync to Mem0 cloud

GET /stats
Response: Memory statistics (count, size, categories)
```

---

## Dependencies

### Required Services
- SQLite (local database)

### Optional Services
- Mem0 API (cloud sync)

---

## Data Models

```python
@dataclass
class Memory:
    id: str
    content: str
    category: str  # "trading" | "conversation" | "system" | "user"
    metadata: dict
    embedding: Optional[List[float]]
    created_at: datetime
    accessed_at: datetime
    access_count: int
    synced_to_cloud: bool
```

---

## Storage Strategy

```
LOCAL (SQLite):
- All memories stored locally first
- Fast reads, offline capable
- Auto-cleanup of old memories

CLOUD (Mem0):
- Important memories synced to cloud
- Semantic search capabilities
- Cross-session persistence

SYNC RULES:
- Sync every 5 minutes
- Sync on shutdown
- Sync when memory is accessed 3+ times
```

---

## Success Criteria

- [ ] Can store and retrieve memories
- [ ] Persists locally on restart
- [ ] Syncs to Mem0 when available
- [ ] Handles semantic queries
- [ ] Passes all UDC compliance tests
- [ ] Has >80% test coverage

---

## Configuration

```bash
# Environment Variables
MEMORY_PORT=8753
SQLITE_PATH=/opt/fpai/memory-droplet/data/memories.db
MEM0_API_KEY=<key>
MEM0_USER_ID=aria_identity
SYNC_INTERVAL_SECONDS=300
MAX_LOCAL_MEMORIES=10000
MEMORY_DECAY_DAYS=90
```

---

## Compliance Notes

- Stores user conversation data
- Must handle data deletion requests
- Must encrypt sensitive memories
- Cloud sync must be optional (offline-capable)








