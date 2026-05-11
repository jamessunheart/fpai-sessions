#!/bin/bash
set -e

echo "=== Droplet-2 Installation ==="

# Navigate to app directory
cd /root/droplet-2 || { echo "Error: /root/droplet-2 not found"; exit 1; }

# Copy environment file
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✓ Created .env file - Please configure it with your credentials"
    echo "Edit .env file: nano .env"
    exit 0
fi

# Run deployment
chmod +x deploy.sh
./deploy.sh
