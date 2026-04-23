# Gemini Vision OCR Service
# ใช้ Google Gemini API สำหรับอ่านลายมือภาษาไทย (ฟรี!)

"""
Gemini Vision API - Thai Handwriting OCR

ข้อดี:
- ฟรี 15 requests/นาที
- ไม่ต้องผูกบัตร
- อ่านลายมือภาษาไทยได้ดีมาก
- รองรับ PDF และ Image

Updated: 2026-02-05 - New Document AI prompt (ADE-style)
"""

import os
import io
import base64
import hashlib
import time
import logging
import threading
from collections import OrderedDict
from typing import Tuple, List, Optional

logger = logging.getLogger(__name__)

# Check if new Google GenAI SDK is available
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
    logger.info("Gemini SDK (google-genai) loaded")
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("Gemini not installed. Run: pip install google-genai")


# API Key from environment variable (set as HF Space secret)
DEFAULT_API_KEY = os.environ.get('GEMINI_API_KEY', '')


# ===== OCR Result Cache (thread-safe, capped) =====
_ocr_cache: OrderedDict = OrderedDict()
_ocr_cache_lock = threading.Lock()
OCR_CACHE_MAX = 50  # Reduced from 100 to save RAM


def _get_file_hash(content: bytes) -> str:
    """Generate MD5 hash of file content for cache key"""
    return hashlib.md5(content).hexdigest()


def _ocr_cache_get(file_hash: str):
    """Get OCR result from cache"""
    with _ocr_cache_lock:
        if file_hash in _ocr_cache:
            _ocr_cache.move_to_end(file_hash)
            logging.getLogger(__name__).info(f"📦 OCR cache HIT: {file_hash[:8]}...")
            return _ocr_cache[file_hash]
    return None


def _ocr_cache_set(file_hash: str, result: tuple):
    """Store OCR result in cache with LRU eviction"""
    with _ocr_cache_lock:
        _ocr_cache[file_hash] = result
        _ocr_cache.move_to_end(file_hash)
        while len(_ocr_cache) > OCR_CACHE_MAX:
            _ocr_cache.popitem(last=False)


