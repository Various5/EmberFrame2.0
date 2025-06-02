# scripts/run.sh
#!/bin/bash

# EmberFrame V2 Run Script
set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠️ Virtual environment not found. Running setup...${NC}"
    ./scripts/setup.sh
fi

# Activate virtual environment
source venv/bin/activate

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Run database migrations if using Alembic
if [ -d "migrations" ]; then
    echo -e "${BLUE}🔄 Running database migrations...${NC}"
    alembic upgrade head
fi

# Start the application
echo -e "${GREEN}🚀 Starting EmberFrame V2...${NC}"
echo ""
echo -e "${BLUE}Application will be available at:${NC}"
echo "http://localhost:8000"
echo ""
echo -e "${BLUE}API Documentation:${NC}"
echo "http://localhost:8000/api/docs"
echo ""

if [ "$1" = "dev" ]; then
    # Development mode with auto-reload
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
else
    # Production mode
    gunicorn main:app -c gunicorn.conf.py
fi