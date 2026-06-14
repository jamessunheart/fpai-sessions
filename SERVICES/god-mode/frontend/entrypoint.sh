#!/bin/sh

# Default credentials if not set
USER=${BASIC_AUTH_USER:-architect}
PASS=${BASIC_AUTH_PASS:-sovereign}

echo "🔒 Securing God Mode with user: $USER"

# Create htpasswd file (using openssl if htpasswd not available, or just simple crypt)
# Alpine usually has htpasswd in apache2-utils
htpasswd -bc /etc/nginx/.htpasswd "$USER" "$PASS"

# Start Nginx
exec nginx -g "daemon off;"

