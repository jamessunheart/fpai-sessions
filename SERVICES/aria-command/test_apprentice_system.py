#!/usr/bin/env python3
"""
APPRENTICE ONBOARDING SYSTEM - FULL TEST
"""
import os
import sys

# Load environment
from dotenv import load_dotenv
load_dotenv()

print("=" * 50)
print("APPRENTICE ONBOARDING SYSTEM - FULL TEST")
print("=" * 50)

# Test 1: Authority System
print("\n[1] AUTHORITY SYSTEM")
from access.authority import (
    get_user_authority, is_steward, is_apprentice,
    can_write_path, can_read_path, get_apprentice_workspace,
    STEWARD_IDS, APPRENTICE_IDS, AuthorityLevel
)

print(f"  Steward IDs configured: {STEWARD_IDS}")
print(f"  Apprentice IDs (in-memory): {APPRENTICE_IDS}")

# Test James
james_id = 1759822075
auth = get_user_authority(james_id)
print(f"  James ({james_id}): {auth.level.value}")
assert auth.level == AuthorityLevel.STEWARD, "James should be steward!"
print("  PASS: James is steward")

# Test unknown user
unknown = get_user_authority(999999999)
print(f"  Unknown user: {unknown.level.value}")
assert unknown.level == AuthorityLevel.UNKNOWN, "Unknown user should be blocked"
print("  PASS: Unknown users blocked")

# Test 2: Path Restrictions
print("\n[2] PATH RESTRICTIONS")
test_apprentice = 123456789

# Test apprentice write to core (should fail)
allowed, reason = can_write_path(test_apprentice, "/opt/fpai/aria-command/brain/tools.py")
print(f"  Apprentice write to core: {allowed} - {reason}")
print("  (Expected: False - users cannot write to core)")

# Test steward can write anywhere
allowed, reason = can_write_path(james_id, "/opt/fpai/aria-command/test.py")
print(f"  Steward write to core: {allowed} - {reason}")
assert allowed, "Steward should write anywhere!"
print("  PASS: Steward has full access")

# Test 3: Rate Limiter
print("\n[3] RATE LIMITER")
from access.rate_limiter import check_rate_limit, record_request, get_rate_limiter
limiter = get_rate_limiter()
print(f"  Rate limiter enabled: {limiter._enabled}")

# Check steward (should have no limits)
allowed, msg, retry = check_rate_limit(james_id, "message")
print(f"  Steward rate limit: {allowed} - {msg}")
assert allowed, "Steward should have no limits!"
print("  PASS: Steward has no limits")

# Test 4: Supabase Connection
print("\n[4] SUPABASE CONNECTION")
from integrations.supabase_client import SupabaseClient
client = SupabaseClient()
print(f"  Supabase enabled: {client.enabled}")

if client.enabled:
    print("  PASS: Supabase connected")
    
    # Check for required tables
    print("\n[4b] CHECKING REQUIRED TABLES")
    tables = ["apprentice_activity", "apprentice_progress", "usage_costs", "rate_limits"]
    missing_tables = []
    for table in tables:
        try:
            result = client.client.table(table).select("*").limit(1).execute()
            print(f"    {table}: EXISTS")
        except Exception as e:
            err = str(e)
            if "does not exist" in err or "PGRST" in err:
                print(f"    {table}: MISSING")
                missing_tables.append(table)
            else:
                print(f"    {table}: ERROR - {err[:80]}")
    
    if missing_tables:
        print(f"\n  WARNING: {len(missing_tables)} tables missing. Run the SQL schema!")
    else:
        print("  PASS: All tables exist")
else:
    print("  WARNING: Supabase not connected - check env vars")

# Test 5: Directory Structure
print("\n[5] DIRECTORY STRUCTURE")
dirs = [
    "/opt/fpai/labs",
    "/opt/fpai/labs/apprentices",
    "/opt/fpai/labs/shared",
    "/opt/fpai/labs/submissions",
    "/opt/fpai/apprentice-os/library/challenges"
]
all_exist = True
for d in dirs:
    exists = os.path.isdir(d)
    status = "EXISTS" if exists else "MISSING"
    print(f"  {d}: {status}")
    if not exists:
        all_exist = False

if all_exist:
    print("  PASS: All directories exist")
else:
    print("  FAIL: Some directories missing")

# Test 6: First Challenge
print("\n[6] FIRST CHALLENGE")
challenge_path = "/opt/fpai/apprentice-os/library/challenges/first-challenge.md"
exists = os.path.isfile(challenge_path)
status = "EXISTS" if exists else "MISSING"
print(f"  First challenge file: {status}")

if exists:
    with open(challenge_path, 'r') as f:
        content = f.read()
    print(f"  File size: {len(content)} bytes")
    print("  PASS: First challenge ready")
else:
    print("  FAIL: First challenge missing")

# Test 7: Service Health
print("\n[7] SERVICE HEALTH")
import requests
try:
    resp = requests.get("http://localhost:8750/health", timeout=5)
    if resp.status_code == 200:
        print(f"  Aria service: HEALTHY")
        print("  PASS: Service running")
    else:
        print(f"  Aria service: UNHEALTHY ({resp.status_code})")
except Exception as e:
    print(f"  Aria service: ERROR - {e}")

# Summary
print("\n" + "=" * 50)
print("SUMMARY")
print("=" * 50)

issues = []
if not client.enabled:
    issues.append("Supabase not connected")
if missing_tables:
    issues.append(f"Missing tables: {', '.join(missing_tables)}")
if not all_exist:
    issues.append("Missing directories")

if issues:
    print("ISSUES FOUND:")
    for i in issues:
        print(f"  - {i}")
    print("\nACTION REQUIRED:")
    print("  1. Run the SQL schema in Supabase SQL Editor:")
    print("     File: /opt/fpai/apprentice-os/core/supabase-schema-v2.sql")
else:
    print("ALL SYSTEMS READY!")
    print("\nReady to onboard apprentices with:")
    print("  /addapprentice <telegram_user_id>")


