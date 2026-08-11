# -*- coding: utf-8 -*-
"""
Redis Cache Layer for Finvista
===============================
Provides high-performance caching for API responses, market data, and computed results.
Supports TTL-based expiration, pattern-based invalidation, and connection pooling.
"""

import json
import os
from typing import Optional, Any, List
from datetime import timedelta
import hashlib

# Optional Redis import - graceful degradation if not installed
try:
    import redis
    from redis import Redis
    from redis.asyncio import Redis as AsyncRedis
    from redis.connection import ConnectionPool
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("⚠️ [Redis] Redis package not installed. Cache will operate in degraded mode (no caching).")
    print("   → Install with: pip install redis>=5.0.0")

from backend.core.config import load_dotenv

load_dotenv()

# Redis Configuration
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "false").lower() == "true"
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
REDIS_MAX_CONNECTIONS = int(os.getenv("REDIS_MAX_CONNECTIONS", 10))

# TTL Configuration (in seconds)
DEFAULT_TTL = 300  # 5 minutes
SHORT_TTL = 60     # 1 minute
MEDIUM_TTL = 600   # 10 minutes
LONG_TTL = 3600    # 1 hour
VERY_LONG_TTL = 86400  # 24 hours

# Cache Key Prefixes
PREFIX_WARRANTS = "cw:"
PREFIX_MARKET = "market:"
PREFIX_CREDIT = "credit:"
PREFIX_REGIME = "regime:"
PREFIX_PORTFOLIO = "portfolio:"
PREFIX_STOCK = "stock:"
PREFIX_ATC = "atc:"
PREFIX_ATC = "atc:"


