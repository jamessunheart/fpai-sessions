#!/bin/bash
# add-dkim-dns.sh - Add DKIM DNS record via Namecheap API

set -e

# Namecheap API credentials
API_USER="globalskypower"
API_KEY="1970bffd68144b08a4bea27acbac0854"
USERNAME="globalskypower"
CLIENT_IP=$(curl -s https://api.ipify.org)

echo "📧 Adding DKIM DNS record for fullpotential.com"
echo ""

# Get DKIM public key from server
echo "Fetching DKIM public key from server..."
DKIM_VALUE=$(ssh root@198.54.123.234 "cat /etc/opendkim/keys/fullpotential.com/mail.txt | grep 'p=' | sed 's/.*p=//; s/\".*//' | tr -d '\n\t '")

if [ -z "$DKIM_VALUE" ]; then
    echo "❌ Failed to get DKIM key"
    exit 1
fi

echo "DKIM Key length: ${#DKIM_VALUE} characters"
echo ""

# Build API URL to add DKIM TXT record
API_URL="https://api.namecheap.com/xml.response"
API_URL+="?ApiUser=${API_USER}"
API_URL+="&ApiKey=${API_KEY}"
API_URL+="&UserName=${USERNAME}"
API_URL+="&Command=namecheap.domains.dns.setHosts"
API_URL+="&ClientIp=${CLIENT_IP}"
API_URL+="&SLD=fullpotential"
API_URL+="&TLD=com"

# Keep existing records and add DKIM
# Record 1: @ A record
API_URL+="&HostName1=@"
API_URL+="&RecordType1=A"
API_URL+="&Address1=198.54.123.234"
API_URL+="&TTL1=1800"

# Record 2: mail A record
API_URL+="&HostName2=mail"
API_URL+="&RecordType2=A"
API_URL+="&Address2=198.54.123.234"
API_URL+="&TTL2=1800"

# Record 3: MX record
API_URL+="&HostName3=@"
API_URL+="&RecordType3=MX"
API_URL+="&Address3=mail.fullpotential.com."
API_URL+="&MXPref3=10"
API_URL+="&TTL3=1800"

# Record 4: SPF record (fixed)
API_URL+="&HostName4=@"
API_URL+="&RecordType4=TXT"
API_URL+="&Address4=v=spf1+ip4:198.54.123.234+mx+~all"
API_URL+="&TTL4=1800"

# Record 5: www CNAME
API_URL+="&HostName5=www"
API_URL+="&RecordType5=CNAME"
API_URL+="&Address5=fullpotential.com."
API_URL+="&TTL5=1800"

# Record 6: DKIM TXT record
DKIM_TXT="v=DKIM1;+h=sha256;+k=rsa;+p=${DKIM_VALUE}"
API_URL+="&HostName6=mail._domainkey"
API_URL+="&RecordType6=TXT"
API_URL+="&Address6=${DKIM_TXT}"
API_URL+="&TTL6=1800"

echo "Updating DNS records..."
RESPONSE=$(curl -s "$API_URL")

if echo "$RESPONSE" | grep -q "<IsSuccess>true</IsSuccess>"; then
    echo "✅ DNS records updated successfully!"
    echo ""
    echo "Added/Updated:"
    echo "  - SPF record: v=spf1 ip4:198.54.123.234 mx ~all"
    echo "  - DKIM record: mail._domainkey"
    echo ""
    echo "⏰ DNS propagation: 5-30 minutes"
    echo ""
    echo "🧪 Verify with:"
    echo "  dig TXT fullpotential.com +short  # SPF"
    echo "  dig TXT mail._domainkey.fullpotential.com +short  # DKIM"
else
    echo "❌ Failed to update DNS"
    echo "$RESPONSE" | grep -oP '(?<=<Error>).*?(?=</Error>)' || echo "$RESPONSE"
fi
