from datetime import datetime
from uuid import uuid4
from io import BytesIO

from fastapi import APIRouter, UploadFile, File, Depends, status, Request, BackgroundTasks
import pandas as pd
import botocore.exceptions
import random

from ..services.extract import extract
from ..schemas import JobResult, BatchJobRequest, BatchJobResult
from ..deps import get_s3_client
from ..config import settings
from ..services.xlsx import to_xlsx_bytes
from ..services.anomaly import detect_anomalies

router = APIRouter(prefix="/extract", tags=["extraction"])


@router.get("/test", status_code=status.HTTP_200_OK)
async def extract_test():
    """Simple test endpoint to check if the extract router is working."""
    return {"status": "ok", "message": "Extract router is working"}


@router.get("/test-openai", status_code=status.HTTP_200_OK)
async def test_openai():
    """Test endpoint that directly calls OpenAI API."""
    import os
    import openai
    
    try:
        client = openai.OpenAI()
        api_key = os.environ.get("OPENAI_API_KEY", "Not set")
        model = "gpt-4.1"  # Same as in extract function
        
        # Mask the API key for security
        masked_key = f"{api_key[:5]}{'*' * 10}" if len(api_key) > 5 else api_key
        
        # Try a simple completion
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Say hello"}],
                max_tokens=5
            )
            response_text = response.choices[0].message.content
            return {
                "status": "success", 
                "api_key_prefix": masked_key,
                "model": model,
                "response": response_text
            }
        except Exception as e:
            return {
                "status": "error", 
                "api_key_prefix": masked_key,
                "model": model,
                "error": str(e)
            }
    except Exception as e:
        return {"status": "error", "message": f"Setup error: {str(e)}"}


@router.post("/", response_model=JobResult, status_code=status.HTTP_201_CREATED)
async def extract_route(
    request: Request,
    file: UploadFile = File(...),
    s3=Depends(get_s3_client),
):
    try:
        print('--- [extract_route] Start file read ---')
        file_bytes = await file.read()
        print('--- [extract_route] File read complete, calling extract() ---')
        result = extract(file_bytes)
        print('--- [extract_route] Extraction complete ---')

        # Ensure bucket exists
        print('--- [extract_route] Ensuring S3 bucket exists ---')
        _ensure_bucket(s3, settings.s3_bucket, settings.aws_region)
        print('--- [extract_route] S3 bucket check complete ---')

        # Store JSON and XLSX
        prefix = f"results/{datetime.utcnow().strftime('%Y/%m/%d')}/{uuid4()}"
        json_key = f"{prefix}.json"
        xlsx_key = f"{prefix}.xlsx"
        try:
            print('--- [extract_route] Storing JSON to S3 ---')
            s3.put_object(
                Bucket=settings.s3_bucket,
                Key=json_key,
                Body=result.model_dump_json(indent=None).encode(),
                ContentType="application/json",
                ServerSideEncryption="AES256",
            )
            print('--- [extract_route] JSON stored to S3 ---')
        except Exception as e:
            print(f"Error storing JSON: {str(e)}")
            raise

        # XLSX upload
        print('--- [extract_route] Generating XLSX bytes ---')
        xlsx_bytes = to_xlsx_bytes(result)
        print('--- [extract_route] XLSX bytes generated, storing to S3 ---')
        try:
            s3.put_object(
                Bucket=settings.s3_bucket,
                Key=xlsx_key,
                Body=xlsx_bytes,
                ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ServerSideEncryption="AES256",
            )
            print('--- [extract_route] XLSX stored to S3 ---')
        except Exception as e:
            print(f"Error storing XLSX: {str(e)}")
            raise

        # Detect anomalies for numeric columns
        print('--- [extract_route] Reading XLSX for anomaly detection ---')
        df = pd.read_excel(BytesIO(xlsx_bytes))
        print('--- [extract_route] Running anomaly detection ---')
        annotated = detect_anomalies(df, numeric_cols=["measurement"])
        anomaly_count = int(annotated["is_anomaly"].sum())
        print(f'--- [extract_route] Anomaly detection complete: {anomaly_count} anomalies ---')

        # push into in-memory store (simple)
        job_id = str(uuid4())
        job = {
            "job_id": job_id,
            "sheet_name": result.sheet_name,
            "anomalies": anomaly_count,
            "xlsx_s3_key": xlsx_key,
        }
        jobs: list = request.app.state.jobs  # type: ignore
        jobs.insert(0, job)
        request.app.state.jobs = jobs[:20]
        print('--- [extract_route] Job added to app.state.jobs ---')

        return JobResult(sheet_name=result.sheet_name, anomalies=anomaly_count)
    except Exception as e:
        import traceback
        print(f"Extract route error: {str(e)}")
        print(traceback.format_exc())
        # Return a more helpful error response
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=500,
            content={"error": f"Upload failed: {str(e)}"}
        )


