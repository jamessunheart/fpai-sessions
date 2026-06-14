#!/bin/bash
set -e

if [ -z "$1" ]; then
    echo "Usage: ./restore.sh <backup_file_name>"
    echo "Example: ./restore.sh magnet_trading_2025-11-19_12-00-00.sql.gz"
    exit 1
fi

BACKUP_FILE=$1
S3_BUCKET="magnet-trading-backups"
RESTORE_DIR="/tmp"

echo "📥 Downloading backup from S3..."
aws s3 cp "s3://${S3_BUCKET}/${BACKUP_FILE}" "${RESTORE_DIR}/${BACKUP_FILE}"

echo "🔄 Restoring database..."
gunzip < "${RESTORE_DIR}/${BACKUP_FILE}" | docker-compose exec -T db psql -U magnet_user magnet_trading

echo "🧹 Cleaning up..."
rm "${RESTORE_DIR}/${BACKUP_FILE}"

echo "✅ Restore complete!"
