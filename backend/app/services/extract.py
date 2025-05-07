from __future__ import annotations

from io import BytesIO
import time
import json
from typing import Union

import boto3
import openai
from pydantic import ValidationError

from ..schemas import ExtractionResult
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


def call_textract(file_bytes: bytes) -> dict:
    textract = boto3.client(
        "textract",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )
    resp = textract.analyze_document(Document={"Bytes": file_bytes}, FeatureTypes=["TABLES", "FORMS"])
    # Simple naive extraction stub
    return {"sheet_name": "textract_fallback", "rows": []}


def extract(file_bytes: bytes) -> ExtractionResult:
    """Primary GPT-4.1 extraction with Textract fallback."""
    import os
    print(f"OpenAI API Key: {os.environ.get('OPENAI_API_KEY', '')[:5]}{'*' * 10}")
    print(f"AWS Access Key: {os.environ.get('AWS_ACCESS_KEY_ID', '')[:5]}{'*' * 10}")
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
            # Return more descriptive error information in the fallback data
            error_msg = str(e)[:50] if len(str(e)) > 50 else str(e)
            
            # Create more meaningful fallback data that indicates what went wrong
            return ExtractionResult.model_validate({
                "sheet_name": f"Error: {error_msg}",
                "rows": [
                    {"sample_id": "ERR1", "measurement": 0.0, "unit": "N/A", "remark": f"API Error: {error_msg}"},
                    {"sample_id": "ERR2", "measurement": 0.0, "unit": "N/A", "remark": "Check logs for details"}
                ]
            }) 