# cover_sheet_playwright.py
"""
Cover Sheet PDF Generator using Playwright (Headless Chrome)
For HuggingFace Spaces deployment

Performance features:
- Browser Pool: singleton Chromium instance, new page per request
- PDF Cache: LRU cache keyed by request data hash
"""

import asyncio
import hashlib
import json
import time
import threading
from collections import OrderedDict
from datetime import datetime
from typing import Optional, List, Dict
import logging
import base64
import re

from playwright.async_api import async_playwright, Browser, Playwright
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


# ===== Browser Pool (Singleton) =====
_playwright_instance: Optional[Playwright] = None
_browser: Optional[Browser] = None


async def _get_browser() -> Browser:
    """Get or create singleton Chromium browser instance"""
    global _playwright_instance, _browser

    if _browser and _browser.is_connected():
        return _browser

    logger.info("🚀 Launching Chromium browser (singleton pool)...")
    if not _playwright_instance:
        _playwright_instance = await async_playwright().start()

    _browser = await _playwright_instance.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-dev-shm-usage']
    )
    logger.info("✅ Chromium browser ready (PID: %s)", _browser.contexts)
    return _browser


async def _shutdown_browser():
    """Shutdown browser pool (call on app shutdown)"""
    global _browser, _playwright_instance
    if _browser:
        await _browser.close()
        _browser = None
    if _playwright_instance:
        await _playwright_instance.stop()
        _playwright_instance = None
    logger.info("👋 Chromium browser pool shut down")


# ===== PDF Cache (LRU, size-aware, thread-safe) =====
_pdf_cache: OrderedDict = OrderedDict()
_pdf_cache_lock = threading.Lock()
_pdf_cache_bytes = 0
PDF_CACHE_MAX_BYTES = 30 * 1024 * 1024  # 30MB max
PDF_CACHE_MAX_COUNT = 200


def _cache_key(request_id: str, form_type: str, steps: List[Dict], submit_date: str) -> str:
    """Generate cache key from request data"""
    data = f"{request_id}:{form_type}:{json.dumps(steps, sort_keys=True, ensure_ascii=False)}:{submit_date}"
    return hashlib.sha256(data.encode()).hexdigest()[:16]


def _cache_get(key: str) -> Optional[bytes]:
    """Get PDF from cache (returns None if miss)"""
    with _pdf_cache_lock:
        if key in _pdf_cache:
            _pdf_cache.move_to_end(key)
            logger.info(f"📦 PDF cache HIT: {key}")
            return _pdf_cache[key]
    return None


def _cache_set(key: str, pdf_bytes: bytes):
    """Store PDF in cache with LRU eviction (size-aware)"""
    global _pdf_cache_bytes
    with _pdf_cache_lock:
        _pdf_cache[key] = pdf_bytes
        _pdf_cache.move_to_end(key)
        _pdf_cache_bytes += len(pdf_bytes)
        while (len(_pdf_cache) > PDF_CACHE_MAX_COUNT or
               _pdf_cache_bytes > PDF_CACHE_MAX_BYTES):
            if not _pdf_cache:
                break
            evicted_key, evicted_val = _pdf_cache.popitem(last=False)
            _pdf_cache_bytes -= len(evicted_val)
            logger.debug(f"🗑️ PDF cache evicted: {evicted_key}")

# Form type mapping
FORM_NAMES = {
    "4": "Form 4 - Prerequisite Course Request",
    "18": "Form 18 - Fee Refund Request",
    "20": "Form 20 - Add Course Registration",
}


