"""Redis caching implementation for API performance optimization.

This module provides Redis connection management, caching decorators, and utilities
for efficient caching of API responses.
"""
from functools import wraps
import json
from typing import Any, Callable, Optional, Union
import redis
from redis.connection import ConnectionPool
from redis.exceptions import RedisError

from .config import settings

# Redis connection pool for connection reuse
REDIS_POOL = ConnectionPool.from_url(
    url=str(settings.REDIS_URL),
    max_connections=50,  # Adjust based on your needs
    decode_responses=True
)

class RedisCache:
    """Redis cache manager with connection pooling.
    
    This class provides methods for interacting with Redis cache using a connection pool
    for better performance and resource management.
    """
    
    def __init__(self) -> None:
        """Initialize Redis cache manager with connection pool."""
        self._redis = redis.Redis(connection_pool=REDIS_POOL)
    
    def get(self, key: str) -> Optional[str]:
        """Retrieve a value from cache.
        
        Args:
            key: Cache key to retrieve
            
        Returns:
            Optional[str]: Cached value if exists, None otherwise
        """
        try:
            return self._redis.get(key)
        except RedisError:
            return None
    
    def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Store a value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds, defaults to REDIS_TTL from settings
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            return bool(self._redis.set(
                key,
                value,
                ex=ttl or settings.REDIS_TTL
            ))
        except RedisError:
            return False
    
    def delete(self, key: str) -> bool:
        """Remove a value from cache.
        
        Args:
            key: Cache key to remove
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            return bool(self._redis.delete(key))
        except RedisError:
            return False
    
    def clear_pattern(self, pattern: str) -> bool:
        """Clear all keys matching a pattern.
        
        Args:
            pattern: Redis key pattern to match (e.g., "user:*")
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            keys = self._redis.keys(pattern)
            if keys:
                return bool(self._redis.delete(*keys))
            return True
        except RedisError:
            return False

# Global cache instance
cache = RedisCache()

def get_redis() -> redis.Redis:
    """Get Redis connection from pool.
    
    Returns:
        redis.Redis: Redis client instance
    """
    return redis.Redis(connection_pool=REDIS_POOL)

def generate_cache_key(prefix: str, *args: Any, **kwargs: Any) -> str:
    """Generate a cache key from function arguments.
    
    Args:
        prefix: Prefix for the cache key
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        str: Generated cache key
    """
    key_parts = [prefix]
    
    if args:
        key_parts.append(":".join(str(arg) for arg in args))
    
    if kwargs:
        sorted_kwargs = sorted(kwargs.items())
        key_parts.append(":".join(f"{k}={v}" for k, v in sorted_kwargs))
    
    return ":".join(key_parts)

def cached(prefix: str, ttl: Optional[int] = None) -> Callable:
    """Cache decorator for API endpoints.
    
    Args:
        prefix: Prefix for cache keys
        ttl: Optional TTL override for cached values
        
    Returns:
        Callable: Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Generate cache key
            cache_key = generate_cache_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                try:
                    return json.loads(cached_value)
                except json.JSONDecodeError:
                    return cached_value
            
            # Execute function if cache miss
            result = await func(*args, **kwargs)
            
            # Cache the result
            try:
                cache_value = json.dumps(result)
                cache.set(cache_key, cache_value, ttl)
            except (TypeError, json.JSONDecodeError):
                # If result can't be JSON serialized, store as string
                cache.set(cache_key, str(result), ttl)
            
            return result
        return wrapper
    return decorator

def invalidate_cache(prefix: str, *args: Any, **kwargs: Any) -> bool:
    """Invalidate cache for specific key or pattern.
    
    Args:
        prefix: Cache key prefix
        *args: Positional arguments for key generation
        **kwargs: Keyword arguments for key generation
        
    Returns:
        bool: True if successful, False otherwise
    """
    if args or kwargs:
        # Invalidate specific key
        cache_key = generate_cache_key(prefix, *args, **kwargs)
        return cache.delete(cache_key)
    else:
        # Invalidate all keys with prefix
        return cache.clear_pattern(f"{prefix}:*")
