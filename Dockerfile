# Dockerfile for Hugging Face Spaces
# Document AI - OCR API (with Playwright for Cover Sheet generation)
# Gemini Vision OCR Only (no EasyOCR/PyTorch - saves ~1.5GB RAM)

FROM python:3.10-slim

WORKDIR /app

# 1. Install system dependencies (including Playwright/Chromium deps)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    # Thai fonts
    fonts-noto-cjk \
    fonts-thai-tlwg \
    # python-magic dependency
    libmagic1 \
    # Playwright/Chromium system dependencies
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libpango-1.0-0 \
    libcairo2 \
    libx11-xcb1 \
    libxcb-dri3-0 \
    && rm -rf /var/lib/apt/lists/*

# 2. Copy requirements first (for Docker layer caching)
COPY requirements.txt .

# 3. Install Python dependencies (includes playwright)
RUN pip install --no-cache-dir -r requirements.txt

# 4. Install Playwright Chromium browser only (smallest footprint)
RUN playwright install chromium

# 5. Copy application code
ENV APP_VERSION=4.2.0
COPY *.py ./
COPY *.yaml ./

# Create directories
RUN mkdir -p mock_pdfs templates

# Expose Hugging Face Spaces default port
EXPOSE 7860

# Run the application on port 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]