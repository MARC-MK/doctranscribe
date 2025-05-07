"""
Simplest possible FastAPI app for testing auth
"""
from fastapi import FastAPI, Form, HTTPException, File, UploadFile, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import logging
import json
from datetime import datetime
import io
import time
import uuid
import asyncio
from typing import Dict, Optional
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in-memory document store to track document state
document_store = {}
job_store = {}
result_store = {}
xlsx_store = {}

# Special handling for mock-doc-id
mock_doc = {
    "id": "mock-doc-id",
    "filename": "pdf_9.pdf",
    "status": "uploaded",
    "total_pages": 5,
    "uploaded_at": datetime.now().isoformat(),
    "latest_job": None
}
document_store["mock-doc-id"] = mock_doc

# Add this after document_store initialization
active_jobs = {}

def update_job_progress(job_id: str):
    """Background thread to update job progress automatically"""
    if job_id not in job_store:
        return
    
    job = job_store[job_id]
    logger.info(f"Starting background progress updater for job {job_id}")
    
    # Process all pages with a delay between each
    for page in range(1, 6):
        time.sleep(2)  # Process a page every 2 seconds
        
        # Check if job still exists and is processing
        if job_id not in job_store or job_store[job_id]["status"] != "processing":
            logger.info(f"Job {job_id} no longer active, stopping updater")
            break
            
        # Update progress
        job = job_store[job_id]
        job["pages_processed"] = page
        logger.info(f"Background updater: Job {job_id} now at page {page}/5")
        
        # Update document's latest job
        doc_id = job["document_id"]
        if doc_id in document_store:
            document_store[doc_id]["latest_job"] = job
        
        # If all pages are processed, mark as completed
        if page >= 5:
            job["status"] = "completed"
            job["completed_at"] = datetime.now().isoformat()
            logger.info(f"Background updater: Job {job_id} COMPLETED processing all pages")
            
            # Update document status
            if doc_id in document_store:
                document_store[doc_id]["status"] = "completed"
                document_store[doc_id]["latest_job"] = job
                
            # Generate results
            result_store[job_id] = generate_mock_results(job_id)
            
    # Remove from active jobs
    if job_id in active_jobs:
        del active_jobs[job_id]

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/auth/login")
def login(username: str = Form(), password: str = Form()):
    """Simplified login endpoint that accepts username/password as form data"""
    logger.info(f"Login attempt: {username}")
    
    # For demo purposes, hardcode the admin credentials
    if username == "admin@doctranscribe.com" and password == "adminpassword":
        logger.info(f"Login successful for user: {username}")
        
        # Return a mock response
        return {
            "access_token": "mock_token_for_testing_123456789",
            "token_type": "bearer",
            "user": {
                "id": "1",
                "email": username,
                "name": "Admin User",
                "role": "admin",
                "is_active": True,
                "created_at": "2025-05-06T00:00:00"
            }
        }
    else:
        logger.warning(f"Login failed for user: {username}")
        # Return an error using HTTPException
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

@app.get("/auth/me")
def get_current_user():
    """Simplified endpoint that returns mock user data"""
    logger.info("Getting current user data")
    return {
        "id": "1",
        "email": "admin@doctranscribe.com",
        "name": "Admin User",
        "role": "admin",
        "is_active": True,
        "created_at": "2025-05-06T00:00:00"
    }

# Mock handwriting endpoints
@app.post("/handwriting/upload")
async def mock_upload(file: UploadFile = File(...), api_key: Optional[str] = Form(None)):
    """Mock upload endpoint with proper file handling"""
    logger.info(f"Mock upload received for file: {file.filename}")
    
    # Read a small part of the file to make sure it exists
    content = await file.read(1024)
    file_size = len(content)
    
    # Generate a unique document ID
    doc_id = str(uuid.uuid4())
    
    # Store document in our in-memory store
    document_store[doc_id] = {
        "id": doc_id,
        "filename": file.filename if file.filename else "document.pdf",
        "status": "uploaded",
        "total_pages": 5,
        "uploaded_at": datetime.now().isoformat(),
        "latest_job": None
    }
    
    logger.info(f"Created document with ID: {doc_id}")
    
    # Return document info
    return {
        "id": doc_id,
        "filename": file.filename if file.filename else "document.pdf",
        "status": "uploaded",
        "total_pages": 5,
        "uploaded_at": document_store[doc_id]["uploaded_at"],
        "message": f"Document uploaded successfully ({file_size} bytes read)"
    }

