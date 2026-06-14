# landing-page - SPECS

**Created:** 2025-11-15
**Status:** MVP
**Port:** 8001

---

## Purpose

Main landing page for fullpotential.ai showcasing vision, progress toward Paradise (11 droplets), and live system metrics. Attracts users, investors, and apprentices by demonstrating the FPAI system in action.

---

## Requirements

### Functional Requirements
- [ ] Landing page with vision statement
- [ ] Live progress widget showing Paradise progress (droplets built / total)
- [ ] Real-time metrics from Dashboard API
- [ ] Responsive mobile-first design
- [ ] Clear value proposition
- [ ] Call-to-action buttons
- [ ] Links to services and documentation
- [ ] Year auto-update in footer

### Non-Functional Requirements
- [ ] Performance: Page load < 2 seconds
- [ ] Design: Modern, professional, gradient aesthetic
- [ ] Real-time: Progress updates every 30 seconds
- [ ] Fallback: Graceful degradation if Dashboard API unavailable
- [ ] SEO: Proper meta tags and structure

---

## API Specs

### Endpoints

**GET /**
- **Purpose:** Main landing page
- **Input:** None
- **Output:** HTML page with live metrics
- **Success:** 200 OK
- **Errors:** 500 if template fails

**GET /health**
- **Purpose:** Health check
- **Input:** None
- **Output:** {"status": "active", "service": "landing-page", "timestamp": "..."}
- **Success:** 200 OK
- **Errors:** 500 if unhealthy

### Data Models

```python
class ProgressData:
    progress_percent: int
    droplets_built: int
    droplets_total: int
```

---

## Dependencies

### External Services
- Dashboard API (Port 8002): Live progress metrics

### APIs Required
- Dashboard API: GET /api/paradise-progress

### Data Sources
- Dashboard API for real-time metrics
- Static content for vision and value props

---

## Success Criteria

How do we know this works?

- [ ] Landing page loads in < 2 seconds
- [ ] Live progress widget displays correct metrics
- [ ] Metrics update from Dashboard API
- [ ] Fallback to default values if API unavailable
- [ ] Mobile responsive design works
- [ ] Health check returns 200 OK
- [ ] Professional appearance

---

## Live Metrics

**From Dashboard API:**
- progress_percent: Overall system completion percentage
- droplets_built: Number of droplets completed
- droplets_total: Total droplets planned (11 for Paradise)

**Update frequency:** Every 30 seconds

**Fallback values:**
```python
{
    "progress_percent": 36,
    "droplets_built": 5,
    "droplets_total": 11
}
```

---

## Technical Constraints

- **Language/Framework:** Python 3.11+ with FastAPI
- **Port:** 8001
- **Resource limits:**
  - Memory: 128MB max
  - CPU: 0.25 cores
  - Storage: 50MB for static assets
- **Response time:** < 2 seconds
- **Static assets:** Minimal, inline CSS
- **API timeout:** 3 seconds for Dashboard API

---

**Next Step:** Deploy to fullpotential.ai production server
