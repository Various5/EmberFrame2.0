"""
General helper functions
"""

import hashlib
import secrets
import string
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta


def generate_random_string(length: int = 32) -> str:
    """Generate random string for tokens, etc."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def hash_string(text: str) -> str:
    """Generate SHA-256 hash of string"""
    return hashlib.sha256(text.encode()).hexdigest()


def format_file_size(size: int) -> str:
    """Format file size in human readable format"""
    if size == 0:
        return "0 B"

    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    return f"{size:.1f} {units[unit_index]}"


def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime to string"""
    return dt.strftime(format_str)


def parse_datetime(dt_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """Parse datetime from string"""
    return datetime.strptime(dt_str, format_str)


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """Split list into chunks"""
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]


def merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
    """Merge two dictionaries"""
    result = dict1.copy()
    result.update(dict2)
    return result


def get_client_ip(request) -> str:
    """Get client IP address from request"""
    x_forwarded_for = request.headers.get('X-Forwarded-For')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.client.host


def is_safe_url(url: str, allowed_hosts: List[str]) -> bool:
    """Check if URL is safe for redirects"""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    return parsed.netloc in allowed_hosts or not parsed.netloc
