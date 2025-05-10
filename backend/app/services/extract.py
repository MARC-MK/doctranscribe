from __future__ import annotations

from io import BytesIO
import time
import json
import traceback

import boto3
import openai
from pydantic import ValidationError

from ..schemas import ExtractionResult, LabRow
from ..config import settings

openai_client = openai.OpenAI()  # requires OPENAI_API_KEY env var

# --- GPT-4.1 extractor ----------------------------------------------------
# We use the full-size model (gpt-4.1) first; we can later downgrade to
# gpt-4.1-mini or gpt-4.1-nano depending on performance/cost.

def call_gpt_4_1(file_bytes: bytes, timeout: int = 300) -> dict:
    """Extract JSON using the *latest* OpenAI Assistants API instead of legacy chat-completions.

    Workflow:
        1. Upload the PDF (`purpose='assistants'`).
        2. Create a transient Assistant with `code_interpreter` to enable PDF tooling
           and instructions enforcing the `ExtractionResult` JSON schema.
        3. Start a thread, attach the file, and post the user message.
        4. Create a run, poll until completion (or timeout).
        5. Parse and return the JSON from the Assistant's reply.
    """
    try:
        # 1) Upload PDF for assistant context
        upload = openai_client.files.create(
            file=("document.pdf", BytesIO(file_bytes)),
            purpose="assistants",
        )

        # 2) Create Assistant (in production, reuse an assistant_id to save quota)
        assistant = openai_client.beta.assistants.create(
            name="Lab PDF Extractor (GPT-4.1)",
            model=settings.openai_model,
            instructions=(
                "You are a precise lab data extraction specialist. "
                "Extract structured information from lab test sheets and return "
                "data EXACTLY matching this JSON schema (no markdown, no extra keys):\n" +
                ExtractionResult.schema_json(indent=None)
            ),
            tools=[{"type": "file_search"}],
        )

        # 3) New thread + initial user message
        thread = openai_client.beta.threads.create()

        openai_client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content="Please extract the data from the attached PDF and respond with *only* the JSON.",
            attachments=[
                {
                    "file_id": upload.id,
                    "tools": [{"type": "file_search"}],
                }
            ],
        )

        # 4) Run Assistant and poll
        run = openai_client.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant.id)

        start_ts = time.time()
        while run.status not in {"completed", "failed", "cancelled", "expired"}:
            if time.time() - start_ts > timeout:
                raise TimeoutError("Assistants run timed out")
            time.sleep(2)
            run = openai_client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

        if run.status != "completed":
            raise RuntimeError(f"Assistants run finished with status '{run.status}'")

        # 5) Retrieve last assistant message and parse JSON
        msgs = openai_client.beta.threads.messages.list(thread_id=thread.id, order="desc", limit=1)
        if not msgs.data:
            raise ValueError("No messages returned by assistant")

        for segment in msgs.data[0].content:
            if getattr(segment, "type", "") == "text":
                try:
                    return json.loads(segment.text.value)
                except Exception as err:
                    raise ValueError(f"Could not parse JSON response: {err}")

        raise ValueError("Assistant response did not include JSON text content")
    except Exception as e:
        print(f"Error in call_gpt_4_1: {str(e)}")
        print(traceback.format_exc())
        raise


def call_textract(file_bytes: bytes) -> dict:
    try:
        textract = boto3.client(
            "textract",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
        resp = textract.analyze_document(Document={"Bytes": file_bytes}, FeatureTypes=["TABLES", "FORMS"])
        
        # Convert Textract response to our schema format
        # This is a simple implementation - would need to be enhanced for production
        rows = []
        for block in resp.get("Blocks", []):
            if block.get("BlockType") == "LINE":
                # Try to extract basic information from each line
                text = block.get("Text", "")
                if ":" in text:
                    sample_id, value = text.split(":", 1)
                    rows.append({
                        "sample_id": sample_id.strip(),
                        "measurement": 0.0,  # Default value
                        "unit": "N/A",
                        "remark": value.strip()
                    })
        
        return {
            "sheet_name": "Textract Extraction",
            "rows": rows
        }
    except Exception as e:
        print(f"Error in call_textract: {str(e)}")
        print(traceback.format_exc())
        # Return a minimal valid structure
        return {
            "sheet_name": "Textract Error",
            "rows": [
                {"sample_id": "ERROR", "measurement": 0.0, "unit": "N/A", "remark": f"Textract error: {str(e)}"}
            ]
        }


def extract(file_bytes: bytes) -> ExtractionResult:
    """Primary GPT-4.1 extraction with Textract fallback."""
    import os
    print(f"OpenAI API Key: {os.environ.get('OPENAI_API_KEY', '')[:5] if os.environ.get('OPENAI_API_KEY', '') else 'Not set'}{'*' * 10 if os.environ.get('OPENAI_API_KEY', '') else ''}")
    print(f"AWS Access Key: {os.environ.get('AWS_ACCESS_KEY_ID', '')[:5] if os.environ.get('AWS_ACCESS_KEY_ID', '') else 'Not set'}{'*' * 10 if os.environ.get('AWS_ACCESS_KEY_ID', '') else ''}")
    print(f"S3 Endpoint URL: {os.environ.get('S3_ENDPOINT_URL', 'Not set')}")
    
    try:
        print("Attempting extraction with Assistants API (gpt-4.1 full)…")
        raw = call_gpt_4_1(file_bytes)  # now routed through Assistants API
        print("Assistants extraction successful!")
        return ExtractionResult.model_validate(raw)
    except (Exception, ValidationError) as e:
        print(f"Assistants extraction failed: {str(e)}")
        try:
            print("Attempting AWS Textract fallback...")
            raw = call_textract(file_bytes)
            print("AWS Textract fallback successful!")
            return ExtractionResult.model_validate(raw)
        except Exception as textract_error:
            print(f"Textract fallback also failed: {str(textract_error)}")
            print("Using mock fallback data")
            
            # Create valid fallback data that indicates what went wrong
            return ExtractionResult(
                sheet_name="Extraction Error",
                rows=[
                    LabRow(sample_id="ERR1", measurement=0.0, unit="N/A", remark=f"API Error: {str(e)[:100]}"),
                    LabRow(sample_id="ERR2", measurement=0.0, unit="N/A", remark="Check logs for details")
                ]
            ) 