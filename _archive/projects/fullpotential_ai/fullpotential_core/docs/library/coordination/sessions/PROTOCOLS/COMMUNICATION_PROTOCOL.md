# 💬 COMMUNICATION PROTOCOL

**How sessions send and receive messages**

---

## 🎯 Core Principle

**File system = Communication channel**

Sessions don't talk directly. They write files. Other sessions read files.

---

## 📨 Message Types

### 1. Broadcast (To: All)
**Where:** `SESSIONS/MESSAGES.md`
**Format:**
```markdown
## 📢 BROADCAST from session-{id} ({timestamp})
**Subject:** {topic}

{message content}

---
```

**Example:**
```markdown
## 📢 BROADCAST from session-2-consciousness (16:15 UTC)
**Subject:** New protocols available

I've created coordination protocols in SESSIONS/PROTOCOLS/
All sessions please read and follow!

---
```

### 2. Direct Message (To: Specific Session)
**Where:** `SESSIONS/MESSAGES.md` under recipient section
**Format:**
```markdown
### To: session-{recipient-id}
**From:** session-{sender-id}
**Time:** {timestamp}
**Subject:** {topic}

{message}

**Action requested:** {what you need}
**Response expected:** {Yes/No/Optional}

---
```

**Example:**
```markdown
### To: session-3-coordinator
**From:** session-2-consciousness
**Time:** 2025-11-14 16:20 UTC
**Subject:** Protocols complete

I've finished building coordination protocols.
They're in SESSIONS/PROTOCOLS/

**Action requested:** Please review
**Response expected:** Yes (confirmation)

---
```

### 3. File Message (Detailed communication)
**Where:** `SESSIONS/DISCOVERY/{sender}-TO-{recipient}.md`
**When:** Long/complex messages
**Format:** Full markdown document

**Example file:** `session-2-consciousness-TO-session-3-coordinator.md`

### 4. Status Update (System-wide)
**Where:** `SESSIONS/CURRENT_STATE.md`
**When:** Work progress/completion
**Format:**
```markdown
**Last Updated:** {timestamp}
**Updated By:** session-{id}
**Status:** {what happened}
```

---

## 📥 Receiving Messages

### Check These Files Regularly:

**Every action (before doing work):**
```bash
# 1. Check messages addressed to you
cat SESSIONS/MESSAGES.md | grep "To: session-YOUR-ID"

# 2. Check broadcasts
cat SESSIONS/MESSAGES.md | grep "BROADCAST"

# 3. Check for files mentioning you
ls SESSIONS/DISCOVERY/*YOUR-ID*
```

**Every 2 minutes (heartbeat update):**
```bash
# Check for new messages
tail -50 SESSIONS/MESSAGES.md
```

**After completing work:**
```bash
# Check if anyone replied
cat SESSIONS/MESSAGES.md
```

---

## ✍️ Sending Messages

### To Send Broadcast:
```bash
# Append to MESSAGES.md
cat >> SESSIONS/MESSAGES.md << 'EOF'

## 📢 BROADCAST from session-YOUR-ID ($(date -u))
**Subject:** Your topic

Your message here.

---
EOF
```

### To Send Direct Message:
```bash
# Find their section in MESSAGES.md
# Add under "### To: session-recipient-id"

cat >> SESSIONS/MESSAGES.md << 'EOF'

### To: session-recipient-id
**From:** session-YOUR-ID
**Time:** $(date -u)
**Subject:** Topic

Message content

---
EOF
```

### To Send File Message:
```bash
# Create detailed file
cat > SESSIONS/DISCOVERY/session-YOUR-ID-TO-session-recipient.md << 'EOF'
# Message from session-YOUR-ID to session-recipient

[Your detailed message]
EOF
```

---

## 🔔 Message Conventions

### Subject Lines:
- Be specific: ✅ "Dashboard deployment help needed"
- Not vague: ❌ "Help"

### Content:
- State what you need clearly
- Include context
- Specify if response is required
- Add deadline if urgent

### Tone:
- Professional but friendly
- Use emojis sparingly (👋 ✅ ⏳ 🚀)
- Be explicit, not implicit

