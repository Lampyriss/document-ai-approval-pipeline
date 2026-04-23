# OCR Service Module
# Primary: Gemini Vision OCR

"""
โมดูลนี้รับผิดชอบ:
1. แปลง PDF เป็น Image
2. OCR อ่านข้อความจากภาพ (Gemini Vision primary)
3. จำแนกประเภทเอกสาร
4. Extract fields ตามประเภทฟอร์ม
"""

import numpy as np
from PIL import Image
import io
import re
import logging
from typing import Optional, List, Tuple
import fitz  # PyMuPDF for PDF processing

# Setup logger
logger = logging.getLogger(__name__)

# Legacy OCR engines removed — Gemini Vision is the only OCR engine
EASYOCR_AVAILABLE = False
TESSERACT_AVAILABLE = False


class OCRService:
    """Service หลักสำหรับ OCR - EasyOCR (Legacy fallback)"""
    
    def __init__(self):
        """Initialize EasyOCR Reader (รองรับไทย + อังกฤษ)"""
        if not EASYOCR_AVAILABLE:
            raise ImportError(
                "EasyOCR is not installed. "
                "Gemini Vision should be used as primary OCR engine. "
                "Set GEMINI_API_KEY environment variable."
            )
        logger.info("Loading OCR Model... (first time may take a while)")
        self.reader = easyocr.Reader(
            ['th', 'en'],  # ภาษาไทย + อังกฤษ
            gpu=False,      # เปลี่ยนเป็น True ถ้ามี GPU
            verbose=False
        )
        self.engine_name = "EasyOCR"
        logger.info("OCR Model loaded successfully!")
    
    def pdf_to_images(self, pdf_bytes: bytes, dpi: int = 200) -> List[np.ndarray]:
        """
        แปลง PDF เป็น list ของ images (numpy arrays)
        
        Args:
            pdf_bytes: ไฟล์ PDF ในรูป bytes
            dpi: ความละเอียดของภาพ (ยิ่งสูงยิ่งชัด แต่ช้าลง)
        
        Returns:
            List ของ numpy arrays (images)
        """
        images = []
        
        # เปิด PDF ด้วย PyMuPDF
        pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            
            # แปลงเป็น pixmap (image)
            zoom = dpi / 72  # 72 คือ default DPI ของ PDF
            matrix = fitz.Matrix(zoom, zoom)
            pixmap = page.get_pixmap(matrix=matrix)
            
            # แปลงเป็น numpy array
            img_data = pixmap.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            img_array = np.array(img)
            
            images.append(img_array)
        
        pdf_document.close()
        return images
    
    def image_to_array(self, image_bytes: bytes) -> np.ndarray:
        """แปลง image bytes เป็น numpy array"""
        img = Image.open(io.BytesIO(image_bytes))
        return np.array(img)
    
    def ocr_image(self, image: np.ndarray) -> Tuple[str, List[dict]]:
        """
        OCR อ่านข้อความจากภาพ
        
        Args:
            image: numpy array ของภาพ
        
        Returns:
            Tuple of (full_text, details)
            - full_text: ข้อความทั้งหมดรวมกัน
            - details: list ของ dict ที่มี bbox, text, confidence
        """
        results = self.reader.readtext(image)
        
        # รวมข้อความทั้งหมด
        full_text = ""
        details = []
        
        for (bbox, text, confidence) in results:
            full_text += text + "\n"
            # Convert bbox to list of lists (for JSON serialization)
            bbox_list = [[float(p[0]), float(p[1])] for p in bbox]
            details.append({
                "bbox": bbox_list,
                "text": text,
                "confidence": float(confidence)
            })
        
        return full_text.strip(), details
    
    def ocr_document(self, file_bytes: bytes, content_type: str) -> Tuple[str, List[dict], float]:
        """
        OCR อ่านเอกสาร (PDF หรือ Image)
        
        Args:
            file_bytes: ไฟล์ในรูป bytes
            content_type: MIME type ของไฟล์
        
        Returns:
            Tuple of (full_text, all_details, average_confidence)
        """
        all_text = ""
        all_details = []
        total_confidence = 0
        total_items = 0
        
        if content_type == "application/pdf":
            # PDF: แปลงเป็น images แล้ว OCR ทีละหน้า
            images = self.pdf_to_images(file_bytes)
            for i, img in enumerate(images):
                text, details = self.ocr_image(img)
                all_text += f"\n--- Page {i+1} ---\n{text}\n"
                all_details.extend(details)
                for d in details:
                    total_confidence += d["confidence"]
                    total_items += 1
        else:
            # Image: OCR โดยตรง
            img = self.image_to_array(file_bytes)
            all_text, all_details = self.ocr_image(img)
            for d in all_details:
                total_confidence += d["confidence"]
                total_items += 1
        
        avg_confidence = total_confidence / total_items if total_items > 0 else 0
        
        return all_text, all_details, avg_confidence


class TesseractOCRService:
    """OCR Service ใช้ Tesseract - เร็วกว่า EasyOCR"""
    
    def __init__(self):
        if not TESSERACT_AVAILABLE:
            raise ImportError("pytesseract not installed. Run: pip install pytesseract")
        self.engine_name = "Tesseract"
        logger.info("Tesseract OCR is ready")
    
    def pdf_to_images(self, pdf_bytes: bytes, dpi: int = 200) -> List[np.ndarray]:
        """แปลง PDF เป็น images"""
        images = []
        pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            zoom = dpi / 72
            matrix = fitz.Matrix(zoom, zoom)
            pixmap = page.get_pixmap(matrix=matrix)
            img_data = pixmap.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            images.append(np.array(img))
        
        pdf_document.close()
        return images
    
    def image_to_array(self, image_bytes: bytes) -> np.ndarray:
        img = Image.open(io.BytesIO(image_bytes))
        return np.array(img)
    
    def ocr_image(self, image: np.ndarray) -> Tuple[str, List[dict]]:
        """OCR ด้วย Tesseract"""
        pil_img = Image.fromarray(image)
        
        # Get detailed data
        data = pytesseract.image_to_data(pil_img, lang='tha+eng', output_type=pytesseract.Output.DICT)
        
        full_text = ""
        details = []
        
        for i in range(len(data['text'])):
            text = data['text'][i].strip()
            conf = int(data['conf'][i])
            
            if text and conf > 0:
                full_text += text + " "
                x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                details.append({
                    "bbox": [[x, y], [x+w, y], [x+w, y+h], [x, y+h]],
                    "text": text,
                    "confidence": conf / 100.0
                })
        
        return full_text.strip(), details
    
    def ocr_document(self, file_bytes: bytes, content_type: str) -> Tuple[str, List[dict], float]:
        """OCR เอกสาร"""
        all_text = ""
        all_details = []
        total_confidence = 0
        total_items = 0
        
        if content_type == "application/pdf":
            images = self.pdf_to_images(file_bytes)
            for i, img in enumerate(images):
                text, details = self.ocr_image(img)
                all_text += f"\n--- Page {i+1} ---\n{text}\n"
                all_details.extend(details)
                for d in details:
                    total_confidence += d["confidence"]
                    total_items += 1
        else:
            img = self.image_to_array(file_bytes)
            all_text, all_details = self.ocr_image(img)
            for d in all_details:
                total_confidence += d["confidence"]
                total_items += 1
        
        avg_confidence = total_confidence / total_items if total_items > 0 else 0
        return all_text, all_details, avg_confidence


class MultiOCRService:
    """Multi-OCR Service - เลือก engine ได้"""
    
    def __init__(self):
        self.engines = {}
        self.default_engine = "easyocr"
        
        # Load EasyOCR
        logger.info("Loading OCR Models...")
        self.engines["easyocr"] = OCRService()
        
        # Load Tesseract if available
        if TESSERACT_AVAILABLE:
            try:
                self.engines["tesseract"] = TesseractOCRService()
            except Exception as e:
                logger.warning(f"Could not load Tesseract: {e}")
        
        logger.info(f"OCR Engines ready: {list(self.engines.keys())}")
    
    def get_available_engines(self) -> dict:
        """รายการ engines ที่พร้อมใช้งาน"""
        return {
            name: {
                **OCR_ENGINES.get(name, {}),
                "loaded": name in self.engines
            }
            for name in ["easyocr", "tesseract"]
        }
    
    def ocr_document(
        self, 
        file_bytes: bytes, 
        content_type: str, 
        engine: str = "easyocr"
    ) -> Tuple[str, List[dict], float, str]:
        """
        OCR เอกสารด้วย engine ที่เลือก
        
        Returns:
            Tuple of (text, details, confidence, engine_used)
        """
        if engine not in self.engines:
            engine = self.default_engine
        
        ocr_service = self.engines[engine]
        text, details, confidence = ocr_service.ocr_document(file_bytes, content_type)
        
        return text, details, confidence, ocr_service.engine_name


