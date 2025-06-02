# app/services/file_service_enhanced.py
"""
Enhanced File Service with Advanced Features
"""

import os
import shutil
import hashlib
import zipfile
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, BinaryIO
from datetime import datetime, timedelta
from PIL import Image, ImageOps
import magic
import mimetypes
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from fastapi import UploadFile, HTTPException, status, BackgroundTasks

from app.models.user import User, File, FileShare, FileComment
from app.core.config import get_settings
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService
from app.utils.validators import validate_file_type, validate_file_size, validate_path, sanitize_filename
from app.utils.helpers import format_file_size

settings = get_settings()

class EnhancedFileService:
    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)
        self.notification_service = NotificationService()
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.upload_dir.mkdir(exist_ok=True)
        
        # Virus scanning enabled flag
        self.virus_scanning_enabled = getattr(settings, 'VIRUS_SCANNING_ENABLED', False)
        
        # Thumbnail settings
        self.thumbnail_sizes = [(150, 150), (300, 300), (600, 600)]
        
        # File type configurations
        self.file_type_configs = {
            'image': {
                'max_size': 50 * 1024 * 1024,  # 50MB
                'extensions': ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg', 'tiff'],
                'generate_thumbnails': True,
                'extract_metadata': True
            },
            'video': {
                'max_size': 500 * 1024 * 1024,  # 500MB
                'extensions': ['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm'],
                'generate_thumbnails': True,
                'extract_metadata': True
            },
            'audio': {
                'max_size': 100 * 1024 * 1024,  # 100MB
                'extensions': ['mp3', 'wav', 'ogg', 'flac', 'm4a', 'aac'],
                'generate_thumbnails': False,
                'extract_metadata': True
            },
            'document': {
                'max_size': 100 * 1024 * 1024,  # 100MB
                'extensions': ['pdf', 'doc', 'docx', 'txt', 'rtf', 'odt', 'pages'],
                'generate_thumbnails': True,
                'extract_metadata': True
            },
            'archive': {
                'max_size': 1024 * 1024 * 1024,  # 1GB
                'extensions': ['zip', 'rar', '7z', 'tar', 'gz', 'bz2'],
                'generate_thumbnails': False,
                'extract_metadata': True
            },
            'code': {
                'max_size': 10 * 1024 * 1024,  # 10MB
                'extensions': ['py', 'js', 'html', 'css', 'json', 'xml', 'sql', 'php', 'java', 'cpp', 'c'],
                'generate_thumbnails': False,
                'extract_metadata': False
            }
        }

    def _get_user_dir(self, user_id: int) -> Path:
        """Get user's upload directory"""
        user_dir = self.upload_dir / str(user_id)
        user_dir.mkdir(exist_ok=True)
        return user_dir

    def _get_file_type_and_config(self, filename: str, mime_type: str = None) -> Tuple[str, Dict]:
        """Determine file type and get configuration"""
        ext = Path(filename).suffix.lower().lstrip('.')
        
        for file_type, config in self.file_type_configs.items():
            if ext in config['extensions']:
                return file_type, config
        
        return 'other', {'max_size': 50 * 1024 * 1024, 'extensions': [], 'generate_thumbnails': False, 'extract_metadata': False}

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def _detect_mime_type(self, file_path: Path) -> str:
        """Detect MIME type using python-magic"""
        try:
            return magic.from_file(str(file_path), mime=True)
        except:
            mime_type, _ = mimetypes.guess_type(str(file_path))
            return mime_type or 'application/octet-stream'

    def _extract_image_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from image files"""
        try:
            with Image.open(file_path) as img:
                metadata = {
                    'width': img.width,
                    'height': img.height,
                    'format': img.format,
                    'mode': img.mode
                }
                
                # Extract EXIF data if available
                if hasattr(img, '_getexif') and img._getexif():
                    exif = img._getexif()
                    if exif:
                        metadata['exif'] = {k: str(v) for k, v in exif.items() if isinstance(v, (str, int, float))}
                
                return metadata
        except Exception as e:
            return {'error': str(e)}

    def _generate_thumbnails(self, file_path: Path, file_type: str) -> List[Path]:
        """Generate thumbnails for supported file types"""
        thumbnails = []
        
        if file_type == 'image':
            try:
                with Image.open(file_path) as img:
                    # Convert to RGB if necessary
                    if img.mode in ('RGBA', 'LA', 'P'):
                        img = img.convert('RGB')
                    
                    thumb_dir = file_path.parent / 'thumbnails'
                    thumb_dir.mkdir(exist_ok=True)
                    
                    for width, height in self.thumbnail_sizes:
                        thumb_path = thumb_dir / f"{file_path.stem}_{width}x{height}.jpg"
                        
                        # Create thumbnail maintaining aspect ratio
                        thumb_img = img.copy()
                        thumb_img.thumbnail((width, height), Image.Resampling.LANCZOS)
                        
                        # Create a white background and paste the thumbnail
                        final_img = Image.new('RGB', (width, height), 'white')
                        paste_x = (width - thumb_img.width) // 2
                        paste_y = (height - thumb_img.height) // 2
                        final_img.paste(thumb_img, (paste_x, paste_y))
                        
                        final_img.save(thumb_path, 'JPEG', quality=85)
                        thumbnails.append(thumb_path)
            except Exception as e:
                print(f"Thumbnail generation failed: {e}")
        
        return thumbnails

    def _scan_for_viruses(self, file_path: Path) -> bool:
        """Scan file for viruses (placeholder implementation)"""
        if not self.virus_scanning_enabled:
            return True
        
        # In a real implementation, integrate with ClamAV or similar
        # For now, just check file size and some basic patterns
        
        # Check file size (extremely large files might be suspicious)
        if file_path.stat().st_size > 10 * 1024 * 1024 * 1024:  # 10GB
            return False
        
        # Check for suspicious patterns in filename
        suspicious_patterns = ['.exe.', '.scr.', '.bat.', '.cmd.']
        filename_lower = file_path.name.lower()
        
        for pattern in suspicious_patterns:
            if pattern in filename_lower:
                return False
        
        return True

    def _check_duplicate_file(self, user_id: int, file_hash: str, filename: str) -> Optional[File]:
        """Check if file already exists (by hash)"""
        return self.db.query(File).filter(
            and_(
                File.owner_id == user_id,
                File.checksum == file_hash,
                File.is_deleted == False
            )
        ).first()

    def _update_user_storage(self, user_id: int, size_delta: int):
        """Update user's storage usage"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if user:
            user.storage_used = max(0, user.storage_used + size_delta)
            self.db.commit()

    async def upload_files_enhanced(
        self, 
        user_id: int, 
        files: List[UploadFile], 
        path: str = "",
        overwrite: bool = False,
        extract_archives: bool = False,
        background_tasks: BackgroundTasks = None
    ) -> Dict[str, Any]:
        """Enhanced file upload with advanced features"""
        
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

        # Check user storage quota
        user = self.db.query(User).filter(User.id == user_id).first()
        total_size = sum(file.size for file in files if file.size)
        
        if user.storage_used + total_size > user.storage_quota:
            raise HTTPException(
                status_code=413,
                detail=f"Storage quota exceeded. Available: {format_file_size(user.storage_quota - user.storage_used)}"
            )

        uploaded_files = []
        skipped_files = []
        failed_files = []

        for file in files:
            try:
                result = await self._process_single_file(
                    file, user_id, target_dir, user_dir, overwrite, extract_archives
                )
                
                if result['status'] == 'uploaded':
                    uploaded_files.append(result['file_info'])
                elif result['status'] == 'skipped':
                    skipped_files.append(result['file_info'])
                    
            except Exception as e:
                failed_files.append({
                    'filename': file.filename,
                    'error': str(e)
                })

        # Update storage usage
        total_uploaded_size = sum(f['size'] for f in uploaded_files)
        self._update_user_storage(user_id, total_uploaded_size)

        # Commit all file records
        self.db.commit()

        # Schedule background tasks
        if background_tasks and uploaded_files:
            for file_info in uploaded_files:
                if file_info.get('generate_thumbnails'):
                    background_tasks.add_task(
                        self._generate_thumbnails_task, 
                        file_info['physical_path'], 
                        file_info['file_type']
                    )

        # Log upload activity
        await self.audit_service.log_action(
            "files_uploaded", "file", f"{len(uploaded_files)} files",
            user_id, details={
                "uploaded_count": len(uploaded_files),
                "skipped_count": len(skipped_files),
                "failed_count": len(failed_files),
                "total_size": total_uploaded_size,
                "path": path
            }
        )

        return {
            "uploaded_files": uploaded_files,
            "skipped_files": skipped_files,
            "failed_files": failed_files,
            "summary": {
                "uploaded": len(uploaded_files),
                "skipped": len(skipped_files),
                "failed": len(failed_files),
                "total_size": total_uploaded_size
            }
        }

    async def _process_single_file(
        self,
        file: UploadFile,
        user_id: int,
        target_dir: Path,
        user_dir: Path,
        overwrite: bool,
        extract_archives: bool
    ) -> Dict[str, Any]:
        """Process a single uploaded file"""
        
        if not file.filename:
            raise ValueError("Filename is required")

        # Sanitize filename
        safe_filename = sanitize_filename(file.filename)
        file_path = target_dir / safe_filename

        # Handle duplicate filenames
        if file_path.exists() and not overwrite:
            counter = 1
            name_parts = safe_filename.rsplit('.', 1)
            while file_path.exists():
                if len(name_parts) == 2:
                    new_name = f"{name_parts[0]}_{counter}.{name_parts[1]}"
                else:
                    new_name = f"{safe_filename}_{counter}"
                file_path = target_dir / new_name
                counter += 1

        # Determine file type and get config
        file_type, type_config = self._get_file_type_and_config(safe_filename)

        # Validate file size against type-specific limits
        if file.size > type_config['max_size']:
            raise ValueError(f"File size exceeds limit for {file_type} files")

        # Save file to temporary location first
        temp_path = file_path.with_suffix('.tmp')
        
        try:
            # Write file
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # Detect MIME type
            mime_type = self._detect_mime_type(temp_path)

            # Calculate file hash
            file_hash = self._calculate_file_hash(temp_path)

            # Check for duplicates
            existing_file = self._check_duplicate_file(user_id, file_hash, safe_filename)
            if existing_file and not overwrite:
                temp_path.unlink()
                return {
                    'status': 'skipped',
                    'file_info': {
                        'filename': safe_filename,
                        'reason': 'duplicate',
                        'existing_file_id': existing_file.id
                    }
                }

            # Virus scan
            if not self._scan_for_viruses(temp_path):
                temp_path.unlink()
                raise ValueError("File failed virus scan")

            # Move to final location
            shutil.move(str(temp_path), str(file_path))

            # Extract metadata
            metadata = {}
            if type_config['extract_metadata']:
                if file_type == 'image':
                    metadata = self._extract_image_metadata(file_path)

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
                checksum=file_hash,
                file_metadata=metadata,
                width=metadata.get('width'),
                height=metadata.get('height'),
                owner_id=user_id
            )

            self.db.add(file_record)
            self.db.flush()  # Get the ID

            # Handle archive extraction
            if extract_archives and file_type == 'archive':
                await self._extract_archive(file_path, user_id, target_dir, user_dir)

            return {
                'status': 'uploaded',
                'file_info': {
                    'id': file_record.id,
                    'name': file_path.name,
                    'original_name': file.filename,
                    'size': file_record.size,
                    'type': file_type,
                    'mime_type': mime_type,
                    'path': relative_path,
                    'checksum': file_hash,
                    'metadata': metadata,
                    'physical_path': str(file_path),
                    'generate_thumbnails': type_config['generate_thumbnails']
                }
            }

        except Exception as e:
            # Clean up on error
            if temp_path.exists():
                temp_path.unlink()
            if file_path.exists():
                file_path.unlink()
            raise e

    async def _extract_archive(
        self, 
        archive_path: Path, 
        user_id: int, 
        target_dir: Path, 
        user_dir: Path
    ):
        """Extract archive files"""
        try:
            extract_dir = target_dir / f"{archive_path.stem}_extracted"
            extract_dir.mkdir(exist_ok=True)

            if archive_path.suffix.lower() == '.zip':
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    # Security: Check for path traversal in zip entries
                    for member in zip_ref.namelist():
                        if '..' in member or member.startswith('/'):
                            continue
                        zip_ref.extract(member, extract_dir)

            # TODO: Add support for other archive formats (tar, 7z, etc.)

        except Exception as e:
            print(f"Archive extraction failed: {e}")

    async def create_file_version(
        self, 
        file_id: int, 
        new_file: UploadFile, 
        user_id: int,
        version_note: str = ""
    ) -> Dict[str, Any]:
        """Create a new version of an existing file"""
        
        # Get original file
        original_file = self.db.query(File).filter(
            and_(File.id == file_id, File.owner_id == user_id)
        ).first()
        
        if not original_file:
            raise HTTPException(status_code=404, detail="File not found")

        # Upload new version
        user_dir = self._get_user_dir(user_id)
        target_dir = Path(original_file.physical_path).parent
        
        result = await self._process_single_file(
            new_file, user_id, target_dir, user_dir, True, False
        )

        if result['status'] != 'uploaded':
            raise HTTPException(status_code=400, detail="Failed to upload new version")

        # Update file record
        file_info = result['file_info']
        new_version = original_file.version + 1

        # Create new file record as version
        version_file = File(
            name=file_info['name'],
            original_name=file_info['original_name'],
            path=file_info['path'],
            physical_path=file_info['physical_path'],
            size=file_info['size'],
            mime_type=file_info['mime_type'],
            file_type=file_info['type'],
            checksum=file_info['checksum'],
            file_metadata=file_info['metadata'],
            version=new_version,
            parent_file_id=original_file.id,
            owner_id=user_id
        )

        self.db.add(version_file)

        # Update original file's version
        original_file.version = new_version

        self.db.commit()

        # Log versioning activity
        await self.audit_service.log_action(
            "file_version_created", "file", str(file_id),
            user_id, details={
                "version": new_version,
                "note": version_note
            }
        )

        return {
            "message": "File version created successfully",
            "version": new_version,
            "file_id": version_file.id
        }

    async def restore_file_version(
        self, 
        file_id: int, 
        version: int, 
        user_id: int
    ) -> Dict[str, Any]:
        """Restore a specific version of a file"""
        
        # Get the version to restore
        version_file = self.db.query(File).filter(
            and_(
                File.parent_file_id == file_id,
                File.version == version,
                File.owner_id == user_id
            )
        ).first()

        if not version_file:
            raise HTTPException(status_code=404, detail="File version not found")

        # Get current file
        current_file = self.db.query(File).filter(
            and_(File.id == file_id, File.owner_id == user_id)
        ).first()

        if not current_file:
            raise HTTPException(status_code=404, detail="File not found")

        # Copy version file to current location
        version_path = Path(version_file.physical_path)
        current_path = Path(current_file.physical_path)

        if version_path.exists():
            shutil.copy2(version_path, current_path)

            # Update current file metadata
            current_file.size = version_file.size
            current_file.checksum = version_file.checksum
            current_file.file_metadata = version_file.file_metadata
            current_file.updated_at = datetime.utcnow()

            self.db.commit()

            # Log restore activity
            await self.audit_service.log_action(
                "file_version_restored", "file", str(file_id),
                user_id, details={"restored_version": version}
            )

            return {"message": f"File restored to version {version}"}
        else:
            raise HTTPException(status_code=404, detail="Version file not found on disk")

    async def get_file_versions(self, file_id: int, user_id: int) -> List[Dict[str, Any]]:
        """Get all versions of a file"""
        
        # Verify file ownership
        file = self.db.query(File).filter(
            and_(File.id == file_id, File.owner_id == user_id)
        ).first()

        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        # Get all versions
        versions = self.db.query(File).filter(
            or_(
                File.id == file_id,
                File.parent_file_id == file_id
            )
        ).order_by(File.version.desc()).all()

        return [
            {
                "id": version.id,
                "version": version.version,
                "size": version.size,
                "checksum": version.checksum,
                "created_at": version.created_at,
                "is_current": version.id == file_id
            }
            for version in versions
        ]

    async def duplicate_file(
        self, 
        file_id: int, 
        user_id: int, 
        new_name: str = None
    ) -> Dict[str, Any]:
        """Duplicate a file"""
        
        # Get original file
        original_file = self.db.query(File).filter(
            and_(File.id == file_id, File.owner_id == user_id)
        ).first()

        if not original_file:
            raise HTTPException(status_code=404, detail="File not found")

        # Generate new filename
        if not new_name:
            name_parts = original_file.name.rsplit('.', 1)
            if len(name_parts) == 2:
                new_name = f"{name_parts[0]}_copy.{name_parts[1]}"
            else:
                new_name = f"{original_file.name}_copy"

        # Copy physical file
        original_path = Path(original_file.physical_path)
        new_path = original_path.parent / new_name

        # Handle name conflicts
        counter = 1
        while new_path.exists():
            name_parts = new_name.rsplit('.', 1)
            if len(name_parts) == 2:
                new_name = f"{name_parts[0]}_{counter}.{name_parts[1]}"
            else:
                new_name = f"{new_name}_{counter}"
            new_path = original_path.parent / new_name
            counter += 1

        shutil.copy2(original_path, new_path)

        # Create new file record
        user_dir = self._get_user_dir(user_id)
        relative_path = str(new_path.relative_to(user_dir))

        duplicate_file = File(
            name=new_name,
            original_name=new_name,
            path=relative_path,
            physical_path=str(new_path),
            size=original_file.size,
            mime_type=original_file.mime_type,
            file_type=original_file.file_type,
            checksum=original_file.checksum,
            file_metadata=original_file.file_metadata,
            width=original_file.width,
            height=original_file.height,
            owner_id=user_id
        )

        self.db.add(duplicate_file)
        self.db.commit()

        # Update storage usage
        self._update_user_storage(user_id, original_file.size)

        # Log duplication
        await self.audit_service.log_action(
            "file_duplicated", "file", str(file_id),
            user_id, details={"duplicate_id": duplicate_file.id}
        )

        return {
            "message": "File duplicated successfully",
            "duplicate_id": duplicate_file.id,
            "duplicate_name": new_name
        }

    async def create_file_archive(
        self, 
        file_ids: List[int], 
        user_id: int, 
        archive_name: str = None,
        archive_format: str = "zip"
    ) -> Dict[str, Any]:
        """Create an archive from multiple files"""
        
        # Get files
        files = self.db.query(File).filter(
            and_(
                File.id.in_(file_ids),
                File.owner_id == user_id,
                File.is_deleted == False
            )
        ).all()

        if not files:
            raise HTTPException(status_code=404, detail="No files found")

        # Generate archive name
        if not archive_name:
            archive_name = f"archive_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{archive_format}"

        user_dir = self._get_user_dir(user_id)
        archive_path = user_dir / archive_name

        # Create archive
        if archive_format == "zip":
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in files:
                    file_path = Path(file.physical_path)
                    if file_path.exists():
                        zipf.write(file_path, file.name)

        # Create file record for archive
        relative_path = str(archive_path.relative_to(user_dir))
        archive_size = archive_path.stat().st_size

        archive_file = File(
            name=archive_name,
            original_name=archive_name,
            path=relative_path,
            physical_path=str(archive_path),
            size=archive_size,
            mime_type='application/zip',
            file_type='archive',
            checksum=self._calculate_file_hash(archive_path),
            owner_id=user_id
        )

        self.db.add(archive_file)
        self.db.commit()

        # Update storage usage
        self._update_user_storage(user_id, archive_size)

        # Log archive creation
        await self.audit_service.log_action(
            "archive_created", "file", str(archive_file.id),
            user_id, details={
                "file_count": len(files),
                "archive_size": archive_size
            }
        )

        return {
            "message": "Archive created successfully",
            "archive_id": archive_file.id,
            "archive_name": archive_name,
            "file_count": len(files),
            "archive_size": archive_size
        }

    async def _generate_thumbnails_task(self, file_path: str, file_type: str):
        """Background task to generate thumbnails"""
        try:
            self._generate_thumbnails(Path(file_path), file_type)
        except Exception as e:
            print(f"Background thumbnail generation failed: {e}")

# Additional file operation methods would go here...