# ===== Document AI System Prompt (ADE-style with per-field confidence) =====
DOCUMENT_AI_PROMPT = """คุณเป็นระบบ Document AI ระดับ Enterprise เชี่ยวชาญในการวิเคราะห์เอกสารคำร้องนิสิตมหาวิทยาลัยเกษตรศาสตร์
ให้ทำงานเหมือน Azure Document Intelligence — ดึงข้อมูลพร้อม confidence score แต่ละฟิลด์

## ประเภทเอกสารที่รองรับ:
1. **แบบ 4** - ขอลงทะเบียนเรียนควบ (Concurrent Registration)
2. **แบบ 18** - ขอคืนเงินค่าธรรมเนียม (Fee Refund)
3. **แบบ 20** - ขอลงทะเบียนเรียนเพิ่ม (Add Registration)

## กฎการดึงข้อมูล:
1. **ทุกฟิลด์ต้องมี confidence** (0.0-1.0):
   - 0.95-1.0 = ข้อความพิมพ์ชัดเจน
   - 0.80-0.94 = ลายมืออ่านออกชัด
   - 0.50-0.79 = ลายมือไม่ชัด อ่านได้บางส่วน
   - 0.0-0.49 = อ่านไม่ออก ให้ใส่ null
2. **ระบุ input_type** ของแต่ละฟิลด์: "printed" หรือ "handwritten"
3. **Format validation**:
   - รหัสนิสิต: ตัวเลข 10 หลัก (ขึ้นต้นด้วย 6)
   - เบอร์โทร: ตัวเลข 10 หลัก (ขึ้นต้นด้วย 0)
   - อีเมล: ต้องมี @ (มักเป็น @ku.th)
   - จำนวนเงิน: ตัวเลขเท่านั้น (หน่วยบาท)
   - วันที่: รูปแบบ DD/MM/YYYY (ปี พ.ศ.)
4. **ลายมือไทย**: ระวังตัวเลขที่มักสับสน: 1↔7, 2↔5, 6↔0, 9↔4

## Output JSON Format:

```json
{
  "document_info": {
    "form_type": "4 | 18 | 20",
    "form_name": "ชื่อแบบฟอร์มภาษาไทย",
    "document_confidence": 0.95,
    "submit_date": {"value": "DD/MM/YYYY", "confidence": 0.9, "input_type": "handwritten"},
    "overall_quality": "good | fair | poor"
  },
  "student_info": {
    "student_id": {"value": "6XXXXXXXXX", "confidence": 0.95, "input_type": "handwritten"},
    "full_name": {"value": "ชื่อ-นามสกุล", "confidence": 0.9, "input_type": "handwritten"},
    "faculty": {"value": "คณะ", "confidence": 0.95, "input_type": "printed"},
    "department": {"value": "สาขา/ภาควิชา", "confidence": 0.9, "input_type": "handwritten"},
    "year": {"value": 1, "confidence": 0.8, "input_type": "handwritten"},
    "phone": {"value": "0XXXXXXXXX", "confidence": 0.85, "input_type": "handwritten"},
    "email": {"value": "xxx@ku.th", "confidence": 0.9, "input_type": "handwritten"},
    "advisor_name": {"value": "ชื่ออาจารย์ที่ปรึกษา", "confidence": 0.85, "input_type": "handwritten"}
  },
  "form_specific_data": {
    "สำหรับแบบ 4": {
      "continuing_course": {"value": "ชื่อวิชา", "confidence": 0.9, "input_type": "handwritten"},
      "course_code": {"value": "รหัสวิชา", "confidence": 0.95, "input_type": "handwritten"},
      "prerequisite_course": {"value": "ชื่อวิชาบังคับก่อน", "confidence": 0.9, "input_type": "handwritten"},
      "prerequisite_code": {"value": "รหัสวิชา", "confidence": 0.95, "input_type": "handwritten"},
      "instructor": {"value": "ชื่ออาจารย์ผู้สอน", "confidence": 0.85, "input_type": "handwritten"},
      "semester": {"value": "ภาคต้น/ปลาย/ซัมเมอร์", "confidence": 0.9, "input_type": "handwritten"},
      "academic_year": {"value": "25XX", "confidence": 0.9, "input_type": "handwritten"},
      "reason": {"value": "เหตุผล", "confidence": 0.8, "input_type": "handwritten"}
    },
    "สำหรับแบบ 18": {
      "refund_amount": {"value": 0, "confidence": 0.8, "input_type": "handwritten"},
      "fee_type": {"value": "ประเภทค่าใช้จ่าย", "confidence": 0.9, "input_type": "printed"},
      "bank_name": {"value": "ธนาคาร", "confidence": 0.85, "input_type": "handwritten"},
      "bank_account": {"value": "เลขบัญชี", "confidence": 0.8, "input_type": "handwritten"},
      "account_name": {"value": "ชื่อบัญชี", "confidence": 0.85, "input_type": "handwritten"},
      "promptpay_id": {"value": "เลขพร้อมเพย์", "confidence": 0.85, "input_type": "handwritten"},
      "refund_reason": {"value": "สาเหตุ", "confidence": 0.8, "input_type": "handwritten"},
      "semester": {"value": "ภาคต้น/ปลาย/ซัมเมอร์", "confidence": 0.9, "input_type": "handwritten"},
      "academic_year": {"value": "25XX", "confidence": 0.9, "input_type": "handwritten"}
    },
    "สำหรับแบบ 20": {
      "courses": [{"course_code": "รหัส", "course_name": "ชื่อวิชา", "credits": 3, "section": "1", "instructor": "อาจารย์", "confidence": 0.9}],
      "total_credits": {"value": 0, "confidence": 0.9, "input_type": "handwritten"},
      "reason": {"value": "เหตุผล", "confidence": 0.8, "input_type": "handwritten"},
      "semester": {"value": "ภาคต้น/ปลาย/ซัมเมอร์", "confidence": 0.9, "input_type": "handwritten"},
      "academic_year": {"value": "25XX", "confidence": 0.9, "input_type": "handwritten"}
    }
  },
  "signatures": {
    "student_signature": {"detected": true, "confidence": 0.9},
    "advisor_signature": {"detected": false, "confidence": 0.1}
  },
  "validation": {
    "is_complete": false,
    "total_fields": 15,
    "filled_fields": 12,
    "completion_rate": 0.8,
    "missing_fields": ["field1", "field2"],
    "format_errors": ["student_id ไม่ครบ 10 หลัก"],
    "warnings": ["ชั้นปีผิดปกติ"],
    "data_quality": "good | fair | poor"
  },
  "raw_text": "ข้อความดิบทั้งหมดที่อ่านได้"
}
```

## กฎสำคัญ:
1. ตอบเป็น JSON เท่านั้น ไม่ต้องมีคำอธิบายเพิ่ม
2. ไม่ต้องใส่ ```json หรือ ``` ครอบ
3. ใส่เฉพาะ form_specific_data ของประเภทที่ตรวจพบ (ไม่ต้องใส่ทุกประเภท)
4. ถ้าอ่านไม่ออก ใส่ value: null, confidence: 0.0
5. ลายมือให้พยายามอ่านให้ดีที่สุด แต่ให้ confidence ต่ำถ้าไม่มั่นใจ
6. รหัสนิสิตต้องเป็นตัวเลข 10 หลัก ขึ้นต้นด้วย 6
7. จำนวนเงินเป็นตัวเลข (หน่วยบาท ไม่มีเครื่องหมาย)"""


