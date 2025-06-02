"""
File management API endpoints
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from typing import List
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.services.file_service import FileService
from app.models.user import User

files_router = APIRouter()


@files_router.get("/")
async def list_files(
    path: str = "",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List files in directory"""
    file_service = FileService(db)
    return await file_service.list_files(user.id, path)


@files_router.post("/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    path: str = "",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload files"""
    file_service = FileService(db)
    return await file_service.upload_files(user.id, files, path)


@files_router.get("/download/{file_path:path}")
async def download_file(
    file_path: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download file"""
    file_service = FileService(db)
    file_info = await file_service.get_file(user.id, file_path)
    return FileResponse(
        path=file_info.physical_path,
        filename=file_info.name,
        media_type='application/octet-stream'
    )


@files_router.delete("/{file_path:path}")
async def delete_file(
    file_path: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete file or folder"""
    file_service = FileService(db)
    return await file_service.delete_file(user.id, file_path)


@files_router.post("/folder")
async def create_folder(
    path: str,
    name: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new folder"""
    file_service = FileService(db)
    return await file_service.create_folder(user.id, path, name)
