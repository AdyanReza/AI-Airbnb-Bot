import redis
import json
import logging
from typing import Any, Optional
from functools import wraps
import os
from ..config import Config

logger = logging.getLogger(__name__)

class Cache:
    """
    Redis-based caching implementation with fallback to in-memory cache.
    """
    
    def __init__(self):
        self._local_cache = {}
        try:
            self.redis = redis.from_url(Config.REDIS_URL)
            self.redis.ping()
            self.use_redis = True
            logger.info("Successfully connected to Redis")
        except Exception as e:
            self.use_redis = False
            logger.warning(f"Failed to connect to Redis, using local cache: {str(e)}")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            if self.use_redis:
                data = self.redis.get(key)
                return json.loads(data) if data else None
            return self._local_cache.get(key)
        except Exception as e:
            logger.error(f"Error retrieving from cache: {str(e)}")
            return None
    
    def set(self, key: str, value: Any, timeout: int = 3600) -> bool:
        """Set value in cache with timeout in seconds"""
        try:
            if self.use_redis:
                return self.redis.setex(
                    key,
                    timeout,
                    json.dumps(value)
                )
            self._local_cache[key] = value
            return True
        except Exception as e:
            logger.error(f"Error setting cache: {str(e)}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from cache"""
        try:
            if self.use_redis:
                return bool(self.redis.delete(key))
            self._local_cache.pop(key, None)
            return True
        except Exception as e:
            logger.error(f"Error deleting from cache: {str(e)}")
            return False

def cached(timeout: int = 3600):
    """
    Decorator for caching function results.
    
    Args:
        timeout: Cache timeout in seconds
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Get cache instance
            cache = Cache()
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Call function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout)
            return result
        return wrapper
    return decorator
