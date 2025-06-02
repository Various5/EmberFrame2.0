# app/__init__.py
"""
Complete EmberFrame V2 Application Factory
"""

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.sessions import SessionMiddleware
import time
import logging

from app.core.config import get_settings
from app.core.security import get_security_middleware, rate_limiter
from app.core.database import create_tables
from app.utils.logging import setup_logging

# Import all API routers
from app.api.auth import auth_router
from app.api.users import users_router
from app.api.files import files_router
from app.api.admin import admin_router
from app.api.websocket import websocket_router
from app.api.system import system_router
from app.api.notifications import notifications_router
from app.api.search import search_router
from app.api.sharing import sharing_router
from app.api.analytics import analytics_router
from app.api.integrations import integrations_router

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""

    settings = get_settings()

    # Setup logging
    setup_logging()

    # Create FastAPI app
    app = FastAPI(
        title="EmberFrame V2 API",
        description="Next-Generation Web Desktop Environment API",
        version="2.0.0",
        docs_url="/api/docs" if settings.DEBUG else None,
        redoc_url="/api/redoc" if settings.DEBUG else None,
        openapi_url="/api/openapi.json" if settings.DEBUG else None
    )

    # Add middleware
    setup_middleware(app, settings)

    # Include API routers
    setup_routes(app)

    # Setup event handlers
    setup_events(app)

    # Create database tables
    create_tables()

    logger.info("🔥 EmberFrame V2 API initialized successfully")

    return app


def setup_middleware(app: FastAPI, settings):
    """Setup application middleware"""

    # Security middleware (rate limiting, headers, etc.)
    security_middleware = get_security_middleware()
    app.add_middleware(type(security_middleware), rate_limiter=rate_limiter)

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_HOSTS if settings.ALLOWED_HOSTS != ["*"] else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Compression middleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Session middleware
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.SECRET_KEY,
        max_age=settings.SESSION_EXPIRE
    )

    # Request timing middleware
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response


def setup_routes(app: FastAPI):
    """Setup API routes"""

    # API routes with prefix
    api_prefix = "/api"

    app.include_router(auth_router, prefix=f"{api_prefix}/auth", tags=["Authentication"])
    app.include_router(users_router, prefix=f"{api_prefix}/users", tags=["Users"])
    app.include_router(files_router, prefix=f"{api_prefix}/files", tags=["Files"])
    app.include_router(sharing_router, prefix=f"{api_prefix}/sharing", tags=["File Sharing"])
    app.include_router(search_router, prefix=f"{api_prefix}/search", tags=["Search"])
    app.include_router(notifications_router, prefix=f"{api_prefix}/notifications", tags=["Notifications"])
    app.include_router(analytics_router, prefix=f"{api_prefix}/analytics", tags=["Analytics"])
    app.include_router(system_router, prefix=f"{api_prefix}/system", tags=["System"])
    app.include_router(integrations_router, prefix=f"{api_prefix}/integrations", tags=["Integrations"])
    app.include_router(admin_router, prefix=f"{api_prefix}/admin", tags=["Administration"])

    # WebSocket routes
    app.include_router(websocket_router, prefix="/ws", tags=["WebSocket"])


def setup_events(app: FastAPI):
    """Setup application event handlers"""

    @app.on_event("startup")
    async def startup_event():
        """Application startup tasks"""
        logger.info("🚀 Starting EmberFrame V2...")

        # Initialize services
        from app.services.notification_service import NotificationService
        from app.services.cache_service import CacheService

        # Setup periodic tasks
        import asyncio
        from app.tasks.maintenance_tasks import cleanup_old_audit_logs

        # Schedule background tasks
        asyncio.create_task(schedule_periodic_tasks())

        logger.info("✅ EmberFrame V2 startup completed")

    @app.on_event("shutdown")
    async def shutdown_event():
        """Application shutdown tasks"""
        logger.info("🛑 Shutting down EmberFrame V2...")

        # Cleanup tasks
        # Close database connections, cache connections, etc.

        logger.info("✅ EmberFrame V2 shutdown completed")


async def schedule_periodic_tasks():
    """Schedule periodic background tasks"""
    import asyncio
    from app.tasks.maintenance_tasks import (
        cleanup_old_audit_logs,
        update_storage_statistics,
        system_health_check
    )

    while True:
        try:
            # Run tasks every hour
            await asyncio.sleep(3600)

            # Cleanup old audit logs
            await cleanup_old_audit_logs()

            # Update storage stats
            await update_storage_statistics()

            # System health check
            await system_health_check()

        except Exception as e:
            logger.error(f"Error in periodic tasks: {e}")


# Global exception handlers
def setup_exception_handlers(app: FastAPI):
    """Setup global exception handlers"""

    from fastapi import HTTPException
    from fastapi.responses import JSONResponse

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "status_code": exc.status_code,
                "timestamp": time.time()
            }
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "status_code": 500,
                "timestamp": time.time()
            }
        )