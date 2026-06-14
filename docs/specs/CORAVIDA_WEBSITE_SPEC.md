# Coravida.com Website Specification

**Version:** 1.0  
**Created:** November 30, 2025  
**Status:** Active Development

---

## Vision

Coravida.com is the premier wellness experiences marketplace, launching in Costa Rica and expanding globally. It serves as the primary real-world use case for Cora tokens, demonstrating the value of conscious circulation through transformative experiences.

**Tagline:** "Experience Life. Circulate Consciously."

---

## Site Architecture

### Primary Pages

| Page | Purpose |
|------|---------|
| **Homepage** | Hero showcase of featured experiences with Cora token value proposition |
| **Experiences Catalog** | Filterable grid of all experiences by category |
| **Experience Detail** | Individual experience pages with booking |
| **About Coravida** | Mission, vision, connection to Cora ecosystem |
| **Cora Token** | How to earn, spend, and benefit from Cora tokens |
| **Host/Partner Portal** | For experience providers to list offerings |
| **Member Dashboard** | Booking history, Cora balance, saved experiences |
| **Blog/Journal** | Wellness content, Costa Rica guides, partner stories |

### Experience Categories (Phase 1 - Costa Rica)

| Category | Examples |
|----------|----------|
| **Stays** | Zen Village retreats, eco-lodges, wellness resorts |
| **Adventures** | Volcano tours, rainforest expeditions, surfing |
| **Wellness** | Yoga retreats, meditation, spa treatments, detox |
| **Retreats** | Multi-day transformation programs, corporate retreats |
| **Culinary** | Farm-to-table experiences, cooking classes, food tours |
| **Cultural** | Local community visits, artisan workshops, ceremonies |

---

## Cora Token Integration

### Payment Options

| Option | Description | Benefit |
|--------|-------------|---------|
| **100% Cora** | Pay entirely with Cora tokens | Up to 17% discount |
| **Hybrid** | Partial Cora + USD | Proportional savings |
| **USD Only** | Standard pricing | Earn Cora on purchase |

### Token Mechanics

- Users earn Cora tokens for reviews, referrals, repeat bookings
- Hosts receive Cora tokens (can convert to USD or hold)
- Loyalty tiers unlock better Cora rates
- Special "Cora-Only" exclusive experiences

### Integration Points

- FP Credits Gateway (port 8765) for Cora balance/transactions
- Real-time Cora value/savings display
- Wallet connection for Cora holders

---

## Technical Implementation

### Phase 1: WordPress Enhancement

Upgrade existing WordPress installation on Third Server (209.74.93.72):

1. **Theme:** Modern wellness theme with custom styling
2. **Booking:** WooCommerce Bookings for experience reservations
3. **Payments:** Custom Cora payment gateway plugin
4. **API:** Integration to FP Credits system

### Phase 2: Custom Application (Future)

Migrate to Next.js application for:
- Server-side rendering for SEO
- Direct API integration with Cora ecosystem
- Real-time availability and pricing
- Progressive Web App capabilities

---

## Design Direction

### Visual Identity

- **Primary Colors:** Ocean Blue (#0077B6), Jungle Green (#2D6A4F), Sunset Gold (#F4A261)
- **Typography:** DM Sans (headings), Inter (body)
- **Imagery:** High-quality Costa Rica photography
- **Mood:** Aspirational, transformative, natural

### Key Design Elements

- Full-bleed hero images with experience highlights
- Card-based experience browsing
- Prominent Cora savings callouts
- Trust indicators (reviews, certifications, partner badges)
- Mobile-first responsive design

---

## Phase 1 Launch Content

### Anchor Property: Zen Village Costa Rica

- Primary featured partner
- Multiple experience types (stays, wellness, retreats)
- Case study for Cora token adoption
- URL: zenvillagecr.com

### Initial Experience Partners (Target 10-15)

- Wellness retreats and yoga centers
- Adventure tour operators
- Eco-lodges and boutique hotels
- Local guides and cultural experiences

---

## Future Expansion (Phase 2+)

### Geographic Expansion

1. Mexico (Tulum, Oaxaca)
2. Bali, Indonesia
3. Portugal
4. Thailand
5. Global wellness destinations

### Platform Features

- Host self-service listing
- Dynamic pricing with Cora incentives
- Community features (groups, forums)
- Experience bundling and packages

---

## Success Metrics

| Metric | Phase 1 Target |
|--------|----------------|
| Listed Experiences | 25+ |
| Monthly Bookings | 50+ |
| Cora Token Transactions | 30% of bookings |
| Partner Satisfaction | 4.5+ stars |
| User Reviews | 100+ |

---

## Technical Details

### Server Location

- **Host:** Third Server (209.74.93.72)
- **Account:** coravida
- **Path:** /home/coravida/public_html/
- **Database:** coravida_wp1

### Related Domains

- coravida.com (main site)
- experiences.coravida.com (subdomain)
- support.coravida.com (help desk)

### API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /api/experiences` | List all experiences |
| `GET /api/experiences/:id` | Get experience details |
| `POST /api/bookings` | Create booking |
| `GET /api/cora/balance` | Get user Cora balance |
| `POST /api/cora/pay` | Process Cora payment |

---

## Implementation Status

- [x] Domain routing fixed (via Main Server proxy)
- [x] SSL certificate configured
- [x] WordPress proxy trust configured
- [ ] New theme installed
- [ ] Experience categories created
- [ ] Cora payment integration
- [ ] Initial content populated
- [ ] Partner onboarding

---

**Related Documents:**
- [ORGANIZATIONAL_STRUCTURE.md](../../docs/legal/church/ORGANIZATIONAL_STRUCTURE.md)
- [DOMAIN_STRATEGY.md](../../SERVICES/DOMAIN_STRATEGY.md)

























