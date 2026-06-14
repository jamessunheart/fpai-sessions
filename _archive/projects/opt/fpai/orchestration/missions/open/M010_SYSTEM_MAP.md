# MISSION M010 — Deploy Live System Map

**Title:** Deploy Live System Map  
**Priority:** P2 (Visibility)  
**Owner:** Haythem / AI Builder  
**Status:** OPEN

---

## 🎯 Objective
1. Create endpoint `/registry/map` (Droplet #1) that returns the full graph of connected droplets.  
2. Build `frontend/app/map/page.tsx` using `react-flow-renderer` or D3.js to render the mesh.  
3. Visualize Registry (center) connected to Orchestrator, Magnet, and Storefront nodes.  
4. Show health via link colors — green for active connections, red for error states.

---

## ✅ Definition of Done
- Registry endpoint deployed and returning graph JSON with live status metadata.  
- Dashboard `map` page auto-polls registry and renders graph with color-coded edges.  
- Mesh view displayed on dashboard with Registry anchored at center and required nodes visible.  
- Errors logged to dashboard console and surfaced visually (red lines) within 5s of detection.  
- Documentation added to dashboard README describing usage and polling interval.

---

## 🚨 Risks & Mitigations
- **Registry data drift:** add heartbeat timestamp to `/registry/map` payload to detect stale data.  
- **Rendering performance:** limit nodes to active droplets + key systems and cap poll frequency to 5s.  
- **Library mismatch:** evaluate `react-flow-renderer` first; fall back to D3 only if layout control needed.

---

## 🧪 Testing Strategy
- Unit tests for registry endpoint ensuring graph schema validity.  
- Frontend component tests verifying color logic for active/error edges.  
- Manual QA checklist validating that disconnecting a droplet flips edge to red within SLA.  
- Snapshot tests on layout to catch regression in node labels/positions.

---

_Last updated: 2025-11-23 (session-1763923279)_

