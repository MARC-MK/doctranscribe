from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, File, UploadFile, HTTPException, status, Depends

from ..deps import get_s3_client
from ..config import settings

router = APIRouter(prefix="/upload", tags=["ingestion"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    s3=Depends(get_s3_client),
):
    # Validate content type (PDF/TIFF)
    if file.content_type not in {"application/pdf", "image/tiff"}:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    key = f"uploads/{datetime.utcnow().strftime('%Y/%m/%d')}/{uuid4()}-{file.filename}"
    s3.upload_fileobj(
        Fileobj=file.file,
        Bucket=settings.s3_bucket,
        Key=key,
        ExtraArgs={
            "ContentType": file.content_type,
            "ServerSideEncryption": "AES256",
        },
    )
    return {"bucket": settings.s3_bucket, "key": key} 