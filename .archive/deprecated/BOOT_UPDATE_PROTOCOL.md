# BOOT.md Update Protocol

**Purpose:** Ensure multiple Claude sessions can safely enhance BOOT.md without losing critical information

**Version:** 1.0.0
**Last Updated:** 2025-11-16

---

## 🎯 Core Principle

**ENHANCE, NEVER REPLACE**

BOOT.md is a living document that grows with the system. Sessions should **add to** and **organize** existing content, not overwrite it.

---

## ✅ ALLOWED Updates

### 1. **Adding New Sections**
- New services in the TIER architecture
- New SPEC tools or capabilities
- New quick reference commands
- New troubleshooting entries

### 2. **Enhancing Existing Sections**
- Adding examples to existing workflows
- Clarifying ambiguous instructions
- Adding helpful tips or notes
- Expanding troubleshooting guides

### 3. **Reorganizing for Clarity**
- Grouping related content
- Improving section hierarchy
- Adding sub-sections
- Creating better navigation

### 4. **Updating Status Information**
- Port numbers when services move
- Service status (active/inactive)
- Version numbers
- Endpoint URLs

---

## ❌ FORBIDDEN Updates

### NEVER Remove or Replace:

1. **Core UDC Endpoint Definitions** (lines ~40-90)
   - The 5 required endpoints
   - JSON examples
   - These are the contract specification

2. **SPEC Creation Protocol** (lines ~100-220)
   - The builder → verifier → optimizer → build flow
   - Phase 1-5 structure
   - This is the core workflow

3. **Critical Rules Section** (lines ~370-395)
   - ALWAYS/NEVER lists
   - These are safety guardrails

4. **Existing Service Listings**
   - TIER 0/1/2 architecture
   - Port assignments
   - Only ADD new services, don't remove old ones

---

## 🔄 Safe Update Workflow

### Step 1: Read and Understand Current State

```bash
# Always read the full file first
cat /Users/jamessunheart/Development/BOOT.md

# Check version and last updated date (line 3-4)
head -10 /Users/jamessunheart/Development/BOOT.md
```

### Step 2: Create Timestamped Backup

```bash
# ALWAYS backup before editing
cp /Users/jamessunheart/Development/BOOT.md \
   /Users/jamessunheart/Development/BOOT.md.backup.$(date +%Y%m%d_%H%M%S)
```

### Step 3: Make Your Updates

**Use the Edit tool, NOT Write:**
- ✅ `Edit` tool preserves surrounding content
- ❌ `Write` tool replaces entire file (dangerous!)

**Be Surgical:**
```python
# Good - Specific edit
Edit(
  file_path="/Users/jamessunheart/Development/BOOT.md",
  old_string="existing specific text...",
  new_string="enhanced version of that text..."
)

# Bad - Wholesale replacement
Write(
  file_path="/Users/jamessunheart/Development/BOOT.md",
  content="entire new file content..."  # NEVER DO THIS
)
```

### Step 4: Update Version and Timestamp

**Always increment version and update timestamp:**

```python
Edit(
  file_path="/Users/jamessunheart/Development/BOOT.md",
  old_string="**Last Updated:** 2025-11-16\n**Version:** 2.0.0",
  new_string="**Last Updated:** 2025-11-16\n**Version:** 2.0.1"
)
```

**Version Semantics:**
- Major (X.0.0): Structural changes, workflow changes
- Minor (0.X.0): New sections, significant additions
- Patch (0.0.X): Small updates, clarifications, fixes

### Step 5: Document Your Changes

**Add a changelog entry at the bottom:**

```python
Edit(
  file_path="/Users/jamessunheart/Development/BOOT.md",
  old_string="**Version:** 2.0.0 (Added SPEC Tools Protocol)\n**Last Updated:** 2025-11-16\n**Next Review:** When new TIER 2+ services are added",
  new_string="**Version:** 2.0.1 (Added new service X to TIER 1)\n**Previous:** 2.0.0 (Added SPEC Tools Protocol)\n**Last Updated:** 2025-11-16\n**Next Review:** When new TIER 2+ services are added"
)
```

