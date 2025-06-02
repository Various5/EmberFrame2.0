"""
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
