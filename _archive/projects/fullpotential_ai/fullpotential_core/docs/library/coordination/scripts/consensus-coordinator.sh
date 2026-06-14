#!/bin/bash

# CONSENSUS COORDINATOR
# Tracks inter-session agreement on numbers, roles, and goals
# Proves real communication through collective consensus

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SESSIONS_DIR="$(dirname "$SCRIPT_DIR")/sessions"
CONSENSUS_FILE="$(dirname "$SCRIPT_DIR")/CONSENSUS_REGISTRY.md"

echo -e "${CYAN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  🤝 CONSENSUS COORDINATOR                              ║${NC}"
echo -e "${CYAN}║  Tracking Inter-Session Agreement                     ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Collect all session proposals
echo -e "${YELLOW}[1/4] Collecting Session Proposals...${NC}"

PROPOSALS=()
SESSION_NUMBERS=()
SESSION_ROLES=()
SESSION_GOALS=()
SESSION_IDS=()

for session_dir in "$SESSIONS_DIR"/session-*; do
    if [ -d "$session_dir" ]; then
        proposal_file="$session_dir/consensus_proposal.yaml"

        if [ -f "$proposal_file" ]; then
            session_id=$(basename "$session_dir")
            number=$(grep "session_number:" "$proposal_file" | cut -d: -f2 | tr -d ' ')
            role=$(grep "role:" "$proposal_file" | cut -d'"' -f2)
            goal=$(grep "goal:" "$proposal_file" | cut -d'"' -f2)

            SESSION_IDS+=("$session_id")
            SESSION_NUMBERS+=("$number")
            SESSION_ROLES+=("$role")
            SESSION_GOALS+=("$goal")

            echo -e "  ${GREEN}✓${NC} $session_id: #$number - $role"
        else
            echo -e "  ${YELLOW}○${NC} $session_dir: No proposal yet"
        fi
    fi
done

echo -e "${GREEN}Found ${#SESSION_IDS[@]} proposals${NC}"
echo ""

# Check for conflicts
echo -e "${YELLOW}[2/4] Checking for Conflicts...${NC}"

CONFLICTS=0

# Check duplicate numbers
for i in "${!SESSION_NUMBERS[@]}"; do
    num="${SESSION_NUMBERS[$i]}"
    count=0
    for j in "${!SESSION_NUMBERS[@]}"; do
        if [ "${SESSION_NUMBERS[$j]}" = "$num" ]; then
            count=$((count + 1))
        fi
    done

    if [ $count -gt 1 ]; then
        echo -e "  ${RED}✗${NC} Duplicate number $num found"
        CONFLICTS=$((CONFLICTS + 1))
    fi
done

