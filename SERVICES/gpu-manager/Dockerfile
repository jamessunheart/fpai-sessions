FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY *.py .

# Environment defaults (override at runtime)
ENV GPU_MANAGER_ENABLED=false
ENV GPU_MANAGER_MODE=monitor_only
ENV VASTAI_API_KEY=""

EXPOSE 8450

CMD ["python", "main.py"]
