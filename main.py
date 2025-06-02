"""
EmberFrame V2 - Main Application Entry Point (Simplified)
"""

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import our app components
try:
    from app.core.config import get_settings
    settings = get_settings()
    logger.info("✅ Configuration loaded successfully")
except Exception as e:
    logger.error(f"❌ Failed to load configuration: {e}")
    # Create minimal settings
    class MinimalSettings:
        DEBUG = True
        APP_NAME = "EmberFrame V2"
        SECRET_KEY = "development-key-change-in-production"
    settings = MinimalSettings()

# Create FastAPI app
app = FastAPI(
    title="EmberFrame V2 API",
    description="Next-Generation Web Desktop Environment API",
    version="2.0.0",
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else ["http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files if directory exists
static_dir = Path("static")
if static_dir.exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")
    logger.info("✅ Static files mounted")

# Try to include API routes
try:
    from app.api.auth import auth_router
    app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
    logger.info("✅ Auth router included")
except Exception as e:
    logger.warning(f"⚠️ Could not include auth router: {e}")

try:
    from app.api.users import users_router
    app.include_router(users_router, prefix="/api/users", tags=["Users"])
    logger.info("✅ Users router included")
except Exception as e:
    logger.warning(f"⚠️ Could not include users router: {e}")

try:
    from app.api.files import files_router
    app.include_router(files_router, prefix="/api/files", tags=["Files"])
    logger.info("✅ Files router included")
except Exception as e:
    logger.warning(f"⚠️ Could not include files router: {e}")

try:
    from app.api.admin import admin_router
    app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])
    logger.info("✅ Admin router included")
except Exception as e:
    logger.warning(f"⚠️ Could not include admin router: {e}")