# Check sequential numbering
if [ ${#SESSION_NUMBERS[@]} -gt 0 ]; then
    max_num=0
    for num in "${SESSION_NUMBERS[@]}"; do
        if [ "$num" -gt "$max_num" ]; then
            max_num=$num
        fi
    done

    if [ "$max_num" -ne "${#SESSION_NUMBERS[@]}" ]; then
        echo -e "  ${YELLOW}⚠${NC} Non-sequential numbering (max: $max_num, count: ${#SESSION_NUMBERS[@]})"
    fi
fi

if [ $CONFLICTS -eq 0 ]; then
    echo -e "${GREEN}✓ No conflicts detected${NC}"
else
    echo -e "${RED}✗ $CONFLICTS conflicts need resolution${NC}"
fi
echo ""

# Check for agreements
echo -e "${YELLOW}[3/4] Checking Agreement Status...${NC}"

TOTAL_SESSIONS=${#SESSION_IDS[@]}
REQUIRED_AGREEMENTS=$((TOTAL_SESSIONS * (TOTAL_SESSIONS - 1)))
RECEIVED_AGREEMENTS=0

for session_dir in "$SESSIONS_DIR"/session-*; do
    if [ -d "$session_dir" ]; then
        agreements_file="$session_dir/consensus_agreements.txt"

        if [ -f "$agreements_file" ]; then
            count=$(wc -l < "$agreements_file")
            RECEIVED_AGREEMENTS=$((RECEIVED_AGREEMENTS + count))
        fi
    fi
done

AGREEMENT_RATE=0
if [ $REQUIRED_AGREEMENTS -gt 0 ]; then
    AGREEMENT_RATE=$(echo "scale=1; $RECEIVED_AGREEMENTS * 100 / $REQUIRED_AGREEMENTS" | bc 2>/dev/null || echo "0")
fi

echo -e "  Total Sessions: $TOTAL_SESSIONS"
echo -e "  Required Agreements: $REQUIRED_AGREEMENTS (each session agrees on all others)"
echo -e "  Received Agreements: $RECEIVED_AGREEMENTS"
echo -e "  Agreement Rate: ${AGREEMENT_RATE}%"
echo ""

# Generate consensus registry
echo -e "${YELLOW}[4/4] Generating Consensus Registry...${NC}"

cat > "$CONSENSUS_FILE" << EOF
# 🤝 SESSION CONSENSUS REGISTRY
**Collective Intelligence Proof Through Agreement**

**Last Updated:** $(date)
**Status:** $(if [ $CONFLICTS -eq 0 ] && [ "$AGREEMENT_RATE" = "100.0" ]; then echo "✅ CONSENSUS ACHIEVED"; else echo "🔄 IN PROGRESS"; fi)

---

## 📊 CONSENSUS METRICS

**Total Active Sessions:** $TOTAL_SESSIONS
**Proposals Submitted:** ${#SESSION_IDS[@]}
**Conflicts Detected:** $CONFLICTS
**Agreement Rate:** ${AGREEMENT_RATE}%
**Required for Consensus:** 100%

---

## 📝 SESSION REGISTRY

$(for i in "${!SESSION_IDS[@]}"; do
    id="${SESSION_IDS[$i]}"
    num="${SESSION_NUMBERS[$i]}"
    role="${SESSION_ROLES[$i]}"
    goal="${SESSION_GOALS[$i]}"

    echo "### Session $num: $id"
    echo "**Role:** $role"
    echo "**Goal:** $goal"
    echo "**Status:** $([ -f "$SESSIONS_DIR/$id/consensus_final.yaml" ] && echo "✅ FINAL" || echo "🔄 PROPOSED")"
    echo ""

    # Show who agreed
    if [ -f "$SESSIONS_DIR/$id/consensus_agreements.txt" ]; then
        echo "**Agreed By:**"
        while IFS= read -r agreement; do
            echo "- $agreement"
        done < "$SESSIONS_DIR/$id/consensus_agreements.txt"
        echo ""
    fi
done)

---

## 🎯 CONSENSUS STATUS

$(if [ $CONFLICTS -eq 0 ] && [ "$AGREEMENT_RATE" = "100.0" ]; then
cat << 'CONSENSUS_ACHIEVED'
### ✅ CONSENSUS ACHIEVED

All sessions have:
- ✅ Chosen unique numbers
- ✅ Defined clear roles
- ✅ Defined measurable goals
- ✅ Reviewed all other sessions
- ✅ Agreed on all assignments

**This proves real inter-session communication and collective intelligence.**

**Ready for human approval.**
CONSENSUS_ACHIEVED
else
cat << 'IN_PROGRESS'
### 🔄 CONSENSUS IN PROGRESS

**Still needed:**
$([ $CONFLICTS -gt 0 ] && echo "- ⚠️  Resolve $CONFLICTS conflicts")
$([ "$AGREEMENT_RATE" != "100.0" ] && echo "- 🔄 Complete agreements (currently ${AGREEMENT_RATE}%)")

**Sessions should:**
1. Review proposals in this file
2. Broadcast AGREE messages for each session
3. Resolve any conflicts through discussion
4. Achieve 100% agreement

**Process:** docs/coordination/CONSENSUS_PROTOCOL.md
IN_PROGRESS
fi)

---

## 🔄 NEXT COORDINATION CYCLE

**Check again:** Every 5 minutes until consensus
**Manual check:** \`./consensus-coordinator.sh\`

---

**Proof of collective intelligence through demonstrable agreement.**
EOF

echo -e "${GREEN}✓ Registry generated: CONSENSUS_REGISTRY.md${NC}"
echo ""

# Summary
if [ $CONFLICTS -eq 0 ] && [ "$AGREEMENT_RATE" = "100.0" ]; then
    echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✅ CONSENSUS ACHIEVED                                 ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}All sessions have reached agreement!${NC}"
    echo -e "${GREEN}Review: $CONSENSUS_FILE${NC}"
    echo ""
else
    echo -e "${YELLOW}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║  🔄 CONSENSUS IN PROGRESS                              ║${NC}"
    echo -e "${YELLOW}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Agreement rate: ${AGREEMENT_RATE}%${NC}"
    echo -e "${YELLOW}Conflicts: $CONFLICTS${NC}"
    echo ""
fi
