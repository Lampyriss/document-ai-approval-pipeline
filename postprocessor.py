"""
OCR Postprocessing Module
=========================

Purpose: ปรับปรุงความแม่นยำของ OCR ด้วย:
- Error correction (O→0, l→1, S→5)
- Format validation
- Text cleaning
"""

import re
from typing import Optional


class OCRPostprocessor:
    """Postprocessing for OCR results to improve accuracy"""
    
    def __init__(self):
        # Common OCR errors mapping
        self.number_corrections = {
            'O': '0', 'o': '0',  # O → 0
            'l': '1', 'I': '1',  # l, I → 1
            'S': '5', 's': '5',  # S → 5 (in number context)
            'Z': '2', 'z': '2',  # Z → 2
        }
        
        # Thai name prefixes to remove
        self.name_prefixes = ['นาย', 'นาง', 'นางสาว', 'เด็กชาย', 'เด็กหญิง', 'ด.ช.', 'ด.ญ.']
        
        # Common Thai spelling errors
        self.spell_corrections = {
            'วิศกรรม': 'วิศวกรรม',
            'ศาสร์': 'ศาสตร์',
            'มหาดทยาลัย': 'มหาวิทยาลัย',
            'เกษตศาสร์': 'เกษตรศาสตร์',
        }
    
    def fix_student_id(self, text: str) -> str:
        """
        แก้ไขรหัสนิสิต
        - ลบทุกอย่างที่ไม่ใช่ตัวเลข
        - แก้ O→0, l→1
        - ตรวจสอบว่าเป็น 10 หลัก
        """
        if text is None:
            return ""
        # แปลงเป็น string ก่อน (กรณี int หรือ float)
        text = str(text)
        if not text:
            return ""
        
        # แก้ common errors ก่อน
        for wrong, correct in self.number_corrections.items():
            text = text.replace(wrong, correct)
        
        # เก็บเฉพาะตัวเลข
        text = re.sub(r'\D', '', text)
        
        # ตรวจสอบความยาว
        if len(text) == 10:
            return text
        elif len(text) > 10:
            # ถ้ายาวเกิน เอา 10 ตัวแรก
            return text[:10]
        else:
            # ถ้าสั้นเกิน return ตามเดิม
            return text
    
    def fix_phone(self, text: str) -> str:
        """
        แก้ไขเบอร์โทรศัพท์
        - Format: 0XX-XXX-XXXX
        - ต้องขึ้นต้นด้วย 0
        - ต้องเป็น 10 หลัก
        """
        if text is None:
            return ""
        text = str(text)
        if not text:
            return ""
        
        # ลบทุกอย่างที่ไม่ใช่ตัวเลข
        text = re.sub(r'\D', '', text)
        
        # ตรวจสอบว่าเป็น 10 หลักและขึ้นต้นด้วย 0
        if len(text) == 10 and text.startswith('0'):
            return f"{text[:3]}-{text[3:6]}-{text[6:]}"
        elif len(text) == 9:
            # ถ้าเป็น 9 หลัก ลองเติม 0 ข้างหน้า
            text = '0' + text
            return f"{text[:3]}-{text[3:6]}-{text[6:]}"
        
        return text
    
    def fix_id_card(self, text: str) -> str:
        """
        แก้ไขเลขบัตรประชาชน
        - ต้องเป็น 13 หลัก
        - แก้ O→0, l→1
        """
        if text is None:
            return ""
        text = str(text)
        if not text:
            return ""
        
        # แก้ common errors
        for wrong, correct in self.number_corrections.items():
            text = text.replace(wrong, correct)
        
        # เก็บเฉพาะตัวเลข
        text = re.sub(r'\D', '', text)
        
        # ตรวจสอบความยาว
        if len(text) == 13:
            return text
        elif len(text) > 13:
            return text[:13]
        
        return text
    
    def clean_name(self, text: str) -> str:
        """
        ทำความสะอาดชื่อ-นามสกุล
        - ลบคำนำหน้า (นาย, นาง, นางสาว)
        - ลบเลขที่
        - จำกัด 4 คำ
        """
        if text is None:
            return ""
        text = str(text)
        if not text:
            return ""
        
        # ลบคำนำหน้า
        for prefix in self.name_prefixes:
            text = re.sub(rf'^{prefix}\s+', '', text, flags=re.IGNORECASE)
        
        # ลบ "เลขที่ XX"
        text = re.sub(r'เลขที่\s*\d+', '', text)
        
        # ลบช่องว่างเกิน
        text = re.sub(r'\s+', ' ', text).strip()
        
        # จำกัด 4 คำ
        words = text.split()
        if len(words) > 4:
            text = ' '.join(words[:4])
        
        # จำกัดความยาว 80 ตัวอักษร
        if len(text) > 80:
            text = text[:80].strip()
        
        return text
    
    def clean_faculty(self, text: str) -> str:
        """
        ทำความสะอาดชื่อคณะ
        - ลบคำว่า "คณะ"
        - จำกัดความยาว
        """
        if text is None:
            return ""
        text = str(text)
        if not text:
            return ""
        
        # ลบคำว่า "คณะ" ถ้ามี
        text = re.sub(r'^คณะ\s*', '', text)
        
        # แก้การสะกดผิดทั่วไป
        for wrong, correct in self.spell_corrections.items():
            text = text.replace(wrong, correct)
        
        # จำกัดความยาว 80 ตัวอักษร
        if len(text) > 80:
            text = text[:80].strip()
        
        return text.strip()
    
    def clean_department(self, text: str) -> str:
        """
        ทำความสะอาดชื่อสาขา/ภาควิชา
        - ลบคำว่า "ภาควิชา", "สาขา"
        - จำกัดความยาว
        """
        if text is None:
            return ""
        text = str(text)
        if not text:
            return ""
        
        # ลบคำนำหน้า
        text = re.sub(r'^(ภาควิชา|สาขาวิชา|สาขา)\s*', '', text)
        
        # แก้การสะกดผิดทั่วไป
        for wrong, correct in self.spell_corrections.items():
            text = text.replace(wrong, correct)
        
        # จำกัดความยาว 100 ตัวอักษร
        if len(text) > 100:
            text = text[:100].strip()
        
        return text.strip()
    
    def validate_email(self, text: str) -> str:
        """
        ตรวจสอบและทำความสะอาดอีเมล
        """
        if text is None:
            return ""
        text = str(text)
        if not text:
            return ""
        
        # ลบช่องว่าง
        text = text.strip().replace(' ', '')
        
        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(email_pattern, text):
            return text.lower()
        
        return text
    
    def fix_amount(self, text: str) -> str:
        """
        แก้ไขจำนวนเงิน
        - เก็บเฉพาะตัวเลขและจุดทศนิยม
        - แปลงเป็น float
        """
        if text is None:
            return ""
        text = str(text)
        if not text:
            return ""
        
        # ลบทุกอย่างยกเว้นตัวเลขและจุด
        text = re.sub(r'[^\d.]', '', text)
        
        try:
            # แปลงเป็นตัวเลข
            amount = float(text)
            # ถ้าเป็นจำนวนเต็ม ไม่ต้องมีจุด
            if amount == int(amount):
                return str(int(amount))
            return str(amount)
        except (ValueError, TypeError):
            return text
    
    def process_all(self, data: dict) -> dict:
        """
        ประมวลผลทุกฟิลด์ (safely handle None values)
        """
        processed = data.copy()
        
        # Process each field (skip if None or empty)
        if processed.get('student_id'):
            processed['student_id'] = self.fix_student_id(processed['student_id'])
        
        if processed.get('phone'):
            processed['phone'] = self.fix_phone(processed['phone'])
        
        if processed.get('id_card'):
            processed['id_card'] = self.fix_id_card(processed['id_card'])
        
        if processed.get('name'):
            processed['name'] = self.clean_name(processed['name'])
        
        if processed.get('faculty'):
            processed['faculty'] = self.clean_faculty(processed['faculty'])
        
        if processed.get('department'):
            processed['department'] = self.clean_department(processed['department'])
        
        if processed.get('email'):
            processed['email'] = self.validate_email(processed['email'])
        
        if processed.get('refund_amount'):
            processed['refund_amount'] = self.fix_amount(processed['refund_amount'])
        
        if processed.get('advisor'):
            processed['advisor'] = self.clean_name(processed['advisor'])
        
        return processed


# Global instance
postprocessor = OCRPostprocessor()
