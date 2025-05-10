"""
Script to fix database schema issues by checking for and adding missing columns.
This is more targeted than recreating the entire database.
"""
import os
import logging
import sqlite3
from sqlmodel import SQLModel, create_engine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import all models to ensure they're registered with SQLModel
from app.database import DB_URL

def check_and_fix_database():
    """Check for missing columns in the database and add them if necessary."""
    logger.info("Checking database schema...")
    
    # For SQLite, extract the filename
    if DB_URL.startswith("sqlite:///"):
        db_path = DB_URL.replace("sqlite:///", "")
        
        # Verify file exists
        if not os.path.exists(db_path):
            logger.error(f"Database file does not exist: {db_path}")
            logger.info("Creating new database...")
            engine = create_engine(DB_URL)
            SQLModel.metadata.create_all(engine)
            logger.info("Database created successfully")
            return
        
        # Connect to SQLite database
        logger.info(f"Connecting to SQLite database: {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check for extractionjob.confidence_score
        cursor.execute("PRAGMA table_info(extractionjob)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        if "confidence_score" not in column_names:
            logger.info("Adding missing column 'confidence_score' to extractionjob table")
            cursor.execute("ALTER TABLE extractionjob ADD COLUMN confidence_score FLOAT")
            conn.commit()
            logger.info("Column added successfully")
        else:
            logger.info("Column 'confidence_score' already exists in extractionjob table")
        
        # Check for extractionresult.confidence_score
        cursor.execute("PRAGMA table_info(extractionresult)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        if "confidence_score" not in column_names:
            logger.info("Adding missing column 'confidence_score' to extractionresult table")
            cursor.execute("ALTER TABLE extractionresult ADD COLUMN confidence_score FLOAT")
            conn.commit()
            logger.info("Column added successfully")
        else:
            logger.info("Column 'confidence_score' already exists in extractionresult table")
        
        conn.close()
        logger.info("Database schema check completed")
    else:
        logger.warning(f"Unsupported database type: {DB_URL}")

if __name__ == "__main__":
    check_and_fix_database() 