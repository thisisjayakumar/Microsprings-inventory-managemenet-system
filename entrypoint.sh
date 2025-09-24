#!/bin/bash

# Exit on any error
set -e

echo "Starting Django application..."

# Create logs directory if it doesn't exist
# Check if we're running in Docker or locally
if [ -w "/app" ] 2>/dev/null; then
    # Running in Docker - create /app/logs
    mkdir -p /app/logs
    echo "Created Docker logs directory: /app/logs"
else
    # Running locally - create logs in current directory
    mkdir -p ./logs
    echo "Created local logs directory: ./logs"
fi

# Wait for database to be ready
echo "Waiting for database..."
while ! python3 -c "
import os
import django
from django.conf import settings
from django.db import connections
from django.core.exceptions import ImproperlyConfigured

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'microsprings_inventory_system.docker_settings')
django.setup()

try:
    db_conn = connections['default']
    db_conn.cursor()
    print('Database is ready!')
except Exception as e:
    print(f'Database not ready: {e}')
    exit(1)
"; do
  echo "Database is unavailable - sleeping"
  sleep 1
done

echo "Database is ready!"

# Run migrations
echo "Running database migrations..."
python3 manage.py migrate --noinput

# Create superuser if it doesn't exist
echo "Creating superuser if it doesn't exist..."
python3 manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser created: admin/admin123')
else:
    print('Superuser already exists')
"

# Collect static files
echo "Collecting static files..."
python3 manage.py collectstatic --noinput --clear

# Ensure static files directory has proper permissions
if [ -d "/app/staticfiles" ]; then
    echo "Setting permissions for static files directory..."
    chmod -R 755 /app/staticfiles
fi

# Setup demo data (optional)
echo "Setting up demo data..."
python3 manage.py setup_roles || echo "Roles setup failed or already exists"
python3 manage.py setup_demo_users || echo "Demo users setup failed or already exists"

echo "Starting Gunicorn server..."
exec gunicorn --bind 0.0.0.0:8000 --workers 3 --timeout 120 microsprings_inventory_system.wsgi:application
