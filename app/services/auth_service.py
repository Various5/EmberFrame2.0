"""
Authentication service
"""

from datetime import timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.security import verify_password, get_password_hash, create_access_token
from app.models.user import User
from app.schemas.auth import UserCreate, TokenResponse
from app.services.audit_service import AuditService


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)

    async def register_user(self, user_data: UserCreate) -> TokenResponse:
        """Register new user"""
        # Check if user exists
        existing_user = self.db.query(User).filter(
            (User.username == user_data.username) | (User.email == user_data.email)
        ).first()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already registered"
            )

        # Create user
        hashed_password = get_password_hash(user_data.password)
        user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            first_name=user_data.first_name,
            last_name=user_data.last_name
        )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        # Log registration
        await self.audit_service.log_action("user_register", "user", str(user.id), user.id)

        # Create token
        access_token = create_access_token(data={"sub": str(user.id)})

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=user.id,
            username=user.username
        )

    async def authenticate_user(self, username: str, password: str) -> TokenResponse:
        """Authenticate user"""
        user = self.db.query(User).filter(User.username == username).first()

        if not user or not verify_password(password, user.hashed_password):
            await self.audit_service.log_action("login_failed", "user", username)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )

        # Log successful login
        await self.audit_service.log_action("login_success", "user", str(user.id), user.id)

        # Create token
        access_token = create_access_token(data={"sub": str(user.id)})

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=user.id,
            username=user.username
        )

    async def get_current_user(self, token: str) -> User:
        """Get current user from token"""
        # Token verification is handled in dependencies
        pass
