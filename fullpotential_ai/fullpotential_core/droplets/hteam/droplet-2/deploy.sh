#!/bin/bash
set -e

echo "🚀 Deploying Droplet-2 (Production)..."

# Stop and remove existing containers
echo "🛑 Cleaning up existing containers..."
docker stop airtable-server 2>/dev/null || true
docker rm airtable-server 2>/dev/null || true

# Build image
echo "🔨 Building Docker image..."
docker build -t airtable-server . || {
    echo "❌ Build failed!"
    exit 1
}

# Run container with health check
echo "🚀 Starting container..."
docker run -d \
  -p 80:8000 \
  -p 443:8000 \
  --env-file .env \
  --restart unless-stopped \
  --health-cmd="curl -f http://localhost:8000/health || exit 1" \
  --health-interval=30s \
  --health-timeout=10s \
  --health-retries=3 \
  --name airtable-server \
  airtable-server

# Wait for container to start
echo "⏳ Waiting for container to start..."
sleep 10

# Check if container is running
if ! docker ps | grep -q airtable-server; then
    echo "❌ Container failed to start!"
    echo "📋 Container logs:"
    docker logs airtable-server
    exit 1
fi

# Test health endpoint
echo "🧪 Testing health endpoint..."
for i in {1..5}; do
    if curl -sf http://localhost/health > /dev/null; then
        echo "✅ Server is healthy!"
        echo "📊 Testing UDC endpoints..."
        curl -s http://localhost/health | head -1
        curl -s http://localhost/capabilities | head -1
        echo "✅ Deployment successful!"
        echo "🌐 Server: https://drop2.fullpotential.ai"
        exit 0
    fi
    echo "⏳ Waiting for server... ($i/5)"
    sleep 5
done

echo "❌ Health check failed!"
echo "📋 Container logs:"
docker logs airtable-server
exit 1
