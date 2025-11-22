#!/bin/bash
# setup-email-dns.sh - Configure MX and related DNS records for email

set -e

DOMAIN="fullpotential.com"
MAIL_SERVER="198.54.123.234"

# Namecheap API credentials
API_USER="globalskypower"
API_KEY="1970bffd68144b08a4bea27acbac0854"
USERNAME="globalskypower"
CLIENT_IP=$(curl -s https://api.ipify.org)

echo "🔧 Setting up email DNS records for $DOMAIN"
echo ""

# Get current DNS records
echo "📋 Fetching current DNS records..."
RESPONSE=$(curl -s "https://api.namecheap.com/xml.response?ApiUser=${API_USER}&ApiKey=${API_KEY}&UserName=${USERNAME}&Command=namecheap.domains.dns.getHosts&ClientIp=${CLIENT_IP}&SLD=fullpotential&TLD=com")

# Check if we're using Namecheap DNS
if echo "$RESPONSE" | grep -q "ApiError"; then
    echo "❌ Error fetching DNS records"
    echo "$RESPONSE" | grep -oP '(?<=<Error>).*?(?=</Error>)'
    exit 1
fi

echo "✅ Current DNS records fetched"
echo ""

# Prepare DNS records
echo "🔨 Configuring email DNS records..."

# We need to set:
# 1. MX record pointing to mail.fullpotential.com with priority 10
# 2. A record for mail.fullpotential.com pointing to server IP
# 3. TXT record for SPF
# 4. Keep existing A record for @ (main domain)

# Get existing A record for main domain
EXISTING_A=$(echo "$RESPONSE" | grep -oP '(?<=<Address>).*?(?=</Address>)' | head -1)

if [ -z "$EXISTING_A" ]; then
    EXISTING_A="198.54.123.234"
fi

echo "   Main domain (@) A record: $EXISTING_A"
echo "   Mail server (mail) A record: $MAIL_SERVER"
echo "   MX record: mail.fullpotential.com (priority 10)"
echo "   SPF record: v=spf1 mx ~all"
echo ""

# Set DNS records via Namecheap API
# Note: Namecheap requires ALL records to be sent at once
read -p "⚠️  This will update DNS records. Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Cancelled"
    exit 0
fi

echo ""
echo "📤 Updating DNS records..."

# Build the API call with all necessary records
API_URL="https://api.namecheap.com/xml.response"
API_URL+="?ApiUser=${API_USER}"
API_URL+="&ApiKey=${API_KEY}"
API_URL+="&UserName=${USERNAME}"
API_URL+="&Command=namecheap.domains.dns.setHosts"
API_URL+="&ClientIp=${CLIENT_IP}"
API_URL+="&SLD=fullpotential"
API_URL+="&TLD=com"

# Add A record for main domain (@)
API_URL+="&HostName1=@"
API_URL+="&RecordType1=A"
API_URL+="&Address1=${EXISTING_A}"
API_URL+="&TTL1=1800"

# Add A record for mail subdomain
API_URL+="&HostName2=mail"
API_URL+="&RecordType2=A"
API_URL+="&Address2=${MAIL_SERVER}"
API_URL+="&TTL2=1800"

# Add MX record
API_URL+="&HostName3=@"
API_URL+="&RecordType3=MX"
API_URL+="&Address3=mail.fullpotential.com."
API_URL+="&MXPref3=10"
API_URL+="&TTL3=1800"

# Add SPF record
API_URL+="&HostName4=@"
API_URL+="&RecordType4=TXT"
API_URL+="&Address4=v=spf1+mx+~all"
API_URL+="&TTL4=1800"

# Add www CNAME (common practice)
API_URL+="&HostName5=www"
API_URL+="&RecordType5=CNAME"
API_URL+="&Address5=fullpotential.com."
API_URL+="&TTL5=1800"

# Make the API call
UPDATE_RESPONSE=$(curl -s "$API_URL")

# Check for errors
if echo "$UPDATE_RESPONSE" | grep -q "ApiError"; then
    echo "❌ Error updating DNS records"
    echo "$UPDATE_RESPONSE" | grep -oP '(?<=<Error>).*?(?=</Error>)'
    exit 1
fi

if echo "$UPDATE_RESPONSE" | grep -q "<IsSuccess>true</IsSuccess>"; then
    echo "✅ DNS records updated successfully!"
    echo ""
    echo "📋 Records configured:"
    echo "   @ A      $EXISTING_A"
    echo "   mail A   $MAIL_SERVER"
    echo "   @ MX     mail.fullpotential.com (priority 10)"
    echo "   @ TXT    v=spf1 mx ~all"
    echo "   www CNAME fullpotential.com"
    echo ""
    echo "⏰ DNS propagation may take 5-30 minutes"
    echo ""
    echo "🧪 Test email after propagation:"
    echo "   dig MX fullpotential.com +short"
    echo "   dig A mail.fullpotential.com +short"
    echo ""
else
    echo "❌ Failed to update DNS records"
    echo "$UPDATE_RESPONSE"
    exit 1
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ EMAIL DNS SETUP COMPLETE!"
echo ""
echo "Next steps:"
echo "1. Wait 5-30 minutes for DNS propagation"
echo "2. Verify with: dig MX fullpotential.com +short"
echo "3. Send test email to: james@fullpotential.com"
echo "4. Check mailbox with: ssh root@198.54.123.234 'mail -u james'"
echo ""
