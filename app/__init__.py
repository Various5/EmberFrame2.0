# app/__init__.py
"""
Complete EmberFrame V2 Application Factory
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import time
import logging

# Import settings first
from app.core.config import get_settings

settings = get_settings()


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""

    # Setup logging first
    from app.utils.logging import setup_logging
    setup_logging()

    logger = logging.getLogger(__name__)

    # Create FastAPI app
    app = FastAPI(
        title="EmberFrame V2 API",
        description="Next-Generation Web Desktop Environment API",
        version="2.0.0",
        docs_url="/api/docs" if settings.DEBUG else None,
        redoc_url="/api/redoc" if settings.DEBUG else None,
        openapi_url="/api/openapi.json" if settings.DEBUG else None
    )

    # Add basic middleware first
    setup_basic_middleware(app)

    # Include API routers
    setup_routes(app)

    # Setup event handlers
    setup_events(app)

    logger.info("🔥 EmberFrame V2 API initialized successfully")

    return app


def setup_basic_middleware(app: FastAPI):
    """Setup basic application middleware"""

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

    try:
        # Import routers individually to handle missing dependencies gracefully
        api_prefix = "/api"

        # Core authentication
        try:
            from app.api.auth import auth_router
            app.include_router(auth_router, prefix=f"{api_prefix}/auth", tags=["Authentication"])
        except ImportError as e:
            print(f"Warning: Could not import auth router: {e}")

        # User management
        try:
            from app.api.users import users_router
            app.include_router(users_router, prefix=f"{api_prefix}/users", tags=["Users"])
        except ImportError as e:
            print(f"Warning: Could not import users router: {e}")

        # File management
        try:
            from app.api.files import files_router
            app.include_router(files_router, prefix=f"{api_prefix}/files", tags=["Files"])
        except ImportError as e:
            print(f"Warning: Could not import files router: {e}")

        # Admin functionality
        try:
            from app.api.admin import admin_router
            app.include_router(admin_router, prefix=f"{api_prefix}/admin", tags=["Administration"])
        except ImportError as e:
            print(f"Warning: Could not import admin router: {e}")

        # WebSocket routes
        try:
            from app.api.websocket import websocket_router
            app.include_router(websocket_router, prefix="/ws", tags=["WebSocket"])
        except ImportError as e:
            print(f"Warning: Could not import websocket router: {e}")

    except Exception as e:
        print(f"Error setting up routes: {e}")


def setup_events(app: FastAPI):
    """Setup application event handlers"""

    @app.on_event("startup")
    async def startup_event():
        """Application startup tasks"""
        logger = logging.getLogger(__name__)
        logger.info("🚀 Starting EmberFrame V2...")

        # Create database tables
        try:
            from app.core.database import create_tables
            create_tables()
            logger.info("✅ Database tables created")
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")

        logger.info("✅ EmberFrame V2 startup completed")

    @app.on_event("shutdown")
    async def shutdown_event():
        """Application shutdown tasks"""
        logger = logging.getLogger(__name__)
        logger.info("🛑 Shutting down EmberFrame V2...")
        logger.info("✅ EmberFrame V2 shutdown completed")


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
        logger = logging.getLogger(__name__)
        logger.error(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "status_code": 500,
                "timestamp": time.time()
            }
        )