# fullpotential.com – Storefront

This directory will evolve into Droplet #15: the **Full Potential Storefront** for the Developer Acceleration Kit and Matching Services intake.

## Assets

- `frontend/index.html` — live placeholder synced from `/opt/fpai/core/applications/website-com/frontend/index.html`.
- `legacy/products.html` — existing “Full Potential AI Empire” sales page from `/var/www/html/products.html`.
- `legacy/get-matched.html` — AI-powered intake form previously served at `/get-matched`.

## Implementation Plan

1. **Componentize the legacy assets**  
   - Extract sections (Hero, Bundle grid, Testimonials, Pricing table, Intake form) into reusable partials.  
   - Port typography/colors into a shared token file so `.ai` and `.com` stay visually aligned.

2. **Stripe + Vault integration**  
   - Use the mission requirements from `M005_ACTIVATE_STOREFRONT.md` to wire Stripe (test mode) and store API keys via the vault workflow.  
   - Mirror the process for the upcoming Cora Token utility rail.

3. **Matching Service intake**  
   - Keep `get-matched.html` as the canonical spec until the new form is built.  
   - When the new React/Vue form is ready, submit payloads to the Orchestrator inbox (`/registry/submit-intent`) so M006 can critique them against the Constitution.

4. **Publishing pipeline**  
   - Build a simple `npm run build && rsync` pipeline so Droplet #15 can be deployed alongside the other services in `/opt/fpai`.  
   - Document updates in `infra/deployment_steps.md` once the storefront ships.

