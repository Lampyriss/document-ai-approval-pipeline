"""
Configuration Management for Document AI API
Centralized config using Pydantic Settings
"""

from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import Optional, List
import os

DEFAULT_PUBLIC_APP_URL = os.environ.get(
    "PUBLIC_APP_URL", "https://document-ai-api.example.com"
)


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # API Configuration
    app_name: str = Field(default="Document AI - OCR API", description="Application name")
    app_version: str = Field(default="4.2.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    
    # File Upload Configuration
    max_file_size: int = Field(default=10 * 1024 * 1024, description="Max file size in bytes (10MB)")
    allowed_file_types: List[str] = Field(
        default=["application/pdf", "image/jpeg", "image/png", "image/tiff"],
        description="Allowed MIME types"
    )
    max_pages_per_pdf: int = Field(default=5, description="Maximum pages per PDF")
    
    # OCR Configuration
    ocr_engine: str = Field(default="gemini", description="Primary OCR engine (gemini/easyocr/tesseract)")
    ocr_dpi: int = Field(default=200, description="DPI for PDF to image conversion")
    ocr_confidence_threshold: float = Field(default=0.70, description="Minimum OCR confidence")
    
    # Gemini Vision Configuration
    gemini_api_key: str = Field(default="", description="Google Gemini API Key")
    gemini_model: str = Field(default="gemini-2.5-flash", description="Gemini model name")
    gemini_max_requests_per_minute: int = Field(default=15, description="Max Gemini requests per minute")
    
    # EasyOCR Configuration (Legacy)
    easyocr_gpu: bool = Field(default=False, description="Use GPU for EasyOCR")
    easyocr_languages: List[str] = Field(default=["th", "en"], description="EasyOCR languages")
    
    # Database Configuration
    database_url: str = Field(default="sqlite:///./ocr_database.db", description="Database URL")
    database_echo: bool = Field(default=False, description="Echo SQL queries")
    
    # Cache Configuration
    cache_enabled: bool = Field(default=True, description="Enable caching")
    cache_ttl: int = Field(default=3600, description="Cache TTL in seconds")
    cache_max_size: int = Field(default=1000, description="Maximum cache entries")
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests_per_minute: int = Field(default=60, description="Max requests per minute")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format"
    )
    
    # Prometheus Metrics
    prometheus_enabled: bool = Field(default=False, description="Enable Prometheus metrics")
    prometheus_port: int = Field(default=9090, description="Prometheus port")
    
    # MCP Integration
    mcp_enabled: bool = Field(default=False, description="Enable MCP integration")
    
    # CORS Configuration
    cors_origins: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "https://flow.microsoft.com",
            "https://make.powerautomate.com",
            "https://*.sharepoint.com",
            "https://*.office.com",
            DEFAULT_PUBLIC_APP_URL,
        ],
        description="Allowed CORS origins"
    )
    cors_allow_credentials: bool = Field(default=True, description="Allow credentials")
    cors_allow_methods: List[str] = Field(default=["*"], description="Allowed methods")
    cors_allow_headers: List[str] = Field(default=["*"], description="Allowed headers")
    
    # Security
    secret_key: str = Field(
        default_factory=lambda: os.environ.get("SECRET_KEY", ""),
        description="Secret key - set SECRET_KEY in HF Space Secrets"
    )
    api_key_header: str = Field(default="X-API-Key", description="API key header name")
    require_api_key: bool = Field(default=False, description="Require API key")
    
    # Validation
    @validator('max_file_size')
    def validate_max_file_size(cls, v):
        """Validate max file size is reasonable"""
        if v > 50 * 1024 * 1024:  # 50MB
            raise ValueError("max_file_size cannot exceed 50MB")
        if v < 1024:  # 1KB
            raise ValueError("max_file_size must be at least 1KB")
        return v
    
    @validator('ocr_dpi')
    def validate_ocr_dpi(cls, v):
        """Validate OCR DPI"""
        if v < 72:
            raise ValueError("ocr_dpi must be at least 72")
        if v > 600:
            raise ValueError("ocr_dpi cannot exceed 600")
        return v
    
    @validator('gemini_max_requests_per_minute')
    def validate_gemini_rate(cls, v):
        """Validate Gemini rate limit"""
        if v < 1:
            raise ValueError("gemini_max_requests_per_minute must be at least 1")
        if v > 60:
            raise ValueError("gemini_max_requests_per_minute cannot exceed 60 (Gemini free tier)")
        return v
    
    @validator('log_level')
    def validate_log_level(cls, v):
        """Validate log level"""
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed_levels:
            raise ValueError(f"log_level must be one of {allowed_levels}")
        return v.upper()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings


def reload_settings() -> Settings:
    """Reload settings from environment (useful for testing)"""
    global settings
    settings = Settings()
    return settings


# Utility functions for common checks
def is_file_size_allowed(size: int) -> bool:
    """Check if file size is within allowed limit"""
    return size <= settings.max_file_size


def is_file_type_allowed(content_type: str) -> bool:
    """Check if file type is allowed"""
    return content_type in settings.allowed_file_types


def get_cors_origins() -> List[str]:
    """Get CORS origins (handles wildcard)"""
    if "*" in settings.cors_origins:
        return ["*"]
    return settings.cors_origins


# Production safety checks
def validate_production_settings():
    """Validate settings for production deployment"""
    warnings = []
    
    if settings.debug:
        warnings.append("DEBUG mode is enabled - should be False in production")
    
    if settings.secret_key == "your-secret-key-change-in-production":
        warnings.append("Default secret key is being used - change for production")
    
    if "*" in settings.cors_origins:
        warnings.append("CORS allows all origins (*) - restrict for production")
    
    if not settings.gemini_api_key and settings.ocr_engine == "gemini":
        warnings.append("GEMINI_API_KEY is not set but gemini is the primary OCR engine")
    
    if settings.require_api_key and not settings.api_key_header:
        warnings.append("API key requirement is enabled but no header name configured")
    
    return warnings


if __name__ == "__main__":
    # Print current settings
    print(f"Application: {settings.app_name} v{settings.app_version}")
    print(f"Debug Mode: {settings.debug}")
    print(f"Max File Size: {settings.max_file_size / 1024 / 1024:.1f} MB")
    print(f"OCR Engine: {settings.ocr_engine}")
    print(f"Database: {settings.database_url}")
    print(f"Cache Enabled: {settings.cache_enabled}")
    print(f"Rate Limit: {settings.rate_limit_requests_per_minute} req/min")
    
    # Check production settings
    warnings = validate_production_settings()
    if warnings:
        print("\n⚠️  Production Warnings:")
        for warning in warnings:
            print(f"  - {warning}")
