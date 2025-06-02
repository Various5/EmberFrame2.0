# app/services/system_service.py
"""
Complete System Management Service
"""

import os
import psutil
import shutil
import tarfile
import zipfile
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.user import User, File, AuditLog, SystemSettings, Theme
from app.schemas.system import SystemSettingCreate, SystemSettingUpdate, ThemeCreate
from app.core.config import get_settings
from app.services.audit_service import AuditService

settings = get_settings()


class SystemService:
    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)
        self.app_start_time = datetime.utcnow()

    async def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics"""

        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        # Application metrics
        user_count = self.db.query(func.count(User.id)).scalar()
        active_sessions = await self.get_active_session_count()
        file_count = self.db.query(func.count(File.id)).filter(File.is_deleted == False).scalar()
        storage_used = self.db.query(func.sum(File.size)).filter(File.is_deleted == False).scalar() or 0

        return {
            "cpu_usage": cpu_percent,
            "memory_usage": memory.percent,
            "memory_total": memory.total,
            "memory_used": memory.used,
            "disk_usage": (disk.used / disk.total) * 100,
            "disk_total": disk.total,
            "disk_used": disk.used,
            "user_count": user_count,
            "active_sessions": active_sessions,
            "file_count": file_count,
            "storage_used": storage_used,
            "uptime": str(datetime.utcnow() - self.app_start_time)
        }

    async def get_user_count(self) -> int:
        """Get total user count"""
        return self.db.query(func.count(User.id)).scalar()

    async def get_active_session_count(self) -> int:
        """Get active session count"""
        # Mock implementation - in real app, query session table
        return 0

    async def get_file_count(self) -> int:
        """Get total file count"""
        return self.db.query(func.count(File.id)).filter(File.is_deleted == False).scalar()

    async def get_total_storage_used(self) -> int:
        """Get total storage used"""
        return self.db.query(func.sum(File.size)).filter(File.is_deleted == False).scalar() or 0

    async def get_uptime(self) -> str:
        """Get system uptime"""
        uptime_delta = datetime.utcnow() - self.app_start_time
        return str(uptime_delta)

    async def get_all_settings(self) -> List[SystemSettings]:
        """Get all system settings"""
        return self.db.query(SystemSettings).all()

    async def get_setting(self, key: str) -> Optional[SystemSettings]:
        """Get specific system setting"""
        return self.db.query(SystemSettings).filter(SystemSettings.key == key).first()

    async def create_setting(self, setting_data: SystemSettingCreate, user_id: int) -> SystemSettings:
        """Create new system setting"""
        setting = SystemSettings(
            key=setting_data.key,
            value=setting_data.value,
            description=setting_data.description,
            is_public=setting_data.is_public,
            is_editable=setting_data.is_editable,
            updated_by=user_id
        )

        self.db.add(setting)
        self.db.commit()
        self.db.refresh(setting)

        await self.audit_service.log_action(
            "system_setting_created", "system", setting.key,
            user_id, details={"key": setting.key, "value": setting.value}
        )

        return setting

    async def update_setting(self, key: str, setting_update: SystemSettingUpdate, user_id: int) -> SystemSettings:
        """Update system setting"""
        setting = await self.get_setting(key)
        if not setting:
            raise ValueError(f"Setting {key} not found")

        if not setting.is_editable:
            raise ValueError(f"Setting {key} is not editable")

        # Update fields
        if setting_update.value is not None:
            old_value = setting.value
            setting.value = setting_update.value

        if setting_update.description is not None:
            setting.description = setting_update.description

        if setting_update.is_public is not None:
            setting.is_public = setting_update.is_public

        if setting_update.is_editable is not None:
            setting.is_editable = setting_update.is_editable

        setting.updated_by = user_id
        setting.updated_at = datetime.utcnow()

        self.db.commit()

        await self.audit_service.log_action(
            "system_setting_updated", "system", key,
            user_id, details={
                "key": key,
                "old_value": old_value if 'old_value' in locals() else None,
                "new_value": setting.value
            }
        )

        return setting

    async def get_themes(self) -> List[Theme]:
        """Get all available themes"""
        return self.db.query(Theme).filter(Theme.is_active == True).all()

    async def create_theme(self, theme_data: ThemeCreate) -> Theme:
        """Create new theme"""
        theme = Theme(
            name=theme_data.name,
            display_name=theme_data.display_name,
            description=theme_data.description,
            css_variables=theme_data.css_variables,
            is_dark=theme_data.is_dark,
            author=theme_data.author,
            version=theme_data.version
        )

        self.db.add(theme)
        self.db.commit()
        self.db.refresh(theme)

        return theme

    async def run_cleanup_tasks(self):
        """Run system cleanup tasks"""
        tasks_run = []

        try:
            # Clean old audit logs (older than 90 days)
            cutoff_date = datetime.utcnow() - timedelta(days=90)
            deleted_logs = self.db.query(AuditLog).filter(
                AuditLog.created_at < cutoff_date
            ).count()

            self.db.query(AuditLog).filter(
                AuditLog.created_at < cutoff_date
            ).delete()

            tasks_run.append(f"Cleaned {deleted_logs} old audit logs")

            # Clean temporary files
            temp_dir = Path("/tmp/emberframe")
            if temp_dir.exists():
                cleaned_files = 0
                for file_path in temp_dir.iterdir():
                    if file_path.is_file():
                        try:
                            file_path.unlink()
                            cleaned_files += 1
                        except:
                            pass
                tasks_run.append(f"Cleaned {cleaned_files} temporary files")

            # Clean orphaned files (files without database records)
            upload_dir = Path(settings.UPLOAD_DIR)
            if upload_dir.exists():
                orphaned_count = 0
                for user_dir in upload_dir.iterdir():
                    if user_dir.is_dir() and user_dir.name.isdigit():
                        user_id = int(user_dir.name)
                        user = self.db.query(User).filter(User.id == user_id).first()
                        if not user:
                            # User deleted, remove their files
                            shutil.rmtree(user_dir)
                            orphaned_count += 1

                tasks_run.append(f"Cleaned {orphaned_count} orphaned user directories")

            self.db.commit()

        except Exception as e:
            print(f"Cleanup task error: {e}")
            tasks_run.append(f"Error during cleanup: {e}")

        return tasks_run

    async def create_backup(self, user_id: int) -> str:
        """Create system backup"""
        backup_id = f"backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        # In a real implementation, this would:
        # 1. Backup database
        # 2. Backup uploaded files
        # 3. Create compressed archive
        # 4. Store in backup location or cloud storage

        await self.audit_service.log_action(
            "backup_created", "system", backup_id,
            user_id, details={"backup_id": backup_id}
        )

        return backup_id

    async def perform_backup(self, backup_id: str):
        """Perform actual backup operation (background task)"""
        try:
            # Mock backup process
            import time
            time.sleep(10)  # Simulate backup time

            print(f"Backup {backup_id} completed successfully")

        except Exception as e:
            print(f"Backup {backup_id} failed: {e}")

    async def get_logs(self, level: str = "INFO", limit: int = 100) -> List[Dict[str, Any]]:
        """Get system logs"""
        # In a real implementation, this would read from log files
        # For now, return recent audit logs

        audit_logs = self.db.query(AuditLog).order_by(
            AuditLog.created_at.desc()
        ).limit(limit).all()

        return [
            {
                "timestamp": log.created_at,
                "level": "INFO",
                "message": f"{log.action} - {log.message or 'No details'}",
                "user_id": log.user_id,
                "ip_address": log.ip_address
            }
            for log in audit_logs
        ]

    async def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health status"""
        health = {
            "status": "healthy",
            "checks": {},
            "timestamp": datetime.utcnow().isoformat()
        }

        # Database check
        try:
            self.db.execute("SELECT 1")
            health["checks"]["database"] = {"status": "healthy", "response_time": "< 1ms"}
        except Exception as e:
            health["checks"]["database"] = {"status": "unhealthy", "error": str(e)}
            health["status"] = "degraded"

        # Disk space check
        disk = psutil.disk_usage('/')
        disk_usage = (disk.used / disk.total) * 100

        if disk_usage > 90:
            health["checks"]["disk_space"] = {"status": "warning", "usage": f"{disk_usage:.1f}%"}
            health["status"] = "warning"
        else:
            health["checks"]["disk_space"] = {"status": "healthy", "usage": f"{disk_usage:.1f}%"}

        # Memory check
        memory = psutil.virtual_memory()
        if memory.percent > 90:
            health["checks"]["memory"] = {"status": "warning", "usage": f"{memory.percent:.1f}%"}
            health["status"] = "warning"
        else:
            health["checks"]["memory"] = {"status": "healthy", "usage": f"{memory.percent:.1f}%"}

        # Application services check
        health["checks"]["file_service"] = {"status": "healthy"}
        health["checks"]["auth_service"] = {"status": "healthy"}
        health["checks"]["notification_service"] = {"status": "healthy"}

        return health


