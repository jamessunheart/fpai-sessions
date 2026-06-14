#!/bin/bash

# Automated DNS Monitoring & SSL Setup
# Checks DNS every 5 minutes, auto-configures SSL when ready

set -e

DOMAIN="fullpotential.com"
SERVER_IP="198.54.123.234"
CHECK_INTERVAL=300  # 5 minutes
MAX_CHECKS=288      # 24 hours (288 * 5 min)

LOG_FILE="/var/log/fpai-dns-monitor.log"
STATUS_FILE="/tmp/fpai-dns-status.txt"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

check_subdomain() {
    local subdomain=$1
    local ip=$(dig +short ${subdomain}.${DOMAIN} @8.8.8.8 | tail -1)

    if [ "$ip" == "$SERVER_IP" ]; then
        return 0  # Success
    else
        return 1  # Not ready
    fi
}

test_wildcard() {
    # Test with random subdomain
    local random="test$(date +%s)"
    check_subdomain "$random"
}

get_ssl_certificates() {
    log "🔒 DNS propagated! Getting SSL certificates..."

    # Get SSL certs for all subdomains
    SUBDOMAINS=("api" "match" "membership" "jobs" "registry")

    for subdomain in "${SUBDOMAINS[@]}"; do
        log "📜 Getting certificate for ${subdomain}.${DOMAIN}..."

        certbot --nginx \
            -d "${subdomain}.${DOMAIN}" \
            --non-interactive \
            --agree-tos \
            --email admin@fullpotential.com \
            --redirect || log "⚠️  Failed: ${subdomain}.${DOMAIN}"
    done

    # Reload nginx
    nginx -t && systemctl reload nginx

    log "✅ SSL setup complete!"
}

verify_all_working() {
    log "🧪 Verifying all domains..."

    local all_good=true
    SUBDOMAINS=("api" "match" "membership" "jobs" "registry")

    for subdomain in "${SUBDOMAINS[@]}"; do
        local url="https://${subdomain}.${DOMAIN}/health"
        local status=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")

        if [[ "$status" == "200" || "$status" == "404" ]]; then
            log "   ✅ ${subdomain}.${DOMAIN} - HTTPS working"
        else
            log "   ❌ ${subdomain}.${DOMAIN} - Failed (HTTP $status)"
            all_good=false
        fi
    done

    if [ "$all_good" = true ]; then
        log "🎉 ALL DOMAINS LIVE WITH HTTPS!"
        return 0
    else
        return 1
    fi
}

main() {
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log "🔍 Starting DNS monitoring for ${DOMAIN}"
    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log "Checking every $CHECK_INTERVAL seconds"
    log "Will check for up to 24 hours"
    log ""

    for i in $(seq 1 $MAX_CHECKS); do
        log "Check $i/$MAX_CHECKS: Testing DNS propagation..."

        if test_wildcard; then
            log "✅ Wildcard DNS is working!"

            # Verify all required subdomains
            all_ready=true
            for sub in api match membership jobs registry; do
                if check_subdomain "$sub"; then
                    log "   ✅ ${sub}.${DOMAIN} resolves"
                else
                    log "   ⏳ ${sub}.${DOMAIN} not ready yet"
                    all_ready=false
                fi
            done

            if [ "$all_ready" = true ]; then
                log "🎯 All subdomains ready! Proceeding with SSL setup..."

                # Get SSL certificates
                get_ssl_certificates

                # Verify everything works
                sleep 10  # Give nginx a moment

                if verify_all_working; then
                    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                    log "✅ COMPLETE! All domains are live with HTTPS!"
                    log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                    echo "complete" > "$STATUS_FILE"
                    exit 0
                else
                    log "⚠️  Some domains not working yet, will retry..."
                fi
            fi
        else
            log "⏳ DNS not propagated yet. Waiting ${CHECK_INTERVAL}s..."
        fi

        # Save status
        echo "checking:$i/$MAX_CHECKS" > "$STATUS_FILE"

        # Wait before next check (unless this is the last check)
        if [ $i -lt $MAX_CHECKS ]; then
            sleep $CHECK_INTERVAL
        fi
    done

    log "❌ DNS did not propagate within 24 hours"
    log "Please check Namecheap DNS configuration"
    echo "timeout" > "$STATUS_FILE"
    exit 1
}

# Run main function
main
