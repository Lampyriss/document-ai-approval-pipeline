# Template-Based Form Extractor
# ใช้ YAML templates สำหรับ extract ข้อมูลจากฟอร์ม

"""
Template Extractor - ใช้ YAML configuration แทน hardcoded regex

ประโยชน์:
1. แก้ไข patterns ได้โดยไม่ต้องแก้ code
2. เพิ่ม form ใหม่ได้ง่าย
3. ทดสอบ patterns ได้แยกต่างหาก
"""

import yaml
import re
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class TemplateExtractor:
    """Extract form data using YAML templates"""
    
    def __init__(self, template_path: str = None):
        """
        Initialize with template file
        
        Args:
            template_path: Path to YAML template file
        """
        if template_path is None:
            template_path = Path(__file__).parent / "form_templates.yaml"
        
        self.template_path = Path(template_path)
        self.templates = self._load_templates()
        self.settings = self.templates.get("settings", {})
        
    def _load_templates(self) -> Dict:
        """Load YAML template file"""
        try:
            with open(self.template_path, 'r', encoding='utf-8') as f:
                templates = yaml.safe_load(f)
            logger.info(f"✅ Loaded templates from {self.template_path}")
            return templates
        except Exception as e:
            logger.error(f"❌ Failed to load templates: {e}")
            return {}
    
    def reload_templates(self):
        """Reload templates from file (for hot-reload)"""
        self.templates = self._load_templates()
        self.settings = self.templates.get("settings", {})
    
    def classify(self, text: str) -> Tuple[str, float]:
        """
        จำแนกประเภทฟอร์มจาก keywords
        
        Args:
            text: ข้อความจาก OCR
            
        Returns:
            Tuple of (form_type, confidence)
        """
        text_lower = text.lower()
        best_match = ("unknown", 0.0)
        
        for form_key, form_config in self.templates.items():
            if form_key == "settings":
                continue
                
            if not isinstance(form_config, dict):
                continue
                
            keywords = form_config.get("keywords", [])
            if not keywords:
                continue
            
            # นับจำนวน keywords ที่ match
            matches = sum(1 for kw in keywords if kw.lower() in text_lower)
            
            if matches > 0:
                # คำนวณ confidence จากจำนวน matches
                confidence = min(1.0, matches / len(keywords) * 2)
                
                # Check for exact pattern match (higher confidence)
                form_num = form_key.replace("form_", "")
                if re.search(rf'registrar[-\s_]*{form_num}', text_lower):
                    confidence = 1.0
                
                if confidence > best_match[1]:
                    best_match = (form_num, confidence)
        
        return best_match
    
    def extract(self, text: str, form_type: str) -> Dict[str, Any]:
        """
        Extract fields จากข้อความตาม template
        
        Args:
            text: ข้อความจาก OCR
            form_type: ประเภทฟอร์ม (4, 18, 20)
            
        Returns:
            Dict of extracted fields
        """
        form_key = f"form_{form_type}"
        template = self.templates.get(form_key, {})
        
        if not template:
            logger.warning(f"No template found for form type: {form_type}")
            return {}
        
        fields_config = template.get("fields", {})
        extracted = {}
        
        for field_name, field_config in fields_config.items():
            patterns = field_config.get("patterns", [])
            field_type = field_config.get("type", "string")
            
            value = self._extract_field(text, patterns, field_type)
            
            if value is not None:
                extracted[field_name] = value
            elif field_config.get("required", False):
                # ใส่ค่า None สำหรับ required fields ที่หาไม่เจอ
                extracted[field_name] = None
        
        return extracted
    
    def _extract_field(self, text: str, patterns: List[str], field_type: str) -> Optional[Any]:
        """
        Extract single field using patterns
        
        Args:
            text: ข้อความที่จะค้นหา
            patterns: List of regex patterns
            field_type: ประเภทของ field (string, float, list, object)
            
        Returns:
            Extracted value or None
        """
        for pattern in patterns:
            try:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                
                if match:
                    if field_type == "list":
                        # หา matches ทั้งหมด
                        all_matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
                        return self._process_list_matches(all_matches)
                    
                    elif field_type == "float":
                        value = match.group(1)
                        # ลบ comma และแปลงเป็น float
                        return float(value.replace(",", ""))
                    
                    elif field_type == "object":
                        # Return all captured groups as dict
                        return {f"group_{i}": g for i, g in enumerate(match.groups())}
                    
                    else:
                        # String type - return first captured group
                        value = match.group(1) if match.groups() else match.group(0)
                        return value.strip() if value else None
                        
            except Exception as e:
                logger.warning(f"Pattern error '{pattern}': {e}")
                continue
        
        return None
    
    def _process_list_matches(self, matches: List) -> List[Dict]:
        """Process list of matches into structured data"""
        results = []
        for match in matches:
            if isinstance(match, tuple):
                # Multiple capture groups
                if len(match) >= 3:
                    results.append({
                        "course_code": match[0],
                        "course_name": match[1].strip() if match[1] else None,
                        "credits": int(match[2]) if match[2] else None
                    })
                elif len(match) >= 1:
                    results.append({"course_code": match[0]})
            else:
                results.append({"course_code": match})
        return results
    
    def extract_with_confidence(self, text: str, form_type: str) -> Tuple[Dict, float]:
        """
        Extract fields พร้อม confidence score
        
        Returns:
            Tuple of (extracted_data, confidence_score)
        """
        template = self.templates.get(f"form_{form_type}", {})
        fields_config = template.get("fields", {})
        
        extracted = self.extract(text, form_type)
        
        # คำนวณ confidence จากจำนวน fields ที่หาเจอ
        required_fields = [k for k, v in fields_config.items() if v.get("required", False)]
        optional_fields = [k for k, v in fields_config.items() if not v.get("required", False)]
        
        required_found = sum(1 for f in required_fields if extracted.get(f) is not None)
        optional_found = sum(1 for f in optional_fields if extracted.get(f) is not None)
        
        # Required fields มีน้ำหนักมากกว่า
        if required_fields:
            required_score = required_found / len(required_fields)
        else:
            required_score = 1.0
            
        if optional_fields:
            optional_score = optional_found / len(optional_fields)
        else:
            optional_score = 1.0
        
        # Weighted average: required 70%, optional 30%
        confidence = required_score * 0.7 + optional_score * 0.3
        
        return extracted, confidence
    
    def get_available_forms(self) -> List[Dict]:
        """Get list of available form templates"""
        forms = []
        for key, config in self.templates.items():
            if key.startswith("form_") and isinstance(config, dict):
                form_num = key.replace("form_", "")
                forms.append({
                    "form_type": form_num,
                    "name": config.get("name", ""),
                    "name_en": config.get("name_en", ""),
                    "fields": list(config.get("fields", {}).keys())
                })
        return forms


