# FPAI Services Index

**Total Services:** 261
**Last Updated:** 2026-04-29

---

## Quick Find

Looking for a specific service? Use Cmd+F to search this page.

---

## Core Services

### Infrastructure
- **alerts** (#106) - Centralized notification service (Telegram, SMS)
- **nerve-center** - System coordination
- **god-mode** - Admin dashboard
- **supervisor** - Service orchestration

### Intelligence
- **sunheart-brain** - Knowledge base and memory
- **strategic-intelligence** - Strategic analysis
- **data-service** - Data collection and processing
- **consciousness** - System consciousness

### Customer-Facing
- **concierge** - Customer service AI
- **ad-portal** - Advertising management
- **i-match** - Matching engine
- **membership** - Member management

### Trading & Finance
- **fp-index** - Full Potential Index
- **whaletrack-magnet-engine** - Trading signals
- **streasury-bot** - Treasury management

---

## All Services (Alphabetical)

Use `ls SERVICES/` to see the complete current list.

To get details on any service:
```bash
cat SERVICES/{service-name}/README.md
cat SERVICES/{service-name}/SPECS.md
```

---

## Service Structure

Every service should have:
- `README.md` - Documentation
- `SPECS.md` - Specifications
- `Dockerfile` - Container configuration
- `requirements.txt` - Dependencies
- `app/` - Application code
- `tests/` - Test suite

**Reference implementation:** See `SERVICES/alerts/` for a complete example.

---

## Adding a New Service

1. Create directory: `mkdir SERVICES/my-service`
2. Copy structure from `SERVICES/alerts/`
3. Update README.md and SPECS.md
4. Implement service
5. Add to this index
6. Deploy

---

**For full structure guide, see:** `/STRUCTURE.md`
