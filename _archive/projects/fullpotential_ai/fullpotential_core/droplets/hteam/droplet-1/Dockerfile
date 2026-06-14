FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Make app/ visible to Python
ENV PYTHONPATH=/app/app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE ${PORT}

# Run the application
# Run the application (FastAPI/ASGI)
CMD ["sh","-c","exec gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:${PORT} --timeout 120 --access-logfile - --error-logfile - app.server:app"]
