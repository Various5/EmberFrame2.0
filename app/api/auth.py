"""
Authentication API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.services.auth_service import AuthService
from app.schemas.auth import TokenResponse, UserCreate, UserLogin

auth_router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


@auth_router.post("/register", response_model=TokenResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register new user"""
    try:
        auth_service = AuthService(db)
        return await auth_service.register_user(user_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@auth_router.post("/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """User login"""
    try:
        auth_service = AuthService(db)
        return await auth_service.authenticate_user(form_data.username, form_data.password)
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid credentials")


@auth_router.post("/logout")
async def logout():
    """User logout"""
    return {"message": "Logged out successfully"}


@auth_router.get("/me")
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Get current user info"""
    auth_service = AuthService(db)
    return await auth_service.get_current_user(token)
