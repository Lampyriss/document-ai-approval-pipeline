"""
Dependency Injection for Document AI API
FastAPI Depends pattern for better testability
"""

from fastapi import Depends, HTTPException
from typing import Generator, Optional
import logging

from ocr_service import OCRService, DocumentClassifier, get_ocr_service, get_classifier
from database import Database, get_database
from cache import OCRResultCache, get_ocr_cache
from config import Settings, get_settings

logger = logging.getLogger(__name__)


# Database Dependency
def get_db() -> Generator[Database, None, None]:
    """Get database session"""
    db = get_database()
    try:
        yield db
    finally:
        db.close()


# OCR Service Dependency
def get_ocr_service_dep() -> Generator[OCRService, None, None]:
    """Get OCR service instance"""
    service = get_ocr_service()
    try:
        yield service
    except Exception as e:
        logger.error(f"OCR service error: {e}")
        raise HTTPException(status_code=500, detail="OCR service unavailable")


# Classifier Dependency
def get_classifier_dep() -> Generator[DocumentClassifier, None, None]:
    """Get document classifier"""
    classifier = get_classifier()
    try:
        yield classifier
    except Exception as e:
        logger.error(f"Classifier error: {e}")
        raise HTTPException(status_code=500, detail="Classification service unavailable")


# Cache Dependency
def get_cache() -> OCRResultCache:
    """Get cache instance"""
    return get_ocr_cache()


# Settings Dependency
def get_config() -> Settings:
    """Get application settings"""
    return get_settings()


# Complex dependency: OCR with caching
async def get_ocr_with_cache(
    file_bytes: bytes,
    preprocessing: str = "none",
    cache: OCRResultCache = Depends(get_cache),
    ocr_service: OCRService = Depends(get_ocr_service_dep)
):
    """
    Get OCR result with caching support
    
    Usage in endpoint:
    @app.post("/ocr/extract")
    async def extract(
        file: UploadFile,
        result: tuple = Depends(get_ocr_with_cache)
    ):
        text, details, confidence = result
        ...
    """
    # Check cache
    cached = cache.get(file_bytes, preprocessing)
    if cached:
        return cached
    
    # Process
    result = ocr_service.ocr_document(file_bytes, "application/pdf")
    
    # Cache result
    cache.set(file_bytes, result, preprocessing)
    
    return result


# Permission/Role dependencies (example)
def verify_api_key(x_api_key: Optional[str] = None, settings: Settings = Depends(get_config)):
    """Verify API key if required"""
    if not settings.require_api_key:
        return True
    
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    # Validate API key (implement your logic)
    # if x_api_key != settings.secret_key:
    #     raise HTTPException(status_code=403, detail="Invalid API key")
    
    return True


# Rate limit check dependency
def check_rate_limit(client_ip: str, settings: Settings = Depends(get_config)):
    """Check if request is within rate limit"""
    # Implement rate limiting logic here
    # or use the RateLimitMiddleware
    return True


# Validation dependency example
async def validate_file_upload(
    file: UploadFile,
    settings: Settings = Depends(get_config)
):
    """Validate uploaded file"""
    # Check file size
    content = await file.read()
    if len(content) > settings.max_file_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {settings.max_file_size / 1024 / 1024:.1f}MB"
        )
    
    # Check file type
    if file.content_type not in settings.allowed_file_types:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {file.content_type}"
        )
    
    # Reset file pointer
    await file.seek(0)
    
    return content


# Combined dependencies for endpoints
def get_processing_dependencies(
    db: Database = Depends(get_db),
    ocr: OCRService = Depends(get_ocr_service_dep),
    classifier: DocumentClassifier = Depends(get_classifier_dep),
    cache: OCRResultCache = Depends(get_cache),
    settings: Settings = Depends(get_config)
):
    """Get all processing dependencies at once"""
    return {
        "db": db,
        "ocr": ocr,
        "classifier": classifier,
        "cache": cache,
        "settings": settings
    }


# Example usage in endpoint:
"""
@app.post("/ocr/extract")
async def extract_document(
    file: UploadFile = File(...),
    deps: dict = Depends(get_processing_dependencies)
):
    # Use dependencies
    ocr_service = deps["ocr"]
    cache = deps["cache"]
    
    content = await file.read()
    
    # Check cache
    cached = cache.get(content)
    if cached:
        return cached
    
    # Process
    result = ocr_service.ocr_document(content, file.content_type)
    
    # Cache result
    cache.set(content, result)
    
    return result
"""
