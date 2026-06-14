# Coravida Design System

**Version:** 1.0  
**Created:** November 30, 2025

---

## Color Palette

### Primary Colors

| Name | Hex | Usage |
|------|-----|-------|
| Ocean Blue | `#0077B6` | Primary actions, headers, links |
| Jungle Green | `#2D6A4F` | Success states, nature elements |
| Sunset Gold | `#F4A261` | Highlights, Cora token accent |

### Secondary Colors

| Name | Hex | Usage |
|------|-----|-------|
| Deep Ocean | `#023E8A` | Dark backgrounds, footer |
| Light Sage | `#95D5B2` | Cards, subtle backgrounds |
| Warm Sand | `#E9C46A` | Hover states, borders |
| Coral | `#E76F51` | Alerts, discounts |

### Neutrals

| Name | Hex | Usage |
|------|-----|-------|
| White | `#FFFFFF` | Backgrounds |
| Off-White | `#F8F9FA` | Card backgrounds |
| Light Gray | `#E9ECEF` | Borders, dividers |
| Medium Gray | `#6C757D` | Secondary text |
| Dark Gray | `#343A40` | Body text |
| Near Black | `#1A1A2E` | Headings |

---

## Typography

### Font Families

```css
--font-heading: 'DM Sans', sans-serif;
--font-body: 'Inter', sans-serif;
--font-accent: 'Playfair Display', serif;
```

### Type Scale

| Element | Size | Weight | Line Height |
|---------|------|--------|-------------|
| H1 | 48px / 3rem | 700 | 1.2 |
| H2 | 36px / 2.25rem | 600 | 1.3 |
| H3 | 28px / 1.75rem | 600 | 1.4 |
| H4 | 22px / 1.375rem | 500 | 1.4 |
| Body Large | 18px / 1.125rem | 400 | 1.6 |
| Body | 16px / 1rem | 400 | 1.6 |
| Small | 14px / 0.875rem | 400 | 1.5 |
| Caption | 12px / 0.75rem | 400 | 1.4 |

---

## Page Layouts

### Homepage Structure

```
┌─────────────────────────────────────────────────────────────┐
│  HEADER: Logo | Experiences | About | Cora | Login          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  HERO SECTION                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Full-bleed image of Costa Rica                      │   │
│  │                                                       │   │
│  │  "Experience Life. Circulate Consciously."           │   │
│  │                                                       │   │
│  │  [Search: Where to? | What? | When?]                 │   │
│  │                                                       │   │
│  │  Pay with Cora tokens - Save up to 17%               │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  CATEGORY GRID                                              │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐          │
│  │Stays│ │Adven│ │Well │ │Retr │ │Culi │ │Cult │          │
│  │     │ │ture │ │ness │ │eats │ │nary │ │ural │          │
│  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘          │
├─────────────────────────────────────────────────────────────┤
│  FEATURED EXPERIENCES                                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ Image    │ │ Image    │ │ Image    │ │ Image    │       │
│  │          │ │          │ │          │ │          │       │
│  │ Title    │ │ Title    │ │ Title    │ │ Title    │       │
│  │ $XXX     │ │ $XXX     │ │ $XXX     │ │ $XXX     │       │
│  │ ⭐ 4.9   │ │ ⭐ 4.8   │ │ ⭐ 5.0   │ │ ⭐ 4.7   │       │
│  │ CORA -17%│ │ CORA -15%│ │ CORA -17%│ │ CORA -12%│       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
├─────────────────────────────────────────────────────────────┤
│  CORA TOKEN SECTION                                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  💰 Pay with Cora Tokens                             │   │
│  │                                                       │   │
│  │  • Save up to 17% on every booking                   │   │
│  │  • Earn tokens for reviews and referrals             │   │
│  │  • Support conscious circulation                     │   │
│  │                                                       │   │
│  │  [Learn More] [Get Cora Tokens]                      │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  ZEN VILLAGE FEATURE                                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Our Anchor Partner: Zen Village Costa Rica          │   │
│  │  [Image Gallery]                                      │   │
│  │  100% Cora Accepted | 5 Experience Types             │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  FOOTER                                                     │
│  About | Experiences | Partners | Cora | Contact           │
│  © 2025 Coravida | Part of the Cora Ecosystem              │
└─────────────────────────────────────────────────────────────┘
```

### Experience Card Component

