"""
Caching System for Document AI API
Reduce OCR processing time by caching results
"""

import hashlib
import time
from typing import Optional, Any, Dict
from functools import wraps
import logging
from config import settings

logger = logging.getLogger(__name__)


class CacheEntry:
    """Cache entry with TTL"""
    def __init__(self, value: Any, ttl: int = 3600):
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl
        self.access_count = 0
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        return time.time() - self.created_at > self.ttl
    
    def touch(self):
        """Update access count"""
        self.access_count += 1


class OCRResultCache:
    """Cache for OCR results based on file hash"""
    
    def __init__(self, max_size: int = None, default_ttl: int = None):
        self.max_size = max_size or settings.cache_max_size
        self.default_ttl = default_ttl or settings.cache_ttl
        self.cache: Dict[str, CacheEntry] = {}
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }
    
    def _generate_key(self, file_bytes: bytes, preprocessing: str = "none") -> str:
        """Generate cache key from file content and preprocessing"""
        # Use MD5 hash of file content + preprocessing mode
        file_hash = hashlib.md5(file_bytes).hexdigest()
        return f"{file_hash}:{preprocessing}"
    
    def get(self, file_bytes: bytes, preprocessing: str = "none") -> Optional[Any]:
        """Get cached OCR result"""
        if not settings.cache_enabled:
            return None
        
        key = self._generate_key(file_bytes, preprocessing)
        entry = self.cache.get(key)
        
        if entry is None:
            self.stats["misses"] += 1
            logger.debug(f"Cache miss: {key[:16]}...")
            return None
        
        if entry.is_expired():
            del self.cache[key]
            self.stats["misses"] += 1
            logger.debug(f"Cache expired: {key[:16]}...")
            return None
        
        entry.touch()
        self.stats["hits"] += 1
        logger.info(f"✅ Cache hit: {key[:16]}... (accessed {entry.access_count} times)")
        return entry.value
    
    def set(self, file_bytes: bytes, result: Any, preprocessing: str = "none", ttl: int = None) -> None:
        """Cache OCR result"""
        if not settings.cache_enabled:
            return
        
        # Check cache size and evict if necessary
        if len(self.cache) >= self.max_size:
            self._evict_oldest()
        
        key = self._generate_key(file_bytes, preprocessing)
        ttl = ttl or self.default_ttl
        
        self.cache[key] = CacheEntry(result, ttl)
        logger.info(f"💾 Cached result: {key[:16]}... (TTL: {ttl}s)")
    
    def _evict_oldest(self) -> None:
        """Evict oldest cache entry"""
        if not self.cache:
            return
        
        # Find oldest entry
        oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k].created_at)
        del self.cache[oldest_key]
        self.stats["evictions"] += 1
        logger.debug(f"Evicted cache entry: {oldest_key[:16]}...")
    
    def clear(self) -> None:
        """Clear all cache entries"""
        self.cache.clear()
        logger.info("Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "evictions": self.stats["evictions"],
            "hit_rate": f"{hit_rate:.1f}%",
            "enabled": settings.cache_enabled
        }
    
    def cleanup_expired(self) -> int:
        """Remove expired entries and return count of removed items"""
        expired_keys = [
            key for key, entry in self.cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)


# Global cache instance
_ocr_cache: Optional[OCRResultCache] = None


def get_ocr_cache() -> OCRResultCache:
    """Get OCR result cache instance (singleton)"""
    global _ocr_cache
    if _ocr_cache is None:
        _ocr_cache = OCRResultCache()
    return _ocr_cache


def cached_ocr(ttl: int = None):
    """Decorator to cache OCR function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(file_bytes: bytes, content_type: str, preprocessing: str = "none", *args, **kwargs):
            cache = get_ocr_cache()
            
            # Try to get from cache
            cached_result = cache.get(file_bytes, preprocessing)
            if cached_result is not None:
                return cached_result
            
            # Process and cache result
            result = func(file_bytes, content_type, preprocessing, *args, **kwargs)
            cache.set(file_bytes, result, preprocessing, ttl)
            
            return result
        return wrapper
    return decorator


# Utility functions
def compute_file_hash(file_bytes: bytes, algorithm: str = "md5") -> str:
    """Compute hash of file bytes"""
    if algorithm == "md5":
        return hashlib.md5(file_bytes).hexdigest()
    elif algorithm == "sha256":
        return hashlib.sha256(file_bytes).hexdigest()
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")


def invalidate_cache() -> None:
    """Invalidate all cached results"""
    cache = get_ocr_cache()
    cache.clear()
    logger.info("All cached results invalidated")


def get_cache_info() -> Dict[str, Any]:
    """Get cache information for monitoring"""
    cache = get_ocr_cache()
    return cache.get_stats()


# Cache warming (optional - preload common templates)
def warm_cache(template_files: list) -> None:
    """Warm cache with common templates"""
    logger.info(f"Warming cache with {len(template_files)} templates...")
    # This would process common templates and cache them
    # Implementation depends on specific use case
    pass
