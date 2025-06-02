#!/usr/bin/env python3
"""
EmberFrame V2 Project Structure Generator
Creates the complete project structure with all files and folders
"""

import os
import sys
from pathlib import Path


def create_directory(path):
    """Create directory if it doesn't exist"""
    Path(path).mkdir(parents=True, exist_ok=True)
    print(f"📁 Created directory: {path}")


def create_file(path, content=""):
    """Create file with optional content"""
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"📄 Created file: {path}")


def generate_emberframe_v2():
    """Generate the complete EmberFrame V2 project structure"""

    project_root = "emberframe-v2"

    print("🔥 Generating EmberFrame V2 Project Structure...")
    print("=" * 60)

    # Root directory
    create_directory(project_root)

    # ==========================================
    # APP DIRECTORY STRUCTURE
    # ==========================================

    # Main app directory
    app_dir = f"{project_root}/app"
    create_directory(app_dir)

    # App __init__.py (Application Factory)
    create_file(f"{app_dir}/__init__.py", '''"""
EmberFrame V2 - Modern Web Desktop Environment
Application Factory Pattern
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.sessions import SessionMiddleware

from app.core.config import get_settings
from app.core.database import engine
from app.api.auth import auth_router
from app.api.files import files_router
from app.api.users import users_router
from app.api.admin import admin_router
from app.api.websocket import websocket_router


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    settings = get_settings()

    app = FastAPI(
        title="EmberFrame V2",
        description="Modern Web Desktop Environment",
        version="2.0.0",
        docs_url="/api/docs" if settings.DEBUG else None,
        redoc_url="/api/redoc" if settings.DEBUG else None
    )

    # Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_HOSTS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.SECRET_KEY,
        max_age=settings.SESSION_EXPIRE
    )

    # Static files
    app.mount("/static", StaticFiles(directory="static"), name="static")

    # API Routes
    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
    app.include_router(files_router, prefix="/api/files", tags=["files"])
    app.include_router(users_router, prefix="/api/users", tags=["users"])
    app.include_router(admin_router, prefix="/api/admin", tags=["admin"])
    app.include_router(websocket_router, prefix="/ws", tags=["websocket"])

    return app
''')

    # ==========================================
    # API LAYER
    # ==========================================

    api_dir = f"{app_dir}/api"
    create_directory(api_dir)

    create_file(f"{api_dir}/__init__.py", '''"""
API Layer - FastAPI routers and endpoints
"""
''')

    # API Files
    create_file(f"{api_dir}/auth.py", '''"""
Authentication API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.services.auth_service import AuthService
from app.schemas.auth import TokenResponse, UserCreate, UserLogin

auth_router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


@auth_router.post("/register", response_model=TokenResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register new user"""
    try:
        auth_service = AuthService(db)
        return await auth_service.register_user(user_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@auth_router.post("/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """User login"""
    try:
        auth_service = AuthService(db)
        return await auth_service.authenticate_user(form_data.username, form_data.password)
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid credentials")


@auth_router.post("/logout")
async def logout():
    """User logout"""
    return {"message": "Logged out successfully"}


@auth_router.get("/me")
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Get current user info"""
    auth_service = AuthService(db)
    return await auth_service.get_current_user(token)
''')

    create_file(f"{api_dir}/files.py", '''"""
File management API endpoints
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from typing import List
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.services.file_service import FileService
from app.models.user import User

files_router = APIRouter()


@files_router.get("/")
async def list_files(
    path: str = "",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List files in directory"""
    file_service = FileService(db)
    return await file_service.list_files(user.id, path)


@files_router.post("/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    path: str = "",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload files"""
    file_service = FileService(db)
    return await file_service.upload_files(user.id, files, path)


@files_router.get("/download/{file_path:path}")
async def download_file(
    file_path: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download file"""
    file_service = FileService(db)
    file_info = await file_service.get_file(user.id, file_path)
    return FileResponse(
        path=file_info.physical_path,
        filename=file_info.name,
        media_type='application/octet-stream'
    )


@files_router.delete("/{file_path:path}")
async def delete_file(
    file_path: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete file or folder"""
    file_service = FileService(db)
    return await file_service.delete_file(user.id, file_path)


@files_router.post("/folder")
async def create_folder(
    path: str,
    name: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new folder"""
    file_service = FileService(db)
    return await file_service.create_folder(user.id, path, name)
''')

    create_file(f"{api_dir}/users.py", '''"""
User management API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.services.user_service import UserService
from app.schemas.user import UserUpdate, UserResponse
from app.models.user import User

users_router = APIRouter()


@users_router.get("/me", response_model=UserResponse)
async def get_my_profile(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user profile"""
    return user


@users_router.put("/me", response_model=UserResponse)
async def update_my_profile(
    user_update: UserUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user profile"""
    user_service = UserService(db)
    return await user_service.update_user(user.id, user_update)


@users_router.get("/preferences")
async def get_user_preferences(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user preferences"""
    user_service = UserService(db)
    return await user_service.get_user_preferences(user.id)


@users_router.put("/preferences")
async def update_user_preferences(
    preferences: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user preferences"""
    user_service = UserService(db)
    return await user_service.update_user_preferences(user.id, preferences)
''')

    create_file(f"{api_dir}/admin.py", '''"""
Admin API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.dependencies import get_db, get_current_user, require_admin
from app.services.user_service import UserService
from app.services.file_service import FileService
from app.schemas.user import UserResponse, UserCreate
from app.models.user import User

admin_router = APIRouter()


@admin_router.get("/users", response_model=List[UserResponse])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get all users (admin only)"""
    user_service = UserService(db)
    return await user_service.get_all_users(skip, limit)


@admin_router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create new user (admin only)"""
    user_service = UserService(db)
    return await user_service.create_user(user_data)


@admin_router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Delete user (admin only)"""
    user_service = UserService(db)
    return await user_service.delete_user(user_id)


@admin_router.get("/system/stats")
async def get_system_stats(
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get system statistics"""
    user_service = UserService(db)
    file_service = FileService(db)

    return {
        "total_users": await user_service.get_user_count(),
        "total_files": await file_service.get_file_count(),
        "storage_used": await file_service.get_storage_usage(),
        "active_sessions": 0  # TODO: Implement session tracking
    }
''')

    create_file(f"{api_dir}/websocket.py", '''"""
WebSocket handlers for real-time features
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
import json

websocket_router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                await self.disconnect(connection)


manager = ConnectionManager()


@websocket_router.websocket("/notifications")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            # Handle different message types
            await manager.send_personal_message(f"Echo: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
''')

    # ==========================================
    # CORE LAYER
    # ==========================================

    core_dir = f"{app_dir}/core"
    create_directory(core_dir)

    create_file(f"{core_dir}/__init__.py", '''"""
Core functionality and configuration
"""
''')

    create_file(f"{core_dir}/config.py", '''"""
Application configuration management
"""

from pydantic import BaseSettings
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""

    # Basic settings
    APP_NAME: str = "EmberFrame V2"
    DEBUG: bool = False
    SECRET_KEY: str = "your-secret-key-change-in-production"

    # Database
    DATABASE_URL: str = "sqlite:///./emberframe.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # Security
    ALLOWED_HOSTS: List[str] = ["*"]
    SESSION_EXPIRE: int = 86400  # 24 hours
    TOKEN_EXPIRE_HOURS: int = 24

    # File storage
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB

    # Admin
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_PASSWORD: str = "admin123"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
''')

    create_file(f"{core_dir}/database.py", '''"""
Database configuration and setup
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
''')

    create_file(f"{core_dir}/cache.py", '''"""
Redis cache configuration
"""

import redis
from typing import Optional, Any
import json

from app.core.config import get_settings

settings = get_settings()


class CacheService:
    def __init__(self):
        self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            value = self.redis_client.get(key)
            return json.loads(value) if value else None
        except Exception:
            return None

    async def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """Set value in cache"""
        try:
            return self.redis_client.setex(key, expire, json.dumps(value))
        except Exception:
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            return bool(self.redis_client.delete(key))
        except Exception:
            return False


# Global cache instance
cache = CacheService()
''')

    create_file(f"{core_dir}/security.py", '''"""
Security utilities and authentication
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status

from app.core.config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.TOKEN_EXPIRE_HOURS)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> dict:
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
''')

    create_file(f"{core_dir}/exceptions.py", '''"""
Custom application exceptions
"""

from fastapi import HTTPException, status


class EmberFrameException(Exception):
    """Base application exception"""
    pass


class AuthenticationError(EmberFrameException):
    """Authentication related errors"""
    pass


class AuthorizationError(EmberFrameException):
    """Authorization related errors"""
    pass


class FileNotFoundError(EmberFrameException):
    """File not found errors"""
    pass


class StorageQuotaExceededError(EmberFrameException):
    """Storage quota exceeded"""
    pass


class InvalidFileTypeError(EmberFrameException):
    """Invalid file type"""
    pass
''')

    create_file(f"{core_dir}/dependencies.py", '''"""
Dependency injection functions
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.models.user import User
from app.services.user_service import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    payload = verify_token(token)
    user_id = payload.get("sub")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

    user_service = UserService(db)
    user = await user_service.get_user(int(user_id))

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require admin privileges"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user
''')

    # ==========================================
    # MODELS
    # ==========================================

    models_dir = f"{app_dir}/models"
    create_directory(models_dir)

    create_file(f"{models_dir}/__init__.py", '''"""
Database models
"""
''')

    create_file(f"{models_dir}/user.py", '''"""
User model
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, BigInteger
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(80), unique=True, index=True, nullable=False)
    email = Column(String(120), unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)

    # Profile
    first_name = Column(String(50))
    last_name = Column(String(50))
    avatar_url = Column(String(255))

    # Permissions
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)

    # Storage
    storage_quota = Column(BigInteger, default=1024*1024*1024)  # 1GB
    storage_used = Column(BigInteger, default=0)

    # Preferences
    preferences = Column(Text, default="{}")
    theme = Column(String(50), default="ember-blue")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))

    # Relationships
    files = relationship("File", back_populates="owner", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")

    def __repr__(self):
        return f"<User {self.username}>"

    @property
    def full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username

    @property
    def storage_usage_percent(self):
        if self.storage_quota > 0:
            return (self.storage_used / self.storage_quota) * 100
        return 0
''')

    create_file(f"{models_dir}/file.py", '''"""
File model
"""

from sqlalchemy import Column, Integer, String, DateTime, BigInteger, Boolean, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    path = Column(String(500), nullable=False, index=True)
    physical_path = Column(String(500), nullable=False)

    # File info
    size = Column(BigInteger, default=0)
    mime_type = Column(String(100))
    file_type = Column(String(50))  # document, image, video, etc.
    checksum = Column(String(64))  # SHA-256

    # Metadata
    is_public = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    description = Column(Text)
    tags = Column(Text)  # JSON array of tags

    # Owner
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    accessed_at = Column(DateTime(timezone=True))

    # Relationships
    owner = relationship("User", back_populates="files")

    def __repr__(self):
        return f"<File {self.name}>"

    @property
    def size_human(self):
        """Human readable file size"""
        if self.size == 0:
            return "0 B"

        size = self.size
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
''')

    create_file(f"{models_dir}/session.py", '''"""
Session model
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), unique=True, index=True, nullable=False)

    # User
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Session info
    ip_address = Column(String(45))  # IPv6 compatible
    user_agent = Column(Text)
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))

    # Relationships
    user = relationship("User", back_populates="sessions")

    def __repr__(self):
        return f"<Session {self.session_id}>"
''')

    create_file(f"{models_dir}/audit.py", '''"""
Audit log model
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    # User (optional - can be system actions)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Action details
    action = Column(String(100), nullable=False)  # login, file_upload, user_create, etc.
    resource_type = Column(String(50))  # user, file, system, etc.
    resource_id = Column(String(100))  # ID of affected resource

    # Context
    ip_address = Column(String(45))
    user_agent = Column(Text)
    details = Column(JSON)  # Additional details as JSON

    # Result
    success = Column(String(10), default="success")  # success, error, warning
    message = Column(Text)

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog {self.action}>"
''')

    # ==========================================
    # SERVICES
    # ==========================================

    services_dir = f"{app_dir}/services"
    create_directory(services_dir)

    create_file(f"{services_dir}/__init__.py", '''"""
Business logic services
"""
''')

    # Continue with services...
    create_file(f"{services_dir}/auth_service.py", '''"""
Authentication service
"""

from datetime import timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.security import verify_password, get_password_hash, create_access_token
from app.models.user import User
from app.schemas.auth import UserCreate, TokenResponse
from app.services.audit_service import AuditService


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)

    async def register_user(self, user_data: UserCreate) -> TokenResponse:
        """Register new user"""
        # Check if user exists
        existing_user = self.db.query(User).filter(
            (User.username == user_data.username) | (User.email == user_data.email)
        ).first()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already registered"
            )

        # Create user
        hashed_password = get_password_hash(user_data.password)
        user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            first_name=user_data.first_name,
            last_name=user_data.last_name
        )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        # Log registration
        await self.audit_service.log_action("user_register", "user", str(user.id), user.id)

        # Create token
        access_token = create_access_token(data={"sub": str(user.id)})

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=user.id,
            username=user.username
        )

    async def authenticate_user(self, username: str, password: str) -> TokenResponse:
        """Authenticate user"""
        user = self.db.query(User).filter(User.username == username).first()

        if not user or not verify_password(password, user.hashed_password):
            await self.audit_service.log_action("login_failed", "user", username)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )

        # Log successful login
        await self.audit_service.log_action("login_success", "user", str(user.id), user.id)

        # Create token
        access_token = create_access_token(data={"sub": str(user.id)})

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=user.id,
            username=user.username
        )

    async def get_current_user(self, token: str) -> User:
        """Get current user from token"""
        # Token verification is handled in dependencies
        pass
''')

    create_file(f"{services_dir}/user_service.py", '''"""
User management service
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import User
from app.schemas.user import UserUpdate, UserCreate
from app.core.security import get_password_hash
from app.services.audit_service import AuditService


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)

    async def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return self.db.query(User).filter(User.id == user_id).first()

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        return self.db.query(User).filter(User.username == username).first()

    async def get_all_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all users with pagination"""
        return self.db.query(User).offset(skip).limit(limit).all()

    async def create_user(self, user_data: UserCreate) -> User:
        """Create new user"""
        hashed_password = get_password_hash(user_data.password)
        user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            is_admin=getattr(user_data, 'is_admin', False)
        )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        await self.audit_service.log_action("user_create", "user", str(user.id))
        return user

    async def update_user(self, user_id: int, user_update: UserUpdate) -> User:
        """Update user"""
        user = await self.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        update_data = user_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)

        self.db.commit()
        self.db.refresh(user)

        await self.audit_service.log_action("user_update", "user", str(user.id), user.id)
        return user

    async def delete_user(self, user_id: int) -> dict:
        """Delete user"""
        user = await self.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        self.db.delete(user)
        self.db.commit()

        await self.audit_service.log_action("user_delete", "user", str(user_id))
        return {"message": "User deleted successfully"}

    async def get_user_count(self) -> int:
        """Get total user count"""
        return self.db.query(User).count()

    async def get_user_preferences(self, user_id: int) -> dict:
        """Get user preferences"""
        user = await self.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        import json
        return json.loads(user.preferences or "{}")

    async def update_user_preferences(self, user_id: int, preferences: dict) -> dict:
        """Update user preferences"""
        user = await self.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        import json
        user.preferences = json.dumps(preferences)
        self.db.commit()

        return {"message": "Preferences updated successfully"}
''')

    create_file(f"{services_dir}/file_service.py", '''"""
File management service
"""

import os
import hashlib
import shutil
from typing import List, Optional
from pathlib import Path
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.models.file import File
from app.models.user import User
from app.core.config import get_settings
from app.services.audit_service import AuditService

settings = get_settings()


class FileService:
    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.upload_dir.mkdir(exist_ok=True)

    def _get_user_dir(self, user_id: int) -> Path:
        """Get user's upload directory"""
        user_dir = self.upload_dir / str(user_id)
        user_dir.mkdir(exist_ok=True)
        return user_dir

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate file SHA-256 checksum"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    async def list_files(self, user_id: int, path: str = "") -> dict:
        """List files in user directory"""
        user_dir = self._get_user_dir(user_id)
        target_dir = user_dir / path if path else user_dir

        if not target_dir.exists() or not target_dir.is_dir():
            raise HTTPException(status_code=404, detail="Directory not found")

        files = []
        for item in target_dir.iterdir():
            if item.is_file():
                file_record = self.db.query(File).filter(
                    File.owner_id == user_id,
                    File.physical_path == str(item)
                ).first()

                files.append({
                    "name": item.name,
                    "type": "file",
                    "size": item.stat().st_size if file_record else 0,
                    "modified": item.stat().st_mtime,
                    "is_public": file_record.is_public if file_record else False
                })
            elif item.is_dir():
                files.append({
                    "name": item.name,
                    "type": "folder",
                    "size": 0,
                    "modified": item.stat().st_mtime
                })

        return {"files": files, "path": path}

    async def upload_files(self, user_id: int, files: List[UploadFile], path: str = "") -> dict:
        """Upload files for user"""
        user_dir = self._get_user_dir(user_id)
        target_dir = user_dir / path if path else user_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        uploaded_files = []

        for file in files:
            # Check file size
            if file.size > settings.MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"File {file.filename} exceeds maximum size"
                )

            # Save file
            file_path = target_dir / file.filename
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # Create file record
            checksum = self._calculate_checksum(file_path)
            file_record = File(
                name=file.filename,
                original_name=file.filename,
                path=f"{path}/{file.filename}" if path else file.filename,
                physical_path=str(file_path),
                size=file_path.stat().st_size,
                mime_type=file.content_type,
                checksum=checksum,
                owner_id=user_id
            )

            self.db.add(file_record)
            uploaded_files.append(file.filename)

        self.db.commit()

        await self.audit_service.log_action(
            "file_upload",
            "file",
            f"{len(uploaded_files)} files",
            user_id
        )

        return {"uploaded_files": uploaded_files, "count": len(uploaded_files)}

    async def get_file(self, user_id: int, file_path: str) -> File:
        """Get file by path"""
        file_record = self.db.query(File).filter(
            File.owner_id == user_id,
            File.path == file_path
        ).first()

        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")

        return file_record

    async def delete_file(self, user_id: int, file_path: str) -> dict:
        """Delete file"""
        file_record = await self.get_file(user_id, file_path)

        # Delete physical file
        physical_path = Path(file_record.physical_path)
        if physical_path.exists():
            if physical_path.is_file():
                physical_path.unlink()
            elif physical_path.is_dir():
                shutil.rmtree(physical_path)

        # Delete record
        self.db.delete(file_record)
        self.db.commit()

        await self.audit_service.log_action("file_delete", "file", file_path, user_id)

        return {"message": "File deleted successfully"}

    async def create_folder(self, user_id: int, path: str, name: str) -> dict:
        """Create folder"""
        user_dir = self._get_user_dir(user_id)
        folder_path = user_dir / path / name if path else user_dir / name

        if folder_path.exists():
            raise HTTPException(status_code=400, detail="Folder already exists")

        folder_path.mkdir(parents=True)

        await self.audit_service.log_action("folder_create", "file", f"{path}/{name}", user_id)

        return {"message": "Folder created successfully"}

    async def get_file_count(self) -> int:
        """Get total file count"""
        return self.db.query(File).count()

    async def get_storage_usage(self) -> int:
        """Get total storage usage"""
        result = self.db.query(func.sum(File.size)).scalar()
        return result or 0
''')

    # Add remaining service files...
    create_file(f"{services_dir}/cache_service.py", '''"""
Caching service
"""

from typing import Any, Optional
from app.core.cache import cache


class CacheService:
    @staticmethod
    async def get_user_cache(user_id: int, key: str) -> Optional[Any]:
        """Get user-specific cached data"""
        cache_key = f"user:{user_id}:{key}"
        return await cache.get(cache_key)

    @staticmethod
    async def set_user_cache(user_id: int, key: str, value: Any, expire: int = 3600) -> bool:
        """Set user-specific cached data"""
        cache_key = f"user:{user_id}:{key}"
        return await cache.set(cache_key, value, expire)

    @staticmethod
    async def delete_user_cache(user_id: int, key: str) -> bool:
        """Delete user-specific cached data"""
        cache_key = f"user:{user_id}:{key}"
        return await cache.delete(cache_key)

    @staticmethod
    async def get_system_cache(key: str) -> Optional[Any]:
        """Get system-wide cached data"""
        cache_key = f"system:{key}"
        return await cache.get(cache_key)

    @staticmethod
    async def set_system_cache(key: str, value: Any, expire: int = 3600) -> bool:
        """Set system-wide cached data"""
        cache_key = f"system:{key}"
        return await cache.set(cache_key, value, expire)
''')

    create_file(f"{services_dir}/audit_service.py", '''"""
Audit logging service
"""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.audit import AuditLog


class AuditService:
    def __init__(self, db: Session):
        self.db = db

    async def log_action(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        success: str = "success",
        message: Optional[str] = None
    ):
        """Log an audit event"""
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
            success=success,
            message=message
        )

        self.db.add(audit_log)
        self.db.commit()

    async def get_user_activity(self, user_id: int, limit: int = 100):
        """Get user activity logs"""
        return self.db.query(AuditLog).filter(
            AuditLog.user_id == user_id
        ).order_by(AuditLog.created_at.desc()).limit(limit).all()

    async def get_system_activity(self, limit: int = 100):
        """Get system activity logs"""
        return self.db.query(AuditLog).order_by(
            AuditLog.created_at.desc()
        ).limit(limit).all()
''')

    create_file(f"{services_dir}/notification_service.py", '''"""
Notification service
"""

from typing import List, Dict, Any
from enum import Enum


class NotificationType(Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class NotificationService:
    def __init__(self):
        self.subscribers = {}

    async def send_notification(
        self,
        user_id: int,
        message: str,
        type: NotificationType = NotificationType.INFO,
        data: Dict[str, Any] = None
    ):
        """Send notification to user"""
        notification = {
            "id": f"notif_{user_id}_{len(self.subscribers)}",
            "message": message,
            "type": type.value,
            "data": data or {},
            "timestamp": "2024-01-01T00:00:00Z"  # Use actual timestamp
        }

        # Here you would implement actual notification delivery
        # For example: WebSocket, email, push notification, etc.
        print(f"Notification for user {user_id}: {message}")

        return notification

    async def broadcast_notification(
        self,
        message: str,
        type: NotificationType = NotificationType.INFO,
        data: Dict[str, Any] = None
    ):
        """Broadcast notification to all users"""
        notification = {
            "message": message,
            "type": type.value,
            "data": data or {},
            "timestamp": "2024-01-01T00:00:00Z"
        }

        # Implement broadcast logic
        print(f"Broadcast notification: {message}")

        return notification
''')

    # ==========================================
    # SCHEMAS
    # ==========================================

    schemas_dir = f"{app_dir}/schemas"
    create_directory(schemas_dir)

    create_file(f"{schemas_dir}/__init__.py", '''"""
Pydantic schemas for request/response validation
"""
''')

    create_file(f"{schemas_dir}/user.py", '''"""
User schemas
"""

from typing import Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime


class UserBase(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar_url: Optional[str] = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    storage_quota: int
    storage_used: int
    theme: str
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        orm_mode = True


class UserPreferences(BaseModel):
    theme: Optional[str] = "ember-blue"
    notifications_enabled: Optional[bool] = True
    desktop_layout: Optional[dict] = {}
    shortcuts: Optional[dict] = {}
''')

    create_file(f"{schemas_dir}/auth.py", '''"""
Authentication schemas
"""

from pydantic import BaseModel
from typing import Optional


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    username: str


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
''')

    create_file(f"{schemas_dir}/file.py", '''"""
File schemas
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class FileBase(BaseModel):
    name: str
    is_public: Optional[bool] = False


class FileCreate(FileBase):
    path: str
    size: int
    mime_type: Optional[str] = None


class FileResponse(FileBase):
    id: int
    path: str
    size: int
    mime_type: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class FileList(BaseModel):
    files: List[FileResponse]
    total: int
    page: int
    per_page: int


class FolderCreate(BaseModel):
    name: str
    path: Optional[str] = ""
''')

    # ==========================================
    # TASKS (Background Jobs)
    # ==========================================

    tasks_dir = f"{app_dir}/tasks"
    create_directory(tasks_dir)

    create_file(f"{tasks_dir}/__init__.py", '''"""
Background task definitions
"""
''')

    create_file(f"{tasks_dir}/file_tasks.py", '''"""
File processing background tasks
"""

from celery import Celery
import os
from pathlib import Path

celery_app = Celery("emberframe")


@celery_app.task
def cleanup_temp_files():
    """Clean up temporary files older than 24 hours"""
    temp_dir = Path("/tmp/emberframe")
    if temp_dir.exists():
        for file in temp_dir.iterdir():
            if file.is_file() and file.stat().st_mtime < (time.time() - 86400):
                file.unlink()
    return "Temp files cleaned"


@celery_app.task
def generate_file_thumbnail(file_id: int):
    """Generate thumbnail for image files"""
    # Implement thumbnail generation
    return f"Thumbnail generated for file {file_id}"


@celery_app.task
def virus_scan_file(file_id: int):
    """Scan uploaded file for viruses"""
    # Implement virus scanning
    return f"File {file_id} scanned"


@celery_app.task
def backup_user_files(user_id: int):
    """Backup user files to external storage"""
    # Implement backup logic
    return f"User {user_id} files backed up"
''')

    create_file(f"{tasks_dir}/maintenance_tasks.py", '''"""
System maintenance background tasks
"""

from celery import Celery
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.audit import AuditLog
from datetime import datetime, timedelta

celery_app = Celery("emberframe")


@celery_app.task
def cleanup_old_audit_logs():
    """Clean up audit logs older than 90 days"""
    db = SessionLocal()
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        deleted = db.query(AuditLog).filter(
            AuditLog.created_at < cutoff_date
        ).delete()
        db.commit()
        return f"Deleted {deleted} old audit logs"
    finally:
        db.close()


@celery_app.task
def update_storage_statistics():
    """Update storage usage statistics"""
    # Implement storage stats update
    return "Storage statistics updated"


@celery_app.task
def system_health_check():
    """Perform system health check"""
    # Implement health check logic
    return "System health check completed"


@celery_app.task
def send_daily_reports():
    """Send daily system reports to admins"""
    # Implement daily report generation
    return "Daily reports sent"
''')

    # ==========================================
    # UTILS
    # ==========================================

    utils_dir = f"{app_dir}/utils"
    create_directory(utils_dir)

    create_file(f"{utils_dir}/__init__.py", '''"""
Utility functions and helpers
"""
''')

    create_file(f"{utils_dir}/validators.py", '''"""
Input validation utilities
"""

import re
from typing import List, Optional
from fastapi import HTTPException


def validate_username(username: str) -> bool:
    """Validate username format"""
    if not username or len(username) < 3 or len(username) > 30:
        return False

    # Allow alphanumeric and underscore
    pattern = r'^[a-zA-Z0-9_]+$'
    return bool(re.match(pattern, username))


def validate_password(password: str) -> bool:
    """Validate password strength"""
    if not password or len(password) < 6:
        return False

    # Check for at least one letter and one number
    has_letter = any(c.isalpha() for c in password)
    has_number = any(c.isdigit() for c in password)

    return has_letter and has_number


def validate_file_type(filename: str, allowed_types: List[str]) -> bool:
    """Validate file type by extension"""
    if not filename:
        return False

    extension = filename.lower().split('.')[-1]
    return extension in [t.lower() for t in allowed_types]


def validate_file_size(file_size: int, max_size: int) -> bool:
    """Validate file size"""
    return 0 < file_size <= max_size


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    # Remove dangerous characters
    unsafe_chars = r'[<>:"/\\|?*]'
    safe_filename = re.sub(unsafe_chars, '_', filename)

    # Limit length
    if len(safe_filename) > 255:
        name, ext = safe_filename.rsplit('.', 1) if '.' in safe_filename else (safe_filename, '')
        safe_filename = name[:255-len(ext)-1] + '.' + ext if ext else name[:255]

    return safe_filename


def validate_path(path: str) -> bool:
    """Validate file path for security"""
    if not path:
        return True

    # Check for path traversal attempts
    dangerous_patterns = ['../', '..\\\\', '/..', '\\\\..']
    return not any(pattern in path for pattern in dangerous_patterns)
''')

    create_file(f"{utils_dir}/helpers.py", '''"""
General helper functions
"""

import hashlib
import secrets
import string
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta


def generate_random_string(length: int = 32) -> str:
    """Generate random string for tokens, etc."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def hash_string(text: str) -> str:
    """Generate SHA-256 hash of string"""
    return hashlib.sha256(text.encode()).hexdigest()


def format_file_size(size: int) -> str:
    """Format file size in human readable format"""
    if size == 0:
        return "0 B"

    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    return f"{size:.1f} {units[unit_index]}"


def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime to string"""
    return dt.strftime(format_str)


def parse_datetime(dt_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """Parse datetime from string"""
    return datetime.strptime(dt_str, format_str)


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """Split list into chunks"""
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]


def merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
    """Merge two dictionaries"""
    result = dict1.copy()
    result.update(dict2)
    return result


def get_client_ip(request) -> str:
    """Get client IP address from request"""
    x_forwarded_for = request.headers.get('X-Forwarded-For')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.client.host


def is_safe_url(url: str, allowed_hosts: List[str]) -> bool:
    """Check if URL is safe for redirects"""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    return parsed.netloc in allowed_hosts or not parsed.netloc
''')

    create_file(f"{utils_dir}/logging.py", '''"""
Logging configuration
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler


def setup_logging(
    log_level: str = "INFO",
    log_file: str = "logs/emberframe.log",
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
):
    """Setup application logging"""

    # Create logs directory
    log_dir = Path(log_file).parent
    log_dir.mkdir(exist_ok=True)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)

    # File handler
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_file_size,
        backupCount=backup_count
    )
    file_handler.setLevel(getattr(logging, log_level.upper()))
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(file_formatter)

    # Add handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Silence noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get logger instance"""
    return logging.getLogger(name)


class AuditLogger:
    """Special logger for audit events"""

    def __init__(self, log_file: str = "logs/audit.log"):
        self.logger = logging.getLogger("audit")
        self.logger.setLevel(logging.INFO)

        # Create handler if not exists
        if not self.logger.handlers:
            handler = TimedRotatingFileHandler(
                log_file,
                when="midnight",
                interval=1,
                backupCount=30
            )

            formatter = logging.Formatter(
                '%(asctime)s - AUDIT - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def log(self, action: str, user_id: int, details: str = ""):
        """Log audit event"""
        message = f"Action: {action} | User: {user_id} | Details: {details}"
        self.logger.info(message)


# Global audit logger instance
audit_logger = AuditLogger()
''')

    # ==========================================
    # ROOT LEVEL FILES
    # ==========================================

    # Main application entry point
    create_file(f"{project_root}/main.py", '''"""
EmberFrame V2 - Main Application Entry Point
"""

import uvicorn
from app import create_app
from app.core.config import get_settings
from app.core.database import create_tables
from app.utils.logging import setup_logging

# Setup logging
setup_logging()

# Create tables
create_tables()

# Create app
app = create_app()

if __name__ == "__main__":
    settings = get_settings()

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )
''')

    # ==========================================
    # REQUIREMENTS
    # ==========================================

    requirements_dir = f"{project_root}/requirements"
    create_directory(requirements_dir)

    create_file(f"{requirements_dir}/base.txt", '''# Base requirements for EmberFrame V2
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
sqlalchemy>=2.0.0
alembic>=1.12.0
pydantic>=2.0.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.6
redis>=5.0.0
celery>=5.3.0
jinja2>=3.1.0
aiofiles>=23.0.0
python-dotenv>=1.0.0
pillow>=10.0.0
''')

    create_file(f"{requirements_dir}/development.txt", '''# Development requirements
-r base.txt

# Development tools
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
black>=23.0.0
isort>=5.12.0
flake8>=6.0.0
mypy>=1.5.0
pre-commit>=3.4.0

# Documentation
mkdocs>=1.5.0
mkdocs-material>=9.2.0

# Database tools
sqlite-utils>=3.35.0
''')

    create_file(f"{requirements_dir}/production.txt", '''# Production requirements
-r base.txt

# Production server
gunicorn>=21.2.0

# Monitoring
sentry-sdk[fastapi]>=1.32.0

# Database
psycopg2-binary>=2.9.0  # PostgreSQL

# Cache
redis>=5.0.0

# File storage (optional)
boto3>=1.29.0  # AWS S3
''')

    # ==========================================
    # CONFIGURATION FILES
    # ==========================================

    # Environment variables template
    create_file(f"{project_root}/.env.example", '''# EmberFrame V2 Environment Variables

# Basic Configuration
APP_NAME=EmberFrame V2
DEBUG=true
SECRET_KEY=your-secret-key-here-change-in-production

# Database
DATABASE_URL=sqlite:///./emberframe.db
# DATABASE_URL=postgresql://user:password@localhost/emberframe

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
ALLOWED_HOSTS=["localhost", "127.0.0.1", "0.0.0.0"]
SESSION_EXPIRE=86400
TOKEN_EXPIRE_HOURS=24

# File Storage
UPLOAD_DIR=uploads
MAX_FILE_SIZE=104857600  # 100MB

# Admin
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=admin123

# External Services (Optional)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1
S3_BUCKET=emberframe-files

# Email (Optional)
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
EMAIL_FROM=noreply@emberframe.com

# Monitoring (Optional)
SENTRY_DSN=
''')

    # Docker configuration
    create_file(f"{project_root}/Dockerfile", '''# EmberFrame V2 Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    g++ \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements/production.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create uploads directory
RUN mkdir -p uploads logs

# Expose port
EXPOSE 8000

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser
RUN chown -R appuser:appuser /app
USER appuser

# Run application
CMD ["gunicorn", "main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
''')

    create_file(f"{project_root}/docker-compose.yml", '''version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/emberframe
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - ./uploads:/app/uploads
      - ./logs:/app/logs

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=emberframe
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  celery:
    build: .
    command: celery -A app.tasks worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/emberframe
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - ./uploads:/app/uploads

volumes:
  postgres_data:
  redis_data:
''')

    # Gunicorn configuration
    create_file(f"{project_root}/gunicorn.conf.py", '''"""
Gunicorn configuration for production
"""

import multiprocessing

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

# Timeout
timeout = 30
keepalive = 2

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%h %l %u %t "%r" %s %b "%{Referer}i" "%{User-Agent}i"'

# Process naming
proc_name = "emberframe"

# Server mechanics
daemon = False
pidfile = "/tmp/gunicorn.pid"
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"
''')

    # Celery configuration
    create_file(f"{project_root}/celery_config.py", '''"""
Celery configuration
"""

from celery import Celery
from app.core.config import get_settings

settings = get_settings()

# Create Celery instance
celery_app = Celery(
    "emberframe",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.file_tasks",
        "app.tasks.maintenance_tasks"
    ]
)

# Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_disable_rate_limits=True,
    worker_prefetch_multiplier=1
)

# Periodic tasks
celery_app.conf.beat_schedule = {
    "cleanup-temp-files": {
        "task": "app.tasks.file_tasks.cleanup_temp_files",
        "schedule": 3600.0,  # Every hour
    },
    "cleanup-audit-logs": {
        "task": "app.tasks.maintenance_tasks.cleanup_old_audit_logs",
        "schedule": 86400.0,  # Daily
    },
    "update-storage-stats": {
        "task": "app.tasks.maintenance_tasks.update_storage_statistics",
        "schedule": 1800.0,  # Every 30 minutes
    },
    "system-health-check": {
        "task": "app.tasks.maintenance_tasks.system_health_check",
        "schedule": 300.0,  # Every 5 minutes
    }
}
''')

    # Alembic configuration
    create_file(f"{project_root}/alembic.ini", '''# A generic, single database configuration.

[alembic]
# path to migration scripts
script_location = migrations

# template used to generate migration files
# file_template = %%(rev)s_%%(slug)s

# sys.path path, will be prepended to sys.path if present.
# defaults to the current working directory.
prepend_sys_path = .

# timezone to use when rendering the date within the migration file
# as well as the filename.
# If specified, requires the python-dateutil library that can be
# installed by adding `alembic[tz]` to the pip requirements
# string value is passed to dateutil.tz.gettz()
# leave blank for localtime
# timezone =

# max length of characters to apply to the
# "slug" field
# truncate_slug_length = 40

# set to 'true' to run the environment during
# the 'revision' command, regardless of autogenerate
# revision_environment = false

# set to 'true' to allow .pyc and .pyo files without
# a source .py file to be detected as revisions in the
# versions/ directory
# sourceless = false

# version number format
version_num_format = %04d

# version path separator; As mentioned above, this is the character used to split
# version_locations. The default within new alembic.ini files is "os", which uses
# os.pathsep. If this key is omitted entirely, it falls back to the legacy
# behavior of splitting on spaces and/or commas.
# Valid values for version_path_separator are:
#
# version_path_separator = :
# version_path_separator = ;
# version_path_separator = space
version_path_separator = os

# the output encoding used when revision files
# are written from script.py.mako
# output_encoding = utf-8

sqlalchemy.url = sqlite:///./emberframe.db


[post_write_hooks]
# post_write_hooks defines scripts or Python functions that are run
# on newly generated revision scripts.  See the documentation for further
# detail and examples

# format using "black" - use the console_scripts runner, against the "black" entrypoint
# hooks = black
# black.type = console_scripts
# black.entrypoint = black
# black.options = -l 79 REVISION_SCRIPT_FILENAME

# Logging configuration
[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
''')

    # Test configuration
    create_file(f"{project_root}/pytest.ini", '''[tool:pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
python_classes = Test*
addopts = 
    --strict-markers
    --strict-config
    --verbose
    --cov=app
    --cov-report=term-missing
    --cov-report=html:htmlcov
    --cov-fail-under=80

markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
''')

    # ==========================================
    # DIRECTORIES
    # ==========================================

    # Create remaining directories
    directories = [
        "migrations",
        "tests",
        "static/js/core",
        "static/js/apps",
        "static/js/utils",
        "static/css",
        "static/images",
        "templates",
        "docker",
        "scripts",
        "logs",
        "uploads"
    ]

    for directory in directories:
        create_directory(f"{project_root}/{directory}")

    # ==========================================
    # BASIC TESTS
    # ==========================================

    tests_dir = f"{project_root}/tests"

    create_file(f"{tests_dir}/__init__.py", "# Test package")

    create_file(f"{tests_dir}/conftest.py", '''"""
Test configuration and fixtures
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import create_app
from app.core.database import Base, get_db
from app.core.config import get_settings

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    """Test client fixture"""
    Base.metadata.create_all(bind=engine)

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user():
    """Test user data"""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123",
        "first_name": "Test",
        "last_name": "User"
    }
''')

    create_file(f"{tests_dir}/test_auth.py", '''"""
Authentication tests
"""

import pytest
from fastapi.testclient import TestClient


def test_register_user(client: TestClient, test_user):
    """Test user registration"""
    response = client.post("/api/auth/register", json=test_user)
    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data
    assert data["username"] == test_user["username"]


def test_login_user(client: TestClient, test_user):
    """Test user login"""
    # First register user
    client.post("/api/auth/register", json=test_user)

    # Then login
    login_data = {
        "username": test_user["username"],
        "password": test_user["password"]
    }
    response = client.post("/api/auth/login", data=login_data)
    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data


def test_invalid_login(client: TestClient):
    """Test invalid login"""
    login_data = {
        "username": "nonexistent",
        "password": "wrongpassword"
    }
    response = client.post("/api/auth/login", data=login_data)
    assert response.status_code == 401
''')

    # ==========================================
    # SCRIPTS
    # ==========================================

    scripts_dir = f"{project_root}/scripts"

    create_file(f"{scripts_dir}/init_db.py", '''#!/usr/bin/env python3
"""
Initialize database with default data
"""

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
''')

    create_file(f"{scripts_dir}/backup_db.py", '''#!/usr/bin/env python3
"""
Database backup script
"""

import os
import shutil
import datetime
from pathlib import Path

def backup_database():
    """Create database backup"""

    # Source database
    db_path = "emberframe.db"

    if not os.path.exists(db_path):
        print("❌ Database file not found")
        return

    # Create backups directory
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)

    # Generate backup filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"emberframe_backup_{timestamp}.db"
    backup_path = backup_dir / backup_filename

    # Copy database
    try:
        shutil.copy2(db_path, backup_path)
        print(f"✅ Database backed up to: {backup_path}")

        # Cleanup old backups (keep last 10)
        backups = sorted(backup_dir.glob("emberframe_backup_*.db"))
        if len(backups) > 10:
            for old_backup in backups[:-10]:
                old_backup.unlink()
                print(f"🗑️ Removed old backup: {old_backup}")

    except Exception as e:
        print(f"❌ Backup failed: {e}")

if __name__ == "__main__":
    backup_database()
''')

    # ==========================================
    # FRONTEND STRUCTURE
    # ==========================================

    # Basic frontend files
    create_file(f"{project_root}/static/css/main.css", '''/* EmberFrame V2 - Main Styles */

:root {
    --primary-color: #667eea;
    --secondary-color: #764ba2;
    --background-color: #0a0a0f;
    --text-color: #ffffff;
    --border-color: #333;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background: var(--background-color);
    color: var(--text-color);
    height: 100vh;
    overflow: hidden;
}

/* Desktop Environment Styles */
.desktop {
    height: 100vh;
    background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
    position: relative;
}

.taskbar {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    height: 60px;
    background: rgba(0, 0, 0, 0.8);
    backdrop-filter: blur(10px);
    border-top: 1px solid var(--border-color);
    display: flex;
    align-items: center;
    padding: 0 20px;
    z-index: 1000;
}

.window {
    position: absolute;
    background: white;
    border-radius: 8px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
    min-width: 400px;
    min-height: 300px;
    overflow: hidden;
}

.window-header {
    background: var(--primary-color);
    color: white;
    padding: 10px 15px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    cursor: move;
}

.window-content {
    padding: 20px;
    height: calc(100% - 50px);
    overflow: auto;
    background: white;
    color: #333;
}
''')

    create_file(f"{project_root}/static/js/core/desktop.js", '''/**
 * EmberFrame V2 Desktop Core
 */

class Desktop {
    constructor() {
        this.init();
    }

    init() {
        console.log('🔥 EmberFrame V2 Desktop Initialized');
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Desktop interaction events
        document.addEventListener('DOMContentLoaded', () => {
            this.onReady();
        });
    }

    onReady() {
        console.log('✅ Desktop ready');
    }
}

// Initialize desktop
window.desktop = new Desktop();
''')

    create_file(f"{project_root}/templates/index.html", '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EmberFrame V2 - Web Desktop</title>
    <link rel="stylesheet" href="/static/css/main.css">
</head>
<body>
    <div class="desktop" id="desktop">
        <div class="taskbar">
            <div class="start-button">🔥 EmberFrame</div>
        </div>
    </div>

    <script src="/static/js/core/desktop.js"></script>
</body>
</html>
''')

    # ==========================================
    # README
    # ==========================================

    create_file(f"{project_root}/README.md", '''# EmberFrame V2 - Modern Web Desktop Environment

A powerful, modern web-based desktop environment built with FastAPI, SQLAlchemy, and modern web technologies.

## Features

- 🚀 **Fast & Modern**: Built with FastAPI for high performance
- 🔐 **Secure**: JWT authentication, secure file handling
- 📁 **File Management**: Complete file system with upload/download
- 👥 **Multi-user**: Support for multiple users with admin panel
- 🎨 **Customizable**: Themeable interface with user preferences
- 📱 **Responsive**: Works on desktop and mobile devices
- 🔄 **Real-time**: WebSocket support for notifications
- 📊 **Analytics**: Built-in audit logging and system monitoring

## Quick Start

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd emberframe-v2
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements/development.txt
   ```

4. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Initialize database**
   ```bash
   python scripts/init_db.py
   ```

6. **Run the application**
   ```bash
   python main.py
   ```

7. **Access the application**
   - Open http://localhost:8000
   - Default admin: admin/admin123

### Production Deployment

#### Using Docker Compose

1. **Clone and configure**
   ```bash
   git clone <repository-url>
   cd emberframe-v2
   cp .env.example .env
   # Configure production settings in .env
   ```

2. **Deploy**
   ```bash
   docker-compose up -d
   ```

#### Manual Deployment

1. **Install dependencies**
   ```bash
   pip install -r requirements/production.txt
   ```

2. **Set up database** (PostgreSQL recommended)
   ```bash
   # Configure DATABASE_URL in .env
   alembic upgrade head
   python scripts/init_db.py
   ```

3. **Run with Gunicorn**
   ```bash
   gunicorn main:app -c gunicorn.conf.py
   ```

## Architecture

### Backend (FastAPI)
- **API Layer**: RESTful endpoints with automatic OpenAPI docs
- **Services Layer**: Business logic and data processing
- **Models Layer**: SQLAlchemy ORM models
- **Core Layer**: Configuration, security, dependencies

### Frontend (Vanilla JS)
- **Desktop Environment**: Window management system
- **Applications**: Modular apps (file manager, text editor, etc.)
- **Utilities**: Helper functions and UI components

### Background Tasks (Celery)
- File processing and thumbnails
- System maintenance and cleanup
- Scheduled reports and notifications

## Development

### Project Structure
```
emberframe-v2/
├── app/                    # Main application
│   ├── api/               # API endpoints
│   ├── core/              # Core functionality
│   ├── models/            # Database models
│   ├── services/          # Business logic
│   ├── schemas/           # Pydantic schemas
│   ├── tasks/             # Background tasks
│   └── utils/             # Utilities
├── static/                # Frontend assets
├── templates/             # HTML templates
├── tests/                 # Test suite
├── requirements/          # Dependencies
└── scripts/               # Utility scripts
```

### Running Tests
```bash
pytest
```

### Code Quality
```bash
# Format code
black .
isort .

# Lint code
flake8 .
mypy .

# Run all checks
pre-commit run --all-files
```

### Database Migrations
```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Configuration

### Environment Variables
- `DEBUG`: Enable debug mode
- `SECRET_KEY`: JWT signing key
- `DATABASE_URL`: Database connection string
- `REDIS_URL`: Redis connection for caching/tasks
- `UPLOAD_DIR`: File upload directory
- `MAX_FILE_SIZE`: Maximum upload size

### Features Configuration
- User registration: `ALLOW_REGISTRATION`
- Admin panel: `ENABLE_ADMIN_PANEL`
- File sharing: `ENABLE_PUBLIC_FILES`
- Background tasks: `ENABLE_CELERY`

## API Documentation

When running in development mode:
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

### Key Endpoints
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `GET /api/files/` - List files
- `POST /api/files/upload` - Upload files
- `GET /api/admin/users` - Admin: List users

## Security

- JWT-based authentication
- Password hashing with bcrypt
- File upload validation
- Path traversal protection
- CORS configuration
- Rate limiting (TODO)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

### Development Guidelines
- Follow PEP 8 style guide
- Write comprehensive tests
- Update documentation
- Use conventional commits

## License

MIT License - see LICENSE file for details.

## Support

- 📖 **Documentation**: See `docs/` folder
- 🐛 **Issues**: GitHub Issues
- 💬 **Discussions**: GitHub Discussions
- 📧 **Email**: support@emberframe.com

---

**EmberFrame V2** - The future of web desktop environments 🔥
''')

    print("\n" + "=" * 60)
    print("🎉 EmberFrame V2 project structure created successfully!")
    print("=" * 60)
    print(f"📁 Project location: {os.path.abspath(project_root)}")
    print("\n📋 Next steps:")
    print("1. cd emberframe-v2")
    print("2. python -m venv venv")
    print("3. source venv/bin/activate  # On Windows: venv\\Scripts\\activate")
    print("4. pip install -r requirements/development.txt")
    print("5. cp .env.example .env")
    print("6. python scripts/init_db.py")
    print("7. python main.py")
    print("\n🌐 Access the application at: http://localhost:8000")
    print("👤 Default admin login: admin/admin123")
    print("\n🔥 EmberFrame V2 is ready for development!")


if __name__ == "__main__":
    generate_emberframe_v2()