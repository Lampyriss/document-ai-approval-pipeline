"""
Custom Exceptions for Document AI API
"""

from fastapi import Request
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)


class DocumentAIException(Exception):
    """Base exception for Document AI"""
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        self.message = message
        self.error_code = error_code or "UNKNOWN_ERROR"
        self.details = details or {}
        super().__init__(self.message)


class OCRError(DocumentAIException):
    """OCR processing error"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, error_code="OCR_ERROR", details=details)


class ValidationError(DocumentAIException):
    """Input validation error"""
    def __init__(self, message: str, field: str = None, details: dict = None):
        self.field = field
        super().__init__(message, error_code="VALIDATION_ERROR", details=details)


class FileError(DocumentAIException):
    """File processing error"""
    def __init__(self, message: str, file_name: str = None, details: dict = None):
        self.file_name = file_name
        super().__init__(message, error_code="FILE_ERROR", details=details)


class RateLimitError(DocumentAIException):
    """Rate limit exceeded"""
    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(message, error_code="RATE_LIMIT_ERROR")


class ClassificationError(DocumentAIException):
    """Document classification error"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, error_code="CLASSIFICATION_ERROR", details=details)


class ExtractionError(DocumentAIException):
    """Field extraction error"""
    def __init__(self, message: str, form_type: str = None, details: dict = None):
        self.form_type = form_type
        super().__init__(message, error_code="EXTRACTION_ERROR", details=details)


class DatabaseError(DocumentAIException):
    """Database operation error"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, error_code="DATABASE_ERROR", details=details)


class GeminiAPIError(DocumentAIException):
    """Gemini API error"""
    def __init__(self, message: str, status_code: int = None, details: dict = None):
        self.status_code = status_code
        super().__init__(message, error_code="GEMINI_API_ERROR", details=details)


# Exception Handlers
async def document_ai_exception_handler(request: Request, exc: DocumentAIException):
    """Handle all Document AI exceptions"""
    logger.error(f"{exc.error_code}: {exc.message}", extra={"details": exc.details})
    
    response = {
        "success": False,
        "message": exc.message,
        "error_code": exc.error_code,
        "details": exc.details
    }
    
    # Add specific fields based on exception type
    if isinstance(exc, ValidationError):
        response["field"] = exc.field
    elif isinstance(exc, FileError):
        response["file_name"] = exc.file_name
    elif isinstance(exc, RateLimitError):
        response["retry_after"] = exc.retry_after
    elif isinstance(exc, ExtractionError):
        response["form_type"] = exc.form_type
    elif isinstance(exc, GeminiAPIError):
        response["status_code"] = exc.status_code
    
    return JSONResponse(
        status_code=400 if isinstance(exc, (ValidationError, FileError)) else 500,
        content=response
    )


async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle validation errors with 422 status"""
    logger.warning(f"Validation error: {exc.message}", extra={"field": exc.field})
    
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": exc.message,
            "error_code": "VALIDATION_ERROR",
            "field": exc.field,
            "details": exc.details
        }
    )


async def rate_limit_exception_handler(request: Request, exc: RateLimitError):
    """Handle rate limit errors with 429 status"""
    logger.warning(f"Rate limit exceeded: {exc.message}")
    
    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "message": exc.message,
            "error_code": "RATE_LIMIT_ERROR",
            "retry_after": exc.retry_after
        },
        headers={"Retry-After": str(exc.retry_after)}
    )


async def ocr_exception_handler(request: Request, exc: OCRError):
    """Handle OCR errors"""
    logger.error(f"OCR error: {exc.message}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "OCR processing failed. Please try again with a clearer image.",
            "error_code": "OCR_ERROR",
            "details": exc.details
        }
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """Handle generic exceptions"""
    logger.exception("Unhandled exception")
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error. Please try again later.",
            "error_code": "INTERNAL_ERROR"
        }
    )


# Function to register all exception handlers
def register_exception_handlers(app):
    """Register all exception handlers with FastAPI app"""
    app.add_exception_handler(DocumentAIException, document_ai_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(RateLimitError, rate_limit_exception_handler)
    app.add_exception_handler(OCRError, ocr_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    
    logger.info("✅ Exception handlers registered")
