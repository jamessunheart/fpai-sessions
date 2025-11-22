#!/bin/bash

# I MATCH - Phase 2 One-Click Deployment Script
# Deploys multi-category marketplace + POTENTIAL token system
# Created by: session-1763235028
# Date: 2025-11-15

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DB_PATH="${PROJECT_ROOT}/i_match.db"
BACKUP_DIR="${PROJECT_ROOT}/backups"
MIGRATION_PATH="${PROJECT_ROOT}/migrations/001_marketplace_v2_schema.sql"

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  I MATCH - Phase 2 Deployment                         ║${NC}"
echo -e "${BLUE}║  Multi-Category Marketplace + POT Token System        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Step 1: Pre-flight checks
echo -e "${YELLOW}[1/7] Pre-flight Checks...${NC}"

# Check if running in correct directory
if [ ! -f "${PROJECT_ROOT}/app/main.py" ]; then
    echo -e "${RED}❌ Error: Not in I MATCH project directory${NC}"
    echo "Please run this script from agents/services/i-match/"
    exit 1
fi

# Check if migration file exists
if [ ! -f "$MIGRATION_PATH" ]; then
    echo -e "${RED}❌ Error: Migration file not found${NC}"
    echo "Expected: $MIGRATION_PATH"
    exit 1
fi

# Check if database exists
if [ ! -f "$DB_PATH" ]; then
    echo -e "${YELLOW}⚠️  Warning: Database not found. Will create new database.${NC}"
    NEW_DB=true
else
    NEW_DB=false
fi

# Check for required tools
command -v sqlite3 >/dev/null 2>&1 || {
    echo -e "${RED}❌ Error: sqlite3 not installed${NC}"
    exit 1
}

command -v python3 >/dev/null 2>&1 || {
    echo -e "${RED}❌ Error: python3 not installed${NC}"
    exit 1
}

echo -e "${GREEN}✅ Pre-flight checks passed${NC}"
echo ""

# Step 2: Backup existing database
echo -e "${YELLOW}[2/7] Backing Up Database...${NC}"

if [ "$NEW_DB" = false ]; then
    mkdir -p "$BACKUP_DIR"
    BACKUP_FILE="${BACKUP_DIR}/i_match_backup_$(date +%Y%m%d_%H%M%S).db"
    cp "$DB_PATH" "$BACKUP_FILE"
    echo -e "${GREEN}✅ Backup created: $BACKUP_FILE${NC}"
else
    echo -e "${BLUE}ℹ️  No existing database to backup${NC}"
fi
echo ""

# Step 3: Run database migration
echo -e "${YELLOW}[3/7] Running Database Migration...${NC}"

# Create test database first
TEST_DB="${PROJECT_ROOT}/i_match_test.db"
if [ "$NEW_DB" = false ]; then
    cp "$DB_PATH" "$TEST_DB"
else
    touch "$TEST_DB"
fi

# Test migration on copy
if sqlite3 "$TEST_DB" < "$MIGRATION_PATH" 2>/dev/null; then
    echo -e "${GREEN}✅ Migration test successful on copy${NC}"

    # Run on production database
    if sqlite3 "$DB_PATH" < "$MIGRATION_PATH" 2>&1 | tee migration.log; then
        echo -e "${GREEN}✅ Migration applied to production database${NC}"
    else
        echo -e "${RED}❌ Migration failed. Check migration.log${NC}"
        exit 1
    fi
else
    echo -e "${RED}❌ Migration test failed${NC}"
    exit 1
fi

# Clean up test database
rm -f "$TEST_DB"
echo ""

# Step 4: Verify migration
echo -e "${YELLOW}[4/7] Verifying Migration...${NC}"

# Check for expected tables
EXPECTED_TABLES=(
    "users"
    "categories"
    "seekers"
    "providers"
    "matches"
    "engagements"
    "ratings"
    "pot_transactions"
    "referrals"
    "content"
)

echo "Checking for tables..."
MISSING_TABLES=0
for table in "${EXPECTED_TABLES[@]}"; do
    if sqlite3 "$DB_PATH" "SELECT name FROM sqlite_master WHERE type='table' AND name='$table';" | grep -q "$table"; then
        echo -e "  ${GREEN}✓${NC} $table"
    else
        echo -e "  ${RED}✗${NC} $table (missing)"
        MISSING_TABLES=$((MISSING_TABLES + 1))
    fi
done

if [ $MISSING_TABLES -eq 0 ]; then
    echo -e "${GREEN}✅ All tables created successfully${NC}"
else
    echo -e "${RED}❌ Migration incomplete: $MISSING_TABLES tables missing${NC}"
    exit 1
fi

