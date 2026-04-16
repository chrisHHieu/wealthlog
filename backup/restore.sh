#!/bin/bash
# Restore WealthLog PostgreSQL backup
# Usage: ./restore.sh [backup_file]
# Default: wealthlog_backup.sql in the same directory

set -e

BACKUP_FILE="${1:-$(dirname "$0")/wealthlog_backup.sql}"

if [ ! -f "$BACKUP_FILE" ]; then
  echo "ERROR: Backup file not found: $BACKUP_FILE"
  exit 1
fi

echo "Restoring from: $BACKUP_FILE"
echo "This will DROP and recreate the wealthlog database."
read -p "Continue? (y/N) " confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
  echo "Aborted."
  exit 0
fi

# Drop and recreate database, then restore
docker compose exec -T db psql -U wealthlog -d postgres -c "DROP DATABASE IF EXISTS wealthlog;"
docker compose exec -T db psql -U wealthlog -d postgres -c "CREATE DATABASE wealthlog;"
docker compose exec -T db psql -U wealthlog -d wealthlog < "$BACKUP_FILE"

echo "Restore complete. Restart backend to apply:"
echo "  docker compose restart backend"
