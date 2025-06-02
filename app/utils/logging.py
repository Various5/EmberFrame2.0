"""
Logging configuration
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler


def setup_logging(
    log_level: str = "INFO",
    log_file: str = "logs/emberframe.log",
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
):
    """Setup application logging"""

    # Create logs directory
    log_dir = Path(log_file).parent
    log_dir.mkdir(exist_ok=True)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)

    # File handler
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_file_size,
        backupCount=backup_count
    )
    file_handler.setLevel(getattr(logging, log_level.upper()))
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(file_formatter)

    # Add handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Silence noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get logger instance"""
    return logging.getLogger(name)


class AuditLogger:
    """Special logger for audit events"""

    def __init__(self, log_file: str = "logs/audit.log"):
        self.logger = logging.getLogger("audit")
        self.logger.setLevel(logging.INFO)

        # Create handler if not exists
        if not self.logger.handlers:
            handler = TimedRotatingFileHandler(
                log_file,
                when="midnight",
                interval=1,
                backupCount=30
            )

            formatter = logging.Formatter(
                '%(asctime)s - AUDIT - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def log(self, action: str, user_id: int, details: str = ""):
        """Log audit event"""
        message = f"Action: {action} | User: {user_id} | Details: {details}"
        self.logger.info(message)


# Global audit logger instance
audit_logger = AuditLogger()
