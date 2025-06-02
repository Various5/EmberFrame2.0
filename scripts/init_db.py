#!/usr/bin/env python3
"""
Initialize database with default data
"""

import sys
import os
from pathlib import Path

# Add the parent directory to the Python path
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

from app.core.database import engine, Base
from app.core.config import get_settings
from app.models.user import User
from app.core.security import get_password_hash
from sqlalchemy.orm import sessionmaker

def init_database():
    """Initialize database with default admin user"""

    # Create tables
    Base.metadata.create_all(bind=engine)

    # Create session
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        settings = get_settings()

        # Check if admin user exists
        admin = db.query(User).filter(User.username == settings.DEFAULT_ADMIN_USERNAME).first()

        if not admin:
            # Create admin user
            admin = User(
                username=settings.DEFAULT_ADMIN_USERNAME,
                email="admin@emberframe.com",
                hashed_password=get_password_hash(settings.DEFAULT_ADMIN_PASSWORD),
                first_name="System",
                last_name="Administrator",
                is_admin=True,
                is_active=True
            )

            db.add(admin)
            db.commit()
            print(f"✅ Created admin user: {settings.DEFAULT_ADMIN_USERNAME}")
        else:
            print("ℹ️ Admin user already exists")

    finally:
        db.close()

if __name__ == "__main__":
    init_database()