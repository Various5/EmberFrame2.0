# scripts/docker-setup.sh
#!/bin/bash

# Docker Setup Script for EmberFrame V2
set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🐳 Setting up EmberFrame V2 with Docker...${NC}"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi

# Create production environment file if it doesn't exist
if [ ! -f .env ]; then
    echo -e "${BLUE}⚙️ Creating production environment file...${NC}"
    cp .env.example .env

    # Generate random secret key
    SECRET_KEY=$(openssl rand -hex 32)
    sed -i "s/your-secret-key-here-change-in-production/$SECRET_KEY/" .env

    echo -e "${YELLOW}⚠️ Please edit .env file with your production configuration${NC}"
fi

# Create SSL directory
mkdir -p ssl

# Generate self-signed SSL certificate if not exists
if [ ! -f ssl/cert.pem ] || [ ! -f ssl/key.pem ]; then
    echo -e "${BLUE}🔒 Generating self-signed SSL certificate...${NC}"
    openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
    echo -e "${YELLOW}⚠️ Self-signed certificate generated. Replace with real certificates for production.${NC}"
fi

# Build and start containers
echo -e "${BLUE}🏗️ Building and starting containers...${NC}"
docker-compose -f docker-compose.yml build
docker-compose -f docker-compose.yml up -d

# Wait for services to be ready
echo -e "${BLUE}⏳ Waiting for services to be ready...${NC}"
sleep 30

# Initialize database
echo -e "${BLUE}🗄️ Initializing database...${NC}"
docker-compose exec app python -c "
from app.core.database import create_tables
create_tables()
print('✅ Database initialized')
"

echo -e "${GREEN}🎉 Docker setup completed!${NC}"
echo ""
echo -e "${BLUE}Services available at:${NC}"
echo "🌐 Application: https://localhost"
echo "📊 Grafana: http://localhost:3000"
echo "📈 Prometheus: http://localhost:9090"
echo ""
echo -e "${BLUE}Useful commands:${NC}"
echo "📝 View logs: docker-compose logs -f"
echo "🔄 Restart: docker-compose restart"
echo "🛑 Stop: docker-compose down"
echo "🧹 Clean up: docker-compose down -v"