---

## 📝 Update Templates

### Template 1: Adding a New Service

```python
# Find the TIER section
Edit(
  file_path="/Users/jamessunheart/Development/BOOT.md",
  old_string="""### TIER 1: Sacred Loop
**Autonomous build and coordination**
- autonomous-executor (8402) - Autonomous droplet builds
- jobs (8008) - Recruitment automation""",
  new_string="""### TIER 1: Sacred Loop
**Autonomous build and coordination**
- autonomous-executor (8402) - Autonomous droplet builds
- jobs (8008) - Recruitment automation
- NEW-SERVICE-NAME (PORT) - Description"""
)
```

### Template 2: Adding a Troubleshooting Entry

```python
# Add to troubleshooting section
Edit(
  file_path="/Users/jamessunheart/Development/BOOT.md",
  old_string="---\n\n## 📞 GETTING HELP",
  new_string="""### New Issue Description

**Issue:** What went wrong

**Solution:** How to fix it
```bash
# Commands to fix
```

---

## 📞 GETTING HELP"""
)
```

### Template 3: Adding a Quick Reference Command

```python
# Add to Quick Reference section
Edit(
  file_path="/Users/jamessunheart/Development/BOOT.md",
  old_string="### Common Tasks\n\n**Create a new service:**",
  new_string="""### Common Tasks

**New task description:**
```bash
# Command to do it
```

**Create a new service:**"""
)
```

---

## 🔒 Protected Sections

**These sections contain critical system contracts - edit with extreme care:**

### 1. UDC Endpoint Definitions (~lines 40-90)
**Why Protected:** This is the Universal Droplet Contract specification
**When to Edit:** Only when UDC standard itself changes (very rare)
**How to Edit:** Add examples or clarifications, never change the core 5 endpoints

### 2. SPEC Creation Protocol (~lines 100-220)
**Why Protected:** This is the standardized workflow all sessions follow
**When to Edit:** Only when SPEC tools change significantly
**How to Edit:** Enhance steps with examples, never change the phase structure

### 3. Critical Rules (~lines 370-395)
**Why Protected:** Safety guardrails preventing bad practices
**When to Edit:** Only when adding new ALWAYS/NEVER rules
**How to Edit:** Add to lists, never remove existing rules

---

## 🔍 Pre-Update Checklist

Before editing BOOT.md, verify:

- [ ] I have read the current version completely
- [ ] I have created a timestamped backup
- [ ] My update ADDS value (not just rewording)
- [ ] My update doesn't contradict existing content
- [ ] I'm using Edit tool (not Write tool)
- [ ] I'm updating version number
- [ ] I'm updating timestamp
- [ ] I'm documenting my change

---

## 🚨 Conflict Resolution

**If you find contradictory information in BOOT.md:**

1. **Don't delete immediately** - Flag it
2. **Check Registry** - What's the actual system state?
```bash
curl http://localhost:8000/droplets | python3 -m json.tool
```
3. **Verify services** - Are they actually running?
```bash
curl http://localhost:PORT/health
```
4. **Update to match reality** - System state is source of truth
5. **Document the fix** - Note what was wrong and what's correct now

---

## 📊 Review Triggers

**BOOT.md should be reviewed when:**

1. **New TIER 0 service added** - Update infrastructure spine section
2. **New TIER 1 service added** - Update sacred loop section
3. **First TIER 2+ service added** - Create new TIER 2 section
4. **SPEC tools change** - Update SPEC creation protocol
5. **UDC standard updates** - Update endpoint definitions (rare)
6. **Major system changes** - Review entire document

---

## 🎯 Best Practices

### DO ✅

- **Read before writing** - Understand current state
- **Backup before editing** - Safety first
- **Be specific** - Surgical edits, not broad strokes
- **Add examples** - Make abstract concepts concrete
- **Cross-reference** - Link to other docs
- **Update metadata** - Version, timestamp, changelog

