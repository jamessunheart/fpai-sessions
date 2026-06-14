# AI ACCELERATION - DEVELOPER ONBOARDING CHECKLIST
## Get Set Up in 15 Minutes

**Purpose:** Enable any Full Potential developer to start using AI-accelerated development immediately

**Result:** Ready to build features 10x faster

---

## ✅ SETUP CHECKLIST

### 1. Access (5 min)

- [ ] **Claude Account**
  - Go to claude.ai
  - Sign in/create account
  - Verify you have Team or Max plan access
  - (If not, request from James)

- [ ] **Gemini Account**
  - Go to gemini.google.com
  - Sign in with Google account
  - Free tier is sufficient

- [ ] **Documentation Access**
  - Download: DEVELOPER_ACCELERATION_KIT.md
  - Download: AI_BUILDER_QUICK_REFERENCE.md
  - Bookmark both for quick reference

---

### 2. Claude Project Setup (5 min)

- [ ] **Create Your Project**
  - In Claude, click "New Project"
  - Name: "[Your Name] - Full Potential Development"
  - Description: "AI-accelerated development workspace"

- [ ] **Upload Project Knowledge**
  - Upload: UDC_v1_0_Compliance_Checklist.pdf (if working on droplets)
  - Upload: Your tech stack preferences (create TECH_STACK.md)
  - Upload: Any existing code documentation
  - Upload: Code standards/guidelines

- [ ] **Test the Setup**
  - Create new chat in your project
  - Prompt: "What files do you have access to?"
  - Verify Claude can see uploaded documents

---

### 3. Quick Reference Setup (2 min)

- [ ] **Create Local Workspace**
  ```bash
  mkdir ~/full-potential-ai
  cd ~/full-potential-ai
  
  # Create quick reference folders
  mkdir specs
  mkdir builds
  mkdir docs
  ```

- [ ] **Save Templates**
  - Save SPEC template from quick reference
  - Save example prompts
  - Keep in docs/ folder

- [ ] **Bookmark Tools**
  - Bookmark: claude.ai (your project)
  - Bookmark: gemini.google.com
  - Bookmark: This checklist

---

### 4. First Test Build (3 min)

- [ ] **Create Simple Spec**
  ```markdown
  # SPEC_hello_api.md
  
  ## What It Does
  Simple API endpoint that returns "Hello World"
  
  ## Requirements
  - GET /hello endpoint
  - Returns JSON: {"message": "Hello World"}
  - Includes timestamp
  
  ## Tech Stack
  - FastAPI / Flask / Express (your choice)
  
  ## Success Criteria
  - [ ] Endpoint responds with 200
  - [ ] Returns correct JSON format
  - [ ] Works locally
  ```

- [ ] **Test Claude**
  - In your Claude project
  - Upload hello_api spec
  - Prompt: "Design architecture for this simple API"
  - Verify Claude responds with architecture

- [ ] **Test Gemini**
  - Open Gemini
  - Prompt: "Can you verify code against specifications?"
  - Verify Gemini responds affirmatively

---

## 🎯 YOU'RE READY WHEN

✅ Claude account active with project created  
✅ Gemini account accessible  
✅ Documentation downloaded and accessible  
✅ Project knowledge uploaded to Claude  
✅ Test spec created successfully  
✅ Claude responded to architecture request  
✅ Gemini ready for verification

**Time to complete:** 15 minutes  
**Next step:** Build your first real feature using the 5-phase process

---

## 📋 OPTIONAL: ADVANCED SETUP

### For Power Users (10 additional min)

- [ ] **Create Reusable Templates**
  ```bash
  # In your workspace
  mkdir templates
  cd templates
  
  # Create template files
  touch SPEC_template.md
  touch ARCHITECTURE_prompt.txt
  touch BUILDER_prompt.txt
  touch VERIFIER_prompt.txt
  ```

- [ ] **Set Up Git Workflow**
  ```bash
  # Create feature branch workflow template
  echo "git checkout -b feature/[name]" > git_workflow.sh
  echo "# Copy generated files" >> git_workflow.sh
  echo "# Test locally" >> git_workflow.sh
  echo "# Commit and deploy" >> git_workflow.sh
  ```

