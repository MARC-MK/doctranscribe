#!/usr/bin/env python
"""
Simple standalone PDF file server that just serves files from the uploads directory.
This bypasses all the complex backend code and validation issues.
"""
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Create the app
app = FastAPI(title="Simple PDF Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Path to uploads directory
UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(exist_ok=True)

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Simple PDF Server is running", "status": "OK"}

@app.get("/handwriting/documents/{document_id}/pdf")
async def get_pdf(document_id: str, page: int = None):
    """
    Get a PDF document by ID.
    
    Args:
        document_id: The document ID
        page: Optional page number (ignored for now)
        
    Returns:
        The PDF file
    """
    try:
        # Look for files in the uploads directory
        potential_paths = [
            UPLOADS_DIR / document_id,  # Direct ID as filename
            UPLOADS_DIR / f"{document_id}.pdf",  # ID with .pdf extension
        ]
        
        # Also check for files that start with the ID (in case they have prefixes/suffixes)
        for item in UPLOADS_DIR.glob(f"*{document_id}*"):
            if item.is_file():
                potential_paths.append(item)
        
        # Try each potential path
        for path in potential_paths:
            if path.exists() and path.is_file():
                print(f"Serving PDF from: {path}")
                return FileResponse(
                    path, 
                    media_type="application/pdf",
                    headers={"Content-Disposition": f"inline; filename={path.name}"}
                )
        
        # Create an empty PDF file for testing if none exists
        print(f"No PDF found for document ID: {document_id}")
        
        # Return a helpful error message
        raise HTTPException(
            status_code=404, 
            detail=f"PDF file not found for document ID: {document_id}"
        )
        
    except Exception as e:
        print(f"Error serving PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error serving PDF: {str(e)}")

@app.get("/handwriting/documents/{document_id}")
async def get_document(document_id: str):
    """
    Get a document's metadata
    
    Args:
        document_id: The document ID
        
    Returns:
        The document metadata
    """
    return {
        "id": document_id,
        "filename": f"{document_id}.pdf",
        "status": "completed",
        "total_pages": 1,
        "uploaded_at": "2023-01-01T00:00:00Z",
        "latest_job": {
            "id": f"job-{document_id}",
            "status": "completed",
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z",
            "pages_processed": 1,
            "total_pages": 1
        }
    }

@app.get("/handwriting/jobs/{job_id}/results")
async def get_job_results(job_id: str):
    """
    Get job results
    
    Args:
        job_id: The job ID
        
    Returns:
        The job results
    """
    # Return a simple placeholder result
    return [
        {
            "id": f"result-{job_id}-1",
            "page_number": 1,
            "content": {
                "form_title": "Sample Form",
                "explanation_text": "This is a sample form with placeholder data.",
                "overall_confidence": 0.95,
                "questions": [
                    {
                        "question": "1. What is your name?",
                        "answer": "John Doe",
                        "page": 1,
                        "confidence": 0.97
                    },
                    {
                        "question": "2. What is your age?",
                        "answer": "30",
                        "page": 1,
                        "confidence": 0.98
                    },
                    {
                        "question": "3. What is your occupation?",
                        "answer": "Software Engineer",
                        "page": 1,
                        "confidence": 0.96
                    }
                ]
            },
            "processing_time": 1.5,
            "confidence_score": 0.95
        }
    ]

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting Simple PDF Server on port {port}")
    print(f"Serving files from: {UPLOADS_DIR.absolute()}")
    uvicorn.run(app, host="0.0.0.0", port=port) 