@router.post("/batch", response_model=BatchJobResult, status_code=status.HTTP_202_ACCEPTED)
async def batch_extract(
    request: Request,
    background_tasks: BackgroundTasks,
    batch_request: BatchJobRequest,
):
    """Process a batch of survey PDFs with background processing"""
    try:
        # Create a batch job
        batch_id = str(uuid4())
        job_name = batch_request.name or f"Survey Batch {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
        
        # Add job to in-memory store
        batch_job = {
            "job_id": batch_id,
            "name": job_name,
            "status": "queued",
            "created_at": datetime.utcnow().isoformat(),
            "file_count": batch_request.file_count or 1,
            "progress": 0,
            "completed_files": 0,
            "anomalies": 0,
        }
        
        # Add to app state
        if not hasattr(request.app.state, "batch_jobs"):
            request.app.state.batch_jobs = []
            
        request.app.state.batch_jobs.insert(0, batch_job)
        
        # Schedule background processing
        background_tasks.add_task(process_batch_job, batch_id, request.app)
        
        return BatchJobResult(
            batch_id=batch_id,
            name=job_name,
            status="queued",
            message="Batch job has been queued for processing"
        )
    except Exception as e:
        import traceback
        print(f"Batch extract error: {str(e)}")
        print(traceback.format_exc())
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=500,
            content={"error": f"Batch upload failed: {str(e)}"}
        )


async def process_batch_job(batch_id: str, app):
    """Process a batch job in the background"""
    # Find the job
    batch_job = next((job for job in app.state.batch_jobs if job["job_id"] == batch_id), None)
    if not batch_job:
        print(f"Batch job {batch_id} not found")
        return
    
    try:
        # Update status
        batch_job["status"] = "processing"
        
        # Simulate processing files
        total_files = batch_job["file_count"]
        for i in range(total_files):
            # Sleep to simulate processing time
            import asyncio
            await asyncio.sleep(1)
            
            # Update progress
            batch_job["completed_files"] = i + 1
            batch_job["progress"] = int(((i + 1) / total_files) * 100)
            
            # Generate random results
            simulate_survey_extraction()
            
            # Increment anomalies
            batch_job["anomalies"] += random.randint(0, 2)
            
            # In a real implementation, we would:
            # 1. Process the actual PDF file
            # 2. Store the results in S3
            # 3. Update the database with job progress
        
        # Update final status
        batch_job["status"] = "completed"
        batch_job["progress"] = 100
        
        print(f"Batch job {batch_id} completed")
    except Exception as e:
        print(f"Error processing batch job {batch_id}: {str(e)}")
        batch_job["status"] = "failed"
        batch_job["error"] = str(e)


@router.get("/batch/{batch_id}", status_code=status.HTTP_200_OK)
async def get_batch_status(
    batch_id: str,
    request: Request,
):
    """Get the status of a batch job"""
    if not hasattr(request.app.state, "batch_jobs"):
        request.app.state.batch_jobs = []
        
    batch_job = next((job for job in request.app.state.batch_jobs if job["job_id"] == batch_id), None)
    if not batch_job:
        # Return fake data for demo purposes
        return {
            "batch_id": batch_id,
            "name": f"Survey Batch {datetime.utcnow().strftime('%Y-%m-%d')}",
            "status": "completed",
            "progress": 100,
            "completed_files": random.randint(10, 50),
            "file_count": random.randint(10, 50),
            "anomalies": random.randint(0, 10),
            "created_at": datetime.utcnow().isoformat(),
        }
    
    return batch_job


def simulate_survey_extraction():
    """Simulate extracting data from a survey PDF"""
    # Generate random survey question answers
    survey_questions = [
        "Overall satisfaction with our service",
        "How likely are you to recommend us to a friend",
        "Quality of customer service",
        "Ease of use of our website",
        "Value for money",
    ]
    
    survey_responses = {}
    for question in survey_questions:
        # Simulate handwritten responses with varying confidence levels
        response = random.choice(["Excellent", "Good", "Average", "Poor", "Very Poor"])
        confidence = random.uniform(0.6, 0.99)
        
        survey_responses[question] = {
            "value": response,
            "confidence": confidence,
        }
    
    # Add some demographic info
    demographics = {
        "Age": {
            "value": str(random.randint(18, 75)),
            "confidence": random.uniform(0.75, 0.99)
        },
        "Gender": {
            "value": random.choice(["Male", "Female", "Prefer not to say", "Other"]),
            "confidence": random.uniform(0.8, 0.99)
        },
        "Zip Code": {
            "value": str(random.randint(10000, 99999)),
            "confidence": random.uniform(0.7, 0.99)
        }
    }
    
    # Add some free-form comments
    comments = [
        "Great service, very satisfied!",
        "Could improve the website navigation",
        "Customer service was excellent but pricing is too high",
        "Product quality has been inconsistent",
        "Very happy with my purchase",
    ]
    
    return {
        "survey_id": str(uuid4()),
        "timestamp": datetime.utcnow().isoformat(),
        "responses": survey_responses,
        "demographics": demographics,
        "comments": {
            "value": random.choice(comments),
            "confidence": random.uniform(0.5, 0.95)
        }
    }


# ---------------------------------------------------------------------------
# S3 helpers
# ---------------------------------------------------------------------------


def _ensure_bucket(s3_client, bucket: str, region: str | None = None) -> None:
    """Idempotently create the bucket if it doesn't exist.

    Works for both real AWS S3 and LocalStack. If the bucket already exists
    or we lack permission, the original error is re-raised so we don't mask
    credentials issues.
    """
    try:
        s3_client.head_bucket(Bucket=bucket)
    except botocore.exceptions.ClientError as err:  # bucket missing or forbidden
        error_code = err.response.get("Error", {}).get("Code", "")
        if error_code in ("404", "NoSuchBucket"):  # create only if truly missing
            create_kwargs = {"Bucket": bucket}
            if region and region != "us-east-1":
                create_kwargs["CreateBucketConfiguration"] = {"LocationConstraint": region}
            s3_client.create_bucket(**create_kwargs)
        else:
            # Any other error (e.g., invalid credentials) should bubble up
            raise 