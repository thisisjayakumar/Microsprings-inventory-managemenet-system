#!/usr/bin/env python3
"""
Entrypoint script for running Gunicorn in distroless container.
This is needed because distroless doesn't have shell access.
"""
import sys
import os
from pathlib import Path

# Create necessary directories if they don't exist
for directory in ['/app/logs', '/app/media']:
    Path(directory).mkdir(parents=True, exist_ok=True)

# Add installed packages to Python path
sys.path.insert(0, '/install/lib/python3.12/site-packages')

# Import and run gunicorn
import gunicorn.app.wsgiapp as wsgi

if __name__ == '__main__':
    # Set default arguments
    default_args = [
        'gunicorn',
        '--bind', f"0.0.0.0:{os.environ.get('PORT', '8000')}",
        '--workers', os.environ.get('GUNICORN_WORKERS', '4'),
        '--timeout', '30',
        '--keep-alive', '2',
        '--max-requests', '1000',
        '--max-requests-jitter', '50',
        '--preload',
        '--access-logfile', '-',
        '--error-logfile', '-',
        '--log-level', os.environ.get('LOG_LEVEL', 'info'),
        '--worker-tmp-dir', '/dev/shm',
        'microsprings_inventory_system.wsgi:application'
    ]
    
    # Override sys.argv with gunicorn arguments
    sys.argv = default_args
    wsgi.run()

