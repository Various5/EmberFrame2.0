"""
Application configuration management
"""

from pydantic_settings import BaseSettings
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

    # Security settings
    RATE_LIMIT_ENABLED: bool = True
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION: int = 900  # 15 minutes

    # Advanced security
    ENABLE_2FA: bool = False
    SESSION_SECURITY: bool = True
    IP_WHITELIST: List[str] = []

    # Performance
    CACHE_TTL: int = 3600
    MAX_WORKERS: int = 4

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()