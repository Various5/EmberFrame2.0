"""
File model
"""

from sqlalchemy import Column, Integer, String, DateTime, BigInteger, Boolean, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    path = Column(String(500), nullable=False, index=True)
    physical_path = Column(String(500), nullable=False)

    # File info
    size = Column(BigInteger, default=0)
    mime_type = Column(String(100))
    file_type = Column(String(50))  # document, image, video, etc.
    checksum = Column(String(64))  # SHA-256

    # Metadata
    is_public = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    description = Column(Text)
    tags = Column(Text)  # JSON array of tags

    # Owner
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    accessed_at = Column(DateTime(timezone=True))

    # Relationships
    owner = relationship("User", back_populates="files")

    def __repr__(self):
        return f"<File {self.name}>"

    @property
    def size_human(self):
        """Human readable file size"""
        if self.size == 0:
            return "0 B"

        size = self.size
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
