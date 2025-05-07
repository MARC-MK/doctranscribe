"""
Router for handwriting recognition endpoints.
"""
import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import io

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from sqlmodel import Session, select
from pydantic import BaseModel, Field

from ..auth import get_current_user
from ..database import get_session
from ..models import Document, ExtractionJob, ExtractionResult, ProcessingStatus, User, XLSXExport
from ..services.pdf_service import PDFProcessingService, UPLOAD_DIR
from ..services.xlsx_service import XLSXExportService

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/handwriting",
    tags=["handwriting"],
    responses={404: {"description": "Not found"}},
)


# API response models as proper Pydantic models
class JobStatusModel(BaseModel):
    """Job status information model"""
    id: Optional[str] = None
    document_id: Optional[str] = None
    status: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    pages_processed: Optional[int] = 0
    total_pages: Optional[int] = 0
    model_name: Optional[str] = None


class DocumentResponse(BaseModel):
    """Response model for document metadata."""
    id: str
    filename: str
    status: str
    total_pages: int
    uploaded_at: str
    latest_job: Optional[JobStatusModel] = None
    message: Optional[str] = None


class JobStatusResponse(BaseModel):
    """Response model for job status."""
    id: Optional[str] = None
    document_id: Optional[str] = None
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    pages_processed: Optional[int] = 0
    total_pages: Optional[int] = 0
    model_name: Optional[str] = None
    message: Optional[str] = None


class ExtractionResultResponse(BaseModel):
    """Response model for extraction results."""
    id: str
    page_number: int
    content: Dict[str, Any]
    processing_time: float
    confidence_score: Optional[float] = None


class XLSXResponse(BaseModel):
    """Response model for XLSX export information."""
    id: str
    filename: str
    message: str
    download_url: str


