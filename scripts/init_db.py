#!/usr/bin/env python3
"""
Database initialization script for EmberFrame V2
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def init_database():
    """Initialize database with tables and default admin user"""
    try:
        print("🗄️ Initializing EmberFrame V2 database...")

        # Import after path setup
        from app.core.config import get_settings
        from app.core.database import engine, Base, SessionLocal
        from app.models.user import User
        from app.core.security import get_password_hash

        # Create tables
        print("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created")

        # Create default admin user
        settings = get_settings()
        db = SessionLocal()

        try:
            admin_user = db.query(User).filter(User.username == settings.DEFAULT_ADMIN_USERNAME).first()
            if not admin_user:
                admin_user = User(
                    username=settings.DEFAULT_ADMIN_USERNAME,
                    email='admin@emberframe.local',
                    hashed_password=get_password_hash(settings.DEFAULT_ADMIN_PASSWORD),
                    first_name='Admin',
                    last_name='User',
                    is_active=True,
                    is_admin=True
                )
                db.add(admin_user)
                db.commit()
                print(f"✅ Admin user created: {settings.DEFAULT_ADMIN_USERNAME}")
            else:
                print(f"ℹ️ Admin user already exists: {settings.DEFAULT_ADMIN_USERNAME}")

        finally:
            db.close()

        print("🎉 Database initialization completed!")
        return True

    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        print(f"Error details: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        success = init_database()
        sys.exit(0 if success else 1)
    else:
        print("Usage: python scripts/init_db.py init")
        sys.exit(1)
