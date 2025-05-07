#!/usr/bin/env python
"""
Handwriting recognition using OpenAI's Assistants API instead of Chat Completions.
This script creates an assistant, uploads PDFs, and uses the Assistants API to extract handwritten text.
"""

import os
import sys
import json
import time
from pathlib import Path

import openai
from openai import OpenAI
import dotenv

# Load environment variables (this doesn't seem to work correctly)
dotenv.load_dotenv()

# Get OpenAI API key - allow it to be passed via command line argument
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
    print("Usage: python assistants_test.py --api-key YOUR_API_KEY path/to/pdf")
    sys.exit(1)

api_key = api_key.strip()
print(f"API key provided (starts with {api_key[:5]}...)")

# Create OpenAI client
client = OpenAI(api_key=api_key)

# Constants
ASSISTANT_NAME = "Handwriting Recognition Assistant"
ASSISTANT_MODEL = "gpt-4.1"  # Using GPT-4.1 with vision capabilities

def create_or_get_assistant():
    """Create a new assistant or get existing one with the same name"""
    try:
        # List existing assistants to look for one with our name
        assistants = client.beta.assistants.list(order="desc", limit=100)
        for assistant in assistants.data:
            if assistant.name == ASSISTANT_NAME:
                print(f"Using existing assistant: {assistant.id}")
                return assistant
        
        # Create new assistant if not found
        print("Creating new assistant...")
        assistant = client.beta.assistants.create(
            name=ASSISTANT_NAME,
            instructions=(
                "You are a handwriting recognition expert specializing in medical survey forms. "
                "Extract all handwritten text from the uploaded PDFs maintaining the form structure. "
                "Identify form fields and their values. Format numerical data appropriately. "
                "If text is illegible, mark it as [ILLEGIBLE]. "
                "Return data in a structured JSON format with field names and values."
            ),
            model=ASSISTANT_MODEL,
            tools=[{"type": "file_search"}]
        )
        print(f"Created new assistant: {assistant.id}")
        return assistant
    except Exception as e:
        print(f"Error creating/getting assistant: {str(e)}")
        sys.exit(1)

def process_pdf(pdf_path, max_polls=5, poll_interval=10):
    """Process a PDF file using Assistants API
    
    Args:
        pdf_path: Path to the PDF file
        max_polls: Maximum number of times to poll for complete results
        poll_interval: Time in seconds between polls
    """
    if not os.path.exists(pdf_path):
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)
    
    print(f"Processing PDF: {pdf_path}")
    try:
        # 1. Create or get assistant
        assistant = create_or_get_assistant()
        
        # 2. Upload the PDF file
        print("Uploading PDF...")
        file = client.files.create(
            file=open(pdf_path, "rb"),
            purpose="assistants"
        )
        print(f"File uploaded with ID: {file.id}")
        
        # 3. Create a thread
        thread = client.beta.threads.create()
        print(f"Created thread: {thread.id}")
        
        # 4. Add a message to the thread with the file
        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content="Please extract all handwritten text from this survey form PDF. Return results in a structured JSON format with field names and values.",
            attachments=[
                {
                    "file_id": file.id,
                    "tools": [{"type": "file_search"}]
                }
            ]
        )
        print(f"Added message with file to thread")
        
        # 5. Run the assistant on the thread
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id,
        )
        print(f"Started run: {run.id}")
        
        # 6. Wait for run to complete
        while run.status in ["queued", "in_progress"]:
            print(f"Run status: {run.status}...")
            time.sleep(3)
            run = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
        
        print(f"Run completed with status: {run.status}")
        
        # 7. Poll for complete results
        full_content = ""
        for poll_count in range(max_polls):
            print(f"Polling for results (attempt {poll_count + 1}/{max_polls})...")
            
            # Get all messages from the assistant
            messages = client.beta.threads.messages.list(
                thread_id=thread.id
            )
            
            # Extract all assistant messages
            assistant_messages = [msg for msg in messages.data if msg.role == "assistant"]
            if not assistant_messages:
                print("No response from assistant yet")
                if poll_count < max_polls - 1:
                    time.sleep(poll_interval)
                    continue
                else:
                    return None
            
            # Concatenate content from all assistant messages
            combined_content = ""
            for msg in assistant_messages:
                for content_item in msg.content:
                    if content_item.type == "text":
                        combined_content += content_item.text.value + "\n\n"
            
            # Check if we have substantive content (more than just processing message)
            if "processing" not in combined_content.lower() or len(combined_content) > 500:
                full_content = combined_content
                break
            
            if poll_count < max_polls - 1:
                print("Still processing. Waiting for more complete results...")
                time.sleep(poll_interval)
        
        # 8. Save results
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        output_file = output_dir / f"{Path(pdf_path).stem}_assistant_results.json"
        with open(output_file, "w") as f:
            f.write(full_content)
        
        print(f"Results saved to {output_file}")
        return full_content
        
    except Exception as e:
        print(f"Error processing PDF: {str(e)}")
        return None

def main():
    if len(sys.argv) <= pdf_path_index:
        print(f"Usage: python assistants_test.py [--api-key YOUR_API_KEY] <pdf_path>")
        sys.exit(1)
    
    # Check for polling argument
    max_polls = 5
    poll_interval = 10
    pdf_path = sys.argv[pdf_path_index]
    
    if len(sys.argv) > pdf_path_index + 2 and sys.argv[pdf_path_index + 1] == "--polls":
        try:
            max_polls = int(sys.argv[pdf_path_index + 2])
        except ValueError:
            pass
    
    result = process_pdf(pdf_path, max_polls=max_polls, poll_interval=poll_interval)
    
    if result:
        print("\nExtracted content:")
        print(result)

if __name__ == "__main__":
    main() 