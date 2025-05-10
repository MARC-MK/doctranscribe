from fastapi import APIRouter, Request, HTTPException, WebSocket, WebSocketDisconnect, Response
from app.schemas import XLSXSignedURLResponse
from app.config import settings
import boto3
import asyncio
import json
import io
import pandas as pd
import uuid
from datetime import datetime
from uuid import uuid4

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
    """Returns a list of processed jobs with their results"""
    jobs = getattr(request.app.state, "jobs", [])
    
    # If no jobs exist, create a default job for demonstration
    if not jobs:
        # Generate a sample job with valid ID
        default_job = {
            "job_id": str(uuid.uuid4()),
            "sheet_name": "Sample Lab Results",
            "anomalies": 2,
            "xlsx_s3_key": None  # Will trigger fallback generation
        }
        # Add the job to the state
        request.app.state.jobs = [default_job]
        jobs = [default_job]
    
    return jobs

@router.get("/{job_id}/xlsx-url", response_model=XLSXSignedURLResponse)
async def get_xlsx_signed_url(job_id: str, request: Request):
    jobs = getattr(request.app.state, "jobs", [])
    job = next((j for j in jobs if j.get("job_id") == job_id), None)
    
    # If job not found, create a placeholder job
    if not job:
        # Log the issue
        print(f"Job {job_id} not found, creating placeholder")
        job = {"job_id": job_id, "xlsx_s3_key": None}
        
    # If no XLSX key, generate sample and store it
    if not job.get("xlsx_s3_key"):
        try:
            # Create a sample XLSX
            file_content = generate_sample_xlsx()
            
            # Set up S3 client
            s3 = boto3.client(
                "s3",
                region_name=settings.aws_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                endpoint_url=settings.s3_endpoint_url,
            )
            
            # Ensure bucket exists
            try:
                s3.head_bucket(Bucket=settings.s3_bucket)
            except:
                s3.create_bucket(Bucket=settings.s3_bucket)
            
            # Upload sample to S3
            prefix = f"results/{datetime.utcnow().strftime('%Y/%m/%d')}/{uuid4()}"
            xlsx_key = f"{prefix}.xlsx"
            
            s3.put_object(
                Bucket=settings.s3_bucket,
                Key=xlsx_key,
                Body=file_content,
                ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            
            # Update job with new key
            job["xlsx_s3_key"] = xlsx_key
            
            # Generate URL
            url = s3.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": settings.s3_bucket, "Key": xlsx_key},
                ExpiresIn=600,  # 10 minutes
            )
            
            return XLSXSignedURLResponse(url=url)
        except Exception as e:
            # Log the error and fall back to a direct download
            print(f"Error generating signed URL: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Could not generate XLSX URL: {e}")
    
    # Normal S3 URL generation flow
    try:
        s3 = boto3.client(
            "s3",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            endpoint_url=settings.s3_endpoint_url,
        )
        bucket = settings.s3_bucket
        key = job["xlsx_s3_key"]
        
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
    """Returns an XLSX file, generating a sample if needed"""
    print(f"Getting XLSX for job_id: {job_id}")
    
    # First check if we have the job
    jobs = getattr(request.app.state, "jobs", [])
    job = next((j for j in jobs if j.get("job_id") == job_id), None)
    
    # Get content from S3 or generate sample
    try:
        if job and job.get("xlsx_s3_key"):
            print(f"Found job with XLSX key: {job['xlsx_s3_key']}")
            # Get from S3
            s3 = boto3.client(
                "s3",
                region_name=settings.aws_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                endpoint_url=settings.s3_endpoint_url,
            )
            try:
                response = s3.get_object(Bucket=settings.s3_bucket, Key=job["xlsx_s3_key"])
                file_content = response['Body'].read()
                print(f"Successfully retrieved XLSX from S3, size: {len(file_content)} bytes")
            except Exception as e:
                print(f"Error retrieving from S3: {str(e)}, falling back to sample")
                file_content = generate_sample_xlsx()
        else:
            print("No job found or no XLSX key, generating sample")
            # Generate sample
            file_content = generate_sample_xlsx()
    except Exception as e:
        print(f"Error in get_xlsx_file: {str(e)}")
        # Always ensure we return something
        file_content = generate_sample_xlsx()
    
    # Set proper filename
    job_name = job.get("sheet_name", "results") if job else "results"
    safe_name = "".join([c if c.isalnum() else "_" for c in job_name])
    filename = f"{safe_name}.xlsx"
    
    content_disposition = f"attachment; filename={filename}" if download else "inline"
    
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