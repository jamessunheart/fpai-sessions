# hub - SPECS

**Created:** 2025-11-15
**Status:** Operational
**Port:** 8500

---

## Purpose

Central landing page for fullpotential.com directing visitors to all Full Potential services. Provides overview of company structure, service directory, and clear CTAs for each service.

---

## Requirements

### Functional Requirements
- [ ] Landing page with beautiful gradient design
- [ ] Services grid displaying all 6 services
- [ ] Status badges (Live, Coming Soon)
- [ ] Detailed service descriptions with clear value props
- [ ] CTA buttons linking to each service
- [ ] Responsive design (mobile, tablet, desktop)
- [ ] Professional corporate structure presentation
- [ ] About Us section
- [ ] Contact information

### Non-Functional Requirements
- [ ] Performance: Page load < 2 seconds
- [ ] Design: Professional, modern, gradient aesthetic
- [ ] SEO: Meta tags, proper heading structure
- [ ] Accessibility: WCAG 2.1 AA compliance
- [ ] Mobile-first: Responsive on all screen sizes

---

## API Specs

### Endpoints

**GET /**
- **Purpose:** Main hub landing page
- **Input:** None
- **Output:** HTML page with service directory
- **Success:** 200 OK
- **Errors:** 500 if template fails

**GET /health**
- **Purpose:** Health check
- **Input:** None
- **Output:** {"status": "healthy", "service": "hub"}
- **Success:** 200 OK
- **Errors:** 500 if unhealthy

### Data Models

```python
class Service:
    name: str
    description: str
    url: str
    status: str  # "live", "coming_soon"
    icon: str
    category: str  # "marketplace", "coaching", "finance", "ai", "community"
```

---

## Dependencies

### External Services
- None (static site)

### APIs Required
- None

### Data Sources
- Static service information (hardcoded in template)

---

## Success Criteria

How do we know this works?

- [ ] Hub accessible at fullpotential.com
- [ ] All services listed with correct information
- [ ] CTAs link to correct service URLs
- [ ] Mobile responsive design works
- [ ] Page loads in < 2 seconds
- [ ] Health check returns 200 OK
- [ ] Professional appearance matches brand

---

## Services Directory

### 1. I MATCH Marketplace
**Status:** Live
**URL:** /match
**Description:** High-value talent marketplace connecting experts with opportunities

### 2. White Rock Coaching
**Status:** Live
**URL:** /coaching
**Description:** Personal transformation coaching for human flourishing

### 3. Treasury Optimization
**Status:** Coming Soon
**URL:** /treasury
**Description:** Autonomous DeFi portfolio management with AI-driven decisions

### 4. AI Services
**Status:** Coming Soon
**URL:** /ai
**Description:** AI-powered business automation and intelligence services

### 5. Church Community
**Status:** Coming Soon
**URL:** /church
**Description:** 508(c)(1)(A) church formation and compliance resources

### 6. About Us
**Status:** Live
**URL:** /about
**Description:** Company mission, vision, and team

---

## URL Structure

```
fullpotential.com (Nginx)
  │
  ├── / → Hub (port 8500) [Main landing]
  ├── /coaching → White Rock (port 8000)
  ├── /match → I MATCH (port 8401)
  ├── /treasury → Treasury (port 8600)
  ├── /ai → AI Services (port 8700)
  └── /church → Church (port 8800)
```

---

## Technical Constraints

- **Language/Framework:** Python 3.11+ with FastAPI
- **Port:** 8500
- **Resource limits:**
  - Memory: 128MB max
  - CPU: 0.25 cores
  - Storage: 50MB for static assets
- **Response time:** < 2 seconds
- **Static assets:** Images, CSS served efficiently
- **Caching:** Browser caching for static assets

---

## Migration Notes

**Old setup:**
- fullpotential.com → White Rock Coaching (root)

**New setup:**
- fullpotential.com → Hub (root)
- fullpotential.com/coaching → White Rock Coaching

**Redirects needed:**
```nginx
rewrite ^/sessions /coaching/sessions permanent;
rewrite ^/membership /coaching/membership permanent;
rewrite ^/login /coaching/login permanent;
rewrite ^/dashboard /coaching/dashboard permanent;
```

---

**Next Step:** Deploy hub to production server, update nginx config, migrate fullpotential.com
