# zenvillage.live/peace

Static landing page for **World Peace Weekend · May 2–3** at Zen Village.

- **Source of truth:** `peace/index.html` (single self-contained file)
- **Target URL:** https://zenvillage.live/peace
- **Hosting:** Primary FPAI server `198.54.123.234`, served by nginx from `/var/www/zenvillage-live/peace/`
- **nginx vhost:** `/etc/nginx/sites-available/zenvillage.live.conf` (mirror in `nginx/zenvillage.live.conf`)

## Status

| Step | Status |
|---|---|
| Page authored | ✅ Done |
| Deployed to primary server | ✅ Done |
| nginx vhost live & reloaded | ✅ Done |
| Serves on `198.54.123.234` (Host: `zenvillage.live`) | ✅ HTTP 200 |
| DNS at Namecheap pointing to server | ⏳ **Manual step — see below** |
| Let's Encrypt cert (HTTPS) | ⏳ Auto after DNS lands |

## Re-deploy after editing the page

```bash
./sites/zenvillage-peace/deploy.sh
```

This rsyncs `peace/`, syncs `nginx/zenvillage.live.conf`, runs `nginx -t`, reloads nginx, and smoke-tests. Idempotent.

## Preview locally

```bash
cd sites/zenvillage-peace
python3 -m http.server 8088
# open http://localhost:8088/peace/
```

## Final step — DNS swap at Namecheap (you, ~2 min)

The domain currently shows the Namecheap parking page. Swap two records and you're live.

1. Go to: https://ap.www.namecheap.com/domains/list/ → **zenvillage.live** → **Manage** → **Advanced DNS**.
2. **Delete** these two existing rows:
   - `CNAME` `www` → `parkingpage.namecheap.com.`
   - `URL Redirect` `@` → `http://www.zenvillage.live/`
3. **Add** these two rows:

   | Type | Host | Value | TTL |
   |---|---|---|---|
   | `A Record` | `@` | `198.54.123.234` | 5 min (Automatic) |
   | `A Record` | `www` | `198.54.123.234` | 5 min |

4. Save (green checkmark on each row, then "Save All Changes").
5. Propagation usually 5–30 min on Namecheap. Verify with:

   ```bash
   dig +short zenvillage.live          # should return 198.54.123.234
   curl -sI http://zenvillage.live/peace/   # should return HTTP/1.1 200
   ```

6. Once DNS is propagated, ping me (or run on the server):

   ```bash
   ssh root@198.54.123.234 \
     'certbot --nginx -d zenvillage.live -d www.zenvillage.live --redirect --agree-tos -m hello@zenvillagecr.com -n'
   ```

   This issues a free Let's Encrypt cert and modifies the nginx vhost to add the 443 server block + 80→443 redirect. Auto-renews via the existing certbot.timer.

## What the page contains

- Hero with peace symbol, "World Peace Weekend", **May 2–3**, "by invitation & intention"
- Saturday May 2 flow (10 stops) + Sunday May 3 flow (6 stops) side-by-side
- The Magic Layer all-night strip (Projection Mapping · World Peace Room · World Council · World Token · Dance Transmission)
- Signature card: "one peaceful action carried into the world"
- 5 field principles ("Peace begins in the field between us")
- Food / Zen Village / Practical cards
- Reign Dance Movement collab → links to `instagram.com/reigndancemovement`
- **The Manifesto** (added 2026-05-07) — Coherent Champions of CHRIST acronym, seven-clause World Peace Agreement, "Sign by email" CTA pointing to `hello@zenvillagecr.com`, current registry state showing the founding Agreement
- Closing invitation in your voice + RSVP CTAs (WhatsApp + email)

## Things to set before the page goes "fully live"

| What | Where |
|---|---|
| **WhatsApp number** | search `wa.me/?text=` in `peace/index.html` and add the number after `wa.me/` |
| **Contact email** | currently `hello@zenvillagecr.com` — change if needed |
| **Manifesto signing email** | currently `hello@zenvillagecr.com` (same as RSVP); change if you want a dedicated signing inbox |
| **OG image** for social previews | drop a `og.png` (1200×630) into `peace/` and uncomment the `og:image` tag (already references `https://zenvillage.live/peace/og.png`) |
| **Real RSVP form** | swap the two CTAs in `#rsvp` for a Tally / Typeform / Mailchimp embed |
| **Page metadata** | `<title>` and `og:` tags still describe the May 2–3 weekend only. Update when you want the page's primary identity to be "WPO Manifesto + past weekend retrospective" |
| **Public roll** | the manifesto section says "public roll coming" — wire this to render `core/INTENT/AGREEMENTS/registry.json` (filtered to `public: true`) when ready |
