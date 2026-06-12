#!/bin/bash

# SSH ACCESS SETUP
# Purpose: Configure SSH key-based authentication for Full Potential AI production server
# Usage: ./setup-ssh-access.sh

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_header() { echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; echo -e "${CYAN}$1${NC}"; echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }

# Configuration
SERVER_IP="198.54.123.234"
SERVER_USER="root"
SERVER="${SERVER_USER}@${SERVER_IP}"
SSH_KEY_PATH="$HOME/.ssh/fpai_deploy_ed25519"

clear
print_header "Full Potential AI - SSH Access Setup"
echo ""
echo "Server: $SERVER"
echo "Key: $SSH_KEY_PATH"
echo ""

# Step 1: Check if SSH directory exists
if [ ! -d "$HOME/.ssh" ]; then
    print_info "Creating .ssh directory..."
    mkdir -p "$HOME/.ssh"
    chmod 700 "$HOME/.ssh"
    print_success ".ssh directory created"
fi

# Step 2: Generate SSH key if doesn't exist
if [ -f "$SSH_KEY_PATH" ]; then
    print_success "SSH key already exists"
else
    print_info "Generating new Ed25519 SSH key..."
    ssh-keygen -t ed25519 -f "$SSH_KEY_PATH" -N "" -C "fpai-deploy-$(date +%Y%m%d)"
    print_success "SSH key generated: $SSH_KEY_PATH"
fi

# Step 3: Display public key
echo ""
print_info "Public Key (will be copied to server):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cat "${SSH_KEY_PATH}.pub"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Step 4: Check if key is already on server
print_info "Checking existing SSH access..."
if ssh -i "$SSH_KEY_PATH" -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$SERVER" "echo 'Key already configured'" 2>/dev/null; then
    print_success "SSH key already configured on server!"
    echo ""
    print_info "Testing connection..."
    ssh -i "$SSH_KEY_PATH" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$SERVER" "hostname && uptime"
    echo ""
    print_success "SSH access is working! ✅"
    exit 0
fi

# Step 5: Offer setup methods
print_warning "SSH key not yet configured on server"
echo ""
print_info "Choose setup method:"
echo "  1. Automatic (requires server password - recommended)"
echo "  2. Manual (copy key yourself)"
echo "  3. Skip (assume you'll configure separately)"
echo ""
read -p "Enter choice (1, 2, or 3): " choice

case $choice in
    1)
        # Automatic setup using ssh-copy-id
        print_info "Attempting automatic SSH key copy..."
        print_warning "You will be prompted for the server root password"
        echo ""

        if ssh-copy-id -i "${SSH_KEY_PATH}.pub" "$SERVER" 2>&1; then
            print_success "SSH key copied successfully!"
        else
            print_error "Automatic copy failed"
            print_info "Falling back to manual instructions..."
            choice=2
        fi
        ;;

    2)
        # Manual setup instructions
        print_info "Manual Setup Instructions:"
        echo ""
        echo "Run these commands on the server (SSH in with password first):"
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "# 1. SSH into server"
        echo "ssh $SERVER"
        echo ""
        echo "# 2. Create .ssh directory (if doesn't exist)"
        echo "mkdir -p ~/.ssh && chmod 700 ~/.ssh"
        echo ""
        echo "# 3. Add public key to authorized_keys"
        echo "echo \"$(cat ${SSH_KEY_PATH}.pub)\" >> ~/.ssh/authorized_keys"
        echo ""
        echo "# 4. Set correct permissions"
        echo "chmod 600 ~/.ssh/authorized_keys"
        echo ""
        echo "# 5. Exit and test"
        echo "exit"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        print_warning "After completing these steps, run this script again to test"
        exit 0
        ;;

    3)
        print_info "Skipping SSH configuration"
        print_warning "Remember to configure SSH access before deploying"
        exit 0
        ;;

    *)
        print_error "Invalid choice"
        exit 1
        ;;
esac

# Step 6: Test connection
echo ""
print_info "Testing SSH connection..."

if ssh -i "$SSH_KEY_PATH" -o ConnectTimeout=10 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$SERVER" "echo 'Connection successful!'" 2>/dev/null; then
    print_success "SSH connection works!"
    echo ""
    print_info "Server details:"
    ssh -i "$SSH_KEY_PATH" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$SERVER" "hostname && uptime && df -h / | tail -1"
else
    print_error "SSH connection test failed"
    echo ""
    print_info "Troubleshooting steps:"
    echo "  1. Verify the public key was added to ~/.ssh/authorized_keys on server"
    echo "  2. Check server SSH config: sudo nano /etc/ssh/sshd_config"
    echo "     - Ensure: PubkeyAuthentication yes"
    echo "     - Ensure: PermitRootLogin yes (or prohibit-password)"
    echo "  3. Check server SSH logs: sudo tail -20 /var/log/auth.log"
    echo "  4. Test with verbose output: ssh -i $SSH_KEY_PATH -v $SERVER"
    echo ""
    exit 1
fi

# Step 7: Configure SSH config for convenience
print_info "Configuring SSH config..."

SSH_CONFIG="$HOME/.ssh/config"
touch "$SSH_CONFIG"
chmod 600 "$SSH_CONFIG"

if grep -q "Host fpai-prod" "$SSH_CONFIG" 2>/dev/null; then
    print_warning "SSH config entry already exists"
else
    cat >> "$SSH_CONFIG" << EOF

# Full Potential AI Production Server
Host fpai-prod
    HostName ${SERVER_IP}
    User ${SERVER_USER}
    IdentityFile ${SSH_KEY_PATH}
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    ServerAliveInterval 60
    ServerAliveCountMax 3

EOF
    print_success "SSH config updated"
fi

# Step 8: Update deployment scripts with SSH key
print_info "Checking deployment scripts..."

DEPLOY_SCRIPT="$(cd "$(dirname "$0")" && pwd)/deploy-to-server.sh"
if [ -f "$DEPLOY_SCRIPT" ]; then
    if grep -q "SSH_KEY=" "$DEPLOY_SCRIPT"; then
        print_success "Deployment script already configured"
    else
        print_warning "Deployment script needs SSH key configuration"
        print_info "Adding SSH_KEY configuration to deploy-to-server.sh..."
        # This will be done in a separate step
    fi
fi

# Summary
echo ""
print_header "SSH Access Setup Complete! 🌐⚡💎"
echo ""
print_success "Configuration Summary:"
echo "  • SSH key: $SSH_KEY_PATH"
echo "  • Server: $SERVER"
echo "  • SSH alias: fpai-prod"
echo ""
print_info "Quick commands:"
echo "  ssh fpai-prod              # Connect to server"
echo "  ssh fpai-prod 'uptime'     # Run remote command"
echo "  ./deploy-to-server.sh      # Deploy services"
echo ""
print_success "You can now deploy services to production! 🚀"
echo ""
