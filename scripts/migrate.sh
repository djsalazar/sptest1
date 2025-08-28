#!/bin/bash
# Migration script for existing exam.db files

echo "🔄 NFT Evaluation System - Database Migration"

# Find existing exam.db files
POSSIBLE_PATHS=(
    "./exam.db"
    "./instance/exam.db" 
    "./app/exam.db"
    "./data/exam.db"
)

FOUND_DB=""
for path in "${POSSIBLE_PATHS[@]}"; do
    if [ -f "$path" ]; then
        echo "📁 Found existing database: $path"
        FOUND_DB="$path"
        break
    fi
done

if [ -z "$FOUND_DB" ]; then
    echo "⚠️  No existing database found. Will create new one."
    mkdir -p ./data
    exit 0
fi

# Create data directory
mkdir -p ./data

# Create backup of existing database
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
mkdir -p ./backups
BACKUP_FILE="./backups/migration_backup_$TIMESTAMP.db"
cp "$FOUND_DB" "$BACKUP_FILE"
echo "💾 Created migration backup: $BACKUP_FILE"

# Move database to new location
if [ "$FOUND_DB" != "./data/exam.db" ]; then
    cp "$FOUND_DB" "./data/exam.db"
    echo "✅ Database migrated to ./data/exam.db"
else
    echo "✅ Database already in correct location"
fi

# Verify migration
echo "🔍 Verifying migrated database..."
RESULT_COUNT=$(sqlite3 "./data/exam.db" "SELECT COUNT(*) FROM results;" 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "✅ Migration successful. Found $RESULT_COUNT existing results."
else
    echo "❌ Migration verification failed"
    exit 1
fi

echo "🚀 Migration completed. You can now run: docker compose up --build"