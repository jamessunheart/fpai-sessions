# Mission: Deploy FullPotential.com Storefront (M005)

- **Priority:** P2 (Revenue Generation)
- **Status:** OPEN
- **Owner:** Elif / Apprentice
- **Objective:**
  1. Locate or initialize Droplet #15 (Website) frontend stack.
  2. Ship a Product Page for the *Developer Acceleration Kit* (pricing tier $97–$497 with Tier comparison + CTA).
  3. Add an Intake Form for the *Matching Service* so prospects can submit intent + budget.
  4. Integrate Stripe Checkout (test mode) to collect orders securely.
  5. Serve the storefront via Nginx at `http://198.54.123.234/` (SSL upgrade deferred).

## Deliverables
- Droplet #15 repo synced into `/opt/fpai/droplets/hteam/droplet-15` (or new path) with build instructions.
- Static/Product page deployed and reachable through Nginx `/`.
- Stripe test checkout documented, with secrets stored via vault workflows.
- Intake form submissions routed to orchestrator inbox or email alias.

## Notes
- Coordinate with Town Crier for launch alerts.
- Reuse dashboard design tokens where possible for brand consistency.
