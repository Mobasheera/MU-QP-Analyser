FROM python:3.12-slim

# Install system dependencies required for OCR and image processing
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency file first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies and Gunicorn
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn

# Install the spaCy English model
RUN python -m spacy download en_core_web_sm

# Copy the project
COPY . .

# Render provides the PORT environment variable
CMD gunicorn --bind 0.0.0.0:${PORT:-10000} app:app