# Singleton instance
_template_extractor: Optional[TemplateExtractor] = None


def get_template_extractor() -> TemplateExtractor:
    """Get or create singleton TemplateExtractor instance"""
    global _template_extractor
    if _template_extractor is None:
        _template_extractor = TemplateExtractor()
    return _template_extractor


# ===== Test Function =====
if __name__ == "__main__":
    # ทดสอบ
    extractor = TemplateExtractor()
    
    print("📋 Available Forms:")
    for form in extractor.get_available_forms():
        print(f"  - Form {form['form_type']}: {form['name']}")
    
    # ทดสอบ classification
    test_text = """
    Registrar-18
    มหาวิทยาลัยเกษตรศาสตร์
    ขอคืนเงินค่าธรรมเนียมการศึกษา
    รหัสนิสิต: 6410500001
    ชื่อ: นายสมชาย ใจดี
    คณะ: วิศวกรรมศาสตร์
    จำนวนเงิน: 15,000 บาท
    ธนาคาร: กสิกรไทย
    เลขที่บัญชี: 123-4-56789-0
    """
    
    form_type, confidence = extractor.classify(test_text)
    print(f"\n🔍 Classification: Form {form_type} (confidence: {confidence:.2%})")
    
    extracted, extract_conf = extractor.extract_with_confidence(test_text, form_type)
    print(f"\n📄 Extracted Data (confidence: {extract_conf:.2%}):")
    for key, value in extracted.items():
        print(f"  {key}: {value}")
