# Use Python 3.12 slim image for better compatibility
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=microsprings_inventory_system.docker_settings

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        python3-dev \
        libpq-dev \
        postgresql-client \
        build-essential \
        && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Install Gunicorn for production
RUN pip install gunicorn

# Copy project
COPY . /app/

# Create logs directory
RUN mkdir -p /app/logs

# Create media directory for file uploads
RUN mkdir -p /app/media

# Create static files directory
RUN mkdir -p /app/staticfiles

# Make entrypoint script executable
RUN chmod +x /app/entrypoint.sh

# Create a non-root user and set permissions
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app/staticfiles
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/admin/', timeout=10)"

# Use entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]
