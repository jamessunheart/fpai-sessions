---
title: WhaleTrack Dashboard Plan
status: spec
location: https://fullpotential.ai/dashboards/whaletrack
---

## 1. Purpose

Create a dedicated dashboard under the existing `/dashboards` estate that visualizes the WhaleTrack trading engine in real time (paper or live mode) using the activity APIs defined in `DASHBOARD_SPEC.md`.

## 2. Deployment Target

- **URL:** `https://fullpotential.ai/dashboards/whaletrack`
- **Host:** same infrastructure as other dashboards (served via `/dashboards` location in nginx → port 8031 or new dedicated service).
- **Source of truth:** WhaleTrack service running on port 8600 (paper or live mode).

## 3. Architecture Overview

```
Bridge (KR/EX) → WhaleTrack API (8600) → Activity Endpoints → Dashboards/WhaleTrack (8031 route)
```

- Frontend dashboard fetches `/api/activity/trades`, `/api/activity/status`, `/api/activity/snapshot`.
- Dashboard is rendered via the dashboards stack (likely React/Flask served from `DASHBOARDS/master` or new FastAPI/Next service).

## 4. UI Requirements

Same as Sprint 1 spec but ensure:
- It lives at `/dashboards/whaletrack`.
- Uses existing dashboard shell (navigation, login if required).
- Links back to `/services/whaletrack` for marketing view.

## 5. Next Steps

1. Implement backend endpoints (`whaletrack-magnetic-trader` Sprint 1).
2. Build frontend page inside dashboards repo (`DASHBOARDS/master/templates/whaletrack.html` or new dashboard service).
3. Update nginx to route `/dashboards/whaletrack` → new page.
4. Deploy and verify.

