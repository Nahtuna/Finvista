# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: RATE LIMIT HANDLER
================================
Centralized rate limit handling for vnstock API calls.
Prevents SystemExit crashes from rate limiting by implementing retry logic and graceful fallbacks.
"""

import time
import logging
import sys
import hashlib
import json
import os
from functools import wraps
from typing import Callable, Any, Optional, TypeVar
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

T = TypeVar('T')

class RateLimitHandler:
    """
    Centralized handler for vnstock API rate limits.
    Catches SystemExit and other exceptions to prevent server crashes.
    """
    
    # Configuration
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_INITIAL_DELAY = 2
    DEFAULT_MAX_DELAY = 60
    
    # Cache configuration
    CACHE_DIR = os.path.join("data", "cache", "vnstock")
    CACHE_EXPIRY_MINUTES = 15  # Cache expires after 15 minutes
    
    # Statistics tracking
    _call_count = 0
    _rate_limit_hits = 0
    _successful_calls = 0
    _cache_hits = 0
    _cache_misses = 0
    
    @classmethod
    def _get_cache_path(cls, cache_key: str) -> str:
        """Get the cache file path for a given cache key."""
        os.makedirs(cls.CACHE_DIR, exist_ok=True)
        return os.path.join(cls.CACHE_DIR, f"{cache_key}.json")
    
    @classmethod
    def _get_cached_data(cls, cache_key: str) -> Optional[Any]:
        """Get cached data if it exists and hasn't expired."""
        try:
            cache_path = cls._get_cache_path(cache_key)
            if not os.path.exists(cache_path):
                return None
            
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Check if cache has expired
            cached_at = datetime.fromisoformat(cache_data['cached_at'])
            if datetime.now() - cached_at > timedelta(minutes=cls.CACHE_EXPIRY_MINUTES):
                logger.debug(f"Cache expired for {cache_key}")
                os.remove(cache_path)
                return None
            
            cls._cache_hits += 1
            logger.debug(f"Cache hit for {cache_key}")
            return cache_data['data']
            
        except Exception as e:
            logger.warning(f"Error reading cache for {cache_key}: {e}")
            return None
    
    @classmethod
    def _set_cached_data(cls, cache_key: str, data: Any) -> None:
        """Cache data with timestamp."""
        try:
            cache_path = cls._get_cache_path(cache_key)
            cache_data = {
                'cached_at': datetime.now().isoformat(),
                'data': data
            }
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, default=str)
            logger.debug(f"Cached data for {cache_key}")
        except Exception as e:
            logger.warning(f"Error caching data for {cache_key}: {e}")
    
    @classmethod
    def _generate_cache_key(cls, func_name: str, *args, **kwargs) -> str:
        """Generate a unique cache key based on function name and arguments."""
        key_string = f"{func_name}_{str(args)}_{str(sorted(kwargs.items()))}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    @classmethod
    def get_stats(cls) -> dict:
        """Get rate limit handler statistics."""
        return {
            "total_calls": cls._call_count,
            "rate_limit_hits": cls._rate_limit_hits,
            "successful_calls": cls._successful_calls,
            "cache_hits": cls._cache_hits,
            "cache_misses": cls._cache_misses,
            "success_rate": cls._successful_calls / cls._call_count if cls._call_count > 0 else 0,
            "cache_hit_rate": cls._cache_hits / (cls._cache_hits + cls._cache_misses) if (cls._cache_hits + cls._cache_misses) > 0 else 0
        }
    
    @classmethod
    def reset_stats(cls):
        """Reset statistics."""
        cls._call_count = 0
        cls._rate_limit_hits = 0
        cls._successful_calls = 0
        cls._cache_hits = 0
        cls._cache_misses = 0
    
    @classmethod
    def handle_vnstock_call(
        cls,
        func: Callable[..., T],
        max_retries: int = DEFAULT_MAX_RETRIES,
        initial_delay: float = DEFAULT_INITIAL_DELAY,
        max_delay: float = DEFAULT_MAX_DELAY,
        fallback_value: Optional[T] = None,
        use_cache: bool = True,
        cache_key: Optional[str] = None
    ) -> Optional[T]:
        """
        Execute a vnstock API call with rate limit handling and optional caching.
        
        Args:
            func: The function to execute
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            fallback_value: Value to return if all retries fail
            use_cache: Whether to use caching
            cache_key: Optional custom cache key
            
        Returns:
            Function result or fallback_value if all retries fail
        """
        cls._call_count += 1
        
        # Try to get from cache first
        if use_cache:
            if cache_key is None:
                cache_key = cls._generate_cache_key(func.__name__)
            cached_result = cls._get_cached_data(cache_key)
            if cached_result is not None:
                return cached_result
            cls._cache_misses += 1
        
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                result = func()
                cls._successful_calls += 1
                
                # Cache the successful result
                if use_cache and cache_key:
                    cls._set_cached_data(cache_key, result)
                
                return result
                
            except SystemExit as e:
                cls._rate_limit_hits += 1
                last_exception = e
                logger.warning(f"Rate limit hit (SystemExit) on attempt {attempt + 1}/{max_retries}")
                
                if attempt < max_retries - 1:
                    delay = min(initial_delay * (2 ** attempt), max_delay)
                    logger.info(f"Waiting {delay:.1f}s before retry...")
                    time.sleep(delay)
                else:
                    logger.error(f"Max retries exceeded for vnstock API call. Using fallback.")
                    
            except Exception as e:
                last_exception = e
                logger.warning(f"Error on attempt {attempt + 1}/{max_retries}: {type(e).__name__}: {e}")
                
                if attempt < max_retries - 1:
                    delay = min(initial_delay * (2 ** attempt), max_delay)
                    logger.info(f"Waiting {delay:.1f}s before retry...")
                    time.sleep(delay)
                else:
                    logger.error(f"Max retries exceeded. Using fallback.")
        
        # All retries failed
        logger.warning(f"All retries failed, returning fallback: {type(last_exception).__name__}")
        return fallback_value


