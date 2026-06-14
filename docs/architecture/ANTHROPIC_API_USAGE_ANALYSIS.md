# Anthropic API Usage Analysis

**Date:** 2025-12-10  
**Cost:** $233.25  
**Status:** ⚠️ Investigation Required

---

## 🔍 Key Finding

An Anthropic API key (`sk-ant-api03-C6r...gQAA`) has accumulated **$233.25 in costs** over the period Nov 29 - Dec 10, 2025.

---

## 📊 Services Using Anthropic API

### Primary Services (Active)

1. **I PROACTIVE** (`SERVICES/i-proactive/`)
   - **Usage:** Model routing for AI tasks
   - **Fallback Logic:** GPU Bridge → Ollama → Claude (fallback only)
   - **Status:** Should prefer GPU Bridge/Ollama
   - **Risk:** ⚠️ May fallback to Claude if GPU Bridge fails

2. **I MATCH** (`SERVICES/i-match/`)
   - **Usage:** AI-powered matching engine
   - **Fallback Logic:** Ollama → Claude (fallback only)
   - **Status:** Should prefer Ollama
   - **Risk:** ⚠️ May fallback to Claude if Ollama unavailable

3. **Spec Builder** (`SERVICES/spec-builder/`)
   - **Usage:** SPEC generation using Claude API
   - **Status:** ⚠️ Direct Claude usage (no fallback)
   - **Risk:** 🔴 High - Direct Claude calls

4. **Spec Optimizer** (`SERVICES/spec-optimizer/`)
   - **Usage:** SPEC optimization using Claude API
   - **Status:** ⚠️ Direct Claude usage (no fallback)
   - **Risk:** 🔴 High - Direct Claude calls

5. **AI Brain** (`SERVICES/ai-brain/`)
   - **Usage:** Intelligence engine with Claude fallback
   - **Fallback Logic:** GPU Fleet → Groq → Ollama → Anthropic
   - **Status:** Should prefer local models
   - **Risk:** ⚠️ May fallback to Claude

6. **Brick2 Marketing Engine** (`SERVICES/brick2-marketing-engine/`)
   - **Usage:** Content generation (Claude preferred)
   - **Status:** ⚠️ Claude is preferred provider
   - **Risk:** 🔴 High - Claude is primary choice

---

## 🔴 High-Risk Services (Direct Claude Usage)

### 1. Spec Builder
- **File:** `SERVICES/spec-builder/app/services/claude_client.py`
- **Usage:** Direct Claude API calls for SPEC generation
- **No Fallback:** Uses Claude exclusively
- **Recommendation:** Migrate to GPU Bridge/Ollama

### 2. Spec Optimizer
- **File:** `SERVICES/spec-optimizer/app/services/claude_client.py`
- **Usage:** Direct Claude API calls for SPEC optimization
- **No Fallback:** Uses Claude exclusively
- **Recommendation:** Migrate to GPU Bridge/Ollama

### 3. Brick2 Marketing Engine
- **File:** `SERVICES/brick2-marketing-engine/app/ai/gateway.py`
- **Usage:** Claude is preferred provider for content generation
- **Routing:** Claude for content, code, strategic planning
- **Recommendation:** Change preference to GPU Bridge/Ollama

---

## ⚠️ Medium-Risk Services (Fallback Usage)

### 1. I PROACTIVE
- **Current:** GPU Bridge → Ollama → Claude fallback
- **Risk:** Falls back to Claude if GPU Bridge/Ollama fail
- **Recommendation:** Ensure GPU Bridge is healthy, monitor fallbacks

### 2. I MATCH
- **Current:** Ollama → Claude fallback
- **Risk:** Falls back to Claude if Ollama unavailable
- **Recommendation:** Ensure Ollama is healthy, monitor fallbacks

### 3. AI Brain
- **Current:** GPU Fleet → Groq → Ollama → Anthropic fallback
- **Risk:** Falls back to Claude if all local options fail
- **Recommendation:** Monitor fallback frequency

---

## 💰 Cost Analysis

### Estimated Costs (Claude Pricing)
- **Claude Opus 4.5:** $5/$25 per 1M tokens (input/output)
- **Claude Sonnet 4:** $3/$15 per 1M tokens (input/output)
- **Claude Haiku:** $0.25/$1.25 per 1M tokens (input/output)

### $233.25 Breakdown (Estimated)
- **If Opus:** ~46M input tokens or ~9M output tokens
- **If Sonnet:** ~77M input tokens or ~15M output tokens
- **If Haiku:** ~933M input tokens or ~186M output tokens

**Most Likely:** Mix of Sonnet/Opus usage over 11 days = ~$21/day average

---

## 🔍 Investigation Steps

### 1. Check Active Usage
```bash
# Check logs for Claude API calls
grep -r "anthropic\|claude" /opt/fpai/*/logs/ 2>/dev/null | grep -i "cost\|tokens"

# Check service configurations
grep -r "anthropic_api_key" /opt/fpai/*/app/config.py 2>/dev/null
```

### 2. Identify High-Usage Services
```bash
# Check which services are making calls
ps aux | grep -E "spec-builder|spec-optimizer|brick2|i-proactive|i-match"

# Check service logs
tail -f /opt/fpai/*/logs/*.log | grep -i "claude\|anthropic"
```

### 3. Monitor Fallback Frequency
```bash
# Check for fallback messages
grep -r "fallback\|failed\|unavailable" /opt/fpai/*/logs/ | grep -i "claude\|anthropic"
```

---

## 🎯 Immediate Actions

### 1. **Disable Direct Claude Usage** (High Priority)
- **Spec Builder:** Migrate to GPU Bridge/Ollama
- **Spec Optimizer:** Migrate to GPU Bridge/Ollama
- **Brick2 Marketing:** Change preference to GPU Bridge/Ollama

### 2. **Monitor Fallback Usage** (Medium Priority)
- Add logging for Claude fallback events
- Track fallback frequency
- Investigate why fallbacks occur

### 3. **Verify GPU Bridge Health** (Medium Priority)
- Ensure GPU Bridge is healthy (25 endpoints)
- Verify Ollama is running
- Check service connectivity

### 4. **Add Cost Tracking** (Low Priority)
- Implement cost tracking per service
- Add cost alerts
- Create cost dashboard

---

## 📋 Recommended Changes

### Priority 1: Migrate Spec Services
1. Update `spec-builder` to use GPU Bridge
2. Update `spec-optimizer` to use GPU Bridge
3. Test and verify functionality

### Priority 2: Update Brick2 Marketing
1. Change Claude preference to GPU Bridge/Ollama
2. Make Claude fallback only
3. Test content generation

### Priority 3: Add Monitoring
1. Add cost tracking to all Claude calls
2. Log fallback events
3. Create cost alerts

---

## 🔒 Security Note

The API key `sk-ant-api03-C6r...gQAA` is visible in:
- Configuration files
- Environment variables
- Service logs

**Recommendation:** Rotate key after migration, use secure storage

---

## 📊 Expected Cost Reduction

### After Migration
- **Spec Builder:** $0 (was ~$50-100/month estimated)
- **Spec Optimizer:** $0 (was ~$50-100/month estimated)
- **Brick2 Marketing:** ~$0 (was ~$50-100/month estimated)
- **Fallback Usage:** ~$10-20/month (only when local fails)

### Total Savings: ~$150-300/month

---

## ✅ Next Steps

1. **Immediate:** Identify which service(s) are causing the $233 cost
2. **Short-term:** Migrate high-risk services to GPU Bridge
3. **Long-term:** Add comprehensive cost tracking and alerts

---

**Status:** 🔴 Investigation Required  
**Action:** Identify primary cost source and migrate to GPU Bridge











