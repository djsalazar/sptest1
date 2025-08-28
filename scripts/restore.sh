#!/bin/bash
# NFT Evaluation System - Database Restore Script
# Usage: ./scripts/restore.sh [backup_file]

if [ $# -eq 0 ]; then
    echo "📋 Available backups:"
    ls -lht ./backups/exam_backup_*.db 2>/dev/null || echo "No backups found"
    echo ""
    echo "Usage: $0 <backup_file>"
    echo "Example: $0 ./backups/exam_backup_20250828_193000.db"
    exit 1
fi

BACKUP_FILE="$1"
TARGET_DB="./data/exam.db"

# Validate backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Stop Docker containers if running
echo "🛑 Stopping Docker containers..."
docker compose down 2>/dev/null

# Create current backup before restore
if [ -f "$TARGET_DB" ]; then
    CURRENT_BACKUP="./backups/pre_restore_backup_$(date +"%Y%m%d_%H%M%S").db"
    echo "💾 Creating pre-restore backup: $CURRENT_BACKUP"
    cp "$TARGET_DB" "$CURRENT_BACKUP"
fi

# Restore database
echo "🔄 Restoring database from: $BACKUP_FILE"
cp "$BACKUP_FILE" "$TARGET_DB"

if [ $? -eq 0 ]; then
    echo "✅ Database restored successfully"
    
    # Verify restored database
    echo "🔍 Verifying restored database..."
    sqlite3 "$TARGET_DB" "SELECT COUNT(*) as total_results FROM results;" 2>/dev/null || echo "⚠️  Unable to verify database integrity"
    
    echo "🚀 Starting Docker containers..."
    docker compose up -d
    
    echo "✅ Restore completed. System is ready."
else
    echo "❌ Error: Failed to restore database"
    exit 1
fi