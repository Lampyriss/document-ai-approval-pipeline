# Document AI - OCR API
# ใช้งานจริงพร้อม OCR Module

"""
API รับไฟล์ PDF/รูปภาพ แล้วใช้ OCR อ่านข้อมูลส่งกลับเป็น JSON
สำหรับให้ Power Automate เรียกใช้งาน

วิธีใช้งาน:
1. pip install -r requirements.txt
2. python main.py
3. API จะรันที่ http://localhost:8000
4. ทดสอบด้วย http://localhost:8000/docs (Swagger UI)
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, APIRouter, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
from contextlib import asynccontextmanager
import uvicorn
import time
import logging
import json
from datetime import datetime

# Prometheus Metrics (v4.1 - Enterprise)
try:
    from prometheus_fastapi_instrumentator import Instrumentator
    from prometheus_client import Counter, Histogram
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import OCR Service
from ocr_service import (
    get_ocr_service,
    get_classifier,
    get_extractor,
    get_review_analyzer,
    process_document_with_review
)

# Import Advanced Utilities
from api_utils import (
    RequestIDMiddleware,
    get_ocr_cache,
    get_rate_limiter,
    get_batch_manager,
    get_signature_detector,
    get_auto_corrector,
    retry_with_backoff
)

# Import Database (v4.1)
try:
    from database import get_database
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False

# Import MCP Integration (NEW)
try:
    from mcp_endpoints import register_mcp_routes
    MCP_AVAILABLE = True
    logger.info("✅ MCP Integration loaded")
except ImportError as e:
    MCP_AVAILABLE = False
    logger.warning(f"⚠️ MCP Integration not available: {e}")

# Import Configuration (NEW)
from config import settings, get_cors_origins

# Import Exception Handlers (NEW)
from exceptions import register_exception_handlers

# Import Middlewares (NEW)
from middleware import (
    RequestValidationMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    LoggingMiddleware,
    WebhookAuthMiddleware
)

# Constants (ใช้จาก settings แทน)
MAX_FILE_SIZE = settings.max_file_size
START_TIME = time.time()

# Lifespan context manager (replaces deprecated @app.on_event)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("🚀 Starting Document AI - OCR API...")
    logger.info("📖 API Docs: http://localhost:8000/docs")
    logger.info("⏳ OCR model will lazy-load on first request (faster cold start)")
    
    yield  # App runs here
    
    # Shutdown — clean up browser pool
    logger.info("👋 Shutting down Document AI - OCR API...")
    try:
        from cover_sheet_playwright import _shutdown_browser
        import asyncio
        await _shutdown_browser()
    except Exception as e:
        logger.warning(f"Browser pool shutdown error: {e}")

# สร้าง FastAPI app with lifespan
app = FastAPI(
    title="Document AI - OCR API",
    description="API สำหรับ OCR เอกสารคำร้อง มก. - Enterprise Edition with Prometheus Metrics",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan  # ✅ wire startup/shutdown events
)

# Prometheus Metrics Instrumentation
if PROMETHEUS_AVAILABLE:
    # Custom metrics
    OCR_REQUESTS = Counter(
        'ocr_requests_total',
        'Total OCR requests',
        ['form_type', 'status']
    )
    OCR_PROCESSING_TIME = Histogram(
        'ocr_processing_seconds',
        'OCR processing time in seconds',
        buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
    )
    
    # Auto-instrument the app
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/metrics"],
    )
    instrumentator.instrument(app).expose(app)
    logger.info("📊 Prometheus metrics enabled at /metrics")


app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Security & Validation Middlewares (NEW)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(WebhookAuthMiddleware)  # Optional HMAC auth
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestValidationMiddleware)

# Add Request ID Middleware
app.add_middleware(RequestIDMiddleware)

# Register Exception Handlers (NEW)
register_exception_handlers(app)



# ===== Data Models =====

class StudentInfo(BaseModel):
    """ข้อมูลนิสิต"""
    name: Optional[str] = None
    student_id: Optional[str] = None
    faculty: Optional[str] = None
    major: Optional[str] = None
    major_code: Optional[str] = None
    year: Optional[int] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class CourseInfo(BaseModel):
    """ข้อมูลรายวิชา"""
    course_code: Optional[str] = None
    course_name: Optional[str] = None
    credits: Optional[int] = None
    section: Optional[str] = None
    instructor: Optional[str] = None


class Form18Response(BaseModel):
    """Response สำหรับแบบ 18 - ขอคืนเงิน"""
    form_type: str = "18"
    form_name: str = "ขอคืนเงินค่าธรรมเนียมการศึกษา"
    student: StudentInfo
    advisor_name: Optional[str] = None
    semester: Optional[str] = None
    academic_year: Optional[str] = None
    refund_reason: Optional[str] = None
    refund_amount: Optional[float] = None
    bank_name: Optional[str] = None
    bank_account: Optional[str] = None
    has_signature: bool = False
    submit_date: Optional[str] = None
    confidence_score: float = 0.0


class Form20Response(BaseModel):
    """Response สำหรับแบบ 20 - ลงทะเบียนเพิ่ม"""
    form_type: str = "20"
    form_name: str = "คำร้องขอลงทะเบียนเรียนเพิ่ม"
    student: StudentInfo
    courses: List[CourseInfo] = []
    reason: Optional[str] = None
    has_signature: bool = False
    submit_date: Optional[str] = None
    confidence_score: float = 0.0


class Form4Response(BaseModel):
    """Response สำหรับแบบ 4 - เรียนควบ"""
    form_type: str = "4"
    form_name: str = "คำร้องขอลงทะเบียนเรียนควบ"
    student: StudentInfo
    prerequisite_course: Optional[CourseInfo] = None
    continuing_course: Optional[CourseInfo] = None
    reason: Optional[str] = None
    has_signature: bool = False
    submit_date: Optional[str] = None
    confidence_score: float = 0.0


class ReviewAnalysis(BaseModel):
    """ผลการวิเคราะห์ว่าต้อง manual review หรือไม่"""
    needs_review: bool = False
    review_reasons: List[str] = []
    confidence_level: str = "high"  # high, medium, low
    auto_process_allowed: bool = True
    review_priority: str = "low"  # urgent, normal, low
    details: Optional[dict] = None


class OCRResponse(BaseModel):
    """Response หลักที่ส่งกลับ"""
    success: bool
    message: str
    detected_form_type: Optional[str] = None
    form_confidence: float = 0.0
    data: Optional[dict] = None
    raw_text: Optional[str] = None
    ocr_confidence: float = 0.0
    processing_time_ms: int = 0
    # NEW: Review Analysis
    review_analysis: Optional[ReviewAnalysis] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    message: str
    version: str
    ocr_ready: bool


# Power Automate File Content Model
class PowerAutomateFile(BaseModel):
    """Model สำหรับ Power Automate file content format"""
    content_type: str = Field(alias="$content-type", default="application/pdf")
    content: str = Field(alias="$content")  # base64 encoded
    
    class Config:
        populate_by_name = True


# ===== Helper Functions =====

def merge_gemini_structured_fields(raw_text: str, extracted: dict) -> dict:
    """Parse Gemini structured JSON from raw_text and merge into extracted dict.
    Gemini fields take priority over regex-extracted fields."""
    try:
        # Find first { in raw_text and extract complete JSON by brace matching
        start_idx = raw_text.find('{')
        if start_idx < 0:
            return extracted
        depth = 0
        end_idx = start_idx
        for i in range(start_idx, len(raw_text)):
            if raw_text[i] == '{':
                depth += 1
            elif raw_text[i] == '}':
                depth -= 1
            if depth == 0:
                end_idx = i + 1
                break
        if depth != 0:
            return extracted
        gemini_data = json.loads(raw_text[start_idx:end_idx])
        student_info = gemini_data.get("student_info", {})
        gemini_field_map = {
            "advisor_name": "advisor_name",
            "full_name": "name",
            "student_id": "student_id",
            "faculty": "faculty",
            "department": "department",
            "year": "year_of_study",
            "phone": "phone",
            "email": "email",
        }
        for gemini_key, extracted_key in gemini_field_map.items():
            field = student_info.get(gemini_key, {})
            val = field.get("value") if isinstance(field, dict) else field
            if val is not None and str(val).strip():
                extracted[extracted_key] = str(val).strip() if not isinstance(val, (int, float)) else val
        logger.info(f"Gemini structured fields merged: {[k for k in gemini_field_map.values() if k in extracted and extracted[k]]}")
    except Exception as e:
        logger.warning(f"Gemini JSON parsing failed (non-critical): {e}")
    return extracted


def build_form18_response(extracted: dict, ocr_confidence: float) -> Form18Response:
    """สร้าง response สำหรับ แบบ 18"""
    return Form18Response(
        student=StudentInfo(
            name=extracted.get("name"),
            student_id=extracted.get("student_id"),
            faculty=extracted.get("faculty"),
            major=extracted.get("major"),
            major_code=extracted.get("major_code"),
            year=extracted.get("year"),
            phone=extracted.get("phone"),
            email=extracted.get("email"),
        ),
        advisor_name=extracted.get("advisor_name"),
        semester=extracted.get("semester"),
        academic_year=extracted.get("academic_year"),
        refund_reason=extracted.get("reason"),
        refund_amount=extracted.get("refund_amount"),
        bank_name=extracted.get("bank_name"),
        bank_account=extracted.get("bank_account"),
        has_signature=extracted.get("has_signature", False),  # From signature detection
        submit_date=datetime.now().strftime("%Y-%m-%d"),
        confidence_score=ocr_confidence
    )


def build_form20_response(extracted: dict, ocr_confidence: float) -> Form20Response:
    """สร้าง response สำหรับ แบบ 20"""
    courses = []
    for c in extracted.get("courses", []):
        courses.append(CourseInfo(
            course_code=c.get("course_code"),
            course_name=c.get("course_name"),
            credits=c.get("credits"),
            section=c.get("section"),
            instructor=c.get("instructor")
        ))
    
    return Form20Response(
        student=StudentInfo(
            name=extracted.get("name"),
            student_id=extracted.get("student_id"),
            faculty=extracted.get("faculty"),
            major=extracted.get("major"),
            major_code=extracted.get("major_code"),
            year=extracted.get("year"),
            phone=extracted.get("phone"),
            email=extracted.get("email"),
        ),
        courses=courses,
        reason=extracted.get("reason"),
        has_signature=extracted.get("has_signature", False),  # From signature detection
        submit_date=datetime.now().strftime("%Y-%m-%d"),
        confidence_score=ocr_confidence
    )


def build_form4_response(extracted: dict, ocr_confidence: float) -> Form4Response:
    """สร้าง response สำหรับ แบบ 4"""
    prereq = extracted.get("prerequisite_course")
    cont = extracted.get("continuing_course")
    
    return Form4Response(
        student=StudentInfo(
            name=extracted.get("name"),
            student_id=extracted.get("student_id"),
            faculty=extracted.get("faculty"),
            major=extracted.get("major"),
            major_code=extracted.get("major_code"),
            year=extracted.get("year"),
            phone=extracted.get("phone"),
            email=extracted.get("email"),
        ),
        prerequisite_course=CourseInfo(**prereq) if prereq else None,
        continuing_course=CourseInfo(**cont) if cont else None,
        reason=extracted.get("reason"),
        has_signature=extracted.get("has_signature", False),  # From signature detection
        submit_date=datetime.now().strftime("%Y-%m-%d"),
        confidence_score=ocr_confidence
    )

# ===== API Endpoints =====

@app.get("/", include_in_schema=False)
async def root():
    """Landing page - redirects to /docs in HF Space iframe"""
    from fastapi.responses import HTMLResponse
    try:
        ocr = get_ocr_service()
        ocr_status = "✅ Ready"
        status_color = "#22c55e"
    except Exception:
        ocr_status = "⚠️ Not Ready"
        status_color = "#f59e0b"

    html = f"""
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Document AI - OCR API</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4338ca 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
            }}
            .card {{
                background: rgba(255,255,255,0.1);
                backdrop-filter: blur(20px);
                border: 1px solid rgba(255,255,255,0.2);
                border-radius: 24px;
                padding: 48px;
                max-width: 520px;
                width: 90%;
                text-align: center;
                box-shadow: 0 25px 50px rgba(0,0,0,0.3);
            }}
            .icon {{ font-size: 64px; margin-bottom: 16px; }}
            h1 {{ font-size: 28px; font-weight: 700; margin-bottom: 8px; }}
            .subtitle {{ font-size: 14px; opacity: 0.7; margin-bottom: 32px; }}
            .status-badge {{
                display: inline-flex;
                align-items: center;
                gap: 8px;
                background: rgba(255,255,255,0.15);
                border-radius: 999px;
                padding: 8px 20px;
                font-size: 14px;
                margin-bottom: 32px;
            }}
            .dot {{ width: 8px; height: 8px; border-radius: 50%; background: {status_color}; }}
            .links {{ display: flex; flex-direction: column; gap: 12px; }}
            a {{
                display: block;
                padding: 14px 24px;
                border-radius: 12px;
                text-decoration: none;
                font-weight: 600;
                font-size: 15px;
                transition: all 0.2s;
            }}
            .btn-primary {{
                background: white;
                color: #4338ca;
            }}
            .btn-primary:hover {{ background: #e0e7ff; transform: translateY(-1px); }}
            .btn-secondary {{
                background: rgba(255,255,255,0.15);
                color: white;
                border: 1px solid rgba(255,255,255,0.3);
            }}
            .btn-secondary:hover {{ background: rgba(255,255,255,0.25); transform: translateY(-1px); }}
            .version {{ margin-top: 24px; font-size: 12px; opacity: 0.5; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="icon">📄</div>
            <h1>Document AI - OCR API</h1>
            <p class="subtitle">API สำหรับ OCR เอกสารคำร้อง มก. - Kasetsart University</p>
            <div class="status-badge">
                <div class="dot"></div>
                <span>OCR Engine: {ocr_status}</span>
            </div>
            <div class="links">
                <a href="/docs" class="btn-primary">📖 API Documentation (Swagger UI)</a>
                <a href="/redoc" class="btn-secondary">📋 API Reference (ReDoc)</a>
                <a href="/api/health" class="btn-secondary">💚 Health Check</a>
            </div>
            <p class="version">Enterprise Edition v{settings.app_version} · Gemini Vision OCR</p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.get("/health-json", response_model=HealthResponse)
async def root_health():
    """Health check endpoint (JSON) - ใช้สำหรับ Power Automate/monitoring"""
    try:
        ocr = get_ocr_service()
        ocr_ready = True
    except Exception:
        ocr_ready = False

    return HealthResponse(
        status="running",
        message="Document AI - OCR API",
        version=settings.app_version,
        ocr_ready=ocr_ready
    )


@app.post("/api/ocr", response_model=OCRResponse)
async def process_document(
    file: UploadFile = File(...),
    ocr_engine: str = Form("gemini"),
    preprocessing: str = Form("none"),
    postprocess: bool = Form(True)
):
    """
    รับไฟล์เอกสาร (PDF/Image) แล้วส่ง JSON กลับ
    
    Power Automate เรียก endpoint นี้
    
    Args:
        file: ไฟล์ PDF/Image
        ocr_engine: OCR engine (gemini = default, ตัวอื่นถูกลบแล้ว)
        preprocessing: โหมด preprocessing สำหรับลายมือ
            - "none": ไม่ใช้ (เร็ว)
            - "standard": มาตรฐาน
            - "handwriting": สำหรับลายมือ (แนะนำ)
            - "auto": ตรวจจับอัตโนมัติ
        postprocess: เปิด/ปิด postprocessor (default: True)
    
    1. รับไฟล์ PDF/Image
    2. OCR อ่านข้อความ (Gemini Vision)
    3. จำแนกประเภทเอกสาร
    4. Extract fields ตามประเภท
    5. ส่ง JSON กลับ
    """
    start_time = time.time()
    
    try:
        # อ่านไฟล์
        contents = await file.read()
        content_type = file.content_type
        
        # Fallback: ถ้า content_type เป็น None ให้ใช้ filename extension
        if content_type is None or content_type == "application/octet-stream":
            filename = file.filename.lower() if file.filename else ""
            if filename.endswith(".pdf"):
                content_type = "application/pdf"
            elif filename.endswith(".jpg") or filename.endswith(".jpeg"):
                content_type = "image/jpeg"
            elif filename.endswith(".png"):
                content_type = "image/png"
            else:
                content_type = None  # Will fail validation below
        
        # ตรวจสอบประเภทไฟล์
        allowed_types = ["image/jpeg", "image/png", "image/jpg", "application/pdf"]
        if content_type not in allowed_types:
            logger.warning(f"Unsupported file type: {content_type}")
            raise HTTPException(
                status_code=400, 
                detail=f"รองรับเฉพาะ PDF, JPEG, PNG (ได้รับ: {content_type})"
            )
        
        # ตรวจสอบขนาดไฟล์
        if len(contents) > MAX_FILE_SIZE:
            logger.warning(f"File too large: {len(contents)} bytes")
            raise HTTPException(
                status_code=413,
                detail=f"ไฟล์ใหญ่เกิน 10MB (ได้รับ: {len(contents) / 1024 / 1024:.1f}MB)"
            )
        
        # 1. OCR อ่านข้อความ (Gemini Vision - primary engine)
        engine_used = "Gemini Vision"
        preprocessing_used = preprocessing
        extracted_fields = {}
        
        logger.info(f"Processing with Gemini Vision, preprocessing: {preprocessing}")
        
        # Use Gemini Vision OCR (primary and only engine)
        ocr_service = get_ocr_service()
        raw_text, details, ocr_confidence = ocr_service.ocr_document(contents, content_type)
        
        # Try to detect engine name from service
        if hasattr(ocr_service, 'engine_name'):
            engine_used = ocr_service.engine_name
        elif hasattr(ocr_service, 'model_name'):
            engine_used = f"Gemini ({ocr_service.model_name})"
        
        logger.info(f"OCR Engine: {engine_used}")
        
        # Guard: ถ้า raw_text เป็น None ให้ใช้ empty string
        if raw_text is None:
            raw_text = ""
        
        if not raw_text.strip():
            return OCRResponse(
                success=False,
                message="ไม่สามารถอ่านข้อความจากเอกสารได้",
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
        
        # 2. จำแนกประเภทเอกสาร
        classifier = get_classifier()
        form_type, form_confidence = classifier.classify(raw_text)
        
        if form_type == "unknown":
            return OCRResponse(
                success=False,
                message="ไม่สามารถระบุประเภทเอกสารได้",
                raw_text=raw_text,
                ocr_confidence=ocr_confidence,
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
        
        # 3. Extract ข้อมูลตามประเภทฟอร์ม
        extractor = get_extractor(form_type)
        extracted = extractor.extract(raw_text)

        # 3.1 Merge Gemini structured fields (priority over regex)
        extracted = merge_gemini_structured_fields(raw_text, extracted)
        
        # 3.5 Detect signature
        try:
            sig_detector = get_signature_detector()
            sig_result = sig_detector.detect(contents)
            extracted["has_signature"] = sig_result.get("has_signature", False)
        except Exception as e:
            logger.warning(f"Signature detection failed: {e}")
            extracted["has_signature"] = False
        
        # 4. วิเคราะห์ว่าต้อง manual review หรือไม่
        review_analyzer = get_review_analyzer()
        review_result = review_analyzer.analyze(
            ocr_confidence=ocr_confidence,
            classification_result=(form_type, form_confidence),
            extracted_data=extracted
        )
        
        # 5. สร้าง response ตามประเภท
        if form_type == "18":
            data = build_form18_response(extracted, ocr_confidence)
        elif form_type == "20":
            data = build_form20_response(extracted, ocr_confidence)
        elif form_type == "4":
            data = build_form4_response(extracted, ocr_confidence)
        else:
            data = None
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # สร้าง ReviewAnalysis object
        review_analysis = ReviewAnalysis(
            needs_review=review_result["needs_review"],
            review_reasons=review_result["review_reasons"],
            confidence_level=review_result["confidence_level"],
            auto_process_allowed=review_result["auto_process_allowed"],
            review_priority=review_result["review_priority"],
            details=review_result["details"]
        )
        
        # กำหนด message ตามผลการวิเคราะห์
        if review_result["needs_review"]:
            message = f"ประมวลผลสำเร็จ - ⚠️ ต้องตรวจสอบ ({review_result['review_priority']})"
        else:
            message = "ประมวลผลสำเร็จ - ✅ ดำเนินการอัตโนมัติได้"
        
        return OCRResponse(
            success=True,
            message=message,
            detected_form_type=form_type,
            form_confidence=form_confidence,
            data=data.dict() if data else None,
            raw_text=raw_text,
            ocr_confidence=ocr_confidence,
            processing_time_ms=processing_time,
            review_analysis=review_analysis
        )
        
    except HTTPException:
        raise
    except Exception as e:
        return OCRResponse(
            success=False,
            message=f"เกิดข้อผิดพลาด: {str(e)}",
            processing_time_ms=int((time.time() - start_time) * 1000)
        )


# NEW: Endpoint specifically for Power Automate JSON format
@app.post("/api/ocr/powerautomate", response_model=OCRResponse)
async def process_document_powerautomate(request: Request):
    """
    Endpoint สำหรับ Power Automate โดยเฉพาะ
    รับ JSON body ในรูปแบบ:
    {
        "$content-type": "application/pdf",
        "$content": "base64..."
    }
    """
    import base64
    import json
    
    start_time = time.time()
    
    try:
        # Read and parse JSON body manually
        raw_body = await request.body()
        logger.info(f"📥 Power Automate raw body: {len(raw_body)} bytes")
        
        if len(raw_body) == 0:
            raise HTTPException(status_code=400, detail="Empty request body")
        
        # Parse JSON
        body_json = json.loads(raw_body.decode('utf-8'))
        logger.info(f"📦 Parsed JSON keys: {list(body_json.keys())}")
        
        # Get content from Power Automate format
        base64_content = body_json.get('$content', '')
        content_type = body_json.get('$content-type', 'application/pdf')
        
        if not base64_content:
            raise HTTPException(status_code=400, detail="Missing $content field")
        
        # Decode base64 content
        contents = base64.b64decode(base64_content)
        
        logger.info(f"✅ Decoded: {len(contents)} bytes, type: {content_type}")
        
        # ตรวจสอบขนาดไฟล์
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"ไฟล์ใหญ่เกิน 10MB (ได้รับ: {len(contents) / 1024 / 1024:.1f}MB)"
            )
        
        if len(contents) == 0:
            raise HTTPException(
                status_code=400,
                detail="ไม่ได้รับข้อมูลไฟล์"
            )
        
        # 1. OCR อ่านข้อความ
        ocr_service = get_ocr_service()
        raw_text, details, ocr_confidence = ocr_service.ocr_document(contents, content_type)
        
        if not raw_text.strip():
            return OCRResponse(
                success=False,
                message="ไม่สามารถอ่านข้อความจากเอกสารได้",
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
        
        # 2. จำแนกประเภทเอกสาร
        classifier = get_classifier()
        form_type, form_confidence = classifier.classify(raw_text)
        
        if form_type == "unknown":
            return OCRResponse(
                success=False,
                message="ไม่สามารถระบุประเภทเอกสารได้",
                raw_text=raw_text,
                ocr_confidence=ocr_confidence,
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
        
        # 3. Extract ข้อมูลตามประเภทฟอร์ม
        extractor = get_extractor(form_type)
        extracted = extractor.extract(raw_text)

        # 3.1 Merge Gemini structured fields (priority over regex)
        extracted = merge_gemini_structured_fields(raw_text, extracted)

        # 4. วิเคราะห์ว่าต้อง manual review หรือไม่
        review_analyzer = get_review_analyzer()
        review_result = review_analyzer.analyze(
            ocr_confidence=ocr_confidence,
            classification_result=(form_type, form_confidence),
            extracted_data=extracted
        )
        
        # 5. สร้าง response ตามประเภท
        if form_type == "18":
            data = build_form18_response(extracted, ocr_confidence)
        elif form_type == "20":
            data = build_form20_response(extracted, ocr_confidence)
        elif form_type == "4":
            data = build_form4_response(extracted, ocr_confidence)
        else:
            data = None
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # สร้าง ReviewAnalysis object
        review_analysis = ReviewAnalysis(
            needs_review=review_result["needs_review"],
            review_reasons=review_result["review_reasons"],
            confidence_level=review_result["confidence_level"],
            auto_process_allowed=review_result["auto_process_allowed"],
            review_priority=review_result["review_priority"],
            details=review_result["details"]
        )
        
        logger.info(f"✅ Power Automate OCR success: form_type={form_type}")
        
        return OCRResponse(
            success=True,
            message=f"ประมวลผลสำเร็จ - Form {form_type}",
            detected_form_type=form_type,
            form_confidence=form_confidence,
            data=data.dict() if data else None,
            raw_text=raw_text,
            ocr_confidence=ocr_confidence,
            processing_time_ms=processing_time,
            review_analysis=review_analysis
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Power Automate OCR error: {str(e)}")
        return OCRResponse(
            success=False,
            message=f"เกิดข้อผิดพลาด: {str(e)}",
            processing_time_ms=int((time.time() - start_time) * 1000)
        )


# NEW: Endpoint for Power Automate (accepts Power Automate file format)
@app.post("/api/ocr/binary", response_model=OCRResponse)
async def process_document_binary(request: Request):
    """
    Endpoint สำหรับ Power Automate ที่ส่ง file content
    รองรับทั้ง:
    1. Power Automate format: {"$content-type": "...", "$content": "base64..."}
    2. Raw binary
    """
    import json
    import base64
    
    start_time = time.time()
    
    try:
        # Read raw body
        raw_body = await request.body()
        content_type = request.headers.get("content-type", "application/pdf")
        
        # Clean content-type
        if ";" in content_type:
            content_type = content_type.split(";")[0].strip()
        
        logger.info(f"📥 Received request: {len(raw_body)} bytes, content-type: {content_type}")
        
        # Default: use raw body
        contents = raw_body
        
        # Try to parse as JSON (Power Automate format)
        if content_type == "application/json" or (raw_body and raw_body.startswith(b'{')):
            try:
                body_json = json.loads(raw_body.decode('utf-8'))
                logger.info(f"📦 Parsed JSON body, keys: {list(body_json.keys())}")
                
                if '$content' in body_json:
                    # Power Automate format
                    base64_content = body_json.get('$content', '')
                    contents = base64.b64decode(base64_content)
                    content_type = body_json.get('$content-type', 'application/pdf')
                    logger.info(f"✅ Decoded Power Automate: {len(contents)} bytes, type: {content_type}")
            except Exception as e:
                logger.warning(f"JSON parse failed, using raw body: {e}")
                contents = raw_body
                if contents.startswith(b'%PDF'):
                    content_type = "application/pdf"
                    logger.info("Detected PDF magic bytes, overriding content-type to application/pdf")
        
        # If content-type is application/pdf but body is empty, check headers
        if len(contents) == 0 and len(raw_body) > 0:
            # Maybe the raw body IS the PDF
            contents = raw_body
            if contents.startswith(b'%PDF'):
                content_type = "application/pdf"
            logger.info(f"Using raw body as content: {len(contents)} bytes")
        # ตรวจสอบขนาดไฟล์
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"ไฟล์ใหญ่เกิน 10MB (ได้รับ: {len(contents) / 1024 / 1024:.1f}MB)"
            )
        
        if len(contents) == 0:
            raise HTTPException(
                status_code=400,
                detail="ไม่ได้รับข้อมูลไฟล์"
            )
        
        # 1. OCR อ่านข้อความ
        ocr_service = get_ocr_service()
        raw_text, details, ocr_confidence = ocr_service.ocr_document(contents, content_type)
        
        if not raw_text.strip():
            return OCRResponse(
                success=False,
                message="ไม่สามารถอ่านข้อความจากเอกสารได้",
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
        
        # 2. จำแนกประเภทเอกสาร
        classifier = get_classifier()
        form_type, form_confidence = classifier.classify(raw_text)
        
        if form_type == "unknown":
            return OCRResponse(
                success=False,
                message="ไม่สามารถระบุประเภทเอกสารได้",
                raw_text=raw_text,
                ocr_confidence=ocr_confidence,
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
        
        # 3. Extract ข้อมูลตามประเภทฟอร์ม
        extractor = get_extractor(form_type)
        extracted = extractor.extract(raw_text)

        # 3.1 Merge Gemini structured fields (priority over regex)
        extracted = merge_gemini_structured_fields(raw_text, extracted)

        # 4. วิเคราะห์ว่าต้อง manual review หรือไม่
        review_analyzer = get_review_analyzer()
        review_result = review_analyzer.analyze(
            ocr_confidence=ocr_confidence,
            classification_result=(form_type, form_confidence),
            extracted_data=extracted
        )

        # 5. สร้าง response ตามประเภท
        if form_type == "18":
            data = build_form18_response(extracted, ocr_confidence)
        elif form_type == "20":
            data = build_form20_response(extracted, ocr_confidence)
        elif form_type == "4":
            data = build_form4_response(extracted, ocr_confidence)
        else:
            data = None

        processing_time = int((time.time() - start_time) * 1000)

        # สร้าง ReviewAnalysis object
        review_analysis = ReviewAnalysis(
            needs_review=review_result["needs_review"],
            review_reasons=review_result["review_reasons"],
            confidence_level=review_result["confidence_level"],
            auto_process_allowed=review_result["auto_process_allowed"],
            review_priority=review_result["review_priority"],
            details=review_result["details"]
        )

        logger.info(f"✅ Binary OCR success: form_type={form_type}, confidence={form_confidence:.2f}")
        
        return OCRResponse(
            success=True,
            message=f"ประมวลผลสำเร็จ (Binary) - Form {form_type}",
            detected_form_type=form_type,
            form_confidence=form_confidence,
            data=data.dict() if data else None,
            raw_text=raw_text,
            ocr_confidence=ocr_confidence,
            processing_time_ms=processing_time,
            review_analysis=review_analysis
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Binary OCR error: {str(e)}")
        return OCRResponse(
            success=False,
            message=f"เกิดข้อผิดพลาด: {str(e)}",
            processing_time_ms=int((time.time() - start_time) * 1000)
        )


@app.post("/api/ocr/form18", response_model=OCRResponse)
async def process_form18(file: UploadFile = File(...)):
    """
    Endpoint เฉพาะสำหรับแบบ 18 - ขอคืนเงิน
    (ไม่ต้องจำแนกประเภท ใช้ extractor โดยตรง)
    """
    start_time = time.time()
    
    try:
        contents = await file.read()
        content_type = file.content_type
        
        ocr_service = get_ocr_service()
        raw_text, details, ocr_confidence = ocr_service.ocr_document(contents, content_type)
        
        extractor = get_extractor("18")
        extracted = extractor.extract(raw_text)
        extracted = merge_gemini_structured_fields(raw_text, extracted)
        data = build_form18_response(extracted, ocr_confidence)
        
        return OCRResponse(
            success=True,
            message="ประมวลผลแบบ 18 สำเร็จ",
            detected_form_type="18",
            form_confidence=1.0,
            data=data.dict(),
            raw_text=raw_text,
            ocr_confidence=ocr_confidence,
            processing_time_ms=int((time.time() - start_time) * 1000)
        )
    except Exception as e:
        return OCRResponse(
            success=False,
            message=f"เกิดข้อผิดพลาด: {str(e)}",
            processing_time_ms=int((time.time() - start_time) * 1000)
        )


@app.post("/api/ocr/form20", response_model=OCRResponse)
async def process_form20(file: UploadFile = File(...)):
    """
    Endpoint เฉพาะสำหรับแบบ 20 - ลงทะเบียนเพิ่ม
    """
    start_time = time.time()
    
    try:
        contents = await file.read()
        content_type = file.content_type
        
        ocr_service = get_ocr_service()
        raw_text, details, ocr_confidence = ocr_service.ocr_document(contents, content_type)
        
        extractor = get_extractor("20")
        extracted = extractor.extract(raw_text)
        extracted = merge_gemini_structured_fields(raw_text, extracted)
        data = build_form20_response(extracted, ocr_confidence)
        
        return OCRResponse(
            success=True,
            message="ประมวลผลแบบ 20 สำเร็จ",
            detected_form_type="20",
            form_confidence=1.0,
            data=data.dict(),
            raw_text=raw_text,
            ocr_confidence=ocr_confidence,
            processing_time_ms=int((time.time() - start_time) * 1000)
        )
    except Exception as e:
        return OCRResponse(
            success=False,
            message=f"เกิดข้อผิดพลาด: {str(e)}",
            processing_time_ms=int((time.time() - start_time) * 1000)
        )


@app.post("/api/ocr/form4", response_model=OCRResponse)
async def process_form4(file: UploadFile = File(...)):
    """
    Endpoint เฉพาะสำหรับแบบ 4 - เรียนควบ
    """
    start_time = time.time()
    
    try:
        contents = await file.read()
        content_type = file.content_type
        
        ocr_service = get_ocr_service()
        raw_text, details, ocr_confidence = ocr_service.ocr_document(contents, content_type)
        
        extractor = get_extractor("4")
        extracted = extractor.extract(raw_text)
        extracted = merge_gemini_structured_fields(raw_text, extracted)
        data = build_form4_response(extracted, ocr_confidence)
        
        return OCRResponse(
            success=True,
            message="ประมวลผลแบบ 4 สำเร็จ",
            detected_form_type="4",
            form_confidence=1.0,
            data=data.dict(),
            raw_text=raw_text,
            ocr_confidence=ocr_confidence,
            processing_time_ms=int((time.time() - start_time) * 1000)
        )
    except Exception as e:
        return OCRResponse(
            success=False,
            message=f"เกิดข้อผิดพลาด: {str(e)}",
            processing_time_ms=int((time.time() - start_time) * 1000)
        )


@app.post("/api/ocr/raw")
async def get_raw_text(file: UploadFile = File(...)):
    """
    Endpoint สำหรับดึงข้อความดิบจาก OCR (สำหรับ debug)
    """
    start_time = time.time()
    
    try:
        contents = await file.read()
        content_type = file.content_type
        
        ocr_service = get_ocr_service()
        raw_text, details, ocr_confidence = ocr_service.ocr_document(contents, content_type)
        
        return {
            "success": True,
            "raw_text": raw_text,
            "details": details,
            "ocr_confidence": ocr_confidence,
            "processing_time_ms": int((time.time() - start_time) * 1000)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "processing_time_ms": int((time.time() - start_time) * 1000)
        }


# ===== Advanced Endpoints (v3.0) =====

@app.get("/api/health")
async def health_extended():
    """
    Extended health check with system stats
    """
    import psutil
    
    try:
        ocr = get_ocr_service()
        ocr_ready = True
    except Exception:
        ocr_ready = False
    
    cache = get_ocr_cache()
    
    return {
        "status": "running",
        "version": settings.app_version,
        "uptime_seconds": int(time.time() - START_TIME),
        "ocr_ready": ocr_ready,
        "cache": cache.stats(),
        "system": {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent
        }
    }


@app.get("/api/cache/stats")
async def cache_stats():
    """Get OCR cache statistics"""
    cache = get_ocr_cache()
    return {
        "success": True,
        "stats": cache.stats()
    }


@app.delete("/api/cache/clear")
async def cache_clear():
    """Clear OCR cache"""
    cache = get_ocr_cache()
    cache.clear()
    return {
        "success": True,
        "message": "Cache cleared"
    }


@app.post("/api/ocr/with-signature")
async def process_with_signature(file: UploadFile = File(...)):
    """
    Process document with signature detection
    Returns OCR results + signature analysis
    """
    start_time = time.time()
    
    try:
        contents = await file.read()
        content_type = file.content_type
        
        # Check file size
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="ไฟล์ใหญ่เกิน 10MB")
        
        # OCR
        ocr_service = get_ocr_service()
        raw_text, details, ocr_confidence = ocr_service.ocr_document(contents, content_type)
        
        # Signature Detection
        sig_detector = get_signature_detector()
        signature_result = sig_detector.detect(contents)
        
        # Classify
        classifier = get_classifier()
        form_type, form_confidence = classifier.classify(raw_text)
        
        # Extract with auto-correction
        extractor = get_extractor(form_type)
        extracted = extractor.extract(raw_text) if extractor else {}
        extracted = merge_gemini_structured_fields(raw_text, extracted)

        # Apply auto-correction
        auto_corrector = get_auto_corrector()
        corrected_data = auto_corrector.correct_extracted_data(extracted)
        
        return {
            "success": True,
            "message": "ประมวลผลสำเร็จพร้อมตรวจลายเซ็น",
            "detected_form_type": form_type,
            "form_confidence": form_confidence,
            "data": corrected_data,
            "signature_analysis": signature_result,
            "ocr_confidence": ocr_confidence,
            "processing_time_ms": int((time.time() - start_time) * 1000)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in signature processing")
        return {
            "success": False,
            "message": f"เกิดข้อผิดพลาด: {str(e)}",
            "processing_time_ms": int((time.time() - start_time) * 1000)
        }


@app.post("/api/ocr/batch")
async def batch_process(files: List[UploadFile] = File(...)):
    """
    Process multiple files at once
    Returns job ID for tracking progress
    """
    # Validate
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="สูงสุด 10 ไฟล์ต่อครั้ง")
    
    batch_manager = get_batch_manager()
    job = batch_manager.create_job(total_files=len(files))
    job.status = "processing"
    
    results = []
    errors = []
    
    for i, file in enumerate(files):
        try:
            contents = await file.read()
            content_type = file.content_type
            
            # Check cache first
            cache = get_ocr_cache()
            cached = cache.get(contents)
            
            if cached:
                results.append({
                    "filename": file.filename,
                    "cached": True,
                    "result": cached
                })
                batch_manager.add_result(job.job_id, cached)
                continue
            
            # OCR
            ocr_service = get_ocr_service()
            raw_text, details, ocr_confidence = ocr_service.ocr_document(contents, content_type)
            
            # Classify
            classifier = get_classifier()
            form_type, form_confidence = classifier.classify(raw_text)
            
            # Extract
            extractor = get_extractor(form_type)
            extracted = extractor.extract(raw_text) if extractor else {}
            extracted = merge_gemini_structured_fields(raw_text, extracted)

            # Auto-correct
            auto_corrector = get_auto_corrector()
            corrected = auto_corrector.correct_extracted_data(extracted)
            
            result = {
                "form_type": form_type,
                "form_confidence": form_confidence,
                "data": corrected,
                "ocr_confidence": ocr_confidence
            }
            
            # Cache result
            cache.set(contents, result)
            
            results.append({
                "filename": file.filename,
                "cached": False,
                "result": result
            })
            batch_manager.add_result(job.job_id, result)
            
        except Exception as e:
            logger.error(f"Error processing {file.filename}: {e}")
            errors.append({
                "filename": file.filename,
                "error": str(e)
            })
            batch_manager.add_error(job.job_id, {"filename": file.filename, "error": str(e)})
    
    return {
        "success": True,
        "job_id": job.job_id,
        "total_files": len(files),
        "processed": len(results),
        "errors": len(errors),
        "results": results,
        "error_details": errors
    }


@app.get("/api/batch/{job_id}")
async def get_batch_status(job_id: str):
    """Get batch job status"""
    batch_manager = get_batch_manager()
    job = batch_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "job_id": job.job_id,
        "status": job.status,
        "total_files": job.total_files,
        "processed_files": job.processed_files,
        "progress_percent": int(job.processed_files / job.total_files * 100) if job.total_files > 0 else 0,
        "results": job.results,
        "errors": job.errors
    }


# ===== API v2 Router (Versioned API) =====

v2_router = APIRouter(prefix="/api/v2", tags=["v2 - Enhanced API"])


@v2_router.get("/info")
async def v2_info():
    """API v2 information and available endpoints"""
    return {
        "version": "2.0.0",
        "description": "Document AI API v2 - Enhanced with Prometheus metrics and versioning",
        "endpoints": [
            "GET /api/v2/info - This endpoint",
            "GET /api/v2/health - Enhanced health check",
            "POST /api/v2/ocr - OCR with metrics tracking",
        ],
        "features": [
            "Prometheus metrics at /metrics",
            "Custom OCR counters and histograms",
            "Request ID tracking",
            "Cache statistics",
        ]
    }


@v2_router.get("/health")
async def v2_health():
    """Enhanced health check with full system status"""
    import psutil
    
    try:
        ocr = get_ocr_service()
        ocr_ready = True
    except Exception:
        ocr_ready = False
    
    cache = get_ocr_cache()
    
    return {
        "api_version": "2.0.0",
        "status": "healthy" if ocr_ready else "degraded",
        "uptime_seconds": int(time.time() - START_TIME),
        "ocr": {
            "ready": ocr_ready,
            "engine": "Gemini Vision",
            "languages": ["th", "en"]
        },
        "cache": cache.stats(),
        "system": {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_available_mb": psutil.virtual_memory().available / 1024 / 1024
        },
        "prometheus_enabled": PROMETHEUS_AVAILABLE
    }


@v2_router.post("/ocr")
async def v2_process_document(file: UploadFile = File(...)):
    """
    OCR v2 - With Prometheus metrics tracking
    """
    start_time = time.time()
    form_type = "unknown"
    
    try:
        contents = await file.read()
        content_type = file.content_type
        
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="ไฟล์ใหญ่เกิน 10MB")
        
        ocr_service = get_ocr_service()
        raw_text, details, ocr_confidence = ocr_service.ocr_document(contents, content_type)
        
        classifier = get_classifier()
        form_type, form_confidence = classifier.classify(raw_text)
        
        extractor = get_extractor(form_type)
        extracted = extractor.extract(raw_text) if extractor else {}
        extracted = merge_gemini_structured_fields(raw_text, extracted)

        review_analyzer = get_review_analyzer()
        review_result = review_analyzer.analyze(
            ocr_confidence=ocr_confidence,
            classification_result=(form_type, form_confidence),
            extracted_data=extracted
        )
        
        processing_time = time.time() - start_time
        
        if PROMETHEUS_AVAILABLE:
            OCR_REQUESTS.labels(form_type=form_type, status="success").inc()
            OCR_PROCESSING_TIME.observe(processing_time)
        
        return {
            "api_version": "2.0.0",
            "success": True,
            "detected_form_type": form_type,
            "form_confidence": form_confidence,
            "data": extracted,
            "ocr_confidence": ocr_confidence,
            "processing_time_seconds": round(processing_time, 3),
            "review_analysis": review_result,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        processing_time = time.time() - start_time
        if PROMETHEUS_AVAILABLE:
            OCR_REQUESTS.labels(form_type=form_type, status="error").inc()
        logger.exception("v2 OCR Error")
        return {
            "api_version": "2.0.0",
            "success": False,
            "message": f"เกิดข้อผิดพลาด: {str(e)}",
            "processing_time_seconds": round(processing_time, 3)
        }


# Include v2 router
app.include_router(v2_router)
logger.info("✅ API v2 endpoints loaded at /api/v2/*")


# ===== Database & LINE Endpoints (v4.1) =====

@app.get("/api/db/results")
async def get_db_results(limit: int = 50, offset: int = 0):
    """ดึงประวัติผล OCR จากฐานข้อมูล"""
    if not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    db = get_database()
    results = db.get_results(limit=limit, offset=offset)
    return {"success": True, "count": len(results), "results": results}


@app.get("/api/db/stats")
async def get_db_stats():
    """ดึงสถิติการประมวลผล"""
    if not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    db = get_database()
    stats = db.get_stats()
    return {"success": True, "stats": stats}


@app.get("/api/db/search")
async def search_results(q: str, limit: int = 20):
    """ค้นหาผลลัพธ์"""
    if not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    db = get_database()
    results = db.search(q, limit=limit)
    return {"success": True, "query": q, "count": len(results), "results": results}


@app.get("/api/status/full")
async def full_status():
    """แสดงสถานะทุกระบบ"""
    import psutil
    
    return {
        "api_version": settings.app_version,
        "uptime_seconds": int(time.time() - START_TIME),
        "modules": {
            "prometheus": PROMETHEUS_AVAILABLE,
            "database": DATABASE_AVAILABLE
        },
        "system": {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent
        }
    }


# ===== Cover Sheet & Final Document Endpoints =====

import json as json_module
from pydantic import validator

class ApprovalStep(BaseModel):
    """ข้อมูลการอนุมัติแต่ละขั้นตอน"""
    step: Optional[int] = None
    role: str
    status: str  # pending/approved/rejected
    approver_name: Optional[str] = None
    datetime: Optional[str] = None
    comment: Optional[str] = None


def _parse_approval_steps(v):
    """Parse approval_steps — รองรับทั้ง array และ JSON string จาก Power Automate"""
    if isinstance(v, str):
        try:
            parsed = json_module.loads(v)
            if isinstance(parsed, list):
                return [ApprovalStep(**item) if isinstance(item, dict) else item for item in parsed]
        except (json_module.JSONDecodeError, TypeError):
            pass
        raise ValueError("approval_steps string ไม่ใช่ JSON array ที่ถูกต้อง")
    return v


class CoverSheetRequest(BaseModel):
    """Request body สำหรับสร้าง Cover Sheet"""
    request_id: str
    form_type: str
    student_name: str
    student_id: str
    faculty: Optional[str] = "คณะวิทยาศาสตร์ ศรีราชา"
    approval_steps: List[ApprovalStep]
    submit_date: Optional[str] = None

    @validator("approval_steps", pre=True)
    def parse_approval_steps(cls, v):
        return _parse_approval_steps(v)


class FinalDocumentRequest(BaseModel):
    """Request body สำหรับสร้างเอกสารสุดท้าย"""
    request_id: str
    form_type: str
    student_name: str
    student_id: str
    faculty: Optional[str] = "คณะวิทยาศาสตร์ ศรีราชา"
    approval_steps: List[ApprovalStep]
    submit_date: Optional[str] = None
    original_pdf_base64: str  # Base64 encoded PDF

    @validator("approval_steps", pre=True)
    def parse_approval_steps(cls, v):
        return _parse_approval_steps(v)


@app.post("/api/cover-sheet/generate")
async def generate_cover_sheet(request: CoverSheetRequest):
    """
    สร้าง Cover Sheet PDF แสดงสถานะการอนุมัติ
    
    Returns: PDF as base64 string
    """
    import base64
    from cover_sheet_playwright import get_cover_sheet_generator
    
    try:
        generator = get_cover_sheet_generator()
        
        # Convert Pydantic models to dicts (model_dump = Pydantic v2)
        steps = [step.model_dump() for step in request.approval_steps]
        logger.info(f"📄 generate_cover_sheet: form_type={request.form_type!r}, approval_steps={len(steps)} items: {steps}")

        pdf_bytes = await generator.create_cover_sheet(
            request_id=request.request_id,
            form_type=request.form_type,
            student_name=request.student_name,
            student_id=request.student_id,
            faculty=request.faculty,
            approval_steps=steps,
            submit_date=request.submit_date,
        )
        
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
        
        return {
            "success": True,
            "message": "Cover Sheet สร้างสำเร็จ",
            "pdf_base64": pdf_base64,
            "size_bytes": len(pdf_bytes),
            "engine": "playwright"
        }
    except Exception as e:
        logger.exception("Error generating cover sheet")
        return {
            "success": False,
            "message": f"เกิดข้อผิดพลาด: {str(e)}"
        }


@app.post("/api/final-document/generate")
async def generate_final_document(request: FinalDocumentRequest):
    """
    สร้างเอกสารสุดท้าย (Cover Sheet + Original Document)
    
    Returns: Merged PDF as base64 string
    """
    import base64
    from cover_sheet_playwright import get_cover_sheet_generator
    
    try:
        generator = get_cover_sheet_generator()

        # Decode original PDF
        original_pdf = base64.b64decode(request.original_pdf_base64)

        # Convert Pydantic models to dicts (model_dump = Pydantic v2)
        steps = [step.model_dump() for step in request.approval_steps]
        logger.info(f"📄 generate_final_document: form_type={request.form_type!r}, approval_steps={len(steps)} items: {steps}")

        final_pdf = await generator.create_final_document(
            request_id=request.request_id,
            form_type=request.form_type,
            student_name=request.student_name,
            student_id=request.student_id,
            faculty=request.faculty,
            approval_steps=steps,
            original_pdf=original_pdf,
            submit_date=request.submit_date,
        )
        
        pdf_base64 = base64.b64encode(final_pdf).decode('utf-8')
        
        return {
            "success": True,
            "message": "Final Document สร้างสำเร็จ",
            "pdf_base64": pdf_base64,
            "size_bytes": len(final_pdf),
            "engine": "playwright"
        }
    except Exception as e:
        logger.exception("Error generating final document")
        return {
            "success": False,
            "message": f"เกิดข้อผิดพลาด: {str(e)}"
        }


# ===== Dashboard API (สำหรับ Dashboard + Power Automate Webhook) =====

class DashboardWebhookRequest(BaseModel):
    """ข้อมูลคำร้องจาก Power Automate"""
    request_id: Optional[str] = None
    form_type: str = "18"
    student_id: Optional[str] = None
    student_name: Optional[str] = None
    student_email: Optional[str] = None
    faculty: Optional[str] = None
    major: Optional[str] = None
    phone: Optional[str] = None
    advisor_name: Optional[str] = None
    advisor_email: Optional[str] = None
    current_step: int = 1
    overall_status: str = "pending"
    courses: Optional[List[str]] = []
    ocr_confidence: float = 0
    source: str = "microsoft-forms"
    submitted_date: Optional[str] = None

class DashboardStatusUpdate(BaseModel):
    """อัปเดตสถานะจาก Power Automate"""
    request_id: str
    overall_status: Optional[str] = None
    current_step: Optional[int] = None
    advisor_name: Optional[str] = None
    advisor_email: Optional[str] = None
    ocr_confidence: Optional[float] = None

@app.post("/api/dashboard/webhook")
async def dashboard_webhook(data: DashboardWebhookRequest):
    """
    Webhook สำหรับ Power Automate ส่งข้อมูลคำร้องเข้ามา
    
    Power Automate จะเรียก endpoint นี้ทุกครั้งที่มีคำร้องใหม่
    """
    if not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        db = get_database()
        request_id = db.save_request(data.dict())
        
        return {
            "success": True,
            "message": f"คำร้อง {request_id} ถูกบันทึกแล้ว",
            "request_id": request_id
        }
    except Exception as e:
        logger.exception("Error saving webhook data")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/dashboard/webhook/status")
async def dashboard_webhook_status(data: DashboardStatusUpdate):
    """
    Webhook สำหรับอัปเดตสถานะคำร้อง (อนุมัติ/ปฏิเสธ)
    
    Power Automate จะเรียกทุกครั้งที่สถานะเปลี่ยน
    """
    if not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        db = get_database()
        update_data = {k: v for k, v in data.dict().items() 
                       if v is not None and k != "request_id"}
        
        success = db.update_request_status(data.request_id, update_data)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"ไม่พบคำร้อง {data.request_id}")
        
        return {
            "success": True,
            "message": f"อัปเดตสถานะ {data.request_id} สำเร็จ",
            "request_id": data.request_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error updating webhook status")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard/requests")
async def get_dashboard_requests(
    limit: int = 50, 
    offset: int = 0, 
    status: Optional[str] = None,
    search: Optional[str] = None
):
    """ดึงรายการคำร้อง สำหรับ Dashboard table"""
    if not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        db = get_database()
        result = db.get_requests(
            limit=limit, offset=offset, 
            status=status, search=search
        )
        return {"success": True, **result}
    except Exception as e:
        logger.exception("Error getting dashboard requests")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard/stats")
async def get_dashboard_stats():
    """ดึงสถิติรวม สำหรับ Dashboard cards + chart"""
    if not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        db = get_database()
        stats = db.get_request_stats()
        return {"success": True, **stats}
    except Exception as e:
        logger.exception("Error getting dashboard stats")
        raise HTTPException(status_code=500, detail=str(e))


# ===== Run Server =====

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