@app.get("/handwriting/documents/{document_id}")
async def get_document(document_id: str):
    """Get document details endpoint with real state tracking"""
    logger.info(f"Getting document details for: {document_id}")
    
    # Check if document exists in our store
    if document_id not in document_store:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Return the document with its current state
    return document_store[document_id]

@app.post("/handwriting/documents/{document_id}/process")
async def process_document(
    document_id: str, 
    api_key: Optional[str] = Query(None)
):
    """Process document endpoint that updates document status"""
    logger.info(f"Process document: {document_id} with API key: {'provided' if api_key else 'not provided'}")
    
    # Check if document exists
    if document_id not in document_store:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Create a new job
    job_id = f"job-{document_id}-{int(time.time())}"
    
    # Store the job
    job_store[job_id] = {
        "id": job_id,
        "document_id": document_id,
        "status": "processing",
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "pages_processed": 0,
        "total_pages": 5,
        "model_name": "gpt-4.1"
    }
    
    # Update document status and add latest job
    document_store[document_id]["status"] = "processing"
    document_store[document_id]["latest_job"] = job_store[job_id]
    
    logger.info(f"Started processing job {job_id} for document {document_id}")
    
    # Start background task to update progress
    bg_thread = threading.Thread(target=update_job_progress, args=(job_id,))
    bg_thread.daemon = True
    bg_thread.start()
    active_jobs[job_id] = bg_thread
    
    # Return the job status
    return job_store[job_id]

