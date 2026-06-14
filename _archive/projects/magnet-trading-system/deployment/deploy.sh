#!/bin/bash
set -e

echo "🚀 Deploying Magnet Trading System..."

# Check environment
if [ ! -f ../backend/.env ]; then
    echo "❌ .env file not found. Copy .env.example to .env first."
    exit 1
fi

# Build containers
echo "📦 Building Docker containers..."
docker-compose build

# Start services
echo "🔧 Starting services..."
docker-compose up -d

# Wait for database
echo "⏳ Waiting for database..."
sleep 5

# Run migrations (if we had Alembic set up)
# echo "🗄️  Running database migrations..."
# docker-compose exec backend alembic upgrade head

# Check health
echo "🏥 Checking system health..."
curl -f http://localhost:8000/health || echo "⚠️  Backend not ready yet"

echo "✅ Deployment complete!"
echo "📊 Dashboard: http://localhost:3000"
echo "🔌 API: http://localhost:8000"
echo "📝 Logs: docker-compose logs -f"
