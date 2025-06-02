"""
EmberFrame V2 - Main Application Entry Point
"""

import uvicorn
from app import create_app
from app.core.config import get_settings
from app.core.database import create_tables
from app.utils.logging import setup_logging

# Setup logging
setup_logging()

# Create tables
create_tables()

# Create app
app = create_app()

if __name__ == "__main__":
    settings = get_settings()

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )
