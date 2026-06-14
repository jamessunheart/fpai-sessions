# Alerts Service

**Droplet ID:** #106
**Version:** 1.0.0
**Status:** Ready for Deployment
**Last Updated:** 2026-04-29

---

## Overview

Centralized notification service for all droplets in the FPAI ecosystem. Supports multiple notification channels with intelligent queuing, rate limiting, and automatic retries.

### Features

- **Multi-Channel Support**: Telegram, SMS, Email (extensible)
- **Smart Queuing**: Priority-based message queuing with configurable limits
- **Rate Limiting**: Per-channel rate limits to prevent API throttling
- **Auto-Retry**: Automatic retry with exponential backoff for failed sends
- **Templates**: Predefined message templates for common notifications
- **UDC Compliant**: Full support for Unified Droplet Communication protocol
- **Delivery Tracking**: Track notification status and delivery history

---

## Quick Start

### 1. Configuration

Copy the example environment file and configure:

```bash
cp .env.example .env
# Edit .env with your credentials
```

### 2. Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the service
python -m app.main
```

### 3. Docker

```bash
# Build
docker build -t alerts:latest .

# Run
docker run -p 8765:8765 --env-file .env alerts:latest
```

---

## API Documentation

Once running, visit:
- **Interactive Docs**: http://localhost:8765/docs
- **ReDoc**: http://localhost:8765/redoc

### UDC Endpoints (Required)

```
GET  /health          - Health check
GET  /capabilities    - Service capabilities
GET  /state           - Current service state
GET  /dependencies    - Service dependencies
POST /message         - Receive UDC messages
```

### Business Endpoints

```
POST /send                    - Send notification
POST /send/template           - Send templated notification
GET  /queue                   - Queue statistics
GET  /history                 - Notification history
GET  /status/{message_id}     - Check notification status
POST /channels/{channel}/test - Test channel connectivity
GET  /templates               - List available templates
POST /templates               - Add custom template
```

---

## Progress

### Complete ✅
- [x] SPECS.md written
- [x] Directory structure created
- [x] Core implementation
- [x] UDC endpoints
- [x] Telegram integration
- [x] SMS integration
- [x] Rate limiting
- [x] Queue system
- [x] Template system
- [x] Dockerfile created
- [x] Requirements defined

### Pending ⏳
- [ ] Tests
- [ ] Deployment
- [ ] Production configuration

---

## Templates

Built-in message templates:

- `trade_alert` - Trading activity notifications
- `position_closed` - Position closure with P&L
- `droplet_restart` - Service restart notifications
- `error_alert` - Error notifications
- `daily_summary` - Daily summary reports
- `system_status` - System status updates
- `health_warning` - Service health warnings
- `deployment_success` - Successful deployments
- `deployment_failed` - Failed deployments
- `budget_alert` - Budget threshold alerts

---

## Configuration

See `.env.example` for all available configuration options.

Key settings:
- `TELEGRAM_BOT_TOKEN` - Your Telegram bot token
- `TELEGRAM_STEWARD_CHAT_ID` - Default recipient chat ID
- `TWILIO_*` - Twilio credentials for SMS
- `*_RATE_LIMIT` - Messages per minute per channel
- `*_RETRY_COUNT` - Max retry attempts per channel

---

## Support

For issues or questions, contact the Full Potential team or file an issue in the coordination system.

