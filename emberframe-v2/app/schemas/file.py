"""
File schemas
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class FileBase(BaseModel):
    name: str
    is_public: Optional[bool] = False


class FileCreate(FileBase):
    path: str
    size: int
    mime_type: Optional[str] = None


class FileResponse(FileBase):
    id: int
    path: str
    size: int
    mime_type: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class FileList(BaseModel):
    files: List[FileResponse]
    total: int
    page: int
    per_page: int


class FolderCreate(BaseModel):
    name: str
    path: Optional[str] = ""
