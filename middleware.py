"""
Input Validation, Security, and Logging Middleware
Includes: Request validation, rate limiting, security headers,
          structured JSON logging, and optional HMAC webhook auth
"""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import magic
import io
import re
import os
import json
import hmac
import hashlib
from typing import Optional
import logging
import time
from collections import defaultdict

from config import settings, is_file_size_allowed, is_file_type_allowed

logger = logging.getLogger(__name__)


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Validate incoming requests"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.max_file_size = settings.max_file_size
        self.allowed_types = settings.allowed_file_types
    
    async def dispatch(self, request: Request, call_next):
        # Log request
        logger.info(f"{request.method} {request.url.path}")
        
        # Skip validation for health endpoints
        if request.url.path in ["/health", "/ready", "/metrics"]:
            return await call_next(request)
        
        # Check for file uploads
        if request.method == "POST" and "multipart/form-data" in request.headers.get("content-type", ""):
            try:
                await self._validate_file_upload(request)
            except ValueError as e:
                logger.warning(f"File validation failed: {e}")
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "message": str(e),
                        "error_type": "validation_error"
                    }
                )
        
        response = await call_next(request)
        return response
    
    async def _validate_file_upload(self, request: Request):
        """Validate file upload"""
        # Get content length
        content_length = request.headers.get("content-length")
        if content_length:
            size = int(content_length)
            if size > self.max_file_size:
                raise ValueError(f"File too large. Max size: {self.max_file_size / 1024 / 1024:.1f}MB")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.requests = defaultdict(list)
        self.max_requests = settings.rate_limit_requests_per_minute
        self.window = 60  # 60 seconds
    
    async def dispatch(self, request: Request, call_next):
        if not settings.rate_limit_enabled:
            return await call_next(request)
        
        # Skip rate limit for health checks
        if request.url.path in ["/health", "/ready"]:
            return await call_next(request)
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Clean old requests
        current_time = time.time()
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if current_time - req_time < self.window
        ]
        
        # Check rate limit
        if len(self.requests[client_ip]) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "message": "Rate limit exceeded. Please try again later.",
                    "error_type": "rate_limit_error"
                }
            )
        
        # Record request
        self.requests[client_ip].append(current_time)
        
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to responses"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Structured JSON request/response logging"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        client_ip = request.client.host if request.client else "unknown"
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        # Structured JSON log entry
        log_entry = {
            "type": "request",
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "latency_ms": round(process_time * 1000, 1),
            "client_ip": client_ip,
        }
        
        # Log level based on status code
        if response.status_code >= 500:
            logger.error(json.dumps(log_entry, ensure_ascii=False))
        elif response.status_code >= 400:
            logger.warning(json.dumps(log_entry, ensure_ascii=False))
        else:
            logger.info(json.dumps(log_entry, ensure_ascii=False))
        
        # Add response time header
        response.headers["X-Process-Time"] = f"{process_time:.3f}"
        
        return response


# ===== Optional Webhook Auth (HMAC-SHA256) =====
# Set PA_WEBHOOK_SECRET in HF Space Secrets to enable
_WEBHOOK_SECRET = os.environ.get("PA_WEBHOOK_SECRET", "")


class WebhookAuthMiddleware(BaseHTTPMiddleware):
    """
    Optional HMAC-SHA256 signature verification for webhook endpoints.
    Only active when PA_WEBHOOK_SECRET env var is set.
    Checks X-PA-Signature header against HMAC of request body.
    """
    
    # Endpoints that require auth (when secret is set)
    PROTECTED_PATHS = [
        "/api/dashboard/webhook",
        "/api/cover-sheet/generate",
        "/api/final-document/generate",
    ]
    
    async def dispatch(self, request: Request, call_next):
        # Skip if no secret configured (backward-compatible)
        if not _WEBHOOK_SECRET:
            return await call_next(request)
        
        # Only check POST requests to protected endpoints
        if request.method != "POST" or request.url.path not in self.PROTECTED_PATHS:
            return await call_next(request)
        
        # Read body for signature check
        body = await request.body()
        
        # Get signature from header
        signature = request.headers.get("X-PA-Signature", "")
        if not signature:
            logger.warning(f"Webhook auth: missing X-PA-Signature for {request.url.path}")
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "message": "Missing X-PA-Signature header",
                    "error_type": "auth_error"
                }
            )
        
        # Compute expected HMAC
        expected = hmac.new(
            _WEBHOOK_SECRET.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected):
            logger.warning(f"Webhook auth: invalid signature for {request.url.path}")
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "message": "Invalid webhook signature",
                    "error_type": "auth_error"
                }
            )
        
        return await call_next(request)


