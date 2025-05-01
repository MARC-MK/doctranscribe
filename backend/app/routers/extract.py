from datetime import datetime
from uuid import uuid4
from io import BytesIO

from fastapi import APIRouter, UploadFile, File, Depends, status
import pandas as pd

from ..services.extract import extract
from ..schemas import ExtractionResult
from ..deps import get_s3_client
from ..config import settings
from ..services.xlsx import to_xlsx_bytes
from ..services.anomaly import detect_anomalies

router = APIRouter(prefix="/extract", tags=["extraction"])


@router.post("/", response_model=ExtractionResult, status_code=status.HTTP_201_CREATED)
async def extract_route(
    file: UploadFile = File(...),
    s3=Depends(get_s3_client),
):
    file_bytes = await file.read()
    result = extract(file_bytes)

    # Store JSON and XLSX
    prefix = f"results/{datetime.utcnow().strftime('%Y/%m/%d')}/{uuid4()}"
    json_key = f"{prefix}.json"
    xlsx_key = f"{prefix}.xlsx"
    s3.put_object(
        Bucket=settings.s3_bucket,
        Key=json_key,
        Body=result.model_dump_json(indent=None).encode(),
        ContentType="application/json",
        ServerSideEncryption="AES256",
    )

    # XLSX upload
    xlsx_bytes = to_xlsx_bytes(result)
    s3.put_object(
        Bucket=settings.s3_bucket,
        Key=xlsx_key,
        Body=xlsx_bytes,
        ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ServerSideEncryption="AES256",
    )

    # Detect anomalies for numeric columns
    df = pd.read_excel(BytesIO(xlsx_bytes))
    annotated = detect_anomalies(df, numeric_cols=["measurement"])
    anomaly_count = int(annotated["is_anomaly"].sum())

    return {"sheet_name": result.sheet_name, "rows": result.rows, "anomalies": anomaly_count} 