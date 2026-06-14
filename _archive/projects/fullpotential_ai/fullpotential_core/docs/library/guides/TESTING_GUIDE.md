# 🔍 SERVICE TESTING GUIDE

**Goal:** Validate I PROACTIVE and I MATCH actually work (not just code files)

---

## QUICK START (5 minutes)

### Test I PROACTIVE

```bash
# 1. Navigate to service
cd /Users/jamessunheart/Development/agents/services/i-proactive

# 2. Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Create .env file
cp .env.example .env

# 4. Run validation
python3 validate.py
```

**Expected Result:**
```
🎉 ALL TESTS PASSED! Service is ready to start.
```

If you see this = **I PROACTIVE works!** ✅

---

### Test I MATCH

```bash
# 1. Navigate to service
cd /Users/jamessunheart/Development/agents/services/i-match

# 2. Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Create .env file
cp .env.example .env

# 4. Run validation
python3 validate.py
```

**Expected Result:**
```
🎉 ALL TESTS PASSED! Service is ready to start.
```

If you see this = **I MATCH works!** ✅

---

## FULL TESTING (15 minutes)

### Phase 1: Start I PROACTIVE

```bash
cd /Users/jamessunheart/Development/agents/services/i-proactive
source venv/bin/activate

# Start service
uvicorn app.main:app --reload --port 8400
```

**Service should start at:** `http://localhost:8400`

### Phase 2: Test I PROACTIVE Endpoints

Open new terminal:

```bash
# Test health endpoint (UBIC compliance)
curl http://localhost:8400/health

# Expected response:
# {
#   "status": "healthy",
#   "droplet_id": 20,
#   "service_name": "i-proactive",
#   "uptime_seconds": 10,
#   ...
# }

# Test capabilities
curl http://localhost:8400/capabilities

# Test root
curl http://localhost:8400/

# View API docs
open http://localhost:8400/docs
```

**If these work = I PROACTIVE is LIVE!** 🚀

---

### Phase 3: Start I MATCH

```bash
cd /Users/jamessunheart/Development/agents/services/i-match
source venv/bin/activate

# Start service
uvicorn app.main:app --reload --port 8401
```

**Service should start at:** `http://localhost:8401`

### Phase 4: Test I MATCH Endpoints

Open new terminal:

```bash
# Test health
curl http://localhost:8401/health

# Test capabilities
curl http://localhost:8401/capabilities

# View API docs
open http://localhost:8401/docs
```

**If these work = I MATCH is LIVE!** 🚀

---

## ADVANCED TESTING (30 minutes)

### Test I MATCH Revenue Flow

#### 1. Create a customer

```bash
curl -X POST "http://localhost:8401/customers/create" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Smith",
    "email": "john@example.com",
    "service_type": "financial_advisor",
    "needs_description": "Need retirement planning help",
    "preferences": {"budget": "premium"},
    "values": {"integrity": 10},
    "location_city": "San Francisco",
    "location_state": "CA"
  }'
```

**Expected:** Customer created with ID

#### 2. Create a provider

```bash
curl -X POST "http://localhost:8401/providers/create" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Jane Doe CFP",
    "email": "jane@advisor.com",
    "company": "Doe Financial",
    "service_type": "financial_advisor",
    "specialties": ["retirement_planning"],
    "description": "20 years experience",
    "years_experience": 20,
    "pricing_model": "retainer",
    "price_range_low": 5000,
    "price_range_high": 20000,
    "location_city": "San Francisco",
    "location_state": "CA",
    "commission_percent": 20.0
  }'
```

**Expected:** Provider created with ID

#### 3. Create a match

```bash
# Replace customer_id and provider_id with actual IDs from above
curl -X POST "http://localhost:8401/matches/create?customer_id=1&provider_id=1"
```

**Expected:**
```json
{
  "match_id": 1,
  "customer_name": "John Smith",
  "provider_name": "Jane Doe CFP",
  "match_score": 85,
  "match_quality": "Very Good Match",
  "match_reasoning": "Strong expertise match...",
  ...
}
```

**⚠️ Note:** AI matching requires `ANTHROPIC_API_KEY` in .env

#### 4. Confirm engagement (earn commission!)

```bash
# When customer and provider agree to work together
curl -X POST "http://localhost:8401/matches/1/confirm-engagement?deal_value_usd=50000"
```

**Expected:**
```json
{
  "match_id": 1,
  "deal_value_usd": 50000,
  "commission_amount_usd": 10000,
  "commission_percent": 20.0
}
```

**🎉 YOU JUST EARNED $10,000 COMMISSION!** (in test environment)

#### 5. Check revenue stats

```bash
curl http://localhost:8401/commissions/stats
```

**Expected:**
```json
{
  "total_amount_usd": 10000,
  "pending_amount_usd": 10000,
  "paid_amount_usd": 0
}
```

---

## TROUBLESHOOTING

### "Module not found" errors
```bash
# Make sure you're in virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### "Port already in use"
```bash
# Find and kill process using port
lsof -ti:8400 | xargs kill  # For I PROACTIVE
lsof -ti:8401 | xargs kill  # For I MATCH
```

### "Database error"
```bash
# For I MATCH - delete and recreate database
cd /Users/jamessunheart/Development/agents/services/i-match
rm -f imatch.db
python3 -c "from app.database import init_db; init_db()"
```

### "API key not configured"
```bash
# Edit .env file
nano .env

# Add your keys:
ANTHROPIC_API_KEY=sk-ant-xxxxx
OPENAI_API_KEY=sk-xxxxx
```

Get keys:
- Anthropic: https://console.anthropic.com/settings/keys
- OpenAI: https://platform.openai.com/api-keys

---

## SUCCESS CRITERIA

✅ **I PROACTIVE validated if:**
- All 7 validation tests pass
- Service starts without errors
- `/health` endpoint returns 200
- API docs load at `/docs`

✅ **I MATCH validated if:**
- All 6 validation tests pass
- Service starts without errors
- Can create customer/provider
- Database tables created
- Commission calculation works

✅ **BOTH services validated if:**
- Both pass all tests
- Both run simultaneously (different ports)
- All UBIC endpoints work
- Can create test revenue flow in I MATCH

---

## WHAT TO REPORT BACK

After testing, report:

1. **Did validation scripts pass?**
   - I PROACTIVE: ✅/❌
   - I MATCH: ✅/❌

2. **Did services start?**
   - I PROACTIVE: ✅/❌
   - I MATCH: ✅/❌

3. **Any errors encountered?**
   - Copy-paste any error messages

4. **What worked?**
   - Which endpoints responded correctly

This will show us what's actually working vs what needs debugging!

---

🔍 **Start with validation scripts - they'll tell you exactly what works and what doesn't.**
