# Web Deployment Verification Protocol

**Mandatory quality gates for all website/frontend deployments**

---

## Core Principle

**NEVER declare a deployment "complete" without verification.**

Every web deployment must pass automated verification before being presented as working. This prevents:
- Broken links shipped to production
- Untested pages going live
- "Trust me, it works" deployments
- Wasted human time debugging avoidable issues

---

## Mandatory Verification Steps

### 1. HTTP Status Checks (BLOCKING)
**All URLs must return 2xx status codes**

```bash
# Test all primary URLs
curl -I https://domain.com/ 2>&1 | grep "HTTP.*200"
curl -I https://domain.com/page1 2>&1 | grep "HTTP.*200"
curl -I https://domain.com/page2 2>&1 | grep "HTTP.*200"
```

**Failure:** Any 4xx or 5xx response is a BLOCKING failure.

---

### 2. Link Verification (BLOCKING)
**All internal links must resolve**

```bash
# Extract all links from a page
curl -s https://domain.com/ | grep -o 'href="[^"]*"'

# Test each internal link
for link in $(curl -s https://domain.com/ | grep -o 'href="/[^"]*"' | cut -d'"' -f2); do
  curl -I "https://domain.com$link" 2>&1 | grep -q "HTTP.*[23]" || echo "BROKEN: $link"
done
```

**Failure:** Any broken internal link is BLOCKING.

---

### 3. Asset Verification (BLOCKING)
**CSS, JS, images must load**

```bash
# Check for 404s in browser console
# Or verify asset paths exist on server
curl -I https://domain.com/static/css/style.css 2>&1 | grep "HTTP.*200"
curl -I https://domain.com/static/js/main.js 2>&1 | grep "HTTP.*200"
```

**Failure:** Missing assets are BLOCKING.

---

### 4. API Endpoint Tests (BLOCKING for dynamic sites)
**Backend APIs must respond correctly**

```bash
# Test JSON endpoints
curl -s https://domain.com/api/data.json | jq . > /dev/null || echo "Invalid JSON"

# Test expected response structure
curl -s https://domain.com/api/data.json | jq '.missions' > /dev/null || echo "Missing expected field"
```

**Failure:** Broken API endpoints are BLOCKING.

---

### 5. Cross-Domain Tests (if applicable)
**Subdomains and redirects must work**

```bash
# Test redirects
curl -I http://domain.com 2>&1 | grep -q "301.*https" || echo "HTTP→HTTPS redirect missing"

# Test CORS if needed
curl -I https://api.domain.com -H "Origin: https://frontend.domain.com" 2>&1 | grep "Access-Control"
```

---

## Automated Verification Script

**Create this script for every web deployment:**

```bash
#!/bin/bash
# verify-web-deployment.sh
# Usage: ./verify-web-deployment.sh <domain>

set -e

DOMAIN=$1
FAILED=0

echo "🔍 Verifying web deployment: $DOMAIN"
echo ""

# 1. Test main page
echo "✓ Testing main page..."
if curl -sf "https://$DOMAIN/" > /dev/null; then
  echo "  ✅ Main page: 200 OK"
else
  echo "  ❌ Main page: FAILED"
  FAILED=1
fi

# 2. Extract and test all links
echo "✓ Testing internal links..."
LINKS=$(curl -s "https://$DOMAIN/" | grep -o 'href="/[^"]*"' | cut -d'"' -f2 | sort -u)
for link in $LINKS; do
  if curl -sf "https://$DOMAIN$link" > /dev/null; then
    echo "  ✅ $link"
  else
    echo "  ❌ $link - BROKEN"
    FAILED=1
  fi
done

# 3. Test API endpoints (if applicable)
if curl -sf "https://$DOMAIN/api/data.json" > /dev/null 2>&1; then
  echo "✓ Testing API endpoints..."
  if curl -s "https://$DOMAIN/api/data.json" | jq . > /dev/null 2>&1; then
    echo "  ✅ API returns valid JSON"
  else
    echo "  ❌ API returns invalid JSON"
    FAILED=1
  fi
fi

# 4. Final verdict
echo ""
if [ $FAILED -eq 0 ]; then
  echo "✅ VERIFICATION PASSED - Deployment is valid"
  exit 0
else
  echo "❌ VERIFICATION FAILED - Fix issues before declaring success"
  exit 1
fi
```

---

## Integration with Cursor AI Rules

**Add to `.cursorrules`:**

```markdown
## Web Deployment Verification (MANDATORY)

Before declaring any web deployment "complete":

1. **Run verification script:**
   ```bash
   ./docs/coordination/scripts/verify-web-deployment.sh <domain>
   ```

2. **Test all links manually** if script not available:
   - Extract all `href` attributes from deployed page
   - Test each link with `curl -I`
   - Verify 200 OK response for each

3. **Only declare success after:**
   - All HTTP checks pass (200 OK)
   - All internal links resolve
   - All assets load
   - All API endpoints respond correctly

4. **Present results:**
   ```
   ✅ Verified Working:
   - https://domain.com/ → 200 OK
   - https://domain.com/page1 → 200 OK
   - https://domain.com/page2 → 200 OK
   - All 5 internal links tested and working
   ```

**NEVER say "deployment complete" without showing verification results.**
```

---

## Example Verification Output

**Good:**
```
🔍 Verifying web deployment: fullpotential.ai

✓ Testing main page...
  ✅ Main page: 200 OK

✓ Testing internal links...
  ✅ /research/
  ✅ /lp1
  ✅ /docs/status/missions.json

✓ Testing API endpoints...
  ✅ API returns valid JSON

✅ VERIFICATION PASSED - Deployment is valid
```

**Bad (what to avoid):**
```
I've deployed the website. It should work now.
```

---

## Quality Gates

| Check | Required | Blocking |
|-------|----------|----------|
| Main page 200 OK | YES | YES |
| All internal links resolve | YES | YES |
| All assets load | YES | YES |
| API endpoints respond | YES (if applicable) | YES |
| Manual spot check | Recommended | NO |

---

## Enforcement

**This protocol is:**
- ✅ Mandatory for all web/frontend deployments
- ✅ Part of the CONSTITUTION's "Verify before Trust" principle
- ✅ Enforced by Gatekeeper (when automated)
- ✅ Checked by session coordinators

**Violations:**
- Declaring "done" without verification = Process failure
- Shipping broken links = Quality failure
- "Trust me, it works" = Protocol violation

---

**Updated:** 2025-11-24  
**Integrated with:** VERIFICATION_PROTOCOL.md, CONSTITUTION.md, Gatekeeper






