"""
PDF processing service with GPT-4.1 handwriting recognition.
"""
import asyncio
import base64
import io
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from uuid import UUID
import traceback
import difflib

import httpx
from fastapi import UploadFile, HTTPException
from fastapi.responses import FileResponse
from pdf2image import convert_from_bytes, convert_from_path
from sqlmodel import Session, select
from sqlalchemy import text

from ..database import engine
from ..models import (
    Document, 
    ExtractionJob, 
    ExtractionResult, 
    ProcessingStatus
)

# Configure logging
logger = logging.getLogger(__name__)

# Environment variables and configuration
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1-2025-04-14")  # Using the new GPT-4.1 model that supports vision
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

def fuzzy_uuid_match(target_uuid: str, available_uuids: List[str], threshold: float = 0.9) -> Optional[str]:
    """
    Find the best matching UUID from a list of available UUIDs using fuzzy matching.
    
    Args:
        target_uuid: The UUID to search for
        available_uuids: List of available UUIDs to search through
        threshold: Similarity threshold (0-1) required for a match
        
    Returns:
        The best matching UUID if similarity is above threshold, otherwise None
    """
    if not target_uuid or not available_uuids:
        return None
        
    # Clean UUIDs (in case of format variations)
    target_clean = target_uuid.lower().replace('-', '')
    
    best_match = None
    best_ratio = 0.0
    
    for uuid in available_uuids:
        # Skip empty values
        if not uuid:
            continue
            
        # Clean comparison UUID
        uuid_clean = uuid.lower().replace('-', '')
        
        # Calculate similarity ratio
        ratio = difflib.SequenceMatcher(None, target_clean, uuid_clean).ratio()
        
        # If exact match, return immediately
        if ratio == 1.0:
            return uuid
            
        # If better than previous best and above threshold
        if ratio > best_ratio and ratio >= threshold:
            best_ratio = ratio
            best_match = uuid
    
    return best_match


