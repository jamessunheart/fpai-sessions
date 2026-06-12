# Receipts Admin — `accounting.zenvillagecr.com`

Password-protected web view of every receipt the Telegram bot has captured via the `/acct` lane. Lets Sunheart/Halley verify what's been ingested without SSH or `/acct_last` paging.

## What it shows

- All entries from `/opt/zen-village/accounting-intake/<YYYY-MM>/intake.jsonl`
- Photos rendered inline (click → fullscreen), docs/PDFs in iframe
- Per-currency totals (USD / CRC) split by inflow/outflow when detectable
- Filters: month, who, free-text, has-photo, has-amount
- CSV export of any filtered view

## Architecture

```
browser
  │  basic-auth (htpasswd)
  ▼
nginx (accounting.zenvillagecr.com)
  │  injects X-Admin-Token: <ZV_AFFILIATES_ADMIN_TOKEN>
  ▼
zen-village FastAPI (127.0.0.1:8770)
  │  require_admin() validates token
  ▼
/opt/zen-village/accounting-intake/  (root-only, on Secondary)
```

Two layers of auth: nginx basic-auth (browser-cached single password) AND backend token check. If either layer is misconfigured the API stays gated.

## One-time setup on Secondary (162.0.208.88)

### 1. DNS

Add an `A` record for `accounting.zenvillagecr.com` → `162.0.208.88` (Namecheap → zenvillagecr.com → Advanced DNS).

### 2. Basic-auth password

```bash
ssh root@162.0.208.88
apt-get install -y apache2-utils
htpasswd -B -c /etc/nginx/.htpasswd-accounting admin
# enter password — share via Signal with Halley + Sunheart
chown root:www-data /etc/nginx/.htpasswd-accounting
chmod 640 /etc/nginx/.htpasswd-accounting
```

### 3. Admin token snippet for nginx

The nginx config references `$zv_admin_token`. Define it once:

```bash
TOKEN=$(grep ^ZV_AFFILIATES_ADMIN_TOKEN /etc/zen-village/zen-village.env | cut -d= -f2-)
cat >/etc/nginx/conf.d/zv-admin-token.conf <<EOF
# Admin token for accounting subdomain → zen-village API.
# Read from /etc/zen-village/zen-village.env at provisioning time.
map \$host \$zv_admin_token {
    default "$TOKEN";
}
EOF
chmod 640 /etc/nginx/conf.d/zv-admin-token.conf
```

(Using `map` keeps the variable scoped to nginx's http context so it's available in any `server {}` block. If you'd rather put the literal `set $zv_admin_token` inside the server block, that works too — adjust `accounting.zenvillagecr.com.conf` accordingly.)

### 4. Drop in the nginx site config

```bash
scp SERVICES/zen-village/nginx/accounting.zenvillagecr.com.conf \
    root@162.0.208.88:/etc/nginx/sites-available/

ssh root@162.0.208.88 "ln -sf /etc/nginx/sites-available/accounting.zenvillagecr.com.conf \
                              /etc/nginx/sites-enabled/ && \
                       nginx -t"
```

### 5. SSL via certbot

```bash
ssh root@162.0.208.88 "certbot --nginx -d accounting.zenvillagecr.com \
                                --non-interactive --agree-tos -m sunheart@fullpotential.ai"
```

Certbot will edit `accounting.zenvillagecr.com.conf` in place to add `ssl_certificate` directives. That's expected; commit the post-certbot version back to the repo if you want it tracked, OR keep the source-controlled version pristine and treat the deployed copy as machine-managed (preferred).

### 6. Deploy the code

The new code is in:
- `SERVICES/zen-village/app/receipts_admin.py` — router
- `SERVICES/zen-village/main_lite.py` — wires the router + `/admin/receipts` HTML route
- `SERVICES/zen-village/frontend/public/receipts-admin.html` — UI

Deploy via the standard pipeline (do not SSH directly — see `.cursor/rules/deploy.mdc`):

```bash
./infra/scripts/safe-deploy.sh zen-village "rsync -av SERVICES/zen-village/ root@162.0.208.88:/opt/fpai/apps/zen-village/ && systemctl restart zen-village"
```

### 7. Reload nginx

```bash
ssh root@162.0.208.88 "nginx -t && systemctl reload nginx"
```

## Verification (smoke test from your laptop)

```bash
# 1. DNS resolves to Secondary
dig +short accounting.zenvillagecr.com   # should print 162.0.208.88

# 2. Without auth → 401
curl -sI https://accounting.zenvillagecr.com/ | head -1
# HTTP/2 401

# 3. With basic-auth, root → HTML
curl -s -u admin:<password> https://accounting.zenvillagecr.com/ | head -5
# <!DOCTYPE html> ... <title>Accounting · Receipts · Zen Village</title>

# 4. With basic-auth, API → JSON
curl -s -u admin:<password> https://accounting.zenvillagecr.com/api/admin/receipts/_meta
# {"ok":true,"accounting_root":"/opt/zen-village/accounting-intake","available_months":[...]}

# 5. Healthz (no auth required, monitoring path)
curl -s https://accounting.zenvillagecr.com/healthz
# {"status":"healthy",...}
```

If step 4 returns `{"detail":"Admin token not configured"}` (503), the `$zv_admin_token` map isn't loaded — re-check step 3.

If step 4 returns `{"detail":"Invalid admin token"}` (401), the token in `/etc/nginx/conf.d/zv-admin-token.conf` doesn't match `ZV_AFFILIATES_ADMIN_TOKEN` in `/etc/zen-village/zen-village.env`. Re-run step 3.

## Day-to-day use

- Open `https://accounting.zenvillagecr.com` in any browser
- Browser prompts for the basic-auth password once, then caches it
- Filter by month or by user (`halley`), browse, click photos to enlarge
- Export CSV when you want to reconcile against a bank statement

## Adding more users to basic-auth

```bash
ssh root@162.0.208.88 "htpasswd -B /etc/nginx/.htpasswd-accounting <username>"
# (no -c flag — appends, doesn't overwrite)
```

## Removing receipts (if needed)

This admin page is **read-only by design**. To delete a receipt entry:

```bash
ssh root@162.0.208.88
cd /opt/zen-village/accounting-intake/<YYYY-MM>/
# Edit intake.jsonl manually or grep -v <id> > intake.jsonl.new && mv -f intake.jsonl.new intake.jsonl
rm -f <photo_or_doc_filename>
```

Document why in `MIGRATION_LOG.md` or the deploy log.

## Security boundary preserved

- Raw receipts stay in `/opt/zen-village/accounting-intake` (root-only `chmod 700`)
- Photos are streamed through the API with token check; never copied to AppFlowy/NocoDB
- Nginx access log shows every view (`/var/log/nginx/accounting.access.log`)
- This subdomain is **independent** of `zenvillagecr.com` / `zenvillage.live` — guests never touch it

## Rollback

If anything misbehaves:

```bash
ssh root@162.0.208.88 "rm /etc/nginx/sites-enabled/accounting.zenvillagecr.com.conf && \
                       nginx -t && systemctl reload nginx"
```

The Telegram `/receipts` and `/acct_last` lookups stay working — this admin page is purely additive.
