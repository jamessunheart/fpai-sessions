# 🚀 Delegation System - Quick Start

**Dashboard:** http://198.54.123.234:8007

---

## Common Tasks

### Add a Credential

```bash
ssh root@198.54.123.234
cd /root/delegation-system
python3 << 'EOF'
from credential_vault import CredentialVault

vault = CredentialVault()
vault.add_credential(
    tier="2",  # or "1" for critical, "3" for delegated
    service="service_name",
    credential_data={
        "key": "value",
        # Add any relevant fields
    },
    requester="admin"
)
print("✅ Credential added!")
EOF
```

### Retrieve a Credential

```python
cred = vault.get_credential(
    tier="2",
    service="operations_card",
    requester="va_name",
    purpose="setup_stripe_account"
)
# All access is logged!
```

### Log Spending

```python
from credential_vault import SpendingMonitor

spending = SpendingMonitor()
spending.log_transaction(
    amount=49.99,
    merchant="Stripe",
    category="tools",
    requester="va_john",
    description="Account setup"
)
```

### Delegate a Task

```python
from upwork_recruiter import TaskDelegator

delegator = TaskDelegator()
result = delegator.delegate_task({
    'description': 'Setup Stripe account + get API keys',
    'deliverables': ['Account ID', 'API Keys'],
    'deadline': '24 hours',
    'credentials': ['operations_card', 'operations_email'],
    'budget': 50
})
```

### Check System Status

```bash
ssh root@198.54.123.234
cd /root/delegation-system

# Credential vault status
python3 -c "
from credential_vault import CredentialVault
vault = CredentialVault()
print('Tier 2 credentials:', vault.list_credentials('2'))
print('Access log entries:', len(vault.get_access_log(hours=24)))
"

# Spending status
python3 -c "
from credential_vault import SpendingMonitor
spending = SpendingMonitor()
print('24h spending: $', spending.get_spending_24h())
"

# View logs
cat credentials/access_log.json | python3 -m json.tool
cat monitoring/spending_log.json | python3 -m json.tool
cat upwork-api/task_log.json | python3 -m json.tool
```

### Restart Dashboard

```bash
pkill -f streamlit
cd /root/delegation-system
nohup python3 -m streamlit run monitoring_dashboard.py --server.port 8007 --server.address 0.0.0.0 > /tmp/delegation-monitor.log 2>&1 &
```

---

## URLs

- **Dashboard:** http://198.54.123.234:8007
- **Privacy.com:** https://privacy.com
- **Upwork API:** https://www.upwork.com/ab/account-security/api

---

## Files

| Path | Purpose |
|------|---------|
| `/root/delegation-system/credential_vault.py` | Encryption & access control |
| `/root/delegation-system/upwork_recruiter.py` | Automated VA hiring |
| `/root/delegation-system/monitoring_dashboard.py` | Real-time monitoring |
| `/root/delegation-system/credentials/` | Encrypted vault |
| `/root/delegation-system/monitoring/` | Spending logs |
| `/root/delegation-system/upwork-api/` | Task & job logs |

---

## Next Steps

1. **Add Privacy.com card** → Tier 2 credentials
2. **Setup Upwork OAuth** → Enable auto-recruitment
3. **Delegate first task** → Test full flow
4. **Monitor dashboard** → Track everything

🚀 Ready to 10x your execution speed!
