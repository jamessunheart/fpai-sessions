#!/bin/bash
# Global AI Capability Database — Map of everything available
# Usage:
#   aidb.sh list [category]    — Browse all capabilities or by category
#   aidb.sh gaps               — Gap analysis: what we're missing
#   aidb.sh search <query>     — Search capabilities
#   aidb.sh stats              — Database overview
#   aidb.sh scan               — Run intelligence scanner now
#   aidb.sh export             — Export as JSON

case "${1:-help}" in
    list)   python3 /opt/fpai/memory-bus/ai-capabilities-db.py list "$2" ;;
    gaps)   python3 /opt/fpai/memory-bus/ai-capabilities-db.py gaps ;;
    search) shift; python3 /opt/fpai/memory-bus/ai-capabilities-db.py search "$*" ;;
    stats)  python3 /opt/fpai/memory-bus/ai-capabilities-db.py stats ;;
    scan)   python3 /opt/fpai/memory-bus/intel-scanner.py scan ;;
    export) python3 /opt/fpai/memory-bus/ai-capabilities-db.py export ;;
    *)
        echo "Global AI Capability Database"
        echo "  list [category]    — Browse capabilities (categories: language_models, voice_audio, agent_frameworks, ...)"
        echo "  gaps               — Gap analysis vs our stack"
        echo "  search <query>     — Search by name/description"
        echo "  stats              — Overview"
        echo "  scan               — Run AI intelligence scan"
        echo "  export             — Export as JSON"
        ;;
esac
