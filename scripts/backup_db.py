#!/usr/bin/env python3
"""
Database backup script
"""

import os
import shutil
import datetime
from pathlib import Path

def backup_database():
    """Create database backup"""

    # Source database
    db_path = "emberframe.db"

    if not os.path.exists(db_path):
        print("❌ Database file not found")
        return

    # Create backups directory
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)

    # Generate backup filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"emberframe_backup_{timestamp}.db"
    backup_path = backup_dir / backup_filename

    # Copy database
    try:
        shutil.copy2(db_path, backup_path)
        print(f"✅ Database backed up to: {backup_path}")

        # Cleanup old backups (keep last 10)
        backups = sorted(backup_dir.glob("emberframe_backup_*.db"))
        if len(backups) > 10:
            for old_backup in backups[:-10]:
                old_backup.unlink()
                print(f"🗑️ Removed old backup: {old_backup}")

    except Exception as e:
        print(f"❌ Backup failed: {e}")

if __name__ == "__main__":
    backup_database()
