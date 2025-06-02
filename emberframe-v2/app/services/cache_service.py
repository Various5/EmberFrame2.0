"""
Caching service
"""

from typing import Any, Optional
from app.core.cache import cache


class CacheService:
    @staticmethod
    async def get_user_cache(user_id: int, key: str) -> Optional[Any]:
        """Get user-specific cached data"""
        cache_key = f"user:{user_id}:{key}"
        return await cache.get(cache_key)

    @staticmethod
    async def set_user_cache(user_id: int, key: str, value: Any, expire: int = 3600) -> bool:
        """Set user-specific cached data"""
        cache_key = f"user:{user_id}:{key}"
        return await cache.set(cache_key, value, expire)

    @staticmethod
    async def delete_user_cache(user_id: int, key: str) -> bool:
        """Delete user-specific cached data"""
        cache_key = f"user:{user_id}:{key}"
        return await cache.delete(cache_key)

    @staticmethod
    async def get_system_cache(key: str) -> Optional[Any]:
        """Get system-wide cached data"""
        cache_key = f"system:{key}"
        return await cache.get(cache_key)

    @staticmethod
    async def set_system_cache(key: str, value: Any, expire: int = 3600) -> bool:
        """Set system-wide cached data"""
        cache_key = f"system:{key}"
        return await cache.set(cache_key, value, expire)
