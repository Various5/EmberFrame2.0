# 🔥 EmberFrame V2 - Modern Web Desktop Environment

**EmberFrame V2** is a cutting-edge, full-featured web desktop environment that brings the power and familiarity of traditional desktop computing to the web browser. Built with modern technologies including FastAPI, React-like vanilla JavaScript, and comprehensive security features.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-00a393.svg)](https://fastapi.tiangolo.com)
[![Security: High](https://img.shields.io/badge/security-high-green.svg)](#security-features)

## 🌟 Features

### 🖥️ **Complete Desktop Environment**
- **Window Management**: Draggable, resizable windows with minimize/maximize controls
- **Taskbar**: Dynamic taskbar with running applications and system tray
- **File Manager**: Full-featured file explorer with upload/download capabilities
- **Desktop Icons**: Customizable desktop with application shortcuts
- **Context Menus**: Right-click context menus throughout the interface

### 📱 **Built-in Applications**
- **File Manager**: Browse, upload, download, and organize files
- **Text Editor**: Rich text editing with syntax highlighting
- **Image Viewer**: View and manage image files
- **Calculator**: Scientific calculator with memory functions
- **Terminal**: Command-line interface for advanced users
- **Settings**: Comprehensive system configuration

### 🔐 **Enterprise-Grade Security**
- **JWT Authentication**: Secure token-based authentication
- **Rate Limiting**: Prevent abuse with intelligent rate limiting
- **File Validation**: Comprehensive file type and size validation
- **Security Headers**: CSRF, XSS, and clickjacking protection
- **Audit Logging**: Complete audit trail of user actions
- **Session Management**: Secure session handling and cleanup

### 🎨 **Customization & Themes**
- **Multiple Themes**: Dark, light, and custom color schemes
- **User Preferences**: Personalized settings and layouts
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Accessibility**: WCAG compliant with keyboard navigation

### 🚀 **Performance & Scalability**
- **Real-time Updates**: WebSocket-based live notifications
- **Background Tasks**: Celery-powered asynchronous processing
- **Caching**: Redis-based caching for optimal performance
- **Database**: PostgreSQL with optimized queries
- **File Storage**: Local and cloud storage support (S3)

### 📊 **Admin Panel**
- **User Management**: Create, edit, and manage user accounts
- **System Monitoring**: Real-time system statistics and health
- **Security Dashboard**: Monitor failed logins and security events
- **Storage Analytics**: Track file usage and storage quotas
- **Audit Logs**: Comprehensive activity logging

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- PostgreSQL 13+ (or SQLite for development)
- Redis 6+ (for caching and background tasks)
- Node.js 16+ (for development tools, optional)

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/your-org/emberframe-v2.git
cd emberframe-v2

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements/development.txt
```

### 2. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit configuration (required!)
nano .env
```

**Essential settings to configure:**
```env
SECRET_KEY=your-super-secret-key-change-this
DATABASE_URL=postgresql://user:password@localhost/emberframe
REDIS_URL=redis://localhost:6379/0
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=change-this-secure-password
```

### 3. Database Setup

```bash
# Initialize database with default data
python scripts/init_db.py init

# Or manually create tables and admin user
python scripts/init_db.py create-user admin admin@example.com admin123 --admin
```

### 4. Launch Application

```bash
# Development mode
python main.py

# Or with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Access EmberFrame

Open your browser and navigate to:
- **Application**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/docs
- **Login**: Use the admin credentials from step 2

## 📁 Project Structure

```
emberframe-v2/
├── 📁 app/                     # Main application
│   ├── 📁 api/                # FastAPI endpoints
│   │   ├── auth.py            # Authentication routes
│   │   ├── files.py           # File management
│   │   ├── users.py           # User management
│   │   ├── admin.py           # Admin panel API
│   │   └── websocket.py       # Real-time features
│   │
│   ├── 📁 core/               # Core functionality
│   │   ├── config.py          # Configuration management
│   │   ├── database.py        # Database setup
│   │   ├── security.py        # Authentication & security
│   │   └── dependencies.py    # Dependency injection
│   │
│   ├── 📁 models/             # Database models
│   │   ├── user.py            # User model
│   │   ├── file.py            # File model
│   │   ├── session.py         # Session tracking
│   │   └── audit.py           # Audit logging
│   │
│   ├── 📁 services/           # Business logic
│   │   ├── auth_service.py    # Authentication logic
│   │   ├── file_service.py    # File operations
│   │   ├── user_service.py    # User management
│   │   └── audit_service.py   # Audit logging
│   │
│   ├── 📁 schemas/            # Pydantic schemas
│   │   ├── auth.py            # Authentication schemas
│   │   ├── user.py            # User schemas
│   │   └── file.py            # File schemas
│   │
│   ├── 📁 tasks/              # Background tasks
│   │   ├── file_tasks.py      # File processing
│   │   └── maintenance_tasks.py # System maintenance
│   │
│   └── 📁 utils/              # Utilities
│       ├── validators.py      # Input validation
│       ├── helpers.py         # Helper functions
│       └── logging.py         # Logging setup
│
├── 📁 static/                 # Frontend assets
│   ├── 📁 css/               # Stylesheets
│   ├── 📁 js/                # JavaScript modules
│   └── 📁 images/            # Static images
│
├── 📁 templates/             # HTML templates
├── 📁 tests/                 # Test suite
├── 📁 scripts/               # Utility scripts
├── 📁 requirements/          # Dependencies
├── 📁 config/                # Configuration files
└── 📁 docker/                # Docker configurations
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DEBUG` | Enable debug mode | `false` | No |
| `SECRET_KEY` | JWT signing key | None | **Yes** |
| `DATABASE_URL` | Database connection | SQLite | No |
| `REDIS_URL` | Redis connection | `redis://localhost:6379/0` | No |
| `UPLOAD_DIR` | File upload directory | `uploads` | No |
| `MAX_FILE_SIZE` | Max upload size (bytes) | `104857600` (100MB) | No |
| `ALLOWED_HOSTS` | Allowed hostnames | `["*"]` | No |

### Database Configuration

**SQLite (Development):**
```env
DATABASE_URL=sqlite:///./emberframe.db
```

**PostgreSQL (Production):**
```env
DATABASE_URL=postgresql://username:password@localhost:5432/emberframe
```

### Redis Configuration

**Local Redis:**
```env
REDIS_URL=redis://localhost:6379/0
```

**Redis with password:**
```env
REDIS_URL=redis://:password@localhost:6379/0
```

### File Storage Options

**Local Storage (Default):**
```env
UPLOAD_DIR=uploads
```

**AWS S3 Storage:**
```env
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1
S3_BUCKET=emberframe-files
```

## 🏗️ Development

### Development Setup

```bash
# Install development dependencies
pip install -r requirements/development.txt

# Install pre-commit hooks
pre-commit install

# Run development server with auto-reload
python main.py
```

### Code Quality Tools

```bash
# Format code
black .
isort .

# Lint code
flake8 .
mypy .

# Run tests
pytest

# Run tests with coverage
pytest --cov=app --cov-report=html
```

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Creating New Applications

1. **Create application directory:**
```bash
mkdir static/js/apps/myapp
```

2. **Create application JavaScript:**
```javascript
// static/js/apps/myapp/myapp.js
class MyApp {
    constructor(windowId) {
        this.windowId = windowId;
        this.init();
    }
    
    init() {
        // Initialize your application
    }
    
    getHTML() {
        return `<div>My Application Content</div>`;
    }
}
```

3. **Register in desktop.js:**
```javascript
this.apps.set('myapp', {
    name: 'My Application',
    icon: 'fas fa-star',
    component: 'MyApp'
});
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/          # Unit tests
pytest tests/integration/   # Integration tests
pytest tests/e2e/          # End-to-end tests

# Run with coverage
pytest --cov=app --cov-report=html --cov-report=term-missing

# Run performance tests
pytest tests/performance/ -m performance
```

### Test Categories

- **Unit Tests**: Test individual functions and classes
- **Integration Tests**: Test API endpoints and services
- **End-to-End Tests**: Test complete user workflows
- **Performance Tests**: Test system performance and scalability
- **Security Tests**: Test security features and vulnerabilities

### Writing Tests

```python
# tests/test_example.py
import pytest
from fastapi.testclient import TestClient

def test_user_registration(client):
    """Test user registration endpoint"""
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "password123"
    }
    
    response = client.post("/api/auth/register", json=user_data)
    
    assert response.status_code == 200
    assert "access_token" in response.json()
```

## 🚢 Production Deployment

### Docker Deployment

```bash
# Build and deploy with Docker Compose
docker-compose -f docker-compose.prod.yml up -d

# Or use the deployment script
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

### Manual Production Setup

1. **Install dependencies:**
```bash
pip install -r requirements/production.txt
```

2. **Configure environment:**
```bash
cp .env.production .env
# Edit .env with production settings
```

3. **Setup database:**
```bash
# Run migrations
alembic upgrade head

# Create admin user
python scripts/init_db.py create-user admin admin@yourdom.com secure_password --admin
```

4. **Configure web server (Nginx):**
```nginx
# /etc/nginx/sites-available/emberframe
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

5. **Run with Gunicorn:**
```bash
gunicorn main:app -c gunicorn.conf.py
```

### Environment-Specific Configurations

**Development:**
- SQLite database
- Debug mode enabled
- Auto-reload
- Detailed error messages

**Staging:**
- PostgreSQL database
- Debug mode disabled
- Basic monitoring
- Similar to production

**Production:**
- PostgreSQL with SSL
- Redis cluster
- Comprehensive monitoring
- Security hardening
- Load balancing

## 🔐 Security Features

### Authentication & Authorization
- **JWT Tokens**: Secure stateless authentication
- **Password Hashing**: Bcrypt with salt rounds
- **Session Management**: Secure session tracking
- **Role-Based Access**: User and admin roles
- **Two-Factor Auth**: TOTP support (optional)

### Data Protection
- **Input Validation**: Comprehensive input sanitization
- **SQL Injection Prevention**: Parameterized queries
- **XSS Protection**: Content Security Policy
- **CSRF Protection**: Token-based CSRF prevention
- **File Upload Security**: Type and size validation

### Network Security
- **Rate Limiting**: Prevent brute force attacks
- **IP Blocking**: Automatic suspicious IP blocking
- **HTTPS Enforcement**: SSL/TLS encryption
- **Security Headers**: HSTS, CSP, X-Frame-Options
- **CORS Configuration**: Controlled cross-origin requests

### Monitoring & Auditing
- **Audit Logging**: Complete activity tracking
- **Security Events**: Failed login monitoring
- **Real-time Alerts**: Suspicious activity notifications
- **Performance Monitoring**: System health tracking

## 📊 Monitoring & Analytics

### Built-in Monitoring

**System Metrics:**
- CPU and memory usage
- Database performance
- File storage usage
- Active user sessions

**User Analytics:**
- Login patterns
- Feature usage
- File upload/download stats
- Session duration

**Security Monitoring:**
- Failed login attempts
- Suspicious IP addresses
- Rate limit violations
- Security alerts

### External Monitoring

**Prometheus Integration:**
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'emberframe'
    static_configs:
      - targets: ['localhost:8000']
```

**Grafana Dashboards:**
- System performance metrics
- User activity analytics
- Security event monitoring
- Business intelligence reports

**Log Aggregation:**
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Grafana Loki
- Centralized logging

## 🔧 Troubleshooting

### Common Issues

**Database Connection Errors:**
```bash
# Check database status
pg_isready -h localhost -p 5432

# Verify connection string
python -c "from app.core.database import engine; print(engine.url)"
```

**Redis Connection Issues:**
```bash
# Test Redis connection
redis-cli ping

# Check Redis configuration
redis-cli config get "*"
```

**File Upload Problems:**
```bash
# Check upload directory permissions
ls -la uploads/

# Verify disk space
df -h

# Check file size limits
grep MAX_FILE_SIZE .env
```

**Performance Issues:**
```bash
# Monitor system resources
htop

# Check database queries
tail -f logs/emberframe.log | grep "slow"

# Monitor Redis memory
redis-cli info memory
```

### Debug Mode

Enable debug mode for detailed error information:
```env
DEBUG=true
```

**Debug Features:**
- Detailed error traces
- SQL query logging
- Request/response logging
- Auto-reload on code changes

### Logging Configuration

```python
# app/utils/logging.py
import logging

# Configure logging levels
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'detailed': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/emberframe.log',
            'formatter': 'detailed',
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['file']
    }
}
```

## 🤝 Contributing

We welcome contributions to EmberFrame V2! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Workflow

1. **Fork the repository**
2. **Create a feature branch:**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes and add tests**
4. **Run the test suite:**
   ```bash
   pytest
   flake8 .
   black .
   ```
5. **Commit your changes:**
   ```bash
   git commit -m "Add amazing feature"
   ```
6. **Push to your fork:**
   ```bash
   git push origin feature/amazing-feature
   ```
7. **Open a Pull Request**

### Code Standards

- **Python**: Follow PEP 8, use Black for formatting
- **JavaScript**: Use modern ES6+ features, consistent naming
- **Documentation**: Document all public APIs
- **Testing**: Maintain >80% code coverage
- **Security**: Follow OWASP guidelines

### Reporting Issues

Please use GitHub Issues to report bugs or request features:

- **Bug Reports**: Include steps to reproduce, expected vs actual behavior
- **Feature Requests**: Describe the use case and proposed solution
- **Security Issues**: Report privately to security@emberframe.com

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **FastAPI**: For the excellent async web framework
- **SQLAlchemy**: For powerful database ORM
- **Redis**: For caching and background task queue
- **PostgreSQL**: For reliable data storage
- **Font Awesome**: For beautiful icons
- **The Open Source Community**: For inspiration and contributions

## 📞 Support

### Community Support
- **GitHub Issues**: Bug reports and feature requests
- **Discussions**: Community Q&A and feature discussions
- **Wiki**: Additional documentation and tutorials

### Commercial Support
For enterprise support, custom development, and consulting:
- **Email**: enterprise@emberframe.com
- **Website**: https://emberframe.com/enterprise

### Security Issues
For security-related issues:
- **Email**: varous555@gmail.com
- **PGP Key**: Available on our website

---

## 🚀 What's Next?

EmberFrame V2 is actively developed with exciting features planned:

### Upcoming Features
- **📱 Mobile App**: Native mobile applications
- **🔗 Federation**: Multi-instance connectivity
- **🤖 AI Integration**: Smart file organization and search
- **📊 Advanced Analytics**: Business intelligence features
- **🎮 App Store**: Third-party application ecosystem
- **☁️ Cloud Sync**: Multi-device synchronization

### Roadmap
- **Q2 2025**: Mobile applications, advanced security features
- **Q3 2025**: AI integration, federated authentication
- **Q4 2025**: App marketplace, enterprise features
- **2025**: Cloud platform, advanced analytics

---

**Made with ❤️ by the EmberFrame Team**

*EmberFrame V2 - Where the future of web desktop computing begins* 🔥

[⬆ Back to top](#-emberframe-v2---modern-web-desktop-environment)