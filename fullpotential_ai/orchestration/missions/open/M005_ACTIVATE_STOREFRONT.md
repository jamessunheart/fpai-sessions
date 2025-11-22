# Mission: Deploy FullPotential.com Storefront (M005)

- **Priority:** P2 (Revenue Generation)
- **Status:** OPEN
- **Owner:** Elif / Apprentice
- **Objective:**
  1. Locate or initialize Droplet #15 (Website) frontend stack.
  2. Ship a Product Page for the *Developer Acceleration Kit* with pricing + CTA.
  3. Integrate Stripe Checkout (test mode) to collect orders.
  4. Front the site via Nginx at `http://198.54.123.234/` (reverse proxy, SSL TBD).

## Deliverables
- Droplet #15 repo synced into `/opt/fpai/droplets/hteam/droplet-15` (or new path) with build instructions.
- Static/Product page deployed and reachable through Nginx `/`.
- Stripe test checkout documented, with secrets stored via vault workflows.

## Notes
- Coordinate with Town Crier for launch alerts.
- Reuse existing design tokens from Dashboard if possible to keep brand consistent.
