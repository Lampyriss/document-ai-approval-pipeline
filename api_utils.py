# Advanced API Utilities
# เพิ่ม features: Request ID, Caching, Retry Logic

import hashlib
import time
import functools
from typing import Optional, Dict, Any, Callable
from uuid import uuid4
import logging

logger = logging.getLogger(__name__)


# ==========================================
# Request ID Tracking
# ==========================================

class RequestIDMiddleware:
    """Middleware to add unique request ID to each request"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Generate unique request ID
            request_id = str(uuid4())[:8]
            
            # Add to scope
            scope["request_id"] = request_id
            
            # Modify response headers
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    headers = list(message.get("headers", []))
                    headers.append((b"X-Request-ID", request_id.encode()))
                    message["headers"] = headers
                await send(message)
            
            await self.app(scope, receive, send_wrapper)
        else:
            await self.app(scope, receive, send)


def get_request_id(request) -> str:
    """Get request ID from current request"""
    return getattr(request.state, "request_id", str(uuid4())[:8])


# ==========================================
# Simple In-Memory Cache
# ==========================================

class OCRCache:
    """
    Simple in-memory cache for OCR results
    Uses file content hash as key
    """
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 3600):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._max_size = max_size
        self._ttl = ttl_seconds
    
    def _get_hash(self, content: bytes) -> str:
        """Generate hash from file content"""
        return hashlib.md5(content).hexdigest()
    
    def _cleanup_expired(self):
        """Remove expired entries"""
        now = time.time()
        expired_keys = [
            k for k, v in self._cache.items()
            if now - v["timestamp"] > self._ttl
        ]
        for key in expired_keys:
            del self._cache[key]
    
    def get(self, content: bytes) -> Optional[Dict[str, Any]]:
        """Get cached OCR result for content"""
        self._cleanup_expired()
        
        key = self._get_hash(content)
        if key in self._cache:
            entry = self._cache[key]
            if time.time() - entry["timestamp"] <= self._ttl:
                logger.info(f"Cache HIT for {key[:8]}...")
                return entry["result"]
            else:
                del self._cache[key]
        
        logger.info(f"Cache MISS for {key[:8]}...")
        return None
    
    def set(self, content: bytes, result: Dict[str, Any]):
        """Store OCR result in cache"""
        # Cleanup if cache is full
        if len(self._cache) >= self._max_size:
            # Remove oldest entry
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k]["timestamp"])
            del self._cache[oldest_key]
        
        key = self._get_hash(content)
        self._cache[key] = {
            "result": result,
            "timestamp": time.time()
        }
        logger.info(f"Cached result for {key[:8]}...")
    
    def clear(self):
        """Clear all cache"""
        self._cache.clear()
        logger.info("Cache cleared")
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "ttl_seconds": self._ttl
        }


# Global cache instance
_ocr_cache: Optional[OCRCache] = None

def get_ocr_cache() -> OCRCache:
    """Get singleton cache instance"""
    global _ocr_cache
    if _ocr_cache is None:
        _ocr_cache = OCRCache(max_size=100, ttl_seconds=3600)
    return _ocr_cache


# ==========================================
# Retry Logic
# ==========================================

def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for retry with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries (seconds)
        backoff_factor: Multiply delay by this factor each retry
        exceptions: Tuple of exceptions to catch and retry
    
    Usage:
        @retry_with_backoff(max_retries=3)
        def my_function():
            ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries} failed: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(f"All {max_retries} attempts failed: {e}")
            
            raise last_exception
        
        return wrapper
    return decorator


async def async_retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0
):
    """
    Async version of retry with backoff
    
    Usage:
        result = await async_retry_with_backoff(
            lambda: ocr_service.process(content),
            max_retries=3
        )
    """
    import asyncio
    
    delay = initial_delay
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return await asyncio.get_event_loop().run_in_executor(None, func)
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                logger.warning(
                    f"Async attempt {attempt + 1}/{max_retries} failed: {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                await asyncio.sleep(delay)
                delay *= backoff_factor
            else:
                logger.error(f"All {max_retries} async attempts failed: {e}")
    
    raise last_exception


# ==========================================
# Rate Limiting (Simple)
# ==========================================

class SimpleRateLimiter:
    """
    Simple in-memory rate limiter
    Uses sliding window algorithm
    """
    
    def __init__(self, requests_per_minute: int = 60):
        self._requests: Dict[str, list] = {}
        self._limit = requests_per_minute
        self._window = 60  # 1 minute
    
    def is_allowed(self, client_id: str) -> bool:
        """Check if client is allowed to make request"""
        now = time.time()
        
        # Get client's request history
        if client_id not in self._requests:
            self._requests[client_id] = []
        
        # Remove old requests outside window
        self._requests[client_id] = [
            t for t in self._requests[client_id]
            if now - t < self._window
        ]
        
        # Check limit
        if len(self._requests[client_id]) >= self._limit:
            return False
        
        # Record new request
        self._requests[client_id].append(now)
        return True
    
    def get_remaining(self, client_id: str) -> int:
        """Get remaining requests for client"""
        now = time.time()
        if client_id not in self._requests:
            return self._limit
        
        recent = [t for t in self._requests[client_id] if now - t < self._window]
        return max(0, self._limit - len(recent))


# Global rate limiter
_rate_limiter: Optional[SimpleRateLimiter] = None

def get_rate_limiter() -> SimpleRateLimiter:
    """Get singleton rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = SimpleRateLimiter(requests_per_minute=60)
    return _rate_limiter


