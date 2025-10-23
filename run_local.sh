#!/bin/bash

# Local development startup script for MSP-ERP
# This script is designed to run the Django application locally

set -e

echo "Starting MSP-ERP Django application locally..."

# Create logs directory if it doesn't exist
mkdir -p ./logs
echo "✅ Created logs directory"

# Activate virtual environment
if [ -d "./venv" ]; then
    source ./venv/bin/activate
    echo "✅ Activated virtual environment"
else
    echo "❌ Virtual environment not found. Please create one with: python3 -m venv venv"
    exit 1
fi

# Set Django settings for local development
export DJANGO_SETTINGS_MODULE=microsprings_inventory_system.settings

# Check if database exists and run migrations
echo "Running database migrations..."
python3 manage.py makemigrations
python3 manage.py migrate --noinput

# Create superuser if it doesn't exist (for local development)
# echo "Creating superuser if it doesn't exist..."
# python3 manage.py shell -c "
# from django.contrib.auth import get_user_model
# User = get_user_model()
# if not User.objects.filter(username='admin').exists():
#     User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
#     print('✅ Superuser created: admin/admin123')
# else:
#     print('✅ Superuser already exists')
# " 2>/dev/null || echo "Note: Superuser creation skipped (may already exist)"

# Setup demo data (optional)
# echo "Setting up demo data..."
# python3 manage.py setup_roles 2>/dev/null || echo "Note: Roles setup skipped (may already exist)"
# python3 manage.py setup_demo_users 2>/dev/null || echo "Note: Demo users setup skipped (may already exist)"

echo "🚀 Starting Django development server..."
echo "Access the application at: http://localhost:8000"
echo "Admin panel at: http://localhost:8000/admin (admin/admin123)"
echo ""
echo "Press Ctrl+C to stop the server"

# Start the development server
python3 manage.py runserver 0.0.0.0:8000
