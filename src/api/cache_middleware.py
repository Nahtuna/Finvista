# -*- coding: utf-8 -*-
"""
Cache Middleware for FastAPI
============================
Provides intelligent caching middleware for API endpoints with:
- Request/response caching with TTL
- Cache key generation based on request parameters
- Conditional caching based on HTTP methods
- Cache invalidation support
"""

import json
import hashlib
from typing import Optional, Callable, Any
from functools import wraps

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from src.infra.redis_cache import cache, generate_cache_key, DEFAULT_TTL


def cache_response(
    prefix: str = "",
    ttl: int = DEFAULT_TTL,
    include_query_params: bool = True,
    cache_headers: bool = True,
):
    """
    Decorator to cache GET request responses.
    
    Args:
        prefix: Cache key prefix (e.g., "cw:", "market:")
        ttl: Time-to-live in seconds
        include_query_params: Include query parameters in cache key
        cache_headers: Include response headers in cache
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request if available
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            # Only cache GET requests
            if request and request.method != "GET":
                return await func(*args, **kwargs)
            
            # Generate cache key
            cache_key = _generate_cache_key(
                prefix, 
                request, 
                include_query_params,
                *args, 
                **kwargs
            )
            
            # Try to get from cache
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                return JSONResponse(
                    content=cached_data.get("content"),
                    headers=cached_data.get("headers", {}),
                    status_code=cached_data.get("status_code", 200)
                )
            
            # Execute the original function
            response = await func(*args, **kwargs)
            
            # Extract response data
            if isinstance(response, JSONResponse):
                content = json.loads(response.body.decode())
                status_code = response.status_code
                headers = dict(response.headers)
            elif isinstance(response, dict):
                content = response
                status_code = 200
                headers = {}
            else:
                # Don't cache non-JSON responses
                return response
            
            # Store in cache
            cache_data = {
                "content": content,
                "status_code": status_code,
                "headers": headers if cache_headers else {}
            }
            cache.set(cache_key, cache_data, ttl)
            
            return response
        
        return wrapper
    return decorator


def _generate_cache_key(
    prefix: str,
    request: Optional[Request],
    include_query_params: bool,
    *args,
    **kwargs
) -> str:
    """Generate cache key from request and function parameters."""
    key_parts = [prefix]
    
    # Add function name
    if args and hasattr(args[0], '__name__'):
        key_parts.append(args[0].__name__)
    
    # Add query parameters
    if request and include_query_params:
        query_params = dict(request.query_params)
        if query_params:
            # Sort for consistency
            sorted_params = sorted(query_params.items())
            for k, v in sorted_params:
                key_parts.append(f"{k}:{v}")
    
    # Add path parameters
    if request:
        path_params = request.path_params
        if path_params:
            sorted_params = sorted(path_params.items())
            for k, v in sorted_params:
                key_parts.append(f"{k}:{v}")
    
    # Add kwargs
    if kwargs:
        sorted_kwargs = sorted(kwargs.items())
        for k, v in sorted_kwargs:
            if v is not None:
                key_parts.append(f"{k}:{v}")
    
    key_string = ":".join(key_parts)
    
    # Hash if key is too long
    if len(key_string) > 200:
        key_hash = hashlib.md5(key_string.encode()).hexdigest()[:12]
        return f"{prefix}hash:{key_hash}"
    
    return key_string


class CacheMiddleware:
    """
    Middleware class for automatic response caching.
    Can be applied at the application level or per-route.
    """
    
    def __init__(
        self,
        default_ttl: int = DEFAULT_TTL,
    ):
        self.default_ttl = default_ttl
        self.cacheable_paths = {
            "/api/warrants/opportunities": {"ttl": 60, "prefix": "cw:opportunities"},
            "/api/credit": {"ttl": 300, "prefix": "credit:health"},
            "/api/credit-health": {"ttl": 300, "prefix": "credit:health"},
            "/api/regime/market": {"ttl": 600, "prefix": "regime:market"},
            "/api/health": {"ttl": 30, "prefix": "system:health"},
        }
    
    async def __call__(self, request: Request, call_next):
        """Process request through cache middleware."""
        # Only cache GET requests
        if request.method != "GET":
            return await call_next(request)
        
        path = request.url.path
        
        # Check if path is cacheable
        cache_config = self._get_cache_config(path)
        if not cache_config:
            return await call_next(request)
        
        # Generate cache key
        cache_key = generate_cache_key(
            cache_config["prefix"],
            path,
            **dict(request.query_params)
        )
        
        # Try to get from cache
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            # Preserve CORS headers from cached response
            headers = dict(cached_data.get("headers", {}))
            headers.update({
                "X-Cache": "HIT",
                "X-Cache-Key": cache_key,
            })
            return JSONResponse(
                content=cached_data.get("content"),
                headers=headers,
                status_code=cached_data.get("status_code", 200)
            )
        
        # Execute request
        response = await call_next(request)
        
        # Only cache successful JSON responses
        if response.status_code == 200 and "application/json" in response.headers.get("content-type", ""):
            # Read response body
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            
            try:
                content = json.loads(body.decode())
                
                # Store important headers (including CORS)
                important_headers = {}
                for key, value in response.headers.items():
                    # Preserve CORS and other important headers
                    if key.lower() in ['access-control-allow-origin', 'access-control-allow-methods', 
                                      'access-control-allow-headers', 'access-control-allow-credentials',
                                      'access-control-expose-headers', 'content-type']:
                        important_headers[key] = value
                
                cache_data = {
                    "content": content,
                    "status_code": response.status_code,
                    "headers": important_headers,
                }
                cache.set(cache_key, cache_data, cache_config["ttl"])
                
                # Return response with cache headers but preserve original headers
                headers = dict(response.headers)
                headers.update({
                    "X-Cache": "MISS",
                    "X-Cache-Key": cache_key,
                })
                return Response(
                    content=body,
                    status_code=response.status_code,
                    headers=headers
                )
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Don't cache if JSON parsing fails
                return Response(
                    content=body,
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
        
        return response
    
    def _get_cache_config(self, path: str) -> Optional[dict]:
        """Get cache configuration for a given path."""
        for cacheable_path, config in self.cacheable_paths.items():
            if path.startswith(cacheable_path):
                return config
        return None
    
    def add_cacheable_path(self, path: str, ttl: int, prefix: str):
        """Add a new cacheable path configuration."""
        self.cacheable_paths[path] = {"ttl": ttl, "prefix": prefix}
    
    def remove_cacheable_path(self, path: str):
        """Remove a cacheable path configuration."""
        if path in self.cacheable_paths:
            del self.cacheable_paths[path]
    
    def invalidate_path(self, path: str):
        """Invalidate cache for a specific path."""
        cache_config = self._get_cache_config(path)
        if cache_config:
            pattern = f"{cache_config['prefix']}*"
            return cache.delete_pattern(pattern)
        return 0


# Global middleware instance
cache_middleware = CacheMiddleware()