# ==========================================
# Batch Processing Helper
# ==========================================

from dataclasses import dataclass, field
from typing import List
import asyncio


@dataclass
class BatchJob:
    """Represents a batch processing job"""
    job_id: str
    status: str = "pending"  # pending, processing, completed, failed
    total_files: int = 0
    processed_files: int = 0
    results: List[Dict] = field(default_factory=list)
    errors: List[Dict] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None


class BatchJobManager:
    """Manages batch processing jobs"""
    
    def __init__(self, max_jobs: int = 50):
        self._jobs: Dict[str, BatchJob] = {}
        self._max_jobs = max_jobs
    
    def create_job(self, total_files: int) -> BatchJob:
        """Create a new batch job"""
        # Cleanup old jobs
        self._cleanup_old_jobs()
        
        job_id = str(uuid4())[:12]
        job = BatchJob(job_id=job_id, total_files=total_files)
        self._jobs[job_id] = job
        logger.info(f"Created batch job {job_id} with {total_files} files")
        return job
    
    def get_job(self, job_id: str) -> Optional[BatchJob]:
        """Get job by ID"""
        return self._jobs.get(job_id)
    
    def update_job(self, job_id: str, **kwargs):
        """Update job attributes"""
        if job_id in self._jobs:
            job = self._jobs[job_id]
            for key, value in kwargs.items():
                if hasattr(job, key):
                    setattr(job, key, value)
    
    def add_result(self, job_id: str, result: Dict):
        """Add a result to job"""
        if job_id in self._jobs:
            job = self._jobs[job_id]
            job.results.append(result)
            job.processed_files += 1
            
            # Check if complete
            if job.processed_files >= job.total_files:
                job.status = "completed"
                job.completed_at = time.time()
    
    def add_error(self, job_id: str, error: Dict):
        """Add an error to job"""
        if job_id in self._jobs:
            job = self._jobs[job_id]
            job.errors.append(error)
            job.processed_files += 1
    
    def _cleanup_old_jobs(self):
        """Remove jobs older than 1 hour"""
        now = time.time()
        old_jobs = [
            jid for jid, job in self._jobs.items()
            if now - job.created_at > 3600
        ]
        for jid in old_jobs:
            del self._jobs[jid]
        
        # Also limit total jobs
        if len(self._jobs) > self._max_jobs:
            oldest = sorted(
                self._jobs.items(),
                key=lambda x: x[1].created_at
            )[:len(self._jobs) - self._max_jobs]
            for jid, _ in oldest:
                del self._jobs[jid]


# Global batch manager
_batch_manager: Optional[BatchJobManager] = None

def get_batch_manager() -> BatchJobManager:
    """Get singleton batch manager instance"""
    global _batch_manager
    if _batch_manager is None:
        _batch_manager = BatchJobManager()
    return _batch_manager


# ==========================================
# Signature Detection (Basic)
# ==========================================

import numpy as np
from PIL import Image
import io


