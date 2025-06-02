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

# Import security middleware
try:
    from app.core.security import SecurityMiddleware, rate_limiter
    SECURITY_AVAILABLE = True
except ImportError:
    SECURITY_AVAILABLE = False
    print("Warning: Security middleware not available")


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    settings = get_settings()

    app = FastAPI(
        title="EmberFrame V2",
        description="Next-Generation Web Desktop Environment",
        version="2.0.0",
        docs_url="/api/docs" if settings.DEBUG else None,
        redoc_url="/api/redoc" if settings.DEBUG else None,
        openapi_url="/api/openapi.json" if settings.DEBUG else None
    )

    # Security Middleware (if available)
    if SECURITY_AVAILABLE and settings.RATE_LIMIT_ENABLED:
        app.add_middleware(SecurityMiddleware, rate_limiter=rate_limiter)

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_HOSTS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Session Middleware
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.SECRET_KEY,
        max_age=settings.SESSION_EXPIRE,
        same_site="lax",
        https_only=not settings.DEBUG
    )

    # Static files (must be before API routes)
    try:
        app.mount("/static", StaticFiles(directory="static"), name="static")
    except RuntimeError:
        # Static directory doesn't exist in some deployment scenarios
        pass

    # API Routes
    app.include_router(auth_router, prefix="/api/auth", tags=["authentication"])
    app.include_router(files_router, prefix="/api/files", tags=["files"])
    app.include_router(users_router, prefix="/api/users", tags=["users"])
    app.include_router(admin_router, prefix="/api/admin", tags=["admin"])
    app.include_router(websocket_router, prefix="/ws", tags=["websocket"])

    # Application event handlers
    @app.on_event("startup")
    async def startup_event():
        """Application startup event"""
        print("🔥 EmberFrame V2 starting up...")

        # Initialize database tables
        try:
            from app.core.database import create_tables
            create_tables()
            print("✅ Database tables initialized")
        except Exception as e:
            print(f"⚠️ Database initialization warning: {e}")

        # Create default admin user if needed
        try:
            from app.scripts.init_db import init_database
            init_database()
            print("✅ Default admin user checked/created")
        except Exception as e:
            print(f"⚠️ Admin user initialization warning: {e}")

        print("🚀 EmberFrame V2 ready!")

    @app.on_event("shutdown")
    async def shutdown_event():
        """Application shutdown event"""
        print("🔥 EmberFrame V2 shutting down...")

    # Custom exception handlers
    @app.exception_handler(404)
    async def not_found_handler(request, exc):
        """Custom 404 handler"""
        return {"detail": "Endpoint not found", "status_code": 404}

    @app.exception_handler(500)
    async def internal_error_handler(request, exc):
        """Custom 500 handler"""
        return {"detail": "Internal server error", "status_code": 500}

    return app