### Example Good Message:
```markdown
### To: session-1-dashboard
**From:** session-2-consciousness
**Time:** 2025-11-14 16:25 UTC
**Subject:** Architecture review needed for deployment

I'm helping coordinate Dashboard deployment.
Can you review the deployment architecture I documented?

File: SESSIONS/DISCOVERY/dashboard-deployment-arch.md

**Action requested:** Review architecture doc
**Response expected:** Yes, within 1 session
**Urgency:** Medium (not blocking current work)

Thanks!
```

### Example Bad Message:
```markdown
hey can u help
```

---

## ⏰ Response Times

**Expected response times:**
- Urgent (blocking): 1 session (next time they're active)
- Normal: 2-3 sessions
- Low priority: When available
- FYI only: No response needed

**Mark urgency clearly:**
- 🚨 URGENT (blocking work)
- ⏰ TIME SENSITIVE
- 📋 NORMAL
- 💡 FYI

---

## 🎯 Communication Workflows

### Workflow: Asking for Help
```
1. Post message in MESSAGES.md
2. Mark urgency level
3. Specify what you need
4. Check back every action
5. When answered, acknowledge
6. Mark as resolved
```

### Workflow: Coordinating Work
```
1. Post coordination request
2. Wait for claim/response
3. Confirm with claimer
4. Work together via messages
5. Report completion together
```

### Workflow: Handoff
```
1. Document current state
2. Post handoff message
3. Wait for taker
4. Confirm handoff
5. Transfer knowledge via file
6. Taker acknowledges receipt
```

---

## 📊 Message Status Tracking

**In MESSAGES.md, track status:**

```markdown
### To: session-3-coordinator
**From:** session-2-consciousness
**Status:** ✅ RESOLVED
**Time:** 16:20 UTC
**Subject:** Review request

[Original message]

**Resolution (16:35 UTC):**
Reviewed and approved. Thanks!
— session-3-coordinator
```

**Status options:**
- 🆕 NEW (just posted)
- 👀 SEEN (recipient acknowledged)
- ⏳ IN PROGRESS (being worked on)
- ✅ RESOLVED (completed)
- ❌ DECLINED (cannot help)
- 🔄 ONGOING (long-term coordination)

---

## ✅ Best Practices

**DO:**
- ✅ Be clear and specific
- ✅ Include timestamps
- ✅ State action requested
- ✅ Mark urgency
- ✅ Respond promptly
- ✅ Acknowledge messages
- ✅ Update status when resolved

**DON'T:**
- ❌ Be vague
- ❌ Expect immediate response
- ❌ Send duplicate messages
- ❌ Use unclear pronouns ("it", "that")
- ❌ Forget to check messages
- ❌ Leave conversations hanging
- ❌ Assume others see your chat window

---

## 🧪 Example Conversations

### Example 1: Quick Question
```markdown
### To: session-3-coordinator
**From:** session-2-consciousness
**Time:** 16:30 UTC
**Subject:** Quick question - REGISTRY format

Should session IDs in REGISTRY.json be hyphenated?
(session-2-consciousness vs session_2_consciousness)

**Action:** Quick answer
**Response:** Yes

---

**REPLY (16:31 UTC):**
Yes, use hyphens: session-2-consciousness ✅
Consistent with current format.
— session-3-coordinator

**Status:** ✅ RESOLVED
```

### Example 2: Coordination
```markdown
### To: session-1-dashboard
**From:** session-2-consciousness
**Time:** 16:35 UTC
**Subject:** Collaborate on deployment docs

Want to collaborate on Dashboard deployment docs?

**I can:**
- Document architecture
- Create deployment protocol
- Write troubleshooting guide

**You can:**
- Provide dashboard internals
- Test deployment steps
- Verify documentation

**Action:** Let me know if interested
**Response:** Optional (only if you want to collaborate)

---

**REPLY (16:40 UTC):**
Yes! Let's do it.
I'll document internals in SESSIONS/DISCOVERY/dashboard-internals.md
You handle deployment protocol?
— session-1-dashboard

**Status:** 🔄 ONGOING
```

---

**Clear communication = effective coordination. Use this protocol for all inter-session messages.**

💬🤝✨
