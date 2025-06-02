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
from app.utils import setup_logging

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

# Login page HTML content
LOGIN_PAGE_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EmberFrame V2 - Login</title>
    <style>
        :root {
            --primary-color: #667eea;
            --secondary-color: #764ba2;
            --error-color: #e74c3c;
            --success-color: #2ecc71;
            --text-color: #ffffff;
            --input-bg: rgba(255, 255, 255, 0.1);
            --border-color: rgba(255, 255, 255, 0.2);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            color: var(--text-color);
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
        }

        .login-container {
            background: rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(20px);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 40px;
            width: 400px;
            max-width: 90vw;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
            animation: slideUp 0.6s ease-out;
        }

        @keyframes slideUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .logo {
            text-align: center;
            margin-bottom: 30px;
        }

        .logo h1 {
            font-size: 2.5rem;
            font-weight: 300;
            margin-bottom: 10px;
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
            background: var(--input-bg);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            color: var(--text-color);
            font-size: 1rem;
            transition: all 0.3s ease;
        }

        .form-group input:focus {
            outline: none;
            border-color: var(--primary-color);
            background: rgba(255, 255, 255, 0.15);
            box-shadow: 0 0 20px rgba(102, 126, 234, 0.3);
        }

        .form-group input::placeholder {
            color: rgba(255, 255, 255, 0.6);
        }

        .login-btn {
            width: 100%;
            padding: 15px;
            background: linear-gradient(45deg, var(--primary-color), var(--secondary-color));
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
            box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
        }

        .login-btn:active {
            transform: translateY(0);
        }

        .login-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }

        .alert {
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 0.9rem;
            text-align: center;
        }

        .alert.error {
            background: rgba(231, 76, 60, 0.2);
            border: 1px solid var(--error-color);
            color: #ffebee;
        }

        .alert.success {
            background: rgba(46, 204, 113, 0.2);
            border: 1px solid var(--success-color);
            color: #e8f5e8;
        }

        .register-link {
            text-align: center;
            margin-top: 20px;
        }

        .register-link a {
            color: var(--text-color);
            text-decoration: none;
            opacity: 0.8;
            transition: opacity 0.3s ease;
        }

        .register-link a:hover {
            opacity: 1;
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

        .floating-particles {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: -1;
        }

        .particle {
            position: absolute;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 50%;
            animation: float 6s ease-in-out infinite;
        }

        @keyframes float {
            0%, 100% { transform: translateY(0px) rotate(0deg); }
            50% { transform: translateY(-20px) rotate(180deg); }
        }
    </style>
</head>
<body>
    <div class="floating-particles" id="particles"></div>
    
    <div class="login-container">
        <div class="logo">
            <h1>🔥 EmberFrame</h1>
            <p>Modern Web Desktop Environment</p>
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
        class AuthManager {
            constructor() {
                this.apiBase = '/api';
                this.init();
            }

            init() {
                this.setupEventListeners();
                this.createParticles();
                this.checkExistingAuth();
            }

            setupEventListeners() {
                const loginForm = document.getElementById('loginForm');
                const registerLink = document.getElementById('registerLink');

                loginForm.addEventListener('submit', (e) => this.handleLogin(e));
                registerLink.addEventListener('click', (e) => this.showRegisterForm(e));
            }

            createParticles() {
                const particlesContainer = document.getElementById('particles');
                for (let i = 0; i < 50; i++) {
                    const particle = document.createElement('div');
                    particle.className = 'particle';
                    particle.style.left = Math.random() * 100 + '%';
                    particle.style.top = Math.random() * 100 + '%';
                    particle.style.width = Math.random() * 4 + 2 + 'px';
                    particle.style.height = particle.style.width;
                    particle.style.animationDelay = Math.random() * 6 + 's';
                    particle.style.animationDuration = (Math.random() * 4 + 4) + 's';
                    particlesContainer.appendChild(particle);
                }
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
                        // Store authentication data
                        localStorage.setItem('accessToken', data.access_token);
                        localStorage.setItem('userInfo', JSON.stringify({
                            id: data.user_id,
                            username: data.username
                        }));

                        this.showAlert('Login successful! Redirecting...', 'success');
                        
                        // Redirect to desktop
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

            checkExistingAuth() {
                const token = localStorage.getItem('accessToken');
                if (token) {
                    // Verify token is still valid
                    this.verifyToken(token);
                }
            }

            async verifyToken(token) {
                try {
                    const response = await fetch(`${this.apiBase}/users/me`, {
                        headers: {
                            'Authorization': `Bearer ${token}`
                        }
                    });

                    if (response.ok) {
                        // Token is valid, redirect to desktop
                        window.location.href = '/desktop';
                    } else {
                        // Token is invalid, clear storage
                        localStorage.clear();
                    }
                } catch (error) {
                    console.error('Token verification error:', error);
                    localStorage.clear();
                }
            }

            showRegisterForm(e) {
                e.preventDefault();
                // TODO: Implement registration form
                this.showAlert('Registration feature coming soon!', 'success');
            }
        }

        // Initialize authentication manager
        document.addEventListener('DOMContentLoaded', () => {
            new AuthManager();
        });
    </script>
</body>
</html>'''

# Desktop page HTML content (embedded for now, could be moved to template)
DESKTOP_PAGE_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EmberFrame V2 - Desktop</title>
    <link rel="stylesheet" href="/static/css/main.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
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
                    <span>Text Editor</span>
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
                    <div class="date" style="font-size: 0.7rem; opacity: 0.8;">Mon, Jan 1</div>
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
    """Serve login page"""
    return HTMLResponse(content=LOGIN_PAGE_HTML)


@app.get("/desktop", response_class=HTMLResponse)
async def desktop_page():
    """Serve desktop page - requires authentication"""
    return HTMLResponse(content=DESKTOP_PAGE_HTML)


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
        "version": "2.0.0"
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

        # Check if test user exists
        existing = db.query(User).filter(User.username == "testuser").first()
        if existing:
            return {"message": "Test user already exists"}

        # Create test user
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