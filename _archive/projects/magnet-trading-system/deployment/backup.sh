#!/bin/bash
set -e

echo "📦 Starting database backup..."

# Configuration
BACKUP_DIR="/backups"
DATE=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP_FILE="magnet_trading_${DATE}.sql.gz"
S3_BUCKET="magnet-trading-backups"

# Create backup
echo "Creating PostgreSQL dump..."
docker-compose exec -T db pg_dump -U magnet_user magnet_trading | gzip > "${BACKUP_DIR}/${BACKUP_FILE}"

# Upload to S3
echo "Uploading to S3..."
aws s3 cp "${BACKUP_DIR}/${BACKUP_FILE}" "s3://${S3_BUCKET}/${BACKUP_FILE}" --server-side-encryption AES256

# Clean up old local backups (keep last 7 days)
echo "Cleaning up old local backups..."
find ${BACKUP_DIR} -name "magnet_trading_*.sql.gz" -mtime +7 -delete

# Clean up S3 backups (retention policy)
echo "Applying S3 retention policy..."
# Daily: 30 days, Weekly: 12 weeks, Monthly: 12 months
# This would be handled by S3 lifecycle policies

echo "✅ Backup complete: ${BACKUP_FILE}"
