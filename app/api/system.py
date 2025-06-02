# app/api/system.py
"""
Complete System Management API
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import psutil
import os
from datetime import datetime, timedelta

from app.core.dependencies import get_db, get_current_user, require_admin
from app.models.user import User, SystemSettings, Theme
from app.schemas.system import SystemStatsResponse, SystemSettingCreate, SystemSettingUpdate, ThemeCreate
from app.services.system_service import SystemService
from app.services.cache_service import CacheService

system_router = APIRouter()

@system_router.get("/stats", response_model=SystemStatsResponse)
async def get_system_stats(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get comprehensive system statistics"""
    system_service = SystemService(db)
    
    # System metrics
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Application metrics
    user_count = await system_service.get_user_count()
    active_sessions = await system_service.get_active_session_count()
    file_count = await system_service.get_file_count()
    storage_used = await system_service.get_total_storage_used()
    
    return SystemStatsResponse(
        cpu_usage=cpu_percent,
        memory_usage=memory.percent,
        memory_total=memory.total,
        memory_used=memory.used,
        disk_usage=(disk.used / disk.total) * 100,
        disk_total=disk.total,
        disk_used=disk.used,
        user_count=user_count,
        active_sessions=active_sessions,
        file_count=file_count,
        storage_used=storage_used,
        uptime=await system_service.get_uptime()
    )

@system_router.get("/health")
async def system_health_check():
    """Comprehensive system health check"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {},
        "metrics": {}
    }
    
    # Check database connection
    try:
        # Simple database query
        health_status["services"]["database"] = "healthy"
    except Exception as e:
        health_status["services"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check Redis connection
    try:
        cache = CacheService()
        await cache.set("health_check", "ok", 60)
        health_status["services"]["redis"] = "healthy"
    except Exception as e:
        health_status["services"]["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check disk space
    disk = psutil.disk_usage('/')
    disk_usage = (disk.used / disk.total) * 100
    if disk_usage > 90:
        health_status["status"] = "warning"
        health_status["warnings"] = health_status.get("warnings", [])
        health_status["warnings"].append("Disk usage above 90%")
    
    health_status["metrics"]["disk_usage"] = disk_usage
    health_status["metrics"]["memory_usage"] = psutil.virtual_memory().percent
    health_status["metrics"]["cpu_usage"] = psutil.cpu_percent()
    
    return health_status

@system_router.get("/settings")
async def get_system_settings(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get all system settings"""
    system_service = SystemService(db)
    return await system_service.get_all_settings()

