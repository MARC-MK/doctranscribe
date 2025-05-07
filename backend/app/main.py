"""
Simplified FastAPI app with only authentication endpoints and basic file upload
"""

from fastapi import FastAPI, Request, Depends, HTTPException, status, File, UploadFile, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from typing import List, Dict, Optional, Any
from sqlmodel import Session, select
import traceback
import os
import uuid
import shutil
from datetime import datetime
import logging

# Import database functions
from .database import init_db, get_session
from .auth import authenticate_user, create_access_token, get_current_user
from .models import User, Document, ProcessingStatus, ExtractionJob, ExtractionResult
from . import worker

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="DocTranscribe API", version="0.1.0")

# Add CORS middleware to allow requests from frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler - ensures the server never crashes on requests
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Exception occurred: {str(exc)}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"error": f"Internal server error: {str(exc)}"},
    )

# Create uploads directory
UPLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Mount uploads directory for static file serving
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized successfully")

# Auth endpoints
@app.post("/auth/login")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_session)
):
    """Authenticate user and return JWT token."""
    logger.info(f"Login attempt for user: {form_data.username}")
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create and return token
    access_token = create_access_token(
        data={"sub": user.email, "user_id": str(user.id)}
    )
    
    logger.info(f"Login successful for user: {user.email}")
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat()
        }
    }

@app.get("/auth/me")
async def get_user_me(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at.isoformat()
    }

# Simplified handwriting endpoints
@app.post("/handwriting/upload")
async def upload_document(
    file: UploadFile = File(...),
    api_key: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Upload a PDF document."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        # Generate unique ID
        doc_id = uuid.uuid4()
        
        # Save file to disk
        file_path = os.path.join(UPLOADS_DIR, f"{doc_id}_{file.filename}")
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
            file_size = len(content)
        
        # Create document record
        document = Document(
            id=doc_id,
            filename=file.filename,
            file_size=file_size,
            mime_type="application/pdf",
            total_pages=1,  # Placeholder, would need PDF parsing to get real count
            status=ProcessingStatus.PENDING
        )
        
        # Link to user if authenticated
        if current_user:
            document.user_id = current_user.id
        
        # Save to database
        db.add(document)
        db.commit()
        db.refresh(document)
        
        return {
            "id": str(document.id),
            "filename": document.filename,
            "status": document.status.value,
            "total_pages": document.total_pages,
            "uploaded_at": document.uploaded_at.isoformat(),
            "message": "Document uploaded successfully."
        }
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error uploading document: {str(e)}")

@app.get("/handwriting/documents/{document_id}")
async def get_document(
    document_id: uuid.UUID,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Get document details."""
    try:
        document = db.exec(select(Document).where(Document.id == document_id)).one_or_none()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Check access rights if user is authenticated and document has an owner
        if current_user and document.user_id and document.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this document")
        
        # Get latest job if exists
        latest_job = db.exec(
            select(ExtractionJob)
            .where(ExtractionJob.document_id == document_id)
            .order_by(ExtractionJob.started_at.desc())
        ).first()
        
        job_info = None
        if latest_job:
            job_info = {
                "id": str(latest_job.id),
                "status": latest_job.status.value,
                "started_at": latest_job.started_at.isoformat() if latest_job.started_at else None,
                "completed_at": latest_job.completed_at.isoformat() if latest_job.completed_at else None,
                "pages_processed": latest_job.pages_processed,
                "total_pages": latest_job.total_pages,
                "model_name": latest_job.model_name
            }
        
        # Return document information
        return {
            "id": str(document.id),
            "filename": document.filename,
            "status": document.status.value,
            "total_pages": document.total_pages,
            "uploaded_at": document.uploaded_at.isoformat(),
            "latest_job": job_info
        }
    except Exception as e:
        logger.error(f"Error retrieving document: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error retrieving document: {str(e)}")

@app.post("/handwriting/documents/{document_id}/process")
async def process_document(
    document_id: uuid.UUID,
    api_key: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Process a document using background worker."""
    # Find document
    document = db.exec(select(Document).where(Document.id == document_id)).one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check access
    if current_user and document.user_id and document.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to process this document")
    
    # Check if already processing
    if document.status == ProcessingStatus.PROCESSING:
        # Find active job
        job = db.exec(
            select(ExtractionJob)
            .where(ExtractionJob.document_id == document_id)
            .where(ExtractionJob.status == ProcessingStatus.PROCESSING)
            .order_by(ExtractionJob.started_at.desc())
        ).first()
        
        if job:
            return {
                "id": str(job.id),
                "document_id": str(document_id),
                "status": "already_processing",
                "message": "Document is already being processed"
            }
    
    # Start processing in background thread
    success = worker.start_processing(document_id)
    
    if success:
        return {
            "document_id": str(document_id),
            "status": "processing_started",
            "message": "Document processing started."
        }
    else:
        return {
            "document_id": str(document_id),
            "status": "already_processing",
            "message": "Document is already being processed"
        }

@app.get("/handwriting/jobs/{job_id}")
async def get_job_status(
    job_id: uuid.UUID,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Get job status."""
    try:
        job = db.exec(select(ExtractionJob).where(ExtractionJob.id == job_id)).one_or_none()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check access rights if user is authenticated
        if current_user:
            document = db.exec(select(Document).where(Document.id == job.document_id)).one_or_none()
            if document and document.user_id and document.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="Not authorized to access this job")
        
        return {
            "id": str(job.id),
            "document_id": str(job.document_id),
            "status": job.status.value,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "pages_processed": job.pages_processed,
            "total_pages": job.total_pages,
            "model_name": job.model_name
        }
    except Exception as e:
        logger.error(f"Error retrieving job: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error retrieving job: {str(e)}")

@app.get("/handwriting/jobs/{job_id}/results")
async def get_job_results(
    job_id: uuid.UUID,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Get extraction results for a job."""
    try:
        job = db.exec(select(ExtractionJob).where(ExtractionJob.id == job_id)).one_or_none()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check access rights if user is authenticated
        if current_user:
            document = db.exec(select(Document).where(Document.id == job.document_id)).one_or_none()
            if document and document.user_id and document.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="Not authorized to access these results")
        
        # Get results
        results = db.exec(
            select(ExtractionResult)
            .where(ExtractionResult.job_id == job_id)
            .order_by(ExtractionResult.page_number)
        ).all()
        
        # Return results
        return [
            {
                "id": str(result.id),
                "page_number": result.page_number,
                "content": result.content,
                "processing_time": result.processing_time,
                "confidence_score": result.confidence_score
            }
            for result in results
        ]
    except Exception as e:
        logger.error(f"Error retrieving results: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Error retrieving results: {str(e)}")

@app.get("/handwriting/test")
async def test_handwriting():
    """Test endpoint for handwriting functionality."""
    return {
        "status": "operational",
        "message": "Handwriting endpoint is working (with background processing)",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "model": "gpt-4.1", "version": "1.0.0"} 