# Router Droplet - SPECS

**Droplet ID:** #102
**Version:** 1.0.0
**Status:** Planning

---

## Purpose

Receive incoming Telegram messages via webhook and route them to the appropriate specialized droplet (Trader, Brain, Memory, etc.). The Router is the "front door" - the only droplet that directly interfaces with Telegram.

---

## Requirements

### Functional Requirements
- [ ] Receive Telegram webhook POST requests
- [ ] Parse message content to determine intent
- [ ] Route trading-related messages to Trader droplet
- [ ] Route memory-related messages to Memory droplet
- [ ] Route general messages to Brain droplet
- [ ] Aggregate responses and send back to Telegram
- [ ] Handle callback queries (inline keyboards)
- [ ] Maintain user session context

### Non-Functional Requirements
- [ ] Must respond to Telegram within 5 seconds
- [ ] Must handle concurrent requests
- [ ] Must gracefully handle droplet unavailability
- [ ] Must not lose messages on routing failure

---

## API Specs

### UDC Endpoints (Required)

```
GET /health
Response: {"status": "healthy", "timestamp": "...", "uptime_seconds": N, "version": "1.0.0"}

GET /capabilities
Response: {"service_name": "router", "droplet_id": 102, "capabilities": [...]}

GET /state
Response: {"status": "active", "messages_routed": N, "active_routes": [...]}

GET /dependencies
Response: {"required_services": [...], "optional_services": [...]}

POST /message
Request: {"from_service": "...", "message_type": "...", "payload": {...}}
```

### Business Endpoints

```
POST /telegram/webhook
Request: Telegram Update object
Response: {"ok": true}

GET /routes
Response: Current routing table and droplet availability

POST /routes/{droplet}/health
Response: Check health of specific route target
```

---

## Dependencies

### Required Services
- Telegram Bot API (external)

### Optional Services
- trader (route to for trading messages)
- brain (route to for general AI messages)
- memory (route to for memory operations)
- alerts (route to for notification requests)

### Fallback Behavior
If a target droplet is unavailable:
1. Log the failure
2. Return "I'm having trouble with that right now. Please try again."
3. Notify Supervisor

---

## Routing Logic

```python
TRADING_KEYWORDS = ["sol", "btc", "eth", "trade", "position", "price", "buy", "sell", "long", "short"]
MEMORY_KEYWORDS = ["remember", "forget", "recall", "memory", "what do you know about"]
ALERT_KEYWORDS = ["alert", "notify", "remind"]

def route(message: str) -> str:
    text = message.lower()
    
    # Check for trading intent
    if any(kw in text for kw in TRADING_KEYWORDS):
        return "trader"
    
    # Check for memory intent
    if any(kw in text for kw in MEMORY_KEYWORDS):
        return "memory"
    
    # Check for alert intent
    if any(kw in text for kw in ALERT_KEYWORDS):
        return "alerts"
    
    # Default to brain for general conversation
    return "brain"
```

---

## Success Criteria

- [ ] Correctly routes trading messages to Trader
- [ ] Correctly routes memory messages to Memory
- [ ] Correctly routes general messages to Brain
- [ ] Responds to Telegram within 5 seconds
- [ ] Handles droplet unavailability gracefully
- [ ] Passes all UDC compliance tests
- [ ] Has >80% test coverage

---

## Configuration

```bash
# Environment Variables
ROUTER_PORT=8750
TELEGRAM_BOT_TOKEN=<token>
TRADER_URL=http://localhost:8751
BRAIN_URL=http://localhost:8752
MEMORY_URL=http://localhost:8753
ALERTS_URL=http://localhost:8765
REQUEST_TIMEOUT_SECONDS=10
```

---

## Compliance Notes

- Processes user messages (contains PII)
- Must not log full message content in production
- Must validate Telegram webhook signature