# Check categories were seeded
CATEGORY_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM categories;")
echo "Categories in database: $CATEGORY_COUNT"
if [ "$CATEGORY_COUNT" -ge 4 ]; then
    echo -e "${GREEN}✅ Initial categories seeded${NC}"
else
    echo -e "${YELLOW}⚠️  Only $CATEGORY_COUNT categories found (expected 4)${NC}"
fi
echo ""

# Step 5: Migrate existing data (if applicable)
echo -e "${YELLOW}[5/7] Migrating Existing Data...${NC}"

if [ "$NEW_DB" = false ]; then
    # Check if old tables exist
    OLD_CUSTOMERS=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM customers;" 2>/dev/null || echo "0")
    OLD_PROVIDERS=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM providers;" 2>/dev/null || echo "0")

    if [ "$OLD_CUSTOMERS" -gt 0 ] || [ "$OLD_PROVIDERS" -gt 0 ]; then
        echo "Found existing data to migrate:"
        echo "  Customers: $OLD_CUSTOMERS"
        echo "  Providers: $OLD_PROVIDERS"

        # Run data migration SQL
        cat > /tmp/migrate_data.sql << 'EOF'
-- Migrate customers to users and seekers
INSERT OR IGNORE INTO users (email, name, account_type, created_at)
SELECT DISTINCT email, name, 'seeker', created_at
FROM customers
WHERE email NOT IN (SELECT email FROM users);

INSERT OR IGNORE INTO seekers (user_id, category_id, needs_description, budget_min, budget_max, location, created_at)
SELECT
    u.id,
    (SELECT id FROM categories WHERE name = 'financial_advisors' LIMIT 1),
    c.needs_description,
    CAST(json_extract(c.preferences, '$.budget_min') AS INTEGER),
    CAST(json_extract(c.preferences, '$.budget_max') AS INTEGER),
    COALESCE(c.location_city || ', ' || c.location_state, c.location_city, c.location_state),
    c.created_at
FROM customers c
JOIN users u ON c.email = u.email
WHERE c.email NOT IN (SELECT u2.email FROM seekers s JOIN users u2 ON s.user_id = u2.id);

-- Migrate providers to users and providers
INSERT OR IGNORE INTO users (email, name, account_type, created_at)
SELECT DISTINCT email, name, 'provider', created_at
FROM providers
WHERE email NOT IN (SELECT email FROM users);

INSERT OR IGNORE INTO providers (user_id, category_id, business_name, bio, specialties, years_experience, certifications, pricing_min, pricing_max, location, created_at, status)
SELECT
    u.id,
    (SELECT id FROM categories WHERE name = 'financial_advisors' LIMIT 1),
    p.company,
    p.description,
    p.specialties,
    p.years_experience,
    p.certifications,
    CAST(p.price_range_low AS INTEGER),
    CAST(p.price_range_high AS INTEGER),
    COALESCE(p.location_city || ', ' || p.location_state, p.location_city, p.location_state),
    p.created_at,
    CASE WHEN p.active = 1 THEN 'active' ELSE 'inactive' END
FROM providers p
JOIN users u ON p.email = u.email
WHERE p.email NOT IN (SELECT u2.email FROM providers prov JOIN users u2 ON prov.user_id = u2.id);
EOF

        if sqlite3 "$DB_PATH" < /tmp/migrate_data.sql 2>&1 | tee data_migration.log; then
            echo -e "${GREEN}✅ Data migration successful${NC}"

            # Verify migrated data
            NEW_USERS=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM users;")
            NEW_SEEKERS=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM seekers;")
            NEW_PROVIDERS=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM providers;")

            echo "Migration results:"
            echo "  Users: $NEW_USERS"
            echo "  Seekers: $NEW_SEEKERS"
            echo "  Providers: $NEW_PROVIDERS"
        else
            echo -e "${RED}❌ Data migration failed. Check data_migration.log${NC}"
            exit 1
        fi

        rm /tmp/migrate_data.sql
    else
        echo -e "${BLUE}ℹ️  No existing data to migrate${NC}"
    fi
else
    echo -e "${BLUE}ℹ️  New database - no data migration needed${NC}"
fi
echo ""

# Step 6: Test POT system
echo -e "${YELLOW}[6/7] Testing POT Token System...${NC}"

python3 << 'PYTHON_EOF'
import sys
sys.path.insert(0, '/Users/jamessunheart/Development/agents/services/i-match')

from app.database import SessionLocal
from app.pot_service import POTService
from app.models_v2 import User, Category
import traceback