@router.post("/test")
async def test_handwriting_extraction() -> Dict[str, str]:
    """Test endpoint to verify the handwriting recognition service is working"""
    return {
        "status": "operational",
        "message": "Handwriting recognition service is ready",
        "model": "gpt-4.1"
    }


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    api_key: Optional[str] = Query(None, description="OpenAI API key (optional)"),
    model: Optional[str] = Query(None, description="OpenAI model name (optional)"),
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_session)
) -> DocumentResponse:
    """
    Upload a PDF document for handwriting recognition.
    
    Args:
        file: The PDF file to upload
        api_key: OpenAI API key (optional)
        model: OpenAI model name (optional)
        current_user: Current authenticated user (optional)
        db: Database session
        
    Returns:
        DocumentResponse: Document metadata
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        # Get API key from query param, or environment
        openai_api_key = api_key
        if not openai_api_key:
            import os
            openai_api_key = os.environ.get("OPENAI_API_KEY", "")
            
        # Initialize PDF processing service
        service = PDFProcessingService(api_key=openai_api_key)
        
        # Save uploaded file
        document = await service.save_uploaded_file(file)
        
        # Associate with user if authenticated
        if current_user:
            document.user_id = current_user.id
            db.add(document)
            db.commit()
            db.refresh(document)
        
        return DocumentResponse(
            id=str(document.id),
            filename=document.filename,
            status=document.status,
            total_pages=document.total_pages,
            uploaded_at=document.uploaded_at.isoformat(),
            message="Document uploaded successfully. Use the /process endpoint to start processing."
        )
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error uploading document: {str(e)}")


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_session)
) -> DocumentResponse:
    """
    Get document metadata.
    
    Args:
        document_id: Document ID
        current_user: Current authenticated user (optional)
        db: Database session
        
    Returns:
        DocumentResponse: Document metadata
    """
    document = db.exec(
        select(Document).where(Document.id == document_id)
    ).one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check access rights if user is authenticated
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
        job_info = JobStatusModel(
            id=str(latest_job.id),
            status=latest_job.status,
            started_at=latest_job.started_at.isoformat() if latest_job.started_at else None,
            completed_at=latest_job.completed_at.isoformat() if latest_job.completed_at else None,
            pages_processed=latest_job.pages_processed,
            total_pages=latest_job.total_pages
        )
    
    return DocumentResponse(
        id=str(document.id),
        filename=document.filename,
        status=document.status,
        total_pages=document.total_pages,
        uploaded_at=document.uploaded_at.isoformat(),
        latest_job=job_info
    )


@router.post("/documents/{document_id}/process", response_model=JobStatusResponse)
async def process_document(
    document_id: uuid.UUID,
    api_key: Optional[str] = Query(None, description="OpenAI API key (optional)"),
    model: Optional[str] = Query(None, description="OpenAI model name (optional)"),
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_session)
) -> JobStatusResponse:
    """
    Start processing a document for handwriting recognition.
    
    Args:
        document_id: Document ID
        api_key: OpenAI API key (optional)
        model: OpenAI model name (optional)
        current_user: Current authenticated user (optional)
        db: Database session
        
    Returns:
        JobStatusResponse: Job status
    """
    document = db.exec(
        select(Document).where(Document.id == document_id)
    ).one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check access rights if user is authenticated and document has an owner
    if current_user and document.user_id and document.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to process this document")
    
    # Check if already being processed
    if document.status == ProcessingStatus.PROCESSING:
        # Find the active job
        active_job = db.exec(
            select(ExtractionJob)
            .where(ExtractionJob.document_id == document_id)
            .where(ExtractionJob.status == ProcessingStatus.PROCESSING)
            .order_by(ExtractionJob.started_at.desc())
        ).first()
        
        if active_job:
            return JobStatusResponse(
                id=str(active_job.id),
                document_id=str(document_id),
                status="already_processing",
                started_at=active_job.started_at.isoformat() if active_job.started_at else None,
                pages_processed=active_job.pages_processed,
                total_pages=active_job.total_pages,
                message="Document is already being processed"
            )
    
    # Get API key from query param, or environment
    openai_api_key = api_key
    if not openai_api_key:
        import os
        openai_api_key = os.environ.get("OPENAI_API_KEY", "")
        
    if not openai_api_key:
        logger.warning("No OpenAI API key provided for document processing")
    
    try:
        # Initialize PDF processing service
        service = PDFProcessingService(api_key=openai_api_key)
        
        # Process document in a background task
        import asyncio
        task = asyncio.create_task(service.process_document(document_id, db))
        
        # Return immediate response
        return JobStatusResponse(
            document_id=str(document_id),
            status="processing_started",
            message=f"Document processing started{' with real API key' if openai_api_key else ' (mock mode - no API key)'}"
        )
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: uuid.UUID,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_session)
) -> JobStatusResponse:
    """
    Get job status.
    
    Args:
        job_id: Job ID
        current_user: Current authenticated user (optional)
        db: Database session
        
    Returns:
        JobStatusResponse: Job status
    """
    job = db.exec(
        select(ExtractionJob).where(ExtractionJob.id == job_id)
    ).one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check access rights if user is authenticated
    if current_user:
        document = db.exec(select(Document).where(Document.id == job.document_id)).one_or_none()
        if document and document.user_id and document.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this job")
    
    return JobStatusResponse(
        id=str(job.id),
        document_id=str(job.document_id),
        status=job.status,
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        pages_processed=job.pages_processed,
        total_pages=job.total_pages,
        model_name=job.model_name
    )


@router.get("/jobs/{job_id}/results", response_model=List[ExtractionResultResponse])
async def get_job_results(
    job_id: uuid.UUID,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_session)
) -> List[ExtractionResultResponse]:
    """
    Get extraction results for a job.
    
    Args:
        job_id: Job ID
        current_user: Current authenticated user (optional)
        db: Database session
        
    Returns:
        List[ExtractionResultResponse]: Extraction results
    """
    job = db.exec(
        select(ExtractionJob).where(ExtractionJob.id == job_id)
    ).one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check access rights if user is authenticated
    if current_user:
        document = db.exec(select(Document).where(Document.id == job.document_id)).one_or_none()
        if document and document.user_id and document.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access these results")
    
    if job.status != ProcessingStatus.COMPLETED:
        raise HTTPException(status_code=400, detail=f"Job is not completed (status: {job.status})")
    
    results = db.exec(
        select(ExtractionResult)
        .where(ExtractionResult.job_id == job_id)
        .order_by(ExtractionResult.page_number)
    ).all()
    
    if not results:
        return []
    
    return [
        ExtractionResultResponse(
            id=str(result.id),
            page_number=result.page_number,
            content=result.content,
            processing_time=result.processing_time,
            confidence_score=result.confidence_score
        )
        for result in results
    ]


@router.post("/jobs/{job_id}/xlsx", response_model=XLSXResponse)
async def generate_xlsx(
    job_id: uuid.UUID,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_session)
) -> XLSXResponse:
    """
    Generate XLSX file from extraction results.
    
    Args:
        job_id: Job ID
        current_user: Current authenticated user (optional)
        db: Database session
        
    Returns:
        XLSXResponse: XLSX export information
    """
    job = db.exec(
        select(ExtractionJob).where(ExtractionJob.id == job_id)
    ).one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check access rights if user is authenticated
    if current_user:
        document = db.exec(select(Document).where(Document.id == job.document_id)).one_or_none()
        if document and document.user_id and document.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to generate XLSX for this job")
    
    if job.status != ProcessingStatus.COMPLETED:
        raise HTTPException(status_code=400, detail=f"Job is not completed (status: {job.status})")
    
    try:
        # Generate XLSX
        xlsx_export = await XLSXExportService.generate_xlsx(job_id, db)
        
        return XLSXResponse(
            id=str(xlsx_export.id),
            filename=xlsx_export.filename,
            message="XLSX file generated successfully",
            download_url=f"/handwriting/xlsx/{xlsx_export.id}/download"
        )
    except Exception as e:
        logger.error(f"Error generating XLSX: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating XLSX: {str(e)}")


@router.get("/xlsx/{export_id}/download")
async def download_xlsx(
    export_id: uuid.UUID,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Download XLSX file.
    
    Args:
        export_id: XLSX export ID
        current_user: Current authenticated user (optional)
        db: Database session
        
    Returns:
        StreamingResponse: XLSX file download
    """
    xlsx_export = db.exec(
        select(XLSXExport).where(XLSXExport.id == export_id)
    ).one_or_none()
    
    if not xlsx_export:
        raise HTTPException(status_code=404, detail="XLSX export not found")
    
    # Check access rights if user is authenticated
    if current_user:
        job = db.exec(select(ExtractionJob).where(ExtractionJob.id == xlsx_export.job_id)).one_or_none()
        if job:
            document = db.exec(select(Document).where(Document.id == job.document_id)).one_or_none()
            if document and document.user_id and document.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="Not authorized to download this file")
    
    # Get file contents
    content = await XLSXExportService.get_xlsx_file(export_id, db)
    
    if not content:
        raise HTTPException(status_code=404, detail="XLSX file not found")
    
    # Return file as download
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{xlsx_export.filename}"'
        }
    )