# File validation functions
def validate_file_type(file_bytes: bytes, declared_content_type: str) -> bool:
    """Validate file type using magic numbers"""
    try:
        detected_type = magic.from_buffer(file_bytes, mime=True)
        
        # Check if detected type matches declared type
        if detected_type != declared_content_type:
            logger.warning(f"File type mismatch: declared={declared_content_type}, detected={detected_type}")
            return False
        
        # Check if type is allowed
        return is_file_type_allowed(detected_type)
    except Exception as e:
        logger.error(f"Error validating file type: {e}")
        return False


def validate_pdf_content(file_bytes: bytes) -> tuple[bool, Optional[str]]:
    """Validate PDF content and structure"""
    try:
        import fitz
        
        # Open PDF
        pdf_document = fitz.open(stream=file_bytes, filetype="pdf")
        
        # Check number of pages
        page_count = len(pdf_document)
        if page_count > settings.max_pages_per_pdf:
            return False, f"PDF has too many pages ({page_count}). Max: {settings.max_pages_per_pdf}"
        
        if page_count == 0:
            return False, "PDF has no pages"
        
        # Check if PDF is encrypted
        if pdf_document.is_encrypted:
            return False, "PDF is encrypted"
        
        pdf_document.close()
        return True, None
        
    except Exception as e:
        return False, f"Invalid PDF: {str(e)}"


def validate_image_content(file_bytes: bytes) -> tuple[bool, Optional[str]]:
    """Validate image content"""
    try:
        from PIL import Image
        import io
        
        image = Image.open(io.BytesIO(file_bytes))
        
        # Check image dimensions
        width, height = image.size
        if width < 10 or height < 10:
            return False, "Image too small"
        
        if width > 10000 or height > 10000:
            return False, "Image too large"
        
        return True, None
        
    except Exception as e:
        return False, f"Invalid image: {str(e)}"


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal"""
    # Remove path components
    filename = filename.replace("..", "")
    filename = filename.replace("/", "_")
    filename = filename.replace("\\", "_")
    
    # Remove special characters
    filename = re.sub(r'[<>"|?*]', "", filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
        filename = name[:250] + "." + ext if ext else name[:255]
    
    return filename


def validate_student_id(student_id: str) -> tuple[bool, Optional[str]]:
    """Validate student ID format"""
    # Must be 10 digits
    if not re.match(r'^[0-9]{10}$', student_id):
        return False, "Student ID must be 10 digits"
    
    # Must start with 6 (year 60-70)
    if not student_id.startswith('6'):
        return False, "Student ID must start with 6 (e.g., 6530111573)"
    
    return True, None


def validate_email(email: str) -> tuple[bool, Optional[str]]:
    """Validate email format"""
    # Basic email pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(pattern, email):
        return False, "Invalid email format"
    
    # Check if @live.ku.th for students
    if "@live.ku.th" not in email and "@ku.ac.th" not in email:
        return False, "Email must be @live.ku.th or @ku.ac.th"
    
    return True, None


def validate_course_code(course_code: str) -> tuple[bool, Optional[str]]:
    """Validate course code format"""
    # Must be 8 digits
    if not re.match(r'^[0-9]{8}$', course_code):
        return False, "Course code must be 8 digits (e.g., 01418111)"
    
    return True, None


# Exception handlers
async def validation_exception_handler(request: Request, exc: ValueError):
    """Handle validation errors"""
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "message": str(exc),
            "error_type": "validation_error"
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "error_type": "http_error"
        }
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """Handle generic exceptions"""
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "error_type": "internal_error"
        }
    )