try:
    db = SessionLocal()
    pot_service = POTService(db)

    # Test 1: Create test user
    test_user = User(
        email=f"test_pot_{import_time.time()}@imatch.com",
        name="POT Test User",
        account_type="seeker"
    )
    db.add(test_user)
    db.commit()
    print(f"✓ Created test user (ID: {test_user.id})")

    # Test 2: Award POT
    result = pot_service.award_pot(
        user_id=test_user.id,
        category="seeker_profile_creation",
        description="Test POT award"
    )
    print(f"✓ Awarded {result['amount']} POT")
    print(f"  Balance: {result['balance_before']} → {result['balance_after']}")

    # Test 3: Get balance
    balance = pot_service.get_user_balance(test_user.id)
    assert balance == 25, f"Expected 25 POT, got {balance}"
    print(f"✓ Balance verification: {balance} POT")

    # Test 4: Spend POT
    try:
        spend_result = pot_service.spend_pot(
            user_id=test_user.id,
            category="premium_match",
            description="Test POT spending"
        )
        print(f"✗ Spending test failed - should have insufficient balance")
        sys.exit(1)
    except ValueError as e:
        if "Insufficient POT balance" in str(e):
            print(f"✓ Insufficient balance check working")
        else:
            raise

    # Test 5: Award more POT and spend
    pot_service.award_pot(
        user_id=test_user.id,
        category="seeker_first_engagement",
        description="Test engagement bonus"
    )

    spend_result = pot_service.spend_pot(
        user_id=test_user.id,
        category="premium_match",
        description="Test premium match purchase"
    )
    print(f"✓ Spent {abs(spend_result['amount'])} POT")
    print(f"  Balance: {spend_result['balance_before']} → {spend_result['balance_after']}")

    # Test 6: Get transaction history
    history = pot_service.get_transaction_history(test_user.id)
    assert len(history) == 3, f"Expected 3 transactions, got {len(history)}"
    print(f"✓ Transaction history: {len(history)} transactions")

    # Test 7: Get economy stats
    stats = pot_service.get_economy_stats()
    print(f"✓ Economy stats retrieved")
    print(f"  Total users: {stats['total_users']}")
    print(f"  POT in circulation: {stats['total_pot_in_circulation']}")

    # Clean up test user
    db.delete(test_user)
    db.commit()
    print(f"✓ Cleaned up test user")

    db.close()
    print("\n✅ All POT system tests passed!")
    sys.exit(0)

except Exception as e:
    print(f"\n❌ POT system test failed:")
    print(f"   {str(e)}")
    traceback.print_exc()
    sys.exit(1)

import time as import_time
PYTHON_EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ POT system operational${NC}"
else
    echo -e "${RED}❌ POT system tests failed${NC}"
    exit 1
fi
echo ""

# Step 7: Generate deployment summary
echo -e "${YELLOW}[7/7] Generating Deployment Summary...${NC}"

cat > deployment_summary.txt << EOF
═══════════════════════════════════════════════════════════
I MATCH - PHASE 2 DEPLOYMENT SUMMARY
═══════════════════════════════════════════════════════════

Deployment Date: $(date)
Deployed By: $(whoami)

DATABASE STATUS:
  Path: $DB_PATH
  Backup: $BACKUP_FILE
  Migration: Success

TABLES CREATED:
$(for table in "${EXPECTED_TABLES[@]}"; do echo "  ✓ $table"; done)

CATEGORIES AVAILABLE:
$(sqlite3 "$DB_PATH" "SELECT '  ' || CASE WHEN active = 1 THEN '✓' ELSE '○' END || ' ' || display_name || ' (' || name || ')' FROM categories;")

POT TOKEN SYSTEM:
  Status: Operational
  Economy Stats:
$(python3 << 'PYSTATS'
import sys
sys.path.insert(0, '/Users/jamessunheart/Development/agents/services/i-match')
from app.database import SessionLocal
from app.pot_service import POTService
db = SessionLocal()
pot_service = POTService(db)
stats = pot_service.get_economy_stats()
for key, value in stats.items():
    print(f"    {key}: {value}")
db.close()
PYSTATS
)

NEXT STEPS:
  1. Update app/main.py to use models_v2
  2. Add POT reward triggers to existing endpoints
  3. Deploy POT API endpoints
  4. Update frontend to display POT balances
  5. Activate additional categories
  6. Start Phase 2 marketing

DOCUMENTATION:
  - Full design: docs/I_MATCH_MARKETPLACE_DESIGN.md
  - Implementation guide: docs/I_MATCH_PHASE2_IMPLEMENTATION.md
  - This summary: deployment_summary.txt

═══════════════════════════════════════════════════════════
EOF

cat deployment_summary.txt

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ PHASE 2 DEPLOYMENT COMPLETE                        ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Deployment summary saved to: deployment_summary.txt${NC}"
echo ""
echo -e "${YELLOW}Next: Follow implementation guide for app integration${NC}"
echo -e "${YELLOW}      docs/I_MATCH_PHASE2_IMPLEMENTATION.md${NC}"
echo ""
