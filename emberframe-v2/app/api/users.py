"""
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
