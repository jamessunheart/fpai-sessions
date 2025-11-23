# Mobile God Mode: Architecture Spec

**Status:** Draft
**Goal:** Deploy the "God Mode" Command Center to a secure public server with a mobile-friendly PWA (Progressive Web App) interface.

## 1. Architecture

### 1.1 Server (The Cloud Council)
Instead of running on `localhost`, we deploy the FastAPI server to your cloud VPS (e.g., DigitalOcean/AWS).
*   **Domain:** `command.fullpotential.ai` (or similar private subdomain)
*   **Security:** 
    *   **Auth:** OAuth2 (Google/GitHub) or a strong Magic Link system. **CRITICAL** since this controls the system.
    *   **SSL:** Let's Encrypt (Certbot).
    *   **Firewall:** Allow 443 (HTTPS) only from specific IPs or VPN if ultra-secure.

### 1.2 Mobile Interface (The Scepter)
We don't need a native iOS/Android app. A **PWA (Progressive Web App)** is superior here:
*   **Installable:** "Add to Home Screen" works instantly.
*   **Offline-Capable:** UI loads instantly; data syncs when connected.
*   **Push Notifications:** "Mission Complete" or "Security Alert" sent to your phone.

## 2. Deployment Plan

### Phase 1: Dockerize
Wrap `god_mode_server.py` and `librarian_server.py` into a single `docker-compose` stack.
*   `nginx`: Reverse proxy and SSL termination.
*   `god-mode`: The dashboard app.
*   `librarian`: The research tool.

### Phase 2: Authentication
Add `FastAPI-Users` or a simple middleware to `god_mode_server.py`.
*   Login screen requiring a Master Key (Environment Variable).

### Phase 3: Mobile UI Polish
Update `god_mode.html`:
*   Add `<meta name="viewport" ...>` for mobile scaling (Already done).
*   Add `manifest.json` for PWA installability (Icon, Name, Theme Color).
*   Make buttons "Thumb-Friendly" (larger touch targets).

## 3. Immediate Action (To prepare for this)

I can add the **PWA Manifest** and **Mobile Styles** to your current dashboard now. This ensures that when you *do* deploy it, it already looks and feels like an app on your phone.

Shall I upgrade the current dashboard to be "Mobile-Ready"?