# Basic HTML responses
LOGIN_PAGE_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EmberFrame V2 - Login</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 0;
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            color: white;
        }
        .container {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.2);
            min-width: 400px;
            text-align: center;
        }
        h1 { margin-bottom: 30px; font-size: 2.5rem; }
        .form-group { margin-bottom: 20px; text-align: left; }
        label { display: block; margin-bottom: 5px; font-weight: 500; }
        input {
            width: 100%;
            padding: 12px;
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.1);
            color: white;
            font-size: 16px;
            box-sizing: border-box;
        }
        input::placeholder { color: rgba(255, 255, 255, 0.7); }
        button {
            width: 100%;
            padding: 12px;
            background: #667eea;
            border: none;
            border-radius: 8px;
            color: white;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.3s;
        }
        button:hover { background: #5a6fd8; }
        .error { color: #ff6b6b; margin-top: 10px; }
        .status { margin-top: 20px; padding: 10px; border-radius: 8px; }
        .success { background: rgba(40, 167, 69, 0.2); border: 1px solid #28a745; }
        .warning { background: rgba(255, 193, 7, 0.2); border: 1px solid #ffc107; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔥 EmberFrame V2</h1>
        <p style="margin-bottom: 30px;">Next-Generation Web Desktop</p>
        
        <div id="status" class="status success">
            <strong>✅ Application is running!</strong><br>
            Backend API is operational
        </div>
        
        <form id="loginForm" style="margin-top: 30px;">
            <div class="form-group">
                <label for="username">Username</label>
                <input type="text" id="username" placeholder="Enter username" required>
            </div>
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" placeholder="Enter password" required>
            </div>
            <button type="submit">Sign In</button>
            <div id="error" class="error" style="display: none;"></div>
        </form>
        
        <div style="margin-top: 30px; font-size: 0.9rem; opacity: 0.8;">
            <p>Default admin credentials:</p>
            <p><strong>Username:</strong> admin<br><strong>Password:</strong> admin123</p>
            <p style="margin-top: 15px;">
                <a href="/api/docs" style="color: #fff;">📚 API Documentation</a> |
                <a href="/health" style="color: #fff;">🏥 Health Check</a>
            </p>
        </div>
    </div>
    
    <script>
        document.getElementById('loginForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            const errorDiv = document.getElementById('error');
            
            try {
                const formData = new FormData();
                formData.append('username', username);
                formData.append('password', password);
                
                const response = await fetch('/api/auth/login', {
                    method: 'POST',
                    body: formData
                });
                
                if (response.ok) {
                    const data = await response.json();
                    localStorage.setItem('accessToken', data.access_token);
                    window.location.href = '/desktop';
                } else {
                    const error = await response.json();
                    errorDiv.textContent = error.detail || 'Login failed';
                    errorDiv.style.display = 'block';
                }
            } catch (error) {
                errorDiv.textContent = 'Network error - API may not be available';
                errorDiv.style.display = 'block';
            }
        });
    </script>
</body>
</html>'''

DESKTOP_PAGE_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EmberFrame V2 - Desktop</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 0;
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            color: white;
        }
        .container {
            text-align: center;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 60px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        h1 { font-size: 3rem; margin-bottom: 20px; }
        p { font-size: 1.2rem; margin-bottom: 30px; opacity: 0.9; }
        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 40px;
        }
        .feature {
            background: rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .feature h3 { margin-bottom: 10px; color: #fff; }
        .links { margin-top: 40px; }
        .links a {
            color: #fff;
            text-decoration: none;
            margin: 0 15px;
            padding: 10px 20px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            transition: all 0.3s;
        }
        .links a:hover {
            background: rgba(255, 255, 255, 0.2);
            transform: translateY(-2px);
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔥 Welcome to EmberFrame V2</h1>
        <p>Your next-generation web desktop environment is ready!</p>
        
        <div class="features">
            <div class="feature">
                <h3>📁 File Management</h3>
                <p>Advanced file operations with drag & drop</p>
            </div>
            <div class="feature">
                <h3>🔐 Security</h3>
                <p>Multi-factor authentication & session management</p>
            </div>
            <div class="feature">
                <h3>🌐 Real-time</h3>
                <p>WebSocket-powered live updates</p>
            </div>
            <div class="feature">
                <h3>📊 Analytics</h3>
                <p>Comprehensive usage insights</p>
            </div>
        </div>
        
        <div class="links">
            <a href="/api/docs">📚 API Docs</a>
            <a href="/api/users/me">👤 Profile</a>
            <a href="/api/files">📁 Files</a>
            <a href="/api/admin/users">⚙️ Admin</a>
            <a href="javascript:localStorage.clear();window.location.href='/login'">🚪 Logout</a>
        </div>
        
        <p style="margin-top: 40px; font-size: 0.9rem; opacity: 0.7;">
            EmberFrame V2 Backend API is running successfully!<br>
            Frontend applications are available through the API endpoints.
        </p>
    </div>
</body>
</html>'''

# Basic routes
@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint"""
    return RedirectResponse(url="/login")

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """Login page"""
    return HTMLResponse(content=LOGIN_PAGE_HTML)

@app.get("/desktop", response_class=HTMLResponse)
async def desktop_page():
    """Desktop page"""
    return HTMLResponse(content=DESKTOP_PAGE_HTML)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": "2.0.0",
        "message": "EmberFrame V2 API is running successfully!"
    }

@app.get("/api/status")
async def api_status():
    """API status endpoint"""
    return {
        "status": "operational",
        "version": "2.0.0",
        "endpoints": {
            "health": "/health",
            "api_docs": "/api/docs",
            "login": "/login",
            "desktop": "/desktop"
        }
    }

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "Something went wrong. Check the logs for details.",
            "type": type(exc).__name__
        }
    )

if __name__ == "__main__":
    print("🔥 Starting EmberFrame V2...")
    print("📍 Application will be available at: http://localhost:8000")
    print("📚 API Documentation at: http://localhost:8000/api/docs")
    print("🏥 Health Check at: http://localhost:8000/health")
    print("")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )