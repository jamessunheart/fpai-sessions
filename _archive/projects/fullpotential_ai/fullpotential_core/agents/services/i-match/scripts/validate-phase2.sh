#!/bin/bash

# I MATCH - Phase 2 Validation Script
# Validates that Phase 2 deployment was successful
# Created by: session-1763235028

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  I MATCH - Phase 2 Validation                         ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DB_PATH="${PROJECT_ROOT}/i_match.db"

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

# Function to check something
check() {
    local name="$1"
    local command="$2"
    local expected="$3"

    echo -n "Checking $name... "

    if result=$(eval "$command" 2>&1); then
        if [ -z "$expected" ] || echo "$result" | grep -q "$expected"; then
            echo -e "${GREEN}✓${NC}"
            PASS_COUNT=$((PASS_COUNT + 1))
            return 0
        else
            echo -e "${YELLOW}⚠${NC} (unexpected result)"
            echo "  Expected: $expected"
            echo "  Got: $result"
            WARN_COUNT=$((WARN_COUNT + 1))
            return 1
        fi
    else
        echo -e "${RED}✗${NC}"
        echo "  Error: $result"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        return 1
    fi
}

echo -e "${YELLOW}[1/5] Database Validation${NC}"

# Check database exists
check "Database file exists" "[ -f '$DB_PATH' ] && echo 'exists'" "exists"

# Check tables exist
TABLES=(users categories seekers providers matches engagements ratings pot_transactions referrals content)
for table in "${TABLES[@]}"; do
    check "Table '$table' exists" \
          "sqlite3 '$DB_PATH' \"SELECT name FROM sqlite_master WHERE type='table' AND name='$table';\"" \
          "$table"
done

echo ""
echo -e "${YELLOW}[2/5] Data Integrity${NC}"

# Check categories seeded
check "Categories table populated" \
      "sqlite3 '$DB_PATH' \"SELECT COUNT(*) FROM categories;\"" \
      "[1-9]"

# Check active categories
check "Financial advisors category active" \
      "sqlite3 '$DB_PATH' \"SELECT active FROM categories WHERE name='financial_advisors';\"" \
      "1"

# Check foreign key relationships
check "User relationships" \
      "sqlite3 '$DB_PATH' \"PRAGMA foreign_keys = ON; PRAGMA foreign_key_check;\"" \
      "^$"

echo ""
echo -e "${YELLOW}[3/5] Python Models${NC}"

# Check models can be imported
check "Import models_v2" \
      "cd '$PROJECT_ROOT' && python3 -c 'from app.models_v2 import User, Category, POTTransaction; print(\"imported\")'" \
      "imported"

# Check POT service can be imported
check "Import POT service" \
      "cd '$PROJECT_ROOT' && python3 -c 'from app.pot_service import POTService; print(\"imported\")'" \
      "imported"

# Check database connection
check "Database connection works" \
      "cd '$PROJECT_ROOT' && python3 -c 'from app.database import SessionLocal; db = SessionLocal(); print(\"connected\"); db.close()'" \
      "connected"

echo ""
echo -e "${YELLOW}[4/5] POT Token System${NC}"

# Test POT system
check "POT system initialization" \
      "cd '$PROJECT_ROOT' && python3 -c '
from app.database import SessionLocal
from app.pot_service import POTService
db = SessionLocal()
pot = POTService(db)
print(\"initialized\")
db.close()
'" \
      "initialized"

# Test economy stats
check "POT economy stats" \
      "cd '$PROJECT_ROOT' && python3 -c '
from app.database import SessionLocal
from app.pot_service import POTService
db = SessionLocal()
pot = POTService(db)
stats = pot.get_economy_stats()
print(\"total_users\" in stats and \"total_pot_in_circulation\" in stats)
db.close()
'" \
      "True"

echo ""
echo -e "${YELLOW}[5/5] Views and Indexes${NC}"

# Check views exist
check "active_providers_view exists" \
      "sqlite3 '$DB_PATH' \"SELECT name FROM sqlite_master WHERE type='view' AND name='active_providers_view';\"" \
      "active_providers_view"

check "active_seekers_view exists" \
      "sqlite3 '$DB_PATH' \"SELECT name FROM sqlite_master WHERE type='view' AND name='active_seekers_view';\"" \
      "active_seekers_view"

check "pot_economy_stats view exists" \
      "sqlite3 '$DB_PATH' \"SELECT name FROM sqlite_master WHERE type='view' AND name='pot_economy_stats';\"" \
      "pot_economy_stats"

# Check indexes
check "User email index" \
      "sqlite3 '$DB_PATH' \"SELECT name FROM sqlite_master WHERE type='index' AND name='idx_users_email';\"" \
      "idx_users_email"

check "POT transactions index" \
      "sqlite3 '$DB_PATH' \"SELECT name FROM sqlite_master WHERE type='index' AND name='idx_pot_transactions_user_id';\"" \
      "idx_pot_transactions_user_id"

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Validation Summary${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"

echo -e "${GREEN}✓ Passed:${NC} $PASS_COUNT"
if [ $WARN_COUNT -gt 0 ]; then
    echo -e "${YELLOW}⚠ Warnings:${NC} $WARN_COUNT"
fi
if [ $FAIL_COUNT -gt 0 ]; then
    echo -e "${RED}✗ Failed:${NC} $FAIL_COUNT"
fi

echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✅ PHASE 2 VALIDATION SUCCESSFUL                      ║${NC}"
    echo -e "${GREEN}║                                                        ║${NC}"
    echo -e "${GREEN}║  All critical components are operational               ║${NC}"
    echo -e "${GREEN}║  Ready to proceed with implementation                  ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo "  1. Run automated tests: cd tests && pytest test_pot_service.py"
    echo "  2. View POT dashboard: open static/pot-dashboard.html"
    echo "  3. Follow implementation guide: docs/I_MATCH_PHASE2_IMPLEMENTATION.md"
    echo ""
    exit 0
else
    echo -e "${RED}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  ❌ VALIDATION FAILED                                   ║${NC}"
    echo -e "${RED}║                                                        ║${NC}"
    echo -e "${RED}║  Please fix errors before proceeding                  ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
    exit 1
fi