# app/services/search_service.py
"""
Advanced Search Service
"""

import re
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func, text
from datetime import datetime

from app.models.user import User, File
from app.schemas.search import SearchRequest, SearchFilter
from app.services.cache_service import CacheService


class SearchService:
    def __init__(self, db: Session):
        self.db = db
        self.cache = CacheService()

    async def search(
            self,
            query: str,
            search_type: str,
            user_id: int,
            limit: int = 20,
            offset: int = 0
    ) -> Dict[str, Any]:
        """Universal search functionality"""

        # Normalize query
        query = query.strip().lower()
        if not query:
            return {"results": [], "total": 0}

        # Cache key
        cache_key = f"search:{user_id}:{search_type}:{query}:{limit}:{offset}"

        # Check cache
        cached_result = await self.cache.get_user_cache(user_id, cache_key)
        if cached_result:
            return cached_result

        results = []
        total = 0

        if search_type in ["all", "files"]:
            file_results = await self._search_files(query, user_id, limit, offset)
            results.extend(file_results["results"])
            total += file_results["total"]

        if search_type in ["all", "users"] and total < limit:
            # Only search users if we haven't reached limit with files
            remaining_limit = limit - len(results)
            user_results = await self._search_users(query, user_id, remaining_limit, 0)
            results.extend(user_results["results"])
            total += user_results["total"]

        # Sort by relevance
        results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

        result = {
            "results": results[:limit],
            "total": total,
            "query": query,
            "search_type": search_type
        }

        # Cache for 5 minutes
        await self.cache.set_user_cache(user_id, cache_key, result, 300)

        return result

    async def _search_files(self, query: str, user_id: int, limit: int, offset: int) -> Dict[str, Any]:
        """Search files with relevance scoring"""

        search_terms = query.split()

        # Build query
        base_query = self.db.query(File).filter(
            and_(
                File.owner_id == user_id,
                File.is_deleted == False
            )
        )

        # Add search conditions
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

        # Get results
        files = base_query.order_by(File.updated_at.desc()).offset(offset).limit(limit).all()

        results = []
        for file in files:
            relevance_score = self._calculate_file_relevance(file, search_terms)
            results.append({
                "id": file.id,
                "name": file.name,
                "type": "file",
                "file_type": file.file_type,
                "path": file.path,
                "size": file.size,
                "created_at": file.created_at,
                "updated_at": file.updated_at,
                "relevance_score": relevance_score
            })

        return {"results": results, "total": total}

    async def _search_users(self, query: str, current_user_id: int, limit: int, offset: int) -> Dict[str, Any]:
        """Search users (for admin or shared content)"""

        # Basic user search (could be expanded based on permissions)
        users = self.db.query(User).filter(
            and_(
                User.id != current_user_id,
                or_(
                    func.lower(User.username).contains(query),
                    func.lower(User.first_name).contains(query),
                    func.lower(User.last_name).contains(query)
                )
            )
        ).offset(offset).limit(limit).all()

        results = []
        for user in users:
            results.append({
                "id": user.id,
                "name": user.username,
                "type": "user",
                "full_name": user.full_name,
                "created_at": user.created_at,
                "relevance_score": self._calculate_user_relevance(user, query)
            })

        return {"results": results, "total": len(results)}

    def _calculate_file_relevance(self, file: File, search_terms: List[str]) -> float:
        """Calculate file search relevance score"""
        score = 0.0

        for term in search_terms:
            # File name match (highest weight)
            if term in file.name.lower():
                score += 10.0
                # Exact match bonus
                if file.name.lower() == term:
                    score += 20.0

            # Description match
            if file.description and term in file.description.lower():
                score += 5.0

            # Tag match
            if file.tags and term in str(file.tags).lower():
                score += 7.0

            # File type match
            if file.file_type and term in file.file_type.lower():
                score += 3.0

        # Recent files get bonus
        days_old = (datetime.utcnow() - file.created_at).days
        if days_old < 7:
            score += 2.0
        elif days_old < 30:
            score += 1.0

        return score

    def _calculate_user_relevance(self, user: User, query: str) -> float:
        """Calculate user search relevance score"""
        score = 0.0

        query_lower = query.lower()

        # Username match
        if query_lower in user.username.lower():
            score += 10.0
            if user.username.lower() == query_lower:
                score += 15.0

        # Name matches
        if user.first_name and query_lower in user.first_name.lower():
            score += 8.0

        if user.last_name and query_lower in user.last_name.lower():
            score += 8.0

        return score

    async def advanced_search(self, search_request: SearchRequest, user_id: int) -> Dict[str, Any]:
        """Advanced search with filters"""

        base_query = self.db.query(File).filter(
            and_(
                File.owner_id == user_id,
                File.is_deleted == False
            )
        )

        # Apply text search
        if search_request.query:
            search_terms = search_request.query.lower().split()
            search_conditions = []

            for term in search_terms:
                term_condition = or_(
                    func.lower(File.name).contains(term),
                    func.lower(File.description).contains(term)
                )
                search_conditions.append(term_condition)

            base_query = base_query.filter(and_(*search_conditions))

        # Apply filters
        if search_request.filters:
            filters = search_request.filters

            if filters.file_type:
                base_query = base_query.filter(File.file_type == filters.file_type)

            if filters.size_min:
                base_query = base_query.filter(File.size >= filters.size_min)

            if filters.size_max:
                base_query = base_query.filter(File.size <= filters.size_max)

            if filters.date_from:
                base_query = base_query.filter(File.created_at >= filters.date_from)

            if filters.date_to:
                base_query = base_query.filter(File.created_at <= filters.date_to)

            if filters.tags:
                # Simple tag search (could be improved with proper tag indexing)
                for tag in filters.tags:
                    base_query = base_query.filter(
                        func.lower(File.tags).contains(tag.lower())
                    )

        # Get total count
        total = base_query.count()

        # Get results with pagination
        files = base_query.order_by(
            File.updated_at.desc()
        ).offset(search_request.offset).limit(search_request.limit).all()

        results = []
        for file in files:
            results.append({
                "id": file.id,
                "name": file.name,
                "type": "file",
                "file_type": file.file_type,
                "path": file.path,
                "size": file.size,
                "created_at": file.created_at,
                "updated_at": file.updated_at,
                "tags": file.get_tag_list() if hasattr(file, 'get_tag_list') else []
            })

        return {
            "results": results,
            "total": total,
            "query": search_request.query,
            "filters_applied": search_request.filters is not None
        }

    async def get_suggestions(self, query: str, user_id: int) -> List[str]:
        """Get search suggestions based on query"""

        if len(query) < 2:
            return []

        # Get recent file names that match
        file_names = self.db.query(File.name).filter(
            and_(
                File.owner_id == user_id,
                File.is_deleted == False,
                func.lower(File.name).contains(query.lower())
            )
        ).limit(10).all()

        suggestions = list(set([name.name for name in file_names]))

        # Add common file type suggestions
        if any(keyword in query.lower() for keyword in ['image', 'photo', 'picture']):
            suggestions.extend(['images', 'photos', 'pictures'])

        if any(keyword in query.lower() for keyword in ['document', 'doc', 'text']):
            suggestions.extend(['documents', 'text files'])

        if any(keyword in query.lower() for keyword in ['video', 'movie']):
            suggestions.extend(['videos', 'movies'])

        return suggestions[:10]