### DON'T ❌

- **Use Write tool** - It replaces entire file
- **Remove working content** - Only deprecate with notes
- **Contradict existing rules** - Resolve conflicts first
- **Skip backups** - Always create before editing
- **Forget version bump** - Track changes
- **Make assumptions** - Verify system state first

---

## 📋 Update Log Template

**Keep a running log of changes at the bottom of BOOT.md:**

```markdown
## Change Log

### 2.0.1 (2025-11-16)
- Added payment-processor to TIER 2
- Updated troubleshooting for SSL issues
- Added example for batch spec verification

### 2.0.0 (2025-11-16)
- Added SPEC Tools Protocol (builder/optimizer/verifier)
- Restructured SPEC Creation workflow
- Added TIER architecture section
```

---

## 🛡️ Validation

**After any update, validate BOOT.md:**

```bash
# Check file is valid markdown
cat /Users/jamessunheart/Development/BOOT.md

# Verify no syntax errors
python3 -c "import markdown; markdown.markdown(open('/Users/jamessunheart/Development/BOOT.md').read())"

# Check links are valid (optional)
grep -o 'http[s]*://[^)]*' /Users/jamessunheart/Development/BOOT.md
```

---

## 🤝 Multi-Session Coordination

**Before making significant updates:**

1. **Check for active work:**
```bash
# See if other sessions are editing BOOT.md
ls -la /Users/jamessunheart/Development/BOOT.md.backup.*
# Recent backups = active editing
```

2. **Claim the work** (if using coordination system):
```bash
# Create claim file
touch /Users/jamessunheart/Development/COORDINATION/claims/BOOT.md.claim
echo "$(date): Session updating BOOT.md" >> /Users/jamessunheart/Development/COORDINATION/claims/BOOT.md.claim
```

3. **Release when done:**
```bash
rm /Users/jamessunheart/Development/COORDINATION/claims/BOOT.md.claim
```

---

## 🎓 Examples

### Example 1: Good Update (Adding Service)

```python
# Session discovers new service running
# 1. Verify it exists
result = await bash("curl http://localhost:8350/health")

# 2. Create backup
await bash("cp /Users/jamessunheart/Development/BOOT.md /Users/jamessunheart/Development/BOOT.md.backup.$(date +%Y%m%d_%H%M%S)")

# 3. Add to appropriate TIER
Edit(
  file_path="/Users/jamessunheart/Development/BOOT.md",
  old_string="### TIER 2+: Domain Services\n**Business logic and specialized services**\n- payment-processor, user-management, etc. (to be built)",
  new_string="### TIER 2+: Domain Services\n**Business logic and specialized services**\n- analytics-engine (8350) - Real-time analytics processing\n- payment-processor, user-management, etc. (to be built)"
)

# 4. Update version
Edit(
  file_path="/Users/jamessunheart/Development/BOOT.md",
  old_string="**Version:** 2.0.0",
  new_string="**Version:** 2.0.1"
)
```

### Example 2: Bad Update (Don't Do This)

```python
# ❌ WRONG - Rewriting entire file
content = """# BOOT - Claude Session Guide
... entire new content ...
"""
Write(
  file_path="/Users/jamessunheart/Development/BOOT.md",
  content=content  # This DELETES everything not in 'content'
)
# This loses all existing content!
```

---

## 🎯 Summary

**Golden Rule:** BOOT.md is append-only with careful edits

**Safe Pattern:**
1. Read current state
2. Backup
3. Surgical edit with Edit tool
4. Update metadata
5. Validate

**Unsafe Pattern:**
1. Assume you know what's there
2. Use Write tool
3. Replace entire file
4. Lose critical content
5. Break the system

---

**Follow this protocol and BOOT.md will grow safely across all sessions.** 🚀

---

**Version:** 1.0.0
**Applies to:** BOOT.md v2.0.0+
**Review:** When BOOT.md structure significantly changes
