#!/bin/bash
# Lead Generation Tool — Find, enrich, and manage prospects
# Usage:
#   leads.sh search <query>              — find leads (Apollo + web)
#   leads.sh find-email <name> <company> — find someone's email
#   leads.sh domain <domain.com>         — find emails at a domain
#   leads.sh enrich <email>              — enrich contact data
#   leads.sh list                        — show all leads
#   leads.sh export                      — export as CSV
#   leads.sh stats                       — pipeline stats
#   leads.sh prospect <vertical>         — auto-prospect a vertical

case "${1:-help}" in
    search|find-email|domain|enrich|list|export|stats)
        python3 /opt/fpai/leads/leads.py "$@"
        ;;
    prospect)
        VERTICAL="${2:-wellness retreat}"
        echo "Auto-prospecting: $VERTICAL"
        echo ""
        python3 /opt/fpai/leads/leads.py search "$VERTICAL CEO founder"
        echo ""
        python3 /opt/fpai/leads/leads.py search "$VERTICAL coaching consultant"
        echo ""
        echo "=== Pipeline After Prospecting ==="
        python3 /opt/fpai/leads/leads.py stats
        ;;
    *)
        echo "Lead Generation Tool"
        echo "  search <query>              — find leads (Apollo + LinkedIn + web)"
        echo "  find-email <name> <company> — find someone's email"
        echo "  domain <domain.com>         — find emails at a domain"
        echo "  enrich <email>              — enrich contact data"
        echo "  list                        — show all leads (top 50)"
        echo "  export                      — export as CSV"
        echo "  stats                       — pipeline stats"
        echo "  prospect <vertical>         — auto-prospect a vertical"
        ;;
esac
