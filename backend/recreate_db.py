"""
Script to recreate the database with the correct schema.
This will delete the existing database and create a new one with the updated schema.
"""
import os
import logging
from sqlmodel import SQLModel, create_engine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import all models to ensure they're registered with SQLModel
from app.database import DB_URL

def recreate_database():
    """Drop all tables and recreate the database schema."""
    logger.info("Recreating database...")
    
    # Check if database file exists and delete it
    if DB_URL.startswith("sqlite:///"):
        db_path = DB_URL.replace("sqlite:///", "")
        if os.path.exists(db_path):
            logger.info(f"Removing existing database file: {db_path}")
            os.remove(db_path)
    
    # Create a new engine and create all tables
    engine = create_engine(DB_URL)
    logger.info("Creating new tables...")
    SQLModel.metadata.create_all(engine)
    logger.info("Database recreation completed successfully")

if __name__ == "__main__":
    recreate_database() 