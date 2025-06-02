"""
Enhanced File management service with security and advanced features
"""

import os
import hashlib
import shutil
import mimetypes
from typing import List, Optional, Dict, Any
from pathlib import Path
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from PIL import Image
import magic

from app.models.file import File
from app.models.user import User
from app.core.config import get_settings
from app.services.audit_service import AuditService
from app.utils.validators import validate_file_type, validate_file_size, validate_path, sanitize_filename
from app.utils.helpers import format_file_size

settings = get_settings()


class FileService:
    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.upload_dir.mkdir(exist_ok=True)

        # Allowed file types
        self.allowed_extensions = {
            'image': ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'],
            'document': ['txt', 'md', 'pdf', 'doc', 'docx', 'rtf', 'odt'],
            'archive': ['zip', 'rar', '7z', 'tar', 'gz'],
            'audio': ['mp3', 'wav', 'ogg', 'flac', 'm4a'],
            'video': ['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv'],
            'code': ['py', 'js', 'html', 'css', 'json', 'xml', 'sql']
        }

        # Max file sizes by type (in bytes)
        self.max_file_sizes = {
            'image': 10 * 1024 * 1024,    # 10MB
            'document': 50 * 1024 * 1024,  # 50MB
            'archive': 100 * 1024 * 1024,  # 100MB
            'audio': 50 * 1024 * 1024,     # 50MB
            'video': 500 * 1024 * 1024,    # 500MB
            'code': 5 * 1024 * 1024        # 5MB
        }

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

    def _detect_file_type(self, file_path: Path) -> tuple[str, str]:
        """Detect file type and MIME type"""
        try:
            # Use python-magic for accurate MIME type detection
            mime_type = magic.from_file(str(file_path), mime=True)
        except:
            # Fallback to mimetypes module
            mime_type, _ = mimetypes.guess_type(str(file_path))
            mime_type = mime_type or 'application/octet-stream'

        # Determine file category
        ext = file_path.suffix.lower().lstrip('.')
        for category, extensions in self.allowed_extensions.items():
            if ext in extensions:
                return category, mime_type

        return 'other', mime_type

    def _validate_file(self, file: UploadFile, file_type: str) -> None:
        """Validate uploaded file"""
        # Check file size
        max_size = self.max_file_sizes.get(file_type, settings.MAX_FILE_SIZE)
        if file.size > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum allowed size for {file_type} files ({format_file_size(max_size)})"
            )

        # Check file extension
        if file.filename:
            ext = file.filename.split('.')[-1].lower()
            allowed_exts = self.allowed_extensions.get(file_type, [])
            if allowed_exts and ext not in allowed_exts:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File type .{ext} not allowed for {file_type} files"
                )

    def _create_thumbnail(self, file_path: Path) -> Optional[Path]:
        """Create thumbnail for image files"""
        try:
            if file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp', '.webp']:
                thumbnail_dir = file_path.parent / 'thumbnails'
                thumbnail_dir.mkdir(exist_ok=True)
                thumbnail_path = thumbnail_dir / f"thumb_{file_path.name}"

                with Image.open(file_path) as img:
                    # Convert to RGB if necessary
                    if img.mode in ('RGBA', 'LA', 'P'):
                        img = img.convert('RGB')

                    # Create thumbnail
                    img.thumbnail((200, 200), Image.Resampling.LANCZOS)
                    img.save(thumbnail_path, 'JPEG', quality=85)

                return thumbnail_path
        except Exception as e:
            print(f"Thumbnail creation failed: {e}")

        return None

    def _check_storage_quota(self, user_id: int, additional_size: int) -> None:
        """Check if user has enough storage quota"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.storage_used + additional_size > user.storage_quota:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Storage quota exceeded. Available: {format_file_size(user.storage_quota - user.storage_used)}"
            )

    def _update_storage_usage(self, user_id: int, size_delta: int) -> None:
        """Update user's storage usage"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if user:
            user.storage_used = max(0, user.storage_used + size_delta)
            self.db.commit()

    async def list_files(self, user_id: int, path: str = "", page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        """List files in user directory with pagination"""
        if not validate_path(path):
            raise HTTPException(status_code=400, detail="Invalid path")

        user_dir = self._get_user_dir(user_id)
        target_dir = user_dir / path.lstrip('/') if path else user_dir

        if not target_dir.exists() or not target_dir.is_dir():
            raise HTTPException(status_code=404, detail="Directory not found")

        # Security check: ensure target_dir is within user directory
        try:
            target_dir.resolve().relative_to(user_dir.resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied")

        files = []
        folders = []

        # Get items from filesystem
        try:
            for item in target_dir.iterdir():
                if item.is_file():
                    # Get file record from database
                    relative_path = str(item.relative_to(user_dir))
                    file_record = self.db.query(File).filter(
                        and_(File.owner_id == user_id, File.path == relative_path)
                    ).first()

                    file_info = {
                        "name": item.name,
                        "type": "file",
                        "size": item.stat().st_size,
                        "modified": item.stat().st_mtime,
                        "path": relative_path,
                        "is_public": file_record.is_public if file_record else False,
                        "mime_type": file_record.mime_type if file_record else None,
                        "file_type": file_record.file_type if file_record else None,
                        "checksum": file_record.checksum if file_record else None
                    }
                    files.append(file_info)

                elif item.is_dir() and not item.name.startswith('.'):
                    folder_info = {
                        "name": item.name,
                        "type": "folder",
                        "size": 0,
                        "modified": item.stat().st_mtime,
                        "path": str(item.relative_to(user_dir))
                    }
                    folders.append(folder_info)
        except PermissionError:
            raise HTTPException(status_code=403, detail="Permission denied")

        # Sort files and folders
        folders.sort(key=lambda x: x['name'].lower())
        files.sort(key=lambda x: x['name'].lower())

        all_items = folders + files

        # Pagination
        total = len(all_items)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_items = all_items[start_idx:end_idx]

        return {
            "files": paginated_items,
            "path": path,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page
        }

    async def upload_files(self, user_id: int, files: List[UploadFile], path: str = "") -> Dict[str, Any]:
        """Upload files for user with validation and security checks"""
        if not validate_path(path):
            raise HTTPException(status_code=400, detail="Invalid path")

        user_dir = self._get_user_dir(user_id)
        target_dir = user_dir / path.lstrip('/') if path else user_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        # Security check
        try:
            target_dir.resolve().relative_to(user_dir.resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied")

        uploaded_files = []
        total_size = sum(file.size for file in files)

        # Check storage quota
        self._check_storage_quota(user_id, total_size)

        for file in files:
            if not file.filename:
                continue

            # Sanitize filename
            safe_filename = sanitize_filename(file.filename)
            file_path = target_dir / safe_filename

            # Handle duplicate filenames
            counter = 1
            original_path = file_path
            while file_path.exists():
                name_parts = safe_filename.rsplit('.', 1)
                if len(name_parts) == 2:
                    new_name = f"{name_parts[0]}_{counter}.{name_parts[1]}"
                else:
                    new_name = f"{safe_filename}_{counter}"
                file_path = target_dir / new_name
                counter += 1

            # Detect file type
            temp_path = file_path.with_suffix('.tmp')

            try:
                # Save file temporarily
                with open(temp_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)

                # Detect file type and validate
                file_type, mime_type = self._detect_file_type(temp_path)
                self._validate_file(file, file_type)

                # Move to final location
                shutil.move(str(temp_path), str(file_path))

                # Calculate checksum
                checksum = self._calculate_checksum(file_path)

                # Create thumbnail for images
                thumbnail_path = self._create_thumbnail(file_path)

                # Create file record
                relative_path = str(file_path.relative_to(user_dir))
                file_record = File(
                    name=file_path.name,
                    original_name=file.filename,
                    path=relative_path,
                    physical_path=str(file_path),
                    size=file_path.stat().st_size,
                    mime_type=mime_type,
                    file_type=file_type,
                    checksum=checksum,
                    owner_id=user_id
                )

                self.db.add(file_record)
                uploaded_files.append({
                    "name": file_path.name,
                    "original_name": file.filename,
                    "size": file_path.stat().st_size,
                    "type": file_type,
                    "mime_type": mime_type,
                    "path": relative_path,
                    "has_thumbnail": thumbnail_path is not None
                })

            except Exception as e:
                # Clean up temporary file
                if temp_path.exists():
                    temp_path.unlink()
                raise HTTPException(status_code=400, detail=f"Failed to upload {file.filename}: {str(e)}")

        # Update storage usage
        self._update_storage_usage(user_id, total_size)

        # Commit all file records
        self.db.commit()

        # Log upload activity
        await self.audit_service.log_action(
            "file_upload",
            "file",
            f"{len(uploaded_files)} files to {path}",
            user_id,
            details={"file_count": len(uploaded_files), "total_size": total_size}
        )

        return {
            "uploaded_files": uploaded_files,
            "count": len(uploaded_files),
            "total_size": total_size
        }

    async def get_file(self, user_id: int, file_path: str) -> File:
        """Get file by path with security checks"""
        if not validate_path(file_path):
            raise HTTPException(status_code=400, detail="Invalid file path")

        file_record = self.db.query(File).filter(
            and_(File.owner_id == user_id, File.path == file_path)
        ).first()

        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")

        # Check if physical file exists
        if not Path(file_record.physical_path).exists():
            raise HTTPException(status_code=404, detail="Physical file not found")

        return file_record

    async def download_file(self, user_id: int, file_path: str) -> tuple[Path, str]:
        """Get file path for download"""
        file_record = await self.get_file(user_id, file_path)

        # Update access time
        file_record.accessed_at = func.now()
        self.db.commit()

        # Log download activity
        await self.audit_service.log_action(
            "file_download",
            "file",
            file_path,
            user_id
        )

        return Path(file_record.physical_path), file_record.mime_type

    async def delete_file(self, user_id: int, file_path: str) -> Dict[str, str]:
        """Delete file with security checks"""
        file_record = await self.get_file(user_id, file_path)

        # Delete physical file
        physical_path = Path(file_record.physical_path)
        file_size = 0

        if physical_path.exists():
            file_size = physical_path.stat().st_size
            if physical_path.is_file():
                physical_path.unlink()

                # Delete thumbnail if exists
                thumbnail_path = physical_path.parent / 'thumbnails' / f"thumb_{physical_path.name}"
                if thumbnail_path.exists():
                    thumbnail_path.unlink()
            elif physical_path.is_dir():
                shutil.rmtree(physical_path)

        # Update storage usage
        self._update_storage_usage(user_id, -file_size)

        # Delete record
        self.db.delete(file_record)
        self.db.commit()

        # Log deletion
        await self.audit_service.log_action(
            "file_delete",
            "file",
            file_path,
            user_id,
            details={"file_size": file_size}
        )

        return {"message": "File deleted successfully"}

    async def create_folder(self, user_id: int, path: str, name: str) -> Dict[str, str]:
        """Create folder with validation"""
        if not validate_path(path) or not name:
            raise HTTPException(status_code=400, detail="Invalid path or folder name")

        # Sanitize folder name
        safe_name = sanitize_filename(name)
        if not safe_name:
            raise HTTPException(status_code=400, detail="Invalid folder name")

        user_dir = self._get_user_dir(user_id)
        parent_dir = user_dir / path.lstrip('/') if path else user_dir
        folder_path = parent_dir / safe_name

        # Security check
        try:
            folder_path.resolve().relative_to(user_dir.resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied")

        if folder_path.exists():
            raise HTTPException(status_code=400, detail="Folder already exists")

        folder_path.mkdir(parents=True)

        # Log folder creation
        await self.audit_service.log_action(
            "folder_create",
            "file",
            f"{path}/{safe_name}",
            user_id
        )

        return {"message": "Folder created successfully", "name": safe_name}

    async def rename_file(self, user_id: int, file_path: str, new_name: str) -> Dict[str, str]:
        """Rename file or folder"""
        if not validate_path(file_path) or not new_name:
            raise HTTPException(status_code=400, detail="Invalid path or name")

        safe_name = sanitize_filename(new_name)
        if not safe_name:
            raise HTTPException(status_code=400, detail="Invalid new name")

        user_dir = self._get_user_dir(user_id)
        old_path = user_dir / file_path.lstrip('/')
        new_path = old_path.parent / safe_name

        # Security checks
        try:
            old_path.resolve().relative_to(user_dir.resolve())
            new_path.resolve().relative_to(user_dir.resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied")

        if not old_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        if new_path.exists():
            raise HTTPException(status_code=400, detail="Target name already exists")

        # Rename physical file/folder
        old_path.rename(new_path)

        # Update database record if it's a file
        if old_path.is_file():
            file_record = self.db.query(File).filter(
                and_(File.owner_id == user_id, File.path == file_path)
            ).first()

            if file_record:
                file_record.name = safe_name
                file_record.path = str(new_path.relative_to(user_dir))
                file_record.physical_path = str(new_path)
                self.db.commit()

        # Log rename activity
        await self.audit_service.log_action(
            "file_rename",
            "file",
            f"{file_path} -> {safe_name}",
            user_id
        )

        return {"message": "Renamed successfully", "new_name": safe_name}

    async def search_files(self, user_id: int, query: str, file_type: str = None) -> List[Dict[str, Any]]:
        """Search files by name and content"""
        if not query or len(query) < 2:
            raise HTTPException(status_code=400, detail="Query too short")

        # Build database query
        db_query = self.db.query(File).filter(File.owner_id == user_id)

        # Add search filters
        if file_type:
            db_query = db_query.filter(File.file_type == file_type)

        # Search by filename
        db_query = db_query.filter(File.name.ilike(f"%{query}%"))

        files = db_query.limit(50).all()

        results = []
        for file in files:
            results.append({
                "name": file.name,
                "path": file.path,
                "size": file.size,
                "type": file.file_type,
                "mime_type": file.mime_type,
                "modified": file.updated_at or file.created_at
            })

        # Log search activity
        await self.audit_service.log_action(
            "file_search",
            "file",
            query,
            user_id,
            details={"results_count": len(results), "file_type": file_type}
        )

        return results

    async def get_file_count(self) -> int:
        """Get total file count"""
        return self.db.query(File).count()

    async def get_storage_usage(self) -> Dict[str, int]:
        """Get storage usage statistics"""
        total_size = self.db.query(func.sum(File.size)).scalar() or 0
        total_files = self.db.query(File).count()

        # Get usage by file type
        usage_by_type = self.db.query(
            File.file_type,
            func.sum(File.size).label('total_size'),
            func.count(File.id).label('file_count')
        ).group_by(File.file_type).all()

        return {
            "total_size": total_size,
            "total_files": total_files,
            "usage_by_type": [
                {
                    "type": row.file_type,
                    "size": row.total_size,
                    "count": row.file_count
                }
                for row in usage_by_type
            ]
        }

    async def get_user_storage_stats(self, user_id: int) -> Dict[str, Any]:
        """Get storage statistics for a specific user"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get file count and size by type
        stats = self.db.query(
            File.file_type,
            func.sum(File.size).label('total_size'),
            func.count(File.id).label('file_count')
        ).filter(File.owner_id == user_id).group_by(File.file_type).all()

        usage_by_type = [
            {
                "type": row.file_type or "unknown",
                "size": row.total_size or 0,
                "count": row.file_count
            }
            for row in stats
        ]

        return {
            "storage_used": user.storage_used,
            "storage_quota": user.storage_quota,
            "storage_percentage": (user.storage_used / user.storage_quota * 100) if user.storage_quota > 0 else 0,
            "total_files": sum(stat["count"] for stat in usage_by_type),
            "usage_by_type": usage_by_type
        }

    async def cleanup_orphaned_files(self) -> Dict[str, int]:
        """Clean up orphaned files (files without database records)"""
        cleaned_count = 0
        freed_space = 0

        try:
            for user_dir in self.upload_dir.iterdir():
                if not user_dir.is_dir() or not user_dir.name.isdigit():
                    continue

                user_id = int(user_dir.name)

                # Get all physical files
                for file_path in user_dir.rglob('*'):
                    if file_path.is_file() and not file_path.name.startswith('.'):
                        relative_path = str(file_path.relative_to(user_dir))

                        # Check if file exists in database
                        file_record = self.db.query(File).filter(
                            and_(File.owner_id == user_id, File.path == relative_path)
                        ).first()

                        if not file_record:
                            # Orphaned file - remove it
                            file_size = file_path.stat().st_size
                            file_path.unlink()
                            cleaned_count += 1
                            freed_space += file_size

        except Exception as e:
            print(f"Cleanup error: {e}")

        return {
            "cleaned_files": cleaned_count,
            "freed_space": freed_space
        }