```
┌────────────────────────────┐
│ ┌────────────────────────┐ │
│ │                        │ │
│ │       IMAGE            │ │
│ │                        │ │
│ │  ♥ (save)    ⭐ 4.9    │ │
│ └────────────────────────┘ │
│                            │
│ Wellness                   │  ← Category tag
│ Sunrise Yoga Retreat       │  ← Title
│ Zen Village, Costa Rica    │  ← Location
│                            │
│ From $299/night            │  ← Price
│ ┌──────────────────────┐   │
│ │ 🪙 Pay with Cora -17%│   │  ← Cora badge
│ └──────────────────────┘   │
└────────────────────────────┘
```

### Experience Detail Page

```
┌─────────────────────────────────────────────────────────────┐
│  HEADER                                                     │
├─────────────────────────────────────────────────────────────┤
│  ← Back to Experiences                                      │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │                                                        │ │
│  │                    HERO IMAGE                          │ │
│  │                                                        │ │
│  └───────────────────────────────────────────────────────┘ │
│  [img] [img] [img] [img] [+12 more]                        │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────┐ ┌───────────────────────┐ │
│  │                             │ │ BOOKING CARD          │ │
│  │  Sunrise Yoga Retreat       │ │                       │ │
│  │  ⭐ 4.9 (127 reviews)       │ │ $299/night            │ │
│  │  Zen Village, Costa Rica    │ │                       │ │
│  │                             │ │ ┌─────────────────┐   │ │
│  │  Description...             │ │ │ Check-in        │   │ │
│  │                             │ │ │ Dec 15, 2025    │   │ │
│  │  What's Included:           │ │ └─────────────────┘   │ │
│  │  ✓ Daily yoga sessions      │ │ ┌─────────────────┐   │ │
│  │  ✓ Organic meals            │ │ │ Check-out       │   │ │
│  │  ✓ Meditation classes       │ │ │ Dec 18, 2025    │   │ │
│  │  ✓ Spa access               │ │ └─────────────────┘   │ │
│  │                             │ │                       │ │
│  │  Host: Maria S.             │ │ Total: $897           │ │
│  │                             │ │                       │ │
│  │                             │ │ ┌─────────────────┐   │ │
│  │                             │ │ │ 🪙 CORA: $744   │   │ │
│  │                             │ │ │   Save $153!    │   │ │
│  │                             │ │ └─────────────────┘   │ │
│  │                             │ │                       │ │
│  │                             │ │ [Book Now]            │ │
│  └─────────────────────────────┘ └───────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  REVIEWS                                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ⭐⭐⭐⭐⭐ "Life-changing experience!" - John D.    │   │
│  │ ⭐⭐⭐⭐⭐ "The yoga sessions were incredible" - S. │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  SIMILAR EXPERIENCES                                        │
│  [Card] [Card] [Card] [Card]                               │
├─────────────────────────────────────────────────────────────┤
│  FOOTER                                                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Components

### Buttons

```css
/* Primary Button */
.btn-primary {
  background: #0077B6;
  color: white;
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
}

/* Cora Button */
.btn-cora {
  background: linear-gradient(135deg, #F4A261, #E76F51);
  color: white;
  padding: 12px 24px;
  border-radius: 8px;
}

/* Secondary Button */
.btn-secondary {
  background: transparent;
  border: 2px solid #0077B6;
  color: #0077B6;
  padding: 12px 24px;
  border-radius: 8px;
}
```

### Cora Savings Badge

```css
.cora-badge {
  background: linear-gradient(135deg, #F4A261, #E9C46A);
  color: #1A1A2E;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
}
```

---

## Responsive Breakpoints

| Breakpoint | Width | Columns |
|------------|-------|---------|
| Mobile | < 640px | 1 |
| Tablet | 640px - 1024px | 2 |
| Desktop | 1024px - 1440px | 3-4 |
| Large | > 1440px | 4 |

---

## Imagery Guidelines

### Photography Style
- Natural lighting, golden hour preferred
- Authentic moments, not overly staged
- Costa Rica landscapes: rainforest, beaches, volcanoes
- People in wellness activities: yoga, meditation, nature
- Local culture and community

### Image Dimensions

| Usage | Dimensions | Aspect Ratio |
|-------|------------|--------------|
| Hero | 1920x1080 | 16:9 |
| Experience Card | 400x300 | 4:3 |
| Gallery | 800x600 | 4:3 |
| Thumbnail | 200x200 | 1:1 |

---

## Animation Guidelines

- Use subtle transitions (200-300ms)
- Hover effects on cards: slight scale (1.02) + shadow
- Page transitions: fade in (300ms)
- Loading states: skeleton screens
- Scroll animations: fade-up on intersection

