@router.get("/documents/{document_id}/pdf")
async def get_document_pdf(
    document_id: uuid.UUID,
    page: Optional[int] = Query(None, description="Specific page to return (1-indexed)"),
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Get the PDF document file for viewing.
    
    Args:
        document_id: Document ID
        page: Specific page to return (1-indexed)
        current_user: Current authenticated user (optional)
        db: Database session
        
    Returns:
        StreamingResponse: PDF document
    """
    document = db.exec(
        select(Document).where(Document.id == document_id)
    ).one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check access rights if user is authenticated
    if current_user and document.user_id and document.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this document")
    
    # Get the file path
    file_path = Path(UPLOAD_DIR) / str(document_id)
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found")
    
    try:
        # If a specific page is requested, extract only that page
        if page is not None:
            from PyPDF2 import PdfReader, PdfWriter
            reader = PdfReader(file_path)
            
            # Check if page is valid
            if page < 1 or page > len(reader.pages):
                raise HTTPException(status_code=400, detail=f"Invalid page number. Document has {len(reader.pages)} pages.")
            
            # Extract the requested page (0-indexed in PyPDF2)
            writer = PdfWriter()
            writer.add_page(reader.pages[page - 1])
            
            # Write to a BytesIO object
            output_stream = io.BytesIO()
            writer.write(output_stream)
            output_stream.seek(0)
            
            return StreamingResponse(
                output_stream,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"inline; filename={document.filename}",
                    "Cache-Control": "max-age=86400"  # Cache for a day
                }
            )
        else:
            # Return the full document
            return StreamingResponse(
                open(file_path, "rb"),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"inline; filename={document.filename}",
                    "Cache-Control": "max-age=86400"  # Cache for a day
                }
            )
    except Exception as e:
        logger.error(f"Error serving PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error serving PDF: {str(e)}") 