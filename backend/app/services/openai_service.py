import base64
import io
import json
import logging
import os
import time
from typing import List, Optional, Dict, Any, Union

from openai import OpenAI, AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
from fastapi import HTTPException
from pdf2image import convert_from_bytes

from ..config import settings

logger = logging.getLogger(__name__)

class OpenAIService:
    """Service for interacting with OpenAI's API, particularly for processing PDFs with GPT-4.1"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("OPENAI_API_KEY environment variable not set")
        
        self.model = settings.openai_model
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None
    
    async def process_pdf(self, pdf_binary: bytes, max_pages: int = 10) -> Dict[str, Any]:
        """
        Process a PDF file using GPT-4.1 to extract handwritten text.
        
        Args:
            pdf_binary: Raw PDF file bytes
            max_pages: Maximum number of pages to process (to avoid excessive costs)
            
        Returns:
            Dictionary containing extracted data and processing metadata
        """
        # Check if API key is available
        if not self.api_key:
            logger.warning("No OpenAI API key provided, returning mock data")
            return {
                "success": True,
                "pages_processed": 1,
                "structured_data": {
                    "form_fields": {
                        "patient_name": "John Doe",
                        "patient_id": "12345",
                        "date_of_visit": "2023-10-15"
                    },
                    "mock_data": True
                },
                "raw_results": [
                    {
                        "page": 1,
                        "content": json.dumps({
                            "form_fields": {
                                "patient_name": "John Doe",
                                "patient_id": "12345",
                                "date_of_visit": "2023-10-15"
                            }
                        }),
                        "finish_reason": "stop",
                        "processing_time": 100
                    }
                ]
            }
            
        try:
            # Convert PDF to list of images
            try:
                logger.info("Converting PDF to images...")
                images = self._pdf_to_images(pdf_binary, max_pages)
                logger.info(f"Successfully converted PDF to {len(images)} images")
            except Exception as e:
                logger.error(f"Error converting PDF to images: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"PDF conversion failed: {str(e)}"
                )
            
            # Process each page
            results = []
            for i, img in enumerate(images):
                logger.info(f"Processing page {i+1} of {len(images)}")
                page_result = await self._process_image(img, page_num=i+1)
                results.append(page_result)
            
            # Combine results into structured data
            structured_data = self._combine_results(results)
            
            return {
                "success": True,
                "pages_processed": len(images),
                "structured_data": structured_data,
                "raw_results": results
            }
            
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"PDF processing failed: {str(e)}"
            )
    
    def _pdf_to_images(self, pdf_binary: bytes, max_pages: int) -> List[bytes]:
        """Convert PDF bytes to a list of image bytes"""
        try:
            # Log the poppler path for debugging
            import shutil
            poppler_path = shutil.which('pdftoppm')
            logger.info(f"Poppler path: {poppler_path}")
            
            # Convert PDF to list of PIL Images
            pil_images = convert_from_bytes(
                pdf_binary,
                dpi=300,  # Higher DPI for better text recognition
                first_page=1,
                last_page=max_pages
            )
            
            logger.info(f"Converted PDF to {len(pil_images)} PIL images")
            
            # Convert PIL Images to bytes
            image_bytes_list = []
            for img in pil_images:
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                image_bytes_list.append(img_byte_arr.getvalue())
            
            return image_bytes_list
            
        except Exception as e:
            logger.error(f"Error converting PDF to images: {str(e)}")
            raise
    
    async def _process_image(self, image_bytes: bytes, page_num: int) -> Dict[str, Any]:
        """
        Process a single image with GPT-4.1
        
        Args:
            image_bytes: PNG image as bytes
            page_num: Page number for reference
            
        Returns:
            Dictionary with extracted content
        """
        # Base64 encode the image
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        # Construct the messages for GPT-4.1
        messages: List[ChatCompletionMessageParam] = [
            {
                "role": "system",
                "content": (
                    "You are a precise handwriting recognition expert specializing in medical survey forms. "
                    "Extract all handwritten text from the image maintaining the form structure. "
                    "Identify form fields and their values. Format numerical data appropriately. "
                    "If text is illegible, mark it as [ILLEGIBLE]. "
                    "Return data in a structured JSON format with field names and values."
                )
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Extract all handwritten information from this survey form (page {page_num})."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}"
                        }
                    }
                ]
            }
        ]
        
        # Make API request with retries
        for attempt in range(self.max_retries):
            try:
                if not self.client:
                    raise ValueError("OpenAI client not initialized (no API key)")
                
                logger.info(f"Sending request to OpenAI for page {page_num}, attempt {attempt+1}")
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=4000,
                    temperature=0.1  # Lower temperature for more deterministic outputs
                )
                
                # Process response
                content = response.choices[0].message.content
                finish_reason = response.choices[0].finish_reason
                total_tokens = response.usage.total_tokens if response.usage else 0
                
                logger.info(f"Received response for page {page_num}, tokens: {total_tokens}")
                
                # Try to parse JSON from the content
                try:
                    # Direct JSON parsing
                    json_content = json.loads(content)
                except json.JSONDecodeError:
                    # Try to extract JSON from markdown code blocks
                    if "```json" in content:
                        json_part = content.split("```json")[1].split("```")[0].strip()
                        json_content = json.loads(json_part)
                    elif "```" in content:
                        json_part = content.split("```")[1].split("```")[0].strip()
                        json_content = json.loads(json_part)
                    else:
                        logger.warning(f"GPT response is not valid JSON: {content[:200]}...")
                        json_content = {"raw_text": content}
                
                return {
                    "page": page_num,
                    "content": json_content,
                    "finish_reason": finish_reason,
                    "processing_time": total_tokens
                }
                
            except Exception as e:
                logger.error(f"Error processing image (attempt {attempt+1}/{self.max_retries}): {str(e)}")
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    return {
                        "page": page_num,
                        "error": f"Failed after {self.max_retries} attempts: {str(e)}",
                        "content": {},
                        "processing_time": 0
                    }
    
    def _combine_results(self, page_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Combine results from multiple pages into a structured data format
        
        Args:
            page_results: List of results from each page
            
        Returns:
            Structured data suitable for XLSX generation
        """
        # For now, a simple combination of all pages
        combined_data = {
            "form_fields": {},
            "tables": []
        }
        
        for page in page_results:
            try:
                if "error" in page:
                    logger.warning(f"Skipping page {page.get('page')} due to error: {page.get('error')}")
                    continue
                
                # Extract content
                page_content = page.get("content", {})
                
                # Merge form fields
                if isinstance(page_content, dict) and "form_fields" in page_content:
                    combined_data["form_fields"].update(page_content["form_fields"])
                elif isinstance(page_content, dict):
                    # If no form_fields key but content is a dict, merge it directly
                    combined_data["form_fields"].update(page_content)
                
                # Append table data
                if isinstance(page_content, dict) and "tables" in page_content:
                    combined_data["tables"].extend(page_content["tables"])
            except Exception as e:
                logger.warning(f"Error combining results for page {page.get('page')}: {str(e)}")
                combined_data[f"raw_page_{page.get('page')}"] = page.get("content", {})
                
        return combined_data 