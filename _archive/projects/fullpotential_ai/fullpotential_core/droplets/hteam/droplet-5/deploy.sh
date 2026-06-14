#!/bin/bash
# Deployment script for Droplet #5 Dashboard

echo "🚀 Deploying Droplet #5 Dashboard..."

# Pull latest code from GitHub
echo "📥 Pulling latest code..."
git pull origin main

# Stop and remove old containers
echo "🛑 Stopping old containers..."
docker-compose down

# Remove old images to force rebuild
echo "🗑️  Removing old images..."
docker-compose rm -f
docker rmi droplet-5-app 2>/dev/null || true

# Rebuild and start containers
echo "🔨 Building new image..."
docker-compose build --no-cache

echo "▶️  Starting containers..."
docker-compose up -d

# Show logs
echo "📋 Container logs:"
docker-compose logs --tail=50

echo "✅ Deployment complete!"
echo "🌐 Dashboard should be running at http://localhost:3000"
