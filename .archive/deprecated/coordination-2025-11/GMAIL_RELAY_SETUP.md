# Gmail SMTP Relay Setup

## Issue: PTR Record Missing

Gmail requires a PTR (reverse DNS) record for the server IP to accept direct email delivery.
This needs to be set up by your hosting provider.

## Solution: Relay Through Gmail SMTP

Configure the server to send emails through Gmail's SMTP instead of directly.

### Setup Steps:

```bash
ssh root@198.54.123.234

# Create Gmail app password at: https://myaccount.google.com/apppasswords
# Use your Gmail account

# Create SASL password file
cat > /etc/postfix/sasl_passwd << EOF
[smtp.gmail.com]:587 YOUR_GMAIL@gmail.com:YOUR_APP_PASSWORD
EOF

# Secure and hash the file
chmod 600 /etc/postfix/sasl_passwd
postmap /etc/postfix/sasl_passwd

# Restart Postfix
systemctl restart postfix

# Test
echo "Test" | mail -s "Test via Gmail Relay" james@fullpotential.com
```

### Result:

- ✅ Daily reports will arrive in Gmail
- ✅ All forwarded emails will work
- ✅ No PTR record needed