class DocumentClassifier:
    """จำแนกประเภทเอกสารจากข้อความ OCR"""
    
    # Pattern สำหรับเลขเอกสาร Registrar-XX (วิธีหลัก - แม่นยำที่สุด)
    REGISTRAR_PATTERNS = [
        r'[Rr]egistrar[\s\-_]*(\d+)',      # Registrar-18, Registrar 18
        r'[Rr]egister[\s\-_]*(\d+)',       # Register-18
        r'แบบ\s*(\d+)',                     # แบบ 18
        r'[Ff]orm[\s\-_]*(\d+)',            # Form-18, Form 18
        r'[Rr]egister[\s\-_]*2[o0]',        # register-2o, register-20 (OCR error)
        r'หรือ\s*20',                       # หรือ 20
        r'or\s*2[o0]',                      # or 2o, or 20
    ]
    
    # เลขเอกสารที่รองรับ
    SUPPORTED_FORMS = ["4", "18", "20", "2"]  # เพิ่ม "2" สำหรับกรณี OCR อ่านผิด
    
    # Keywords สำหรับ fallback (ถ้าหา pattern ไม่เจอ)
    FORM_KEYWORDS = {
        "18": [
            "ขอคืนเงิน", "คืนเงิน", "refund", "tuition fee",
            "ค่าธรรมเนียม", "เลขที่บัญชี", "ธนาคาร"
        ],
        "20": [
            "ลงทะเบียนเรียนเพิ่ม", "add registration", "ลงเพิ่ม",
            "รายวิชา", "หน่วยกิต", "section"
        ],
        "4": [
            "เรียนควบ", "prerequisite", "วิชาบังคับก่อน",
            "วิชาต่อเนื่อง", "continuing course"
        ]
    }
    
    def classify(self, text: str) -> Tuple[str, float]:
        """
        จำแนกประเภทเอกสาร
        
        วิธีการ:
        1. หา pattern Registrar-XX ก่อน (แม่นยำ 100%)
        2. ถ้าไม่เจอ ใช้ keyword matching (fallback)
        
        Args:
            text: ข้อความที่ได้จาก OCR
        
        Returns:
            Tuple of (form_type, confidence)
        """
        
        # Special check: หา pattern เฉพาะสำหรับ Form 20
        # เช่น "register-2 หรือ 20", "register-2o", "or 2o"
        special_20_patterns = [
            r'[Rr]egister[\s\-_]*2\s*หรือ\s*20',    # register-2 หรือ 20
            r'[Rr]egister[\s\-_]*2[o0]',             # register-2o, register-20
            r'or\s*2[o0]',                            # or 2o
            r'หรือ\s*20',                             # หรือ 20
        ]
        for pattern in special_20_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                logger.debug(f"Found special pattern for Form 20: {pattern}")
                return "20", 1.0
        
        # 1. หา Registrar-XX pattern ก่อน (วิธีหลัก)
        for pattern in self.REGISTRAR_PATTERNS:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, str):
                    form_num = match.strip()
                    # Map "2" to "20" (OCR error correction)
                    if form_num == "2":
                        form_num = "20"
                    if form_num in self.SUPPORTED_FORMS:
                        logger.debug(f"Found pattern: {pattern} -> Form {form_num}")
                        return form_num, 1.0  # confidence 100%
        
        # 2. Fallback: ใช้ keyword matching
        logger.debug("Registrar pattern not found, using keyword matching...")
        text_lower = text.lower()
        
        scores = {}
        for form_type, keywords in self.FORM_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    score += 1
            scores[form_type] = score / len(keywords) if keywords else 0
        
        # หา form type ที่มี score สูงสุด
        best_form = max(scores, key=scores.get)
        best_score = scores[best_form]
        
        # ถ้า score ต่ำเกินไป ให้ return unknown
        if best_score < 0.2:
            return "unknown", 0.0
        
        return best_form, best_score


