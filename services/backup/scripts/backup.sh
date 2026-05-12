#!/usr/bin/env bash
set -euo pipefail

DATA_DIR="${DATA_DIR:-/app/data}"
BACKUP_DIR="${BACKUP_DIR:-/app/data/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

mkdir -p "${BACKUP_DIR}"

echo "[$(date)] Starting backup..."

# Backup workbook
WORKBOOK="${DATA_DIR}/active/diet_plan.xlsx"
if [ -f "${WORKBOOK}" ]; then
    cp "${WORKBOOK}" "${BACKUP_DIR}/diet_plan_${TIMESTAMP}.xlsx"
    echo "[$(date)] Backed up workbook -> diet_plan_${TIMESTAMP}.xlsx"
else
    echo "[$(date)] No workbook found, skipping."
fi

# Backup SQLite DB
DB="${DATA_DIR}/active/app.db"
if [ -f "${DB}" ]; then
    cp "${DB}" "${BACKUP_DIR}/app_${TIMESTAMP}.db"
    echo "[$(date)] Backed up database -> app_${TIMESTAMP}.db"
else
    echo "[$(date)] No database found, skipping."
fi

# Prune old backups
echo "[$(date)] Pruning backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -name "*.xlsx" -mtime "+${RETENTION_DAYS}" -delete
find "${BACKUP_DIR}" -name "*.db"   -mtime "+${RETENTION_DAYS}" -delete

echo "[$(date)] Backup complete."
