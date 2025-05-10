"""
Database migration script to add missing fields to ExtractionJob table.
"""
import sys
import logging
from pathlib import Path
import os

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlmodel import create_engine
from sqlalchemy import text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database URL from environment or default
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///doctranscribe.db")

def run_migration():
    """Add confidence_score and error_message columns to extractionjob table."""
    logger.info("Starting database migration...")
    
    # Create engine
    engine = create_engine(DATABASE_URL)
    
    # Check if columns already exist
    with engine.connect() as connection:
        # Check if confidence_score column exists
        result = connection.execute(text(
            "SELECT COUNT(*) FROM pragma_table_info('extractionjob') WHERE name='confidence_score'"
        ))
        has_confidence_score = result.scalar() > 0
        
        # Check if error_message column exists
        result = connection.execute(text(
            "SELECT COUNT(*) FROM pragma_table_info('extractionjob') WHERE name='error_message'"
        ))
        has_error_message = result.scalar() > 0
    
    # Add columns if they don't exist
    with engine.begin() as connection:
        if not has_confidence_score:
            logger.info("Adding confidence_score column to extractionjob table")
            connection.execute(text(
                "ALTER TABLE extractionjob ADD COLUMN confidence_score FLOAT"
            ))
        else:
            logger.info("confidence_score column already exists")
            
        if not has_error_message:
            logger.info("Adding error_message column to extractionjob table")
            connection.execute(text(
                "ALTER TABLE extractionjob ADD COLUMN error_message TEXT"
            ))
        else:
            logger.info("error_message column already exists")
    
    logger.info("Database migration completed successfully")

if __name__ == "__main__":
    run_migration() 