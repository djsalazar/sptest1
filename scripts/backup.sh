#!/bin/bash
# NFT Evaluation System - Database Backup Script
# Usage: ./scripts/backup.sh

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="./backups"
SOURCE_DB="./data/exam.db"
BACKUP_FILE="$BACKUP_DIR/exam_backup_$TIMESTAMP.db"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Check if source database exists
if [ ! -f "$SOURCE_DB" ]; then
    echo "❌ Error: Database file not found at $SOURCE_DB"
    exit 1
fi

# Create backup
echo "🔄 Creating backup of exam.db..."
cp "$SOURCE_DB" "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo "✅ Backup created successfully: $BACKUP_FILE"
    
    # Show backup size
    SIZE=$(ls -lh "$BACKUP_FILE" | awk '{print $5}')
    echo "📊 Backup size: $SIZE"
    
    # Keep only last 10 backups
    echo "🧹 Cleaning old backups (keeping last 10)..."
    ls -t $BACKUP_DIR/exam_backup_*.db | tail -n +11 | xargs -r rm
    
    echo "📁 Available backups:"
    ls -lht $BACKUP_DIR/exam_backup_*.db | head -10
else
    echo "❌ Error: Failed to create backup"
    exit 1
fi