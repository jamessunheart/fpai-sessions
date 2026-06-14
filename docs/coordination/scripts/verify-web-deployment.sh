#!/bin/bash
# verify-web-deployment.sh
# Automated verification for web/frontend deployments
# Usage: ./verify-web-deployment.sh <domain> [additional-pages...]

set -e

if [ -z "$1" ]; then
  echo "Usage: $0 <domain> [additional-pages...]"
  echo "Example: $0 fullpotential.ai /research/ /lp1"
  exit 1
fi

DOMAIN=$1
shift
ADDITIONAL_PAGES="$@"
FAILED=0

echo "🔍 Verifying web deployment: $DOMAIN"
echo ""

# 1. Test main page
echo "✓ Testing main page..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://$DOMAIN/" 2>/dev/null || echo "000")
if [[ "$HTTP_CODE" =~ ^2 ]]; then
  echo "  ✅ Main page: $HTTP_CODE OK"
else
  echo "  ❌ Main page: $HTTP_CODE FAILED"
  FAILED=1
fi

# 2. Test additional pages if provided
if [ -n "$ADDITIONAL_PAGES" ]; then
  echo "✓ Testing specified pages..."
  for page in $ADDITIONAL_PAGES; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://$DOMAIN$page" 2>/dev/null || echo "000")
    if [[ "$HTTP_CODE" =~ ^2 ]]; then
      echo "  ✅ $page: $HTTP_CODE OK"
    else
      echo "  ❌ $page: $HTTP_CODE FAILED"
      FAILED=1
    fi
  done
fi

# 3. Extract and test all internal links from main page
echo "✓ Testing internal links from main page..."
TEMP_FILE=$(mktemp)
curl -s "https://$DOMAIN/" > "$TEMP_FILE" 2>/dev/null || true

# Extract href links (both absolute /path and relative path)
LINKS=$(grep -o 'href="[^"]*"' "$TEMP_FILE" | cut -d'"' -f2 | grep -E '^/' | sort -u || true)

if [ -z "$LINKS" ]; then
  echo "  ⚠️  No internal links found (or static page)"
else
  for link in $LINKS; do
    # Skip anchors and external links
    if [[ "$link" =~ ^# ]] || [[ "$link" =~ ^http ]]; then
      continue
    fi
    
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://$DOMAIN$link" 2>/dev/null || echo "000")
    if [[ "$HTTP_CODE" =~ ^2 ]]; then
      echo "  ✅ $link: $HTTP_CODE"
    else
      echo "  ❌ $link: $HTTP_CODE - BROKEN"
      FAILED=1
    fi
  done
fi

rm -f "$TEMP_FILE"

# 4. Test common API endpoints (if they exist)
echo "✓ Testing API endpoints (if applicable)..."
for endpoint in "/api/data.json" "/docs/status/missions.json"; do
  if curl -sf "https://$DOMAIN$endpoint" > /dev/null 2>&1; then
    # Verify it's valid JSON
    if curl -s "https://$DOMAIN$endpoint" | jq . > /dev/null 2>&1; then
      echo "  ✅ $endpoint - Valid JSON"
    else
      echo "  ⚠️  $endpoint - Not valid JSON (may be expected)"
    fi
  fi
done

# 5. Test HTTP → HTTPS redirect
echo "✓ Testing HTTP → HTTPS redirect..."
if curl -I "http://$DOMAIN/" 2>&1 | grep -q "301\|302"; then
  echo "  ✅ HTTP redirects to HTTPS"
else
  echo "  ⚠️  HTTP redirect not detected (may be handled at CDN level)"
fi

# 6. Final verdict
echo ""
if [ $FAILED -eq 0 ]; then
  echo "✅ VERIFICATION PASSED - Deployment is valid"
  echo ""
  echo "Safe to declare deployment complete."
  exit 0
else
  echo "❌ VERIFICATION FAILED - Fix issues before declaring success"
  echo ""
  echo "Do NOT declare deployment complete until all checks pass."
  exit 1
fi

