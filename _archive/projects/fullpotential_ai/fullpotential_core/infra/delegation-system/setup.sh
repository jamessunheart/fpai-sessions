#!/bin/bash

# Delegation System Setup Script
# Initializes 3-tier security infrastructure on server

set -e

echo "🚀 Setting up Delegation System..."
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "⚠️  Please run as root (or use sudo)"
  exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip3 install --upgrade cryptography python-dotenv requests streamlit pandas

# Create directory structure
echo "📁 Creating directory structure..."
mkdir -p /root/delegation-system/{credentials,monitoring,upwork-api,scripts}

# Copy files
echo "📋 Copying files..."
cp credential_vault.py /root/delegation-system/
cp upwork_recruiter.py /root/delegation-system/
cp monitoring_dashboard.py /root/delegation-system/

# Set permissions
echo "🔒 Setting secure permissions..."
chmod 700 /root/delegation-system
chmod 600 /root/delegation-system/credential_vault.py
chmod 600 /root/delegation-system/credentials/.vault_key 2>/dev/null || true

# Initialize credential vault
echo "🔐 Initializing credential vault..."
cd /root/delegation-system
python3 << 'EOF'
from credential_vault import CredentialVault, SpendingMonitor

# Initialize vault
vault = CredentialVault()
print("✅ Credential vault initialized")

# Initialize spending monitor
spending = SpendingMonitor()
print("✅ Spending monitor initialized")

print("\n📊 System Status:")
print(f"- Vault path: /root/delegation-system/credentials")
print(f"- Access log: /root/delegation-system/credentials/access_log.json")
print(f"- Spending log: /root/delegation-system/monitoring/spending_log.json")
EOF

# Create systemd service for monitoring dashboard
echo "🖥️  Creating monitoring dashboard service..."
cat > /etc/systemd/system/delegation-monitor.service << 'EOF'
[Unit]
Description=Delegation System Monitoring Dashboard
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/delegation-system
ExecStart=/usr/bin/python3 -m streamlit run monitoring_dashboard.py --server.port 8007 --server.address 0.0.0.0
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload

# Start monitoring dashboard
echo "▶️  Starting monitoring dashboard..."
systemctl start delegation-monitor
systemctl enable delegation-monitor

echo ""
echo "✅ Delegation System Setup Complete!"
echo ""
echo "📊 Monitoring Dashboard: http://198.54.123.234:8007"
echo "🔐 Credential Vault: /root/delegation-system/credentials"
echo "📋 Task Log: /root/delegation-system/upwork-api/task_log.json"
echo ""
echo "Next steps:"
echo "1. Add operations card credentials (Tier 2)"
echo "2. Add Upwork API credentials (Tier 2)"
echo "3. Access monitoring dashboard to verify"
echo ""
echo "🔒 Security Status: All systems operational"
