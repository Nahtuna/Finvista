# -*- coding: utf-8 -*-
"""
Demo User Seeding Script
Creates a demo user for development/testing purposes.
"""

import sys
import os

# Ensure root folder is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.core.database import SessionLocal, User
from backend.api.dependencies import hash_password

def seed_demo_user():
    """Create or update demo user."""
    db = SessionLocal()
    try:
        # Check if demo user already exists
        existing_user = db.query(User).filter(User.username == "demo").first()
        
        # Using "Finvista123!" which meets the requirements:
        # - 12+ characters
        # - Contains uppercase (F)
        # - Contains lowercase (invista)
        # - Contains digits (123)
        # - Contains special character (!)
        new_password_hash = hash_password("Finvista123!")
        
        if existing_user:
            # Update existing user's password
            existing_user.hashed_password = new_password_hash
            db.commit()
            print("✅ Demo user 'demo' password updated successfully!")
        else:
            # Create new demo user
            demo_user = User(
                username="demo",
                hashed_password=new_password_hash
            )
            db.add(demo_user)
            db.commit()
            print("✅ Demo user created successfully!")
        
        print("   Username: demo")
        print("   Password: Finvista123!")
        print("\n🔐 You can now login with these credentials.")
        
    except Exception as e:
        print(f"❌ Error with demo user: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_demo_user()
