# Database Storage Module
# เก็บผล OCR ลง SQLite Database

"""
SQLite Storage Module สำหรับเก็บผล OCR
- บันทึกทุกการประมวลผล
- ดูประวัติย้อนหลังได้
- Export เป็น CSV ได้
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
import os
import logging

logger = logging.getLogger(__name__)

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), "ocr_results.db")


class OCRDatabase:
    """SQLite Database for storing OCR results"""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """สร้างตารางถ้ายังไม่มี"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # สร้างตาราง ocr_results
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ocr_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                form_type TEXT,
                form_confidence REAL,
                ocr_confidence REAL,
                student_id TEXT,
                student_name TEXT,
                faculty TEXT,
                department TEXT,
                raw_text TEXT,
                extracted_data TEXT,
                review_needed INTEGER DEFAULT 0,
                review_reasons TEXT,
                processing_time_ms INTEGER,
                success INTEGER DEFAULT 1,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # สร้างตาราง processing_stats
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processing_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE UNIQUE,
                total_processed INTEGER DEFAULT 0,
                total_success INTEGER DEFAULT 0,
                total_errors INTEGER DEFAULT 0,
                avg_confidence REAL DEFAULT 0,
                avg_processing_time REAL DEFAULT 0,
                form_4_count INTEGER DEFAULT 0,
                form_18_count INTEGER DEFAULT 0,
                form_20_count INTEGER DEFAULT 0,
                unknown_count INTEGER DEFAULT 0
            )
        ''')
        
        # สร้างตาราง document_requests (สำหรับ Dashboard)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS document_requests (
                request_id TEXT PRIMARY KEY,
                form_type TEXT NOT NULL,
                student_id TEXT,
                student_name TEXT,
                student_email TEXT,
                faculty TEXT,
                major TEXT,
                phone TEXT,
                advisor_name TEXT,
                advisor_email TEXT,
                current_step INTEGER DEFAULT 1,
                total_steps INTEGER DEFAULT 2,
                overall_status TEXT DEFAULT 'pending',
                courses TEXT,
                ocr_confidence REAL DEFAULT 0,
                source TEXT DEFAULT 'microsoft-forms',
                submitted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Database initialized at {self.db_path}")
    
    def save_result(self, result: Dict[str, Any], filename: str = None) -> int:
        """บันทึกผล OCR ลงฐานข้อมูล"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Extract data
        data = result.get("data", {})
        student = data.get("student", data)
        review = result.get("review_analysis", {})
        
        cursor.execute('''
            INSERT INTO ocr_results (
                filename, form_type, form_confidence, ocr_confidence,
                student_id, student_name, faculty, department,
                raw_text, extracted_data, review_needed, review_reasons,
                processing_time_ms, success, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            filename,
            result.get("detected_form_type"),
            result.get("form_confidence", 0),
            result.get("ocr_confidence", 0),
            student.get("student_id"),
            student.get("name"),
            student.get("faculty"),
            student.get("department"),
            result.get("raw_text", ""),
            json.dumps(data, ensure_ascii=False),
            1 if review.get("needs_review") else 0,
            json.dumps(review.get("review_reasons", []), ensure_ascii=False),
            result.get("processing_time_ms", 0),
            1 if result.get("success") else 0,
            result.get("message") if not result.get("success") else None
        ))
        
        result_id = cursor.lastrowid
        
        # Update daily stats
        self._update_daily_stats(cursor, result)
        
        conn.commit()
        conn.close()
        
        logger.info(f"💾 Saved OCR result #{result_id}")
        return result_id
    
    def _update_daily_stats(self, cursor, result: Dict):
        """อัปเดตสถิติประจำวัน"""
        today = datetime.now().strftime("%Y-%m-%d")
        form_type = result.get("detected_form_type", "unknown")
        
        # Check if today's record exists
        cursor.execute("SELECT id FROM processing_stats WHERE date = ?", (today,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing
            form_col = f"form_{form_type}_count" if form_type in ["4", "18", "20"] else "unknown_count"
            cursor.execute(f'''
                UPDATE processing_stats SET
                    total_processed = total_processed + 1,
                    total_success = total_success + ?,
                    total_errors = total_errors + ?,
                    {form_col} = {form_col} + 1
                WHERE date = ?
            ''', (
                1 if result.get("success") else 0,
                0 if result.get("success") else 1,
                today
            ))
        else:
            # Create new
            cursor.execute('''
                INSERT INTO processing_stats (
                    date, total_processed, total_success, total_errors,
                    form_4_count, form_18_count, form_20_count, unknown_count
                ) VALUES (?, 1, ?, ?, ?, ?, ?, ?)
            ''', (
                today,
                1 if result.get("success") else 0,
                0 if result.get("success") else 1,
                1 if form_type == "4" else 0,
                1 if form_type == "18" else 0,
                1 if form_type == "20" else 0,
                1 if form_type not in ["4", "18", "20"] else 0
            ))
    
    def get_results(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """ดึงประวัติผลลัพธ์"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM ocr_results
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return results
    
    def get_result_by_id(self, result_id: int) -> Optional[Dict]:
        """ดึงผลลัพธ์ตาม ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM ocr_results WHERE id = ?", (result_id,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    def get_stats(self) -> Dict:
        """ดึงสถิติรวม"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total stats
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success,
                AVG(CASE WHEN success = 1 THEN ocr_confidence ELSE NULL END) as avg_confidence,
                AVG(CASE WHEN success = 1 THEN processing_time_ms ELSE NULL END) as avg_time
            FROM ocr_results
        ''')
        total_row = cursor.fetchone()
        
        # Form type breakdown
        cursor.execute('''
            SELECT form_type, COUNT(*) as count
            FROM ocr_results
            WHERE success = 1
            GROUP BY form_type
        ''')
        form_breakdown = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Daily stats (last 7 days)
        cursor.execute('''
            SELECT * FROM processing_stats
            ORDER BY date DESC
            LIMIT 7
        ''')
        
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM processing_stats
            ORDER BY date DESC
            LIMIT 7
        ''')
        daily_stats = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            "total_processed": total_row[0] or 0,
            "total_success": total_row[1] or 0,
            "success_rate": (total_row[1] / total_row[0] * 100) if total_row[0] else 0,
            "avg_confidence": total_row[2] or 0,
            "avg_processing_time_ms": total_row[3] or 0,
            "form_breakdown": form_breakdown,
            "daily_stats": daily_stats
        }
    
    def search(self, query: str, limit: int = 20) -> List[Dict]:
        """ค้นหาผลลัพธ์"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM ocr_results
            WHERE student_id LIKE ? OR student_name LIKE ? OR filename LIKE ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (f'%{query}%', f'%{query}%', f'%{query}%', limit))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return results
    
    # ===== Dashboard Methods =====
    
    def save_request(self, data: Dict[str, Any]) -> str:
        """บันทึกคำร้องใหม่จาก Power Automate webhook"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # สร้าง request_id ถ้าไม่มี
        request_id = data.get("request_id")
        if not request_id:
            today = datetime.now().strftime("%Y%m%d")
            cursor.execute("SELECT COUNT(*) FROM document_requests WHERE request_id LIKE ?", (f"REQ-{today}%",))
            count = cursor.fetchone()[0]
            request_id = f"REQ-{today}-{count + 1:03d}"
        
        # กำหนด total_steps ตาม form_type
        form_type = str(data.get("form_type", "18"))
        total_steps = 2 if form_type == "18" else 3
        
        courses = data.get("courses", [])
        if isinstance(courses, list):
            courses = json.dumps(courses, ensure_ascii=False)
        
        cursor.execute('''
            INSERT OR REPLACE INTO document_requests (
                request_id, form_type, student_id, student_name, student_email,
                faculty, major, phone, advisor_name, advisor_email,
                current_step, total_steps, overall_status, courses,
                ocr_confidence, source, submitted_date, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            request_id,
            form_type,
            data.get("student_id"),
            data.get("student_name"),
            data.get("student_email"),
            data.get("faculty"),
            data.get("major"),
            data.get("phone"),
            data.get("advisor_name"),
            data.get("advisor_email"),
            data.get("current_step", 1),
            total_steps,
            data.get("overall_status", "pending"),
            courses,
            data.get("ocr_confidence", 0),
            data.get("source", "microsoft-forms"),
            data.get("submitted_date", datetime.now().isoformat()),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"📋 Saved request {request_id}")
        return request_id
    
    def update_request_status(self, request_id: str, data: Dict[str, Any]) -> bool:
        """อัปเดตสถานะคำร้อง"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # สร้าง SET clause แบบ dynamic
        allowed_fields = [
            "overall_status", "current_step", "advisor_name", 
            "advisor_email", "ocr_confidence"
        ]
        updates = []
        values = []
        for field in allowed_fields:
            if field in data:
                updates.append(f"{field} = ?")
                values.append(data[field])
        
        if not updates:
            conn.close()
            return False
        
        updates.append("updated_at = ?")
        values.append(datetime.now().isoformat())
        values.append(request_id)
        
        cursor.execute(
            f"UPDATE document_requests SET {', '.join(updates)} WHERE request_id = ?",
            values
        )
        
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        logger.info(f"📋 Updated request {request_id}: {data}")
        return affected > 0
    
    def get_requests(self, limit: int = 50, offset: int = 0, 
                     status: str = None, search: str = None) -> List[Dict]:
        """ดึงรายการคำร้อง สำหรับ Dashboard table"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM document_requests"
        params = []
        conditions = []
        
        if status:
            conditions.append("overall_status = ?")
            params.append(status)
        
        if search:
            conditions.append(
                "(student_id LIKE ? OR student_name LIKE ? OR request_id LIKE ?)"
            )
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY submitted_date DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        
        # Count total
        count_query = "SELECT COUNT(*) FROM document_requests"
        if conditions:
            count_query += " WHERE " + " AND ".join(conditions)
        cursor.execute(count_query, params[:-2] if params else [])
        total = cursor.fetchone()[0]
        
        conn.close()
        return {"requests": results, "total": total}
    
    def get_request_stats(self) -> Dict:
        """ดึงสถิติคำร้อง สำหรับ Dashboard cards + chart"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # นับรวม
        cursor.execute("SELECT COUNT(*) FROM document_requests")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM document_requests WHERE overall_status = 'approved'")
        approved = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM document_requests WHERE overall_status = 'pending'")
        pending = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM document_requests WHERE overall_status = 'rejected'")
        rejected = cursor.fetchone()[0]
        
        # ค่าเฉลี่ย OCR confidence
        cursor.execute("SELECT AVG(ocr_confidence) FROM document_requests WHERE ocr_confidence > 0")
        avg_confidence = cursor.fetchone()[0] or 0
        
        # แยกตาม form_type
        cursor.execute('''
            SELECT form_type, COUNT(*) as count 
            FROM document_requests 
            GROUP BY form_type
        ''')
        form_breakdown = {row[0]: row[1] for row in cursor.fetchall()}
        
        # สถิติรายวัน (7 วันล่าสุด)
        cursor.execute('''
            SELECT 
                DATE(submitted_date) as date,
                COUNT(*) as total,
                SUM(CASE WHEN form_type = '4' THEN 1 ELSE 0 END) as form4,
                SUM(CASE WHEN form_type = '18' THEN 1 ELSE 0 END) as form18,
                SUM(CASE WHEN form_type = '20' THEN 1 ELSE 0 END) as form20,
                SUM(CASE WHEN overall_status = 'approved' THEN 1 ELSE 0 END) as approved
            FROM document_requests
            WHERE submitted_date >= DATE('now', '-7 days')
            GROUP BY DATE(submitted_date)
            ORDER BY date ASC
        ''')
        daily = []
        for row in cursor.fetchall():
            daily.append({
                "date": row[0], "total": row[1],
                "form4": row[2], "form18": row[3], 
                "form20": row[4], "approved": row[5]
            })
        
        conn.close()
        
        return {
            "total_requests": total,
            "approved": approved,
            "pending": pending,
            "rejected": rejected,
            "avg_ocr_confidence": round(avg_confidence, 1),
            "form_breakdown": form_breakdown,
            "daily_stats": daily
        }
    
    def export_csv(self, filepath: str) -> int:
        """Export ผลลัพธ์เป็น CSV"""
        import csv
        
        results = self.get_results(limit=10000)
        
        if not results:
            return 0
        
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
        
        return len(results)


# Singleton instance
_db_instance: Optional[OCRDatabase] = None


def get_database() -> OCRDatabase:
    """Get or create singleton database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = OCRDatabase()
    return _db_instance


# ===== Test =====
if __name__ == "__main__":
    db = get_database()
    
    # Test save
    test_result = {
        "success": True,
        "detected_form_type": "18",
        "form_confidence": 1.0,
        "ocr_confidence": 0.92,
        "data": {
            "student": {
                "student_id": "6410500001",
                "name": "สมชาย ใจดี",
                "faculty": "วิศวกรรมศาสตร์"
            }
        },
        "raw_text": "Test OCR text",
        "processing_time_ms": 3500,
        "review_analysis": {
            "needs_review": False,
            "review_reasons": []
        }
    }
    
    result_id = db.save_result(test_result, "test.pdf")
    print(f"✅ Saved result #{result_id}")
    
    # Test get stats
    stats = db.get_stats()
    print(f"\n📊 Stats:")
    print(f"   Total: {stats['total_processed']}")
    print(f"   Success Rate: {stats['success_rate']:.1f}%")
    print(f"   Avg Confidence: {stats['avg_confidence']:.2%}")
