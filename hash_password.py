#!/usr/bin/env python3
"""
Standalone script to hash passwords using Django's password hashing mechanism.
This allows you to generate hashed passwords to manually update in the database.

Usage:
    python hash_password.py

Or make it executable and run directly:
    chmod +x hash_password.py
    ./hash_password.py
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

# Now we can import Django's password hasher
from django.contrib.auth.hashers import make_password


def hash_password(plain_password):
    """
    Hash a plain text password using Django's default password hasher.
    
    Args:
        plain_password (str): The plain text password to hash
        
    Returns:
        str: The hashed password ready to be inserted into the database
    """
    return make_password(plain_password)


def main():
    """Main function to interactively hash passwords."""
    print("=" * 60)
    print("Django Password Hasher")
    print("=" * 60)
    print("\nThis script will hash passwords using Django's default")
    print("password hashing algorithm (PBKDF2).")
    print("\nYou can then copy the hashed password and paste it directly")
    print("into your database's password field.")
    print("-" * 60)
    
    while True:
        print("\n")
        # Get password from user
        plain_password = input("Enter password to hash (or 'quit' to exit): ").strip()
        
        if plain_password.lower() in ['quit', 'exit', 'q']:
            print("\nExiting...")
            break
            
        if not plain_password:
            print("❌ Error: Password cannot be empty!")
            continue
        
        # Hash the password
        hashed = hash_password(plain_password)
        
        # Display the result
        print("\n" + "=" * 60)
        print("✅ Password hashed successfully!")
        print("=" * 60)
        print(f"\nPlain Password: {plain_password}")
        print(f"\nHashed Password:\n{hashed}")
        print("\n" + "=" * 60)
        print("📋 Copy the hashed password above and paste it into your")
        print("   database's 'password' field for the user.")
        print("=" * 60)
        
        # Ask if user wants to hash another password
        another = input("\n\nHash another password? (y/n): ").strip().lower()
        if another not in ['y', 'yes']:
            print("\nExiting...")
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

