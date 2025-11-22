#!/bin/bash

# Service Registry Sync Strategy
# Mirrors services between Server ↔ Local ↔ GitHub

SERVER="root@198.54.123.234"
SERVER_DIR="/root/SERVICES"
LOCAL_DIR="/Users/jamessunheart/Development/SERVICES"
GITHUB_REPO="github.com/your-org/fpai-services"  # Update this

echo "🔄 Service Registry Sync Strategy"
echo "=================================="
echo ""

# Step 1: Pull services from server to local (one-time initial sync)
sync_from_server() {
    echo "📥 Step 1: Pull services from server to local"
    echo "   This is a ONE-TIME operation to get existing services"
    echo ""

    # List services on server
    echo "Services on server:"
    ssh $SERVER "ls -1 $SERVER_DIR"
    echo ""

    read -p "Pull all services from server? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Create local SERVICES directory if not exists
        mkdir -p "$LOCAL_DIR"

        # Rsync each service
        for service in $(ssh $SERVER "ls -1 $SERVER_DIR"); do
            echo "   Syncing: $service"
            rsync -avz --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
                  "$SERVER:$SERVER_DIR/$service/" "$LOCAL_DIR/$service/"
        done

        echo "✅ Services synced to: $LOCAL_DIR"
    fi
}

# Step 2: Initialize Git repo (if not already)
init_git() {
    echo ""
    echo "📦 Step 2: Initialize Git repository"

    cd "$LOCAL_DIR" || exit

    if [ ! -d ".git" ]; then
        echo "   Initializing git..."
        git init

        # Create .gitignore
        cat > .gitignore << 'EOF'
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.so
*.egg
*.egg-info/
dist/
build/
.env
.venv/
venv/
*.log
.DS_Store
*.swp
*.swo
*~
.idea/
.vscode/
EOF

        git add .
        git commit -m "Initial commit: Import services from server"

        echo "✅ Git repository initialized"
        echo "   Next: Create GitHub repo and add remote:"
        echo "      git remote add origin git@github.com:your-org/fpai-services.git"
        echo "      git push -u origin main"
    else
        echo "   ℹ️  Git repository already exists"
    fi
}

# Step 3: Create deployment script (GitHub → Server)
create_deploy_script() {
    echo ""
    echo "🚀 Step 3: Create deployment script"

    cat > "$LOCAL_DIR/deploy-to-server.sh" << 'DEPLOY_SCRIPT'
#!/bin/bash

# Deploy services from local/GitHub to server
# Usage: ./deploy-to-server.sh [service-name]

SERVER="root@198.54.123.234"
SERVER_DIR="/root/SERVICES"

if [ -n "$1" ]; then
    # Deploy specific service
    SERVICE="$1"
    echo "🚀 Deploying $SERVICE to server..."

    if [ ! -d "$SERVICE" ]; then
        echo "❌ Service directory not found: $SERVICE"
        exit 1
    fi

    # Rsync service to server
    rsync -avz --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
          "$SERVICE/" "$SERVER:$SERVER_DIR/$SERVICE/"

    echo "✅ $SERVICE deployed"

    # Restart service if running
    echo "🔄 Checking if service needs restart..."
    ssh $SERVER "cd $SERVER_DIR/$SERVICE && [ -f restart.sh ] && ./restart.sh || echo 'No restart script'"

else
    # Deploy all services
    echo "🚀 Deploying ALL services to server..."

    for service in */; do
        service=${service%/}
        if [ "$service" != ".git" ]; then
            echo "   Deploying: $service"
            rsync -avz --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
                  "$service/" "$SERVER:$SERVER_DIR/$service/"
        fi
    done

    echo "✅ All services deployed"
fi
DEPLOY_SCRIPT

    chmod +x "$LOCAL_DIR/deploy-to-server.sh"

    echo "✅ Created: $LOCAL_DIR/deploy-to-server.sh"
    echo "   Usage: ./deploy-to-server.sh [service-name]"
}

# Step 4: Create server-side pull script (Server pulls from GitHub)
create_server_pull_script() {
    echo ""
    echo "📥 Step 4: Create server-side GitHub pull script"

    cat > /tmp/pull-from-github.sh << 'PULL_SCRIPT'
#!/bin/bash

# Server-side script to pull latest services from GitHub
# Install on server and run via cron

REPO_URL="git@github.com:your-org/fpai-services.git"  # Update this
SERVICES_DIR="/root/SERVICES"
TEMP_DIR="/tmp/fpai-services-sync"

echo "📥 Pulling latest services from GitHub..."

# Clone/pull repo
if [ -d "$TEMP_DIR" ]; then
    cd "$TEMP_DIR"
    git pull origin main
else
    git clone "$REPO_URL" "$TEMP_DIR"
    cd "$TEMP_DIR"
fi

# Sync each service
for service in */; do
    service=${service%/}
    if [ "$service" != ".git" ]; then
        echo "   Syncing: $service"
        rsync -av --exclude='.git' "$service/" "$SERVICES_DIR/$service/"

        # Restart if needed
        if [ -f "$SERVICES_DIR/$service/restart.sh" ]; then
            echo "   Restarting: $service"
            cd "$SERVICES_DIR/$service" && ./restart.sh
        fi
    fi
done

echo "✅ Services updated from GitHub"
PULL_SCRIPT

    echo "✅ Created: /tmp/pull-from-github.sh"
    echo "   Copy to server:"
    echo "      scp /tmp/pull-from-github.sh $SERVER:/root/pull-from-github.sh"
    echo "      ssh $SERVER 'chmod +x /root/pull-from-github.sh'"
    echo ""
    echo "   Set up cron (run hourly):"
    echo "      ssh $SERVER 'echo \"0 * * * * /root/pull-from-github.sh >> /var/log/service-sync.log 2>&1\" | crontab -'"
}

# Main menu
echo "Choose sync strategy:"
echo "  1. One-time: Pull services from server → local"
echo "  2. Initialize Git repository"
echo "  3. Create deploy script (local → server)"
echo "  4. Create server pull script (GitHub → server)"
echo "  5. All of the above"
echo ""
read -p "Select (1-5): " choice

case $choice in
    1) sync_from_server ;;
    2) init_git ;;
    3) create_deploy_script ;;
    4) create_server_pull_script ;;
    5)
        sync_from_server
        init_git
        create_deploy_script
        create_server_pull_script
        echo ""
        echo "🎉 Complete! Next steps:"
        echo "   1. Create GitHub repository: fpai-services"
        echo "   2. Add remote: git remote add origin git@github.com:your-org/fpai-services.git"
        echo "   3. Push: git push -u origin main"
        echo "   4. Deploy changes: ./deploy-to-server.sh [service-name]"
        ;;
    *) echo "Invalid choice" ;;
esac
