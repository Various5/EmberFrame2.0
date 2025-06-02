"""
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
