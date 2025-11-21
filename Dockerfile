# Multi-stage build for optimized Django production image
# Stage 1: Builder - Install dependencies and build
FROM python:3.12-alpine AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    mariadb-dev \
    linux-headers \
    libffi-dev \
    openssl-dev \
    jpeg-dev \
    zlib-dev \
    && apk add --no-cache \
    mariadb-connector-c \
    jpeg \
    zlib

WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies to a separate directory
RUN pip install --upgrade pip setuptools wheel && \
    pip install --prefix=/install --no-warn-script-location -r requirements.txt && \
    find /install -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    find /install -type f -name "*.pyc" -delete && \
    find /install -type f -name "*.pyo" -delete

# Copy application code
COPY . .

# Collect static files (needed before distroless stage)
RUN DJANGO_SETTINGS_MODULE=microsprings_inventory_system.docker_settings \
    python manage.py collectstatic --noinput --clear || true

# Stage 2: Production - Use distroless for minimal attack surface
FROM gcr.io/distroless/python3-debian12:nonroot

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:/install/lib/python3.12/site-packages \
    DJANGO_SETTINGS_MODULE=microsprings_inventory_system.docker_settings \
    PORT=8000

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder --chown=nonroot:nonroot /install /install

# Copy application code
COPY --from=builder --chown=nonroot:nonroot /app /app

# Copy collected static files
COPY --from=builder --chown=nonroot:nonroot /app/staticfiles /app/staticfiles

# Copy entrypoint script
COPY --from=builder --chown=nonroot:nonroot /app/entrypoint.py /app/entrypoint.py

# Create necessary directories (using Python since distroless has no shell)
# Note: We'll create these in entrypoint.py instead since distroless has no RUN command with shell

# Expose port
EXPOSE 8000

# Use Python entrypoint script (distroless doesn't have shell, so we use Python directly)
CMD ["python", "/app/entrypoint.py"]
