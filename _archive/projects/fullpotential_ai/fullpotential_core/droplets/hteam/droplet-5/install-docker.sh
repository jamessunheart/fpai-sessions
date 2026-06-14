#!/bin/bash

# Update system
apt-get update

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
apt-get install -y docker-compose-plugin

# Start Docker
systemctl start docker
systemctl enable docker

echo "Docker and Docker Compose installed successfully!"
docker --version
docker compose version
