# 🚀 How to Use the Delegation Portal

**Portal URL:** http://198.54.123.234:8007
**Server:** root@198.54.123.234
**Purpose:** Delegate tasks to VAs automatically

---

## 🎯 What the Portal Does

**Complete Delegation Lifecycle:**
1. ✅ Detect blockers (missing credentials/tasks)
2. ✅ Create detailed VA tasks
3. ✅ Post to Upwork (manual for now, auto when API connected)
4. ✅ Monitor task completion
5. ✅ Store credentials securely
6. ✅ Auto-integrate when complete

---

## 📊 Portal Dashboard

**URL:** http://198.54.123.234:8007

**5 Tabs Available:**

**1. Overview**
- Current spending
- Active tasks
- Recent credential access
- Security alerts

**2. Credentials**
- View stored credentials (encrypted)
- Add new credentials
- Access log (who accessed what/when)

**3. Spending**
- 24-hour spending total
- Category breakdown
- Merchant tracking
- Alert thresholds

**4. Tasks**
- Pending tasks
- In-progress tasks
- Completed tasks
- VA assignments

**5. Security**
- Denied access attempts
- Suspicious activity
- Access patterns
- Recommendations

---

## 🔧 How to Delegate Our Testnet Task

### **Method 1: Use the Portal (Recommended)**

**Step 1: Access the Dashboard**
```bash
# Open browser to:
http://198.54.123.234:8007
```

**Step 2: SSH to Server**
```bash
ssh root@198.54.123.234
cd /root/delegation-system
```

**Step 3: Create the Task**
```python
# Run this on the server:
python3 << 'EOF'
from upwork_recruiter import TaskDelegator

delegator = TaskDelegator()

# Create testnet deployment task
task = delegator.delegate_task({
    'description': '''Deploy FPAI Token to Sepolia testnet:
    - Setup MetaMask wallet (testnet)
    - Get free Sepolia ETH
    - Deploy smart contract
    - Verify on Etherscan
    - Test all functions
    - Document results

    Complete instructions provided.
    Entry-level welcome!''',

    'deliverables': [
        'Contract address on Sepolia',
        'Etherscan verification link',
        'Test transaction screenshots',
        'All credentials in secure vault',
        'Completion report with time tracking'
    ],

    'deadline': '24 hours',
    'credentials': [],  # No credentials needed for testnet
    'budget': 15  # $15 fixed price test
})

print(f"✅ Task created: {task['id']}")
print(f"Status: {task['status']}")
print(f"Budget: ${task['budget']}")
EOF
```

**Step 4: View Task Details**
```bash
# Check task was created
cat upwork-api/task_log.json | python3 -m json.tool
```

**Step 5: Get Job Posting**
```bash
# The task details are saved, now you need to post to Upwork manually
cat upwork-api/jobs_log.json | python3 -m json.tool
```

---

### **Method 2: Run Full Orchestrator**

**This detects blockers and creates tasks automatically:**

```bash
ssh root@198.54.123.234
cd /root/delegation-system

# Run the orchestrator
python3 delegation_orchestrator.py
```

**What it does:**
1. Scans for missing credentials
2. Creates tasks for each blocker
3. Generates Upwork job postings
4. Monitors for completion
5. Auto-integrates credentials

---

## 📝 How to Post to Upwork (Manual)

**Until Upwork API is connected, post manually:**

**Step 1: Get the Job Posting**
```bash
# Use the one we created:
cat /Users/jamessunheart/Development/agents/services/treasury-manager/UPWORK_JOB_POSTING.md
```

**Step 2: Post on Upwork**
- Go to: https://www.upwork.com/nx/wm/client/postjob
- Job type: **Fixed price**
- Budget: **$15** (or $10-20 range)
- Duration: **Less than 1 week**
- Experience: **Entry level**
- Category: **Web, Mobile & Software Dev** > **Blockchain**
- Title: **TEST TASK: Deploy Crypto Token to Testnet ($15 Fixed)**
- Description: **Paste from UPWORK_JOB_POSTING.md**
- Screening questions:
  - Command line experience? (None/Basic/Comfortable)
  - Crypto experience? (None/Wallet/Technical)
  - Can start in 2-4 hours? (Yes/No)

**Step 3: Monitor Applications**
- Look for "TESTNET READY" in cover letters
- Check if they answered all 3 questions
- Use AI scoring system we created

---

## 🤖 How to Use AI Screening

**When applications come in:**

```bash
# Create a file with applications
cd /Users/jamessunheart/Development/agents/services/treasury-manager

cat > applications.json << 'EOF'
[
  {
    "name": "John D.",
    "cover_letter": "...",
    "screening_answers": ["Basic", "Wallet user", "Yes"]
  },
  {
    "name": "Jane S.",
    "cover_letter": "...",
    "screening_answers": ["None", "None", "Tomorrow"]
  }
]
EOF

# Run screening
python3 << 'EOF'
import json
from scripts.post-va-test-task import ai_score_application

with open('applications.json') as f:
    apps = json.load(f)

for app in apps:
    result = ai_score_application(
        app['cover_letter'],
        app.get('screening_answers', [])
    )

    print(f"\n{app['name']}")
    print(f"  Score: {result['score']}/10")
    print(f"  Recommendation: {result['recommendation']}")
    for feedback in result['feedback']:
        print(f"  {feedback}")
EOF
```

---

## 💾 How to Store VA Credentials

**When VA completes the task:**

