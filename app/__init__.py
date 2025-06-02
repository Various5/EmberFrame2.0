"""
EmberFrame V2 - Modern Web Desktop Environment
Application Factory Pattern - Complete Implementation
"""

import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager

# Import core modules
from app.core.config import get_settings
from app.core.database import create_tables

# Import API routers
from app.api.auth import auth_router
from app.api.files import files_router
from app.api.users import users_router
from app.api.admin import admin_router
from app.api.websocket import websocket_router

# Import security middleware with error handling
try:
    from app.core.security import SecurityMiddleware, rate_limiter, auth_security
    SECURITY_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Security middleware not available: {e}")
    SECURITY_AVAILABLE = False
    SecurityMiddleware = None
    rate_limiter = None
    auth_security = None

# Import utilities
try:
    from app.utils.logging import setup_logging
    LOGGING_AVAILABLE = True
except ImportError:
    LOGGING_AVAILABLE = False

# Enhanced HTML templates
LOGIN_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EmberFrame V2 - Login</title>
    <style>
        :root {
            --primary: #667eea;
            --secondary: #764ba2;
            --bg: #0a0a0f;
            --text: #ffffff;
            --glass: rgba(255,255,255,0.1);
            --border: rgba(255,255,255,0.2);
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: var(--text);
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
            overflow: hidden;
        }
        
        .bg-pattern {
            position: absolute;
            top: 0; left: 0; width: 100%; height: 100%;
            background: radial-gradient(circle at 20% 50%, rgba(120,119,198,0.3) 0%, transparent 50%),
                        radial-gradient(circle at 80% 20%, rgba(255,119,198,0.3) 0%, transparent 50%),
                        radial-gradient(circle at 40% 80%, rgba(120,200,255,0.2) 0%, transparent 50%);
            animation: float 20s ease-in-out infinite;
        }
        
        @keyframes float {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-20px); }
        }
        
        .login-container {
            background: var(--glass);
            backdrop-filter: blur(25px);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 40px;
            width: 400px;
            max-width: 90vw;
            box-shadow: 0 25px 50px rgba(0,0,0,0.3);
            position: relative;
            z-index: 1;
            animation: slideUp 0.8s ease-out;
        }
        
        @keyframes slideUp {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .logo {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .logo h1 {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 8px;
            background: linear-gradient(45deg, #fff, #e0e0e0);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .logo p {
            opacity: 0.8;
            font-size: 0.9rem;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            opacity: 0.9;
        }
        
        .form-group input {
            width: 100%;
            padding: 15px;
            background: rgba(255,255,255,0.1);
            border: 1px solid var(--border);
            border-radius: 10px;
            color: var(--text);
            font-size: 1rem;
            transition: all 0.3s ease;
        }
        
        .form-group input:focus {
            outline: none;
            border-color: var(--primary);
            background: rgba(255,255,255,0.15);
            box-shadow: 0 0 20px rgba(102,126,234,0.3);
        }
        
        .form-group input::placeholder {
            color: rgba(255,255,255,0.6);
        }
        
        .login-btn {
            width: 100%;
            padding: 15px;
            background: linear-gradient(45deg, var(--primary), var(--secondary));
            border: none;
            border-radius: 10px;
            color: white;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-bottom: 20px;
        }
        
        .login-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(102,126,234,0.4);
        }
        
        .alert {
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            text-align: center;
        }
        
        .alert.error {
            background: rgba(231,76,60,0.2);
            border: 1px solid #e74c3c;
        }
        
        .alert.success {
            background: rgba(46,204,113,0.2);
            border: 1px solid #2ecc71;
        }
        
        .loading-spinner {
            display: none;
            width: 20px;
            height: 20px;
            border: 2px solid transparent;
            border-top: 2px solid white;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-right: 10px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="bg-pattern"></div>
    
    <div class="login-container">
        <div class="logo">
            <h1>🔥 EmberFrame</h1>
            <p>Next-Generation Web Desktop</p>
        </div>

        <div id="alertContainer"></div>

        <form id="loginForm">
            <div class="form-group">
                <label for="username">Username</label>
                <input type="text" id="username" name="username" placeholder="Enter your username" required>
            </div>

            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" placeholder="Enter your password" required>
            </div>

            <button type="submit" class="login-btn" id="loginBtn">
                <span class="loading-spinner" id="loadingSpinner"></span>
                <span id="btnText">Sign In</span>
            </button>
        </form>
    </div>

    <script>
        class AuthManager {
            constructor() {
                this.apiBase = '/api';
                this.init();
            }

            init() {
                this.setupEventListeners();
                this.checkExistingAuth();
            }

            setupEventListeners() {
                document.getElementById('loginForm').addEventListener('submit', (e) => this.handleLogin(e));
            }

            showAlert(message, type = 'error') {
                const alertContainer = document.getElementById('alertContainer');
                alertContainer.innerHTML = `<div class="alert ${type}">${message}</div>`;
                setTimeout(() => alertContainer.innerHTML = '', 5000);
            }

            setLoading(loading) {
                const loginBtn = document.getElementById('loginBtn');
                const spinner = document.getElementById('loadingSpinner');
                const btnText = document.getElementById('btnText');

                if (loading) {
                    loginBtn.disabled = true;
                    spinner.style.display = 'inline-block';
                    btnText.textContent = 'Signing In...';
                } else {
                    loginBtn.disabled = false;
                    spinner.style.display = 'none';
                    btnText.textContent = 'Sign In';
                }
            }

            async handleLogin(e) {
                e.preventDefault();
                
                const username = document.getElementById('username').value;
                const password = document.getElementById('password').value;

                if (!username || !password) {
                    this.showAlert('Please fill in all fields');
                    return;
                }

                this.setLoading(true);

                try {
                    const formData = new FormData();
                    formData.append('username', username);
                    formData.append('password', password);

                    const response = await fetch(`${this.apiBase}/auth/login`, {
                        method: 'POST',
                        body: formData
                    });

                    const data = await response.json();

                    if (response.ok) {
                        localStorage.setItem('accessToken', data.access_token);
                        localStorage.setItem('userInfo', JSON.stringify({
                            id: data.user_id,
                            username: data.username
                        }));

                        this.showAlert('Login successful! Launching desktop...', 'success');
                        
                        setTimeout(() => {
                            window.location.href = '/desktop';
                        }, 1000);
                    } else {
                        this.showAlert(data.detail || 'Login failed');
                    }
                } catch (error) {
                    console.error('Login error:', error);
                    this.showAlert('Network error. Please try again.');
                } finally {
                    this.setLoading(false);
                }
            }

            async checkExistingAuth() {
                const token = localStorage.getItem('accessToken');
                if (token) {
                    try {
                        const response = await fetch(`${this.apiBase}/users/me`, {
                            headers: { 'Authorization': `Bearer ${token}` }
                        });

                        if (response.ok) {
                            window.location.href = '/desktop';
                        } else {
                            localStorage.clear();
                        }
                    } catch (error) {
                        localStorage.clear();
                    }
                }
            }
        }

        document.addEventListener('DOMContentLoaded', () => {
            new AuthManager();
        });
    </script>
</body>
</html>"""

DESKTOP_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EmberFrame V2 - Desktop</title>
    <link rel="stylesheet" href="/static/css/main.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
</head>
<body>
    <div class="desktop" id="desktop">
        <div class="desktop-content">
            <div class="desktop-icons" id="desktopIcons">
                <div class="desktop-icon" data-app="filemanager">
                    <i class="fas fa-folder"></i>
                    <span>Files</span>
                </div>
                <div class="desktop-icon" data-app="settings">
                    <i class="fas fa-cog"></i>
                    <span>Settings</span>
                </div>
                <div class="desktop-icon" data-app="texteditor">
                    <i class="fas fa-edit"></i>
                    <span>Editor</span>
                </div>
                <div class="desktop-icon" data-app="calculator">
                    <i class="fas fa-calculator"></i>
                    <span>Calculator</span>
                </div>
                <div class="desktop-icon" data-app="terminal">
                    <i class="fas fa-terminal"></i>
                    <span>Terminal</span>
                </div>
                <div class="desktop-icon" data-app="admin" style="display: none;" id="adminIcon">
                    <i class="fas fa-shield-alt"></i>
                    <span>Admin</span>
                </div>
            </div>
        </div>

        <div class="taskbar">
            <div class="start-button" id="startButton">
                <span>🔥 Start</span>
            </div>

            <div class="taskbar-items" id="taskbarItems"></div>

            <div class="system-tray">
                <div class="system-icon" id="notificationIcon">
                    <i class="fas fa-bell"></i>
                </div>
                <div class="system-icon" id="networkIcon">
                    <i class="fas fa-wifi"></i>
                </div>
                <div class="system-icon" id="userIcon">
                    <i class="fas fa-user"></i>
                </div>
                <div class="time-display" id="timeDisplay">
                    <div class="time">12:00</div>
                    <div class="date">Mon, Jan 1</div>
                </div>
            </div>
        </div>
    </div>

    <div class="notification-container" id="notificationContainer"></div>

    <div class="context-menu" id="contextMenu">
        <div class="context-menu-item" data-action="refresh">
            <i class="fas fa-sync"></i> Refresh
        </div>
        <div class="context-menu-item" data-action="properties">
            <i class="fas fa-info-circle"></i> Properties
        </div>
    </div>

    <script src="/static/js/core/desktop.js"></script>
</body>
</html>"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    # Startup
    logging.info("🔥 EmberFrame V2 starting up...")

    try:
        # Initialize database tables
        create_tables()
        logging.info("✅ Database tables initialized")
    except Exception as e:
        logging.error(f"⚠️ Database initialization error: {e}")

    try:
        # Create default admin user if needed
        from scripts.init_db import init_database
        init_database()
        logging.info("✅ Default admin user checked/created")
    except Exception as e:
        logging.error(f"⚠️ Admin user initialization error: {e}")

    # Setup logging if available
    if LOGGING_AVAILABLE:
        setup_logging()

    logging.info("🚀 EmberFrame V2 ready!")

    yield

    # Shutdown
    logging.info("🔥 EmberFrame V2 shutting down...")


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    settings = get_settings()

    app = FastAPI(
        title="EmberFrame V2",
        description="🔥 Next-Generation Web Desktop Environment - A complete operating system experience in your browser with advanced security, real-time collaboration, and modern UI/UX.",
        version="2.0.0",
        docs_url="/api/docs" if settings.DEBUG else None,
        redoc_url="/api/redoc" if settings.DEBUG else None,
        openapi_url="/api/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan
    )

    # Security Headers Middleware
    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if not settings.DEBUG:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    # Trusted Host Middleware (security)
    if not settings.DEBUG:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.ALLOWED_HOSTS
        )

    # Security Middleware (if available)
    if SECURITY_AVAILABLE and hasattr(settings, 'RATE_LIMIT_ENABLED') and settings.RATE_LIMIT_ENABLED:
        app.add_middleware(SecurityMiddleware, rate_limiter=rate_limiter)

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_HOSTS if settings.ALLOWED_HOSTS != ["*"] else ["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
        expose_headers=["X-Process-Time", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
    )

    # Session Middleware
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.SECRET_KEY,
        max_age=settings.SESSION_EXPIRE,
        same_site="lax",
        https_only=not settings.DEBUG
    )

    # Static files with error handling
    try:
        static_dir = Path("static")
        if static_dir.exists():
            app.mount("/static", StaticFiles(directory="static"), name="static")
        else:
            logging.warning("Static directory not found")
    except Exception as e:
        logging.warning(f"Could not mount static files: {e}")

    # API Routes
    app.include_router(auth_router, prefix="/api/auth", tags=["🔐 Authentication"])
    app.include_router(files_router, prefix="/api/files", tags=["📁 Files"])
    app.include_router(users_router, prefix="/api/users", tags=["👥 Users"])
    app.include_router(admin_router, prefix="/api/admin", tags=["🛡️ Admin"])
    app.include_router(websocket_router, prefix="/ws", tags=["🔌 WebSocket"])

    # Main routes
    @app.get("/", response_class=HTMLResponse)
    async def root():
        """Root endpoint - redirect to login"""
        return RedirectResponse(url="/login")

    @app.get("/login", response_class=HTMLResponse)
    async def login_page():
        """Enhanced login page"""
        return HTMLResponse(content=LOGIN_TEMPLATE)

    @app.get("/desktop", response_class=HTMLResponse)
    async def desktop_page():
        """Enhanced desktop page"""
        return HTMLResponse(content=DESKTOP_TEMPLATE)

    @app.get("/admin", response_class=HTMLResponse)
    async def admin_redirect():
        """Admin panel redirect"""
        return RedirectResponse(url="/static/admin.html")

    @app.get("/logout")
    async def logout():
        """Logout endpoint"""
        response = RedirectResponse(url="/login")
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        return response

    # Health check endpoints
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "app_name": settings.APP_NAME,
            "version": "2.0.0",
            "environment": "development" if settings.DEBUG else "production",
            "features": {
                "security": SECURITY_AVAILABLE,
                "logging": LOGGING_AVAILABLE,
                "websockets": True,
                "file_management": True,
                "admin_panel": True
            }
        }

    @app.get("/api/status")
    async def api_status():
        """Detailed API status"""
        status = {
            "status": "operational",
            "services": {
                "database": "connected",
                "authentication": "active",
                "file_system": "ready",
                "websockets": "active"
            },
            "security": {
                "rate_limiting": SECURITY_AVAILABLE,
                "csrf_protection": True,
                "secure_headers": True
            }
        }

        # Test Redis connection if security is available
        if SECURITY_AVAILABLE and rate_limiter:
            try:
                # Simple Redis test
                test_result = rate_limiter.check_rate_limit("health_check", 1000, 60)
                status["services"]["redis"] = "connected"
            except Exception:
                status["services"]["redis"] = "unavailable"

        return status

    # Development endpoints
    if settings.DEBUG:
        @app.get("/debug/info")
        async def debug_info():
            """Debug information"""
            return {
                "settings": {
                    "debug": settings.DEBUG,
                    "database_url": settings.DATABASE_URL,
                    "upload_dir": settings.UPLOAD_DIR,
                    "max_file_size": settings.MAX_FILE_SIZE
                },
                "available_features": {
                    "security_middleware": SECURITY_AVAILABLE,
                    "logging": LOGGING_AVAILABLE
                }
            }

    # Custom exception handlers
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc):
        """Custom 404 handler"""
        if request.url.path.startswith("/api/"):
            return {"detail": "API endpoint not found", "status_code": 404}
        return RedirectResponse(url="/login")

    @app.exception_handler(500)
    async def internal_error_handler(request: Request, exc):
        """Custom 500 handler"""
        logging.error(f"Internal server error: {exc}")
        if request.url.path.startswith("/api/"):
            return {"detail": "Internal server error", "status_code": 500}
        return RedirectResponse(url="/login")

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Custom HTTP exception handler"""
        if request.url.path.startswith("/api/"):
            return {"detail": exc.detail, "status_code": exc.status_code}

        if exc.status_code == 401:
            return RedirectResponse(url="/login")
        elif exc.status_code == 403:
            return {"detail": "Access forbidden", "status_code": 403}

        return {"detail": exc.detail, "status_code": exc.status_code}

    return app