class GeminiVisionOCR:
    """
    Gemini Vision OCR Service
    
    Best for Thai handwriting recognition - FREE!
    Uses new google-genai SDK with Client-based architecture.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini Vision client
        
        Args:
            api_key: Gemini API key (optional, uses default if not provided)
        """
        if not GEMINI_AVAILABLE:
            raise ImportError(
                "Gemini not installed. "
                "Run: pip install google-genai"
            )
        
        # Get API key
        self.api_key = api_key or os.environ.get('GEMINI_API_KEY') or DEFAULT_API_KEY
        
        if not self.api_key:
            raise ValueError("Gemini API key not provided")
        
        # Initialize Client (new SDK architecture)
        self.client = genai.Client(api_key=self.api_key)
        
        # Model name for Gemini 2.5 Flash (2.0 deprecated for new users)
        self.model_name = "gemini-2.5-flash"
        
        logger.info("Gemini Vision initialized successfully")
    
    def _image_to_base64(self, image_bytes: bytes) -> str:
        """Convert image bytes to base64"""
        return base64.b64encode(image_bytes).decode('utf-8')
    
    def ocr_image(self, image_bytes: bytes, mime_type: str = "image/png", custom_prompt: str = None) -> Tuple[str, List[dict], float]:
        """
        OCR an image using Gemini Vision (with cache)
        
        Args:
            image_bytes: Image as bytes
            mime_type: MIME type of image
            custom_prompt: Custom prompt for OCR (optional)
            
        Returns:
            Tuple of (text, details, confidence)
        """
        # Check cache first (only for default prompt)
        file_hash = _get_file_hash(image_bytes)
        if not custom_prompt:
            cached = _ocr_cache_get(file_hash)
            if cached:
                return cached
        
        # Create image part for Gemini using types.Part.from_bytes()
        image_part = types.Part.from_bytes(
            data=image_bytes,
            mime_type=mime_type
        )
        
        # Use custom prompt if provided, otherwise use default ADE-style prompt
        if custom_prompt:
            prompt = custom_prompt
        else:
            # Default prompt - ADE-style structured JSON extraction
            prompt = DOCUMENT_AI_PROMPT

        # Retry logic with exponential backoff
        max_retries = 3
        base_delay = 2  # seconds
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                # Call Gemini using new Client API
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=[prompt, image_part]
                )
                
                # Extract text
                full_text = response.text if response.text else ""
                
                # Create simple details (Gemini doesn't provide bounding boxes)
                details = [{
                    "text": full_text,
                    "confidence": 0.9,  # Gemini doesn't provide confidence, estimate high
                    "bbox": []
                }]
                
                # Estimate confidence based on response
                confidence = 0.9 if full_text else 0.0
                
                if attempt > 0:
                    logger.info(f"✅ Gemini succeeded on retry attempt {attempt}")
                
                result = (full_text, details, confidence)
                # Store in cache (only default prompt)
                if not custom_prompt:
                    _ocr_cache_set(file_hash, result)
                
                return result
                
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                
                # Check if retryable error (rate limit, server error)
                is_retryable = any(keyword in error_str for keyword in [
                    '429', 'rate limit', 'quota', 'resource exhausted',
                    '500', '503', 'unavailable', 'internal', 'timeout',
                    'deadline exceeded'
                ])
                
                if is_retryable and attempt < max_retries:
                    delay = base_delay * (2 ** attempt)  # 2s, 4s, 8s
                    logger.warning(
                        f"⚠️ Gemini API error (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                        f"Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"❌ Gemini Vision OCR error (attempt {attempt + 1}): {e}")
                    raise
    
    def ocr_pdf(self, pdf_bytes: bytes, custom_prompt: str = None) -> Tuple[str, List[dict], float]:
        """
        OCR a PDF using Gemini Vision
        
        Converts PDF to images first, then OCR each page
        
        Args:
            pdf_bytes: PDF file as bytes
            custom_prompt: Custom prompt for OCR (optional)
        """
        try:
            import fitz  # PyMuPDF
            
            # Convert PDF to images
            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            all_text = ""
            all_details = []
            total_confidence = 0
            count = 0
            
            for page_num in range(len(pdf_document)):
                page = pdf_document.load_page(page_num)
                
                # Render at higher DPI for better OCR
                zoom = 200 / 72  # 200 DPI
                matrix = fitz.Matrix(zoom, zoom)
                pixmap = page.get_pixmap(matrix=matrix)
                
                # Convert to bytes
                img_bytes = pixmap.tobytes("png")
                
                # OCR the page with custom prompt
                text, details, confidence = self.ocr_image(img_bytes, "image/png", custom_prompt)
                
                all_text += f"\n--- Page {page_num + 1} ---\n{text}\n"
                all_details.extend(details)
                total_confidence += confidence
                count += 1
            
            pdf_document.close()
            
            avg_confidence = total_confidence / count if count > 0 else 0
            return all_text, all_details, avg_confidence
            
        except Exception as e:
            logger.error(f"Gemini Vision PDF OCR error: {e}")
            raise
    
    def ocr_document(self, file_bytes: bytes, content_type: str, custom_prompt: str = None) -> Tuple[str, List[dict], float]:
        """
        OCR a document (PDF or Image)
        
        Args:
            file_bytes: File content as bytes
            content_type: MIME type
            custom_prompt: Custom prompt for OCR (optional)
            
        Returns:
            Tuple of (text, details, confidence)
        """
        if content_type == "application/pdf":
            return self.ocr_pdf(file_bytes, custom_prompt)
        else:
            # Map content type to mime type
            mime_type = content_type if content_type else "image/png"
            return self.ocr_image(file_bytes, mime_type, custom_prompt)


# Singleton instance
_gemini_vision_ocr = None

def get_gemini_vision_ocr(api_key: Optional[str] = None) -> GeminiVisionOCR:
    """Get singleton Gemini Vision OCR instance"""
    global _gemini_vision_ocr
    
    if _gemini_vision_ocr is None:
        _gemini_vision_ocr = GeminiVisionOCR(api_key)
    
    return _gemini_vision_ocr


def is_gemini_available() -> bool:
    """Check if Gemini is available"""
    return GEMINI_AVAILABLE and bool(DEFAULT_API_KEY or os.environ.get('GEMINI_API_KEY'))
