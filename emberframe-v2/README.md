# EmberFrame V2 - Modern Web Desktop Environment

A powerful, modern web-based desktop environment built with FastAPI, SQLAlchemy, and modern web technologies.

## Features

- 🚀 **Fast & Modern**: Built with FastAPI for high performance
- 🔐 **Secure**: JWT authentication, secure file handling
- 📁 **File Management**: Complete file system with upload/download
- 👥 **Multi-user**: Support for multiple users with admin panel
- 🎨 **Customizable**: Themeable interface with user preferences
- 📱 **Responsive**: Works on desktop and mobile devices
- 🔄 **Real-time**: WebSocket support for notifications
- 📊 **Analytics**: Built-in audit logging and system monitoring

## Quick Start

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd emberframe-v2
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements/development.txt
   ```

4. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Initialize database**
   ```bash
   python scripts/init_db.py
   ```

6. **Run the application**
   ```bash
   python main.py
   ```

7. **Access the application**
   - Open http://localhost:8000
   - Default admin: admin/admin123

### Production Deployment

#### Using Docker Compose

1. **Clone and configure**
   ```bash
   git clone <repository-url>
   cd emberframe-v2
   cp .env.example .env
   # Configure production settings in .env
   ```

2. **Deploy**
   ```bash
   docker-compose up -d
   ```

#### Manual Deployment

1. **Install dependencies**
   ```bash
   pip install -r requirements/production.txt
   ```

2. **Set up database** (PostgreSQL recommended)
   ```bash
   # Configure DATABASE_URL in .env
   alembic upgrade head
   python scripts/init_db.py
   ```

3. **Run with Gunicorn**
   ```bash
   gunicorn main:app -c gunicorn.conf.py
   ```

## Architecture

### Backend (FastAPI)
- **API Layer**: RESTful endpoints with automatic OpenAPI docs
- **Services Layer**: Business logic and data processing
- **Models Layer**: SQLAlchemy ORM models
- **Core Layer**: Configuration, security, dependencies

### Frontend (Vanilla JS)
- **Desktop Environment**: Window management system
- **Applications**: Modular apps (file manager, text editor, etc.)
- **Utilities**: Helper functions and UI components

### Background Tasks (Celery)
- File processing and thumbnails
- System maintenance and cleanup
- Scheduled reports and notifications

## Development

### Project Structure
```
emberframe-v2/
├── app/                    # Main application
│   ├── api/               # API endpoints
│   ├── core/              # Core functionality
│   ├── models/            # Database models
│   ├── services/          # Business logic
│   ├── schemas/           # Pydantic schemas
│   ├── tasks/             # Background tasks
│   └── utils/             # Utilities
├── static/                # Frontend assets
├── templates/             # HTML templates
├── tests/                 # Test suite
├── requirements/          # Dependencies
└── scripts/               # Utility scripts
```

### Running Tests
```bash
pytest
```

### Code Quality
```bash
# Format code
black .
isort .

# Lint code
flake8 .
mypy .

# Run all checks
pre-commit run --all-files
```

### Database Migrations
```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Configuration

### Environment Variables
- `DEBUG`: Enable debug mode
- `SECRET_KEY`: JWT signing key
- `DATABASE_URL`: Database connection string
- `REDIS_URL`: Redis connection for caching/tasks
- `UPLOAD_DIR`: File upload directory
- `MAX_FILE_SIZE`: Maximum upload size

### Features Configuration
- User registration: `ALLOW_REGISTRATION`
- Admin panel: `ENABLE_ADMIN_PANEL`
- File sharing: `ENABLE_PUBLIC_FILES`
- Background tasks: `ENABLE_CELERY`

## API Documentation

When running in development mode:
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

### Key Endpoints
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `GET /api/files/` - List files
- `POST /api/files/upload` - Upload files
- `GET /api/admin/users` - Admin: List users

## Security

- JWT-based authentication
- Password hashing with bcrypt
- File upload validation
- Path traversal protection
- CORS configuration
- Rate limiting (TODO)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

### Development Guidelines
- Follow PEP 8 style guide
- Write comprehensive tests
- Update documentation
- Use conventional commits

## License

MIT License - see LICENSE file for details.

## Support

- 📖 **Documentation**: See `docs/` folder
- 🐛 **Issues**: GitHub Issues
- 💬 **Discussions**: GitHub Discussions
- 📧 **Email**: support@emberframe.com

---

**EmberFrame V2** - The future of web desktop environments 🔥
