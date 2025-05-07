from datetime import datetime
from uuid import uuid4
import io
from PyPDF2 import PdfReader
from sqlmodel import Session

from fastapi import APIRouter, File, UploadFile, HTTPException, status, Depends

from ..deps import get_s3_client, get_session
from ..config import settings
from ..schemas import PDFMetadataResponse

router = APIRouter(prefix="/upload", tags=["ingestion"])


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=PDFMetadataResponse)
async def upload_file(
    file: UploadFile = File(...),
    s3=Depends(get_s3_client),
    session: Session = Depends(get_session),
):
    # Validate content type (PDF/TIFF)
    if file.content_type not in {"application/pdf", "image/tiff"}:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    # Read file bytes for processing
    file.file.seek(0)
    file_bytes = file.file.read()
    file_size = len(file_bytes)
    file.file.seek(0)

    # Extract PDF page count (only for PDFs)
    page_count = None
    if file.content_type == "application/pdf":
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            page_count = len(reader.pages)
        except Exception:
            raise HTTPException(status_code=400, detail="Could not read PDF for page count")
    else:
        page_count = 1  # Assume 1 page for TIFF for now

    # Generate summary string
    def human_readable_size(num_bytes):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if num_bytes < 1024.0:
                return f"{num_bytes:.1f} {unit}"
            num_bytes /= 1024.0
        return f"{num_bytes:.1f} TB"
    summary = f"{page_count} pages, {human_readable_size(file_size)}, {file.filename}"

    # Store metadata in DB
    # pdf_upload = PDFUpload(
    #     filename=file.filename,
    #     filesize_bytes=file_size,
    #     page_count=page_count,
    #     summary=summary,
    # )
    # session.add(pdf_upload)
    # session.commit()
    # session.refresh(pdf_upload)

    key = f"uploads/{datetime.utcnow().strftime('%Y/%m/%d')}/{uuid4()}-{file.filename}"
    s3.upload_fileobj(
        Fileobj=io.BytesIO(file_bytes),
        Bucket=settings.s3_bucket,
        Key=key,
        ExtraArgs={
            "ContentType": file.content_type,
            "ServerSideEncryption": "AES256",
        },
    )
    return PDFMetadataResponse(
        filename=file.filename,
        filesize_bytes=file_size,
        page_count=page_count,
        summary=summary,
    ) 