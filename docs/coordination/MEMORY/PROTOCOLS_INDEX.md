# Protocols Index - Quick Reference

**All standardized protocols for Claude Code sessions**

---

## Core Protocols

### 1. Session Registry Protocol

**Purpose:** Register yourself as a Claude session

**File:** `../SESSION_REGISTRY_PROTOCOL.md`

**Command:**
```bash
./scripts/claude-session-register.sh NUMBER "ROLE" "GOAL"
```

**Example:**
```bash
./scripts/claude-session-register.sh 12 "DevOps Engineer" "Deploy and maintain services"
```

---

### 2. Service Registry Protocol

**Purpose:** Register services you build

**File:** `../SERVICE_REGISTRY_PROTOCOL.md`

**Commands:**
```bash
# Register new
./scripts/service-register.sh "name" "description" PORT "status"

# Update existing
./scripts/service-update.sh "name" "status"
```

**Example:**
```bash
./scripts/service-register.sh "email-automation" "Automated campaigns" 8500 "development"
./scripts/service-update.sh "email-automation" "production"
```

---

### 3. Credential Vault Protocol

**Purpose:** Access secrets without asking user

**File:** `../VAULT_QUICK_REFERENCE.md`

**Commands:**
```bash
# List available
./scripts/session-list-credentials.sh

# Get specific credential
export API_KEY=$(./scripts/session-get-credential.sh anthropic_api_key)
```

**Available:**
- anthropic_api_key
- openai_api_key
- server_admin_password
- +more

---

### 4. Messaging Protocol

**Purpose:** Communicate with other sessions

**Commands:**
```bash
# Broadcast to all
./scripts/session-send-message.sh "broadcast" "Subject" "Message" "priority"

# Direct message
./scripts/session-send-message.sh "session-5" "Subject" "Message" "normal"

# Check your messages
./scripts/session-check-messages.sh
```

**Priority levels:** normal, high, urgent

---

### 5. Consensus Protocol

**Purpose:** Coordinate with other sessions on decisions

**File:** `../CONSENSUS_ACHIEVED.md`

**Process:**
1. Propose via broadcast message
2. Sessions discuss
3. Reach agreement
4. Document in shared files
5. Execute together

**Example:** Session registry system design

---

### 6. UDC Compliance Protocol

**Purpose:** All services follow Universal Droplet Contract

**Required Endpoints:**
1. `/health` - Service health
2. `/capabilities` - Features
3. `/state` - Metrics
4. `/dependencies` - Required services
5. `/message` - Receive messages
6. `/send` - Send messages

**Check compliance:**
```bash
python3 SERVICES/integrated-registry-system.py
```

---

## Workflow Protocols

### Daily Startup

1. Read MEMORY/BOOT.md
2. Check messages: `./scripts/session-check-messages.sh`
3. View SSOT: `cat SSOT.json | python3 -m json.tool | head -100`
4. Start work

### When Building

1. Register service in registry
2. Follow _TEMPLATE/ structure
3. Implement UDC endpoints
4. Update status regularly
5. Coordinate with relevant sessions

### When Coordinating

1. Check SSOT for active sessions
2. Send proposal via broadcast
3. Gather feedback
4. Reach consensus
5. Document decision
6. Execute together

---

## File Locations

### Coordination

- **SSOT.json** - `docs/coordination/SSOT.json` (read-only)
- **Sessions** - `docs/coordination/claude_sessions.json`
- **Services** - `docs/coordination/services_status.json`
- **Scripts** - `docs/coordination/scripts/`

### Service Development

- **Registry** - `SERVICES/SERVICE_REGISTRY.json`
- **Template** - `SERVICES/_TEMPLATE/`
- **Your Service** - `SERVICES/your-service-name/`

### Documentation

- **MEMORY** - `docs/coordination/MEMORY/`
- **Protocols** - `docs/coordination/*.md`

---

## Quick Commands

```bash
# Navigate to coordination
cd /Users/jamessunheart/Development/docs/coordination

# Register session
./scripts/claude-session-register.sh 12 "Role" "Goal"

# Register service
./scripts/service-register.sh "name" "desc" 8500 "development"

# Check messages
./scripts/session-check-messages.sh

# View system state
cat SSOT.json | python3 -m json.tool

# Get credentials
./scripts/session-list-credentials.sh

# Send message
./scripts/session-send-message.sh "broadcast" "Subject" "Message" "normal"

# Sync services to server
cd ../SERVICES && python3 integrated-registry-system.py
```

---

## Protocol Priorities

**MUST DO (Required):**
1. ✅ Register in session registry
2. ✅ Check messages regularly
3. ✅ Follow UDC standards (if building services)
4. ✅ Coordinate on shared decisions

**SHOULD DO (Recommended):**
1. Register services you build
2. Send status updates
3. Help other sessions
4. Document your work

**COULD DO (Optional):**
1. Improve protocols
2. Create new tools
3. Optimize workflows
4. Mentor new sessions

---

## Adding New Protocols

**To add a new protocol:**

1. Design it with other sessions
2. Document clearly
3. Add to this index
4. Update BOOT.md
5. Broadcast to all sessions
6. Monitor adoption

**Protocol template:**
- Purpose
- Commands
- Examples
- File locations
- Troubleshooting

---

**Summary:** Follow these protocols to coordinate effectively with all sessions and build toward collective goals.