class PlaywrightCoverSheetGenerator:
    """Generate Cover Sheet PDFs using Playwright"""

    def __init__(self):
        self.template_content = self._get_embedded_template()

    def _get_embedded_template(self) -> str:
        """Embedded HTML template — beige/cream style"""
        return '''<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <link href="https://fonts.googleapis.com/css2?family=Maitree:wght@400;700&family=IBM+Plex+Sans+Thai:wght@300;400;600&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #f4f2ec;
            --text-dark: #3d3c38;
            --accent-green: #4a9e6a;
            --pill-bg: rgba(255,255,255,0.5);
            --border-light: rgba(61,60,56,0.1);
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        @page { size: A4; margin: 0; }
        body { font-family: 'IBM Plex Sans Thai', sans-serif; color: var(--text-dark); background: var(--bg-base); }

        .page {
            width: 100%; min-height: 100vh;
            padding: 40px 50px;
            background: var(--bg-base);
            position: relative; overflow: hidden;
            display: flex; flex-direction: column;
        }
        .page::before {
            content: ""; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background: radial-gradient(circle at 70% 40%, rgba(163,177,138,0.15) 0%, transparent 60%);
            pointer-events: none;
        }
        .page::after {
            content: ""; position: absolute; inset: 0; pointer-events: none; opacity: 0.03;
            background-image: radial-gradient(circle, #3d3c38 0.4px, transparent 0.4px);
            background-size: 14px 14px;
        }

        .label-top {
            font-family: 'Space Mono', monospace;
            font-size: 10px; letter-spacing: 2px; opacity: 0.45;
            text-transform: uppercase; margin-bottom: 4px;
        }
        .student-name {
            font-family: 'Maitree', serif;
            font-size: 42px; font-weight: 700; line-height: 1.15; margin-bottom: 20px;
        }
        .badge-container { display: flex; gap: 10px; margin-bottom: 35px; flex-wrap: wrap; }
        .badge {
            font-family: 'Space Mono', monospace; font-size: 10px;
            padding: 5px 14px; border-radius: 50px;
            border: 1px solid var(--border-light); background: var(--pill-bg);
            text-transform: uppercase; letter-spacing: 0.5px;
            display: inline-flex; align-items: center; line-height: 1;
        }
        .badge-thai {
            font-family: 'IBM Plex Sans Thai', sans-serif; font-size: 11px;
            padding: 5px 14px; border-radius: 50px;
            border: 1px solid var(--border-light); background: var(--pill-bg);
            letter-spacing: 0;
            display: inline-flex; align-items: center; line-height: 1;
        }

        .meta-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; }
        .meta-item b {
            display: block; font-family: 'Space Mono', monospace;
            font-size: 16px; margin-top: 3px;
        }
        .form-type-section {
            margin-bottom: 24px; border-bottom: 1px solid var(--border-light); padding-bottom: 16px;
        }
        .form-type-value {
            font-family: 'Space Mono', monospace; font-size: 13px; font-weight: 600; margin-top: 4px;
        }
        .section-title {
            font-family: 'Space Mono', monospace; font-size: 9px;
            letter-spacing: 1.5px; opacity: 0.45; margin-bottom: 10px; text-transform: uppercase;
        }

        .timeline { display: flex; flex-direction: column; gap: 6px; }
        .tl-item {
            display: flex; align-items: center;
            background: rgba(255,255,255,0.4); border: 1px solid var(--border-light);
            border-radius: 10px; padding: 10px 14px;
        }
        .tl-item.pending { opacity: 0.55; }
        .tl-item.rejected { border-color: rgba(211,47,47,0.4); background: rgba(255,235,235,0.5); }
        .tl-icon {
            width: 22px; height: 22px; border-radius: 50%;
            background: var(--accent-green); color: white;
            display: flex; align-items: center; justify-content: center;
            margin-right: 12px; font-size: 11px; flex-shrink: 0;
        }
        .tl-icon.pend { background: #ccc; }
        .tl-icon.reject { background: #d32f2f; }
        .tl-body { flex: 1; min-width: 0; }
        .tl-body h3 { font-size: 11px; font-weight: 600; margin: 0; line-height: 1.3; }
        .tl-body h3 .cc { font-weight: 700; }
        .tl-body p { font-size: 10px; opacity: 0.55; margin: 1px 0 0; }
        .tl-body .comment { font-size: 9px; opacity: 0.7; font-style: italic; margin-top: 2px; }
        .tl-right { text-align: right; margin-left: 12px; flex-shrink: 0; }
        .tag {
            font-family: 'Space Mono', monospace; font-size: 9px;
            padding: 3px 8px; border-radius: 3px; display: inline-block;
        }
        .tag.approved { background: #c8e6c9; color: #2e7d32; }
        .tag.rejected { background: #ffcdd2; color: #c62828; }
        .tag.pending { background: #eee; color: #999; }
        .ts {
            font-family: 'Space Mono', monospace; font-size: 9px;
            opacity: 0.35; margin-top: 3px;
        }

        .status-badge {
            font-family: 'Space Mono', monospace; font-size: 10px;
            padding: 5px 14px; border-radius: 50px;
            letter-spacing: 0.5px; text-transform: uppercase; font-weight: 700;
            display: inline-flex; align-items: center; justify-content: center;
            line-height: 1;
        }
        .status-badge.completed { background: #c8e6c9; color: #2e7d32; }
        .status-badge.in-progress { background: #e8dfc8; color: #8a7a55; }
        .status-badge.rejected { background: #ffcdd2; color: #c62828; }

        .stamp {
            position: absolute; top: 35px; right: 45px;
            width: 90px; height: 90px;
            border: 1px solid rgba(0,0,0,0.08); border-radius: 50%;
            display: flex; flex-direction: column; align-items: center; justify-content: center;
            font-family: 'Space Mono', monospace; text-align: center;
            transform: rotate(12deg); opacity: 0.25;
        }
        .stamp .top { font-size: 9px; letter-spacing: 1px; }
        .stamp .mid { font-size: 22px; font-weight: 700; line-height: 1; margin: 1px 0; }

        .footer {
            margin-top: auto; padding-top: 16px;
            border-top: 1px solid var(--border-light);
            display: flex; justify-content: space-between;
            font-family: 'Space Mono', monospace; font-size: 9px; opacity: 0.4;
            text-transform: uppercase;
        }
    </style>
</head>
<body>
<div class="page">
    <div class="stamp">
        <span class="top">SCI SRC</span>
        <span class="mid">KU</span>
    </div>

    <div class="label-top">Approval Sheet</div>
    <h1 class="student-name">{{student_name_line1}}<br>{{student_name_line2}}</h1>

    <div class="badge-container">
        <div class="status-badge {{overall_status_class}}">{{overall_status_text}}</div>
        <div class="badge">Student</div>
        <div class="badge">ID: {{student_id}}</div>
        <div class="badge-thai">{{faculty_short}}</div>
    </div>

    <div class="meta-grid">
        <div class="meta-item">
            <div class="label-top">Request ID</div>
            <b>#{{request_id}}</b>
        </div>
        <div class="meta-item" style="text-align:right">
            <div class="label-top">Submitted Date</div>
            <b>{{submit_date}}</b>
        </div>
    </div>

    <div class="form-type-section">
        <div class="label-top">Form Type</div>
        <div class="form-type-value">{{form_name}}</div>
    </div>

    <div class="section-title">Process Timeline <span style="opacity:0.8; margin-left:6px;">{{progress_counter}}</span></div>
    <div class="timeline">
        {{approval_steps_html}}
    </div>

    <div class="footer">
        <div>DOC.AI SYSTEM / SECURE VERIFICATION / REF #{{request_id}}</div>
        <div>GENERATED AT {{generated_time}}</div>
    </div>
</div>
</body>
</html>'''

    def _generate_approval_step_html(self, step: Dict) -> str:
        """Generate HTML for a single approval step (beige style)"""
        status = step.get("status", "pending")
        approver_name = step.get("approver_name", "-")
        role = step.get("role", f"Step {step.get('step', '')}").replace("วิชา ", "")
        # Bold course codes (8-digit numbers like 01418111)
        role = re.sub(r'(\d{8})', r'<span class="cc">\1</span>', role)
        dt = step.get("datetime", "--:--")
        comment = step.get("comment", "")

        if status == "approved":
            return f'''<div class="tl-item">
            <div class="tl-icon">&#10003;</div>
            <div class="tl-body">
                <h3>{role}</h3>
                <p>{approver_name}</p>
            </div>
            <div class="tl-right">
                <div class="tag approved">APPROVED</div>
                <div class="ts">{dt}</div>
            </div>
        </div>'''
        elif status == "rejected":
            comment_html = f'<div class="comment">&ldquo;{comment}&rdquo;</div>' if comment else ""
            return f'''<div class="tl-item rejected">
            <div class="tl-icon reject">&#10007;</div>
            <div class="tl-body">
                <h3>{role}</h3>
                <p>{approver_name}</p>
                {comment_html}
            </div>
            <div class="tl-right">
                <div class="tag rejected">REJECTED</div>
                <div class="ts">{dt}</div>
            </div>
        </div>'''
        else:  # pending
            return f'''<div class="tl-item pending">
            <div class="tl-icon pend">&#9711;</div>
            <div class="tl-body">
                <h3>{role}</h3>
                <p>Waiting...</p>
            </div>
            <div class="tl-right">
                <div class="tag pending">PENDING</div>
                <div class="ts">--:--</div>
            </div>
        </div>'''

    def _render_template(self, data: Dict) -> str:
        """Render HTML template with data"""
        html = self.template_content
        for key, value in data.items():
            html = html.replace(f"{{{{{key}}}}}", str(value) if value else "-")
        return html

    async def _generate_pdf_async(self, html: str) -> bytes:
        """Generate PDF from HTML using Playwright direct PDF (vector output)"""
        t0 = time.time()
        browser = await _get_browser()

        # New page per request (fast: ~50ms vs ~3s for browser launch)
        page = await browser.new_page(viewport={'width': 794, 'height': 1123})

        try:
            await page.set_content(html, wait_until='networkidle')
            await page.wait_for_timeout(300)

            # Direct PDF — vector text, no rasterization, smaller file
            pdf_bytes = await page.pdf(
                format='A4',
                print_background=True,
                margin={'top': '0', 'right': '0', 'bottom': '0', 'left': '0'},
            )
        finally:
            await page.close()

        elapsed = time.time() - t0
        logger.info(f"⚡ PDF generated in {elapsed:.2f}s (direct PDF, {len(pdf_bytes)//1024}KB)")

        return pdf_bytes

    async def create_cover_sheet(
        self,
        request_id: str,
        form_type: str,
        student_name: str,
        student_id: str,
        faculty: str,
        approval_steps: List[Dict],
        submit_date: Optional[str] = None,
    ) -> bytes:
        """Create Cover Sheet PDF (async, with caching)"""
        # Normalize form_type: "แบบ 18" → "18", "แบบ 4" → "4"
        form_key = form_type.replace("แบบ ", "").strip() if form_type else form_type

        # Default approval steps when Power Automate sends empty array
        if not approval_steps:
            if form_key == "18":
                approval_steps = [
                    {"step": 1, "role": "อาจารย์ที่ปรึกษา", "status": "pending"},
                    {"step": 2, "role": "ฝ่ายทะเบียน", "status": "pending"},
                ]
            else:
                approval_steps = [
                    {"step": 1, "role": "อาจารย์ที่ปรึกษา", "status": "pending"},
                    {"step": 2, "role": "อาจารย์ผู้สอน", "status": "pending"},
                    {"step": 3, "role": "ฝ่ายทะเบียน", "status": "pending"},
                ]
            logger.info(f"📄 create_cover_sheet: empty steps → generated defaults for form_key={form_key!r}: {len(approval_steps)} steps")

        logger.info(f"📄 create_cover_sheet: form_type={form_type!r} → form_key={form_key!r}, approval_steps={len(approval_steps)} items")

        sd = submit_date or datetime.now().strftime("%Y-%m-%d")

        # Check PDF cache first
        cache_key = _cache_key(request_id, form_type, approval_steps, sd)
        cached = _cache_get(cache_key)
        if cached:
            return cached

        # Split name
        name_parts = student_name.split(" ", 1)
        student_name_line1 = name_parts[0] if len(name_parts) > 0 else student_name
        student_name_line2 = name_parts[1] if len(name_parts) > 1 else ""

        # Format date
        try:
            if submit_date:
                parsed_date = datetime.strptime(submit_date, "%Y-%m-%d")
                formatted_date = parsed_date.strftime("%b %d, %Y").upper()
            else:
                formatted_date = datetime.now().strftime("%b %d, %Y").upper()
        except:
            formatted_date = submit_date or datetime.now().strftime("%b %d, %Y").upper()

        # Progress counter + overall status
        approved_count = sum(1 for s in approval_steps if s.get("status") == "approved")
        total_count = len(approval_steps)
        progress_counter = f"{approved_count} / {total_count}"

        has_rejected = any(s.get("status") == "rejected" for s in approval_steps)
        all_approved = all(s.get("status") == "approved" for s in approval_steps)
        if has_rejected:
            overall_status_class = "rejected"
            overall_status_text = "REJECTED"
        elif all_approved:
            overall_status_class = "completed"
            overall_status_text = "COMPLETED"
        else:
            overall_status_class = "in-progress"
            overall_status_text = "IN PROGRESS"

        # Generate steps HTML
        approval_steps_html = "\n".join([
            self._generate_approval_step_html(step) for step in approval_steps
        ])

        data = {
            "request_id": request_id,
            "form_name": FORM_NAMES.get(form_key, f"Form {form_key}"),
            "student_name_line1": student_name_line1,
            "student_name_line2": student_name_line2,
            "student_id": student_id,
            "faculty_short": faculty,
            "submit_date": formatted_date,
            "generated_time": datetime.now().strftime("%I:%M.%S%p"),
            "progress_counter": progress_counter,
            "overall_status_class": overall_status_class,
            "overall_status_text": overall_status_text,
            "approval_steps_html": approval_steps_html,
        }

        html = self._render_template(data)
        pdf_bytes = await self._generate_pdf_async(html)

        # Store in cache
        _cache_set(cache_key, pdf_bytes)
        return pdf_bytes

    def merge_pdfs(self, pdf_list: List[bytes]) -> bytes:
        """Merge multiple PDFs"""
        merged_doc = fitz.open()
        for pdf_bytes in pdf_list:
            try:
                src_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                merged_doc.insert_pdf(src_doc)
                src_doc.close()
            except Exception as e:
                logger.error(f"Error merging PDF: {e}")
        result_bytes = merged_doc.tobytes()
        merged_doc.close()
        return result_bytes

    async def create_final_document(
        self,
        request_id: str,
        form_type: str,
        student_name: str,
        student_id: str,
        faculty: str,
        approval_steps: List[Dict],
        original_pdf: bytes,
        submit_date: Optional[str] = None,
    ) -> bytes:
        """Create final document (Cover Sheet + Original)"""
        cover_sheet = await self.create_cover_sheet(
            request_id=request_id,
            form_type=form_type,
            student_name=student_name,
            student_id=student_id,
            faculty=faculty,
            approval_steps=approval_steps,
            submit_date=submit_date,
        )
        return self.merge_pdfs([cover_sheet, original_pdf])


# Singleton
_generator = None

def get_cover_sheet_generator() -> PlaywrightCoverSheetGenerator:
    global _generator
    if _generator is None:
        _generator = PlaywrightCoverSheetGenerator()
    return _generator
