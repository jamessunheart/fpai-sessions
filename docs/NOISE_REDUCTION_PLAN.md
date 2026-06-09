# Noise Reduction Plan: Making the System Clear

## The Problem

**Too many ways to do the same thing = Confusion = Noise = Chaos**

## The Solution

**ONE way to do each thing = Clarity = Order = Flow**

---

## Priority 1: Mission System (CRITICAL)

### Current Chaos:
- Mission Hub (port 8700) ✅ REAL
- File-based missions (docs/) ❓
- File-based missions (core/) ❓
- Marketing missions (JSON) ❓
- Mission control scripts (3+ places) ❓

### Reduction:
1. **Mission Hub = THE Mission System**
   - Document this clearly
   - All missions go through Mission Hub API
   - File-based systems are deprecated

2. **Archive File-Based Systems**
   - Move to `.archive/missions/file-based/`
   - Add deprecation notice
   - Redirect to Mission Hub

3. **Remove Duplicate Scripts**
   - Keep ONE mission-control script
   - Remove others
   - Update references

**Result:** Clear answer - "Use Mission Hub API"

---

## Priority 2: Service Registry (CRITICAL)

### Current Chaos:
- Genesis registry (port 8150) ✅ REAL
- SERVICE_REGISTRY.json ❓
- SERVICE_CATALOG.json ❓
- SERVICE_REGISTRY.json.backup ❓

### Reduction:
1. **Genesis = THE Service Registry**
   - Document this clearly
   - All services register in Genesis
   - JSON files are deprecated

2. **Archive JSON Registries**
   - Move to `.archive/registries/`
   - Add deprecation notice
   - Redirect to Genesis

3. **Update All References**
   - Change code to query Genesis
   - Remove JSON registry code
   - Update documentation

**Result:** Clear answer - "Query Genesis API"

---

## Priority 3: Status Board (HIGH)

### Current Chaos:
- `core/STATE/NOW.md` ✅ REAL
- `docs/coordination/STATUS_BOARD.md` ❓
- `docs/coordination/SYSTEM_ARCHITECTURE_MAP.md` ❓
- `docs/coordination/REVENUE_PERFECTION_ENGINE.md` ❓

### Reduction:
1. **core/STATE/NOW.md = THE Status Board**
   - Document this clearly
   - All status updates go here
   - Other boards are deprecated

2. **Archive Other Status Boards**
   - Move to `.archive/status/`
   - Add deprecation notice
   - Redirect to NOW.md

3. **Consolidate Information**
   - Merge useful info into NOW.md
   - Remove duplicates
   - Keep ONE source of truth

**Result:** Clear answer - "Check core/STATE/NOW.md"

---

## Priority 4: Documentation Location (MEDIUM)

### Current Chaos:
- Docs in `docs/` folder
- Docs in `core/` folder
- Docs in `fullpotential_ai/fullpotential_core/docs/` folder
- Docs in service-specific folders

### Reduction:
1. **docs/ = THE Documentation Location**
   - Document this clearly
   - All docs go in `docs/`
   - Service docs in `docs/services/`

2. **Consolidate Existing Docs**
   - Move core docs to `docs/core/`
   - Move service docs to `docs/services/`
   - Archive old locations

3. **Create Documentation Index**
   - `docs/README.md` with structure
   - Clear navigation
   - Easy to find things

**Result:** Clear answer - "Check docs/"

---

## Priority 5: Service Deduplication (MEDIUM)

### Orchestrator Services:
- `SERVICES/orchestrator/` (port 8001)
- `SERVICES/orchestrator-unified/` (port 8600)

**Action:** Audit both, keep ONE, archive other

### God Mode Services:
- `SERVICES/god-mode/` (port 8300)
- `ops/godmode-v3/` (port 8300?)

**Action:** Audit both, keep ONE, archive other

### Consciousness Services (10+):
- Map all services
- Identify active ones
- Archive unused ones
- Document architecture

**Action:** Create `docs/services/consciousness-architecture.md`

### Treasury Services (5+):
- Map all services
- Identify canonical one
- Archive others

**Action:** Create `docs/services/treasury-architecture.md`

---

## Priority 6: Port Management (LOW)

### Current Chaos:
- Hardcoded ports everywhere
- Inconsistent URL patterns
- No port discovery

### Reduction:
1. **Use Genesis for Ports**
   - All services register ports in Genesis
   - Query Genesis for port info
   - Remove hardcoded ports

2. **Standardize URLs**
   - Use server IPs (not localhost)
   - Document URL patterns
   - Update all references

3. **Environment Variables**
   - All ports via env vars
   - Defaults in config
   - No hardcoded ports

---

## Implementation Order

### Week 1: Critical Reductions
1. ✅ Document Mission Hub as THE mission system
2. ✅ Document Genesis as THE service registry
3. ✅ Document NOW.md as THE status board
4. ✅ Archive deprecated systems

### Week 2: Service Deduplication
1. Audit orchestrator services
2. Audit god-mode services
3. Map consciousness services
4. Map treasury services

### Week 3: Documentation Consolidation
1. Consolidate docs to `docs/`
2. Create documentation index
3. Archive old locations

### Week 4: Port Standardization
1. Use Genesis for ports
2. Standardize URLs
3. Environment variables

---

## Success Metrics

### Before:
- Mission Systems: 5+
- Service Registries: 4+
- Status Boards: 4+
- Documentation Locations: 5+
- Duplicate Services: 10+
- Dead Code: ~180 services

### After:
- Mission Systems: 1
- Service Registries: 1
- Status Boards: 1
- Documentation Locations: 1
- Duplicate Services: 0
- Dead Code: Archived

**Target: 80% noise reduction**

---

## Quick Reference: The ONE Way

| Thing | THE ONE Way | Location |
|-------|-------------|----------|
| Missions | Mission Hub API | `http://198.54.123.234:8700/api/missions` |
| Service Registry | Genesis | `http://198.54.123.234:8150/registry/services` |
| Status Board | NOW.md | `core/STATE/NOW.md` |
| Documentation | docs/ | `docs/` |
| Port Info | Genesis | `http://198.54.123.234:8150/registry/services` |

**Memorize this. This is THE way.**







