"""
EmberFrame V2 - Enhanced Main Application Entry Point
"""

import uvicorn
from fastapi import Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import create_app
from app.core.config import get_settings
from app.core.database import create_tables, get_db
from app.utils.logging import setup_logging

# Setup logging
setup_logging()

# Create tables
create_tables()

# Create app
app = create_app()

# Setup templates
templates = Jinja2Templates(directory="templates")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Settings
settings = get_settings()

# Enhanced Login page with modern design
LOGIN_PAGE_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EmberFrame V2 - Login</title>
    <style>
        :root {
            --primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --secondary: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            --dark: #0a0a0f;
            --glass: rgba(255, 255, 255, 0.1);
            --border: rgba(255, 255, 255, 0.2);
            --text: #ffffff;
            --shadow: 0 25px 50px rgba(0, 0, 0, 0.3);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--dark);
            color: var(--text);
            height: 100vh;
            overflow: hidden;
            position: relative;
        }

        /* Animated background */
        .bg-animation {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: var(--primary);
            z-index: -2;
        }

        .bg-animation::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><pattern id="grid" width="10" height="10" patternUnits="userSpaceOnUse"><path d="M 10 0 L 0 0 0 10" fill="none" stroke="rgba(255,255,255,0.1)" stroke-width="0.5"/></pattern></defs><rect width="100" height="100" fill="url(%23grid)"/></svg>');
            animation: gridMove 20s linear infinite;
        }

        @keyframes gridMove {
            0% { transform: translate(0, 0); }
            100% { transform: translate(10px, 10px); }
        }

        /* Floating particles */
        .particles {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: -1;
        }

        .particle {
            position: absolute;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 50%;
            animation: float 8s ease-in-out infinite;
        }

        @keyframes float {
            0%, 100% { transform: translateY(0px) rotate(0deg); }
            25% { transform: translateY(-20px) rotate(90deg); }
            50% { transform: translateY(-10px) rotate(180deg); }
            75% { transform: translateY(-30px) rotate(270deg); }
        }

        /* Login container */
        .login-container {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: var(--glass);
            backdrop-filter: blur(25px);
            border: 1px solid var(--border);
            border-radius: 24px;
            padding: 48px 40px;
            min-width: 420px;
            max-width: 90vw;
            box-shadow: var(--shadow);
            animation: slideUp 0.8s cubic-bezier(0.25, 0.46, 0.45, 0.94);
        }

        @keyframes slideUp {
            from {
                opacity: 0;
                transform: translate(-50%, -40%) scale(0.9);
            }
            to {
                opacity: 1;
                transform: translate(-50%, -50%) scale(1);
            }
        }

        /* Logo section */
        .logo {
            text-align: center;
            margin-bottom: 40px;
        }

        .logo h1 {
            font-size: 3rem;
            font-weight: 700;
            margin-bottom: 8px;
            background: linear-gradient(135deg, #fff 0%, #f0f0f0 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            animation: glow 2s ease-in-out infinite alternate;
        }

        @keyframes glow {
            from { filter: drop-shadow(0 0 5px rgba(255,255,255,0.3)); }
            to { filter: drop-shadow(0 0 20px rgba(255,255,255,0.6)); }
        }

        .logo p {
            opacity: 0.8;
            font-size: 1rem;
            font-weight: 300;
        }

        /* Form styles */
        .form-group {
            margin-bottom: 24px;
            position: relative;
        }

        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            font-size: 0.9rem;
            opacity: 0.9;
        }

        .form-group input {
            width: 100%;
            padding: 16px 20px;
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid var(--border);
            border-radius: 12px;
            color: var(--text);
            font-size: 1rem;
            transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
            backdrop-filter: blur(10px);
        }

        .form-group input:focus {
            outline: none;
            border-color: #667eea;
            background: rgba(255, 255, 255, 0.12);
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.15),
                        0 0 30px rgba(102, 126, 234, 0.2);
            transform: translateY(-2px);
        }

        .form-group input::placeholder {
            color: rgba(255, 255, 255, 0.5);
        }

        /* Login button */
        .login-btn {
            width: 100%;
            padding: 16px;
            background: var(--primary);
            border: none;
            border-radius: 12px;
            color: white;
            font-size: 1.1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
            margin-bottom: 24px;
            position: relative;
            overflow: hidden;
        }

        .login-btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
            transition: left 0.5s;
        }

        .login-btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 15px 35px rgba(102, 126, 234, 0.4);
        }

        .login-btn:hover::before {
            left: 100%;
        }

        .login-btn:active {
            transform: translateY(-1px);
        }

        .login-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }

        /* Alert styles */
        .alert {
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 0.9rem;
            text-align: center;
            animation: slideIn 0.3s ease-out;
        }

        @keyframes slideIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .alert.error {
            background: rgba(231, 76, 60, 0.15);
            border: 1px solid rgba(231, 76, 60, 0.3);
            color: #ffebee;
        }

        .alert.success {
            background: rgba(46, 204, 113, 0.15);
            border: 1px solid rgba(46, 204, 113, 0.3);
            color: #e8f5e8;
        }

        /* Loading spinner */
        .loading-spinner {
            display: none;
            width: 20px;
            height: 20px;
            border: 2px solid transparent;
            border-top: 2px solid white;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-right: 8px;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        /* Register link */
        .register-link {
            text-align: center;
            margin-top: 24px;
        }

        .register-link a {
            color: var(--text);
            text-decoration: none;
            opacity: 0.8;
            transition: all 0.3s ease;
            font-weight: 500;
        }

        .register-link a:hover {
            opacity: 1;
            color: #667eea;
        }

        /* Responsive */
        @media (max-width: 480px) {
            .login-container {
                padding: 32px 24px;
                min-width: auto;
                margin: 20px;
            }

            .logo h1 {
                font-size: 2.5rem;
            }
        }
    </style>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
</head>
<body>
    <div class="bg-animation"></div>
    
    <div class="particles" id="particles"></div>
    
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

        <div class="register-link">
            <a href="#" id="registerLink">Don't have an account? Register here</a>
        </div>
    </div>

    <script>
        // Create floating particles
        function createParticles() {
            const particlesContainer = document.getElementById('particles');
            const particleCount = Math.floor(Math.random() * 50) + 30;

            for (let i = 0; i < particleCount; i++) {
                const particle = document.createElement('div');
                particle.className = 'particle';
                
                const size = Math.random() * 4 + 2;
                particle.style.width = size + 'px';
                particle.style.height = size + 'px';
                particle.style.left = Math.random() * 100 + '%';
                particle.style.top = Math.random() * 100 + '%';
                particle.style.animationDelay = Math.random() * 8 + 's';
                particle.style.animationDuration = (Math.random() * 6 + 6) + 's';
                
                particlesContainer.appendChild(particle);
            }
        }

        class AuthManager {
            constructor() {
                this.apiBase = '/api';
                this.init();
            }

            init() {
                this.setupEventListeners();
                createParticles();
                this.checkExistingAuth();
            }

            setupEventListeners() {
                const loginForm = document.getElementById('loginForm');
                const registerLink = document.getElementById('registerLink');

                loginForm.addEventListener('submit', (e) => this.handleLogin(e));
                registerLink.addEventListener('click', (e) => this.showRegisterForm(e));
            }

            showAlert(message, type = 'error') {
                const alertContainer = document.getElementById('alertContainer');
                alertContainer.innerHTML = `
                    <div class="alert ${type}">
                        ${message}
                    </div>
                `;

                setTimeout(() => {
                    alertContainer.innerHTML = '';
                }, 5000);
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
                        }, 1500);
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
                            headers: {
                                'Authorization': `Bearer ${token}`
                            }
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

            showRegisterForm(e) {
                e.preventDefault();
                this.showAlert('Registration will be available soon!', 'success');
            }
        }

        document.addEventListener('DOMContentLoaded', () => {
            new AuthManager();
        });
    </script>
