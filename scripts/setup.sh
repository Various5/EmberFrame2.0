#!/bin/bash

# EmberFrame V2 Setup Script - Fixed Version
set -e

echo "🔥 Setting up EmberFrame V2..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if Python 3.11+ is installed
python_version=$(python3 --version 2>&1 | grep -Po '(?<=Python )[0-9]+\.[0-9]+')
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo -e "${RED}❌ Python 3.11 or higher is required. Found: $python_version${NC}"
    echo -e "${YELLOW}💡 Please install Python 3.11+ and try again${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Python version check passed: $python_version${NC}"

# Create virtual environment
echo -e "${BLUE}📦 Creating virtual environment...${NC}"
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
echo -e "${BLUE}📦 Upgrading pip...${NC}"
pip install --upgrade pip

# Install dependencies
echo -e "${BLUE}📦 Installing dependencies...${NC}"
if [ "$1" = "dev" ]; then
    pip install -r requirements/development.txt
    echo -e "${GREEN}✅ Development dependencies installed${NC}"
else
    pip install -r requirements/production.txt
    echo -e "${GREEN}✅ Production dependencies installed${NC}"
fi

# Create necessary directories
echo -e "${BLUE}📁 Creating directories...${NC}"
mkdir -p uploads
mkdir -p logs
mkdir -p static/uploads
mkdir -p backups
mkdir -p temp

# Set proper permissions
chmod 755 uploads logs static/uploads backups temp

# Copy environment file
if [ ! -f .env ]; then
    echo -e "${BLUE}⚙️ Creating environment file...${NC}"
    cp .env.example .env

    # Generate a random secret key
    if command -v openssl &> /dev/null; then
        SECRET_KEY=$(openssl rand -hex 32)
        sed -i.bak "s/your-secret-key-here-change-in-production/$SECRET_KEY/" .env
        rm -f .env.bak
        echo -e "${GREEN}✅ Generated random secret key${NC}"
    fi

    echo -e "${YELLOW}⚠️ Please edit .env file with your configuration${NC}"
fi

# Test Python imports
echo -e "${BLUE}🔍 Testing Python dependencies...${NC}"
python3 -c "
import sys
try:
    import fastapi
    import sqlalchemy
    import redis
    import uvicorn
    print('✅ Core dependencies imported successfully')
except ImportError as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)
" || {
    echo -e "${RED}❌ Dependency test failed. Please check the installation${NC}"
    exit 1
}

# Initialize database (simplified)
echo -e "${BLUE}🗄️ Initializing database...${NC}"
python3 -c "
import sys
import os
sys.path.insert(0, os.getcwd())

try:
    # Test basic imports first
    from app.core.config import get_settings
    from app.core.database import engine, Base, SessionLocal

    print('✅ Configuration and database modules loaded')

    # Create tables
    Base.metadata.create_all(bind=engine)
    print('✅ Database tables created')

    # Test database connection
    db = SessionLocal()
    result = db.execute('SELECT 1').fetchone()
    db.close()
    print('✅ Database connection test passed')

except Exception as e:
    print(f'❌ Database initialization error: {e}')
    print('ℹ️ You can manually initialize the database later with: python scripts/init_db.py')
    # Don't exit here, let setup continue
"

# Create a simple database initialization script for later use
echo -e "${BLUE}📝 Creating database initialization script...${NC}"
cat > scripts/init_db.py << 'EOF'
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
EOF

# Make the script executable
chmod +x scripts/init_db.py

# Create a simple run script
echo -e "${BLUE}📝 Creating run script...${NC}"
cat > scripts/run.py << 'EOF'
#!/usr/bin/env python3
"""
Simple run script for EmberFrame V2
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_app(dev_mode=False):
    """Run the EmberFrame V2 application"""
    try:
        # Import uvicorn
        import uvicorn

        # Import the app
        from main import app

        print("🚀 Starting EmberFrame V2...")
        print("📍 Application will be available at: http://localhost:8000")
        print("📚 API Documentation at: http://localhost:8000/api/docs")
        print("")

        # Run with uvicorn
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=dev_mode,
            log_level="info" if not dev_mode else "debug"
        )

    except Exception as e:
        print(f"❌ Failed to start application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    dev_mode = len(sys.argv) > 1 and sys.argv[1] == "dev"
    run_app(dev_mode)
EOF

chmod +x scripts/run.py

echo -e "${GREEN}🎉 Setup completed successfully!${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Edit .env file with your configuration:"
echo "   nano .env"
echo ""
echo "2. Initialize the database:"
echo "   python scripts/init_db.py init"
echo ""
echo "3. Start the application:"
echo "   python scripts/run.py dev    # Development mode"
echo "   python scripts/run.py        # Production mode"
echo ""
echo -e "${BLUE}Or use the simple run script:${NC}"
echo "   source venv/bin/activate"
echo "   python main.py"
echo ""
echo -e "${BLUE}Default admin credentials (after database init):${NC}"
echo "Username: admin"
echo "Password: admin123"
echo -e "${YELLOW}⚠️ Please change the default password after first login!${NC}"