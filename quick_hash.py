#!/usr/bin/env python3
"""
Quick password hasher - pass password as argument.

Usage:
    python quick_hash.py "your_password_here"
"""

import os
import sys
import django

# Setup Django environment
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'microsprings_inventory_system.settings')

# Initialize Django
django.setup()

from django.contrib.auth.hashers import make_password


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python quick_hash.py 'your_password'")
        print("Example: python quick_hash.py 'MyNewPassword123'")
        sys.exit(1)
    
    password = sys.argv[1]
    hashed = make_password(password)
    print(hashed)

