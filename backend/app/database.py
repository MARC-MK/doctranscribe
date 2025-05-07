"""
Database configuration and utilities for DocTranscribe.
"""
import os
from pathlib import Path
from typing import Generator, Optional

from sqlmodel import Session, SQLModel, create_engine as sqlmodel_create_engine

# Get database URL from environment or use SQLite default
DB_URL = os.environ.get("DATABASE_URL", "sqlite:///./doctranscribe.db")
DB_ECHO = os.environ.get("DATABASE_ECHO", "False").lower() in ("true", "1", "t")

# Create database directory if using SQLite file
if DB_URL.startswith("sqlite:///"):
    # Extract the file path
    db_path = DB_URL.replace("sqlite:///", "")
    if db_path != ":memory:":
        # Make sure directory exists
        db_dir = Path(db_path).parent
        os.makedirs(db_dir, exist_ok=True)

def create_engine():
    """Create and return a new SQLAlchemy engine instance."""
    return sqlmodel_create_engine(
        DB_URL, 
        echo=DB_ECHO,
        connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {}
    )

# Create SQLAlchemy engine
engine = create_engine()

def get_engine():
    """Return the database engine."""
    return engine

def get_session() -> Generator[Session, None, None]:
    """
    Create and yield a database session.
    
    Usage:
        from fastapi import Depends
        
        @app.get("/items")
        def get_items(db: Session = Depends(get_session)):
            # Use session here
            pass
    """
    with Session(engine) as session:
        yield session

def create_db_and_tables() -> None:
    """Create all database tables."""
    # Import models here to ensure they're registered with SQLModel
    from .models import Document, ExtractionJob, ExtractionResult, XLSXExport, User
    
    SQLModel.metadata.create_all(engine)

def init_db(drop_all: bool = False) -> None:
    """Initialize the database with starting data."""
    if drop_all:
        SQLModel.metadata.drop_all(engine)
    
    create_db_and_tables()
    
    # Add any initial data here if needed
    with Session(engine) as session:
        # Check if we need to add initial admin user
        from .models import User, UserRole
        if session.query(User).count() == 0:
            # Create admin user
            from .auth import get_password_hash
            admin_user = User(
                email="admin@doctranscribe.com",
                name="Admin User",
                password=get_password_hash("adminpassword"),  # Change in production!
                role=UserRole.ADMIN
            )
            session.add(admin_user)
            
        session.commit() 