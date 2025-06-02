"""
EmberFrame V2 - Modern Web Desktop Environment
Application Factory Pattern
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import get_settings
from app.core.database import engine
from app.api.auth import auth_router
from app.api.files import files_router
from app.api.users import users_router
from app.api.admin import admin_router
from app.api.websocket import websocket_router


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    settings = get_settings()

    app = FastAPI(
        title="EmberFrame V2",
        description="Modern Web Desktop Environment",
        version="2.0.0",
        docs_url="/api/docs" if settings.DEBUG else None,
        redoc_url="/api/redoc" if settings.DEBUG else None
    )

    # Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_HOSTS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.SECRET_KEY,
        max_age=settings.SESSION_EXPIRE
    )

    # Static files
    app.mount("/static", StaticFiles(directory="static"), name="static")

    # API Routes
    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
    app.include_router(files_router, prefix="/api/files", tags=["files"])
    app.include_router(users_router, prefix="/api/users", tags=["users"])
    app.include_router(admin_router, prefix="/api/admin", tags=["admin"])
    app.include_router(websocket_router, prefix="/ws", tags=["websocket"])

    return app