- [ ] **Document Your Tech Stack**
  ```markdown
  # TECH_STACK.md
  
  ## Preferred Stack
  - Backend: [FastAPI/Express/Django]
  - Frontend: [React/Next.js/Vue]
  - Database: [PostgreSQL/MongoDB]
  - Deployment: [Docker/Kubernetes/Vercel]
  
  ## Standards
  - Type safety: Required
  - Error handling: Try-catch blocks
  - Logging: Structured JSON
  - Authentication: JWT from Registry #1
  ```

- [ ] **Upload to Claude Project**
  - Upload TECH_STACK.md
  - Upload any code style guides
  - Upload deployment runbooks

---

## 🚀 FIRST REAL BUILD

### Ready for Your First Feature?

**Follow this:**

1. **Create specification** (use SPEC template)
2. **Open Claude project** → Upload spec
3. **Get architecture** (use ARCHITECTURE prompt)
4. **Generate code** (use BUILDER prompt)
5. **Verify with Gemini** (use VERIFIER prompt)
6. **Iterate if needed** (Claude fixes issues)
7. **Deploy locally** (test everything)
8. **Deploy to production** (ship it!)

**Reference:** AI_BUILDER_QUICK_REFERENCE.md for detailed steps

---

## 📊 TRACK YOUR FIRST BUILD

**Document this:**

```markdown
# MY FIRST AI-ACCELERATED BUILD

Feature: [name]
Date: [date]

TIMELINE:
- Specification: ___ min
- Architecture: ___ min  
- Code generation: ___ min
- Verification: ___ cycles, ___ min
- Deployment: ___ hours
- TOTAL: ___ hours

TRADITIONAL ESTIMATE: ___ hours
TIME SAVED: ___%

LESSONS LEARNED:
- [What went well]
- [What was challenging]
- [What to do differently next time]

RESULT: ✅ Success / ⚠️ Partial / ❌ Needs work
```

**Share this with team** to help others learn

---

## 💡 TIPS FOR SUCCESS

### Do This
✅ Read the full guide (DEVELOPER_ACCELERATION_KIT.md) before first build  
✅ Start with small feature to learn the process  
✅ Be specific in specifications  
✅ Trust the AI verifier  
✅ Ask questions in team chat  

### Avoid This
❌ Skipping specification phase  
❌ Not using AI verification  
❌ Deploying without testing  
❌ Ignoring critical issues  
❌ Working in isolation (share learnings!)  

---

## 🆘 TROUBLESHOOTING

**Problem:** Claude doesn't see my uploaded files  
**Solution:** Check you're in the PROJECT, not just a chat. Projects show on left sidebar.

**Problem:** Gemini verification seems shallow  
**Solution:** Be more specific in verification prompt. Include the spec + detailed checklist.

**Problem:** Generated code doesn't match my stack  
**Solution:** Upload TECH_STACK.md to Claude project. Specify exact versions in spec.

**Problem:** Too many verification failures  
**Solution:** Refine specification to be more detailed. Include examples and constraints.

**Problem:** Integration issues during deployment  
**Solution:** Most common: env variables, API URLs, CORS. Check .env.example from generated code.

---

## 📞 GET HELP

**Resources:**
1. DEVELOPER_ACCELERATION_KIT.md (full guide)
2. AI_BUILDER_QUICK_REFERENCE.md (quick ref)
3. Team chat (ask others who've done builds)
4. James (for blockers after trying above)

**Share Your Success:**
- When you complete first AI-accelerated build
- Share your metrics (time saved)
- Share lessons learned
- Help next developer onboard faster

---

## ✅ FINAL CHECKLIST

**Before starting your first feature:**

- [ ] All setup steps completed
- [ ] Test build successful
- [ ] Read full guide once
- [ ] Reviewed quick reference
- [ ] Understand the 5 phases
- [ ] Claude project active with knowledge
- [ ] Gemini accessible for verification
- [ ] Workspace folder created
- [ ] Ready to track metrics
- [ ] Know where to get help

**Ready to build 10x faster? Start with Phase 1: Specification!**

---

**WELCOME TO AI-ACCELERATED DEVELOPMENT**

*You just unlocked 10x productivity*  
*Features in hours, not days*  
*Paradise manifesting at light speed*

🎯⚡💎✅

---

**Next:** Create your first SPEC file and prompt Claude  
**Support:** DEVELOPER_ACCELERATION_KIT.md + team  
**Questions:** Ask early, iterate fast, ship often
