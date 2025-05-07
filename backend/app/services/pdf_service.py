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
from typing import Dict, List, Optional, Tuple, Union
from uuid import UUID

import httpx
from fastapi import UploadFile
from pdf2image import convert_from_bytes, convert_from_path
from sqlmodel import Session, select

from ..database import get_session
from ..models import (
    Document, 
    ExtractionJob, 
    ExtractionResult, 
    ProcessingStatus, 
    XLSXExport
)

# Configure logging
logger = logging.getLogger(__name__)

# Environment variables and configuration
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
MODEL = "gpt-4.1"  # Using GPT-4.1 with vision capabilities
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

class PDFProcessingService:
    """Service for processing PDFs and extracting handwritten text."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the service with an optional API key."""
        self.api_key = api_key or OPENAI_API_KEY
        if not self.api_key:
            logger.warning("No OpenAI API key provided")
    
    async def process_document(self, document_id: UUID, session: Session) -> ExtractionJob:
        """
        Process a document with handwriting recognition.
        
        Args:
            document_id: UUID of the document to process
            session: Database session
            
        Returns:
            ExtractionJob: The extraction job record
        """
        # Find the document
        document = session.exec(
            select(Document).where(Document.id == document_id)
        ).one_or_none()
        
        if not document:
            raise ValueError(f"Document with ID {document_id} not found")
        
        # Create extraction job
        job = ExtractionJob(
            document_id=document_id,
            started_at=datetime.utcnow(),
            model_name=MODEL,
            status=ProcessingStatus.PROCESSING,
            total_pages=document.total_pages or 0,
            pages_processed=0
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        
        # Update document status
        document.status = ProcessingStatus.PROCESSING
        session.commit()
        
        # Create a background task to periodically update job status
        # This ensures the frontend gets regular updates even for long-running jobs
        async def update_job_status():
            while True:
                await asyncio.sleep(2)  # Update every 2 seconds
                
                # Check if job is still running
                current_job = session.exec(
                    select(ExtractionJob).where(ExtractionJob.id == job.id)
                ).one_or_none()
                
                if not current_job or current_job.status in [
                    ProcessingStatus.COMPLETED, 
                    ProcessingStatus.FAILED
                ]:
                    break
                
                # Commit any pending changes to ensure frontend sees latest progress
                try:
                    session.commit()
                except Exception as e:
                    logger.error(f"Error updating job status: {str(e)}")
        
        # Start the background task
        status_task = asyncio.create_task(update_job_status())
        
        try:
            # Get file path
            file_path = Path(UPLOAD_DIR) / str(document.id)
            
            if not file_path.exists():
                raise FileNotFoundError(f"PDF file not found at {file_path}")
            
            # Convert PDF to images
            logger.info(f"Converting PDF at {file_path} to images")
            images = convert_pdf_to_images(file_path, max_pages=document.total_pages or 10)
            
            # Update total pages if needed
            if not document.total_pages or document.total_pages != len(images):
                document.total_pages = len(images)
                job.total_pages = len(images)
                session.commit()
                logger.info(f"Updated document to {len(images)} total pages")
            
            # Check API key
            if not self.api_key:
                logger.warning("No OpenAI API key provided, results will be mock data")
            
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
                result = await process_image(img, page_num, self.api_key)
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
                    logger.info(f"Processed page {page_num}/{len(images)} - {processing_time:.2f}s")
                else:
                    logger.error(f"Failed to process page {page_num}")
                    extraction_result = ExtractionResult(
                        job_id=job.id,
                        page_number=page_num,
                        content={"error": "Processing failed for this page"},
                        processing_time=processing_time,
                        confidence_score=0.0
                    )
                    session.add(extraction_result)
            
            # Create a combined content structure with results from all pages
            combined_content = {
                "form_title": form_title,
                "explanation_text": explanation_text,
                "questions": all_questions,
                "overall_confidence": 0.0 if not all_results else 
                    sum(r.confidence_score for r in all_results) / len(all_results)
            }
            
            # Add combined result record
            combined_result = ExtractionResult(
                job_id=job.id,
                page_number=0,  # 0 indicates combined result
                content=combined_content,
                processing_time=sum(r.processing_time for r in all_results),
                confidence_score=0.0 if not all_results else 
                    sum(r.confidence_score for r in all_results) / len(all_results)
            )
            session.add(combined_result)
            
            # Update job status
            job.status = ProcessingStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            
            # Update document status
            document.status = ProcessingStatus.COMPLETED
            
            session.commit()
            session.refresh(job)
            
            logger.info(f"Document {document_id} processing completed - {job.pages_processed} pages")
            return job
            
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            job.status = ProcessingStatus.FAILED
            document.status = ProcessingStatus.FAILED
            session.commit()
            raise
        finally:
            # Make sure background task is cancelled
            status_task.cancel()
            try:
                await status_task
            except asyncio.CancelledError:
                pass
    
    async def save_uploaded_file(self, file: UploadFile) -> Document:
        """
        Save an uploaded PDF file and create a Document record.
        
        Args:
            file: The uploaded PDF file
            
        Returns:
            Document: The created document record
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
        
        # Save to database
        async with get_session() as session:
            session.add(document)
            session.commit()
            session.refresh(document)
        
        # Save file to disk
        file_path = Path(UPLOAD_DIR) / str(document.id)
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
                
                document.total_pages = total_pages
                
                async with get_session() as session:
                    session.add(document)
                    session.commit()
        except Exception as e:
            logger.error(f"Error getting page count: {str(e)}")
        
        return document


def convert_pdf_to_images(pdf_path: Union[str, Path], max_pages: int = 10) -> List:
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
        images = convert_from_path(
            pdf_path,
            dpi=300,  # Higher DPI for better text recognition
            first_page=1,
            last_page=max_pages
        )
        return images
    except Exception as e:
        logger.error(f"Error converting PDF to images: {e}")
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
        return {"error": "No OpenAI API key provided. Please provide a valid API key to process this document."}
    
    # Encode the image to base64
    base64_image = encode_image_to_base64(image)
    
    # Construct the messages for GPT-4.1
    messages = [
        {
            "role": "system",
            "content": (
                "You are a world-class handwriting recognition expert with superior organizational skills, specializing in extracting and structuring content from medical and survey forms. "
                "Your expertise includes:\n"
                "- Precise recognition of various handwriting styles, even when messy or hurried\n"
                "- Superior organization of form data into consistent, well-structured formats\n"
                "- Accurate identification of form elements like questions, fields, and tables\n"
                "- Contextual understanding to infer unclear text based on surrounding content\n\n"
                "Extract all handwritten text from the image while maintaining the form's structure and hierarchy. "
                "Identify question-answer pairs, field labels and values, and any other form elements. "
                "Format numerical data appropriately based on context (dates, measurements, scales, etc). "
                "If text is completely illegible, mark it as [ILLEGIBLE]. "
                "For each question, include the page number where it appears. "
                "Include a confidence score for each answer between 0.0 and 1.0. "
                "We are targeting 92% confidence, but include all answers regardless of confidence. "
                "For very low confidence items, mark them as '[UNCLEAR]' but still include your best interpretation. "
                "If there is a form title, extract it as 'form_title'. "
                "If there is explanatory text at the beginning, extract it as 'explanation_text'. "
                "Return data in a structured JSON format with this schema:\n"
                "{\n"
                "  \"form_title\": \"Title of the form\",\n"
                "  \"explanation_text\": \"Any introductory text explaining the form purpose\",\n"
                "  \"overall_confidence\": 0.0-1.0,\n"
                "  \"questions\": [\n"
                "    {\n"
                "      \"question\": \"The question text\",\n"
                "      \"answer\": \"The handwritten answer\",\n"
                "      \"page\": " + str(page_num) + ",\n"
                "      \"confidence\": 0.0-1.0\n"
                "    }\n"
                "  ]\n"
                "}\n"
                "Only return the JSON object without any additional text, explanations, or markdown. "
                "Maintain clear, logical organization of all extracted content. "
                "We're aiming for high accuracy (92%+) but need to extract all text during our fine-tuning period."
            )
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"Extract all handwritten information from this form (page {page_num}) with your superior organizational skills. Identify the form structure, all questions, answers, and other elements. Return ONLY the JSON object with well-organized content. Make sure to set the page number to {page_num} for all questions found on this page. Include confidence scores for each answer."
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_image}",
                        "detail": "high"
                    }
                }
            ]
        }
    ]
    
    # Make the API request
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:  # Increased timeout for larger images
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            payload = {
                "model": MODEL,
                "messages": messages,
                "max_tokens": 4000,
                "temperature": 0.1,  # Lower temperature for more deterministic outputs
            }
            
            logger.info(f"Making API request to {OPENAI_API_URL}...")
            response = await client.post(
                OPENAI_API_URL,
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                logger.info(f"Page {page_num} processed successfully: {content[:100]}...")
                
                # Parse JSON content
                try:
                    # Try to parse directly
                    parsed_content = json.loads(content)
                    
                    # Ensure page numbers are set for all questions
                    if "questions" in parsed_content:
                        for question in parsed_content["questions"]:
                            if "page" not in question:
                                question["page"] = page_num
                    
                    return parsed_content
                except json.JSONDecodeError:
                    # Check if the content is wrapped in ```json ... ``` code blocks
                    if "```json" in content:
                        json_part = content.split("```json")[1].split("```")[0].strip()
                        parsed_content = json.loads(json_part)
                    elif "```" in content:
                        # Try with just the code block markers
                        json_part = content.split("```")[1].split("```")[0].strip()
                        parsed_content = json.loads(json_part)
                    else:
                        logger.error(f"Failed to parse JSON from response: {content[:200]}...")
                        return {"error": "Failed to parse JSON", "raw_content": content}
                    
                    # Ensure page numbers are set for all questions
                    if "questions" in parsed_content:
                        for question in parsed_content["questions"]:
                            if "page" not in question:
                                question["page"] = page_num
                    
                    return parsed_content
            else:
                error_msg = f"Error from OpenAI API: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {"error": error_msg}
    except Exception as e:
        error_msg = f"Error in API request: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg} 