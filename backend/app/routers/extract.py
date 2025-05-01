from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, UploadFile, File, Depends, status

from ..services.extract import extract
from ..schemas import ExtractionResult
from ..deps import get_s3_client
from ..config import settings

router = APIRouter(prefix="/extract", tags=["extraction"])


@router.post("/", response_model=ExtractionResult, status_code=status.HTTP_201_CREATED)
async def extract_route(
    file: UploadFile = File(...),
    s3=Depends(get_s3_client),
):
    file_bytes = await file.read()
    result = extract(file_bytes)

    # Store JSON next to original using same prefix (.json extension) or generated path
    json_key = f"results/{datetime.utcnow().strftime('%Y/%m/%d')}/{uuid4()}.json"
    s3.put_object(
        Bucket=settings.s3_bucket,
        Key=json_key,
        Body=result.model_dump_json(indent=None).encode(),
        ContentType="application/json",
        ServerSideEncryption="AES256",
    )

    return result 