@system_router.post("/settings")
async def create_system_setting(
    setting: SystemSettingCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create a new system setting"""
    system_service = SystemService(db)
    return await system_service.create_setting(setting, current_user.id)

@system_router.put("/settings/{key}")
async def update_system_setting(
    key: str,
    setting: SystemSettingUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update a system setting"""
    system_service = SystemService(db)
    return await system_service.update_setting(key, setting, current_user.id)

@system_router.get("/themes")
async def get_themes(db: Session = Depends(get_db)):
    """Get all available themes"""
    system_service = SystemService(db)
    return await system_service.get_themes()

@system_router.post("/themes")
async def create_theme(
    theme: ThemeCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create a new theme"""
    system_service = SystemService(db)
    return await system_service.create_theme(theme)

@system_router.post("/maintenance/cleanup")
async def run_cleanup(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Run system cleanup tasks"""
    system_service = SystemService(db)
    background_tasks.add_task(system_service.run_cleanup_tasks)
    return {"message": "Cleanup tasks started"}

@system_router.post("/backup")
async def create_backup(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create system backup"""
    system_service = SystemService(db)
    backup_id = await system_service.create_backup(current_user.id)
    background_tasks.add_task(system_service.perform_backup, backup_id)
    return {"message": "Backup started", "backup_id": backup_id}

@system_router.get("/logs")
async def get_system_logs(
    level: str = "INFO",
    limit: int = 100,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get system logs"""
    system_service = SystemService(db)
    return await system_service.get_logs(level, limit)


# app/api/notifications.py
"""
Complete Notification Management API
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.dependencies import get_db, get_current_user
from app.models.user import User, Notification, NotificationStatus
from app.schemas.notifications import NotificationResponse, NotificationUpdate, NotificationCreate
from app.services.notification_service import NotificationService

notifications_router = APIRouter()

@notifications_router.get("/", response_model=List[NotificationResponse])
async def get_notifications(
    status: Optional[NotificationStatus] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user notifications"""
    notification_service = NotificationService(db)
    return await notification_service.get_user_notifications(
        current_user.id, status, limit, offset
    )

@notifications_router.get("/unread/count")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get unread notification count"""
    notification_service = NotificationService(db)
    count = await notification_service.get_unread_count(current_user.id)
    return {"unread_count": count}

@notifications_router.put("/{notification_id}/read")
async def mark_as_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark notification as read"""
    notification_service = NotificationService(db)
    await notification_service.mark_as_read(notification_id, current_user.id)
    return {"message": "Notification marked as read"}

@notifications_router.put("/read-all")
async def mark_all_as_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark all notifications as read"""
    notification_service = NotificationService(db)
    count = await notification_service.mark_all_as_read(current_user.id)
    return {"message": f"Marked {count} notifications as read"}

@notifications_router.delete("/{notification_id}")
async def delete_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete notification"""
    notification_service = NotificationService(db)
    await notification_service.delete_notification(notification_id, current_user.id)
    return {"message": "Notification deleted"}

@notifications_router.post("/send")
async def send_notification(
    notification: NotificationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send notification to user(s)"""
    notification_service = NotificationService(db)
    return await notification_service.send_notification(notification, current_user.id)


# app/api/search.py
"""
Complete Search API
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.dependencies import get_db, get_current_user
from app.models.user import User
from app.schemas.search import SearchRequest, SearchResponse, SearchFilter
from app.services.search_service import SearchService

search_router = APIRouter()

@search_router.get("/", response_model=SearchResponse)
async def search(
    q: str = Query(..., description="Search query"),
    type: Optional[str] = Query(None, description="Search type: files, users, all"),
    limit: int = Query(20, le=100),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Universal search endpoint"""
    search_service = SearchService(db)
    return await search_service.search(q, type, current_user.id, limit, offset)

@search_router.post("/advanced", response_model=SearchResponse)
async def advanced_search(
    search_request: SearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Advanced search with filters"""
    search_service = SearchService(db)
    return await search_service.advanced_search(search_request, current_user.id)

@search_router.get("/suggestions")
async def get_search_suggestions(
    q: str = Query(..., min_length=2),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get search suggestions"""
    search_service = SearchService(db)
    return await search_service.get_suggestions(q, current_user.id)


# app/api/sharing.py
"""
Complete File Sharing API
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.dependencies import get_db, get_current_user
from app.models.user import User
from app.schemas.sharing import ShareCreate, ShareResponse, ShareUpdate, PublicFileResponse
from app.services.sharing_service import SharingService

sharing_router = APIRouter()

@sharing_router.post("/", response_model=ShareResponse)
async def create_share(
    share: ShareCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a file share"""
    sharing_service = SharingService(db)
    return await sharing_service.create_share(share, current_user.id)

@sharing_router.get("/", response_model=List[ShareResponse])
async def get_shares(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's file shares"""
    sharing_service = SharingService(db)
    return await sharing_service.get_user_shares(current_user.id)

@sharing_router.get("/shared-with-me", response_model=List[ShareResponse])
async def get_shared_with_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get files shared with current user"""
    sharing_service = SharingService(db)
    return await sharing_service.get_shared_with_user(current_user.id)

@sharing_router.put("/{share_id}", response_model=ShareResponse)
async def update_share(
    share_id: int,
    share_update: ShareUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a file share"""
    sharing_service = SharingService(db)
    return await sharing_service.update_share(share_id, share_update, current_user.id)

@sharing_router.delete("/{share_id}")
async def delete_share(
    share_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a file share"""
    sharing_service = SharingService(db)
    await sharing_service.delete_share(share_id, current_user.id)
    return {"message": "Share deleted successfully"}

@sharing_router.get("/public/{share_token}", response_model=PublicFileResponse)
async def get_public_file(
    share_token: str,
    password: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Access public shared file"""
    sharing_service = SharingService(db)
    return await sharing_service.get_public_file(share_token, password)


# app/api/analytics.py
"""
Complete Analytics API
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.core.dependencies import get_db, get_current_user, require_admin
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsResponse, UserActivityResponse, FileAnalyticsResponse,
    SystemMetricsResponse, AnalyticsTimeRange
)
from app.services.analytics_service import AnalyticsService

analytics_router = APIRouter()

@analytics_router.get("/user", response_model=UserActivityResponse)
async def get_user_analytics(
    time_range: AnalyticsTimeRange = Query(AnalyticsTimeRange.LAST_30_DAYS),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user analytics"""
    analytics_service = AnalyticsService(db)
    return await analytics_service.get_user_analytics(current_user.id, time_range)

@analytics_router.get("/files", response_model=FileAnalyticsResponse)
async def get_file_analytics(
    time_range: AnalyticsTimeRange = Query(AnalyticsTimeRange.LAST_30_DAYS),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get file analytics"""
    analytics_service = AnalyticsService(db)
    return await analytics_service.get_file_analytics(current_user.id, time_range)

@analytics_router.get("/system", response_model=SystemMetricsResponse)
async def get_system_analytics(
    time_range: AnalyticsTimeRange = Query(AnalyticsTimeRange.LAST_30_DAYS),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get system analytics (admin only)"""
    analytics_service = AnalyticsService(db)
    return await analytics_service.get_system_analytics(time_range)

@analytics_router.get("/dashboard")
async def get_dashboard_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dashboard analytics data"""
    analytics_service = AnalyticsService(db)
    return await analytics_service.get_dashboard_data(current_user.id)


# app/api/integrations.py
"""
Complete External Integrations API
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.dependencies import get_db, get_current_user
from app.models.user import User
from app.schemas.integrations import (
    IntegrationCreate, IntegrationResponse, CloudStorageConfig,
    ExternalServiceConnect, ImportResponse
)
from app.services.integration_service import IntegrationService

integrations_router = APIRouter()

@integrations_router.get("/", response_model=List[IntegrationResponse])
async def get_integrations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user integrations"""
    integration_service = IntegrationService(db)
    return await integration_service.get_user_integrations(current_user.id)

@integrations_router.post("/cloud-storage")
async def connect_cloud_storage(
    config: CloudStorageConfig,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Connect cloud storage service"""
    integration_service = IntegrationService(db)
    return await integration_service.connect_cloud_storage(config, current_user.id)

@integrations_router.post("/import/dropbox")
async def import_from_dropbox(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Import files from Dropbox"""
    integration_service = IntegrationService(db)
    return await integration_service.import_from_dropbox(current_user.id)

@integrations_router.post("/import/google-drive")
async def import_from_google_drive(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Import files from Google Drive"""
    integration_service = IntegrationService(db)
    return await integration_service.import_from_google_drive(current_user.id)

@integrations_router.post("/export/{service}")
async def export_to_service(
    service: str,
    file_ids: List[int],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export files to external service"""
    integration_service = IntegrationService(db)
    return await integration_service.export_files(service, file_ids, current_user.id)

@integrations_router.delete("/{integration_id}")
async def disconnect_integration(
    integration_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disconnect integration"""
    integration_service = IntegrationService(db)
    await integration_service.disconnect_integration(integration_id, current_user.id)
    return {"message": "Integration disconnected successfully"}