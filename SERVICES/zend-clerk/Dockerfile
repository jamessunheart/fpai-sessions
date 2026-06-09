FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/

# Environment
ENV PYTHONUNBUFFERED=1
ENV ZEND_CLERK_PORT=8582

EXPOSE 8582

CMD ["python", "-m", "app.main"]