</body>
</html>'''

# Enhanced Desktop page with modern design
DESKTOP_PAGE_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EmberFrame V2 - Desktop</title>
    <link rel="stylesheet" href="/static/css/main.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
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
                <div class="desktop-icon" data-app="imageviewer">
                    <i class="fas fa-image"></i>
                    <span>Images</span>
                </div>
                <div class="desktop-icon" data-app="musicplayer">
                    <i class="fas fa-music"></i>
                    <span>Music</span>
                </div>
                <div class="desktop-icon" data-app="browser">
                    <i class="fas fa-globe"></i>
                    <span>Browser</span>
                </div>
                <div class="desktop-icon" data-app="notes">
                    <i class="fas fa-sticky-note"></i>
                    <span>Notes</span>
                </div>
                <div class="desktop-icon" data-app="systemmonitor">
                    <i class="fas fa-chart-line"></i>
                    <span>Monitor</span>
                </div>
            </div>
        </div>

        <div class="taskbar">
            <div class="start-button" id="startButton">
                <span>🔥 Start</span>
            </div>

            <div class="taskbar-items" id="taskbarItems">
                <!-- Running applications will appear here -->
            </div>

            <div class="system-tray">
                <div class="system-icon" id="notificationIcon" title="Notifications">
                    <i class="fas fa-bell"></i>
                    <span class="notification-badge" id="notificationBadge" style="display: none;">0</span>
                </div>
                <div class="system-icon" id="networkIcon" title="Network Status">
                    <i class="fas fa-wifi"></i>
                </div>
                <div class="system-icon" id="volumeIcon" title="Volume">
                    <i class="fas fa-volume-up"></i>
                </div>
                <div class="system-icon" id="userIcon" title="User Menu">
                    <i class="fas fa-user"></i>
                </div>
                <div class="time-display" id="timeDisplay">
                    <div class="time">12:00</div>
                    <div class="date">Mon, Jan 1</div>
                </div>
            </div>
        </div>
    </div>

    <!-- Notification Container -->
    <div class="notification-container" id="notificationContainer"></div>

    <!-- Context Menu -->
    <div class="context-menu" id="contextMenu">
        <div class="context-menu-item" data-action="refresh">
            <i class="fas fa-sync"></i> Refresh
        </div>
        <div class="context-menu-item" data-action="paste">
            <i class="fas fa-paste"></i> Paste
        </div>
        <div class="context-menu-item" data-action="properties">
            <i class="fas fa-info-circle"></i> Properties
        </div>
        <div class="context-menu-separator"></div>
        <div class="context-menu-item" data-action="wallpaper">
            <i class="fas fa-image"></i> Change Wallpaper
        </div>
    </div>

    <!-- Start Menu -->
    <div class="start-menu" id="startMenu">
        <div class="start-menu-header">
            <div class="user-info">
                <div class="user-avatar">
                    <i class="fas fa-user"></i>
                </div>
                <div class="user-details">
                    <div class="username" id="startMenuUsername">User</div>
                    <div class="user-status">Online</div>
                </div>
            </div>
        </div>
        <div class="start-menu-content">
            <div class="quick-actions">
                <div class="quick-action" data-app="filemanager">
                    <i class="fas fa-folder"></i>
                    <span>Files</span>
                </div>
                <div class="quick-action" data-app="settings">
                    <i class="fas fa-cog"></i>
                    <span>Settings</span>
                </div>
                <div class="quick-action" data-app="terminal">
                    <i class="fas fa-terminal"></i>
                    <span>Terminal</span>
                </div>
                <div class="quick-action" onclick="desktop.logout()">
                    <i class="fas fa-sign-out-alt"></i>
                    <span>Logout</span>
                </div>
            </div>
            <div class="apps-grid">
                <div class="app-item" data-app="texteditor">
                    <i class="fas fa-edit"></i>
                    <span>Text Editor</span>
                </div>
                <div class="app-item" data-app="calculator">
                    <i class="fas fa-calculator"></i>
                    <span>Calculator</span>
                </div>
                <div class="app-item" data-app="imageviewer">
                    <i class="fas fa-image"></i>
                    <span>Image Viewer</span>
                </div>
                <div class="app-item" data-app="musicplayer">
                    <i class="fas fa-music"></i>
                    <span>Music Player</span>
                </div>
                <div class="app-item" data-app="browser">
                    <i class="fas fa-globe"></i>
                    <span>Browser</span>
                </div>
                <div class="app-item" data-app="notes">
                    <i class="fas fa-sticky-note"></i>
                    <span>Notes</span>
                </div>
                <div class="app-item" data-app="systemmonitor">
                    <i class="fas fa-chart-line"></i>
                    <span>System Monitor</span>
                </div>
            </div>
        </div>
    </div>

    <script src="/static/js/core/desktop.js"></script>
</body>
</html>'''


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint - redirect to login or desktop based on auth"""
    return RedirectResponse(url="/login")


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """Serve enhanced login page"""
    return HTMLResponse(content=LOGIN_PAGE_HTML)


@app.get("/desktop", response_class=HTMLResponse)
async def desktop_page():
    """Serve enhanced desktop page"""
    return HTMLResponse(content=DESKTOP_PAGE_HTML)


@app.get("/admin")
async def admin_panel():
    """Admin panel redirect"""
    return RedirectResponse(url="/static/admin.html")


@app.get("/logout")
async def logout():
    """Logout endpoint"""
    response = RedirectResponse(url="/login")
    response.delete_cookie("access_token")
    return response


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": "2.0.0",
        "timestamp": "2024-06-02T12:00:00Z"
    }


# API status endpoint
@app.get("/api/status")
async def api_status():
    """API status endpoint"""
    return {
        "status": "operational",
        "services": {
            "database": "connected",
            "redis": "connected",
            "websocket": "active"
        },
        "uptime": "running"
    }


# Development endpoints
if settings.DEBUG:
    @app.get("/debug/users")
    async def debug_users(db: Session = Depends(get_db)):
        """Debug endpoint to list all users"""
        from app.models.user import User
        users = db.query(User).all()
        return [
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_admin": user.is_admin,
                "is_active": user.is_active,
                "created_at": user.created_at
            }
            for user in users
        ]

    @app.get("/debug/create-test-user")
    async def create_test_user(db: Session = Depends(get_db)):
        """Debug endpoint to create a test user"""
        from app.models.user import User
        from app.core.security import get_password_hash

        existing = db.query(User).filter(User.username == "testuser").first()
        if existing:
            return {"message": "Test user already exists"}

        test_user = User(
            username="testuser",
            email="test@example.com",
            hashed_password=get_password_hash("testpass123"),
            first_name="Test",
            last_name="User",
            is_active=True,
            is_admin=False
        )

        db.add(test_user)
        db.commit()

        return {"message": "Test user created", "username": "testuser", "password": "testpass123"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )