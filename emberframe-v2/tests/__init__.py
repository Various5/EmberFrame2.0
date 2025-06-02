"""
Comprehensive testing suite for EmberFrame V2
Includes unit tests, integration tests, and end-to-end tests
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import io
import json

# Import application modules
from app import create_app
from app.core.database import Base, get_db
from app.core.config import get_settings
from app.core.security import get_password_hash, create_access_token
from app.models.user import User, UserRole
from app.models.file import File
from app.models.session import Session, SessionStatus
from app.models.audit import AuditLog
from app.services.file_service import FileService
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.utils.validators import validate_password, validate_file_type

# Test Database Setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session")
def test_settings():
    """Test settings configuration"""
    return {
        "APP_NAME": "EmberFrame V2 Test",
        "DEBUG": True,
        "SECRET_KEY": "test-secret-key-for-testing-only",
        "DATABASE_URL": SQLALCHEMY_DATABASE_URL,
        "REDIS_URL": "redis://localhost:6379/1",
        "UPLOAD_DIR": "test_uploads",
        "MAX_FILE_SIZE": 10 * 1024 * 1024,  # 10MB for testing
    }


@pytest.fixture(scope="session")
def app(test_settings):
    """Create test FastAPI application"""
    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    return app


@pytest.fixture(scope="session")
def client(app):
    """Create test client"""
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    """Create test database session"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user(db_session):
    """Create test user"""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("testpass123"),
        first_name="Test",
        last_name="User",
        role=UserRole.USER,
        is_active=True,
        is_verified=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session):
    """Create admin user"""
    user = User(
        username="admin",
        email="admin@example.com",
        hashed_password=get_password_hash("admin123"),
        first_name="Admin",
        last_name="User",
        role=UserRole.ADMIN,
        is_admin=True,
        is_active=True,
        is_verified=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    """Create authentication headers"""
    token = create_access_token(data={"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(admin_user):
    """Create admin authentication headers"""
    token = create_access_token(data={"sub": str(admin_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def temp_upload_dir():
    """Create temporary upload directory"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


# Unit Tests

class TestUserModel:
    """Test User model functionality"""

    def test_user_creation(self, db_session):
        """Test basic user creation"""
        user = User(
            username="newuser",
            email="new@example.com",
            hashed_password=get_password_hash("password123"),
            role=UserRole.USER
        )
        db_session.add(user)
        db_session.commit()

        assert user.id is not None
        assert user.username == "newuser"
        assert user.role == UserRole.USER
        assert not user.is_admin

    def test_user_full_name_property(self, test_user):
        """Test full name property"""
        assert test_user.full_name == "Test User"

        # Test with no first/last name
        user_no_name = User(username="noname")
        assert user_no_name.full_name == "noname"

    def test_storage_usage_percent(self, test_user):
        """Test storage usage percentage calculation"""
        test_user.storage_quota = 1000
        test_user.storage_used = 250

        assert test_user.storage_usage_percent == 25.0

        # Test with zero quota
        test_user.storage_quota = 0
        assert test_user.storage_usage_percent == 0

    def test_user_preferences(self, test_user):
        """Test user preferences functionality"""
        # Test default preferences
        assert test_user.get_preference("theme", "default") == "default"

        # Set preference
        test_user.set_preference("theme", "dark")
        assert test_user.get_preference("theme") == "dark"


class TestFileModel:
    """Test File model functionality"""

    def test_file_creation(self, db_session, test_user):
        """Test basic file creation"""
        file = File(
            name="test.txt",
            original_name="test.txt",
            path="test.txt",
            physical_path="/uploads/1/test.txt",
            size=1024,
            mime_type="text/plain",
            file_type="document",
            owner_id=test_user.id
        )
        db_session.add(file)
        db_session.commit()

        assert file.id is not None
        assert file.name == "test.txt"
        assert file.size == 1024
        assert file.owner_id == test_user.id

    def test_file_size_human_property(self, db_session, test_user):
        """Test human-readable file size"""
        file = File(
            name="large.txt",
            original_name="large.txt",
            path="large.txt",
            physical_path="/uploads/1/large.txt",
            size=1536,  # 1.5 KB
            owner_id=test_user.id
        )

        assert file.size_human == "1.5 KB"

    def test_file_tags(self, db_session, test_user):
        """Test file tagging functionality"""
        file = File(
            name="tagged.txt",
            original_name="tagged.txt",
            path="tagged.txt",
            physical_path="/uploads/1/tagged.txt",
            owner_id=test_user.id
        )

        # Test adding tags
        file.add_tag("important")
        file.add_tag("work")
        assert "important" in file.get_tag_list()
        assert "work" in file.get_tag_list()

        # Test removing tags
        file.remove_tag("work")
        assert "work" not in file.get_tag_list()
        assert "important" in file.get_tag_list()


class TestValidators:
    """Test validation utilities"""

    def test_password_validation(self):
        """Test password validation"""
        # Valid password
        assert validate_password("password123") == True

        # Too short
        assert validate_password("pass") == False

        # No numbers
        assert validate_password("password") == False

        # No letters
        assert validate_password("123456") == False

    def test_file_type_validation(self):
        """Test file type validation"""
        allowed_types = ['jpg', 'png', 'pdf']

        # Valid file
        assert validate_file_type("image.jpg", allowed_types) == True
        assert validate_file_type("document.pdf", allowed_types) == True

        # Invalid file
        assert validate_file_type("script.exe", allowed_types) == False
        assert validate_file_type("", allowed_types) == False


# Service Tests

class TestAuthService:
    """Test authentication service"""

    @pytest.mark.asyncio
    async def test_register_user(self, db_session):
        """Test user registration"""
        auth_service = AuthService(db_session)

        user_data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "password123",
            "first_name": "New",
            "last_name": "User"
        }

        # Mock UserCreate schema
        from unittest.mock import Mock
        user_create = Mock()
        user_create.username = user_data["username"]
        user_create.email = user_data["email"]
        user_create.password = user_data["password"]
        user_create.first_name = user_data["first_name"]
        user_create.last_name = user_data["last_name"]

        result = await auth_service.register_user(user_create)

        assert result.username == "newuser"
        assert result.access_token is not None
        assert result.token_type == "bearer"

    @pytest.mark.asyncio
    async def test_authenticate_user(self, db_session, test_user):
        """Test user authentication"""
        auth_service = AuthService(db_session)

        result = await auth_service.authenticate_user("testuser", "testpass123")

        assert result.username == "testuser"
        assert result.access_token is not None
        assert result.user_id == test_user.id

    @pytest.mark.asyncio
    async def test_authenticate_invalid_user(self, db_session):
        """Test authentication with invalid credentials"""
        auth_service = AuthService(db_session)

        with pytest.raises(Exception):  # Should raise HTTPException
            await auth_service.authenticate_user("nonexistent", "wrongpass")


class TestFileService:
    """Test file service"""

    @pytest.mark.asyncio
    async def test_list_files_empty_directory(self, db_session, test_user, temp_upload_dir):
        """Test listing files in empty directory"""
        with patch('app.services.file_service.FileService._get_user_dir', return_value=temp_upload_dir):
            file_service = FileService(db_session)
            result = await file_service.list_files(test_user.id)

            assert result["files"] == []
            assert result["path"] == ""
            assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_create_folder(self, db_session, test_user, temp_upload_dir):
        """Test folder creation"""
        with patch('app.services.file_service.FileService._get_user_dir', return_value=temp_upload_dir):
            file_service = FileService(db_session)
            result = await file_service.create_folder(test_user.id, "", "test_folder")

            assert result["message"] == "Folder created successfully"
            assert (temp_upload_dir / "test_folder").exists()

    @pytest.mark.asyncio
    async def test_file_upload_validation(self, db_session, test_user, temp_upload_dir):
        """Test file upload validation"""
        file_service = FileService(db_session)

        # Mock oversized file
        mock_file = Mock()
        mock_file.filename = "large.txt"
        mock_file.size = 1024 * 1024 * 1024  # 1GB
        mock_file.content_type = "text/plain"

        with pytest.raises(Exception):  # Should raise HTTPException for size
            await file_service.upload_files(test_user.id, [mock_file])


class TestUserService:
    """Test user service"""

    @pytest.mark.asyncio
    async def test_get_user(self, db_session, test_user):
        """Test getting user by ID"""
        user_service = UserService(db_session)
        result = await user_service.get_user(test_user.id)

        assert result.id == test_user.id
        assert result.username == test_user.username

    @pytest.mark.asyncio
    async def test_get_user_by_username(self, db_session, test_user):
        """Test getting user by username"""
        user_service = UserService(db_session)
        result = await user_service.get_user_by_username("testuser")

        assert result.id == test_user.id
        assert result.username == "testuser"

    @pytest.mark.asyncio
    async def test_update_user_preferences(self, db_session, test_user):
        """Test updating user preferences"""
        user_service = UserService(db_session)

        preferences = {"theme": "dark", "notifications": True}
        result = await user_service.update_user_preferences(test_user.id, preferences)

        assert result["message"] == "Preferences updated successfully"

        # Verify preferences were saved
        updated_prefs = await user_service.get_user_preferences(test_user.id)
        assert updated_prefs["theme"] == "dark"
        assert updated_prefs["notifications"] == True


# API Integration Tests

class TestAuthAPI:
    """Test authentication API endpoints"""

    def test_register_user_success(self, client):
        """Test successful user registration"""
        user_data = {
            "username": "apiuser",
            "email": "api@example.com",
            "password": "password123",
            "first_name": "API",
            "last_name": "User"
        }

        response = client.post("/api/auth/register", json=user_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["username"] == "apiuser"

    def test_register_duplicate_username(self, client, test_user):
        """Test registration with duplicate username"""
        user_data = {
            "username": "testuser",  # Already exists
            "email": "different@example.com",
            "password": "password123"
        }

        response = client.post("/api/auth/register", json=user_data)

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    def test_login_success(self, client, test_user):
        """Test successful login"""
        login_data = {
            "username": "testuser",
            "password": "testpass123"
        }

        response = client.post("/api/auth/login", data=login_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["username"] == "testuser"

    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials"""
        login_data = {
            "username": "nonexistent",
            "password": "wrongpass"
        }

        response = client.post("/api/auth/login", data=login_data)

        assert response.status_code == 401
        assert "credentials" in response.json()["detail"].lower()


class TestUserAPI:
    """Test user API endpoints"""

    def test_get_current_user(self, client, auth_headers):
        """Test getting current user profile"""
        response = client.get("/api/users/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert "email" in data

    def test_update_user_profile(self, client, auth_headers):
        """Test updating user profile"""
        update_data = {
            "first_name": "Updated",
            "last_name": "Name"
        }

        response = client.put("/api/users/me", json=update_data, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Updated"
        assert data["last_name"] == "Name"

    def test_unauthorized_access(self, client):
        """Test accessing protected endpoint without authentication"""
        response = client.get("/api/users/me")

        assert response.status_code == 401


class TestFileAPI:
    """Test file API endpoints"""

    def test_list_files_empty(self, client, auth_headers):
        """Test listing files in empty directory"""
        response = client.get("/api/files/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["files"] == []
        assert data["total"] == 0

    def test_create_folder(self, client, auth_headers):
        """Test folder creation via API"""
        folder_data = {
            "name": "api_test_folder",
            "path": ""
        }

        response = client.post("/api/files/folder", json=folder_data, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "created successfully" in data["message"]

    def test_upload_file(self, client, auth_headers):
        """Test file upload via API"""
        # Create test file
        test_content = b"Test file content for API upload"
        files = {
            "files": ("test.txt", io.BytesIO(test_content), "text/plain")
        }

        response = client.post("/api/files/upload", files=files, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "uploaded" in data["message"].lower()
        assert data["uploaded_files"][0]["name"] == "test.txt"


class TestAdminAPI:
    """Test admin API endpoints"""

    def test_get_users_as_admin(self, client, admin_headers):
        """Test getting users list as admin"""
        response = client.get("/api/admin/users", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_users_as_regular_user(self, client, auth_headers):
        """Test accessing admin endpoint as regular user"""
        response = client.get("/api/admin/users", headers=auth_headers)

        assert response.status_code == 403
        assert "Admin" in response.json()["detail"]

    def test_get_system_stats(self, client, admin_headers):
        """Test getting system statistics"""
        response = client.get("/api/admin/system/stats", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
        assert "total_files" in data
        assert "storage_used" in data


# Security Tests

class TestSecurity:
    """Test security features"""

    def test_password_hashing(self):
        """Test password hashing"""
        password = "testpassword123"
        hashed = get_password_hash(password)

        assert hashed != password
        assert len(hashed) > 50  # Bcrypt hashes are long

    def test_jwt_token_creation(self):
        """Test JWT token creation and validation"""
        from app.core.security import verify_token

        data = {"sub": "123", "username": "testuser"}
        token = create_access_token(data)

        assert token is not None
        assert len(token) > 50  # JWT tokens are long

        # Verify token
        decoded = verify_token(token)
        assert decoded["sub"] == "123"

    def test_invalid_jwt_token(self):
        """Test invalid JWT token handling"""
        from app.core.security import verify_token
        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            verify_token("invalid.token.here")


class TestRateLimiting:
    """Test rate limiting functionality"""

    def test_rate_limiter_basic(self):
        """Test basic rate limiting"""
        from app.middleware.security import RateLimiter

        rate_limiter = RateLimiter()
        identifier = "test_user"

        # First request should be allowed
        result = rate_limiter.check_rate_limit(identifier, limit=5, window=60)
        assert result["allowed"] == True
        assert result["remaining"] == 4

        # After 5 requests, should be denied
        for _ in range(4):
            rate_limiter.check_rate_limit(identifier, limit=5, window=60)

        result = rate_limiter.check_rate_limit(identifier, limit=5, window=60)
        assert result["allowed"] == False
        assert result["remaining"] == 0


# Performance Tests

class TestPerformance:
    """Test performance characteristics"""

    @pytest.mark.asyncio
    async def test_concurrent_user_creation(self, db_session):
        """Test concurrent user creation performance"""
        import asyncio

        auth_service = AuthService(db_session)

        async def create_user(index):
            from unittest.mock import Mock
            user_data = Mock()
            user_data.username = f"perfuser{index}"
            user_data.email = f"perf{index}@example.com"
            user_data.password = "password123"
            user_data.first_name = "Perf"
            user_data.last_name = f"User{index}"

            return await auth_service.register_user(user_data)

        # Create 10 users concurrently
        start_time = datetime.now()
        tasks = [create_user(i) for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = datetime.now()

        # Check that most operations succeeded (some might fail due to race conditions)
        successful = [r for r in results if not isinstance(r, Exception)]
        assert len(successful) >= 8  # At least 80% should succeed

        # Should complete within reasonable time
        duration = (end_time - start_time).total_seconds()
        assert duration < 5.0  # Should complete within 5 seconds

    def test_large_file_listing_performance(self, client, auth_headers, temp_upload_dir):
        """Test performance of listing many files"""
        # Create many files in temp directory
        user_dir = temp_upload_dir / "1"  # User ID 1
        user_dir.mkdir(exist_ok=True)

        # Create 1000 test files
        for i in range(1000):
            (user_dir / f"file_{i:04d}.txt").write_text(f"Content {i}")

        start_time = datetime.now()
        response = client.get("/api/files/", headers=auth_headers)
        end_time = datetime.now()

        assert response.status_code == 200

        # Should complete within reasonable time
        duration = (end_time - start_time).total_seconds()
        assert duration < 2.0  # Should complete within 2 seconds


# End-to-End Tests

class TestEndToEnd:
    """End-to-end workflow tests"""

    def test_complete_user_workflow(self, client):
        """Test complete user workflow from registration to file upload"""
        # 1. Register user
        user_data = {
            "username": "e2euser",
            "email": "e2e@example.com",
            "password": "password123",
            "first_name": "E2E",
            "last_name": "User"
        }

        register_response = client.post("/api/auth/register", json=user_data)
        assert register_response.status_code == 200

        # 2. Login
        login_data = {
            "username": "e2euser",
            "password": "password123"
        }

        login_response = client.post("/api/auth/login", data=login_data)
        assert login_response.status_code == 200

        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Get user profile
        profile_response = client.get("/api/users/me", headers=headers)
        assert profile_response.status_code == 200
        assert profile_response.json()["username"] == "e2euser"

        # 4. Create folder
        folder_data = {"name": "e2e_folder", "path": ""}
        folder_response = client.post("/api/files/folder", json=folder_data, headers=headers)
        assert folder_response.status_code == 200

        # 5. Upload file
        test_content = b"E2E test file content"
        files = {"files": ("e2e_test.txt", io.BytesIO(test_content), "text/plain")}
        upload_response = client.post("/api/files/upload", files=files, headers=headers)
        assert upload_response.status_code == 200

        # 6. List files to verify upload
        list_response = client.get("/api/files/", headers=headers)
        assert list_response.status_code == 200

        files_data = list_response.json()
        file_names = [f["name"] for f in files_data["files"]]
        assert "e2e_test.txt" in file_names
        assert "e2e_folder" in file_names

    def test_admin_user_management_workflow(self, client, admin_headers):
        """Test admin user management workflow"""
        # 1. Get initial user count
        users_response = client.get("/api/admin/users", headers=admin_headers)
        assert users_response.status_code == 200
        initial_count = len(users_response.json())

        # 2. Create new user via admin
        new_user_data = {
            "username": "adminuser",
            "email": "admin@example.com",
            "password": "password123",
            "is_admin": False
        }

        create_response = client.post("/api/admin/users", json=new_user_data, headers=admin_headers)
        assert create_response.status_code == 200

        # 3. Verify user was created
        users_response = client.get("/api/admin/users", headers=admin_headers)
        assert users_response.status_code == 200
        assert len(users_response.json()) == initial_count + 1

        # 4. Get system stats
        stats_response = client.get("/api/admin/system/stats", headers=admin_headers)
        assert stats_response.status_code == 200

        stats = stats_response.json()
        assert stats["total_users"] >= initial_count + 1


# Fixtures for specific test scenarios

@pytest.fixture
def sample_files(db_session, test_user, temp_upload_dir):
    """Create sample files for testing"""
    user_dir = temp_upload_dir / str(test_user.id)
    user_dir.mkdir(exist_ok=True)

    files = []

    # Create test files
    for i in range(5):
        file_path = user_dir / f"sample_{i}.txt"
        file_path.write_text(f"Sample content {i}")

        file_record = File(
            name=f"sample_{i}.txt",
            original_name=f"sample_{i}.txt",
            path=f"sample_{i}.txt",
            physical_path=str(file_path),
            size=len(f"Sample content {i}"),
            mime_type="text/plain",
            file_type="document",
            owner_id=test_user.id
        )
        db_session.add(file_record)
        files.append(file_record)

    db_session.commit()
    return files


# Utility functions for testing

def create_test_file(directory: Path, name: str, content: str = None) -> Path:
    """Create a test file with optional content"""
    file_path = directory / name
    content = content or f"Test content for {name}"
    file_path.write_text(content)
    return file_path


def assert_file_exists(file_path: Path, content: str = None):
    """Assert that a file exists and optionally check content"""
    assert file_path.exists(), f"File {file_path} should exist"
    if content:
        assert file_path.read_text() == content


# Test runner configuration

if __name__ == "__main__":
    pytest.main([
        "-v",  # Verbose output
        "--tb=short",  # Short traceback format
        "--cov=app",  # Coverage for app module
        "--cov-report=html:htmlcov",  # HTML coverage report
        "--cov-report=term-missing",  # Terminal coverage report
        "--cov-fail-under=80",  # Fail if coverage below 80%
        __file__
    ])