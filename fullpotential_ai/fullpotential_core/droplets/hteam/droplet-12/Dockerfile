# Chat Orchestrator Droplet 12 - Production Container
# Per TECH_STACK.md and SECURITY_REQUIREMENTS.md

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Create non-root user
# Per SECURITY_REQUIREMENTS.md - never run as root
RUN useradd -m -u 1000 chatorch && \
    chown -R chatorch:chatorch /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=chatorch:chatorch . .

# Create data directory
RUN mkdir -p /app/data && chown -R chatorch:chatorch /app/data

# Switch to non-root user
USER chatorch

# Expose port
EXPOSE 8012

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8012/health || exit 1

# Run application
# Per TECH_STACK.md - use uvicorn with workers
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8012", "--workers", "4"]