class PDFProcessingService:
    """Service for processing PDFs and extracting handwritten text."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the service with an optional API key."""
        self.api_key = api_key or OPENAI_API_KEY
        if not self.api_key:
            logger.warning("No OpenAI API key provided")
    
    async def get_pdf_by_id(self, document_id: str, page: Optional[int] = None) -> FileResponse:
        """
        Get a PDF file by document ID.
        
        Args:
            document_id: The document ID (can be UUID or string)
            page: Optional page number
            
        Returns:
            FileResponse with the PDF file
        """
        try:
            logger.info(f"Looking for PDF with ID: {document_id}")
            
            # Get list of all files in uploads directory
            if not os.path.exists(UPLOAD_DIR):
                logger.warning(f"Uploads directory not found: {UPLOAD_DIR}")
                os.makedirs(UPLOAD_DIR, exist_ok=True)
                
            upload_files = os.listdir(UPLOAD_DIR)
            logger.info(f"Found {len(upload_files)} files in uploads directory")
            
            # Try exact match first
            exact_path = UPLOAD_DIR / document_id
            if os.path.exists(exact_path) and os.path.isfile(exact_path):
                logger.info(f"Found exact match at: {exact_path}")
                return FileResponse(
                    exact_path, 
                    media_type="application/pdf",
                    headers={"Content-Disposition": f"inline; filename={document_id}.pdf"}
                )
                
            # Try with .pdf extension
            exact_path_pdf = UPLOAD_DIR / f"{document_id}.pdf"
            if os.path.exists(exact_path_pdf) and os.path.isfile(exact_path_pdf):
                logger.info(f"Found exact match with .pdf extension at: {exact_path_pdf}")
                return FileResponse(
                    exact_path_pdf, 
                    media_type="application/pdf",
                    headers={"Content-Disposition": f"inline; filename={document_id}.pdf"}
                )
            
            # No exact match, try fuzzy matching
            logger.info("No exact match found, trying fuzzy matching")
            best_match = fuzzy_uuid_match(document_id, upload_files)
            
            if best_match:
                logger.info(f"Found fuzzy match: {best_match} for requested ID: {document_id}")
                fuzzy_path = UPLOAD_DIR / best_match
                return FileResponse(
                    fuzzy_path, 
                    media_type="application/pdf",
                    headers={"Content-Disposition": f"inline; filename={document_id}.pdf"}
                )
                
            # If still no match, try database lookup
            try:
                document_uuid = UUID(str(document_id))
                with Session(engine) as session:
                    document = session.exec(
                        select(Document).where(Document.id == document_uuid)
                    ).one_or_none()
                    
                    if document:
                        # Try fuzzy matching with DB document ID
                        db_document_id = str(document.id)
                        db_best_match = fuzzy_uuid_match(db_document_id, upload_files)
                        
                        if db_best_match:
                            logger.info(f"Found match via DB lookup: {db_best_match}")
                            db_match_path = UPLOAD_DIR / db_best_match
                            return FileResponse(
                                db_match_path, 
                                media_type="application/pdf",
                                headers={"Content-Disposition": f"inline; filename={document.filename}"}
                            )
            except ValueError:
                # Not a valid UUID, continue with string-based search
                pass
            
            # If no PDF is found, generate an error PDF
            logger.warning(f"No matching PDF found for document ID: {document_id}")
            error_pdf_path = await self._generate_error_pdf(document_id)
            
            logger.info(f"Serving error PDF from: {error_pdf_path}")
            return FileResponse(
                error_pdf_path,
                media_type="application/pdf",
                headers={"Content-Disposition": f"inline; filename=error-{document_id}.pdf"}
            )
            
        except Exception as e:
            logger.error(f"Error serving PDF: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Error serving PDF: {str(e)}")
    
    async def _generate_error_pdf(self, document_id: str) -> Path:
        """
        Generate a PDF with an error message when the actual document is not found.
        
        Args:
            document_id: The document ID that was not found
            
        Returns:
            Path to the generated error PDF
        """
        try:
            # Create basic PDF with error message using ReportLab
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            
            # Ensure the directory exists - use absolute path within app
            error_dir = Path("/app/error_pdfs")
            os.makedirs(error_dir, exist_ok=True)
            logger.info(f"Creating error PDF in directory: {error_dir}")
            
            # Create a unique filename for the error PDF
            error_pdf_path = error_dir / f"error-{document_id}.pdf"
            
            # Generate PDF
            c = canvas.Canvas(str(error_pdf_path), pagesize=letter)
            width, height = letter
            
            # Add error message
            c.setFont("Helvetica-Bold", 18)
            c.drawString(100, height - 100, "Document Not Found")
            
            c.setFont("Helvetica", 12)
            c.drawString(100, height - 150, f"We couldn't find the document with ID: {document_id}")
            c.drawString(100, height - 180, "Please check if the document exists in the system.")
            c.drawString(100, height - 210, "Try uploading the document again if needed.")
            
            c.save()
            
            logger.info(f"Created error PDF at: {error_pdf_path}")
            return error_pdf_path
        except Exception as e:
            logger.error(f"Error generating error PDF: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Fallback to a simple text file if PDF generation fails
            error_txt_path = Path("/app/error_pdfs") / f"error-{document_id}.txt"
            os.makedirs(error_txt_path.parent, exist_ok=True)
            
            with open(error_txt_path, "w") as f:
                f.write(f"Document with ID {document_id} not found.")
            
            logger.info(f"Created error text file at: {error_txt_path}")
            return error_txt_path
    
    async def get_document_by_id(self, document_id: str) -> Dict[str, Any]:
        """
        Get document metadata by ID.
        
        Args:
            document_id: The document ID (can be UUID or string)
            
        Returns:
            Document metadata
        """
        try:
            try:
                document_uuid = UUID(str(document_id))
                logger.info(f"get_document_by_id: Looking up document with UUID {document_uuid}")
                
                with Session(engine) as session:
                    # Force refresh of the database connection to ensure latest data
                    session.execute(text("SELECT 1"))
                    
                    document = session.exec(
                        select(Document).where(Document.id == document_uuid)
                    ).one_or_none()
                    
                    if document:
                        logger.info(f"get_document_by_id: Found document with status={document.status.value}")
                        
                        # Get latest job
                        latest_job = session.exec(
                            select(ExtractionJob)
                            .where(ExtractionJob.document_id == document_uuid)
                            .order_by(ExtractionJob.started_at.desc())
                        ).first()
                        
                        if latest_job:
                            session.refresh(latest_job)
                            logger.info(f"get_document_by_id: Found latest job with id={latest_job.id}, status={latest_job.status.value}, pages_processed={latest_job.pages_processed}")
                        else:
                            logger.info(f"get_document_by_id: No jobs found for document {document_uuid}")

                        # Always return latest_job data if document is in one of these statuses, even if no job was found
                        include_job_data = latest_job is not None or document.status.value in ["processing", "completed", "failed"]
                        
                        # Log the inclusion decision
                        logger.info(f"get_document_by_id: Will include job data: {include_job_data}")
                        
                        result = {
                            "id": str(document.id),
                            "filename": document.filename,
                            "status": document.status.value,
                            "total_pages": document.total_pages or 1,
                            "uploaded_at": document.uploaded_at.isoformat() if document.uploaded_at else datetime.utcnow().isoformat()
                        }
                        
                        if include_job_data:
                            if latest_job:
                                result["latest_job"] = {
                                    "id": str(latest_job.id),
                                    "status": latest_job.status.value,
                                    "created_at": latest_job.started_at.isoformat() if latest_job.started_at else datetime.utcnow().isoformat(),
                                    "updated_at": latest_job.completed_at.isoformat() if latest_job.completed_at else datetime.utcnow().isoformat(),
                                    "pages_processed": latest_job.pages_processed,
                                    "total_pages": latest_job.total_pages or document.total_pages or 1
                                }
                            else:
                                # Create virtual job data using document's status - better than no job data
                                result["latest_job"] = {
                                    "id": f"virtual-{document_id}",
                                    "status": document.status.value,
                                    "created_at": document.uploaded_at.isoformat() if document.uploaded_at else datetime.utcnow().isoformat(),
                                    "updated_at": datetime.utcnow().isoformat(),
                                    "pages_processed": 0,
                                    "total_pages": document.total_pages or 1
                                }
                        
                        # Log the final result for debugging
                        logger.info(f"get_document_by_id: Returning document status={result['status']}, latest_job={result.get('latest_job', {}).get('id') if 'latest_job' in result else None}")
                        
                        return result
                    else:
                        # Document not found
                        logger.error(f"Document with ID {document_id} not found in database")
                        raise HTTPException(status_code=404, detail=f"Document not found: {document_id}")
            except ValueError as e:
                # Not a valid UUID, raise clear error
                logger.error(f"Invalid document ID format: {document_id}")
                raise HTTPException(status_code=400, detail=f"Invalid document ID format: {document_id}")
            
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"Error getting document metadata: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Error getting document metadata: {str(e)}")
    
    async def get_job_results(self, job_id: str) -> List[Dict[str, Any]]:
        """
        Get results for a job.
        
        Args:
            job_id: The job ID
            
        Returns:
            List of extraction results
        """
        try:
            # Handle virtual job IDs
            if job_id.startswith("virtual-"):
                document_id = job_id[8:]  # Remove "virtual-" prefix
                logger.info(f"Virtual job ID detected, looking up latest real job for document {document_id}")
                
                try:
                    document_uuid = UUID(document_id)
                    with Session(engine) as session:
                        # Find the latest real job for this document
                        real_job = session.exec(
                            select(ExtractionJob)
                            .where(ExtractionJob.document_id == document_uuid)
                            .order_by(ExtractionJob.started_at.desc())
                        ).first()
                        
                        if real_job:
                            logger.info(f"Found real job {real_job.id} for virtual job {job_id}")
                            job_id = str(real_job.id)
                        else:
                            # No real job found
                            logger.error(f"No real job found for document {document_id}")
                            return [{
                                "id": f"error-{job_id}",
                                "page_number": 0,
                                "content": {
                                    "error": "No processing job found",
                                    "form_title": "Error: No Job Found",
                                    "document_type": "error",
                                    "explanation_text": "No extraction job was found for this document.",
                                    "questions": [
                                        {
                                            "question": "Error Details",
                                            "answer": "The document needs to be processed first. Please click 'Start Processing' to extract text from the document.",
                                            "page": 0,
                                            "confidence": 0.0,
                                            "is_handwritten": False
                                        }
                                    ],
                                    "overall_confidence": 0.0
                                },
                                "processing_time": 0,
                                "confidence_score": 0
                            }]
                except (ValueError, Exception) as e:
                    logger.error(f"Error processing virtual job ID: {str(e)}")
                    return [{
                        "id": f"error-{job_id}",
                        "page_number": 0,
                        "content": {
                            "error": f"Error processing virtual job ID: {str(e)}",
                            "form_title": "Error: Invalid Job ID",
                            "document_type": "error",
                            "explanation_text": "The job ID is not valid.",
                            "questions": [
                                {
                                    "question": "Error Details",
                                    "answer": f"Virtual job ID error: {str(e)}",
                                    "page": 0,
                                    "confidence": 0.0,
                                    "is_handwritten": False
                                }
                            ],
                            "overall_confidence": 0.0
                        },
                        "processing_time": 0,
                        "confidence_score": 0
                    }]
            
            # Try to parse as UUID
            job_uuid = None
            try:
                job_uuid = UUID(job_id)
            except ValueError:
                # Invalid UUID format
                logger.error(f"Invalid job ID format: {job_id}")
                return [{
                    "id": f"error-{job_id}",
                    "page_number": 0,
                    "content": {
                        "error": "Invalid job ID format",
                        "form_title": "Error: Invalid Job ID",
                        "document_type": "error",
                        "explanation_text": f"The job ID '{job_id}' is not a valid UUID.",
                        "questions": [
                            {
                                "question": "Error Details",
                                "answer": f"The provided job ID '{job_id}' is not in a valid format. Please use a valid job ID.",
                                "page": 0,
                                "confidence": 0.0,
                                "is_handwritten": False
                            }
                        ],
                        "overall_confidence": 0.0
                    },
                    "processing_time": 0,
                    "confidence_score": 0
                }]
            
            # Query for results with the valid UUID
            with Session(engine) as session:
                # Log what we're looking for
                logger.info(f"Looking for results for job {job_uuid}")
                
                # Find all results for the job, ordered by page number
                results = session.exec(
                    select(ExtractionResult).where(
                        ExtractionResult.job_id == job_uuid
                    ).order_by(ExtractionResult.page_number)
                ).all()
                
                logger.info(f"Found {len(results)} results for job {job_uuid}")
                
                # If results found, format and return them
                if results:
                    logger.info(f"Returning {len(results)} results for job {job_uuid}")
                    
                    # Check if we have a page 0 (combined result)
                    has_combined = any(r.page_number == 0 for r in results)
                    
                    # If no combined result exists, try to create one from individual pages
                    if not has_combined and len(results) > 0:
                        logger.info(f"No combined result found for job {job_uuid}, creating one from {len(results)} individual pages")
                        
                        # Create combined result with all questions
                        all_questions = []
                        for result in results:
                            if result.content and isinstance(result.content, dict) and "questions" in result.content:
                                questions = result.content["questions"]
                                if isinstance(questions, list):
                                    for q in questions:
                                        if "page" not in q:
                                            q["page"] = result.page_number
                                    all_questions.extend(questions)
                        
                        # Get form title and metadata from the first page
                        first_page = next((r for r in results if r.page_number == 1), None)
                        form_title = first_page.content.get("form_title", "Extracted Document") if first_page else "Extracted Document"
                        document_type = first_page.content.get("document_type", "form") if first_page else "form"
                        explanation_text = first_page.content.get("explanation_text", "") if first_page else ""
                        
                        # Calculate overall confidence
                        overall_confidence = 0.0
                        if all_questions:
                            confidence_values = [q.get("confidence", 0.0) for q in all_questions if q.get("confidence") is not None]
                            if confidence_values:
                                overall_confidence = sum(confidence_values) / len(confidence_values)
                        
                        # Create and add the combined result
                        combined_content = {
                            "form_title": form_title,
                            "document_type": document_type,
                            "explanation_text": explanation_text,
                            "questions": all_questions,
                            "overall_confidence": overall_confidence
                        }
                        
                        # Create result object but don't save it to DB - just for API response
                        combined_result = ExtractionResult(
                            id=UUID('00000000-0000-0000-0000-000000000000'),  # Dummy ID
                            job_id=job_uuid,
                            page_number=0,
                            content=combined_content,
                            processing_time=sum(r.processing_time or 0 for r in results),
                            confidence_score=overall_confidence
                        )
                        
                        # Add to results
                        results.append(combined_result)
                        logger.info(f"Added synthetic combined result with {len(all_questions)} questions")
                    
                    # Format all results for the API response
                    return [
                        {
                            "id": str(r.id),
                            "page_number": r.page_number,
                            "content": r.content,
                            "processing_time": r.processing_time,
                            "confidence_score": r.confidence_score
                        }
                        for r in results
                    ]
                
                # If no results found but job exists, check job status
                job = session.get(ExtractionJob, job_uuid)
                if job:
                    logger.info(f"No results but job found with status {job.status.value}")
                    
                    # If job is completed but no results, something went wrong
                    if job.status == ProcessingStatus.COMPLETED:
                        logger.warning(f"Job {job_uuid} is completed but has no results - creating a synthetic result")
                        
                        # Create synthetic questions for better UI
                        return [{
                            "id": f"synthetic-{job_id}",
                            "page_number": 0,
                            "content": {
                                "form_title": "Processing Completed",
                                "document_type": "report",
                                "explanation_text": "The document was processed, but no structured data was extracted.",
                                "questions": [
                                    {
                                        "question": "Status",
                                        "answer": "The document was processed successfully, but no structured data could be extracted.",
                                        "page": 0,
                                        "confidence": 0.0,
                                        "is_handwritten": False
                                    },
                                    {
                                        "question": "Recommendation",
                                        "answer": "Try processing the document again, or try a different document.",
                                        "page": 0, 
                                        "confidence": 0.0,
                                        "is_handwritten": False
                                    }
                                ],
                                "overall_confidence": 0.0
                            },
                            "processing_time": 0,
                            "confidence_score": 0
                        }]
                    else:
                        # Return status info for pending/processing jobs
                        return [{
                            "id": f"pending-{job_id}",
                            "page_number": 0,
                            "content": {
                                "status": job.status.value,
                                "form_title": f"Job Status: {job.status.value.capitalize()}",
                                "document_type": "status",
                                "explanation_text": f"The job is currently in '{job.status.value}' status.",
                                "questions": [
                                    {
                                        "question": "Job Status",
                                        "answer": f"The job is {job.status.value}. Please check back later if the job is still processing.",
                                        "page": 0,
                                        "confidence": 0.0,
                                        "is_handwritten": False
                                    }
                                ],
                                "overall_confidence": 0.0
                            },
                            "processing_time": 0,
                            "confidence_score": 0
                        }]
                
                # Job not found
                logger.error(f"Job with ID {job_id} not found")
                return [{
                    "id": f"error-{job_id}",
                    "page_number": 0,
                    "content": {
                        "error": "Results not found",
                        "form_title": "Error: Results Not Found",
                        "document_type": "error",
                        "explanation_text": f"No results were found for job ID '{job_id}'.",
                        "questions": [
                            {
                                "question": "Error Details",
                                "answer": "The job may have failed or does not exist. Please try processing the document again.",
                                "page": 0,
                                "confidence": 0.0,
                                "is_handwritten": False
                            }
                        ],
                        "overall_confidence": 0.0
                    },
                    "processing_time": 0,
                    "confidence_score": 0
                }]
        except Exception as e:
            logger.error(f"Error retrieving job results: {str(e)}")
            logger.error(traceback.format_exc())
            return [{
                "id": f"error-{job_id}",
                "page_number": 0,
                "content": {
                    "error": f"Error retrieving results: {str(e)}",
                    "form_title": "Error: System Error",
                    "document_type": "error",
                    "explanation_text": "An unexpected error occurred while retrieving the results.",
                    "questions": [
                        {
                            "question": "Error Details",
                            "answer": f"System error: {str(e)}",
                            "page": 0,
                            "confidence": 0.0,
                            "is_handwritten": False
                        }
                    ],
                    "overall_confidence": 0.0
                },
                "processing_time": 0,
                "confidence_score": 0
            }]

    async def save_uploaded_file(self, file: UploadFile) -> Dict[str, Any]:
        """
        Save an uploaded PDF file and create a Document record.
        
        Args:
            file: The uploaded PDF file
            
        Returns:
            Dictionary with document information
        """
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # Create document record
        document = Document(
            filename=file.filename,
            file_size=file_size,
            mime_type=file.content_type or "application/pdf",
            status=ProcessingStatus.PENDING
        )
        
        # Save to database - use a regular session since get_session is not async
        with Session(engine) as session:
            session.add(document)
            session.commit()
            session.refresh(document)
            
            # Save document properties before the session closes
            doc_dict = {
                "id": document.id,
                "filename": document.filename,
                "file_size": document.file_size,
                "mime_type": document.mime_type,
                "status": document.status,
                "total_pages": document.total_pages,
                "uploaded_at": document.uploaded_at
            }
        
        # Save file to disk
        file_path = Path(UPLOAD_DIR) / str(doc_dict["id"])
        file_path.parent.mkdir(exist_ok=True)
        
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Try to get page count
        try:
            # Quick check of first few pages to get count
            with open(file_path, "rb") as f:
                from PyPDF2 import PdfReader
                reader = PdfReader(f)
                total_pages = len(reader.pages)
                
                doc_dict["total_pages"] = total_pages
                
                # Use a regular session here as well
                with Session(engine) as session:
                    document = session.get(Document, doc_dict["id"])
                    if document:
                        document.total_pages = total_pages
                        session.commit()
        except Exception as e:
            logger.error(f"Error getting page count: {str(e)}")
        
        return doc_dict

    async def process_document(self, document_id: Union[str, UUID], session: Session) -> ExtractionJob:
        """
        Process a document for handwriting extraction.
        
        Args:
            document_id: The document ID
            session: Database session
            
        Returns:
            Job information
        """
        api_key = self.api_key
        
        # Get document info
        document = session.exec(
            select(Document).where(Document.id == document_id)
        ).one_or_none()
        
        if not document:
            logger.error(f"Document {document_id} not found")
            # Create a job with error status
            error_job = ExtractionJob(
                document_id=document_id,
                status=ProcessingStatus.FAILED,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                model_name=MODEL,
                total_pages=0
            )
            session.add(error_job)
            session.commit()
            session.refresh(error_job)
            return error_job
        
        # Validate API key with a simple models list call
        if not await self._validate_api_key(api_key):
            logger.error("Invalid API key")
            document.status = ProcessingStatus.FAILED
            session.commit()
                
            # Create a job with error status
            error_job = ExtractionJob(
                document_id=document_id,
                status=ProcessingStatus.FAILED,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                model_name=MODEL,
                total_pages=document.total_pages or 0
            )
            session.add(error_job)
            session.commit()
            session.refresh(error_job)
            
            # Add error result
            error_result = ExtractionResult(
                job_id=error_job.id,
                page_number=0,
                content={
                    "error": "Invalid API key",
                    "form_title": "Error: API Key Invalid",
                    "document_type": "error",
                    "explanation_text": "The provided OpenAI API key is invalid or has expired.",
                    "questions": [
                        {
                            "question": "Error Details",
                            "answer": "The API key provided for OpenAI services is invalid. Please check your API key and try again.",
                            "page": 0,
                            "confidence": 0.0,
                            "is_handwritten": False
                        }
                    ],
                    "overall_confidence": 0.0
                },
                processing_time=0,
                confidence_score=0
            )
            session.add(error_result)
            session.commit()
            return error_job
        
        # Update document status to 'processing' early
        document.status = ProcessingStatus.PROCESSING
        session.add(document) # Ensure change is staged

        # Create extraction job
        job = ExtractionJob(
            document_id=document_id,
            started_at=datetime.utcnow(),
            model_name=MODEL,
            total_pages=document.total_pages or 0,
            status=ProcessingStatus.PENDING # Job starts as pending, task will update it
        )
        session.add(job)
        session.commit() # Commit document status update and new job
        session.refresh(job)
        session.refresh(document) # Refresh document to reflect its new status
        
        # Derive file path from document ID
        pdf_path = os.path.join(UPLOAD_DIR, str(document.id))
            
        # Get the full path
        full_path = os.path.join(os.getcwd(), pdf_path)
        
        # Start the background task
        asyncio.create_task(self._process_document_task(full_path, job.id, api_key))
        
        return job

    async def _process_document_task(self, pdf_path: str, job_id: UUID, api_key: str) -> None:
        """
        Background task to process a PDF document.
        
        Args:
            pdf_path: Path to the PDF file
            job_id: The job ID
            api_key: OpenAI API key
        """
        logger.info(f"Starting background processing task for job {job_id}")
        
        try:
            with Session(engine) as session:
                # Get the job
                job = session.exec(
                    select(ExtractionJob).where(ExtractionJob.id == job_id)
                ).one_or_none()
                
                if not job:
                    logger.error(f"Job {job_id} not found")
                    return
                
                # Get the document
                document = session.exec(
                    select(Document).where(Document.id == job.document_id)
                ).one_or_none()
                
                if not document:
                    logger.error(f"Document {job.document_id} not found")
                    job.status = "failed"
                    job.error_message = f"Document {job.document_id} not found"
                    session.commit()
                    return
                
                # Update document and job status
                document.status = "processing"
                job.status = "processing"
                session.commit()
                
                # Check if PDF file exists
                if not os.path.exists(pdf_path):
                    logger.error(f"PDF file not found at {pdf_path}")
                    job.status = "failed"
                    job.error_message = f"PDF file not found at {pdf_path}"
                    document.status = "failed"
                    session.commit()
                    return
                
                # Convert PDF to images
                logger.info(f"Converting PDF at {pdf_path} to images")
                images = await convert_pdf_to_images(pdf_path, max_pages=job.total_pages or 10)
                
                # Update total pages if needed
                if not job.total_pages or job.total_pages != len(images):
                    job.total_pages = len(images)
                    document.total_pages = len(images)
                    session.commit()
                    logger.info(f"Updated document to {len(images)} total pages")
                
                # Process each page
                all_results = []
                form_title = None
                explanation_text = None
                all_questions = []
                
                for i, img in enumerate(images):
                    page_num = i + 1
                    logger.info(f"Processing page {page_num} of {len(images)}")
                    
                    # Process the image
                    start_time = time.time()
                    result = await process_image(img, page_num, api_key)
                    processing_time = time.time() - start_time
                    
                    if result:
                        # Extract form title from the first page if available
                        if page_num == 1 and "form_title" in result:
                            form_title = result.get("form_title")
                        
                        # Extract explanation text from the first page if available    
                        if page_num == 1 and "explanation_text" in result:
                            explanation_text = result.get("explanation_text")
                            
                        # Add page number to each question if not already present
                        if "questions" in result:
                            for question in result["questions"]:
                                if "page" not in question:
                                    question["page"] = page_num
                            all_questions.extend(result["questions"])
                        
                        # Create extraction result record
                        extraction_result = ExtractionResult(
                            job_id=job.id,
                            page_number=page_num,
                            content=result,
                            processing_time=processing_time,
                            # Use overall confidence score or calculate from questions
                            confidence_score=result.get("overall_confidence", 
                                # If no overall score, calculate from questions
                                sum(q.get("confidence", 0.0) for q in result.get("questions", []))
                                / max(1, len(result.get("questions", []))) 
                                if result.get("questions") else 0.0
                            ) if not isinstance(result.get("error"), str) else 0.0
                        )
                        session.add(extraction_result)
                        all_results.append(extraction_result)
                        
                        # Update job progress
                        job.pages_processed = page_num
                        session.commit()
                        session.refresh(job)
                        logger.info(f"Processed page {page_num}/{len(images)} - {processing_time:.2f}s")
                    else:
                        logger.error(f"Failed to process page {page_num}")
                        extraction_result = ExtractionResult(
                            job_id=job.id,
                            page_number=page_num,
                            content={
                                "error": "Processing failed for this page",
                                "form_title": "Processing Error",
                                "document_type": "error",
                                "questions": [
                                    {
                                        "question": "Error Details",
                                        "answer": "The page processing failed with no results returned",
                                        "page": page_num,
                                        "confidence": 0.0,
                                        "is_handwritten": False
                                    }
                                ],
                                "overall_confidence": 0.0
                            },
                            processing_time=processing_time,
                            confidence_score=0.0
                        )
                        session.add(extraction_result)
                
                # If no successful results were obtained
                if not all_results:
                    logger.error(f"No pages were processed successfully for job {job_id}")
                    job.status = "failed"
                    job.error_message = "No pages were processed successfully"
                    document.status = "failed"
                    session.commit()
                    return
                
                # Create a combined content structure with results from all pages
                combined_content = {
                    "form_title": form_title,
                    "explanation_text": explanation_text,
                    "questions": all_questions,
                    "overall_confidence": 0.0 if not all_results else 
                        sum(r.confidence_score for r in all_results) / len(all_results)
                }
                
                # If the first page has structured data but it's not in the expected format
                if all_results and not combined_content["questions"]:
                    # Get data from first page result
                    first_page_result = session.exec(
                        select(ExtractionResult).where(
                            (ExtractionResult.job_id == job.id) & 
                            (ExtractionResult.page_number == 1)
                        )
                    ).first()
                    
                    if first_page_result and first_page_result.content:
                        # Check for flat key-value structure and convert to questions array
                        questions_list = []
                        content_to_convert = first_page_result.content.copy()
                        
                        # Skip these standard fields that aren't questions
                        skip_keys = ['form_title', 'questions', 'explanation_text', 'overall_confidence', 
                                    'document_type', 'error', 'raw_content', 'Signature', 'Position', 'Date',
                                    'Title', 'On behalf of']
                        
                        # Extract document metadata from the content
                        metadata = {}
                        if 'form_title' not in combined_content or not combined_content['form_title']:
                            # Try to find the form title in the content
                            for key in ['form_title', 'title', 'document_title', 'header', 'document_type']:
                                if key in content_to_convert:
                                    metadata['form_title'] = content_to_convert[key]
                                    break
                        
                        # Extract other metadata fields
                        metadata_fields = ['document_type', 'explanation_text', 'form_id', 'version', 'header']
                        for field in metadata_fields:
                            if field in content_to_convert and field not in combined_content:
                                metadata[field] = content_to_convert[field]
                                
                        # Add metadata to combined content
                        for key, value in metadata.items():
                            combined_content[key] = value
                            
                        # Process questions from flat key-value structure
                        for key, value in content_to_convert.items():
                            if key not in skip_keys and isinstance(value, str):
                                # Remove numbering from the start of the key if present
                                clean_key = key
                                if key.strip().startswith(tuple("0123456789")) and ". " in key:
                                    clean_key = key.split(". ", 1)[1]
                                    
                                questions_list.append({
                                    "question": clean_key,
                                    "answer": value,
                                    "page": 1,
                                    "confidence": 0.95,
                                    "is_handwritten": True
                                })
                        
                        if questions_list:
                            combined_content["questions"] = questions_list
                            
                            # Calculate overall confidence from questions
                            if combined_content["questions"]:
                                # Ensure all questions have a confidence value
                                for question in combined_content["questions"]:
                                    if "confidence" not in question or question["confidence"] is None:
                                        question["confidence"] = 0.95
                                
                                total_confidence = sum(q.get("confidence", 0.95) for q in combined_content["questions"])
                                avg_confidence = total_confidence / len(combined_content["questions"])
                                combined_content["overall_confidence"] = avg_confidence
                        else:
                            # If no questions were created, copy all fields as before
                            for key, value in first_page_result.content.items():
                                if key not in combined_content or not combined_content[key]:
                                    combined_content[key] = value
                
                # Add combined result record
                combined_result = ExtractionResult(
                    job_id=job.id,
                    page_number=0,  # 0 indicates combined result
                    content=combined_content,
                    processing_time=sum(r.processing_time for r in all_results),
                    confidence_score=combined_content.get("overall_confidence", 0.95)  # Default to 95% if not set
                )
                session.add(combined_result)
                
                # Ensure the job record also has the confidence score
                job.confidence_score = combined_content.get("overall_confidence", 0.95)
                session.commit()
                
                # Update job status
                job.status = "completed"
                job.completed_at = datetime.utcnow()
                job.pages_processed = len(images)
                
                # Update document status
                document.status = "completed"
                
                session.commit()
                session.refresh(job)
                logger.info(f"Job {job.id} status set to completed. Pages processed: {job.pages_processed}")

                session.refresh(document)
                logger.info(f"Document {document.id} status set to completed.")
                
        except Exception as e:
            logger.error(f"Error in background processing task: {str(e)}")
            # Update job status
            try:
                with Session(engine) as session:
                    job = session.exec(
                        select(ExtractionJob).where(ExtractionJob.id == job_id)
                    ).one_or_none()
                    
                    if job:
                        job.status = "failed"
                        job.error_message = str(e)
                        
                        # Also update document status
                        document = session.exec(
                            select(Document).where(Document.id == job.document_id)
                        ).one_or_none()
                        
                        if document:
                            document.status = "failed"
                        
                        session.commit()
                        
                        # Add error result
                        error_result = ExtractionResult(
                            job_id=job.id,
                            page_number=0,
                            content={
                                "error": str(e),
                                "form_title": "Processing Error",
                                "document_type": "error",
                                "questions": [
                                    {
                                        "question": "Error Details",
                                        "answer": f"An error occurred during document processing: {str(e)}",
                                        "page": 0,
                                        "confidence": 0.0,
                                        "is_handwritten": False
                                    }
                                ],
                                "overall_confidence": 0.0
                            },
                            processing_time=0,
                            confidence_score=0
                        )
                        session.add(error_result)
                        session.commit()
            except Exception as inner_error:
                logger.error(f"Failed to update job status after error: {str(inner_error)}")

    async def _validate_api_key(self, api_key: str) -> bool:
        """
        Validate the OpenAI API key by making a simple API call.
        
        Args:
            api_key: The OpenAI API key to validate
            
        Returns:
            bool: True if the API key is valid, False otherwise
        """
        if not api_key:
            logger.error("No API key provided")
            return False
            
        try:
            # Use httpx for async call
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {
                    "Authorization": f"Bearer {api_key}"
                }
                response = await client.get("https://api.openai.com/v1/models", headers=headers)
                
                if response.status_code == 200:
                    logger.info("API key validated successfully")
                    return True
                else:
                    logger.error(f"API key validation failed: {response.status_code} - {response.text}")
                    return False
        except Exception as e:
            logger.error(f"Error validating API key: {str(e)}")
            return False


