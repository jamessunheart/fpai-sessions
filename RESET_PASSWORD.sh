#!/bin/bash

echo "🔐 GOD MODE PASSWORD RESET"
echo "---------------------------------"

# 1. Configuration
read -p "Server IP: " SERVER_IP
read -p "SSH User (Leave empty for 'root'): " SSH_USER
SSH_USER=${SSH_USER:-root}

echo ""
echo "👉 Resetting password for user: architect"
read -s -p "Enter NEW Password: " NEW_PASS
echo ""
read -s -p "Confirm Password:   " CONFIRM_PASS
echo ""

if [ "$NEW_PASS" != "$CONFIRM_PASS" ]; then
    echo "❌ Passwords do not match!"
    exit 1
fi

echo "🔄 Updating server..."

ssh $SSH_USER@$SERVER_IP "
    echo '1. Finding Container...'
    CONTAINER_ID=\$(docker ps -qf name=god-mode-frontend)
    
    if [ -z \"\$CONTAINER_ID\" ]; then
        echo '❌ Error: Frontend container is not running!'
        exit 1
    fi
    
    echo '2. Updating Password...'
    docker exec \$CONTAINER_ID htpasswd -bc /etc/nginx/.htpasswd architect '$NEW_PASS'
    
    echo '3. Reloading Nginx...'
    docker exec \$CONTAINER_ID nginx -s reload
    
    echo '✅ Password Updated Successfully!'
"

