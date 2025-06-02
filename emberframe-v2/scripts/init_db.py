#!/usr/bin/env python3
"""
Enhanced database initialization script for EmberFrame V2
Creates tables, default users, system settings, and sample data
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Add the parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.orm import sessionmaker
from app.core.database import engine, Base
from app.core.config import get_settings
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.file import File
from app.models.audit import AuditLog
from app.models.session import Session, SessionStatus
from app.models.notification import Notification, NotificationStatus
from app.models.system_settings import SystemSettings
from app.models.theme import Theme


def init_database():
    """Initialize database with tables and default data"""
    print("🔥 Initializing EmberFrame V2 Database...")
    print("=" * 60)

    # Create all tables
    print("📋 Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")

    # Create session
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        settings = get_settings()

        # Create default admin user
        create_default_admin(db, settings)

        # Create default system settings
        create_system_settings(db)

        # Create default themes
        create_default_themes(db)

        # Create sample data (if in debug mode)
        if settings.DEBUG:
            create_sample_data(db)

        # Commit all changes
        db.commit()

        print("\n" + "=" * 60)
        print("🎉 Database initialization completed successfully!")
        print("=" * 60)

        # Display connection info
        print(f"\n📊 Database URL: {settings.DATABASE_URL}")
        print(f"🔧 Debug Mode: {settings.DEBUG}")

        # Display admin credentials
        print(f"\n👤 Default Admin User:")
        print(f"   Username: {settings.DEFAULT_ADMIN_USERNAME}")
        print(f"   Password: {settings.DEFAULT_ADMIN_PASSWORD}")
        print(f"   ⚠️  Please change the default password after first login!")

        print(f"\n🌐 Access EmberFrame V2 at: http://localhost:8000")
        print(f"📚 API Documentation: http://localhost:8000/api/docs")

    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def create_default_admin(db, settings):
    """Create default admin user"""
    print("\n👤 Creating default admin user...")

    # Check if admin user already exists
    admin = db.query(User).filter(User.username == settings.DEFAULT_ADMIN_USERNAME).first()

    if admin:
        print(f"ℹ️  Admin user '{settings.DEFAULT_ADMIN_USERNAME}' already exists")
        return admin

    # Create admin user
    admin = User(
        username=settings.DEFAULT_ADMIN_USERNAME,
        email="admin@emberframe.local",
        hashed_password=get_password_hash(settings.DEFAULT_ADMIN_PASSWORD),
        first_name="System",
        last_name="Administrator",
        role=UserRole.ADMIN,
        is_admin=True,
        is_active=True,
        is_verified=True,
        storage_quota=10 * 1024 * 1024 * 1024,  # 10GB for admin
        preferences={
            "theme": "ember-blue",
            "notifications_enabled": True,
            "desktop_layout": {
                "show_desktop_icons": True,
                "taskbar_position": "bottom",
                "window_animations": True
            },
            "file_manager": {
                "view_mode": "grid",
                "show_hidden_files": False,
                "sort_by": "name"
            }
        }
    )

    db.add(admin)
    db.flush()  # Get the ID

    # Create initial audit log
    audit_log = AuditLog(
        user_id=admin.id,
        action="system_init",
        resource_type="system",
        resource_id="database",
        success=True,
        message="Database initialized with default admin user",
        details={
            "admin_username": admin.username,
            "admin_email": admin.email,
            "initialization_time": datetime.utcnow().isoformat()
        }
    )
    db.add(audit_log)

    print(f"✅ Created admin user: {admin.username}")
    return admin


def create_system_settings(db):
    """Create default system settings"""
    print("\n⚙️  Creating system settings...")

    default_settings = [
        {
            "key": "app_name",
            "value": "EmberFrame V2",
            "data_type": "string",
            "description": "Application name displayed in UI",
            "is_public": True,
            "is_editable": True
        },
        {
            "key": "app_version",
            "value": "2.0.0",
            "data_type": "string",
            "description": "Current application version",
            "is_public": True,
            "is_editable": False
        },
        {
            "key": "maintenance_mode",
            "value": False,
            "data_type": "bool",
            "description": "Enable maintenance mode to prevent user access",
            "is_public": False,
            "is_editable": True
        },
        {
            "key": "registration_enabled",
            "value": True,
            "data_type": "bool",
            "description": "Allow new user registration",
            "is_public": True,
            "is_editable": True
        },
        {
            "key": "max_file_size",
            "value": 100 * 1024 * 1024,  # 100MB
            "data_type": "int",
            "description": "Maximum file upload size in bytes",
            "is_public": True,
            "is_editable": True,
            "validation_rules": {
                "min": 1024,  # 1KB minimum
                "max": 1024 * 1024 * 1024  # 1GB maximum
            }
        },
        {
            "key": "default_storage_quota",
            "value": 1024 * 1024 * 1024,  # 1GB
            "data_type": "int",
            "description": "Default storage quota for new users",
            "is_public": False,
            "is_editable": True
        },
        {
            "key": "session_timeout",
            "value": 86400,  # 24 hours
            "data_type": "int",
            "description": "Session timeout in seconds",
            "is_public": False,
            "is_editable": True
        },
        {
            "key": "password_policy",
            "value": {
                "min_length": 6,
                "require_uppercase": False,
                "require_lowercase": False,
                "require_numbers": True,
                "require_symbols": False,
                "max_age_days": 0  # 0 = no expiration
            },
            "data_type": "json",
            "description": "Password policy rules",
            "is_public": True,
            "is_editable": True
        },
        {
            "key": "notification_settings",
            "value": {
                "email_notifications": True,
                "desktop_notifications": True,
                "notification_retention_days": 30
            },
            "data_type": "json",
            "description": "Global notification settings",
            "is_public": False,
            "is_editable": True
        },
        {
            "key": "file_types_allowed",
            "value": [
                "jpg", "jpeg", "png", "gif", "bmp", "webp", "svg",  # Images
                "txt", "md", "pdf", "doc", "docx", "rtf", "odt",  # Documents
                "zip", "rar", "7z", "tar", "gz",  # Archives
                "mp3", "wav", "ogg", "flac", "m4a",  # Audio
                "mp4", "avi", "mkv", "mov", "wmv", "flv",  # Video
                "py", "js", "html", "css", "json", "xml", "sql"  # Code
            ],
            "data_type": "json",
            "description": "Allowed file extensions for upload",
            "is_public": True,
            "is_editable": True
        }
    ]

    created_count = 0
    for setting_data in default_settings:
        # Check if setting already exists
        existing = db.query(SystemSettings).filter(
            SystemSettings.key == setting_data["key"]
        ).first()

        if not existing:
            setting = SystemSettings(**setting_data)
            db.add(setting)
            created_count += 1

    print(f"✅ Created {created_count} system settings")


def create_default_themes(db):
    """Create default themes"""
    print("\n🎨 Creating default themes...")

    themes = [
        {
            "name": "ember-blue",
            "display_name": "Ember Blue",
            "description": "Default blue theme with modern gradients",
            "css_variables": {
                "--primary-color": "#667eea",
                "--secondary-color": "#764ba2",
                "--background-color": "#0a0a0f",
                "--text-color": "#ffffff",
                "--border-color": "#333",
                "--window-bg": "#1a1a2e",
                "--taskbar-bg": "rgba(0, 0, 0, 0.8)",
                "--success-color": "#2ecc71",
                "--warning-color": "#f39c12",
                "--error-color": "#e74c3c",
                "--accent-color": "#9b59b6"
            },
            "is_dark": True,
            "is_default": True,
            "author": "EmberFrame Team",
            "version": "1.0.0"
        },
        {
            "name": "ember-purple",
            "display_name": "Ember Purple",
            "description": "Purple variant of the default theme",
            "css_variables": {
                "--primary-color": "#8b5cf6",
                "--secondary-color": "#a855f7",
                "--background-color": "#0f0a1a",
                "--text-color": "#ffffff",
                "--border-color": "#333",
                "--window-bg": "#1a1a2e",
                "--taskbar-bg": "rgba(0, 0, 0, 0.8)",
                "--success-color": "#2ecc71",
                "--warning-color": "#f39c12",
                "--error-color": "#e74c3c",
                "--accent-color": "#ec4899"
            },
            "is_dark": True,
            "author": "EmberFrame Team",
            "version": "1.0.0"
        },
        {
            "name": "ember-green",
            "display_name": "Ember Green",
            "description": "Green nature-inspired theme",
            "css_variables": {
                "--primary-color": "#10b981",
                "--secondary-color": "#059669",
                "--background-color": "#0a1a0a",
                "--text-color": "#ffffff",
                "--border-color": "#333",
                "--window-bg": "#1a2e1a",
                "--taskbar-bg": "rgba(0, 0, 0, 0.8)",
                "--success-color": "#2ecc71",
                "--warning-color": "#f39c12",
                "--error-color": "#e74c3c",
                "--accent-color": "#3b82f6"
            },
            "is_dark": True,
            "author": "EmberFrame Team",
            "version": "1.0.0"
        },
        {
            "name": "ember-dark",
            "display_name": "Ember Dark",
            "description": "Pure dark theme for reduced eye strain",
            "css_variables": {
                "--primary-color": "#404040",
                "--secondary-color": "#606060",
                "--background-color": "#000000",
                "--text-color": "#ffffff",
                "--border-color": "#333",
                "--window-bg": "#111111",
                "--taskbar-bg": "rgba(0, 0, 0, 0.9)",
                "--success-color": "#2ecc71",
                "--warning-color": "#f39c12",
                "--error-color": "#e74c3c",
                "--accent-color": "#888888"
            },
            "is_dark": True,
            "author": "EmberFrame Team",
            "version": "1.0.0"
        }
    ]

    created_count = 0
    for theme_data in themes:
        # Check if theme already exists
        existing = db.query(Theme).filter(Theme.name == theme_data["name"]).first()

        if not existing:
            theme = Theme(**theme_data)
            db.add(theme)
            created_count += 1

    print(f"✅ Created {created_count} themes")


def create_sample_data(db):
    """Create sample data for development/testing"""
    print("\n📊 Creating sample data (debug mode)...")

    # Create test user
    test_user = db.query(User).filter(User.username == "testuser").first()
    if not test_user:
        test_user = User(
            username="testuser",
            email="test@example.com",
            hashed_password=get_password_hash("testpass123"),
            first_name="Test",
            last_name="User",
            role=UserRole.USER,
            is_active=True,
            is_verified=True,
            preferences={
                "theme": "ember-purple",
                "notifications_enabled": True
            }
        )
        db.add(test_user)
        db.flush()
        print("✅ Created test user: testuser")

    # Create sample notifications for test user
    sample_notifications = [
        {
            "title": "Welcome to EmberFrame V2!",
            "message": "Your account has been created successfully. Explore the desktop environment and discover all the features.",
            "notification_type": "success",
            "is_important": True,
            "action_url": "/desktop",
            "action_text": "Get Started"
        },
        {
            "title": "Storage Quota",
            "message": "You have 1GB of storage space available. Upload your files to get started.",
            "notification_type": "info",
            "related_resource_type": "user",
            "related_resource_id": str(test_user.id)
        }
    ]

    for notif_data in sample_notifications:
        notification = Notification(
            user_id=test_user.id,
            **notif_data
        )
        db.add(notification)

    # Create sample session
    sample_session = Session(
        session_id="sample_session_123",
        user_id=test_user.id,
        ip_address="127.0.0.1",
        user_agent="Mozilla/5.0 (Test Browser)",
        device_info={
            "browser": "Test Browser",
            "os": "Test OS",
            "device_type": "desktop"
        },
        status=SessionStatus.ACTIVE,
        login_method="password",
        expires_at=datetime.utcnow() + timedelta(days=1)
    )
    db.add(sample_session)

    print("✅ Created sample notifications and session")


def reset_database():
    """Reset database by dropping and recreating all tables"""
    print("⚠️  Resetting database (all data will be lost)...")
    response = input("Are you sure? Type 'yes' to confirm: ")

    if response.lower() != 'yes':
        print("❌ Database reset cancelled")
        return

    print("🗑️  Dropping all tables...")
    Base.metadata.drop_all(bind=engine)

    print("📋 Recreating tables...")
    init_database()


def create_user(username: str, email: str, password: str, is_admin: bool = False):
    """Create a new user"""
    print(f"👤 Creating user: {username}")

    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # Check if user exists
        existing = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()

        if existing:
            print(f"❌ User with username '{username}' or email '{email}' already exists")
            return

        # Create user
        user = User(
            username=username,
            email=email,
            hashed_password=get_password_hash(password),
            role=UserRole.ADMIN if is_admin else UserRole.USER,
            is_admin=is_admin,
            is_active=True,
            is_verified=True
        )

        db.add(user)
        db.commit()

        print(f"✅ Created {'admin' if is_admin else 'user'}: {username}")
        print(f"   Email: {email}")
        print(f"   Password: {password}")

    except Exception as e:
        print(f"❌ Failed to create user: {e}")
        db.rollback()
    finally:
        db.close()


def main():
    """Main function with command line interface"""
    import argparse

    parser = argparse.ArgumentParser(description="EmberFrame V2 Database Management")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Init command
    init_parser = subparsers.add_parser('init', help='Initialize database')

    # Reset command
    reset_parser = subparsers.add_parser('reset', help='Reset database (WARNING: destroys all data)')

    # Create user command
    user_parser = subparsers.add_parser('create-user', help='Create a new user')
    user_parser.add_argument('username', help='Username')
    user_parser.add_argument('email', help='Email address')
    user_parser.add_argument('password', help='Password')
    user_parser.add_argument('--admin', action='store_true', help='Create admin user')

    args = parser.parse_args()

    if args.command == 'init' or not args.command:
        init_database()
    elif args.command == 'reset':
        reset_database()
    elif args.command == 'create-user':
        create_user(args.username, args.email, args.password, args.admin)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()