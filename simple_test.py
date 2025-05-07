#!/usr/bin/env python
"""
Simple test script for GPT-4.1 handwriting recognition.
This is a standalone script that doesn't depend on the backend infrastructure.
"""

import base64
import json
import os
import sys
from pathlib import Path

import httpx
import dotenv
from pdf2image import convert_from_path

# Load environment variables
dotenv.load_dotenv()

# Get the OpenAI API key - allow it to be passed via command line argument
if len(sys.argv) > 2 and sys.argv[1] == '--api-key':
    api_key = sys.argv[2]
    pdf_path_index = 3
else:
    # Try to get from environment, but it might not work
    api_key = os.environ.get("OPENAI_API_KEY")
    pdf_path_index = 1

# Validate API key
if not api_key or api_key == "your_openai_api_key_here":
    print("Error: No valid OpenAI API key provided")
    print("Usage: python simple_test.py --api-key YOUR_API_KEY path/to/pdf")
    sys.exit(1)

# Clean the API key (remove any whitespace or newlines)
api_key = api_key.strip()
print(f"API key provided (starts with {api_key[:5]}...)")

# Configuration
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
MODEL = "gpt-4.1"  # Using the new GPT-4.1 model that supports vision

def convert_pdf_to_images(pdf_path, max_pages=5):
    """Convert a PDF file to a list of images"""
    print(f"Converting PDF to images: {pdf_path}")
    try:
        images = convert_from_path(
            pdf_path,
            dpi=300,  # Higher DPI for better text recognition
            first_page=1,
            last_page=max_pages
        )
        return images
    except Exception as e:
        print(f"Error converting PDF to images: {e}")
        sys.exit(1)

def encode_image_to_base64(pil_image):
    """Convert a PIL image to base64-encoded string"""
    import io
    buffer = io.BytesIO()
    pil_image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

async def process_image(image, page_num):
    """Process a single image with GPT-4.1"""
    print(f"Processing page {page_num}...")
    
    # Encode the image to base64
    base64_image = encode_image_to_base64(image)
    
    # Construct the messages for GPT-4.1
    messages = [
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
            
            print(f"Making API request to {OPENAI_API_URL}...")
            response = await client.post(
                OPENAI_API_URL,
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                print(f"Page {page_num} processed successfully")
                return {
                    "page": page_num,
                    "content": content
                }
            else:
                print(f"Error from OpenAI API: {response.status_code} - {response.text}")
                return None
    except Exception as e:
        print(f"Error in API request: {e}")
        return None

async def main():
    # Check command line arguments
    if len(sys.argv) <= pdf_path_index:
        print(f"Usage: python simple_test.py [--api-key YOUR_API_KEY] <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[pdf_path_index]
    if not os.path.exists(pdf_path):
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)
    
    # Get max pages argument if provided
    max_pages = 5  # Default
    if len(sys.argv) > pdf_path_index + 2 and sys.argv[pdf_path_index + 1] == "--max-pages":
        try:
            max_pages = int(sys.argv[pdf_path_index + 2])
        except ValueError:
            print(f"Warning: Invalid --max-pages value, using default: {max_pages}")
    
    print(f"Processing PDF: {pdf_path} (max pages: {max_pages})")
    
    # Convert PDF to images
    images = convert_pdf_to_images(pdf_path, max_pages=max_pages)
    print(f"Converted {len(images)} pages from PDF")
    
    # Process each image
    results = []
    for i, img in enumerate(images):
        result = await process_image(img, i + 1)
        if result:
            results.append(result)
    
    # Save results
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / f"{Path(pdf_path).stem}_gpt41_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"Results saved to {output_file}")
    
    # Print extracted content summary
    print("\nExtracted content summary:")
    for result in results:
        print(f"\nPage {result['page']}:")
        content = result['content']
        
        # Try to parse JSON if it's in that format
        try:
            # Check if the content is wrapped in ```json ... ``` code blocks
            if "```json" in content:
                json_part = content.split("```json")[1].split("```")[0].strip()
                parsed = json.loads(json_part)
                print(f"Successfully parsed JSON with {len(parsed)} fields")
                # Print a preview of a few fields
                preview = dict(list(parsed.items())[:3])
                print(json.dumps(preview, indent=2) + "...")
            else:
                # Try parsing the whole content as JSON
                parsed = json.loads(content)
                print(f"Successfully parsed JSON with {len(parsed)} fields")
                # Print a preview of a few fields
                preview = dict(list(parsed.items())[:3])
                print(json.dumps(preview, indent=2) + "...")
        except (json.JSONDecodeError, IndexError, ValueError):
            # If not JSON or parsing fails, just print the first few lines
            preview_lines = content.split("\n")[:5]
            print("\n".join(preview_lines) + "...")
    
    print(f"\nFull results available in {output_file}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 