def rate_limit_safe(
    max_retries: int = RateLimitHandler.DEFAULT_MAX_RETRIES,
    initial_delay: float = RateLimitHandler.DEFAULT_INITIAL_DELAY,
    max_delay: float = RateLimitHandler.DEFAULT_MAX_DELAY,
    fallback_value: Optional[Any] = None,
    use_cache: bool = True
):
    """
    Decorator to wrap vnstock API calls with rate limit handling.
    
    Usage:
        @rate_limit_safe(max_retries=3, initial_delay=2)
        def fetch_market_data():
            from vnstock import Market
            m = Market()
            return m.index(symbol="VNINDEX").ohlcv()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., Optional[T]]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Optional[T]:
            cache_key = RateLimitHandler._generate_cache_key(func.__name__, *args, **kwargs)
            def inner_func():
                return func(*args, **kwargs)
            
            return RateLimitHandler.handle_vnstock_call(
                inner_func,
                max_retries=max_retries,
                initial_delay=initial_delay,
                max_delay=max_delay,
                fallback_value=fallback_value,
                use_cache=use_cache,
                cache_key=cache_key
            )
        return wrapper
    return decorator


def safe_vnstock_import() -> bool:
    """
    Safely import vnstock and check if it's available.
    Returns True if successful, False otherwise.
    """
    try:
        import vnstock
        return True
    except ImportError:
        logger.error("vnstock package not available")
        return False
    except Exception as e:
        logger.error(f"Error importing vnstock: {e}")
        return False


# Monkey patch sys.exit to prevent SystemExit from crashing the server
_original_exit = sys.exit

def _safe_exit(code=0):
    """
    Override sys.exit to prevent vnstock from crashing the server.
    Allows clean exits (code=0) and multiprocessing child shutdowns through.
    Only intercepts non-zero exits in the main process.
    """
    import multiprocessing
    if code == 0 or multiprocessing.current_process().name != 'MainProcess':
        _original_exit(code)
    logger.warning(f"Intercepted sys.exit({code}) - preventing server crash")
    raise RuntimeError(f"Rate limit exceeded. Exit code: {code}")

def apply_monkey_patch():
    """
    Apply monkey patch to prevent vnstock from crashing the server via sys.exit.
    This should be called once at application startup.
    """
    if sys.exit != _safe_exit:
        sys.exit = _safe_exit
        logger.info("Applied monkey patch to prevent sys.exit crashes")
    else:
        logger.debug("Monkey patch already applied")