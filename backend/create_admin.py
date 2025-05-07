"""
Script to create an admin user in the database.
"""
import sys
import os

# Add the current directory to path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from app.database import get_engine, init_db
from app.models import User, UserRole
from app.auth import get_password_hash

def create_admin_user(email="admin@doctranscribe.com", password="adminpassword", name="Admin User"):
    """Create an admin user if it doesn't exist already."""
    print(f"Initializing database...")
    init_db()
    
    # Create a database session
    engine = get_engine()
    with Session(engine) as session:
        # Check if user already exists
        existing_user = session.exec(select(User).where(User.email == email)).first()
        if existing_user:
            print(f"User with email {email} already exists. Skipping creation.")
            return
        
        # Create new admin user
        hashed_password = get_password_hash(password)
        admin_user = User(
            email=email,
            password=hashed_password,
            name=name,
            role=UserRole.ADMIN,
            is_active=True
        )
        
        session.add(admin_user)
        session.commit()
        print(f"Admin user created successfully: {email}")

if __name__ == "__main__":
    create_admin_user() 