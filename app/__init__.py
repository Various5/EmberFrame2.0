# app/api/__init__.py
"""
Complete API Router Implementation
"""

from fastapi import APIRouter
from app.api.auth import auth_router
from app.api.users import users_router
from app.api.files import files_router
from app.api.admin import admin_router
from app.api.websocket import websocket_router
from app.api.search import search_router
from app.api.sharing import sharing_router
from app.api.analytics import analytics_router
from app.api.notifications import notifications_router
from app.api.system import system_router
from app.api.integrations import integrations_router

api_router = APIRouter()

# Include all routers
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(files_router, prefix="/files", tags=["Files"])
api_router.include_router(sharing_router, prefix="/sharing", tags=["Sharing"])
api_router.include_router(search_router, prefix="/search", tags=["Search"])
api_router.include_router(notifications_router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(system_router, prefix="/system", tags=["System"])
api_router.include_router(integrations_router, prefix="/integrations", tags=["Integrations"])
api_router.include_router(admin_router, prefix="/admin", tags=["Admin"])

# app/api/search.py
"""
Complete Search API Implementation
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from typing import List, Optional, Dict, Any
import re

from app.core.dependencies import get_db, get_current_user
from app.models.user import User, File
from app.schemas.search import SearchResponse, SearchResult, SearchFilter
from app.services.cache_service import CacheService

search_router = APIRouter()

class SearchService:
    def __init__(self, db: Session):
        self.db = db
        self.cache = CacheService()

    async def universal_search(
        self, 
        query: str, 
        user_id: int, 
        search_type: str = "all",
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Universal search across all content"""
        
        # Cache key for search results
        cache_key = f"search:{user_id}:{search_type}:{query}:{limit}:{offset}"
        
        # Check cache first
        cached_result = await self.cache.get_user_cache(user_id, cache_key)
        if cached_result:
            return cached_result

        results = {"files": [], "total": 0}
        
        if search_type in ["all", "files"]:
            file_results = await self._search_files(query, user_id, limit, offset)
            results["files"] = file_results["files"]
            results["total"] = file_results["total"]

        # Cache results for 5 minutes
        await self.cache.set_user_cache(user_id, cache_key, results, 300)
        
        return results

    async def _search_files(self, query: str, user_id: int, limit: int, offset: int) -> Dict[str, Any]:
        """Search files with advanced filtering"""
        
        # Build search query
        search_terms = query.lower().split()
        
        # Base query
        base_query = self.db.query(File).filter(
            and_(
                File.owner_id == user_id,
                File.is_deleted == False
            )
        )

        # Add search filters
        search_conditions = []
        for term in search_terms:
            term_condition = or_(
                func.lower(File.name).contains(term),
                func.lower(File.description).contains(term),
                func.lower(File.tags).contains(term)
            )
            search_conditions.append(term_condition)

        if search_conditions:
            base_query = base_query.filter(and_(*search_conditions))

        # Get total count
        total = base_query.count()

        # Get paginated results
        files = base_query.order_by(File.updated_at.desc()).offset(offset).limit(limit).all()

        file_results = []
        for file in files:
            file_results.append({
                "id": file.id,
                "name": file.name,
                "path": file.path,
                "size": file.size,
                "type": file.file_type,
                "mime_type": file.mime_type,
                "created_at": file.created_at,
                "updated_at": file.updated_at,
                "relevance_score": self._calculate_relevance(file, search_terms)
            })

        return {"files": file_results, "total": total}

    def _calculate_relevance(self, file: File, search_terms: List[str]) -> float:
        """Calculate search relevance score"""
        score = 0.0
        
        for term in search_terms:
            # Name match (highest weight)
            if term in file.name.lower():
                score += 10.0
            
            # Description match
            if file.description and term in file.description.lower():
                score += 5.0
            
            # Tag match
            if file.tags and term in str(file.tags).lower():
                score += 3.0

        return score

@search_router.get("/", response_model=SearchResponse)
async def search(
    q: str = Query(..., description="Search query"),
    type: str = Query("all", description="Search type: files, users, all"),
    limit: int = Query(20, le=100),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Universal search endpoint"""
    search_service = SearchService(db)
    results = await search_service.universal_search(q, current_user.id, type, limit, offset)
    
    return SearchResponse(
        query=q,
        results=results,
        total=results.get("total", 0),
        limit=limit,
        offset=offset
    )

@search_router.get("/suggestions")
async def get_search_suggestions(
    q: str = Query(..., min_length=2),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get search suggestions"""
    
    # Get recent file names for suggestions
    recent_files = db.query(File.name).filter(
        and_(
            File.owner_id == current_user.id,
            func.lower(File.name).contains(q.lower())
        )
    ).limit(10).all()
    
    suggestions = [file.name for file in recent_files]
    
    return {"suggestions": suggestions}

# app/api/sharing.py
"""
Complete File Sharing API Implementation
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import secrets
from datetime import datetime, timedelta

from app.core.dependencies import get_db, get_current_user
from app.models.user import User, File, FileShare
from app.schemas.sharing import ShareCreate, ShareResponse, ShareUpdate, PublicFileResponse
from app.core.security import get_password_hash, verify_password
from app.services.audit_service import AuditService

sharing_router = APIRouter()

class SharingService:
    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)

    async def create_share(self, share_data: ShareCreate, owner_id: int) -> FileShare:
        """Create a new file share"""
        
        # Verify file ownership
        file = self.db.query(File).filter(
            File.id == share_data.file_id,
            File.owner_id == owner_id
        ).first()
        
        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        # Generate share token
        share_token = secrets.token_urlsafe(32)
        
        # Create share record
        share = FileShare(
            file_id=share_data.file_id,
            user_id=share_data.user_id if share_data.user_id else None,
            shared_by_id=owner_id,
            permission=share_data.permission,
            is_public=share_data.is_public,
            password_protected=bool(share_data.password),
            password_hash=get_password_hash(share_data.password) if share_data.password else None,
            expires_at=share_data.expires_at,
            share_token=share_token
        )
        
        self.db.add(share)
        self.db.commit()
        self.db.refresh(share)
        
        # Log sharing activity
        await self.audit_service.log_action(
            "file_shared", "file", str(share_data.file_id),
            owner_id, details={
                "share_id": share.id,
                "permission": share_data.permission,
                "is_public": share_data.is_public
            }
        )
        
        return share

    async def get_user_shares(self, user_id: int) -> List[FileShare]:
        """Get all shares created by user"""
        return self.db.query(FileShare).filter(
            FileShare.shared_by_id == user_id
        ).all()

    async def get_shared_with_user(self, user_id: int) -> List[FileShare]:
        """Get all files shared with user"""
        return self.db.query(FileShare).filter(
            FileShare.user_id == user_id
        ).all()

    async def update_share(self, share_id: int, share_update: ShareUpdate, user_id: int) -> FileShare:
        """Update a file share"""
        share = self.db.query(FileShare).filter(
            FileShare.id == share_id,
            FileShare.shared_by_id == user_id
        ).first()
        
        if not share:
            raise HTTPException(status_code=404, detail="Share not found")

        # Update fields
        for field, value in share_update.dict(exclude_unset=True).items():
            if field == "password" and value:
                share.password_hash = get_password_hash(value)
                share.password_protected = True
            elif field == "password" and not value:
                share.password_hash = None
                share.password_protected = False
            else:
                setattr(share, field, value)

        self.db.commit()
        return share

    async def delete_share(self, share_id: int, user_id: int):
        """Delete a file share"""
        share = self.db.query(FileShare).filter(
            FileShare.id == share_id,
            FileShare.shared_by_id == user_id
        ).first()
        
        if not share:
            raise HTTPException(status_code=404, detail="Share not found")

        self.db.delete(share)
        self.db.commit()

    async def get_public_file(self, share_token: str, password: str = None) -> dict:
        """Access public shared file"""
        share = self.db.query(FileShare).filter(
            FileShare.share_token == share_token,
            FileShare.is_public == True
        ).first()
        
        if not share:
            raise HTTPException(status_code=404, detail="Share not found")

        # Check expiration
        if share.expires_at and datetime.utcnow() > share.expires_at:
            raise HTTPException(status_code=410, detail="Share has expired")

        # Check password if required
        if share.password_protected:
            if not password:
                raise HTTPException(status_code=401, detail="Password required")
            if not verify_password(password, share.password_hash):
                raise HTTPException(status_code=401, detail="Invalid password")

        # Update access count
        share.access_count += 1
        share.last_accessed = datetime.utcnow()
        self.db.commit()

        # Get file info
        file = self.db.query(File).filter(File.id == share.file_id).first()
        
        return {
            "file": {
                "id": file.id,
                "name": file.name,
                "size": file.size,
                "mime_type": file.mime_type,
                "file_type": file.file_type
            },
            "share": {
                "permission": share.permission,
                "access_count": share.access_count
            }
        }

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
Complete Analytics API Implementation
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Dict, Any
from datetime import datetime, timedelta
from enum import Enum

from app.core.dependencies import get_db, get_current_user, require_admin
from app.models.user import User, File, AuditLog, Session as UserSession
from app.schemas.analytics import (
    AnalyticsResponse, UserActivityResponse, FileAnalyticsResponse,
    SystemMetricsResponse, AnalyticsTimeRange
)

analytics_router = APIRouter()

class AnalyticsTimeRange(str, Enum):
    LAST_7_DAYS = "7d"
    LAST_30_DAYS = "30d"
    LAST_90_DAYS = "90d"
    LAST_YEAR = "1y"

class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def _get_date_range(self, time_range: AnalyticsTimeRange) -> tuple:
        """Get start and end dates for time range"""
        end_date = datetime.utcnow()
        
        if time_range == AnalyticsTimeRange.LAST_7_DAYS:
            start_date = end_date - timedelta(days=7)
        elif time_range == AnalyticsTimeRange.LAST_30_DAYS:
            start_date = end_date - timedelta(days=30)
        elif time_range == AnalyticsTimeRange.LAST_90_DAYS:
            start_date = end_date - timedelta(days=90)
        else:  # LAST_YEAR
            start_date = end_date - timedelta(days=365)
            
        return start_date, end_date

    async def get_user_analytics(self, user_id: int, time_range: AnalyticsTimeRange) -> Dict[str, Any]:
        """Get user activity analytics"""
        start_date, end_date = self._get_date_range(time_range)
        
        # File statistics
        total_files = self.db.query(func.count(File.id)).filter(
            and_(File.owner_id == user_id, File.is_deleted == False)
        ).scalar()
        
        files_in_period = self.db.query(func.count(File.id)).filter(
            and_(
                File.owner_id == user_id,
                File.created_at >= start_date,
                File.created_at <= end_date
            )
        ).scalar()
        
        # Storage usage
        storage_used = self.db.query(func.sum(File.size)).filter(
            and_(File.owner_id == user_id, File.is_deleted == False)
        ).scalar() or 0
        
        # Activity by day
        daily_activity = self.db.query(
            func.date(AuditLog.created_at).label('date'),
            func.count(AuditLog.id).label('actions')
        ).filter(
            and_(
                AuditLog.user_id == user_id,
                AuditLog.created_at >= start_date,
                AuditLog.created_at <= end_date
            )
        ).group_by(func.date(AuditLog.created_at)).all()
        
        # File types distribution
        file_types = self.db.query(
            File.file_type,
            func.count(File.id).label('count'),
            func.sum(File.size).label('total_size')
        ).filter(
            and_(File.owner_id == user_id, File.is_deleted == False)
        ).group_by(File.file_type).all()
        
        return {
            "total_files": total_files,
            "files_in_period": files_in_period,
            "storage_used": storage_used,
            "daily_activity": [
                {"date": str(row.date), "actions": row.actions}
                for row in daily_activity
            ],
            "file_types": [
                {
                    "type": row.file_type,
                    "count": row.count,
                    "total_size": row.total_size or 0
                }
                for row in file_types
            ]
        }

    async def get_file_analytics(self, user_id: int, time_range: AnalyticsTimeRange) -> Dict[str, Any]:
        """Get file-specific analytics"""
        start_date, end_date = self._get_date_range(time_range)
        
        # Most accessed files
        popular_files = self.db.query(
            File.name,
            File.view_count,
            File.download_count
        ).filter(
            and_(File.owner_id == user_id, File.is_deleted == False)
        ).order_by(File.view_count.desc()).limit(10).all()
        
        # File upload trends
        upload_trends = self.db.query(
            func.date(File.created_at).label('date'),
            func.count(File.id).label('uploads'),
            func.sum(File.size).label('total_size')
        ).filter(
            and_(
                File.owner_id == user_id,
                File.created_at >= start_date,
                File.created_at <= end_date
            )
        ).group_by(func.date(File.created_at)).all()
        
        return {
            "popular_files": [
                {
                    "name": row.name,
                    "views": row.view_count or 0,
                    "downloads": row.download_count or 0
                }
                for row in popular_files
            ],
            "upload_trends": [
                {
                    "date": str(row.date),
                    "uploads": row.uploads,
                    "total_size": row.total_size or 0
                }
                for row in upload_trends
            ]
        }

    async def get_system_analytics(self, time_range: AnalyticsTimeRange) -> Dict[str, Any]:
        """Get system-wide analytics (admin only)"""
        start_date, end_date = self._get_date_range(time_range)
        
        # User statistics
        total_users = self.db.query(func.count(User.id)).scalar()
        active_users = self.db.query(func.count(User.id)).filter(
            User.last_activity >= start_date
        ).scalar()
        
        # File statistics
        total_files = self.db.query(func.count(File.id)).filter(
            File.is_deleted == False
        ).scalar()
        
        total_storage = self.db.query(func.sum(File.size)).filter(
            File.is_deleted == False
        ).scalar() or 0
        
        # Daily registrations
        daily_registrations = self.db.query(
            func.date(User.created_at).label('date'),
            func.count(User.id).label('registrations')
        ).filter(
            and_(
                User.created_at >= start_date,
                User.created_at <= end_date
            )
        ).group_by(func.date(User.created_at)).all()
        
        # System activity
        system_activity = self.db.query(
            func.date(AuditLog.created_at).label('date'),
            func.count(AuditLog.id).label('total_actions')
        ).filter(
            and_(
                AuditLog.created_at >= start_date,
                AuditLog.created_at <= end_date
            )
        ).group_by(func.date(AuditLog.created_at)).all()
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "total_files": total_files,
            "total_storage": total_storage,
            "daily_registrations": [
                {"date": str(row.date), "registrations": row.registrations}
                for row in daily_registrations
            ],
            "system_activity": [
                {"date": str(row.date), "actions": row.total_actions}
                for row in system_activity
            ]
        }

    async def get_dashboard_data(self, user_id: int) -> Dict[str, Any]:
        """Get dashboard overview data"""
        # Recent activity (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        recent_files = self.db.query(File).filter(
            and_(
                File.owner_id == user_id,
                File.created_at >= week_ago,
                File.is_deleted == False
            )
        ).count()
        
        recent_activity = self.db.query(AuditLog).filter(
            and_(
                AuditLog.user_id == user_id,
                AuditLog.created_at >= week_ago
            )
        ).count()
        
        # Storage info
        user = self.db.query(User).filter(User.id == user_id).first()
        
        return {
            "recent_files": recent_files,
            "recent_activity": recent_activity,
            "storage_used": user.storage_used,
            "storage_quota": user.storage_quota,
            "storage_percentage": (user.storage_used / user.storage_quota * 100) if user.storage_quota > 0 else 0
        }

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

# app/api/notifications.py
"""
Complete Notification Management API
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
from datetime import datetime

from app.core.dependencies import get_db, get_current_user
from app.models.user import User, Notification, NotificationStatus
from app.schemas.notifications import (
    NotificationResponse, NotificationUpdate, NotificationCreate,
    NotificationPreferences, BulkNotificationAction
)
from app.services.notification_service import NotificationService, NotificationType

notifications_router = APIRouter()

class NotificationManager:
    def __init__(self, db: Session):
        self.db = db
        self.notification_service = NotificationService()

    async def get_user_notifications(
        self, 
        user_id: int, 
        status: Optional[NotificationStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Notification]:
        """Get user notifications with filtering"""
        
        query = self.db.query(Notification).filter(Notification.user_id == user_id)
        
        if status:
            query = query.filter(Notification.status == status)
            
        return query.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()

    async def get_unread_count(self, user_id: int) -> int:
        """Get count of unread notifications"""
        return self.db.query(Notification).filter(
            and_(
                Notification.user_id == user_id,
                Notification.status == NotificationStatus.UNREAD
            )
        ).count()

    async def mark_as_read(self, notification_id: int, user_id: int):
        """Mark notification as read"""
        notification = self.db.query(Notification).filter(
            and_(
                Notification.id == notification_id,
                Notification.user_id == user_id
            )
        ).first()
        
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")
            
        notification.mark_as_read()
        self.db.commit()

    async def mark_all_as_read(self, user_id: int) -> int:
        """Mark all notifications as read"""
        updated = self.db.query(Notification).filter(
            and_(
                Notification.user_id == user_id,
                Notification.status == NotificationStatus.UNREAD
            )
        ).update({
            "status": NotificationStatus.READ,
            "read_at": datetime.utcnow()
        })
        
        self.db.commit()
        return updated

    async def delete_notification(self, notification_id: int, user_id: int):
        """Delete notification"""
        notification = self.db.query(Notification).filter(
            and_(
                Notification.id == notification_id,
                Notification.user_id == user_id
            )
        ).first()
        
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")
            
        self.db.delete(notification)
        self.db.commit()

    async def send_notification(self, notification_data: NotificationCreate, sender_id: int) -> Notification:
        """Send notification to user(s)"""
        
        # Create notification record
        notification = Notification(
            user_id=notification_data.user_id,
            title=notification_data.title,
            message=notification_data.message,
            notification_type=notification_data.type,
            is_important=notification_data.is_important,
            action_url=notification_data.action_url,
            action_text=notification_data.action_text,
            data=notification_data.data,
            expires_at=notification_data.expires_at
        )
        
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        
        # Send real-time notification via WebSocket
        await self.notification_service.send_notification(
            notification_data.user_id,
            notification_data.title,
            notification_data.message,
            NotificationType(notification_data.type),
            notification_data.data
        )
        
        return notification

    async def bulk_action(self, user_id: int, action: BulkNotificationAction) -> int:
        """Perform bulk action on notifications"""
        
        query = self.db.query(Notification).filter(Notification.user_id == user_id)
        
        if action.notification_ids:
            query = query.filter(Notification.id.in_(action.notification_ids))
        elif action.filter_status:
            query = query.filter(Notification.status == action.filter_status)
            
        if action.action == "mark_read":
            updated = query.update({
                "status": NotificationStatus.READ,
                "read_at": datetime.utcnow()
            })
        elif action.action == "mark_unread":
            updated = query.update({
                "status": NotificationStatus.UNREAD,
                "read_at": None
            })
        elif action.action == "archive":
            updated = query.update({
                "status": NotificationStatus.ARCHIVED,
                "archived_at": datetime.utcnow()
            })
        elif action.action == "delete":
            notifications = query.all()
            for notification in notifications:
                self.db.delete(notification)
            updated = len(notifications)
        else:
            raise HTTPException(status_code=400, detail="Invalid action")
            
        self.db.commit()
        return updated

@notifications_router.get("/", response_model=List[NotificationResponse])
async def get_notifications(
    status: Optional[NotificationStatus] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user notifications"""
    manager = NotificationManager(db)
    notifications = await manager.get_user_notifications(current_user.id, status, limit, offset)
    
    return [
        NotificationResponse(
            id=n.id,
            title=n.title,
            message=n.message,
            type=n.notification_type,
            status=n.status,
            is_important=n.is_important,
            action_url=n.action_url,
            action_text=n.action_text,
            data=n.data,
            created_at=n.created_at,
            read_at=n.read_at
        )
        for n in notifications
    ]

@notifications_router.get("/unread/count")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get unread notification count"""
    manager = NotificationManager(db)
    count = await manager.get_unread_count(current_user.id)
    return {"unread_count": count}

@notifications_router.put("/{notification_id}/read")
async def mark_as_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark notification as read"""
    manager = NotificationManager(db)
    await manager.mark_as_read(notification_id, current_user.id)
    return {"message": "Notification marked as read"}

@notifications_router.put("/read-all")
async def mark_all_as_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark all notifications as read"""
    manager = NotificationManager(db)
    count = await manager.mark_all_as_read(current_user.id)
    return {"message": f"Marked {count} notifications as read"}

@notifications_router.delete("/{notification_id}")
async def delete_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete notification"""
    manager = NotificationManager(db)
    await manager.delete_notification(notification_id, current_user.id)
    return {"message": "Notification deleted"}

@notifications_router.post("/send")
async def send_notification(
    notification: NotificationCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send notification to user(s)"""
    manager = NotificationManager(db)
    result = await manager.send_notification(notification, current_user.id)
    return {"message": "Notification sent", "notification_id": result.id}

@notifications_router.post("/bulk-action")
async def bulk_notification_action(
    action: BulkNotificationAction,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Perform bulk action on notifications"""
    manager = NotificationManager(db)
    count = await manager.bulk_action(current_user.id, action)
    return {"message": f"Action performed on {count} notifications"}

@notifications_router.get("/preferences", response_model=NotificationPreferences)
async def get_notification_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user notification preferences"""
    preferences = {
        "email_notifications": current_user.get_preference("email_notifications", True),
        "push_notifications": current_user.get_preference("push_notifications", True),
        "desktop_notifications": current_user.get_preference("desktop_notifications", True),
        "notification_types": current_user.get_preference("notification_types", {
            "file_shared": True,
            "file_commented": True,
            "storage_warning": True,
            "security_alert": True
        })
    }
    
    return NotificationPreferences(**preferences)

@notifications_router.put("/preferences")
async def update_notification_preferences(
    preferences: NotificationPreferences,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user notification preferences"""
    
    current_user.set_preference("email_notifications", preferences.email_notifications)
    current_user.set_preference("push_notifications", preferences.push_notifications)
    current_user.set_preference("desktop_notifications", preferences.desktop_notifications)
    current_user.set_preference("notification_types", preferences.notification_types)
    
    db.commit()
    
    return {"message": "Notification preferences updated"}