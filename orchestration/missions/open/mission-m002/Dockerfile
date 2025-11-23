# Use an official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.11-slim

# Set environment variables to prevent Python from writing pyc files to disc
# and buffering stdout and stderr.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create a non-root user to run the application for security.
RUN addgroup --system app && adduser --system --group app

# Set the working directory in the container.
WORKDIR /app

# Install system dependencies (if any are needed for python packages).
# For now, we just need basic build tools.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the application code to the container.
COPY app /app/app
COPY env.example /app/.env
COPY entrypoint.sh /app/entrypoint.sh

# Chown all the files to the app user.
RUN chown -R app:app /app && chmod +x /app/entrypoint.sh

# Switch to the non-root user.
USER app

# Expose the port that the application listens on.
EXPOSE 8000

# Run the application.
ENTRYPOINT ["/app/entrypoint.sh"]

