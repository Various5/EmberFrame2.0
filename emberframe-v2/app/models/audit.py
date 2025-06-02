"""
Audit log model
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    # User (optional - can be system actions)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Action details
    action = Column(String(100), nullable=False)  # login, file_upload, user_create, etc.
    resource_type = Column(String(50))  # user, file, system, etc.
    resource_id = Column(String(100))  # ID of affected resource

    # Context
    ip_address = Column(String(45))
    user_agent = Column(Text)
    details = Column(JSON)  # Additional details as JSON

    # Result
    success = Column(String(10), default="success")  # success, error, warning
    message = Column(Text)

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog {self.action}>"
