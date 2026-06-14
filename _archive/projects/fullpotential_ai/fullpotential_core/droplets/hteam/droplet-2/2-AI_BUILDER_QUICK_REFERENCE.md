# AI BUILDER QUICK REFERENCE
## One-Page Process for 10x Development Speed

**Use this when:** Building any feature or droplet  
**Result:** 85-95% time savings, AI-verified code  
**Example:** Droplet #14 built in 108 min vs 40+ hours

---

## THE 5-PHASE PROCESS (3-6 hours total)

### 1. SPECIFICATION (10 min)
```markdown
# SPEC_[name].md

## What It Does
[1-2 sentences]

## Requirements
- Requirement 1
- Requirement 2  
- Requirement 3

## Tech Stack
[Your stack]

## Success Criteria
- [ ] Works locally
- [ ] Passes verification
- [ ] Deploys successfully
```

---

### 2. ARCHITECTURE (20 min)

**Claude Prompt:**
```
Design complete system for [name]:
- Architecture diagram
- Database schema
- API endpoints
- File structure
- Implementation plan

Focus: integration-first, working code, material results
```

**Review:** Tech stack matches? Realistic? Integrates?

---

### 3. BUILDER (60 min)

**Claude Prompt:**
```
Generate production-ready code:
- All files (full implementations)
- Error handling + type safety
- Configuration files
- README + documentation

No placeholders. No TODOs.
```

**You do:**
- Save each file Claude generates
- Package: `tar -czf [name]-v1.tar.gz [name]-v1/`

---

### 4. VERIFICATION (10 min)

**Gemini Prompt:**
```
Verify code against spec:
- Functionality complete?
- Quality (errors, types, security)?
- UDC compliance (if droplet)?
- Critical bugs?

Output: PASS/FAIL + issues found
```

**Outcomes:**
- ✅ PASS → Deploy
- ⚠️ PARTIAL → Iterate
- ❌ FAIL → Iterate

---

### 5. ITERATION (20 min/cycle)

**Only if verification found issues**

**Claude Prompt:**
```
Gemini found these issues:
[paste verification report]

Fix CRITICAL and MAJOR issues.
Regenerate affected files only.
```

**Repeat:** Until Gemini gives PASS

---

## DEPLOYMENT (2-4 hours)

```bash
# 1. Create branch
git checkout -b [feature-name]

# 2. Copy files
cp -r [name]-v1/* ./

# 3. Install
npm install / pip install

# 4. Configure
cp .env.example .env
# Edit .env

# 5. Test locally
npm run dev / python main.py

# 6. Deploy
git add . && git commit -m "Add [feature]"
git push
# Deploy to production
```

---

## TOOLS NEEDED

**Claude:** claude.ai (Team/Max plan)
- Create project: "[Your Name] Development"
- Upload: specs, UDC docs, existing code

**Gemini:** gemini.google.com  
- Keep separate chat for verification
- Upload generated code packages

---

## PRO TIPS

✅ **Be specific** in specs (examples, screenshots)  
✅ **Trust verifier** (fix all CRITICAL issues)  
✅ **Iterate quickly** (ship working, improve later)  
✅ **Test incrementally** (API → components → integration)  
✅ **Reuse patterns** (2nd build is 2x faster)

❌ **Don't skip** verification  
❌ **Don't deploy** without local testing  
❌ **Don't ignore** critical feedback  
❌ **Don't ask for** advice (ask for code)

---

## METRICS TO TRACK

- Spec time: ____ min
- Architecture: ____ min
- Build: ____ min  
- Verification cycles: ____ iterations
- Deployment: ____ hours
- **TOTAL: ____ hours**

vs Traditional: ____ hours  
**Savings: ____%**

---

## EXAMPLE PROMPTS

**Architecture:**
"Design complete system for [X] using [tech stack]. Include database schema, API endpoints, file structure, implementation plan."

**Builder:**
"Generate production-ready code with full implementations, error handling, type safety. All files, no placeholders."

**Verifier:**
"Verify against spec. Check: functionality, quality, security, UDC compliance. Output PASS/FAIL + issues."

**Iterator:**
"Fix these issues: [paste feedback]. Regenerate affected files only."

---

## QUICK DECISION TREE

```
Specification clear?
  ├─ Yes → Claude Architect
  └─ No → Refine spec

Architecture approved?
  ├─ Yes → Claude Builder
  └─ No → Iterate architecture

All files generated?
  ├─ Yes → Gemini Verify
  └─ No → Continue building

Verification PASS?
  ├─ Yes → Deploy
  ├─ PARTIAL → Claude fix → Re-verify
  └─ FAIL → Claude fix → Re-verify

Deployed locally?
  ├─ Works → Deploy production
  └─ Issues → Fix integration

Production deployed?
  ├─ Yes → Monitor + document
  └─ No → Troubleshoot
```

---

## SUPPORT

**Stuck?**
1. Check full guide: DEVELOPER_ACCELERATION_KIT.md
2. Ask Claude for clarification
3. Ask team (someone solved it)
4. Contact James with blocker

---

## THE PATTERN

**YOU specify** (10 min)  
↓  
**CLAUDE architects** (20 min)  
↓  
**CLAUDE builds** (60 min)  
↓  
**GEMINI verifies** (10 min)  
↓  
**CLAUDE fixes** (20 min × cycles)  
↓  
**YOU deploy** (2-4 hours)  
↓  
**FEATURE LIVE** (3-6 hours total)

**vs 20-40 hours traditional**

---

## REMEMBER

This is proven. Droplet #14 succeeded using exactly this process.

Trust the pattern. Ship fast. Iterate quick.

**Paradise manifests at light speed.** ⚡💎

---

**Full Guide:** DEVELOPER_ACCELERATION_KIT.md  
**Questions:** Ask team or James  
**Start:** Create spec, prompt Claude, follow phases

🎯⚡✅