async def convert_pdf_to_images(pdf_path: Union[str, Path], max_pages: int = 10) -> List:
    """
    Convert a PDF file to a list of images.
    
    Args:
        pdf_path: Path to the PDF file
        max_pages: Maximum number of pages to process
        
    Returns:
        List of PIL images
    """
    logger.info(f"Converting PDF to images: {pdf_path}")
    try:
        # First try the standard method
        try:
            images = convert_from_path(
                pdf_path,
                dpi=300,  # Higher DPI for better text recognition
                first_page=1,
                last_page=max_pages
            )
            if images:
                return images
        except Exception as e:
            logger.warning(f"Standard PDF conversion failed: {e}, trying alternative method")
        
        # If standard method fails, try with file bytes
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
            
        images = convert_from_bytes(
            pdf_bytes,
            dpi=300,
            first_page=1,
            last_page=max_pages
        )
        return images
    except Exception as e:
        logger.error(f"All PDF conversion methods failed: {e}")
        raise


def encode_image_to_base64(pil_image) -> str:
    """
    Convert a PIL image to base64-encoded string.
    
    Args:
        pil_image: PIL image
        
    Returns:
        Base64-encoded string
    """
    buffer = io.BytesIO()
    pil_image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


async def process_image(image, page_num: int, api_key: str) -> Dict:
    """
    Process a single image with GPT-4.1.
    
    Args:
        image: PIL image
        page_num: Page number
        api_key: OpenAI API key
        
    Returns:
        Dict of extracted content or None on failure
    """
    logger.info(f"Processing page {page_num}...")
    
    # Check for API key
    if not api_key:
        logger.error("No OpenAI API key provided for processing")
        return {
            "error": "No OpenAI API key provided. Please provide a valid API key to process this document.",
            "form_title": "API Key Missing",
            "document_type": "error",
            "questions": [
                {"question": "API Key", "answer": ""}
            ]
        }
    
    # Encode the image to base64
    base64_image = encode_image_to_base64(image)
    
    # Construct the messages for GPT-4.1
    messages = [
        {
            "role": "system",
            "content": "You are a world-class handwriting recognition assistant specializing in historical documents and forms. Extract all handwritten text from the provided image, including form titles, headers, and all text. Pay special attention to letterhead information such as 'THE LIVERPOOL SCHOOL FOR THE BLIND'. Return the result as structured JSON with form_title for the document title, document_type for the type of form, letterhead for the institution name, and questions/answers for form fields."
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": f"Extract all handwritten text and document information from page {page_num}. Look for letterhead information like 'THE LIVERPOOL SCHOOL FOR THE BLIND' at the top of the form. Identify the document type, any headers or letterhead, and all form fields. Return as JSON with form_title, document_type, letterhead, and questions array. Add confidence:0.95 field to each question."},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
            ]
        }
    ]
    
    # Make the API request with the new OpenAI client library
    try:
        from openai import AsyncOpenAI
        
        # Create client with the API key
        client = AsyncOpenAI(api_key=api_key)
        
        logger.info(f"Making API request to OpenAI with model {MODEL}...")
        
        response = await client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=4000,
            temperature=0.1  # Lower temperature for more deterministic outputs
        )
            
        # Extract the content from the response
        content = response.choices[0].message.content
        logger.info(f"Page {page_num} processed successfully: {content[:100]}...")
        
        # Parse JSON content
        try:
            # Check if the content is wrapped in ```json ... ``` code blocks
            if "```json" in content:
                json_part = content.split("```json")[1].split("```")[0].strip()
                parsed_content = json.loads(json_part)
            elif "```" in content:
                # Try with just the code block markers
                json_part = content.split("```")[1].split("```")[0].strip()
                parsed_content = json.loads(json_part)
            else:
                # Try to parse directly as JSON
                try:
                    parsed_content = json.loads(content)
                except json.JSONDecodeError:
                    # Try to fix common issues by completing the JSON
                    if content.strip().startswith('{') and not content.strip().endswith('}'):
                        # Add missing closing brace
                        fixed_content = content.strip() + "}"
                        try:
                            parsed_content = json.loads(fixed_content)
                        except json.JSONDecodeError:
                            # Still failed, fall back to error handling
                            logger.error(f"Failed to parse JSON from response: {content[:200]}...")
                            return {
                                "error": "Failed to parse JSON from OpenAI response",
                                "form_title": "JSON Parsing Error",
                                "document_type": "error",
                                "questions": [
                                    {
                                        "question": "Error Details",
                                        "answer": "The OpenAI API returned a response that couldn't be parsed as JSON",
                                        "page": page_num,
                                        "confidence": 0.0,
                                        "is_handwritten": False
                                    }
                                ],
                                "raw_content": content[:1000],  # Increase the length of raw_content to debug
                                "overall_confidence": 0.0
                            }
                    else:
                        # Not a fixable JSON format
                        logger.error(f"Failed to parse JSON from response: {content[:200]}...")
                        return {
                            "error": "Failed to parse JSON from OpenAI response",
                            "form_title": "JSON Parsing Error",
                            "document_type": "error",
                            "questions": [
                                {
                                    "question": "Error Details",
                                    "answer": "The OpenAI API returned a response that couldn't be parsed as JSON",
                                    "page": page_num,
                                    "confidence": 0.0,
                                    "is_handwritten": False
                                }
                            ],
                            "raw_content": content[:1000],  # Increase the length of raw_content to debug
                            "overall_confidence": 0.0
                        }
            
            # Ensure page numbers are set for all questions
            if "questions" in parsed_content:
                for question in parsed_content["questions"]:
                    if "page" not in question:
                        question["page"] = page_num
                    if "confidence" not in question or question["confidence"] is None:
                        question["confidence"] = 0.95
            
            # Calculate and set overall confidence
            if parsed_content.get("questions") and not parsed_content.get("overall_confidence"):
                total_confidence = sum(q.get("confidence", 0.95) for q in parsed_content["questions"])
                parsed_content["overall_confidence"] = total_confidence / len(parsed_content["questions"])
            
            return parsed_content
        except Exception as e:
            error_msg = f"Error in API request: {str(e)}"
            logger.error(error_msg)
            return {
                "error": error_msg,
                "form_title": "OpenAI API Error",
                "document_type": "error",
                "questions": [
                    {
                        "question": "Error Details",
                        "answer": f"An error occurred while processing your document: {str(e)}",
                        "page": page_num,
                        "confidence": 0.0,
                        "is_handwritten": False
                    }
                ],
                "overall_confidence": 0.0
            }
    except Exception as e:
        logger.error(f"OpenAI API call failed: {e}")
        return {
            "error": f"OpenAI API call failed: {e}",
            "form_title": "API Error",
            "document_type": "error",
            "questions": [
                {"question": "API Error", "answer": str(e)}
            ]
        }
