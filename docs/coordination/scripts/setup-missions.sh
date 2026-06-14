#!/bin/bash
# Setup Current High-Priority Missions

MISSION_CONTROL="/Users/jamessunheart/Development/docs/coordination/scripts/mission-control.py"

echo "🎯 Setting up Mission Priorities..."
echo ""

# Mission format: name urgency impact feasibility "description"

# HIGHEST PRIORITY: Revenue generation
python3 "$MISSION_CONTROL" mission revenue_generation 10 10 9 \
    "Get first VA hired and generating revenue - enables all future development"

# HIGH: DNS Automation
python3 "$MISSION_CONTROL" mission dns_automation 8 7 8 \
    "Automate all DNS/SSL management for instant subdomain deployment"

# HIGH: Treasury Optimization
python3 "$MISSION_CONTROL" mission treasury_optimization 7 9 6 \
    "Deploy automated yield farming and treasury management system"

# MEDIUM-HIGH: The Brain Phase 2
python3 "$MISSION_CONTROL" mission brain_phase2 6 10 5 \
    "Implement vector database and semantic search for enhanced consciousness"

# MEDIUM: Multi-Agent Coordination
python3 "$MISSION_CONTROL" mission multi_agent 5 8 7 \
    "Enable multiple Claude sessions to coordinate on complex tasks"

# MEDIUM: Knowledge Graph Enhancement
python3 "$MISSION_CONTROL" mission knowledge_graph 5 7 8 \
    "Build comprehensive knowledge graph of all FPAI systems and learnings"

# ONGOING: Documentation
python3 "$MISSION_CONTROL" mission documentation 4 6 9 \
    "Maintain comprehensive docs for all systems and processes"

# ONGOING: System Monitoring
python3 "$MISSION_CONTROL" mission monitoring 6 6 8 \
    "Ensure all services running smoothly with proactive monitoring"

echo ""
echo "✅ Mission priorities configured!"
echo ""
echo "To view current priorities:"
echo "  python3 $MISSION_CONTROL status | jq '.active_missions'"
echo ""
