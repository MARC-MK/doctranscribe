from fastapi import APIRouter, Request, HTTPException, WebSocket, WebSocketDisconnect, Response
from app.schemas import XLSXSignedURLResponse
from app.config import settings
import boto3
import os
import asyncio
import json
from botocore.exceptions import ClientError
import io
import pandas as pd

router = APIRouter(prefix="/results", tags=["extraction"])

# In-memory job status store for demo (replace with Redis for prod)
job_status_store = {}

def generate_sample_xlsx():
    """Generate a sample XLSX using pandas"""
    # Create a sample dataframe
    data = {
        "Sample": ["Blood Glucose", "Hemoglobin", "White Blood Cells", "Cholesterol", "Sodium"],
        "Measurement": ["Fasting", "Total", "Total", "Total", "Serum"],
        "Value": [85, 14.2, 6.8, 240, 140],
        "Units": ["mg/dL", "g/dL", "K/uL", "mg/dL", "mmol/L"],
        "Reference Range": ["70-100", "13.5-17.5", "4.5-11.0", "<200", "135-145"],
        "Anomaly": ["No", "No", "No", "Yes", "No"]
    }
    
    df = pd.DataFrame(data)
    
    # Write to bytes buffer
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, sheet_name="Lab Test Results")
    buffer.seek(0)
    
    return buffer.getvalue()

@router.get("/")
async def get_results(request: Request):
    return request.app.state.jobs  # type: ignore 

@router.get("/{job_id}/xlsx-url", response_model=XLSXSignedURLResponse)
async def get_xlsx_signed_url(job_id: str, request: Request):
    jobs = getattr(request.app.state, "jobs", [])
    job = next((j for j in jobs if j.get("job_id") == job_id), None)
    if not job or not job.get("xlsx_s3_key"):
        raise HTTPException(status_code=404, detail="Job or XLSX key not found")
    s3 = boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        endpoint_url=settings.s3_endpoint_url,
    )
    bucket = settings.s3_bucket
    key = job["xlsx_s3_key"]
    try:
        url = s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=600,  # 10 minutes
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Could not generate XLSX URL: {e}")
    return XLSXSignedURLResponse(url=url)

@router.get("/{job_id}/xlsx")
async def get_xlsx_file(job_id: str, request: Request, download: bool = False):
    """Returns a sample XLSX file"""
    jobs = getattr(request.app.state, "jobs", [])
    job = next((j for j in jobs if j.get("job_id") == job_id), None)
    
    if not job or not job.get("xlsx_s3_key"):
        # Generate a sample XLSX file
        file_content = generate_sample_xlsx()
    else:
        # Try to get the file from S3
        try:
            s3 = boto3.client(
                "s3",
                region_name=settings.aws_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                endpoint_url=settings.s3_endpoint_url,
            )
            response = s3.get_object(Bucket=settings.s3_bucket, Key=job["xlsx_s3_key"])
            file_content = response['Body'].read()
        except Exception:
            # Fallback to sample if S3 fails
            file_content = generate_sample_xlsx()
    
    content_disposition = f"attachment; filename={job_id}.xlsx" if download else "inline"
    
    return Response(
        content=file_content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": content_disposition
        }
    )

@router.websocket("/ws/jobs/{job_id}")
async def job_status_ws(websocket: WebSocket, job_id: str):
    await websocket.accept()
    try:
        progress = 0
        # Simulate progress for demo; replace with real job tracking
        while progress < 100:
            status = job_status_store.get(job_id, {
                "status": "processing",
                "progress": progress,
                "message": f"Processing ({progress}%)"
            })
            await websocket.send_text(json.dumps(status))
            await asyncio.sleep(0.5)
            progress += 10
            job_status_store[job_id] = {
                "status": "processing" if progress < 100 else "done",
                "progress": min(progress, 100),
                "message": f"Processing ({min(progress, 100)}%)" if progress < 100 else "Done!"
            }
        # Send final done message
        await websocket.send_text(json.dumps(job_status_store[job_id]))
    except WebSocketDisconnect:
        pass 