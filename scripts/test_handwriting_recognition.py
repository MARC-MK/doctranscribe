#!/usr/bin/env python
"""
Test script for handwriting recognition functionality.

Usage:
    python test_handwriting_recognition.py <path_to_pdf>

Example:
    python test_handwriting_recognition.py test_samples/handwritten_form.pdf
"""

import argparse
import base64
import json
import os
import sys
from pathlib import Path

import httpx
import dotenv

# Load environment variables
dotenv.load_dotenv()

# Configuration
API_BASE_URL = "http://localhost:8000"
TEST_ENDPOINT = f"{API_BASE_URL}/handwriting/test"
PROCESS_ENDPOINT = f"{API_BASE_URL}/handwriting/process"
RESULTS_ENDPOINT = f"{API_BASE_URL}/handwriting/result"
STATUS_ENDPOINT = f"{API_BASE_URL}/handwriting/status"

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def check_service_status():
    """Check if the handwriting recognition service is available"""
    try:
        print(f"{Colors.BLUE}Checking handwriting recognition service...{Colors.ENDC}")
        response = httpx.post(TEST_ENDPOINT, timeout=10.0)
        response.raise_for_status()
        print(f"{Colors.GREEN}Service status: {response.json()}{Colors.ENDC}")
        return True
    except Exception as e:
        print(f"{Colors.RED}Error: Service unavailable - {str(e)}{Colors.ENDC}")
        print(f"{Colors.YELLOW}Make sure the backend server is running on {API_BASE_URL}{Colors.ENDC}")
        return False


def process_pdf(pdf_path):
    """Upload PDF for processing"""
    try:
        print(f"{Colors.BLUE}Processing PDF: {pdf_path}{Colors.ENDC}")
        
        with open(pdf_path, "rb") as f:
            files = {"file": (os.path.basename(pdf_path), f, "application/pdf")}
            response = httpx.post(
                PROCESS_ENDPOINT,
                files=files,
                params={"max_pages": 5},  # Process up to 5 pages for testing
                timeout=30.0
            )
        
        response.raise_for_status()
        result = response.json()
        print(f"{Colors.GREEN}PDF submitted successfully{Colors.ENDC}")
        print(f"Job ID: {result['job_id']}")
        print(f"Status: {result['status']}")
        return result['job_id']
    
    except Exception as e:
        print(f"{Colors.RED}Error uploading PDF: {str(e)}{Colors.ENDC}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")
        return None


def check_job_status(job_id):
    """Check the status of a job"""
    try:
        print(f"{Colors.BLUE}Checking status for job: {job_id}{Colors.ENDC}")
        response = httpx.get(f"{STATUS_ENDPOINT}/{job_id}", timeout=10.0)
        response.raise_for_status()
        result = response.json()
        status = result['status']
        print(f"Status: {status}")
        
        if status == "FAILED":
            print(f"{Colors.RED}Processing failed: {result.get('error', 'Unknown error')}{Colors.ENDC}")
            return False
        
        if status == "COMPLETED":
            print(f"{Colors.GREEN}Processing completed successfully{Colors.ENDC}")
            return True
        
        print(f"{Colors.YELLOW}Job is still processing...{Colors.ENDC}")
        return None
    
    except Exception as e:
        print(f"{Colors.RED}Error checking job status: {str(e)}{Colors.ENDC}")
        return False


def get_job_result(job_id):
    """Get the results of a completed job"""
    try:
        print(f"{Colors.BLUE}Getting results for job: {job_id}{Colors.ENDC}")
        response = httpx.get(f"{RESULTS_ENDPOINT}/{job_id}", timeout=10.0)
        response.raise_for_status()
        result = response.json()
        
        # Save structured data as JSON
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        # Save structured data
        with open(output_dir / f"{job_id}_data.json", "w") as f:
            json.dump(result["data"], f, indent=2)
            print(f"{Colors.GREEN}Structured data saved to {output_dir}/{job_id}_data.json{Colors.ENDC}")
        
        # Save XLSX file
        xlsx_data = base64.b64decode(result["xlsx_data"])
        with open(output_dir / f"{job_id}.xlsx", "wb") as f:
            f.write(xlsx_data)
            print(f"{Colors.GREEN}XLSX file saved to {output_dir}/{job_id}.xlsx{Colors.ENDC}")
        
        print(f"{Colors.GREEN}Successfully retrieved results{Colors.ENDC}")
        return True
    
    except Exception as e:
        print(f"{Colors.RED}Error getting job results: {str(e)}{Colors.ENDC}")
        return False


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Test handwriting recognition functionality")
    parser.add_argument("pdf_path", help="Path to PDF file to process")
    parser.add_argument("--poll", type=int, default=5, help="Number of times to poll for results")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.pdf_path):
        print(f"{Colors.RED}Error: File not found: {args.pdf_path}{Colors.ENDC}")
        return 1
    
    if not check_service_status():
        return 1
    
    job_id = process_pdf(args.pdf_path)
    if not job_id:
        return 1
    
    # Poll for job completion
    import time
    poll_count = 0
    while poll_count < args.poll:
        status = check_job_status(job_id)
        
        if status is True:  # Job completed
            get_job_result(job_id)
            return 0
        
        if status is False:  # Job failed
            return 1
        
        # Job still processing
        poll_count += 1
        if poll_count < args.poll:
            print(f"{Colors.YELLOW}Waiting 5 seconds before checking again...{Colors.ENDC}")
            time.sleep(5)
    
    print(f"{Colors.YELLOW}Reached maximum polling attempts. Check status later with:{Colors.ENDC}")
    print(f"  curl {STATUS_ENDPOINT}/{job_id}")
    print(f"{Colors.YELLOW}And get results when complete with:{Colors.ENDC}")
    print(f"  curl {RESULTS_ENDPOINT}/{job_id}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 