class SignatureDetector:
    """
    Basic signature detection using image analysis
    Detects areas with handwriting-like patterns
    """
    
    def __init__(self, min_area_ratio: float = 0.01, max_area_ratio: float = 0.15):
        self.min_area_ratio = min_area_ratio
        self.max_area_ratio = max_area_ratio
    
    def detect(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Detect signature in image
        
        Returns:
            {
                "has_signature": bool,
                "confidence": float,
                "regions": list of bounding boxes
            }
        """
        try:
            # Load image
            img = Image.open(io.BytesIO(image_bytes))
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img_array = np.array(img)
            
            # Convert to grayscale
            gray = np.mean(img_array, axis=2)
            
            # Binary threshold (detect dark regions)
            threshold = 100
            binary = gray < threshold
            
            # Look for signature-like regions
            # Signatures tend to be in bottom portion of document
            height, width = binary.shape
            bottom_region = binary[int(height * 0.6):, :]  # Bottom 40%
            
            # Calculate dark pixel ratio
            dark_ratio = np.sum(bottom_region) / bottom_region.size
            
            # Signature typically has moderate ink coverage
            has_signature = self.min_area_ratio < dark_ratio < self.max_area_ratio
            
            # Confidence based on how typical the pattern is
            if has_signature:
                # Closer to middle of range = higher confidence
                mid = (self.min_area_ratio + self.max_area_ratio) / 2
                distance = abs(dark_ratio - mid)
                max_distance = (self.max_area_ratio - self.min_area_ratio) / 2
                confidence = 1.0 - (distance / max_distance) * 0.5
            else:
                confidence = 0.3
            
            return {
                "has_signature": has_signature,
                "confidence": round(confidence, 3),
                "ink_ratio": round(dark_ratio, 4),
                "analysis_region": "bottom_40%"
            }
            
        except Exception as e:
            logger.error(f"Signature detection error: {e}")
            return {
                "has_signature": False,
                "confidence": 0.0,
                "error": str(e)
            }


# Global signature detector
_signature_detector: Optional[SignatureDetector] = None

def get_signature_detector() -> SignatureDetector:
    """Get singleton signature detector instance"""
    global _signature_detector
    if _signature_detector is None:
        _signature_detector = SignatureDetector()
    return _signature_detector


# ==========================================
# OCR Auto-Correction
# ==========================================

class OCRAutoCorrector:
    """
    Auto-correct common OCR errors using rules and patterns
    """
    
    # Common OCR mistakes: wrong -> correct
    CORRECTIONS = {
        # Numbers confused with letters
        "0": ["O", "o"],
        "1": ["l", "I", "|"],
        "5": ["S", "s"],
        "8": ["B"],
        
        # Letters confused with numbers
        "O": ["0"],
        "l": ["1", "|"],
        "I": ["1", "|"],
        "S": ["5"],
        "B": ["8"],
        
        # Thai common mistakes
        "ก": ["n"],
        "ด": ["ค"],
        "ภ": ["ค"],
    }
    
    # Patterns for specific fields
    STUDENT_ID_PATTERN = r'^[5-7][0-9]{9}$'
    COURSE_CODE_PATTERN = r'^[0-9]{8}$'
    
    def __init__(self):
        import re
        self.re = re
    
    def correct_student_id(self, text: str) -> str:
        """
        Correct OCR errors in student ID
        Student ID should be 10 digits starting with 5, 6, or 7
        """
        if not text:
            return text
        
        # Remove spaces and common substitutions
        corrected = text.strip().replace(" ", "")
        
        # Fix letter->number substitutions
        substitutions = {
            'O': '0', 'o': '0',
            'l': '1', 'I': '1', '|': '1',
            'S': '5', 's': '5',
            'B': '8', 'b': '8',
            'g': '9', 'q': '9',
        }
        
        for wrong, right in substitutions.items():
            corrected = corrected.replace(wrong, right)
        
        # Validate
        if self.re.match(self.STUDENT_ID_PATTERN, corrected):
            if corrected != text:
                logger.info(f"Auto-corrected student ID: {text} → {corrected}")
            return corrected
        
        return text  # Return original if can't fix
    
    def correct_course_code(self, text: str) -> str:
        """
        Correct OCR errors in course code
        Course code should be 8 digits
        """
        if not text:
            return text
        
        corrected = text.strip().replace(" ", "").replace("-", "")
        
        # Fix letter->number substitutions
        substitutions = {
            'O': '0', 'o': '0',
            'l': '1', 'I': '1', '|': '1',
            'S': '5', 's': '5',
            'B': '8',
        }
        
        for wrong, right in substitutions.items():
            corrected = corrected.replace(wrong, right)
        
        if self.re.match(self.COURSE_CODE_PATTERN, corrected):
            if corrected != text:
                logger.info(f"Auto-corrected course code: {text} → {corrected}")
            return corrected
        
        return text
    
    def correct_name(self, text: str) -> str:
        """
        Clean up name field
        Remove numbers and special characters that shouldn't be in names
        """
        if not text:
            return text
        
        # Remove numbers (likely OCR errors in names)
        corrected = self.re.sub(r'[0-9]', '', text)
        
        # Remove special characters except spaces and hyphens
        corrected = self.re.sub(r'[^\w\s\-\u0E00-\u0E7F]', '', corrected)
        
        # Clean up extra spaces
        corrected = ' '.join(corrected.split())
        
        if corrected != text:
            logger.info(f"Auto-corrected name: {text} → {corrected}")
        
        return corrected
    
    def correct_extracted_data(self, data: Dict) -> Dict:
        """
        Apply corrections to all fields in extracted data
        """
        corrected = data.copy()
        
        if 'student_id' in corrected:
            corrected['student_id'] = self.correct_student_id(corrected['student_id'])
        
        if 'name' in corrected:
            corrected['name'] = self.correct_name(corrected['name'])
        
        if 'courses' in corrected and isinstance(corrected['courses'], list):
            for course in corrected['courses']:
                if 'course_code' in course:
                    course['course_code'] = self.correct_course_code(course['course_code'])
        
        if 'prerequisite_course' in corrected and corrected['prerequisite_course']:
            if 'course_code' in corrected['prerequisite_course']:
                corrected['prerequisite_course']['course_code'] = self.correct_course_code(
                    corrected['prerequisite_course']['course_code']
                )
        
        if 'continuing_course' in corrected and corrected['continuing_course']:
            if 'course_code' in corrected['continuing_course']:
                corrected['continuing_course']['course_code'] = self.correct_course_code(
                    corrected['continuing_course']['course_code']
                )
        
        return corrected


# Global auto-corrector
_auto_corrector: Optional[OCRAutoCorrector] = None

def get_auto_corrector() -> OCRAutoCorrector:
    """Get singleton auto-corrector instance"""
    global _auto_corrector
    if _auto_corrector is None:
        _auto_corrector = OCRAutoCorrector()
    return _auto_corrector
