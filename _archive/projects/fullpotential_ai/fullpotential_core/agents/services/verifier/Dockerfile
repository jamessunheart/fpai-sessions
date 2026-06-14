FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Create work directory for jobs
RUN mkdir -p /tmp/verifier-jobs

# Expose port
EXPOSE 8200

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8200"]
