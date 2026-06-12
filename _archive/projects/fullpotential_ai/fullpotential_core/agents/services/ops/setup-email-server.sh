#!/bin/bash
# Email Server Setup for .234
# Sets up Postfix (SMTP) + Dovecot (IMAP) for james@fullpotential.com

set -e

echo "🔧 Setting up Email Server on 198.54.123.234..."
echo ""

# Update system
apt update && apt upgrade -y

# Install email server components
apt install -y postfix dovecot-core dovecot-imapd opendkim opendkim-tools

echo ""
echo "✅ Email packages installed"
echo ""

# Configure Postfix (SMTP for sending/receiving)
cat > /etc/postfix/main.cf << 'EOF'
# Main Postfix config for fullpotential.com
smtpd_banner = $myhostname ESMTP
biff = no
append_dot_mydomain = no
readme_directory = no

# Basic settings
myhostname = mail.fullpotential.com
mydomain = fullpotential.com
myorigin = $mydomain
mydestination = $myhostname, localhost.$mydomain, localhost, $mydomain
relayhost =
mynetworks = 127.0.0.0/8 [::ffff:127.0.0.0]/104 [::1]/128
mailbox_size_limit = 0
recipient_delimiter = +
inet_interfaces = all
inet_protocols = all

# Virtual mailbox settings
home_mailbox = Maildir/
mailbox_command =

# TLS parameters (for secure connections)
smtpd_tls_cert_file=/etc/ssl/certs/ssl-cert-snakeoil.pem
smtpd_tls_key_file=/etc/ssl/private/ssl-cert-snakeoil.key
smtpd_use_tls=yes
smtpd_tls_session_cache_database = btree:${data_directory}/smtpd_scache
smtp_tls_session_cache_database = btree:${data_directory}/smtp_scache

# DKIM
milter_protocol = 2
milter_default_action = accept
smtpd_milters = inet:localhost:12301
non_smtpd_milters = inet:localhost:12301
EOF

# Configure Dovecot (IMAP for accessing mail via Gmail app)
cat > /etc/dovecot/dovecot.conf << 'EOF'
# Dovecot configuration for fullpotential.com
protocols = imap
listen = *

# Mail location
mail_location = maildir:~/Maildir

# Authentication
disable_plaintext_auth = no
auth_mechanisms = plain login

passdb {
  driver = passwd-file
  args = /etc/dovecot/users
}

userdb {
  driver = static
  args = uid=vmail gid=vmail home=/var/mail/vhosts/%d/%n
}

# SSL (will update with real certs later)
ssl = yes
ssl_cert = </etc/ssl/certs/ssl-cert-snakeoil.pem
ssl_key = </etc/ssl/private/ssl-cert-snakeoil.key

# Logging
log_path = /var/log/dovecot.log
info_log_path = /var/log/dovecot-info.log
EOF

# Create virtual mail user
groupadd -g 5000 vmail
useradd -g vmail -u 5000 vmail -d /var/mail

# Create mail directories
mkdir -p /var/mail/vhosts/fullpotential.com/james
chown -R vmail:vmail /var/mail

echo ""
echo "✅ Email server configured"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  📧 EMAIL SETUP INSTRUCTIONS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Create email user password:"
echo "   Run: dovecot pw -s SHA512-CRYPT"
echo "   Enter a password and copy the hash"
echo ""
echo "2. Add user to Dovecot:"
echo "   echo 'james@fullpotential.com:{HASH}' > /etc/dovecot/users"
echo ""
echo "3. Restart services:"
echo "   systemctl restart postfix"
echo "   systemctl restart dovecot"
echo ""
echo "4. Test email works:"
echo "   echo 'Test' | mail -s 'Test' james@fullpotential.com"
echo ""
echo "5. Configure Gmail to access via IMAP:"
echo "   Server: 198.54.123.234"
echo "   Port: 993 (IMAP SSL)"
echo "   Username: james@fullpotential.com"
echo "   Password: [your password]"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
