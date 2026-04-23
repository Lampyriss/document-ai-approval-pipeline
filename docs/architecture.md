# Architecture Notes

## System Overview

This project automates student document requests from submission to approval tracking.

1. A student submits a Microsoft Forms request.
2. Power Automate Flow 1 fetches the uploaded PDF and sends it to the OCR API.
3. The FastAPI backend extracts structured fields with Gemini Vision.
4. Request metadata is stored for dashboard reporting and downstream approval logic.
5. Flow 1 starts the advisor approval step and notifies the dashboard.
6. Flow 2 handles instructor and office approvals for multi-step forms.
7. The backend generates a cover sheet and a merged final PDF when the workflow completes.

## Main Services

- `main.py`: FastAPI app and API routes
- `ocr_service.py`: OCR orchestration and classification logic
- `gemini_vision_service.py`: Gemini Vision integration
- `cover_sheet_playwright.py`: HTML-to-PDF rendering
- `database.py`: request persistence for dashboard views
- `dashboard/`: Next.js monitoring UI

## Supported Form Types

- Form 4: co-enrollment request
- Form 18: fee refund request
- Form 20: add-course request

## Integration Boundaries

- Microsoft Forms: intake channel
- Power Automate: workflow orchestration
- Microsoft Teams Approvals: human approval loop
- SharePoint / SQLite: operational storage
- Next.js dashboard: operational visibility

## Portfolio Scope

This public copy keeps the application code, dashboard, field specs, and benchmark assets that help explain the system design. It intentionally omits tenant-bound exports, secrets, personal data, and local workspace history.