class Form18Extractor:
    """Extract ข้อมูลจากแบบ 18 - ขอคืนเงิน"""
    
    # Constants
    STUDENT_ID_LENGTH = 10
    PROMPTPAY_LENGTH = 13
    MIN_ACADEMIC_YEAR = 2560  # Minimum valid academic year (B.E.)
    MIN_REFUND_AMOUNT = 100.0  # Minimum reasonable refund amount
    
    def _clean_text(self, text: str) -> str:
        """ทำความสะอาด text - ลบ special chars ที่ OCR ใส่มา (เก็บ newlines ไว้)"""
        # Input validation
        if text is None:
            logger.warning("_clean_text received None, returning empty string")
            return ""
        if not isinstance(text, str):
            logger.warning(f"_clean_text received non-string type: {type(text)}, converting to string")
            text = str(text)
        
        # ลบ _, *, `, .. ที่ OCR ใส่มา
        text = re.sub(r'[_*`]', '', text)
        text = re.sub(r'\.{2,}', ' ', text)  # .. -> space
        # ลบ multiple spaces แต่เก็บ newlines ไว้ (สำคัญสำหรับการหาข้อมูลแบบแยกบรรทัด)
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            cleaned_line = re.sub(r'\s+', ' ', line).strip()
            if cleaned_line:
                cleaned_lines.append(cleaned_line)
        return '\n'.join(cleaned_lines)
    
    def extract(self, text: str) -> dict:
        """Extract fields จากข้อความ"""
        # Input validation
        if text is None:
            logger.warning("Form18Extractor.extract received None text")
            return {}
        if not isinstance(text, str):
            logger.warning(f"Form18Extractor.extract received non-string type: {type(text)}, converting to string")
            text = str(text)
        if not text.strip():
            logger.warning("Form18Extractor.extract received empty text")
            return {}
        
        logger.info(f"Starting Form 18 extraction, text length: {len(text)} chars")
        
        # ทำความสะอาด text ก่อน
        clean = self._clean_text(text)
        
        data = {
            "student_id": self._extract_student_id(text),  # ใช้ original เพราะต้องการเลข
            "name": self._extract_name(clean),
            "faculty": self._extract_faculty(clean),
            "department": self._extract_department(clean),
            "year_of_study": self._extract_year_of_study(clean),
            "phone": self._extract_phone(text),  # ใช้ original
            "email": self._extract_email(text),  # ใช้ original
            "advisor_name": self._extract_advisor(clean),
            "semester": self._extract_semester(clean),
            "academic_year": self._extract_academic_year(clean),
            "refund_amount": self._extract_amount(clean),
            "promptpay_id": self._extract_promptpay(text),  # ใช้ original
            "bank_name": self._extract_bank(clean),
        }
        
        # Log extraction results
        extracted_count = sum(1 for v in data.values() if v is not None)
        logger.info(f"Form 18 extraction complete: {extracted_count}/{len(data)} fields extracted")
        
        return data
    
    def _extract_student_id(self, text: str) -> Optional[str]:
        """หารหัสนิสิต (10 หลัก) - รองรับกรณีตัวเลขกระจายในหลายบรรทัด"""
        # Pattern 1: เลขติดกัน 10 หลัก (ปกติ) - ขึ้นต้นด้วย 5, 6 หรือ 7
        pattern1 = r'\b[5-7][0-9]{9}\b'
        match = re.search(pattern1, text)
        if match:
            return match.group(0)
        
        # Pattern 2: หาในบริเวณที่มีคำว่า "รหัสประจำตัวนิสิต" หรือ "Student ID"
        # รองรับกรณีเลขกระจายในบรรทัดเดียวกัน เช่น "5 3 0 1 1 5 7 3"
        context_patterns = [
            r'(?:รหัสประจำตัวนิสิต|student\s*id|รหัสนิสิต)[^0-9]*([5-7](?:\s*\d){9})',
            r'(?:รหัสประจำตัวนิสิต|student\s*id|รหัสนิสิต)[^0-9]*([5-7]\s*\d\s*\d\s*\d\s*\d\s*\d\s*\d\s*\d\s*\d\s*\d)',
        ]
        for pattern in context_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                student_id = re.sub(r'\s+', '', match.group(1))
                if len(student_id) == 10 and student_id[0] in ['5', '6', '7']:
                    return student_id
        
        # Pattern 3: เลขกระจายในหลายบรรทัด (หลังคำว่า "รหัสประจำตัวนิสิต")
        # กรณี: รหัสประจำตัวนิสิต
        #        นิสิตชั้นปีที่ 4
        #        คณะ วิทยาการจัดการ  
        #        5
        #        3
        #        0
        #        1
        #        1
        #        5
        #        7
        #        3
        lines = text.split('\n')
        for i, line in enumerate(lines):
            # ต้องเป็นรหัสประจำตัวนิสิต หรือ ID Number (ไม่ใช่แค่ Student/Name)
            if 'รหัสประจำตัวนิสิต' in line or 'id number' in line.lower() or 'student id' in line.lower():
                # เก็บเลขจากบรรทัดถัดไป 20 บรรทัด (ข้ามข้อความที่มีตัวอักษรไทย)
                student_digits = []
                for j in range(i+1, min(i+20, len(lines))):
                    line_content = lines[j].strip()
                    # หยุดถ้าเจอคำว่า "โทรศัพท์" หรือ "สาขา" หรือ "field" (จบส่วนรหัสนิสิตแล้ว)
                    if any(keyword in line_content for keyword in ['โทรศัพท์', 'สาขา', 'field', 'e-mail', 'email', 'phone']):
                        break
                    # ข้ามบรรทัดที่มีตัวอักษรไทย (เช่น "นิสิตชั้นปีที่ 4", "คณะ...") - ไม่ใช่ส่วนของรหัสนิสิต
                    thai_chars = re.findall(r'[ก-๙]', line_content)
                    if thai_chars:
                        continue
                    # ดึงตัวเลขจากแต่ละบรรทัด
                    digits_in_line = re.findall(r'\d', line_content)
                    if digits_in_line:
                        student_digits.extend(digits_in_line)
                    if len(student_digits) >= self.STUDENT_ID_LENGTH:
                        break
                
                if len(student_digits) >= self.STUDENT_ID_LENGTH:
                    # หา 10 ตัวเลขติดกันที่ขึ้นต้นด้วย 5, 6, หรือ 7
                    for k in range(len(student_digits) - 9):
                        candidate = ''.join(student_digits[k:k+10])
                        if len(candidate) == 10 and candidate[0] in ['5', '6', '7']:
                            return candidate
        
        # Pattern 4: หารหัสนิสิตจากตาราง (กรณีข้อมูลอยู่ห่างจาก label)
        # มักอยู่ในบริเวณที่มี "Year of Study" และ "Faculty"
        for i, line in enumerate(lines):
            if 'year of study' in line.lower() or 'faculty' in line.lower():
                # ดูบรรทัดถัดไป 10 บรรทัดเพื่อหาเลขกระจาย
                student_digits = []
                for j in range(i+1, min(i+10, len(lines))):
                    line_content = lines[j].strip()
                    # ข้ามบรรทัดที่มีตัวอักษรไทยหรือเป็นคำยาว
                    if len(line_content) > 20:
                        continue
                    thai_chars = re.findall(r'[ก-๙]', line_content)
                    if thai_chars and len(thai_chars) > 2:
                        continue
                    # ดึงตัวเลข
                    digits_in_line = re.findall(r'\d', line_content)
                    if digits_in_line:
                        student_digits.extend(digits_in_line)
                    # หยุดถ้าเจอ phone number หรือ email
                    if re.search(r'\b\d{10}\b', line_content) and j > i+1:
                        break
                    if '@' in line_content:
                        break
                    if len(student_digits) >= self.STUDENT_ID_LENGTH:
                        break
                
                if len(student_digits) >= self.STUDENT_ID_LENGTH:
                    candidate = ''.join(student_digits[:10])
                    if len(candidate) == 10 and candidate[0] in ['5', '6', '7']:
                        return candidate
        
        return None
    
    def _extract_name(self, text: str) -> Optional[str]:
        """หาชื่อ-นามสกุล - รองรับทั้ง pattern ติดกันและแยกบรรทัด"""
        # Pattern สำหรับภาษาไทย (รวมสระและวรรณยุกต์)
        thai_name = r'[ก-ฮะ-์เ-ไ]+[\sก-ฮะ-์เ-ไ]+'
        
        patterns = [
            # Pattern 1: ชื่อนิสิต (...) ชื่อ นามสกุล
            rf'ชื่อนิสิต\s*\([^)]*\)\s*({thai_name})',
            # Pattern 2: หลัง นาย/นาง/นางสาว
            rf'(?:นาย|นาง|นางสาว)\s*({thai_name})',
            # Pattern 3: Student's Name ... ชื่อ
            rf"[Ss]tudent'?s?\s*[Nn]ame[^ก-ฮ]*({thai_name})",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                name = match.group(1).strip()
                # ตัดคำที่ไม่ใช่ชื่อ
                unwanted = ['ตัวบรรจง', 'ตวบรรจง', 'print', 'name', 'student']
                for word in unwanted:
                    name = re.sub(rf'\s*{word}\s*', ' ', name, flags=re.IGNORECASE)
                name = re.sub(r'\s+', ' ', name).strip()
                if len(name) > 3:
                    return name
        
        # Pattern 4: หาชื่อจากบรรทัดถัดไปหลัง "ชื่อนิสิต" (กรณีกรอกแยกบรรทัด)
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if 'ชื่อนิสิต' in line or ('Student' in line and 'Name' in line):
                # ดูบรรทัดถัดไป 10 บรรทัด
                for j in range(i+1, min(i+11, len(lines))):
                    candidate = lines[j].strip()
                    # หยุดถ้าเจอ keywords ที่ไม่ใช่ชื่อ
                    if any(kw in candidate.lower() for kw in ['reason', 'เหตุผล', 'field of study', 'สาขา', 'phone', 'โทรศัพท์', 'e-mail', 'email']):
                        break
                    # ต้องมีตัวอักษรไทยและไม่มีคำที่ไม่ใช่ชื่อ
                    if re.search(r'[ก-ฮะ-์เ-ไ]', candidate):
                        # ตัดคำที่ไม่ใช่ชื่อ
                        unwanted = ['ตัวบรรจง', 'ตวบรรจง', 'print', 'name', 'student', 'mr.', 'mrs.', 'miss']
                        name = candidate
                        for word in unwanted:
                            name = re.sub(rf'\s*{word}\s*', ' ', name, flags=re.IGNORECASE)
                        name = re.sub(r'\s+', ' ', name).strip()
                        # ต้องมีคำขึ้นต้นด้วย นาย/นาง/นางสาว หรือเป็นชื่อภาษาไทยที่มีความยาวพอสมควร
                        if len(name) > 3:
                            # ถ้าไม่มี นาย/นาง/นางสาว แต่เป็นชื่อ 2 คำภาษาไทย ก็รับได้
                            if 'นาย' in name or 'นาง' in name or len(name.split()) >= 2:
                                return name
        
        # Pattern 5: หาชื่อจากตาราง (กรณีอยู่ใกล้ Year of Study / Faculty)
        # ชื่อมักอยู่บรรทัดถัดไปหลัง Year of Study/Faculty (ก่อนหน้ารหัสนิสิตที่กระจาย)
        for i, line in enumerate(lines):
            if 'year of study' in line.lower() or 'faculty' in line.lower():
                # ดูบรรทัดถัดไป 5 บรรทัด (ข้าม "Faculty" label)
                thai_lines = []
                for j in range(i+1, min(i+6, len(lines))):
                    candidate = lines[j].strip()
                    # ต้องมีตัวอักษรไทยและไม่ใช่คำทั่วไป
                    if re.search(r'[ก-ฮะ-์เ-ไ]', candidate) and len(candidate) > 3:
                        if not any(kw in candidate for kw in ['คณะ', 'สาขา', 'ที่ปรึกษา', 'โทรศัพท์']):
                            thai_lines.append((j, candidate))
                
                # ถ้าเจอหลายบรรทัดที่มี Thai
                # บรรทัดแรกอาจเป็น advisor (มักมี 3 คำ: อาจารย์ ชื่อ นามสกุล)
                # บรรทัดที่สองมักเป็น student name (มักมี 2 คำ: ชื่อ นามสกุล)
                if len(thai_lines) >= 2:
                    # เลือกบรรทัดที่มี 2 คำ (น่าจะเป็น student name)
                    for idx, (line_num, candidate) in enumerate(thai_lines):
                        # ตัดคำที่ไม่ใช่ชื่อ
                        unwanted = ['อาจารย์', 'อ.', 'ผศ.', 'รศ.', 'ดร.', 'mr.', 'mrs.', 'miss']
                        name = candidate
                        for word in unwanted:
                            name = name.replace(word, '').strip()
                        name = re.sub(r'\s+', ' ', name).strip()
                        # Skip if name is empty after cleaning
                        if not name or len(name.strip()) == 0:
                            continue
                        words = name.split()
                        # ถ้ามี 2 คำ น่าจะเป็น student name
                        if len(words) == 2:
                            return name
                    # ถ้าไม่เจอ 2 คำ ให้เอาอันที่ไม่มี title (ไม่มี อาจารย์/ดร.)
                    for idx, (line_num, candidate) in enumerate(thai_lines):
                        if 'อาจารย์' not in candidate and 'อ.' not in candidate and 'ดร.' not in candidate:
                            unwanted = ['ผศ.', 'รศ.', 'mr.', 'mrs.', 'miss']
                            name = candidate
                            for word in unwanted:
                                name = name.replace(word, '').strip()
                            name = re.sub(r'\s+', ' ', name).strip()
                            if len(name.split()) >= 2:
                                return name
                elif len(thai_lines) == 1:
                    # ถ้ามีแค่บรรทัดเดียว
                    line_num, candidate = thai_lines[0]
                    unwanted = ['อาจารย์', 'อ.', 'ผศ.', 'รศ.', 'ดร.', 'mr.', 'mrs.', 'miss']
                    name = candidate
                    for word in unwanted:
                        name = name.replace(word, '').strip()
                    name = re.sub(r'\s+', ' ', name).strip()
                    if len(name.split()) >= 2:
                        return name
        
        return None
    
    def _extract_department(self, text: str) -> Optional[str]:
        """หาสาขาวิชา - รองรับกรณีกรอกแยกบรรทัด"""
        # Pattern 1: สาขา: xxx รหัสสาขา (แบบติดกัน)
        pattern1 = r'สาขา\s*[:\s]*([ก-ฮะ-์เ-ไa-zA-Z\s]+?)(?:\s*รหัสสาขา|\s*รหัส|\s*Field|\s*โทรศัพท์|\n)'
        match = re.search(pattern1, text)
        if match:
            dept = match.group(1).strip()
            # ตัดคำที่ไม่ใช่ชื่อสาขา
            dept = re.sub(r'Field of Study.*', '', dept).strip()
            dept = re.sub(r'Code.*', '', dept).strip()
            # ข้ามถ้าเป็นจุด (.....) หรือมีตัวอักษรไทยน้อยเกินไป หรือเป็นคำทั่วไป
            if len(dept) > 5 and dept not in ['Field', 'Code', 'of', 'Study']:
                if re.search(r'[ก-ฮะ-์เ-ไ]', dept) and not re.match(r'^[.\s]+$', dept):
                    # ข้ามถ้าเป็นคำทั่วไป เช่น "รหัส", "โทรศัพท์", "E-mail"
                    if not any(kw in dept for kw in ['รหัสสาขา', 'รหัส', 'โทรศัพท์', 'E-mail', 'email', 'กรุณา', '........']):
                        return dept
        
        # Pattern 2: หาจากบรรทัดที่มี "สาขา" แล้วดูบรรทัดถัดไป
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if 'สาขา' in line and 'Field of Study' not in line:
                # ถ้าบรรทัดนี้มีข้อความต่อจาก "สาขา" เลย
                if len(line) > 10:
                    dept = line.replace('สาขา', '').strip()
                    dept = re.sub(r'[:\s]+', ' ', dept).strip()
                    if len(dept) > 2:
                        return dept
                # ถ้าไม่มี ดูบรรทัดถัดไป
                elif i + 1 < len(lines):
                    candidate = lines[i + 1].strip()
                    # ต้องเป็นข้อความที่มีตัวอักษรไทยและไม่มีคำทั่วไป
                    if re.search(r'[ก-ฮะ-์เ-ไ]', candidate):
                        if not any(kw in candidate for kw in ['รหัส', 'โทรศัพท์', 'E-mail', 'Field', 'Code']):
                            return candidate
        
        # Pattern 3: สาขาวิชา...
        pattern3 = r'สาขาวิชา\s*([ก-ฮะ-์เ-ไ]+)'
        match = re.search(pattern3, text)
        if match:
            return match.group(1).strip()
        
        # Pattern 4: หาจากตาราง (หลัง email/phone)
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if '@' in line or re.search(r'\b0\d{9}\b', line):
                # ดูบรรทัดถัดไป 3 บรรทัด
                for j in range(i+1, min(i+4, len(lines))):
                    candidate = lines[j].strip()
                    if re.search(r'[ก-ฮะ-์เ-ไ]', candidate):
                        # ตรวจสอบว่าไม่ใช่ semester หรือ year
                        if not any(kw in candidate for kw in ['ต้น', 'ปลาย', 'ฤดูร้อน']):
                            if not re.search(r'\b(25\d{2}|26\d{2})\b', candidate):
                                if len(candidate) > 3:
                                    return candidate
        
        return None
    
    def _extract_year_of_study(self, text: str) -> Optional[str]:
        """หาชั้นปีที่ - รองรับทั้ง pattern ติดกันและแยกบรรทัด (ตาราง)"""
        # Pattern 1: แบบติดกัน
        patterns = [
            r'(?:นิสิต)?ชั้นปีที่[:\s]*(\d+)',
            r'ปีที่[:\s]*(\d+)',
            r'[Yy]ear[:\s]*(\d+)',
            r'[Yy]ear of [Ss]tudy[:\s]*(\d+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        # Pattern 2: แบบแยกบรรทัด (ตาราง) - หลัง "Year of Study" ในรูปแบบตาราง
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if 'year of study' in line.lower():
                # เก็บเลข 1 หลักทั้งหมดที่เจอในบรรทัดถัดไป 7 บรรทัด
                single_digits = []
                for j in range(i+1, min(i+8, len(lines))):
                    line_content = lines[j].strip()
                    # ต้องเป็นเลข 1 หลักเท่านั้น (ไม่มีอย่างอื่นผสม)
                    match = re.search(r'^(\d)$', line_content)
                    if match:
                        year = match.group(1)
                        if year in ['1', '2', '3', '4', '5', '6']:
                            single_digits.append(year)
                
                # ถ้าเจอหลายตัว ให้เอาตัวสุดท้าย (เพราะน่าจะอยู่หลังรหัสนิสิต)
                if single_digits:
                    return single_digits[-1]
        
        return None
    
    def _extract_phone(self, text: str) -> Optional[str]:
        """หาเบอร์โทรศัพท์"""
        patterns = [
            r'(?:โทรศัพท์|โทร|[Pp]hone|[Tt]el)[:\s]*(0\d{8,9})',
            r'(?:โทรศัพท์|โทร|[Pp]hone|[Tt]el)[^0-9]*(0\d{2}[\-\s]?\d{3}[\-\s]?\d{4})',
            r'\b(0[689]\d{8})\b',  # มือถือ 08x, 09x, 06x
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                phone = re.sub(r'[\-\s]', '', match.group(1))
                if len(phone) == 10:
                    return phone
        return None
    
    def _extract_email(self, text: str) -> Optional[str]:
        """หา Email - รองรับ @live.ku.th, @ku.ac.th และอื่นๆ"""
        # Pattern สำหรับ email ทั่วไป
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        
        # หา email ทั้งหมดใน text
        emails = re.findall(pattern, text)
        
        # กรองเฉพาะ email ที่มี domain ที่น่าจะใช่ (ku.th, live.ku.th เป็นต้น)
        valid_domains = ['ku.th', 'live.ku.th', 'ku.ac.th', 'gmail.com', 'hotmail.com', 'outlook.com', 'yahoo.com']
        
        for email in emails:
            email_lower = email.lower()
            # ตรวจสอบว่าเป็น domain ที่ยอมรับได้
            if any(domain in email_lower for domain in valid_domains):
                return email
        
        # ถ้าไม่เจอ domain ที่รู้จัก แต่เจอ email อื่นๆ ให้ return อันแรกที่เจอ
        if emails:
            return emails[0]
        
        return None
    
    def _extract_advisor(self, text: str) -> Optional[str]:
        """หาชื่ออาจารย์ที่ปรึกษา - รองรับทั้ง pattern ติดกันและในตาราง"""
        thai_name = r'[ก-ฮะ-์เ-ไ]+[\sก-ฮะ-์เ-ไ]*'
        
        patterns = [
            # เรียน อาจารย์ ชื่อ
            rf'เรียน\s*(?:อาจารย์|ดร\.|ผศ\.|รศ\.|ศ\.)\s*({thai_name})',
            # อาจารย์ที่ปรึกษา: ชื่อ
            rf'(?:อาจารย์ที่ปรึกษา|[Aa]dvisor)\s*[:\s]*({thai_name})',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                name = match.group(1).strip()
                # ตัดข้อความที่ไม่ใช่ชื่อ
                name = re.sub(r'(?:Date|Day|Month|Year|วันที่|To).*', '', name).strip()
                name = re.sub(r'\s+', ' ', name).strip()
                if len(name) > 2:
                    return name
        
        # Pattern 3: หาจากตาราง (กรณีอยู่ใกล้ Year of Study / Faculty)
        # อาจารย์มักอยู่บรรทัดแรกหลัง Year of Study/Faculty (ก่อนชื่อนิสิต)
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if 'year of study' in line.lower() or 'faculty' in line.lower():
                # ดูบรรทัดถัดไป 3 บรรทัด หาบรรทัดแรกที่มีตัวอักษรไทย
                # (ซึ่งน่าจะเป็น advisor เนื่องจากอยู่ก่อน student name)
                thai_lines = []
                for j in range(i+1, min(i+4, len(lines))):
                    candidate = lines[j].strip()
                    if re.search(r'[ก-ฮะ-์เ-ไ]', candidate) and len(candidate) > 3:
                        if not any(kw in candidate for kw in ['คณะ', 'สาขา', 'โทรศัพท์']):
                            thai_lines.append((j, candidate))
                
                # ถ้าเจอหลายบรรทัด บรรทัดแรกมักเป็น advisor (มี 3 คำ)
                # บรรทัดที่สองมักเป็น student name (มี 2 คำ)
                if len(thai_lines) >= 1:
                    # เลือกบรรทัดแรกที่มี 3 คำขึ้นไป (น่าจะเป็น advisor)
                    for idx, (line_num, candidate) in enumerate(thai_lines):
                        words = candidate.split()
                        if len(words) >= 3:
                            # ตัดคำนำหน้า
                            name = re.sub(r'^(อาจารย์|อ\.|ดร\.|ผศ\.|รศ\.|ศ\.)\s*', '', candidate).strip()
                            name = re.sub(r'(?:Date|Day|Month|Year|วันที่|To).*', '', name).strip()
                            name = re.sub(r'\s+', ' ', name).strip()
                            if len(name.split()) >= 2:
                                return name
                    
                    # ถ้าไม่เจอ 3 คำ ให้ลองบรรทัดแรกเลย
                    if thai_lines:
                        line_num, candidate = thai_lines[0]
                        name = re.sub(r'^(อาจารย์|อ\.|ดร\.|ผศ\.|รศ\.|ศ\.)\s*', '', candidate).strip()
                        name = re.sub(r'(?:Date|Day|Month|Year|วันที่|To).*', '', name).strip()
                        name = re.sub(r'\s+', ' ', name).strip()
                        if len(name.split()) >= 2:
                            return name
        
        return None
    
    def _extract_promptpay(self, text: str) -> Optional[str]:
        """หาเลข PromptPay / บัตรประชาชน - รองรับกรณีเลขกระจาย"""
        # Pattern 1: เลขติดกัน 13 หลัก
        patterns = [
            r'(?:พร้อมเพย์|[Pp]rompt\s*[Pp]ay)[:\s]*(\d{13})',
            r'(?:บัตรประชาชน|ID\s*card|ID\s*card\s*number)[:\s]*(\d{13})',
            r'\b(1[0-9]{12})\b',  # เลข 13 หลักขึ้นต้นด้วย 1
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        # Pattern 2: เลขกระจายมี space คั่น (เช่น "1 3662 4329 1167")
        # หาเลข 13 หลักที่อาจมี space หรือจุดคั่น
        pattern2 = r'(1)\s*[.]?\s*(\d)\s*[.]?\s*(\d)\s*[.]?\s*(\d)\s*[.]?\s*(\d)\s*[.]?\s*(\d)\s*[.]?\s*(\d)\s*[.]?\s*(\d)\s*[.]?\s*(\d)\s*[.]?\s*(\d)\s*[.]?\s*(\d)\s*[.]?\s*(\d)\s*[.]?\s*(\d)'
        match2 = re.search(pattern2, text)
        if match2:
            # รวมเลขกลับมา
            promptpay = ''.join(match2.groups())
            if len(promptpay) == self.PROMPTPAY_LENGTH and promptpay.startswith('1'):
                return promptpay
        
        # Pattern 3: หาในบริเวณช่องทางการคืนเงิน
        context_pattern = r'(?:ช่องทางการคืนเงิน|refund\s*channels|โอนเข้า)[^0-9]*(1\s*\d\s*\d\s*\d\s*\d\s*\d\s*\d\s*\d\s*\d\s*\d\s*\d\s*\d\s*\d)'
        match3 = re.search(context_pattern, text, re.IGNORECASE)
        if match3:
            promptpay = re.sub(r'\s+', '', match3.group(1))
            if len(promptpay) == self.PROMPTPAY_LENGTH:
                return promptpay
        
        return None
    
    def _extract_faculty(self, text: str) -> Optional[str]:
        """หาคณะ (รองรับทั้งไทยและอังกฤษ) - แก้ปัญหา encoding"""
        # รายการคณะที่รู้จัก
        known_faculties = [
            # ไทย
            'วิทยาการจัดการ', 'วิศวกรรมศาสตร์', 'วิทยาศาสตร์', 'ศิลปศาสตร์', 
            'เศรษฐศาสตร์', 'นิติศาสตร์', 'แพทยศาสตร์', 'ทันตแพทยศาสตร์',
            'เภสัชศาสตร์', 'สัตวแพทยศาสตร์', 'สถาปัตยกรรมศาสตร์', 'ครุศาสตร์',
            'นิเทศศาสตร์', 'สหเวชศาสตร์', 'เกษตร', 'ประมง', 'อุตสาหกรรมเกษตร',
            'วนศาสตร์', 'สิ่งแวดล้อม', 'สาธารณสุขศาสตร์',
            # อังกฤษ
            'Engineering', 'Science', 'Arts', 'Management', 'Economics',
            'Law', 'Medicine', 'Dentistry', 'Pharmacy', 'Veterinary',
            'Architecture', 'Education', 'Communication', 'Agriculture',
            'Fisheries', 'Forestry', 'Environment', 'Public Health'
        ]
        
        # Pattern 1: หาจากรายการที่รู้จักก่อน
        for faculty in known_faculties:
            if faculty in text:
                return faculty
        
        # Pattern 2: คณะ[ภาษาไทย] ที่ไม่ใช่คำทั่วไป
        pattern_thai = r'คณะ\s*([ก-ฮะ-์เ-ไ]{3,20})'
        matches = re.findall(pattern_thai, text)
        for match in matches:
            # กรองคำที่ไม่ใช่ชื่อคณะ
            if match not in ['นิสิต', 'สาขา', 'อาจารย์', 'ที่ปรึกษา', 'รหัส']:
                return match
        
        # Pattern 3: English
        pattern_eng = r'[Ff]aculty[:\s]+([A-Za-z]+)'
        match = re.search(pattern_eng, text)
        if match:
            return match.group(1).strip()
        
        return None
    
    def _extract_semester(self, text: str) -> Optional[str]:
        """หาภาคการศึกษา - รองรับทั้งใน text และในตาราง"""
        lines = text.split('\n')
        
        # Pattern 1: หาโดยตรง - บรรทัดสั้นๆ ที่มีแค่ "ต้น", "ปลาย", หรือ "ฤดูร้อน"
        for i, line in enumerate(lines):
            candidate = line.strip()
            # ถ้าบรรทัดสั้นมาก (1-4 ตัวอักษร) และเป็นตัวอักษรไทย
            if 1 <= len(candidate) <= 4:
                if re.match(r'^[ก-๙\s]+$', candidate):
                    # ลอง match ด้วย regex pattern
                    if re.search(r'^ต[้ั้][่-๋]?[\s]*$', candidate) or 'ต้น' in candidate:
                        return 'ต้น'
                    elif re.search(r'^ป[ลล][าๅ][ยใ]?[\s]*$', candidate) or 'ปลาย' in candidate:
                        return 'ปลาย'
                    elif 'ฤดูร้อน' in candidate:
                        return 'ฤดูร้อน'
        
        # Pattern 1b: หาในตาราง - มักอยู่บรรทัดสั้นๆ หลัง phone/email และก่อน year
        phone_email_found = False
        for i, line in enumerate(lines):
            if '@' in line or re.search(r'\b0\d{9}\b', line):
                phone_email_found = True
                continue
            
            if phone_email_found:
                candidate = line.strip()
                # ถ้าเจอตัวเลข 4 หลัก (year) ให้หยุด
                if re.search(r'\b(25\d{2}|26\d{2})\b', candidate):
                    break
                
                # ถ้าบรรทัดสั้นๆ มีตัวอักษรไทย
                if 1 <= len(candidate) <= 5:
                    if re.match(r'^[ก-๙\s]+$', candidate):
                        if re.search(r'ต้น', candidate):
                            return 'ต้น'
                        elif re.search(r'ปลาย', candidate):
                            return 'ปลาย'
                        elif re.search(r'ฤดูร้อน', candidate):
                            return 'ฤดูร้อน'
        
        # Pattern 2: หาในตาราง (หลัง department/field) - เวอร์ชันเดิม
        for i, line in enumerate(lines):
            # หาบรรทัดที่มี department (มีตัวอักษรไทย ไม่ใช่ชื่อคน ไม่ใช่ semester เอง)
            if re.search(r'[ก-ฮะ-์เ-ไ]', line) and len(line) > 5 and len(line) < 50:
                if 'นาย' not in line and 'นาง' not in line and line.strip() not in ['ต้น', 'ปลาย', 'ฤดูร้อน']:
                    # ดูบรรทัดถัดไป 2 บรรทัด
                    for j in range(i+1, min(i+3, len(lines))):
                        candidate = lines[j].strip()
                        if candidate in ['ต้น', 'ปลาย', 'ฤดูร้อน']:
                            return candidate
                        elif 'ภาคต้น' in candidate:
                            return 'ต้น'
                        elif 'ภาคปลาย' in candidate:
                            return 'ปลาย'
                        elif 'ภาคฤดูร้อน' in candidate:
                            return 'ฤดูร้อน'
        
        # Pattern 3: หาใน text ทั้งหมด (fallback)
        if re.search(r'\bภาคต้น\b|\bต้น\b', text):
            return "ต้น"
        elif re.search(r'\bภาคปลาย\b|\bปลาย\b', text):
            return "ปลาย"
        elif re.search(r'\bภาคฤดูร้อน\b|\bฤดูร้อน\b', text):
            return "ฤดูร้อน"
        return None
    
    def _extract_academic_year(self, text: str) -> Optional[str]:
        """หาปีการศึกษา - ให้ความสำคัญกับค่าที่อยู่ใกล้ข้อมูลนิสิตในตาราง"""
        lines = text.split('\n')
        
        # Pattern 1: หาปีการศึกษาหลัง "Year of Study" หรือ "Faculty" (แบบตาราง)
        # มักจะอยู่ห่างจาก label ประมาณ 5-15 บรรทัด
        for i, line in enumerate(lines):
            if any(kw in line.lower() for kw in ['year of study', 'faculty']):
                # ดูบรรทัดถัดไป 15 บรรทัด (เพราะข้อมูลอาจอยู่ไกล)
                years_found = []
                for j in range(i+1, min(i+16, len(lines))):
                    line_content = lines[j].strip()
                    # หาเลข 4 หลักขึ้นต้นด้วย 25 หรือ 26
                    match = re.search(r'\b(25\d{2}|26\d{2})\b', line_content)
                    if match:
                        year = match.group(1)
                        # ตรวจสอบว่าไม่ใช่วันที่ (เช่น 17 ก.ค. 2557)
                        prev_line = lines[max(0,j-1)]
                        is_date = bool(re.search(r'\d{1,2}\s*[\./]\s*\d{1,2}', prev_line) or
                                      re.search(r'ก\.ค\.|ม\.ค\.|มี\.ค\.|พ\.ค\.|ก\.พ\.|มี\.ค\.', prev_line))
                        if not is_date:
                            years_found.append((j, year))
                
                # ถ้าเจอหลายปี ให้เอาอันที่อยู่หลังสุด (มักจะใกล้ข้อมูลนิสิตมากกว่า)
                if years_found:
                    # กรองเอาเฉพาะปีที่มากกว่า 2560 (ปีปัจจุบัน)
                    recent_years = [(pos, yr) for pos, yr in years_found if int(yr) >= self.MIN_ACADEMIC_YEAR]
                    if recent_years:
                        return recent_years[-1][1]
                    return years_found[-1][1]
        
        # Pattern 2: หา "ปีการศึกษา" ตามปกติ
        pattern = r'ปีการศึกษา[:\s]*(\d{4})'
        match = re.search(pattern, text)
        if match:
            return match.group(1)
        
        # Pattern 3: หาเลข 4 หลักที่ขึ้นต้นด้วย 25xx หรือ 26xx (ไม่ใช่วันที่)
        # ข้ามวันที่ในรูปแบบต่างๆ
        text_no_dates = re.sub(r'\d{1,2}\s*[\.\-/]\s*\d{1,2}\s*[\.\-/]\s*\d{4}', '', text)
        text_no_dates = re.sub(r'\d{1,2}\s+(?:ก\.ค\.|ม\.ค\.|มี\.ค\.|พ\.ค\.|ก\.พ\.|มิ\.ย\.|ก\.ย\.|ต\.ค\.|พ\.ย\.|ธ\.ค\.)\s*\.?\s*\d{4}', '', text_no_dates)
        pattern2 = r'\b(25\d{2}|26\d{2})\b'
        match2 = re.search(pattern2, text_no_dates)
        if match2:
            return match2.group(1)
        
        return None
    
    def _extract_amount(self, text: str) -> Optional[float]:
        """หาจำนวนเงินที่ขอคืน (รองรับทั้งไทยและอังกฤษ) - แยกระหว่างจำนวนเงินและหน่วยกิต"""
        
        # ลบข้อความที่เป็น credits/หน่วยกิต ออกก่อน เพื่อไม่ให้สับสน
        text_clean = re.sub(r'\d+\s*(?:หน่วยกิต|Credits?|credit)', '', text, flags=re.IGNORECASE)
        
        # Pattern สำหรับจำนวนเงิน (ต้องมี บาท/Baht หรือเป็นจำนวนเงินที่มีจุดทศนิยม 2 ตำแหน่ง)
        money_patterns = [
            # จำนวนเงินที่มี บาท ตามหลัง (ลำดับความสำคัญสูงสุด)
            r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:บาท|baht|THB)',
            # เงิน...บาท
            r'(?:เงิน|จำนวนเงิน|amount)[^0-9]*(\d[\d,]*(?:\.\d{2})?)\s*(?:บาท|baht)',
            # ค่าลงทะเบียน...บาท
            r'(?:ค่าลงทะเบียน|tuition\s*fee)[^0-9]*(\d[\d,]*(?:\.\d{2})?)',
            # เลขที่มีทศนิยม 2 ตำแหน่ง (น่าจะเป็นเงิน)
            r'\b(\d{1,3}(?:,\d{3})*\.\d{2})\b',
        ]
        
        for pattern in money_patterns:
            match = re.search(pattern, text_clean, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(",", "")
                try:
                    amount = float(amount_str)
                    # ตรวจสอบว่าเป็นเงินที่สมเหตุสมผล (ไม่ใช่ credits)
                    if amount >= self.MIN_REFUND_AMOUNT:  # ค่าลงทะเบียนมักจะไม่ต่ำกว่า 100 บาท
                        return amount
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse amount '{amount_str}': {e}")
                    continue
        
        return None
    
    def _extract_bank(self, text: str) -> Optional[str]:
        """หาชื่อธนาคาร (รองรับทั้งไทยและอังกฤษ)"""
        banks = [
            # Thai
            "กสิกรไทย", "กรุงไทย", "กรุงเทพ", "ไทยพาณิชย์",
            "ทหารไทยธนชาต", "กรุงศรี", "ออมสิน", "ธ.ก.ส.",
            # English
            "kasikorn", "kbank", "scb", "bangkok bank", "krungsri",
            "ktb", "tmb", "gsb"
        ]
        text_lower = text.lower()
        for bank in banks:
            if bank.lower() in text_lower:
                return bank
        return None


class Form20Extractor:
    """Extract ข้อมูลจากแบบ 20 - ลงทะเบียนเพิ่ม"""
    
    def extract(self, text: str) -> dict:
        """Extract fields จากข้อความ"""
        data = {
            "student_id": self._extract_student_id(text),
            "name": self._extract_name(text),
            "faculty": self._extract_faculty(text),
            "courses": self._extract_courses(text),
            "reason": self._extract_reason(text),
        }
        return data
    
    def _extract_student_id(self, text: str) -> Optional[str]:
        # รองรับรหัสปี 50-79 (พ.ศ. 2550-2579)
        pattern = r'\b[5-7][0-9]{9}\b'
        match = re.search(pattern, text)
        return match.group(0) if match else None
    
    def _extract_name(self, text: str) -> Optional[str]:
        """หาชื่อ-นามสกุล (รองรับทั้งไทยและอังกฤษ)"""
        patterns = [
            # English patterns
            r'[Nn]ame[:\s]+([A-Za-z]+\s+[A-Za-z]+)',
            r'[Nn]ame[:\s]+([A-Za-z\s]+?)(?:\n|$)',
            # Thai patterns
            r'ชื่อ[:\s]*(.+?)(?:\s*นามสกุล|\s*รหัส|\n)',
            r'นาย\s*(\S+\s+\S+)',
            r'นางสาว\s*(\S+\s+\S+)',
            r'นาง\s*(\S+\s+\S+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                name = re.sub(r'[^\w\s]', '', name).strip()
                if len(name) > 2:
                    return name
        return None
    
    def _extract_faculty(self, text: str) -> Optional[str]:
        """หาคณะ (รองรับทั้งไทยและอังกฤษ)"""
        patterns = [
            r'[Ff]aculty[:\s]+([A-Za-z]+)',
            r'คณะ[:\s]*(\S+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return None
    
    def _extract_courses(self, text: str) -> List[dict]:
        """หารายวิชา"""
        courses = []
        
        # Pattern สำหรับรหัสวิชา (8 หลัก เช่น 01418111)
        course_pattern = r'\b(\d{8})\b'
        matches = re.findall(course_pattern, text)
        
        for course_code in matches:
            courses.append({
                "course_code": course_code,
                "course_name": None,  # ต้อง map จาก database
                "credits": None,
                "section": None,
                "instructor": None
            })
        
        return courses
    
    def _extract_reason(self, text: str) -> Optional[str]:
        """หาเหตุผล"""
        pattern = r'(?:เหตุผล|สาเหตุ)[:\s]*(.+?)(?:\n|$)'
        match = re.search(pattern, text)
        return match.group(1).strip() if match else None


class Form4Extractor:
    """Extract ข้อมูลจากแบบ 4 - เรียนควบ"""
    
    def extract(self, text: str) -> dict:
        """Extract fields จากข้อความ"""
        data = {
            "student_id": self._extract_student_id(text),
            "name": self._extract_name(text),
            "faculty": self._extract_faculty(text),
            "prerequisite_course": self._extract_prerequisite(text),
            "continuing_course": self._extract_continuing(text),
            "reason": self._extract_reason(text),
        }
        return data
    
    def _extract_student_id(self, text: str) -> Optional[str]:
        # รองรับรหัสปี 50-79 (พ.ศ. 2550-2579)
        pattern = r'\b[5-7][0-9]{9}\b'
        match = re.search(pattern, text)
        return match.group(0) if match else None
    
    def _extract_name(self, text: str) -> Optional[str]:
        """หาชื่อ-นามสกุล (รองรับทั้งไทยและอังกฤษ)"""
        patterns = [
            # English patterns
            r'[Nn]ame[:\s]+([A-Za-z]+\s+[A-Za-z]+)',
            r'[Nn]ame[:\s]+([A-Za-z\s]+?)(?:\n|$)',
            # Thai patterns
            r'ชื่อ[:\s]*(.+?)(?:\s*นามสกุล|\s*รหัส|\n)',
            r'นาย\s*(\S+\s+\S+)',
            r'นางสาว\s*(\S+\s+\S+)',
            r'นาง\s*(\S+\s+\S+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                name = re.sub(r'[^\w\s]', '', name).strip()
                if len(name) > 2:
                    return name
        return None
    
    def _extract_faculty(self, text: str) -> Optional[str]:
        """หาคณะ (รองรับทั้งไทยและอังกฤษ)"""
        patterns = [
            r'[Ff]aculty[:\s]+([A-Za-z]+)',
            r'คณะ[:\s]*(\S+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return None
    
    def _extract_prerequisite(self, text: str) -> Optional[dict]:
        """หาวิชาบังคับก่อน"""
        # หารหัสวิชาแรกที่เจอ
        pattern = r'\b(\d{8})\b'
        matches = re.findall(pattern, text)
        if len(matches) >= 1:
            return {
                "course_code": matches[0],
                "course_name": None,
                "credits": None,
                "instructor": None
            }
        return None
    
    def _extract_continuing(self, text: str) -> Optional[dict]:
        """หาวิชาต่อเนื่อง"""
        pattern = r'\b(\d{8})\b'
        matches = re.findall(pattern, text)
        if len(matches) >= 2:
            return {
                "course_code": matches[1],
                "course_name": None,
                "credits": None,
                "section": None,
                "instructor": None
            }
        return None
    
    def _extract_reason(self, text: str) -> Optional[str]:
        pattern = r'(?:เหตุผล|สาเหตุ)[:\s]*(.+?)(?:\n|$)'
        match = re.search(pattern, text)
        return match.group(1).strip() if match else None


# ==========================================
# Confidence Threshold Configuration
# ==========================================

class ConfidenceConfig:
    """Configuration สำหรับ confidence thresholds"""
    
    # OCR Confidence Thresholds
    OCR_HIGH_CONFIDENCE = 0.85      # สูง - ดำเนินการอัตโนมัติได้
    OCR_MEDIUM_CONFIDENCE = 0.70    # กลาง - ควรตรวจสอบ
    OCR_LOW_CONFIDENCE = 0.50       # ต่ำ - ต้อง manual review
    
    # Classification Confidence
    CLASSIFICATION_THRESHOLD = 0.80  # ต้องมั่นใจ 80% ว่าจำแนกถูก
    
    # Field Extraction - Required fields per form type
    REQUIRED_FIELDS = {
        "18": ["student_id", "name"],  # ฟอร์มขอคืนเงิน
        "20": ["student_id", "name"],  # ฟอร์มลงทะเบียนเพิ่ม
        "4": ["student_id", "name"],   # ฟอร์มเรียนควบ
    }


class ReviewAnalyzer:
    """
    วิเคราะห์ว่าเอกสารต้อง manual review หรือไม่
    
    เงื่อนไขที่ต้อง manual review:
    1. OCR confidence ต่ำกว่า threshold
    2. จำแนกประเภทไม่ได้หรือ confidence ต่ำ  
    3. Extract required fields ไม่ครบ
    4. พบ pattern ที่น่าสงสัย (เช่น ลายมือที่อ่านไม่ชัด)
    """
    
    def __init__(self, config: ConfidenceConfig = None):
        self.config = config or ConfidenceConfig()
    
    def analyze(
        self, 
        ocr_confidence: float,
        classification_result: tuple,  # (form_type, confidence)
        extracted_data: dict
    ) -> dict:
        """
        วิเคราะห์และให้ผลลัพธ์ว่าต้อง review หรือไม่
        
        Returns:
            dict: {
                "needs_review": bool,
                "review_reasons": list[str],
                "confidence_level": "high" | "medium" | "low",
                "auto_process_allowed": bool,
                "review_priority": "urgent" | "normal" | "low",
                "details": dict
            }
        """
        review_reasons = []
        
        form_type, class_confidence = classification_result
        
        # 1. Check OCR Confidence
        ocr_status = self._check_ocr_confidence(ocr_confidence)
        if ocr_status["needs_review"]:
            review_reasons.append(ocr_status["reason"])
        
        # 2. Check Classification Confidence
        class_status = self._check_classification(form_type, class_confidence)
        if class_status["needs_review"]:
            review_reasons.append(class_status["reason"])
        
        # 3. Check Required Fields
        fields_status = self._check_required_fields(form_type, extracted_data)
        if fields_status["needs_review"]:
            review_reasons.extend(fields_status["reasons"])
        
        # 4. Check for suspicious patterns
        pattern_status = self._check_suspicious_patterns(extracted_data)
        if pattern_status["needs_review"]:
            review_reasons.extend(pattern_status["reasons"])
        
        # Determine overall status
        needs_review = len(review_reasons) > 0
        confidence_level = self._get_confidence_level(ocr_confidence)
        
        return {
            "needs_review": needs_review,
            "review_reasons": review_reasons,
            "confidence_level": confidence_level,
            "auto_process_allowed": not needs_review and confidence_level == "high",
            "review_priority": self._get_review_priority(review_reasons, ocr_confidence),
            "details": {
                "ocr_confidence": round(ocr_confidence, 3),
                "classification_confidence": round(class_confidence, 3),
                "form_type": form_type,
                "missing_fields": fields_status.get("missing_fields", []),
                "total_issues": len(review_reasons)
            }
        }
    
    def _check_ocr_confidence(self, confidence: float) -> dict:
        """ตรวจสอบ OCR confidence"""
        if confidence < self.config.OCR_LOW_CONFIDENCE:
            return {
                "needs_review": True,
                "reason": f"⚠️ OCR confidence ต่ำมาก ({confidence:.1%}) - อาจเป็นลายมือหรือภาพไม่ชัด"
            }
        elif confidence < self.config.OCR_MEDIUM_CONFIDENCE:
            return {
                "needs_review": True,
                "reason": f"⚠️ OCR confidence ต่ำ ({confidence:.1%}) - ควรตรวจสอบความถูกต้อง"
            }
        return {"needs_review": False}
    
    def _check_classification(self, form_type: str, confidence: float) -> dict:
        """ตรวจสอบการจำแนกประเภท"""
        if form_type == "unknown":
            return {
                "needs_review": True,
                "reason": "❌ ไม่สามารถจำแนกประเภทเอกสารได้"
            }
        elif confidence < self.config.CLASSIFICATION_THRESHOLD:
            return {
                "needs_review": True,
                "reason": f"⚠️ ไม่แน่ใจในประเภทเอกสาร (confidence: {confidence:.1%})"
            }
        return {"needs_review": False}
    
    def _check_required_fields(self, form_type: str, extracted_data: dict) -> dict:
        """ตรวจสอบว่า extract required fields ได้ครบหรือไม่"""
        required = self.config.REQUIRED_FIELDS.get(form_type, [])
        missing_fields = []
        
        for field in required:
            value = extracted_data.get(field)
            if value is None or value == "" or value == []:
                missing_fields.append(field)
        
        if missing_fields:
            return {
                "needs_review": True,
                "reasons": [f"❌ ไม่พบข้อมูล: {', '.join(missing_fields)}"],
                "missing_fields": missing_fields
            }
        return {"needs_review": False, "missing_fields": []}
    
    def _check_suspicious_patterns(self, extracted_data: dict) -> dict:
        """ตรวจสอบ patterns ที่น่าสงสัย"""
        reasons = []
        
        # Check student ID format
        student_id = extracted_data.get("student_id")
        if student_id:
            if not student_id.isdigit():
                reasons.append("⚠️ รหัสนิสิตมีตัวอักษรแปลก - อาจ OCR อ่านผิด")
            elif len(student_id) != 10:
                reasons.append(f"⚠️ รหัสนิสิตไม่ใช่ 10 หลัก ({len(student_id)} หลัก)")
        
        # Check name for suspicious characters
        name = extracted_data.get("name")
        if name:
            if re.search(r'[0-9@#$%^&*]', name):
                reasons.append("⚠️ ชื่อมีตัวอักษรแปลก - อาจ OCR อ่านผิด")
        
        return {
            "needs_review": len(reasons) > 0,
            "reasons": reasons
        }
    
    def _get_confidence_level(self, ocr_confidence: float) -> str:
        """แปลง confidence เป็น level"""
        if ocr_confidence >= self.config.OCR_HIGH_CONFIDENCE:
            return "high"
        elif ocr_confidence >= self.config.OCR_MEDIUM_CONFIDENCE:
            return "medium"
        else:
            return "low"
    
    def _get_review_priority(self, reasons: list, ocr_confidence: float) -> str:
        """กำหนดลำดับความสำคัญในการ review"""
        if len(reasons) >= 3 or ocr_confidence < self.config.OCR_LOW_CONFIDENCE:
            return "urgent"
        elif len(reasons) >= 1:
            return "normal"
        else:
            return "low"


def process_document_with_review(
    file_bytes: bytes, 
    content_type: str
) -> dict:
    """
    ฟังก์ชันหลักสำหรับ process เอกสารพร้อมวิเคราะห์ว่าต้อง review หรือไม่
    
    Returns:
        dict: {
            "ocr_text": str,
            "ocr_details": list,
            "ocr_confidence": float,
            "form_type": str,
            "classification_confidence": float,
            "extracted_data": dict,
            "review_analysis": dict  # ผลการวิเคราะห์ว่าต้อง review หรือไม่
        }
    """
    # 1. OCR
    ocr_service = get_ocr_service()
    ocr_text, ocr_details, ocr_confidence = ocr_service.ocr_document(file_bytes, content_type)
    
    # 2. Classify
    classifier = get_classifier()
    form_type, class_confidence = classifier.classify(ocr_text)
    
    # 3. Extract
    extractor = get_extractor(form_type)
    extracted_data = extractor.extract(ocr_text) if extractor else {}
    
    # 4. Analyze for review
    analyzer = ReviewAnalyzer()
    review_analysis = analyzer.analyze(
        ocr_confidence=ocr_confidence,
        classification_result=(form_type, class_confidence),
        extracted_data=extracted_data
    )
    
    return {
        "ocr_text": ocr_text,
        "ocr_details": ocr_details,
        "ocr_confidence": ocr_confidence,
        "form_type": form_type,
        "classification_confidence": class_confidence,
        "extracted_data": extracted_data,
        "review_analysis": review_analysis
    }


# Singleton instance สำหรับใช้งานใน API
_ocr_service = None
_classifier = None
_extractors = {}
_review_analyzer = None

def get_ocr_service():
    """
    Get OCR service instance - GEMINI VISION ONLY
    
    Returns:
        GeminiVisionOCR instance (primary and only engine)
    Raises:
        RuntimeError: If Gemini is not available and EasyOCR is not installed
    """
    global _ocr_service
    
    if _ocr_service is None:
        # Use Gemini Vision as the only OCR engine
        try:
            from gemini_vision_service import get_gemini_vision_ocr, is_gemini_available
            if is_gemini_available():
                _ocr_service = get_gemini_vision_ocr()
                logger.info("✅ Using Gemini Vision as OCR engine")
                print("✅ Using Gemini Vision as OCR engine")
            else:
                raise RuntimeError(
                    "❌ No OCR engine available! "
                    "Set GEMINI_API_KEY environment variable."
                )
        except ImportError as e:
            raise RuntimeError(
                f"❌ Gemini import failed: {e}. "
                f"Check google-genai is installed."
            )
        except Exception as e:
            raise RuntimeError(
                f"❌ Gemini init failed: {e}. "
                f"Check GEMINI_API_KEY is valid."
            )
    
    return _ocr_service

def get_classifier() -> DocumentClassifier:
    """Get singleton classifier instance"""
    global _classifier
    if _classifier is None:
        _classifier = DocumentClassifier()
    return _classifier

def get_extractor(form_type: str):
    """Get extractor for specific form type"""
    global _extractors
    if form_type not in _extractors:
        if form_type == "18":
            _extractors[form_type] = Form18Extractor()
        elif form_type == "20":
            _extractors[form_type] = Form20Extractor()
        elif form_type == "4":
            _extractors[form_type] = Form4Extractor()
    return _extractors.get(form_type)

def get_review_analyzer() -> ReviewAnalyzer:
    """Get singleton review analyzer instance"""
    global _review_analyzer
    if _review_analyzer is None:
        _review_analyzer = ReviewAnalyzer()
    return _review_analyzer
