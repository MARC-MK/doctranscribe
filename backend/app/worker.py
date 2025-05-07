"""
Background worker for document processing with OpenAI API.
"""
import time
import threading
import logging
import uuid
import json
import os
import random
from datetime import datetime
from typing import Dict, List, Optional

from sqlmodel import Session, select

from .models import Document, ProcessingStatus, ExtractionJob, ExtractionResult
from .database import get_session
from .services.openai_service import OpenAIService

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global dictionary to track active processing jobs
active_jobs = {}

async def process_document_task(document_id: uuid.UUID) -> None:
    """
    Background task to process a document with real OpenAI API.
    """
    logger.info(f"Starting background processing for document {document_id}")
    
    # Get a new db session for this thread
    db = next(get_session())
    
    try:
        # Get document
        document = db.exec(select(Document).where(Document.id == document_id)).one_or_none()
        if not document:
            logger.error(f"Document {document_id} not found")
            return
        
        # Create a new job
        job = ExtractionJob(
            document_id=document_id,
            started_at=datetime.utcnow(),
            model_name="gpt-4.1",
            status=ProcessingStatus.PROCESSING,
            total_pages=document.total_pages or 1,
            pages_processed=0
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        
        job_id = job.id
        logger.info(f"Created job {job_id} for document {document_id}")
        
        # Update document status
        document.status = ProcessingStatus.PROCESSING
        db.add(document)
        db.commit()
        
        # Find PDF file
        uploads_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
        
        # List all files in the directory for debugging
        all_files = os.listdir(uploads_dir)
        logger.info(f"Files in uploads directory: {all_files}")
        
        # Find files matching the document ID
        files = [f for f in all_files if str(document_id) in f]
        logger.info(f"Matching files for document {document_id}: {files}")
        
        if not files:
            error_msg = f"No file found for document {document_id}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        # Get the first matching file
        file_path = os.path.join(uploads_dir, files[0])
        logger.info(f"Processing file: {file_path}")
        
        # Check if file exists and is accessible
        if not os.path.exists(file_path):
            error_msg = f"File does not exist: {file_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        # Check file size
        file_size = os.path.getsize(file_path)
        logger.info(f"File size: {file_size} bytes")
        
        if file_size == 0:
            error_msg = f"File is empty: {file_path}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Read the PDF content
        with open(file_path, "rb") as f:
            pdf_content = f.read()
            logger.info(f"Successfully read PDF content, {len(pdf_content)} bytes")
        
        # Initialize OpenAI service
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.error("No OpenAI API key found in environment variables")
            raise ValueError("OpenAI API key is not set")
            
        logger.info(f"Initializing OpenAI service with API key: {api_key[:5]}...")
        openai_service = OpenAIService(api_key=api_key)
        
        # Process the PDF
        logger.info("Sending PDF to OpenAI service for processing...")
        result = await openai_service.process_pdf(pdf_content)
        logger.info(f"Received processing result: {len(result.get('raw_results', []))} pages processed")
        
        # Calculate actual number of pages
        total_pages = result.get("pages_processed", 1)
        if document.total_pages != total_pages:
            document.total_pages = total_pages
            db.add(document)
            db.commit()
            
            # Update job total pages
            job.total_pages = total_pages
            db.add(job)
            db.commit()
        
        # Process each page result
        raw_results = result.get("raw_results", [])
        for page_result in raw_results:
            page_number = page_result.get("page", 1)
            processing_time = page_result.get("processing_time", 0) / 1000  # Convert tokens to seconds
            
            # Debug log the content
            content = page_result.get("content", {})
            logger.info(f"Content for page {page_number}: {content}")
            
            # Create extraction result
            extraction_result = ExtractionResult(
                job_id=job_id,
                page_number=page_number,
                processing_time=processing_time,
                confidence_score=0.9,  # OpenAI doesn't provide confidence scores
                content=content
            )
            db.add(extraction_result)
            
            # Update job progress
            job.pages_processed = page_number
            db.add(job)
            db.commit()
            
            logger.info(f"Processed page {page_number}/{total_pages} for document {document_id}")
        
        # Mark job as completed
        job.completed_at = datetime.utcnow()
        job.status = ProcessingStatus.COMPLETED
        db.add(job)
        
        # Update document status
        document.status = ProcessingStatus.COMPLETED
        db.add(document)
        db.commit()
        
        logger.info(f"Completed processing document {document_id}")
        
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {str(e)}")
        logger.error(f"Exception details: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        try:
            # Mark document and job as failed
            document = db.exec(select(Document).where(Document.id == document_id)).one_or_none()
            if document:
                document.status = ProcessingStatus.FAILED
                db.add(document)
            
            job = db.exec(select(ExtractionJob).where(
                ExtractionJob.document_id == document_id,
                ExtractionJob.status == ProcessingStatus.PROCESSING
            )).first()
            
            if job:
                job.status = ProcessingStatus.FAILED
                job.completed_at = datetime.utcnow()
                db.add(job)
                
            db.commit()
        except Exception as inner_e:
            logger.error(f"Error updating status after failure: {str(inner_e)}")
    finally:
        # Remove job from active jobs
        if str(document_id) in active_jobs:
            del active_jobs[str(document_id)]
        
        # Close db session
        db.close()

def start_processing(document_id: uuid.UUID) -> bool:
    """
    Start processing a document in the background.
    
    Args:
        document_id: The document ID to process
        
    Returns:
        bool: True if processing started, False if already processing
    """
    document_id_str = str(document_id)
    
    # Check if already processing
    if document_id_str in active_jobs:
        logger.warning(f"Document {document_id} is already being processed")
        return False
    
    # Import asyncio here to avoid circular imports
    import asyncio
    
    # Create a new event loop for the thread
    loop = asyncio.new_event_loop()
    
    # Function to run the async process in a separate thread
    def run_async_process():
        asyncio.set_event_loop(loop)
        loop.run_until_complete(process_document_task(document_id))
        loop.close()
    
    # Start background thread
    thread = threading.Thread(
        target=run_async_process,
        daemon=True
    )
    thread.start()
    
    # Track active job
    active_jobs[document_id_str] = {
        "thread": thread,
        "started_at": datetime.utcnow()
    }
    
    logger.info(f"Started background processing for document {document_id}")
    return True 