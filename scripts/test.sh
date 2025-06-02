# scripts/test.sh
#!/bin/bash

# EmberFrame V2 Test Script
set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🧪 Running EmberFrame V2 Tests...${NC}"

# Activate virtual environment
source venv/bin/activate

# Install test dependencies if not already installed
pip install -r requirements/development.txt

# Run tests with coverage
echo -e "${BLUE}📊 Running tests with coverage...${NC}"
pytest tests/ \
    --cov=app \
    --cov-report=term-missing \
    --cov-report=html:htmlcov \
    --cov-fail-under=80 \
    -v

# Run code quality checks
echo -e "${BLUE}🔍 Running code quality checks...${NC}"

# Black formatting check
echo "Checking code formatting with Black..."
black --check app/ tests/ || {
    echo -e "${RED}❌ Code formatting issues found. Run: black app/ tests/${NC}"
    exit 1
}

# isort import sorting check
echo "Checking import sorting with isort..."
isort --check-only app/ tests/ || {
    echo -e "${RED}❌ Import sorting issues found. Run: isort app/ tests/${NC}"
    exit 1
}

# Flake8 linting
echo "Running flake8 linting..."
flake8 app/ tests/ || {
    echo -e "${RED}❌ Linting issues found${NC}"
    exit 1
}

# MyPy type checking
echo "Running mypy type checking..."
mypy app/ || {
    echo -e "${RED}❌ Type checking issues found${NC}"
    exit 1
}

echo -e "${GREEN}✅ All tests and checks passed!${NC}"