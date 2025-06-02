# app/schemas/search.py
"""
Search API Schemas
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class SearchType(str, Enum):
    ALL = "all"
    FILES = "files"
    USERS = "users"

class SearchFilter(BaseModel):
    file_type: Optional[str] = None
    size_min: Optional[int] = None
    size_max: Optional[int] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    tags: Optional[List[str]] = None

class SearchRequest(BaseModel):
    query: str
    search_type: SearchType = SearchType.ALL
    filters: Optional[SearchFilter] = None
    limit: int = 20
    offset: int = 0

class SearchResult(BaseModel):
    id: int
    name: str
    type: str
    path: Optional[str] = None
    size: Optional[int] = None
    created_at: datetime
    relevance_score: float

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    total: int
    limit: int
    offset: int
    took_ms: Optional[float] = None

# app/schemas/sharing.py
"""
File Sharing Schemas
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ShareCreate(BaseModel):
    file_id: int
    user_id: Optional[int] = None  # None for public shares
    permission: str = "read"  # read, write, admin
    is_public: bool = False
    password: Optional[str] = None
    expires_at: Optional[datetime] = None

class ShareUpdate(BaseModel):
    permission: Optional[str] = None
    is_public: Optional[bool] = None
    password: Optional[str] = None
    expires_at: Optional[datetime] = None

class ShareResponse(BaseModel):
    id: int
    file_id: int
    user_id: Optional[int]
    shared_by_id: int
    permission: str
    is_public: bool
    password_protected: bool
    share_token: str
    access_count: int
    expires_at: Optional[datetime]
    created_at: datetime
    last_accessed: Optional[datetime]

    class Config:
        orm_mode = True

class PublicFileResponse(BaseModel):
    file: Dict[str, Any]
    share: Dict[str, Any]

# app/schemas/notifications.py
"""
Notification Schemas
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class NotificationStatus(str, Enum):
    UNREAD = "unread"
    READ = "read"
    ARCHIVED = "archived"

class NotificationType(str, Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"

class NotificationCreate(BaseModel):
    user_id: int
    title: str
    message: str
    type: NotificationType = NotificationType.INFO
    is_important: bool = False
    action_url: Optional[str] = None
    action_text: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None

class NotificationUpdate(BaseModel):
    status: Optional[NotificationStatus] = None

class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    type: str
    status: NotificationStatus
    is_important: bool
    action_url: Optional[str]
    action_text: Optional[str]
    data: Optional[Dict[str, Any]]
    created_at: datetime
    read_at: Optional[datetime]

    class Config:
        orm_mode = True

class NotificationPreferences(BaseModel):
    email_notifications: bool = True
    push_notifications: bool = True
    desktop_notifications: bool = True
    notification_types: Dict[str, bool] = {
        "file_shared": True,
        "file_commented": True,
        "storage_warning": True,
        "security_alert": True
    }

class BulkNotificationAction(BaseModel):
    action: str  # mark_read, mark_unread, archive, delete
    notification_ids: Optional[List[int]] = None
    filter_status: Optional[NotificationStatus] = None

# app/schemas/analytics.py
"""
Analytics Schemas
"""

from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime
from enum import Enum

class AnalyticsTimeRange(str, Enum):
    LAST_7_DAYS = "7d"
    LAST_30_DAYS = "30d"
    LAST_90_DAYS = "90d"
    LAST_YEAR = "1y"

class DailyActivity(BaseModel):
    date: str
    actions: int

class FileTypeStats(BaseModel):
    type: str
    count: int
    total_size: int

class PopularFile(BaseModel):
    name: str
    views: int
    downloads: int

class UploadTrend(BaseModel):
    date: str
    uploads: int
    total_size: int

class UserActivityResponse(BaseModel):
    total_files: int
    files_in_period: int
    storage_used: int
    daily_activity: List[DailyActivity]
    file_types: List[FileTypeStats]

class FileAnalyticsResponse(BaseModel):
    popular_files: List[PopularFile]
    upload_trends: List[UploadTrend]

class SystemMetricsResponse(BaseModel):
    total_users: int
    active_users: int
    total_files: int
    total_storage: int
    daily_registrations: List[Dict[str, Any]]
    system_activity: List[Dict[str, Any]]

class AnalyticsResponse(BaseModel):
    timeframe: AnalyticsTimeRange
    data: Dict[str, Any]
    generated_at: datetime

# app/schemas/integrations.py
"""
Integration Schemas
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class IntegrationType(str, Enum):
    CLOUD_STORAGE = "cloud_storage"
    EMAIL = "email"
    CALENDAR = "calendar"
    SOCIAL = "social"

class IntegrationStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    PENDING = "pending"

class CloudStorageProvider(str, Enum):
    DROPBOX = "dropbox"
    GOOGLE_DRIVE = "google_drive"
    ONEDRIVE = "onedrive"
    AWS_S3 = "aws_s3"

class IntegrationCreate(BaseModel):
    name: str
    type: IntegrationType
    provider: str
    config: Dict[str, Any]

class IntegrationResponse(BaseModel):
    id: int
    name: str
    type: IntegrationType
    provider: str
    status: IntegrationStatus
    connected_at: Optional[datetime]
    last_sync: Optional[datetime]
    sync_count: int
    config: Dict[str, Any]

    class Config:
        orm_mode = True

class CloudStorageConfig(BaseModel):
    provider: CloudStorageProvider
    access_token: str
    refresh_token: Optional[str] = None
    folder_path: Optional[str] = "/"
    auto_sync: bool = False

class ExternalServiceConnect(BaseModel):
    provider: str
    auth_code: str
    redirect_uri: str

class ImportResponse(BaseModel):
    imported_files: int
    skipped_files: int
    failed_files: int
    total_size: int
    import_id: str

# app/schemas/system.py
"""
System Management Schemas
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class SystemStatsResponse(BaseModel):
    cpu_usage: float
    memory_usage: float
    memory_total: int
    memory_used: int
    disk_usage: float
    disk_total: int
    disk_used: int
    user_count: int
    active_sessions: int
    file_count: int
    storage_used: int
    uptime: str

class SystemSettingCreate(BaseModel):
    key: str
    value: Any
    description: Optional[str] = None
    is_public: bool = False
    is_editable: bool = True

class SystemSettingUpdate(BaseModel):
    value: Optional[Any] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None
    is_editable: Optional[bool] = None

class SystemSettingResponse(BaseModel):
    id: int
    key: str
    value: Any
    data_type: str
    description: Optional[str]
    is_public: bool
    is_editable: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True

class ThemeCreate(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None
    css_variables: Dict[str, str]
    is_dark: bool = False
    author: Optional[str] = None
    version: str = "1.0.0"

class ThemeResponse(BaseModel):
    id: int
    name: str
    display_name: str
    description: Optional[str]
    css_variables: Dict[str, str]
    is_dark: bool
    is_default: bool
    is_active: bool
    author: Optional[str]
    version: str
    preview_image: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True

class BackupCreate(BaseModel):
    include_files: bool = True
    include_database: bool = True
    compress: bool = True
    encrypt: bool = False

class BackupResponse(BaseModel):
    id: str
    status: str
    size: Optional[int]
    created_at: datetime
    completed_at: Optional[datetime]
    download_url: Optional[str]

# app/schemas/auth_advanced.py
"""
Advanced Authentication Schemas
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class TwoFactorSetupResponse(BaseModel):
    secret: str
    qr_code: str
    backup_codes: List[str]

class TwoFactorVerifyRequest(BaseModel):
    code: str

class PasswordResetRequest(BaseModel):
    email: str

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

class SessionResponse(BaseModel):
    id: int
    session_id: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    device_info: Optional[Dict[str, Any]]
    is_current: bool
    last_activity: datetime
    created_at: datetime

    class Config:
        orm_mode = True

class SecuritySettingsResponse(BaseModel):
    two_factor_enabled: bool
    password_changed_at: Optional[datetime]
    last_login: Optional[datetime]
    failed_login_attempts: int
    is_locked: bool
    active_sessions_count: int

class SecuritySettingsUpdate(BaseModel):
    session_timeout: Optional[int] = None
    login_notifications: Optional[bool] = None
    security_emails: Optional[bool] = None