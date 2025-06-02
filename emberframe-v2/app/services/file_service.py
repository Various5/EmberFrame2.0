"""
File management service
"""

import os
import hashlib
import shutil
from typing import List, Optional
from pathlib import Path
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.models.file import File
from app.models.user import User
from app.core.config import get_settings
from app.services.audit_service import AuditService

settings = get_settings()


class FileService:
    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.upload_dir.mkdir(exist_ok=True)

    def _get_user_dir(self, user_id: int) -> Path:
        """Get user's upload directory"""
        user_dir = self.upload_dir / str(user_id)
        user_dir.mkdir(exist_ok=True)
        return user_dir

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate file SHA-256 checksum"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    async def list_files(self, user_id: int, path: str = "") -> dict:
        """List files in user directory"""
        user_dir = self._get_user_dir(user_id)
        target_dir = user_dir / path if path else user_dir

        if not target_dir.exists() or not target_dir.is_dir():
            raise HTTPException(status_code=404, detail="Directory not found")

        files = []
        for item in target_dir.iterdir():
            if item.is_file():
                file_record = self.db.query(File).filter(
                    File.owner_id == user_id,
                    File.physical_path == str(item)
                ).first()

                files.append({
                    "name": item.name,
                    "type": "file",
                    "size": item.stat().st_size if file_record else 0,
                    "modified": item.stat().st_mtime,
                    "is_public": file_record.is_public if file_record else False
                })
            elif item.is_dir():
                files.append({
                    "name": item.name,
                    "type": "folder",
                    "size": 0,
                    "modified": item.stat().st_mtime
                })

        return {"files": files, "path": path}

    async def upload_files(self, user_id: int, files: List[UploadFile], path: str = "") -> dict:
        """Upload files for user"""
        user_dir = self._get_user_dir(user_id)
        target_dir = user_dir / path if path else user_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        uploaded_files = []

        for file in files:
            # Check file size
            if file.size > settings.MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"File {file.filename} exceeds maximum size"
                )

            # Save file
            file_path = target_dir / file.filename
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # Create file record
            checksum = self._calculate_checksum(file_path)
            file_record = File(
                name=file.filename,
                original_name=file.filename,
                path=f"{path}/{file.filename}" if path else file.filename,
                physical_path=str(file_path),
                size=file_path.stat().st_size,
                mime_type=file.content_type,
                checksum=checksum,
                owner_id=user_id
            )

            self.db.add(file_record)
            uploaded_files.append(file.filename)

        self.db.commit()

        await self.audit_service.log_action(
            "file_upload",
            "file",
            f"{len(uploaded_files)} files",
            user_id
        )

        return {"uploaded_files": uploaded_files, "count": len(uploaded_files)}

    async def get_file(self, user_id: int, file_path: str) -> File:
        """Get file by path"""
        file_record = self.db.query(File).filter(
            File.owner_id == user_id,
            File.path == file_path
        ).first()

        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")

        return file_record

    async def delete_file(self, user_id: int, file_path: str) -> dict:
        """Delete file"""
        file_record = await self.get_file(user_id, file_path)

        # Delete physical file
        physical_path = Path(file_record.physical_path)
        if physical_path.exists():
            if physical_path.is_file():
                physical_path.unlink()
            elif physical_path.is_dir():
                shutil.rmtree(physical_path)

        # Delete record
        self.db.delete(file_record)
        self.db.commit()

        await self.audit_service.log_action("file_delete", "file", file_path, user_id)

        return {"message": "File deleted successfully"}

    async def create_folder(self, user_id: int, path: str, name: str) -> dict:
        """Create folder"""
        user_dir = self._get_user_dir(user_id)
        folder_path = user_dir / path / name if path else user_dir / name

        if folder_path.exists():
            raise HTTPException(status_code=400, detail="Folder already exists")

        folder_path.mkdir(parents=True)

        await self.audit_service.log_action("folder_create", "file", f"{path}/{name}", user_id)

        return {"message": "Folder created successfully"}

    async def get_file_count(self) -> int:
        """Get total file count"""
        return self.db.query(File).count()

    async def get_storage_usage(self) -> int:
        """Get total storage usage"""
        result = self.db.query(func.sum(File.size)).scalar()
        return result or 0