class RedisCache:
    """
    Synchronous Redis cache wrapper for general caching needs.
    Provides connection pooling, automatic serialization, and TTL management.
    Gracefully degrades when Redis is not available.
    """
    
    def __init__(self):
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[Redis] = None
        if REDIS_AVAILABLE and REDIS_ENABLED:
            self._connect()
        else:
            if not REDIS_AVAILABLE:
                print("ℹ️ [Redis] Operating in degraded mode (Redis not installed)")
            elif not REDIS_ENABLED:
                print("ℹ️ [Redis] Operating in degraded mode (Redis disabled via REDIS_ENABLED=false)")
    
    def _connect(self):
        """Initialize Redis connection pool."""
        if not REDIS_AVAILABLE:
            return
        if not REDIS_ENABLED:
            print("ℹ️ [Redis] Connection skipped (Redis disabled via REDIS_ENABLED=false)")
            return
        
        try:
            self._pool = ConnectionPool(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD,
                max_connections=REDIS_MAX_CONNECTIONS,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )
            self._client = Redis(connection_pool=self._pool)
            # Test connection
            self._client.ping()
            print(f"✅ [Redis] Connected to {REDIS_HOST}:{REDIS_PORT} (DB {REDIS_DB})")
        except Exception as e:
            print(f"⚠️ [Redis] Connection failed: {e}")
            print("   → Cache will operate in degraded mode (no caching)")
            self._client = None
    
    def is_available(self) -> bool:
        """Check if Redis is available."""
        if not REDIS_AVAILABLE:
            return False
        if not REDIS_ENABLED:
            return False
        if self._client is None:
            return False
        try:
            self._client.ping()
            return True
        except Exception:
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.is_available():
            return None
        
        try:
            value = self._client.get(key)
            if value is None:
                return None
            return json.loads(value)
        except Exception as e:
            print(f"⚠️ [Redis] Get error for key '{key}': {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = DEFAULT_TTL) -> bool:
        """Set value in cache with TTL."""
        if not self.is_available():
            return False
        
        try:
            serialized = json.dumps(value, default=str)
            self._client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            print(f"⚠️ [Redis] Set error for key '{key}': {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self.is_available():
            return False
        
        try:
            self._client.delete(key)
            return True
        except Exception as e:
            print(f"⚠️ [Redis] Delete error for key '{key}': {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern."""
        if not self.is_available():
            return 0
        
        try:
            keys = self._client.keys(pattern)
            if keys:
                return self._client.delete(*keys)
            return 0
        except Exception as e:
            print(f"⚠️ [Redis] Delete pattern error for '{pattern}': {e}")
            return 0
    
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self.is_available():
            return False
        
        try:
            return bool(self._client.exists(key))
        except Exception:
            return False
    
    def get_ttl(self, key: str) -> int:
        """Get remaining TTL for key."""
        if not self.is_available():
            return -1
        
        try:
            return self._client.ttl(key)
        except Exception:
            return -1
    
    def flush_db(self) -> bool:
        """Flush current database (use with caution)."""
        if not self.is_available():
            return False
        
        try:
            self._client.flushdb()
            print("⚠️ [Redis] Database flushed")
            return True
        except Exception as e:
            print(f"⚠️ [Redis] Flush error: {e}")
            return False
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        if not REDIS_AVAILABLE:
            return {"available": False, "error": "Redis package not installed"}
        if not REDIS_ENABLED:
            return {"available": False, "error": "Redis disabled via REDIS_ENABLED=false"}
        if not self.is_available():
            return {"available": False, "error": "Redis connection failed"}
        
        try:
            info = self._client.info()
            return {
                "available": True,
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "N/A"),
                "total_keys": info.get("db0", {}).get("keys", 0),
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
            }
        except Exception as e:
            print(f"⚠️ [Redis] Stats error: {e}")
            return {"available": False, "error": str(e)}
    
    def close(self):
        """Close connection pool."""
        if self._pool:
            self._pool.disconnect()
            print("🔌 [Redis] Connection closed")


class AsyncRedisCache:
    """
    Asynchronous Redis cache wrapper for FastAPI async endpoints.
    Provides non-blocking cache operations for high-concurrency scenarios.
    Gracefully degrades when Redis is not available.
    """
    
    def __init__(self):
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[AsyncRedis] = None
        if not REDIS_AVAILABLE:
            print("ℹ️ [Redis-Async] Operating in degraded mode (Redis not installed)")
        elif not REDIS_ENABLED:
            print("ℹ️ [Redis-Async] Operating in degraded mode (Redis disabled via REDIS_ENABLED=false)")
    
    async def connect(self):
        """Initialize async Redis connection pool."""
        if not REDIS_AVAILABLE:
            return
        if not REDIS_ENABLED:
            print("ℹ️ [Redis-Async] Connection skipped (Redis disabled via REDIS_ENABLED=false)")
            return
        
        try:
            self._pool = ConnectionPool(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD,
                max_connections=REDIS_MAX_CONNECTIONS,
                decode_responses=True,
            )
            self._client = AsyncRedis(connection_pool=self._pool)
            await self._client.ping()
            print(f"✅ [Redis-Async] Connected to {REDIS_HOST}:{REDIS_PORT} (DB {REDIS_DB})")
        except Exception as e:
            print(f"⚠️ [Redis-Async] Connection failed: {e}")
            self._client = None
    
    async def is_available(self) -> bool:
        """Check if async Redis is available."""
        if not REDIS_AVAILABLE:
            return False
        if not REDIS_ENABLED:
            return False
        if self._client is None:
            return False
        try:
            await self._client.ping()
            return True
        except Exception:
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache asynchronously."""
        if not self.is_available():
            return None
        
        try:
            value = await self._client.get(key)
            if value is None:
                return None
            return json.loads(value)
        except Exception as e:
            print(f"⚠️ [Redis-Async] Get error for key '{key}': {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = DEFAULT_TTL) -> bool:
        """Set value in cache with TTL asynchronously."""
        if not self.is_available():
            return False
        
        try:
            serialized = json.dumps(value, default=str)
            await self._client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            print(f"⚠️ [Redis-Async] Set error for key '{key}': {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache asynchronously."""
        if not self.is_available():
            return False
        
        try:
            await self._client.delete(key)
            return True
        except Exception as e:
            print(f"⚠️ [Redis-Async] Delete error for key '{key}': {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern asynchronously."""
        if not self.is_available():
            return 0
        
        try:
            keys = await self._client.keys(pattern)
            if keys:
                return await self._client.delete(*keys)
            return 0
        except Exception as e:
            print(f"⚠️ [Redis-Async] Delete pattern error for '{pattern}': {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists asynchronously."""
        if not self.is_available():
            return False
        
        try:
            return bool(await self._client.exists(key))
        except Exception:
            return False
    
    async def close(self):
        """Close async connection pool."""
        if self._client:
            await self._client.close()
            print("🔌 [Redis-Async] Connection closed")


# Global instances
cache = RedisCache()
async_cache = AsyncRedisCache()


def generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """
    Generate a consistent cache key from parameters.
    
    Args:
        prefix: Key prefix (e.g., "cw:", "market:")
        *args: Positional arguments to include in key
        **kwargs: Keyword arguments to include in key
    
    Returns:
        Hash-based cache key
    """
    key_parts = [prefix]
    
    # Add positional args
    for arg in args:
        if arg is not None:
            key_parts.append(str(arg))
    
    # Add keyword args (sorted for consistency)
    for k in sorted(kwargs.keys()):
        v = kwargs[k]
        if v is not None:
            key_parts.append(f"{k}:{v}")
    
    key_string = ":".join(key_parts)
    
    # Hash if key is too long
    if len(key_string) > 200:
        key_hash = hashlib.md5(key_string.encode()).hexdigest()[:12]
        return f"{prefix}hash:{key_hash}"
    
    return key_string


def invalidate_warrant_cache(symbol: Optional[str] = None):
    """Invalidate warrant cache for specific symbol or all warrants."""
    if symbol:
        pattern = f"{PREFIX_WARRANTS}{symbol}:*"
    else:
        pattern = f"{PREFIX_WARRANTS}*"
    return cache.delete_pattern(pattern)


def invalidate_market_cache(symbol: Optional[str] = None):
    """Invalidate market cache for specific symbol or all market data."""
    if symbol:
        pattern = f"{PREFIX_MARKET}{symbol}:*"
    else:
        pattern = f"{PREFIX_MARKET}*"
    return cache.delete_pattern(pattern)


def invalidate_atc_cache():
    """Invalidate all ATC-related cache."""
    return cache.delete_pattern(f"{PREFIX_ATC}*")


def invalidate_stock_cache():
    """Invalidate all stock history-related cache."""
    return cache.delete_pattern(f"{PREFIX_STOCK}*")


def invalidate_credit_cache():
    """Invalidate all credit-related cache."""
    return cache.delete_pattern(f"{PREFIX_CREDIT}*")


def invalidate_regime_cache():
    """Invalidate all regime-related cache."""
    return cache.delete_pattern(f"{PREFIX_REGIME}*")

def get_regime_cache_key(symbol: str, horizon: int = 1, instrument_type: str = "STOCK") -> str:
    """Generate cache key for regime results."""
    key_data = f"{symbol}:{horizon}:{instrument_type}"
    hash_key = hashlib.md5(key_data.encode()).hexdigest()[:8]
    return f"{PREFIX_REGIME}{symbol}:{hash_key}"

def cache_ensemble_regime(regime_result: dict, symbol: str = "VNINDEX", horizon: int = 1, 
                         instrument_type: str = "STOCK", ttl: int = MEDIUM_TTL) -> bool:
    """Cache ensemble regime result."""
    key = get_regime_cache_key(symbol, horizon, instrument_type)
    return cache.set(key, regime_result, ttl)

def get_cached_regime(symbol: str = "VNINDEX", horizon: int = 1, instrument_type: str = "STOCK") -> Optional[dict]:
    """Get cached ensemble regime result."""
    key = get_regime_cache_key(symbol, horizon, instrument_type)
    return cache.get(key)


def invalidate_all_cache():
    """Invalidate all application cache."""
    patterns = [
        f"{PREFIX_WARRANTS}*",
        f"{PREFIX_MARKET}*",
        f"{PREFIX_CREDIT}*",
        f"{PREFIX_REGIME}*",
        f"{PREFIX_PORTFOLIO}*",
        f"{PREFIX_ATC}*",
    ]
    total = 0
    for pattern in patterns:
        total += cache.delete_pattern(pattern)
    return total
