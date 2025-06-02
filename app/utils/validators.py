"""
Input validation utilities
"""

import re
from typing import List, Optional
from fastapi import HTTPException


def validate_username(username: str) -> bool:
    """Validate username format"""
    if not username or len(username) < 3 or len(username) > 30:
        return False

    # Allow alphanumeric and underscore
    pattern = r'^[a-zA-Z0-9_]+$'
    return bool(re.match(pattern, username))


def validate_password(password: str) -> bool:
    """Validate password strength"""
    if not password or len(password) < 6:
        return False

    # Check for at least one letter and one number
    has_letter = any(c.isalpha() for c in password)
    has_number = any(c.isdigit() for c in password)

    return has_letter and has_number


def validate_file_type(filename: str, allowed_types: List[str]) -> bool:
    """Validate file type by extension"""
    if not filename:
        return False

    extension = filename.lower().split('.')[-1]
    return extension in [t.lower() for t in allowed_types]


def validate_file_size(file_size: int, max_size: int) -> bool:
    """Validate file size"""
    return 0 < file_size <= max_size


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    # Remove dangerous characters
    unsafe_chars = r'[<>:"/\|?*]'
    safe_filename = re.sub(unsafe_chars, '_', filename)

    # Limit length
    if len(safe_filename) > 255:
        name, ext = safe_filename.rsplit('.', 1) if '.' in safe_filename else (safe_filename, '')
        safe_filename = name[:255-len(ext)-1] + '.' + ext if ext else name[:255]

    return safe_filename


def validate_path(path: str) -> bool:
    """Validate file path for security"""
    if not path:
        return True

    # Check for path traversal attempts
    dangerous_patterns = ['../', '..\\', '/..', '\\..']
    return not any(pattern in path for pattern in dangerous_patterns)
