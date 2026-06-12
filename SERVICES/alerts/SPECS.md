# Alerts Droplet - SPECS

**Droplet ID:** #106
**Version:** 1.0.0
**Status:** Planning

---

## Purpose

Send notifications via Telegram, SMS, and other channels. Provides a centralized notification service for all droplets.

---

## Requirements

### Functional Requirements
- [ ] Send Telegram messages to specified chat IDs
- [ ] Support multiple notification channels (Telegram, SMS)
- [ ] Queue notifications to prevent flooding
- [ ] Track notification delivery status
- [ ] Support notification templates
- [ ] Rate limit per channel

### Non-Functional Requirements
- [ ] Must queue messages if Telegram is unavailable
- [ ] Must not send more than 30 messages/minute to same chat
- [ ] Must retry failed sends up to 3 times
- [ ] Must log all sent notifications

---

## API Specs

### UDC Endpoints (Required)

```
GET /health
Response: {"status": "healthy", "timestamp": "...", "uptime_seconds": N, "version": "1.0.0"}

GET /capabilities
Response: {"service_name": "alerts", "droplet_id": 106, "capabilities": [...]}

GET /state
Response: {"status": "active", "queued": N, "sent_today": N}

GET /dependencies
Response: {"required_services": [...], "optional_services": [...]}

POST /message
Request: {"from_service": "supervisor", "message_type": "task_assignment", "payload": {"channel": "telegram", "text": "..."}}
Response: {"received": true, "status": "queued", "message_id": "..."}
```

### Business Endpoints

```
POST /send
Request: {"channel": "telegram", "recipient": "123456", "message": "...", "priority": "normal"}
Response: {"message_id": "...", "status": "queued"}

POST /send/template
Request: {"template": "trade_alert", "recipient": "123456", "data": {...}}
Response: {"message_id": "...", "status": "queued"}

GET /queue
Response: Current notification queue

GET /history
Response: Sent notification history (paginated)

POST /channels/{channel}/test
Response: Send test message to channel
```

---

## Dependencies

### Required Services
- Telegram Bot API

### Optional Services
- SMS Provider (Twilio)
- Email Provider (SendGrid)

---

## Notification Channels

```python
CHANNELS = {
    "telegram": {
        "rate_limit": 30,  # per minute
        "retry_count": 3,
        "retry_delay": 5  # seconds
    },
    "sms": {
        "rate_limit": 5,
        "retry_count": 2,
        "retry_delay": 10
    }
}
```

---

## Templates

```python
TEMPLATES = {
    "trade_alert": "🚨 Trade Alert: {symbol} {side} at ${price}",
    "position_closed": "✅ Position Closed: {symbol} P&L: {pnl}",
    "droplet_restart": "🔄 Droplet Restarted: {name} - {reason}",
    "error_alert": "❌ Error in {service}: {error}",
    "daily_summary": "📊 Daily Summary:\n- Trades: {trades}\n- P&L: {pnl}"
}
```

---

## Success Criteria

- [ ] Can send Telegram messages
- [ ] Queues messages when rate limited
- [ ] Retries failed sends
- [ ] Tracks delivery status
- [ ] Passes all UDC compliance tests
- [ ] Has >80% test coverage

---

## Configuration

```bash
# Environment Variables
ALERTS_PORT=8765
TELEGRAM_BOT_TOKEN=<token>
TELEGRAM_STEWARD_CHAT_ID=<chat_id>
TWILIO_ACCOUNT_SID=<sid>
TWILIO_AUTH_TOKEN=<token>
TWILIO_PHONE_NUMBER=<number>
MAX_QUEUE_SIZE=1000
RATE_LIMIT_WINDOW_SECONDS=60
```

---

## Compliance Notes

- Handles user contact information
- Must respect user notification preferences
- Must not spam users
- Must log all notifications for audit








