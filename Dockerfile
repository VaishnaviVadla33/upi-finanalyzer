# Use Ubuntu base image for better package availability
FROM ubuntu:22.04

# Set working directory
WORKDIR /app

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install Python and system dependencies including Tesseract OCR
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-script-latn \
    libtesseract-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Create symlink for python command
RUN ln -s /usr/bin/python3 /usr/bin/python

# Set Tesseract environment variables
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata/

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p uploads

# Set environment variables
ENV PYTHONPATH=/app
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata/

# Expose port
EXPOSE 5000

# Create a non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Run the application
CMD ["python", "app.py"]