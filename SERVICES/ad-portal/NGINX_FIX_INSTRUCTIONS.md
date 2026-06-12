# Nginx Fix Instructions - Ad Portal Frontend

## Problem
The `/ads/` location blocks are nested inside the `/dashboards/whaletrack/api/` location block, causing nginx to not match them correctly.

## Quick Fix

SSH to the server and run:

```bash
# Find the line numbers
WHALETRACK=$(grep -n "location ^~ /dashboards/whaletrack/api/" /etc/nginx/sites-available/fullpotential.ai | head -1 | cut -d: -f1)
ADS=$(grep -n "# Ad Portal" /etc/nginx/sites-available/fullpotential.ai | head -1 | cut -d: -f1)

echo "Whaletrack block: line $WHALETRACK"
echo "Ads section: line $ADS"

# Close the whaletrack block before ads section
sed -i "${ADS}i\\
    }\\
\\
" /etc/nginx/sites-available/fullpotential.ai

# Test and reload
nginx -t && systemctl reload nginx
```

## Manual Fix

1. SSH to server: `ssh fpai` (or `ssh root@198.54.123.234`)

2. Edit config: `nano /etc/nginx/sites-available/fullpotential.ai`

3. Find the line that says `# Ad Portal Frontend Dashboard`

4. **BEFORE that line**, add:
   ```
   }
   
   ```

5. This closes the `/dashboards/whaletrack/api/` block that was left open

6. Test: `nginx -t`

7. Reload: `systemctl reload nginx`

## Verify Fix

After fixing, test:
```bash
curl -s https://fullpotential.ai/ads/ | grep -i "Ad Portal"
```

Should show: `<title>Ad Portal - Full Potential AI</title>`

## Current Status

- ✅ Backend API: Working (when config is correct)
- ✅ Frontend files: Deployed
- ⚠️ Nginx config: Needs whaletrack block closed

