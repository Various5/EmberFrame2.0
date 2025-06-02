# scripts/setup.sh
#!/bin/bash

# EmberFrame V2 Setup Script
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

# Copy environment file
if [ ! -f .env ]; then
    echo -e "${BLUE}⚙️ Creating environment file...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}⚠️ Please edit .env file with your configuration${NC}"
fi

# Initialize database
echo -e "${BLUE}🗄️ Initializing database...${NC}"
python -c "
from app.core.database import create_tables
from app.core.config import get_settings
from app.models.user import User
from app.core.security import get_password_hash
from app.core.database import SessionLocal

# Create tables
create_tables()
print('✅ Database tables created')

# Create default admin user
settings = get_settings()
db = SessionLocal()

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
    print(f'✅ Admin user created: {settings.DEFAULT_ADMIN_USERNAME}')
else:
    print(f'✅ Admin user already exists: {settings.DEFAULT_ADMIN_USERNAME}')

db.close()
"

echo -e "${GREEN}🎉 Setup completed successfully!${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Edit .env file with your configuration"
echo "2. Run: ./scripts/run.sh"
echo ""
echo -e "${BLUE}Default admin credentials:${NC}"
echo "Username: admin"
echo "Password: admin123"
echo -e "${YELLOW}⚠️ Please change the default password after first login!${NC}"
