#!/bin/bash
set -e

# Restore Script
# Usage: ./restore_db.sh <backup_file_path> <database_url>

BACKUP_FILE=$1
DB_URL=$2

if [ -z "$BACKUP_FILE" ] || [ -z "$DB_URL" ]; then
    echo "Usage: $0 <backup_file_path> <database_url>"
    exit 1
fi

echo "Restoring database from $BACKUP_FILE..."
pg_restore -d "$DB_URL" --clean --if-exists -F c "$BACKUP_FILE"

echo "Running verification..."
# Verify critical records are present
psql "$DB_URL" -c "SELECT count(*) FROM security_users;"
psql "$DB_URL" -c "SELECT count(*) FROM scheduling_events;"

echo "Restore and verification complete!"
