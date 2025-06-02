# requirements/base.txt
# Base requirements for EmberFrame V2

# Core Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
gunicorn==21.2.0

# Database
sqlalchemy==2.0.23
alembic==1.12.1
psycopg2-binary==2.9.9  # PostgreSQL
sqlite3  # Built-in Python

# Authentication & Security
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
pyotp==2.9.0
qrcode[pil]==7.4.2

# Caching
redis==5.0.1
hiredis==2.2.3

# Background Tasks
celery==5.3.4

# HTTP Client
httpx==0.25.2

# File Processing
Pillow==10.1.0
python-magic==0.4.27
zipfile38==0.0.3  # Enhanced zip support

# Email
Jinja2==3.1.2
aiosmtplib==3.0.1

# Configuration
pydantic==2.5.0
pydantic-settings==2.1.0
python-dotenv==1.0.0

# Utilities
python-dateutil==2.8.2
pytz==2023.3

# Monitoring & Logging
psutil==5.9.6
structlog==23.2.0

# Development
python-json-logger==2.0.7

---

# requirements/development.txt
# Development requirements

-r base.txt

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
pytest-mock==3.12.0
httpx==0.25.2  # For testing

# Code Quality
black==23.11.0
isort==5.12.0
flake8==6.1.0
mypy==1.7.1

# Documentation
mkdocs==1.5.3
mkdocs-material==9.4.8

# Debugging
pytest-xdist==3.5.0
pytest-sugar==0.9.7

---

# requirements/production.txt
# Production requirements

-r base.txt

# Production WSGI Server
gunicorn==21.2.0

# Production Database
psycopg2-binary==2.9.9

# Monitoring
sentry-sdk[fastapi]==1.38.0

# Performance
orjson==3.9.10  # Faster JSON

---

# tests/conftest.py
"""
Test configuration and fixtures
"""

import pytest
import asyncio
from typing import Generator, AsyncGenerator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import create_app
from app.core.database import get_db, Base
from app.core.config import get_settings
from app.models.user import User
from app.core.security import get_password_hash

# Test database URL
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

# Create test engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Create test session
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def db_session():
    """Create a fresh database session for each test."""
    # Create tables
    Base.metadata.create_all(bind=engine)

    # Create session
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        # Drop tables after test
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def app(db_session):
    """Create a test FastAPI app."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    return app

@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)

@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("testpass123"),
        first_name="Test",
        last_name="User",
        is_active=True
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return user

@pytest.fixture
def admin_user(db_session):
    """Create a test admin user."""
    user = User(
        username="admin",
        email="admin@example.com",
        hashed_password=get_password_hash("adminpass123"),
        first_name="Admin",
        last_name="User",
        is_active=True,
        is_admin=True
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return user

@pytest.fixture
def auth_headers(client, test_user):
    """Get authentication headers for test user."""
    response = client.post(
        "/api/auth/login",
        data={"username": test_user.username, "password": "testpass123"}
    )

    assert response.status_code == 200
    token = response.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def admin_auth_headers(client, admin_user):
    """Get authentication headers for admin user."""
    response = client.post(
        "/api/auth/login",
        data={"username": admin_user.username, "password": "adminpass123"}
    )

    assert response.status_code == 200
    token = response.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}
