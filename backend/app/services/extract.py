from __future__ import annotations

from io import BytesIO
from typing import Union

import boto3
import openai
from pydantic import ValidationError

from ..schemas import ExtractionResult
from ..config import settings

openai_client = openai.OpenAI()  # requires OPENAI_API_KEY env var

def call_gpt_4o(file_bytes: bytes) -> dict:
    """Call GPT-4o multimodal to extract JSON."""
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",  # placeholder id
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an OCR data extractor. Return only valid JSON matching this schema:"
                    f"{ExtractionResult.schema_json(indent=None)}"
                ),
            },
            {
                "role": "user",
                "content": "Please extract data from this lab sheet.",
                "attachments": [
                    {
                        "file": file_bytes,
                        "mime_type": "application/pdf",
                    }
                ],
            },
        ],
        max_tokens=2048,
        response_format="json",
    )
    return response.choices[0].message.json()


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
    """Primary GPT-4o extraction with Textract fallback."""
    try:
        raw = call_gpt_4o(file_bytes)
        return ExtractionResult.model_validate(raw)
    except (Exception, ValidationError):
        raw = call_textract(file_bytes)
        return ExtractionResult.model_validate(raw) 