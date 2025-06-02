"""
Enhanced database models with improved relationships and features
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, BigInteger, ForeignKey, JSON, Float, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from enum import Enum
import json

from app.core.database import Base


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"


class NotificationStatus(str, Enum):
    UNREAD = "unread"
    READ = "read"
    ARCHIVED = "archived"


class SessionStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


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
    bio = Column(Text)

    # Permissions and status
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)  # Backward compatibility

    # Storage and quotas
    storage_quota = Column(BigInteger, default=1024*1024*1024)  # 1GB default
    storage_used = Column(BigInteger, default=0)
    file_count_limit = Column(Integer, default=10000)

    # Preferences and settings
    preferences = Column(JSON, default=dict)
    theme = Column(String(50), default="ember-blue")
    language = Column(String(10), default="en")
    timezone = Column(String(50), default="UTC")

    # Security settings
    two_factor_enabled = Column(Boolean, default=False)
    two_factor_secret = Column(String(32))
    password_changed_at = Column(DateTime(timezone=True))
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True))

    # Activity tracking
    last_login = Column(DateTime(timezone=True))
    last_activity = Column(DateTime(timezone=True))
    login_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True))  # Soft delete

    # Relationships
    files = relationship("File", back_populates="owner", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    shared_files = relationship("FileShare", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.username}>"

    @hybrid_property
    def full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username

    @hybrid_property
    def storage_usage_percent(self):
        if self.storage_quota > 0:
            return (self.storage_used / self.storage_quota) * 100
        return 0

    @hybrid_property
    def is_locked(self):
        if self.locked_until:
            return func.now() < self.locked_until
        return False

    def get_preference(self, key: str, default=None):
        """Get user preference by key"""
        if self.preferences:
            return self.preferences.get(key, default)
        return default

    def set_preference(self, key: str, value):
        """Set user preference"""
        if not self.preferences:
            self.preferences = {}
        self.preferences[key] = value


class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    original_name = Column(String(255), nullable=False)
    path = Column(String(500), nullable=False, index=True)
    physical_path = Column(String(500), nullable=False)

    # File info
    size = Column(BigInteger, default=0)
    mime_type = Column(String(100))
    file_type = Column(String(50), index=True)  # document, image, video, etc.
    checksum = Column(String(64), index=True)  # SHA-256

    # Extended metadata
    width = Column(Integer)  # For images/videos
    height = Column(Integer)  # For images/videos
    duration = Column(Float)  # For audio/video files
    encoding = Column(String(50))  # File encoding

    # Content and organization
    description = Column(Text)
    tags = Column(JSON)  # Array of tags
    file_metadata = Column(JSON)  # Additional metadata (renamed from 'metadata')

    # Permissions and sharing
    is_public = Column(Boolean, default=False, index=True)
    is_deleted = Column(Boolean, default=False, index=True)
    is_favorite = Column(Boolean, default=False)

    # Versioning
    version = Column(Integer, default=1)
    parent_file_id = Column(Integer, ForeignKey("files.id"))

    # Security
    encrypted = Column(Boolean, default=False)
    encryption_key = Column(String(256))  # Encrypted with master key

    # Usage tracking
    download_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)

    # Owner
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    accessed_at = Column(DateTime(timezone=True))
    deleted_at = Column(DateTime(timezone=True))  # Soft delete

    # Relationships
    owner = relationship("User", back_populates="files")
    parent_file = relationship("File", remote_side=[id], backref="versions")
    shares = relationship("FileShare", back_populates="file", cascade="all, delete-orphan")
    comments = relationship("FileComment", back_populates="file", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<File {self.name}>"

    @hybrid_property
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

    @hybrid_property
    def is_image(self):
        return self.file_type == 'image'

    @hybrid_property
    def is_video(self):
        return self.file_type == 'video'

    @hybrid_property
    def is_audio(self):
        return self.file_type == 'audio'

    def get_tag_list(self):
        """Get tags as list"""
        if self.tags:
            return self.tags if isinstance(self.tags, list) else []
        return []

    def add_tag(self, tag: str):
        """Add tag to file"""
        tags = self.get_tag_list()
        if tag not in tags:
            tags.append(tag)
            self.tags = tags

    def remove_tag(self, tag: str):
        """Remove tag from file"""
        tags = self.get_tag_list()
        if tag in tags:
            tags.remove(tag)
            self.tags = tags


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), unique=True, index=True, nullable=False)

    # User
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Session info
    ip_address = Column(String(45), index=True)  # IPv6 compatible
    user_agent = Column(Text)
    device_info = Column(JSON)  # Browser, OS, device type
    location = Column(JSON)  # Geolocation data

    # Status and security
    status = Column(SQLEnum(SessionStatus), default=SessionStatus.ACTIVE, nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    is_mobile = Column(Boolean, default=False)

    # Security flags
    is_suspicious = Column(Boolean, default=False)
    login_method = Column(String(50))  # password, 2fa, api_key

    # Activity tracking
    page_views = Column(Integer, default=0)
    api_calls = Column(Integer, default=0)
    last_activity = Column(DateTime(timezone=True), server_default=func.now())

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))
    revoked_at = Column(DateTime(timezone=True))

    # Relationships
    user = relationship("User", back_populates="sessions")

    def __repr__(self):
        return f"<Session {self.session_id}>"

    @hybrid_property
    def is_expired(self):
        if self.expires_at:
            return func.now() > self.expires_at
        return False


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    # User (optional - can be system actions)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    # Action details
    action = Column(String(100), nullable=False, index=True)  # login, file_upload, user_create, etc.
    resource_type = Column(String(50), index=True)  # user, file, system, etc.
    resource_id = Column(String(100), index=True)  # ID of affected resource

    # Context
    ip_address = Column(String(45))
    user_agent = Column(Text)
    session_id = Column(String(255))
    request_id = Column(String(100))  # For request tracing

    # Additional data
    details = Column(JSON)  # Additional details as JSON
    old_values = Column(JSON)  # Previous values for updates
    new_values = Column(JSON)  # New values for updates

    # Result and severity
    success = Column(Boolean, default=True)
    severity = Column(String(10), default="info")  # info, warning, error, critical
    message = Column(Text)
    error_code = Column(String(50))

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog {self.action}>"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)

    # Target user
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Notification content
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String(50), default="info", index=True)  # info, success, warning, error

    # Status and visibility
    status = Column(SQLEnum(NotificationStatus), default=NotificationStatus.UNREAD, nullable=False, index=True)
    is_important = Column(Boolean, default=False)

    # Action and linking
    action_url = Column(String(500))  # URL to navigate to
    action_text = Column(String(100))  # Text for action button
    related_resource_type = Column(String(50))  # file, user, system
    related_resource_id = Column(String(100))

    # Metadata
    data = Column(JSON)  # Additional data

    # Delivery tracking
    sent_at = Column(DateTime(timezone=True))
    read_at = Column(DateTime(timezone=True))
    archived_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="notifications")

    def __repr__(self):
        return f"<Notification {self.title}>"

    def mark_as_read(self):
        """Mark notification as read"""
        self.status = NotificationStatus.READ
        self.read_at = func.now()

    def archive(self):
        """Archive notification"""
        self.status = NotificationStatus.ARCHIVED
        self.archived_at = func.now()


class FileShare(Base):
    __tablename__ = "file_shares"

    id = Column(Integer, primary_key=True, index=True)

    # File and user
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    shared_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Share settings
    permission = Column(String(20), default="read")  # read, write, admin
    is_public = Column(Boolean, default=False)
    password_protected = Column(Boolean, default=False)
    password_hash = Column(String(255))

    # Access tracking
    access_count = Column(Integer, default=0)
    last_accessed = Column(DateTime(timezone=True))

    # Expiration
    expires_at = Column(DateTime(timezone=True))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    file = relationship("File", back_populates="shares")
    user = relationship("User", back_populates="shared_files", foreign_keys=[user_id])
    shared_by = relationship("User", foreign_keys=[shared_by_id])

    def __repr__(self):
        return f"<FileShare {self.file_id} -> {self.user_id}>"

    @hybrid_property
    def is_expired(self):
        if self.expires_at:
            return func.now() > self.expires_at
        return False


class FileComment(Base):
    __tablename__ = "file_comments"

    id = Column(Integer, primary_key=True, index=True)

    # File and user
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Comment content
    comment = Column(Text, nullable=False)
    is_resolved = Column(Boolean, default=False)

    # Threading
    parent_comment_id = Column(Integer, ForeignKey("file_comments.id"))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    file = relationship("File", back_populates="comments")
    user = relationship("User")
    parent_comment = relationship("FileComment", remote_side=[id], backref="replies")

    def __repr__(self):
        return f"<FileComment {self.id}>"


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)

    # User
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Key details
    name = Column(String(100), nullable=False)  # Human-readable name
    key_hash = Column(String(255), nullable=False, unique=True, index=True)  # Hashed API key
    key_prefix = Column(String(10), nullable=False)  # First few chars for identification

    # Permissions and scope
    scopes = Column(JSON)  # List of allowed scopes/permissions
    is_active = Column(Boolean, default=True, index=True)

    # Usage tracking
    last_used = Column(DateTime(timezone=True))
    usage_count = Column(Integer, default=0)

    # Expiration
    expires_at = Column(DateTime(timezone=True))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="api_keys")

    def __repr__(self):
        return f"<APIKey {self.name}>"

    @hybrid_property
    def is_expired(self):
        if self.expires_at:
            return func.now() > self.expires_at
        return False


class SystemSettings(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)

    # Setting details
    key = Column(String(100), nullable=False, unique=True, index=True)
    value = Column(JSON)  # Can store any JSON-serializable value
    data_type = Column(String(20), default="string")  # string, int, float, bool, json

    # Metadata
    description = Column(Text)
    is_public = Column(Boolean, default=False)  # Can be read by non-admin users
    is_editable = Column(Boolean, default=True)  # Can be modified via API

    # Validation
    validation_rules = Column(JSON)  # Rules for validating values

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(Integer, ForeignKey("users.id"))

    # Relationships
    updated_by_user = relationship("User")

    def __repr__(self):
        return f"<SystemSettings {self.key}>"

    def get_typed_value(self):
        """Get value with proper type conversion"""
        if self.data_type == "int":
            return int(self.value)
        elif self.data_type == "float":
            return float(self.value)
        elif self.data_type == "bool":
            return bool(self.value)
        elif self.data_type == "json":
            return self.value
        else:
            return str(self.value)


class Theme(Base):
    __tablename__ = "themes"

    id = Column(Integer, primary_key=True, index=True)

    # Theme details
    name = Column(String(100), nullable=False, unique=True, index=True)
    display_name = Column(String(100), nullable=False)
    description = Column(Text)

    # Theme data
    css_variables = Column(JSON, nullable=False)  # CSS custom properties
    is_dark = Column(Boolean, default=False)
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    # Metadata
    author = Column(String(100))
    version = Column(String(20), default="1.0.0")
    preview_image = Column(String(255))  # URL to preview image

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Theme {self.name}>"