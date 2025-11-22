# ============================================================================
# DROPLET #10: ORCHESTRATOR - PRODUCTION DOCKERFILE
# ============================================================================

# Build stage
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# ============================================================================
# Runtime stage
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r orchestrator && useradd -r -g orchestrator orchestrator

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/orchestrator/.local

# Copy application code
COPY app/ ./app/
COPY schema.sql udc_config.json ./

# Create logs directory
RUN mkdir -p /app/logs && chown -R orchestrator:orchestrator /app

# Switch to non-root user
USER orchestrator

# Add local Python packages to PATH
ENV PATH=/home/orchestrator/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=5).raise_for_status()"

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002", "--workers", "4"]