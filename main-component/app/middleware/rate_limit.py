"""Rate limiting middleware using Redis.

This module provides a FastAPI middleware for rate limiting API requests using Redis
as the backend for storing rate limit counters.
"""
from datetime import datetime
from typing import Optional, Tuple

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..cache import RedisCache
from ..config import settings

class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""
    pass

class RateLimiter:
    """Rate limiter using Redis for counter storage."""
    
    def __init__(self, redis_cache: RedisCache):
        """Initialize rate limiter with Redis cache instance.
        
        Args:
            redis_cache: Redis cache instance for storing counters
        """
        self._cache = redis_cache
        self._window = settings.RATE_LIMIT_WINDOW
        self._max_requests = settings.RATE_LIMIT_REQUESTS
    
    def _generate_key(self, identifier: str) -> str:
        """Generate Redis key for rate limit counter.
        
        Args:
            identifier: Unique identifier for the client/endpoint
            
        Returns:
            str: Redis key for the rate limit counter
        """
        timestamp = int(datetime.now().timestamp() / self._window) * self._window
        return f"ratelimit:{identifier}:{timestamp}"
    
    def check_rate_limit(self, identifier: str) -> Tuple[bool, int, int, int]:
        """Check if rate limit is exceeded for the given identifier.
        
        Args:
            identifier: Unique identifier for the client/endpoint
            
        Returns:
            Tuple containing:
            - bool: True if rate limit is not exceeded
            - int: Number of remaining requests
            - int: Total requests allowed
            - int: Time until reset in seconds
        """
        key = self._generate_key(identifier)
        current_count = int(self._cache.get(key) or 0)
        
        # Calculate time until window reset
        now = datetime.now().timestamp()
        window_start = int(now / self._window) * self._window
        reset_time = int(window_start + self._window - now)
        
        if current_count >= self._max_requests:
            return False, 0, self._max_requests, reset_time
        
        # Increment counter and set TTL if needed
        new_count = current_count + 1
        if new_count == 1:
            self._cache.set(key, str(new_count), self._window)
        else:
            self._cache.set(key, str(new_count))
        
        remaining = max(0, self._max_requests - new_count)
        return True, remaining, self._max_requests, reset_time

class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting requests."""
    
    def __init__(
        self,
        app: ASGIApp,
        redis_cache: Optional[RedisCache] = None,
        exclude_paths: Optional[list[str]] = None
    ):
        """Initialize rate limit middleware.
        
        Args:
            app: FastAPI application instance
            redis_cache: Optional Redis cache instance (uses global if not provided)
            exclude_paths: Optional list of paths to exclude from rate limiting
        """
        super().__init__(app)
        from ..cache import cache as default_cache
        self.limiter = RateLimiter(redis_cache or default_cache)
        self.exclude_paths = exclude_paths or []
    
    def _should_rate_limit(self, request: Request) -> bool:
        """Check if request should be rate limited.
        
        Args:
            request: FastAPI request object
            
        Returns:
            bool: True if request should be rate limited
        """
        # Skip rate limiting for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return False
        
        # Skip rate limiting for authorized clients with bypass token
        bypass_token = request.headers.get("X-RateLimit-Bypass")
        if bypass_token and bypass_token == settings.RATE_LIMIT_BYPASS_TOKEN:
            return False
        
        return True
    
    def _get_client_identifier(self, request: Request) -> str:
        """Get unique identifier for the client.
        
        Args:
            request: FastAPI request object
            
        Returns:
            str: Unique identifier for rate limiting
        """
        # Use X-Forwarded-For header if behind proxy, fallback to client host
        client_ip = request.headers.get(
            "X-Forwarded-For",
            request.client.host if request.client else "unknown"
        )
        return f"{client_ip}:{request.url.path}"
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process the request through rate limiting.
        
        Args:
            request: FastAPI request object
            call_next: ASGI application callable
            
        Returns:
            Response: API response
        """
        if not self._should_rate_limit(request):
            return await call_next(request)
        
        identifier = self._get_client_identifier(request)
        allowed, remaining, limit, reset = self.limiter.check_rate_limit(identifier)
        
        # Add rate limit headers to response
        response_headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset)
        }
        
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "limit": limit,
                    "reset_in": reset
                },
                headers=response_headers
            )
        
        response = await call_next(request)
        
        # Add headers to successful response
        for key, value in response_headers.items():
            response.headers[key] = value
        
        return response

def add_rate_limit_middleware(
    app: FastAPI,
    redis_cache: Optional[RedisCache] = None,
    exclude_paths: Optional[list[str]] = None
) -> None:
    """Add rate limiting middleware to FastAPI application.
    
    Args:
        app: FastAPI application instance
        redis_cache: Optional Redis cache instance
        exclude_paths: Optional list of paths to exclude from rate limiting
    """
    app.add_middleware(
        RateLimitMiddleware,
        redis_cache=redis_cache,
        exclude_paths=exclude_paths
    )