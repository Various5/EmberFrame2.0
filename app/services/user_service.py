"""
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
