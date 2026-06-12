# ⚡ God Mode

**The Omniscient View of the Full Potential OS.**

God Mode is a high-level meta-module designed to provide total system observability and control. Unlike standard services that perform specific tasks, God Mode sits above the architecture to map, verify, and synchronize the relationship between:
1. The **Codebase** (Static Truth)
2. The **Runtime State** (Dynamic Truth)
3. The **Core Consciousness** (SSOT/NOW.md)

## Components

### 1. `system_map.json`
The cartography of the OS. Defines layers (Consciousness, Infrastructure, Services, Interfaces) and their expected locations and states.

### 2. `sync_map.py`
The active process that keeps the map real. It:
- Scans the physical file structure.
- Ingests the `SSOT.json` from the Coordination core.
- Updates `system_map.json` to reflect reality.

### 3. Web Dashboard
A visualization of the System Map.
- **Live:** http://198.54.123.234:8300
- **Local:** http://localhost:8888

## Usage

### Sync Map
```bash
python3 godmode/sync_map.py
```

### Run Local Server
```bash
python3 godmode/server.py
```

## Deployment

God Mode is deployed as a systemd service on the production server.

**Service Location:** `/root/godmode`
**Port:** `8300`

To update deployment:
```bash
scp -r godmode/* root@198.54.123.234:/root/godmode/
ssh root@198.54.123.234 "systemctl restart godmode"
```

## Integration
God Mode is intended to be run by the **Coordinator** or **Architect** personas to ensure that the system's self-image matches reality.