```bash
ssh root@198.54.123.234
cd /root/delegation-system

# Add their credentials to vault
python3 << 'EOF'
from credential_vault import CredentialVault

vault = CredentialVault()

# Store testnet wallet credentials
vault.add_credential(
    tier="3",  # Tier 3 = Delegated (VA completed)
    service="fpai_testnet_deployment",
    credential_data={
        "contract_address": "0xABCD...EFGH",
        "wallet_address": "0x1234...5678",
        "etherscan_link": "https://sepolia.etherscan.io/address/0x...",
        "infura_rpc": "https://sepolia.infura.io/v3/...",
        "deployment_tx": "0x...",
        "completed_by": "va_john",
        "completed_at": "2025-11-15"
    },
    requester="admin"
)

print("✅ Testnet deployment credentials stored!")
EOF

# View stored credentials
python3 -c "
from credential_vault import CredentialVault
vault = CredentialVault()
print(vault.list_credentials('3'))
"
```

---

## 📊 How to Monitor Progress

### **Dashboard (Visual)**
```bash
# Open browser:
http://198.54.123.234:8007

# Check:
- Tasks tab: See task status
- Credentials tab: See when VA submits creds
- Spending tab: Track payments
```

### **Command Line (Fast)**
```bash
ssh root@198.54.123.234
cd /root/delegation-system

# Check tasks
cat upwork-api/task_log.json | python3 -m json.tool

# Check recent credential access
tail -20 credentials/access_log.json

# Check spending
cat monitoring/spending_log.json | python3 -m json.tool

# Check orchestrator log
cat orchestrator_log.json | python3 -m json.tool
```

---

## 🔄 Complete Workflow Example

### **Delegate Testnet Deployment End-to-End**

**1. Create Task on Server:**
```bash
ssh root@198.54.123.234
cd /root/delegation-system

python3 << 'EOF'
from upwork_recruiter import TaskDelegator

task = TaskDelegator().delegate_task({
    'description': 'Deploy FPAI Token to Sepolia testnet',
    'deliverables': ['Contract address', 'Verification link', 'Test results'],
    'deadline': '24 hours',
    'budget': 15
})

import json
print(json.dumps(task, indent=2))
EOF
```

**2. Post to Upwork:**
- Copy job posting from UPWORK_JOB_POSTING.md
- Post manually on Upwork
- Budget: $15 fixed

**3. Screen Applications:**
- Use AI scoring system
- Look for "TESTNET READY"
- Hire top 2-3 candidates

**4. Send Instructions:**
- Send TESTNET_DEPLOYMENT_GUIDE.md
- Provide access to deployment scripts
- Give them 24 hours

**5. Monitor Completion:**
```bash
# Check dashboard
http://198.54.123.234:8007

# Or check logs
ssh root@198.54.123.234
tail -f /root/delegation-system/upwork-api/task_log.json
```

**6. Receive & Store Credentials:**
```bash
# When VA completes, they send you:
# - Contract address
# - Etherscan link
# - Test results

# Store in vault:
python3 << 'EOF'
from credential_vault import CredentialVault
vault = CredentialVault()
vault.add_credential(
    tier="3",
    service="fpai_testnet",
    credential_data={"contract": "0x...", ...},
    requester="admin"
)
EOF
```

**7. Release Payment:**
- Verify deployment on Etherscan
- Check test results
- Release $15 on Upwork

**8. Scale Winners:**
- VA did great? Give them more tasks
- VA was OK? Test again
- VA failed? Try someone else

---

## 💡 Pro Tips

### **Use the Portal For:**
- ✅ Viewing real-time status
- ✅ Monitoring spending
- ✅ Checking credential access
- ✅ Seeing security alerts

### **Use SSH For:**
- ✅ Creating new tasks
- ✅ Adding credentials
- ✅ Checking detailed logs
- ✅ Running orchestrator

### **Use Local Scripts For:**
- ✅ AI screening applicants
- ✅ Generating job postings
- ✅ Creating task templates

---

## 🚀 Quick Commands Cheatsheet

```bash
# Access portal
open http://198.54.123.234:8007

# SSH to server
ssh root@198.54.123.234
cd /root/delegation-system

# Create task
python3 -c "from upwork_recruiter import TaskDelegator; ..."

# View tasks
cat upwork-api/task_log.json | python3 -m json.tool

# Add credential
python3 -c "from credential_vault import CredentialVault; ..."

# Check spending
cat monitoring/spending_log.json | python3 -m json.tool

# Run orchestrator
python3 delegation_orchestrator.py

# Restart dashboard
pkill -f streamlit
nohup python3 -m streamlit run monitoring_dashboard.py --server.port 8007 --server.address 0.0.0.0 &
```

---

## ✅ Summary

**The Delegation Portal lets you:**

1. **Create VA tasks** (testnet deployment, API setups, etc.)
2. **Monitor progress** (real-time dashboard)
3. **Store credentials securely** (encrypted vault)
4. **Track spending** (every transaction logged)
5. **Screen applicants** (AI scoring system)
6. **Scale winners** (test → ongoing work pipeline)

**For our testnet deployment:**
- Create task via portal
- Post to Upwork ($15)
- Hire 2-3 VAs
- Monitor via dashboard
- Store results in vault
- Scale best performers

**Zero your time after setup!** 🎯

---

**Portal:** http://198.54.123.234:8007
**Server:** ssh root@198.54.123.234
**Local Tools:** /Users/jamessunheart/Development/agents/services/treasury-manager/scripts/

**Let's delegate!** 🚀
