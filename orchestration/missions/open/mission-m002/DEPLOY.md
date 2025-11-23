# Deployment Guide

This service is containerized and ready for deployment to any Docker-compatible environment (AWS ECS, DigitalOcean App Platform, Kubernetes, or a simple VPS).

## 🐳 Docker Deployment (Recommended)

### 1. Build the Image
```bash
docker build -t mission-control-backend .
```

### 2. Run with Docker Compose
This will start the service on port `8000`.
```bash
docker-compose up -d
```

### 3. Verify Deployment
Check the logs to ensure startup was successful:
```bash
docker-compose logs -f
```
Then visit `http://<your-server-ip>:8000/health`.

## ☁️ Cloud Deployment

### DigitalOcean / AWS / Azure
1. **Push** this repository to GitHub/GitLab.
2. **Connect** your cloud provider to the repo.
3. **Configure** the following Environment Variables:
   - `ENVIRONMENT`: `production`
   - `SERVICE_NAME`: `mission-control-backend`
   - `DATABASE_URL`: (Optional) Connection string for a managed PostgreSQL instance.

### Health Checks
Configure your load balancer to ping:
- Path: `/health`
- Port: `8000`
- Success Code: `200`

## 🔄 CI/CD Pipeline
This project is ready for CI/CD. A standard pipeline should:
1. Run tests: `pytest`
2. Build Docker image.
3. Push to container registry.
4. Trigger deployment.

