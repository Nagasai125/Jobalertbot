FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and browsers
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy application code
COPY job_alerts/ ./job_alerts/
COPY config/ ./config/

# Create directories for data and logs
RUN mkdir -p data logs

# HuggingFace Spaces runs as user with uid 1000
RUN chown -R 1000:1000 /app
USER 1000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Default command - runs continuously with scheduling
CMD ["python", "-m", "job_alerts.main"]
