# README.md
# EmberFrame V2 🔥

**Next-Generation Web Desktop Environment**

EmberFrame V2 is a modern, full-featured web-based desktop environment with advanced file management, real-time collaboration, and extensive customization options.

## ✨ Features

### 🖥️ Desktop Environment
- **Modern UI**: Glass-morphism design with smooth animations
- **Multiple Themes**: Built-in themes with dark/light mode support
- **Responsive Design**: Works perfectly on desktop, tablet, and mobile
- **Real-time Updates**: WebSocket-powered live notifications

### 📁 Advanced File Management
- **Drag & Drop**: Intuitive file uploads and organization
- **File Versioning**: Track and restore file versions
- **Smart Search**: Full-text search with filters and suggestions
- **File Sharing**: Secure sharing with permissions and expiration
- **Thumbnails**: Automatic thumbnail generation for images and videos

### 🔐 Enterprise Security
- **Multi-Factor Authentication**: TOTP-based 2FA support
- **Advanced Password Security**: Strength validation and breach checking
- **Session Management**: Multiple session tracking and control
- **Audit Logging**: Comprehensive activity tracking
- **Rate Limiting**: Protection against abuse and attacks

### 🚀 Performance & Scalability
- **Async Architecture**: Built on FastAPI with async/await
- **Redis Caching**: Fast data access and session storage
- **Background Tasks**: Celery-powered task processing
- **Database Optimization**: Efficient SQLAlchemy queries
- **CDN Ready**: Static asset optimization

### 🔧 Developer Experience
- **RESTful API**: Comprehensive API with OpenAPI documentation
- **WebSocket Support**: Real-time bidirectional communication
- **Docker Ready**: Complete containerization with Docker Compose
- **Test Coverage**: Extensive test suite with 80%+ coverage
- **Type Safety**: Full TypeScript and Python type annotations

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+ (for frontend development)
- PostgreSQL 13+ (or SQLite for development)
- Redis 6+

### Development Setup

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/emberframe-v2.git
cd emberframe-v2
```

2. **Run the setup script**
```bash
chmod +x scripts/setup.sh
./scripts/setup.sh dev
```

3. **Start the development server**
```bash
./scripts/run.sh dev
```

4. **Access the application**
- Web Interface: http://localhost:8000
- API Documentation: http://localhost:8000/api/docs
- Admin Panel: http://localhost:8000/admin

### Production Deployment

#### Docker Deployment (Recommended)

1. **Setup with Docker**
```bash
chmod +x scripts/docker-setup.sh
./scripts/docker-setup.sh
```

2. **Configure environment**
```bash
# Edit production settings
nano .env
```

3. **Deploy**
```bash
docker-compose -f docker-compose.yml up -d
```

#### Manual Deployment

1. **Setup production environment**
```bash
./scripts/setup.sh
```

2. **Configure web server** (Nginx example)
```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /ws/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## 📖 Documentation

### API Documentation
- **OpenAPI Docs**: `/api/docs` (Swagger UI)
- **ReDoc**: `/api/redoc` (Alternative documentation)
- **OpenAPI JSON**: `/api/openapi.json`

### Architecture Overview

```
├── app/
│   ├── api/           # API endpoints
│   ├── core/          # Core functionality (database, security, config)
│   ├── models/        # SQLAlchemy models
│   ├── schemas/       # Pydantic schemas
│   ├── services/      # Business logic services
│   ├── tasks/         # Background tasks
│   └── utils/         # Utility functions
├── static/
│   ├── css/           # Stylesheets
│   ├── js/            # JavaScript applications
│   └── assets/        # Images, fonts, etc.
├── tests/             # Test suite
├── scripts/           # Deployment and utility scripts
└── requirements/      # Python dependencies
```

### Key Technologies

- **Backend**: FastAPI, SQLAlchemy, Redis, Celery
- **Frontend**: Vanilla JavaScript, CSS3, WebSockets
- **Database**: PostgreSQL (production), SQLite (development)
- **Caching**: Redis
- **Security**: JWT, bcrypt, rate limiting
- **Deployment**: Docker, Nginx, Gunicorn

## 🧪 Testing

Run the complete test suite:

```bash
./scripts/test.sh
```

Run specific test categories:

```bash
# Unit tests only
pytest tests/test_*.py -v

# Integration tests
pytest tests/test_integration.py -v

# API tests
pytest tests/test_api.py -v
```

## 🔧 Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# Application
APP_NAME=EmberFrame V2
DEBUG=false
SECRET_KEY=your-secret-key

# Database
DATABASE_URL=postgresql://user:pass@localhost/emberframe

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
ALLOWED_HOSTS=["your-domain.com"]
SESSION_EXPIRE=86400
TOKEN_EXPIRE_HOURS=24

# File Storage
UPLOAD_DIR=uploads
MAX_FILE_SIZE=104857600

# Email (Optional)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your-email@example.com
SMTP_PASSWORD=your-password
```

### Advanced Configuration

For advanced configuration options, see:
- `app/core/config.py` - Application settings
- `gunicorn.conf.py` - WSGI server configuration
- `docker-compose.yml` - Container orchestration

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and add tests
4. Run the test suite: `./scripts/test.sh`
5. Commit your changes: `git commit -m 'Add amazing feature'`
6. Push to the branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [Wiki](https://github.com/yourusername/emberframe-v2/wiki)
- **Issues**: [GitHub Issues](https://github.com/yourusername/emberframe-v2/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/emberframe-v2/discussions)
- **Email**: support@emberframe.com

## 🎯 Roadmap

### Version 2.1 (Q2 2024)
- [ ] Mobile application (React Native)
- [ ] Advanced collaboration features
- [ ] Plugin system
- [ ] Enhanced analytics dashboard

### Version 2.2 (Q3 2024)
- [ ] AI-powered file organization
- [ ] Advanced workflow automation
- [ ] Third-party integrations (Slack, Teams)
- [ ] Performance optimizations

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) for the amazing web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) for database ORM
- [Redis](https://redis.io/) for caching and sessions
- [Celery](https://docs.celeryproject.org/) for background tasks
- All our contributors and users!

---