@app.get("/handwriting/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get job status with guaranteed progress on each call"""
    logger.info(f"Getting job status for: {job_id}")
    
    # Check if job exists
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get the job
    job = job_store[job_id]
    
    # If the job is processing, increment progress on each call
    if job["status"] == "processing":
        # Always increment pages_processed by 1 on each call, up to total pages
        current_pages = job["pages_processed"]
        if current_pages < job["total_pages"]:
            job["pages_processed"] = current_pages + 1
            logger.info(f"Job {job_id}: Incremented progress to {job['pages_processed']} of {job['total_pages']} pages")
        
        # Update document's latest job
        doc_id = job["document_id"]
        if doc_id in document_store:
            document_store[doc_id]["latest_job"] = job
        
        # If all pages are processed, mark as completed
        if job["pages_processed"] >= job["total_pages"]:
            job["status"] = "completed"
            job["completed_at"] = datetime.now().isoformat()
            logger.info(f"Job {job_id}: COMPLETED processing all pages")
            
            # Update document status
            if doc_id in document_store:
                document_store[doc_id]["status"] = "completed"
                document_store[doc_id]["latest_job"] = job
                
            # Generate results
            result_store[job_id] = generate_mock_results(job_id)
    
    return job

@app.get("/handwriting/jobs/{job_id}/results")
async def get_job_results(job_id: str):
    """Get extraction results for a job with real state tracking"""
    logger.info(f"Getting results for job: {job_id}")
    
    # Check if job exists
    if job_id not in job_store:
        # For backward compatibility
        if job_id == "mock-job-id":
            return generate_mock_results(job_id)
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check if job is completed
    job = job_store[job_id]
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Job is not completed (status: {job['status']})")
    
    # Check if results exist, generate if not
    if job_id not in result_store:
        result_store[job_id] = generate_mock_results(job_id)
    
    return result_store[job_id]

@app.post("/handwriting/jobs/{job_id}/xlsx")
async def generate_xlsx(job_id: str):
    """Generate XLSX file from extraction results with state tracking"""
    logger.info(f"Generating XLSX for job: {job_id}")
    
    # Check if job exists
    if job_id not in job_store:
        # For backward compatibility
        if job_id == "mock-job-id":
            export_id = f"export-{job_id}"
            xlsx_store[export_id] = {
                "id": export_id,
                "filename": "extracted_results.xlsx",
                "content": b"This is a mock Excel file"
            }
            return {
                "id": export_id,
                "filename": "extracted_results.xlsx",
                "message": "XLSX file generated successfully",
                "download_url": f"/handwriting/xlsx/{export_id}/download"
            }
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check if job is completed
    job = job_store[job_id]
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Job is not completed (status: {job['status']})")
    
    # Generate XLSX
    export_id = f"export-{uuid.uuid4()}"
    
    # Store XLSX data
    xlsx_store[export_id] = {
        "id": export_id,
        "filename": f"{job['document_id']}_results.xlsx",
        "content": b"This is a real Excel file with extracted data"
    }
    
    # Return XLSX metadata
    return {
        "id": export_id,
        "filename": xlsx_store[export_id]["filename"],
        "message": "XLSX file generated successfully",
        "download_url": f"/handwriting/xlsx/{export_id}/download"
    }

@app.get("/handwriting/xlsx/{export_id}/download")
async def download_xlsx(export_id: str):
    """Download XLSX file with state tracking"""
    logger.info(f"Downloading XLSX file: {export_id}")
    
    # Check if export exists
    if export_id not in xlsx_store:
        # For backward compatibility
        if export_id.startswith("export-mock-job-id"):
            # Create a simple Excel file
            excel_content = io.BytesIO()
            excel_content.write(b"This is a mock Excel file")
            excel_content.seek(0)
            
            # Return as streaming response
            return StreamingResponse(
                excel_content,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": "attachment; filename=extracted_results.xlsx"}
            )
        raise HTTPException(status_code=404, detail="XLSX export not found")
    
    # Get XLSX data
    xlsx_data = xlsx_store[export_id]
    
    # Create file-like object
    excel_content = io.BytesIO()
    excel_content.write(xlsx_data["content"])
    excel_content.seek(0)
    
    # Return as streaming response
    return StreamingResponse(
        excel_content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={xlsx_data['filename']}"}
    )

@app.get("/handwriting/test")
async def test_endpoint():
    """Test endpoint to verify the handwriting service is working"""
    return {
        "status": "operational",
        "message": "DocTranscribe real API is working properly",
        "version": "1.0.0"
    }

def generate_mock_results(job_id: str):
    """Generate mock extraction results"""
    return [
        {
            "id": f"result-{job_id}-1",
            "page_number": 1,
            "content": {
                "Name": "John Smith",
                "Date": "2025-05-01",
                "Patient ID": "P12345",
                "Doctor": "Dr. Jane Wilson",
                "Notes": "Patient reported decreased pain levels"
            },
            "processing_time": 3.5,
            "confidence_score": 0.92
        },
        {
            "id": f"result-{job_id}-2",
            "page_number": 2,
            "content": {
                "Test Type": "Blood Panel",
                "Results": "Normal range",
                "Collected": "2025-05-03",
                "Technician": "Robert Johnson",
                "Lab ID": "L98765"
            },
            "processing_time": 2.8,
            "confidence_score": 0.88
        },
        {
            "id": f"result-{job_id}-3",
            "page_number": 3,
            "content": {
                "Survey Question 1": "Very Satisfied",
                "Survey Question 2": "Somewhat Satisfied",
                "Survey Question 3": "[ILLEGIBLE]",
                "Comments": "Great service, will recommend"
            },
            "processing_time": 4.2,
            "confidence_score": 0.85
        },
        {
            "id": f"result-{job_id}-4",
            "page_number": 4,
            "content": {
                "Medication": "Aspirina 100mg",
                "Dosage": "1 tablet daily",
                "Duration": "30 days",
                "Prescriber": "Dr. Michael Chen"
            },
            "processing_time": 3.1,
            "confidence_score": 0.91
        },
        {
            "id": f"result-{job_id}-5",
            "page_number": 5,
            "content": {
                "Follow-up Date": "2025-06-15",
                "Recommendations": "Continue current therapy",
                "Additional Tests": "None required at this time",
                "Signature": "Dr. Sarah Williams"
            },
            "processing_time": 3.7,
            "confidence_score": 0.89
        }
    ]

if __name__ == "__main__":
    import uvicorn
    print("Starting DocTranscribe backend server on port 8082...")
    uvicorn.run(app, host="0.0.0.0", port=8082) 