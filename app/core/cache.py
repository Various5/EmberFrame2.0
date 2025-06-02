"""
Redis cache configuration
"""

import redis
from typing import Optional, Any
import json

from app.core.config import get_settings

settings = get_settings()


class CacheService:
    def __init__(self):
        self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            value = self.redis_client.get(key)
            return json.loads(value) if value else None
        except Exception:
            return None

    async def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """Set value in cache"""
        try:
            return self.redis_client.setex(key, expire, json.dumps(value))
        except Exception:
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            return bool(self.redis_client.delete(key))
        except Exception:
            return False


# Global cache instance
cache = CacheService()
