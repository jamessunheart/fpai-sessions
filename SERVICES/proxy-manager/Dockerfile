FROM python:3.11-slim

# Install system dependencies
# We install nginx-extras to match typical host configurations
RUN apt-get update && apt-get install -y \
    nginx-extras \
    certbot \
    python3-certbot-nginx \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY start.sh .
RUN chmod +x start.sh

# Expose port
EXPOSE 8100

# Run application
CMD ["./start.sh"]
