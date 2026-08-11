# -*- coding: utf-8 -*-
"""
Cache Middleware for FastAPI - intelligent caching with TTL support.
"""

import json
import hashlib
from typing import Optional, Callable, Any
from functools import wraps

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from backend.infra.redis_cache import cache, generate_cache_key, DEFAULT_TTL


def cache_response(
    prefix: str = "",
    ttl: int = DEFAULT_TTL,
    include_query_params: bool = True,
    cache_headers: bool = True,
):
    """Decorator to cache GET request responses."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = _extract_request(args)
            
            if request and request.method != "GET":
                return await func(*args, **kwargs)
            
            cache_key = _generate_cache_key(prefix, request, include_query_params, *args, **kwargs)
            cached_data = cache.get(cache_key)
            
            if cached_data is not None:
                return JSONResponse(
                    content=cached_data.get("content"),
                    headers=cached_data.get("headers", {}),
                    status_code=cached_data.get("status_code", 200)
                )
            
            response = await func(*args, **kwargs)
            cache_data = _extract_cache_data(response, cache_headers)
            
            if cache_data:
                cache.set(cache_key, cache_data, ttl)
            
            return response
        return wrapper
    return decorator


def _extract_request(args) -> Optional[Request]:
    """Extract Request object from args."""
    for arg in args:
        if isinstance(arg, Request):
            return arg
    return None


def _generate_cache_key(prefix: str, request: Optional[Request], include_query_params: bool, *args, **kwargs) -> str:
    """Generate cache key from request and function parameters."""
    key_parts = [prefix]
    
    if args and hasattr(args[0], '__name__'):
        key_parts.append(args[0].__name__)
    
    if request and include_query_params:
        for k, v in sorted(dict(request.query_params).items()):
            key_parts.append(f"{k}:{v}")
    
    if request:
        for k, v in sorted(request.path_params.items()):
            key_parts.append(f"{k}:{v}")
    
    for k, v in sorted(kwargs.items()):
        if v is not None:
            key_parts.append(f"{k}:{v}")
    
    key_string = ":".join(key_parts)
    return f"{prefix}hash:{hashlib.md5(key_string.encode()).hexdigest()[:12]}" if len(key_string) > 200 else key_string


def _extract_cache_data(response: Any, cache_headers: bool) -> Optional[dict]:
    """Extract cacheable data from response."""
    if isinstance(response, JSONResponse):
        content = json.loads(response.body.decode())
        return {
            "content": content,
            "status_code": response.status_code,
            "headers": dict(response.headers) if cache_headers else {}
        }
    elif isinstance(response, dict):
        return {"content": response, "status_code": 200, "headers": {}}
    return None


class CacheMiddleware:
    """Middleware class for automatic response caching."""
    
    CACHEABLE_PATHS = {
        "/api/warrants/opportunities": {"ttl": 10, "prefix": "cw:opportunities"},
        "/api/credit": {"ttl": 60, "prefix": "credit:health"},
        "/api/credit-health": {"ttl": 60, "prefix": "credit:health"},
        "/api/regime/market": {"ttl": 120, "prefix": "regime:market"},
    }
    
    CORS_HEADERS = {
        'access-control-allow-origin', 'access-control-allow-methods',
        'access-control-allow-headers', 'access-control-allow-credentials',
        'access-control-expose-headers', 'content-type'
    }
    
    def __init__(self, default_ttl: int = DEFAULT_TTL):
        self.default_ttl = default_ttl
    
    def _get_cache_config(self, path: str) -> Optional[dict]:
        """Get cache configuration for path."""
        return self.CACHEABLE_PATHS.get(path)
    
    async def __call__(self, request: Request, call_next):
        """Process request through cache middleware."""
        if request.method != "GET":
            return await call_next(request)
        
        cache_config = self._get_cache_config(request.url.path)
        if not cache_config:
            return await call_next(request)
        
        cache_key = generate_cache_key(
            cache_config["prefix"],
            request.url.path,
            **dict(request.query_params)
        )
        
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            headers = dict(cached_data.get("headers", {}))
            headers.update({"X-Cache": "HIT", "X-Cache-Key": cache_key})
            return JSONResponse(
                content=cached_data.get("content"),
                headers=headers,
                status_code=cached_data.get("status_code", 200)
            )
        
        response = await call_next(request)
        
        if response.status_code == 200 and "application/json" in response.headers.get("content-type", ""):
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            
            try:
                content = json.loads(body.decode())
                important_headers = {
                    k: v for k, v in response.headers.items() 
                    if k.lower() in self.CORS_HEADERS
                }
                
                cache.set(cache_key, {
                    "content": content,
                    "status_code": response.status_code,
                    "headers": important_headers,
                }, cache_config["ttl"])
                
                headers = dict(response.headers)
                headers.update({"X-Cache": "MISS", "X-Cache-Key": cache_key})
                return Response(content=body, status_code=response.status_code, headers=headers)
            except (json.JSONDecodeError, UnicodeDecodeError):
                return response
        
        return response
