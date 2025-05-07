#!/usr/bin/env python
"""
Worker script for processing background tasks.
Run this script to start the background worker:
  python worker.py
"""
import asyncio
import logging
import sys
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("worker.log")
    ]
)

logger = logging.getLogger(__name__)

# Add parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def main():
    """Main entry point for the worker."""
    from app.worker import start_worker
    
    logger.info("Starting background worker process...")
    
    try:
        await start_worker()
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error(f"Worker error: {str(e)}")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main())) 