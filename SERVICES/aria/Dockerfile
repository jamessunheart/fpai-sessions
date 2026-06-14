FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/

# Environment
ENV SERVICE_NAME=aria
ENV SERVICE_PORT=8710

# Run
EXPOSE 8710
CMD ["python", "-m", "app.main"]



