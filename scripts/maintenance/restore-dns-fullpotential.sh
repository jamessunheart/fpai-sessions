#!/bin/bash
# Restore DNS records for fullpotential.com
# This fixes the issue where namecheap-dns-automation.sh wiped all records

set -e

# Namecheap API credentials
API_USER="globalskypower"
API_KEY="1970bffd68144b08a4bea27acbac0854"
USERNAME="globalskypower"
CLIENT_IP=$(curl -s https://api.ipify.org)

SERVER_IP="198.54.123.234"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔧 RESTORING DNS RECORDS FOR fullpotential.com"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "This will restore:"
echo "  ✅ Main domain (@ A record → $SERVER_IP)"
echo "  ✅ WWW subdomain (www CNAME → fullpotential.com)"
echo "  ✅ Mail server (mail A record → $SERVER_IP)"
echo "  ✅ Email routing (@ MX → mail.fullpotential.com)"
echo "  ✅ SPF record for email authentication"
echo "  ✅ Wildcard for all subdomains (* A → $SERVER_IP)"
echo "  ✅ Dashboard subdomain (dashboard A → $SERVER_IP)"
echo ""
echo "Client IP: $CLIENT_IP"
echo ""

read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Cancelled"
    exit 0
fi

echo ""
echo "📤 Restoring DNS records via Namecheap API..."
echo ""

# Build API call with ALL records
# CRITICAL: Namecheap's setHosts replaces ALL records, so we must include everything

API_URL="https://api.namecheap.com/xml.response"
API_URL+="?ApiUser=${API_USER}"
API_URL+="&ApiKey=${API_KEY}"
API_URL+="&UserName=${USERNAME}"
API_URL+="&Command=namecheap.domains.dns.setHosts"
API_URL+="&ClientIp=${CLIENT_IP}"
API_URL+="&SLD=fullpotential"
API_URL+="&TLD=com"

# Record 1: Main domain @ A record
API_URL+="&HostName1=@"
API_URL+="&RecordType1=A"
API_URL+="&Address1=${SERVER_IP}"
API_URL+="&TTL1=300"

# Record 2: WWW CNAME
API_URL+="&HostName2=www"
API_URL+="&RecordType2=CNAME"
API_URL+="&Address2=fullpotential.com."
API_URL+="&TTL2=300"

# Record 3: Mail server A record
API_URL+="&HostName3=mail"
API_URL+="&RecordType3=A"
API_URL+="&Address3=${SERVER_IP}"
API_URL+="&TTL3=300"

# Record 4: MX record for email
API_URL+="&HostName4=@"
API_URL+="&RecordType4=MX"
API_URL+="&Address4=mail.fullpotential.com."
API_URL+="&MXPref4=10"
API_URL+="&TTL4=300"

# Record 5: SPF TXT record
API_URL+="&HostName5=@"
API_URL+="&RecordType5=TXT"
API_URL+="&Address5=v=spf1+mx+~all"
API_URL+="&TTL5=300"

# Record 6: Wildcard for all subdomains
API_URL+="&HostName6=*"
API_URL+="&RecordType6=A"
API_URL+="&Address6=${SERVER_IP}"
API_URL+="&TTL6=300"

# Record 7: Dashboard explicit (in case wildcard has issues)
API_URL+="&HostName7=dashboard"
API_URL+="&RecordType7=A"
API_URL+="&Address7=${SERVER_IP}"
API_URL+="&TTL7=300"

# Make the API call
RESPONSE=$(curl -s "$API_URL")

# Check response
if echo "$RESPONSE" | grep -q "ApiError"; then
    echo "❌ Error updating DNS records"
    echo ""
    echo "Error details:"
    echo "$RESPONSE" | grep -oP '(?<=<Error>).*?(?=</Error>)' || echo "$RESPONSE"
    echo ""
    echo "Possible issues:"
    echo "  - IP address $CLIENT_IP not whitelisted at Namecheap"
    echo "  - API credentials invalid"
    echo "  - API access not enabled"
    echo ""
    exit 1
fi

if echo "$RESPONSE" | grep -q 'Status="OK"' || echo "$RESPONSE" | grep -q '<Status>OK</Status>'; then
    echo "✅ DNS RECORDS RESTORED SUCCESSFULLY!"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📋 CONFIGURED RECORDS:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "  @ A         $SERVER_IP         (main domain)"
    echo "  www CNAME   fullpotential.com  (www redirect)"
    echo "  mail A      $SERVER_IP         (mail server)"
    echo "  @ MX        mail.fullpotential.com (priority 10)"
    echo "  @ TXT       v=spf1 mx ~all     (email auth)"
    echo "  * A         $SERVER_IP         (wildcard - all subdomains)"
    echo "  dashboard A $SERVER_IP         (explicit dashboard)"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⏰ DNS PROPAGATION"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "  Typical time: 5-30 minutes"
    echo "  Maximum time: 48 hours (rare)"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🧪 VERIFICATION COMMANDS"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "  # Check main domain"
    echo "  dig fullpotential.com +short"
    echo ""
    echo "  # Check email (MX records)"
    echo "  dig MX fullpotential.com +short"
    echo ""
    echo "  # Check mail server"
    echo "  dig mail.fullpotential.com +short"
    echo ""
    echo "  # Check wildcard subdomain"
    echo "  dig api.fullpotential.com +short"
    echo ""
    echo "  # Check all DNS propagation globally"
    echo "  # Visit: https://dnschecker.org"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📧 EMAIL STATUS"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "  Email should work again once DNS propagates!"
    echo "  james@fullpotential.com will route to $SERVER_IP"
    echo ""
    echo "  Test email delivery:"
    echo "  ssh root@198.54.123.234 'tail -f /var/log/mail.log'"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
else
    echo "❌ Unexpected response from Namecheap API"
    echo ""
    echo "$RESPONSE"
    exit 1
fi
