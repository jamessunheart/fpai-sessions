FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

# Expose port
EXPOSE 3000

# Run
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3000"]

